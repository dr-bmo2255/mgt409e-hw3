"""Turn every photo in data/products into a structured catalogue and a search index.

Writes output/catalogue.json (the full entries) and output/catalogue.db (the same
entries indexed by characteristic). Run with --help for options.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from PIL import Image
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.usage import UsageLimits

from catalogue_db import build_database, facet_counts
from config import (
    CATALOGUE_DB_PATH,
    CATALOGUE_JSON_PATH,
    MAX_LOOP_USD,
    PRODUCTS_DIR,
    PROJECT_DIR,
    build_model,
    catalogue_model_name,
    inside_sandbox,
    model_name,
    price_usd,
)
from models import CATEGORY_BY_TYPE, HOUSE_BRAND, Catalogue, CatalogueEntry, ProductVisualFields

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIDE = 768
DEFAULT_CONCURRENCY = 8
CHECKPOINT_EVERY = 10
# One image is one request; a second is allowed only to repair invalid structured output.
PER_PRODUCT_LIMITS = UsageLimits(
    request_limit=2, input_tokens_limit=6_000, output_tokens_limit=2_000
)
# Assumed cost of a call before any real one has finished, used to reserve budget.
FIRST_CALL_ESTIMATE_USD = Decimal("0.01")
STOP_WORDS = {"the", "and", "of", "for", "a", "an", "with", "in", "on", "vs", "est"}

INSTRUCTIONS = """\
You catalogue apparel for Campus Customs, a shop that sells Yale merchandise.
You are shown one studio product photo and the product's filename slug.

Describe only what is visible. Copy printed text exactly as it appears, including
small secondary lines. The slug is reliable for the product's name, garment maker,
and which sport, residential college, school, or family member it is for; the photo
is the authority for colour, garment construction, and the design itself.

For brand, name the garment maker only when its name or logo is legible in the photo or
it is named in the slug; otherwise answer 'House Brand'.

Use null and empty lists rather than guessing. Choose 'general_yale' when the design
names no sport, college, school, family member, or event.
"""

describer = Agent(output_type=ProductVisualFields, instructions=INSTRUCTIONS)


@dataclass
class Budget:
    """Running spend for one build, with room reserved for calls still in flight."""

    cap: Decimal
    spent: Decimal = Decimal("0")
    reserved: Decimal = Decimal("0")
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    unpriced_calls: int = 0
    skipped: list[str] = field(default_factory=list)

    def estimate(self) -> Decimal:
        return self.spent / self.calls if self.calls else FIRST_CALL_ESTIMATE_USD

    def try_reserve(self) -> Decimal | None:
        amount = self.estimate()
        if self.spent + self.reserved + amount > self.cap:
            return None
        self.reserved += amount
        return amount

    def settle(self, reservation: Decimal, name: str, input_tokens: int, output_tokens: int) -> None:
        self.reserved -= reservation
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        cost = price_usd(input_tokens, output_tokens, name)
        if cost is None:
            self.unpriced_calls += 1
        else:
            self.spent += cost

    def release(self, reservation: Decimal) -> None:
        self.reserved -= reservation


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def product_images(folder: Path = PRODUCTS_DIR) -> list[Path]:
    folder = inside_sandbox(folder)
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


def prepare_image(path: Path) -> bytes:
    """Flatten onto white and cap the size so every photo costs a predictable amount."""

    with Image.open(path) as image:
        image = image.convert("RGBA")
        flattened = Image.new("RGB", image.size, "white")
        flattened.paste(image, mask=image.getchannel("A"))
        flattened.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buffer = io.BytesIO()
        flattened.save(buffer, format="JPEG", quality=88)
        return buffer.getvalue()


def search_terms(product_id: str, fields: ProductVisualFields) -> list[str]:
    """Lower-case lookup words drawn from everything that names or marks the product."""

    sources = [
        product_id.replace("-", " "),
        *fields.printed_text,
        *fields.graphic_elements,
        fields.sport,
        fields.residential_college,
        fields.school,
        fields.family_member,
        fields.event,
        None if fields.brand == HOUSE_BRAND else fields.brand,
    ]
    words = re.findall(r"[a-z0-9]+", " ".join(s for s in sources if s).lower())
    return sorted({w for w in words if len(w) > 1 and w not in STOP_WORDS})


def make_entry(path: Path, digest: str, fields: ProductVisualFields, name: str) -> CatalogueEntry:
    return CatalogueEntry(
        **fields.model_dump(),
        product_id=path.stem,
        image_file=path.relative_to(PROJECT_DIR).as_posix(),
        image_sha256=digest,
        garment_category=CATEGORY_BY_TYPE[fields.garment_type],
        search_terms=search_terms(path.stem, fields),
        described_by_model=name,
        described_at_utc=_now_iso(),
    )


def load_cache(path: Path = CATALOGUE_JSON_PATH) -> dict[str, CatalogueEntry]:
    """Entries from the last build, keyed by product id; empty if none or unreadable."""

    if not path.is_file():
        return {}
    try:
        catalogue = Catalogue.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return {entry.product_id: entry for entry in catalogue.entries}


def write_catalogue(entries: list[CatalogueEntry], path: Path = CATALOGUE_JSON_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries, key=lambda entry: entry.product_id)
    catalogue = Catalogue(
        generated_at_utc=_now_iso(),
        model=catalogue_model_name(),
        product_count=len(ordered),
        entries=ordered,
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(catalogue.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


async def describe_product(path: Path, digest: str, name: str) -> tuple[CatalogueEntry, int, int]:
    image = BinaryContent(
        prepare_image(path), media_type="image/jpeg", vendor_metadata={"detail": "high"}
    )
    result = await describer.run(
        [f"Filename slug: {path.stem}", image],
        model=build_model(name),
        usage_limits=PER_PRODUCT_LIMITS,
    )
    usage = result.usage
    return make_entry(path, digest, result.output, name), usage.input_tokens, usage.output_tokens


async def build(
    limit: int | None, force: bool, concurrency: int, max_usd: Decimal
) -> tuple[list[CatalogueEntry], Budget, dict[str, int]]:
    images = product_images()[:limit]
    cache = {} if force else load_cache()
    entries: dict[str, CatalogueEntry] = {}
    pending: list[tuple[Path, str]] = []
    for path in images:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = cache.get(path.stem)
        if cached and cached.image_sha256 == digest:
            # Search terms are derived, so refresh them in case the rules changed.
            entries[path.stem] = cached.model_copy(
                update={"search_terms": search_terms(path.stem, cached)}
            )
        else:
            pending.append((path, digest))
    counts = {"photos": len(images), "reused": len(entries), "described": 0, "failed": 0}

    budget = Budget(cap=max_usd)
    if pending:
        primary = catalogue_model_name()
        gate = asyncio.Semaphore(concurrency)

        async def worker(path: Path, digest: str) -> None:
            async with gate:
                reservation = budget.try_reserve()
                if reservation is None:
                    budget.skipped.append(path.stem)
                    return
                name = primary
                try:
                    try:
                        entry, tokens_in, tokens_out = await describe_product(path, digest, name)
                    except ModelHTTPError as exc:
                        # The small model's image filter wrongly blocks some heraldic crests.
                        if "content policy" not in str(exc) or model_name() == primary:
                            raise
                        name = model_name()
                        print(f"  {path.stem}: blocked by {primary} image filter, using {name}")
                        entry, tokens_in, tokens_out = await describe_product(path, digest, name)
                except Exception as exc:  # Reported without environment values or secrets.
                    budget.release(reservation)
                    counts["failed"] += 1
                    print(f"  failed {path.stem}: {type(exc).__name__}: {str(exc)[:160]}")
                    return
                budget.settle(reservation, name, tokens_in, tokens_out)
                entries[path.stem] = entry
                counts["described"] += 1
                if counts["described"] % CHECKPOINT_EVERY == 0:
                    write_catalogue(list(entries.values()))
                    print(f"  {counts['described']}/{len(pending)} described, ${budget.spent:.2f} spent")

        await asyncio.gather(*(worker(path, digest) for path, digest in pending))

    final = list(entries.values())
    write_catalogue(final)
    build_database(final)
    return final, budget, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, help="Only process the first N photos.")
    parser.add_argument("--force", action="store_true", help="Ignore cached entries.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument(
        "--max-usd",
        type=Decimal,
        default=MAX_LOOP_USD,
        help=f"Stop starting new photos once this much is spent (default {MAX_LOOP_USD}).",
    )
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    started = time.perf_counter()
    entries, budget, counts = asyncio.run(
        build(args.limit, args.force, max(1, args.concurrency), args.max_usd)
    )
    elapsed = time.perf_counter() - started

    print(f"Catalogue: {len(entries)} of {counts['photos']} photos in {elapsed:.1f}s")
    print(f"  reused from cache: {counts['reused']}   described now: {counts['described']}"
          f"   failed: {counts['failed']}")
    print(f"  model: {catalogue_model_name()}   tokens in/out: {budget.input_tokens}/{budget.output_tokens}"
          f"   cost: ${budget.spent:.4f} of ${budget.cap} cap")
    if budget.unpriced_calls:
        print(f"  WARNING: {budget.unpriced_calls} calls could not be priced for this model.")
    if budget.skipped:
        print(f"  STOPPED AT BUDGET: {len(budget.skipped)} photos not described. "
              "Run again to continue from the cache.")
    print(f"  wrote {CATALOGUE_JSON_PATH.relative_to(PROJECT_DIR)} and "
          f"{CATALOGUE_DB_PATH.relative_to(PROJECT_DIR)}")
    for facet, values in facet_counts().items():
        print(f"  {facet}: " + ", ".join(f"{value} {count}" for value, count in values.items()))


if __name__ == "__main__":
    main()
