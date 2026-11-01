"""Tools the Campus Customs agent can call, plus the helpers that support them."""

from __future__ import annotations

import base64
import hashlib
import html
import io
import math
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from pydantic import TypeAdapter
from pydantic_ai import BinaryContent, ModelRetry, RunContext, Tool, ToolReturn
from pydantic_ai.tools import ToolDefinition

from catalogue_db import find_candidates, get_entries
from config import DATA_DIR, OUTPUT_DIR, PROFILES_DIR, PROJECT_DIR, inside_sandbox
from models import (
    AdEffectivenessResult,
    AdProductMatch,
    AffiliationType,
    AgentStep,
    AuditEntry,
    Cart,
    CartItem,
    CatalogueEntry,
    Closure,
    ColorFamily,
    CustomerProfile,
    DesignPlacement,
    FamilyMember,
    GarmentCategory,
    GarmentType,
    IdentifyResult,
    ProductCard,
    SleeveLength,
    VideoFacts,
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
MAX_PHOTO_BYTES = 15_000_000
MAX_VIDEO_BYTES = 200_000_000
MAX_VIDEO_SECONDS = 180
MAX_PROFILE_BYTES = 20_000
PHOTO_MAX_SIDE = 1024
REFERENCE_MAX_SIDE = 640
SHORTLIST_SIZE = 5
MAX_SEARCHES = 2
MAX_REFERENCE_IMAGES = 3
# One 4 x 3 sheet of 448 px frames: every later request re-sends it, so it is kept to one image.
AD_FRAMES = 12
FRAMES_PER_SHEET = 12
SHEET_COLUMNS = 4
FRAME_WIDTH = 448
CART_PATH = OUTPUT_DIR / "cart.json"
SIDEBAR_PATH = OUTPUT_DIR / "identify_product.html"
AD_FRAMES_DIR = OUTPUT_DIR / "ad_frames"


@dataclass
class AgentDeps:
    """State for one run: the job, what the agent has been shown, and what it has done."""

    image_path: Path | None = None
    task: Literal["identify", "ad"] = "identify"
    video_path: Path | None = None
    profile_path: Path | None = None
    shortlist: dict[str, CatalogueEntry] = field(default_factory=dict)
    viewed: list[str] = field(default_factory=list)
    cart: list[str] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    searches: int = 0
    profile: CustomerProfile | None = None
    video: VideoFacts | None = None
    # Catalogue products already identified in this video on an earlier run, if any.
    known_products: list[AdProductMatch] | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- image helpers ---------------------------------------------------------


def resolve_photo(raw: str) -> Path:
    """Accept only an image file inside the project's data folder."""

    path = Path(raw)
    path = inside_sandbox(path if path.is_absolute() else PROJECT_DIR / path, DATA_DIR)
    if not path.is_file():
        raise FileNotFoundError(f"No such image: {raw}")
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError(f"Not a supported image type: {path.suffix}")
    if path.stat().st_size > MAX_PHOTO_BYTES:
        raise ValueError("Image is larger than 15 MB.")
    return path


def jpeg_bytes(path: Path, max_side: int, quality: int = 88) -> bytes:
    """Flatten onto white and cap the size so each image costs a predictable amount."""

    with Image.open(path) as image:
        image = image.convert("RGBA")
        flattened = Image.new("RGB", image.size, "white")
        flattened.paste(image, mask=image.getchannel("A"))
        flattened.thumbnail((max_side, max_side))
        buffer = io.BytesIO()
        flattened.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


def model_image(path: Path, max_side: int) -> BinaryContent:
    return BinaryContent(
        jpeg_bytes(path, max_side), media_type="image/jpeg", vendor_metadata={"detail": "high"}
    )


# --- agent tools -----------------------------------------------------------


def search_catalogue(
    ctx: RunContext[AgentDeps],
    printed_words: list[str],
    garment_category: GarmentCategory | None = None,
    garment_type: GarmentType | None = None,
    sleeve_length: SleeveLength | None = None,
    has_hood: bool | None = None,
    closure: Closure | None = None,
    primary_color: ColorFamily | None = None,
    design_placement: DesignPlacement | None = None,
    affiliation_type: AffiliationType | None = None,
    sport: str | None = None,
    residential_college: str | None = None,
    school: str | None = None,
    family_member: FamilyMember | None = None,
    graphic_words: list[str] | None = None,
) -> list[dict[str, object]] | str:
    """Shortlist catalogue products from the characteristics seen on the garment.

    Searches the catalogue's indexed fields, not its photos. Pass every characteristic
    you can see and omit the rest. Results are ranked by how many characteristics agree,
    so a colour or cut you misjudged lowers a product's rank rather than hiding it.

    Args:
        printed_words: Words legible on the garment, e.g. ["YALE", "DAD"].
        garment_category: tee, sweatshirt, or jacket.
        garment_type: The specific cut, if clear.
        sleeve_length: short, long, or sleeveless.
        has_hood: Whether the garment has a hood.
        closure: pullover, quarter_zip, full_zip, or buttons.
        primary_color: Colour family of the garment body.
        design_placement: Where the design sits on the garment.
        affiliation_type: What kind of Yale affiliation the design names.
        sport: Sport named on the garment, e.g. "soccer".
        residential_college: Yale college named, e.g. "Davenport".
        school: Yale graduate or professional school named.
        family_member: Family member named, e.g. "dad".
        graphic_words: Single words for artwork, e.g. ["bulldog", "shield"].
    """

    deps = ctx.deps
    if deps.searches >= MAX_SEARCHES:
        return "Search limit reached. Decide from the products already shortlisted."
    deps.searches += 1
    facets = {
        "garment_category": garment_category,
        "garment_type": garment_type,
        "sleeve_length": sleeve_length,
        "has_hood": has_hood,
        "closure": closure,
        "primary_color": primary_color,
        "design_placement": design_placement,
        "affiliation_type": affiliation_type,
        "sport": sport,
        "residential_college": residential_college,
        "school": school,
        "family_member": family_member,
    }
    words = re.findall(r"[a-z0-9]+", " ".join([*printed_words, *(graphic_words or [])]).lower())
    ranked = find_candidates(facets, words, limit=SHORTLIST_SIZE)
    seen = {key: value for key, value in facets.items() if value is not None}
    deps.steps.append(
        AgentStep(
            tool="search_catalogue",
            arguments={"words": words, **seen},
            outcome="Shortlisted by catalogue fields: "
            + (", ".join(f"{entry.product_id} (score {score})" for entry, score in ranked) or "nothing"),
        )
    )
    if not ranked:
        return "No catalogue product shares any of these characteristics."
    shortlist = []
    for entry, score in ranked:
        deps.shortlist[entry.product_id] = entry
        shortlist.append(
            {
                "product_id": entry.product_id,
                "score": score,
                "garment_type": entry.garment_type,
                "sleeve_length": entry.sleeve_length,
                "color": entry.color_detail,
                "printed_text": entry.printed_text,
                "graphics": entry.graphic_elements,
                "placement": entry.design_placement,
                "style": entry.design_style,
                "brand": entry.brand,
            }
        )
    return shortlist


def view_catalogue_images(ctx: RunContext[AgentDeps], product_ids: list[str]) -> ToolReturn:
    """Open the catalogue reference photos of shortlisted products to compare with the photo.

    Args:
        product_ids: Up to three product ids taken from the search_catalogue shortlist.
    """

    deps = ctx.deps
    unknown = [pid for pid in product_ids if pid not in deps.shortlist]
    if unknown:
        raise ModelRetry(f"Not in the shortlist: {unknown}. Use ids returned by search_catalogue.")
    wanted = [pid for pid in dict.fromkeys(product_ids) if pid not in deps.viewed]
    room = MAX_REFERENCE_IMAGES - len(deps.viewed)
    showing, refused = wanted[:room], wanted[room:]
    content: list[str | BinaryContent] = []
    for pid in showing:
        deps.viewed.append(pid)
        content.append(f"Catalogue reference photo for {pid}:")
        content.append(model_image(PROJECT_DIR / deps.shortlist[pid].image_file, REFERENCE_MAX_SIDE))
    summary = f"Showing reference photos for: {showing or 'none (already shown)'}."
    if refused:
        summary += f" Reference photo limit of {MAX_REFERENCE_IMAGES} reached; not shown: {refused}."
    deps.steps.append(
        AgentStep(
            tool="view_catalogue_images",
            arguments={"product_ids": product_ids},
            outcome=f"Opened {len(showing)} catalogue reference photo(s) to compare: "
            + (", ".join(showing) or "none"),
        )
    )
    return ToolReturn(return_value=summary, content=content)


def add_to_cart(ctx: RunContext[AgentDeps], product_id: str) -> str:
    """Put a confirmed product in the shopping cart. This does not buy anything.

    Args:
        product_id: The product whose reference photo you compared and confirmed.
    """

    deps = ctx.deps
    if product_id not in deps.viewed:
        raise ModelRetry(
            "Compare the product's reference photo with view_catalogue_images before adding it."
        )
    if product_id not in deps.cart:
        deps.cart.append(product_id)
    deps.steps.append(
        AgentStep(
            tool="add_to_cart",
            arguments={"product_id": product_id},
            outcome="Added to the shopping cart. No purchase was made.",
        )
    )
    return f"{product_id} is in the cart. Checkout is not available to the agent."


# --- ad effectiveness: video and profile -----------------------------------


def resolve_video(raw: str) -> Path:
    """Accept only a video file inside the project's data folder."""

    path = Path(raw)
    path = inside_sandbox(path if path.is_absolute() else PROJECT_DIR / path, DATA_DIR)
    if not path.is_file():
        raise FileNotFoundError(f"No such video: {raw}")
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"Not a supported video type: {path.suffix}")
    if path.stat().st_size > MAX_VIDEO_BYTES:
        raise ValueError("Video is larger than 200 MB.")
    return path


def resolve_profile(raw: str) -> Path:
    """Accept only a JSON file inside the project's profiles folder."""

    path = Path(raw)
    path = inside_sandbox(path if path.is_absolute() else PROJECT_DIR / path, PROFILES_DIR)
    if not path.is_file():
        raise FileNotFoundError(f"No such profile: {raw}")
    if path.suffix.lower() != ".json":
        raise ValueError("The customer profile must be a .json file.")
    if path.stat().st_size > MAX_PROFILE_BYTES:
        raise ValueError("Profile file is larger than 20 KB.")
    return path


def load_profile(path: Path) -> CustomerProfile:
    return CustomerProfile.model_validate_json(path.read_text(encoding="utf-8"))


def probe_video(path: Path) -> tuple[float, bool]:
    """Duration in seconds and whether there is an audio track, read from ffmpeg's header dump."""

    header = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        errors="replace",
    ).stderr
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", header)
    if not match:
        raise ValueError("Could not read the video's duration.")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds), "Audio:" in header


def grab_frame(path: Path, second: float) -> Image.Image:
    """One frame at the given time, scaled down."""

    frame = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error",
            "-ss", f"{second:.3f}", "-i", str(path), "-frames:v", "1",
            "-vf", f"scale={FRAME_WIDTH}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    return Image.open(io.BytesIO(frame)).convert("RGB")


def contact_sheet(frames: list[tuple[float, Image.Image]]) -> Image.Image:
    """Tile frames in time order, each stamped with its timestamp."""

    width, height = frames[0][1].size
    rows = -(-len(frames) // SHEET_COLUMNS)
    sheet = Image.new("RGB", (width * SHEET_COLUMNS, height * rows), "black")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    for index, (second, frame) in enumerate(frames):
        x, y = (index % SHEET_COLUMNS) * width, (index // SHEET_COLUMNS) * height
        sheet.paste(frame, (x, y))
        label = f"{second:.1f}s"
        draw.rectangle([x, y, x + draw.textlength(label, font=font) + 12, y + 32], fill="black")
        draw.text((x + 6, y + 3), label, fill="white", font=font)
    return sheet


def read_customer_profile(ctx: RunContext[AgentDeps]) -> dict[str, object]:
    """Read the customer profile the ad is being judged against."""

    deps = ctx.deps
    deps.profile = load_profile(deps.profile_path)
    deps.steps.append(
        AgentStep(
            tool="read_customer_profile",
            arguments={},
            outcome=f"Read profile '{deps.profile.profile_id}': {deps.profile.label}.",
        )
    )
    return deps.profile.model_dump(exclude_none=True)


def watch_ad_video(ctx: RunContext[AgentDeps]) -> ToolReturn:
    """Watch the ad: returns frames sampled evenly through the video, each stamped with its time.

    The frames come as a contact sheet read left to right, top to bottom. Audio is not included.
    """

    deps = ctx.deps
    if deps.video is not None:
        return ToolReturn(return_value="The ad's frames were already shown above.", content=[])
    duration, has_audio = probe_video(deps.video_path)
    if duration > MAX_VIDEO_SECONDS:
        raise ValueError(f"Video is longer than {MAX_VIDEO_SECONDS} seconds.")
    seconds = [round(duration * (index + 0.5) / AD_FRAMES, 2) for index in range(AD_FRAMES)]
    frames = [(second, grab_frame(deps.video_path, second)) for second in seconds]
    AD_FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    content: list[str | BinaryContent] = []
    sheets: list[str] = []
    for number, start in enumerate(range(0, AD_FRAMES, FRAMES_PER_SHEET), start=1):
        group = frames[start : start + FRAMES_PER_SHEET]
        sheet_path = inside_sandbox(
            AD_FRAMES_DIR / f"{deps.video_path.stem}_sheet{number}.jpg", OUTPUT_DIR
        )
        contact_sheet(group).save(sheet_path, format="JPEG", quality=85)
        sheets.append(sheet_path.relative_to(PROJECT_DIR).as_posix())
        content.append(f"Frames {group[0][0]:.1f}s to {group[-1][0]:.1f}s:")
        content.append(
            BinaryContent(
                sheet_path.read_bytes(), media_type="image/jpeg", vendor_metadata={"detail": "high"}
            )
        )
    deps.video = VideoFacts(
        duration_seconds=round(duration, 2),
        has_audio=has_audio,
        audio_assessed=False,
        frames_sampled=AD_FRAMES,
        frame_timestamps_seconds=seconds,
        frame_sheets=sheets,
    )
    deps.steps.append(
        AgentStep(
            tool="watch_ad_video",
            arguments={},
            outcome=f"Viewed {AD_FRAMES} frames sampled across {duration:.1f} seconds. "
            "Audio could not be assessed.",
        )
    )
    audio = (
        "It has an audio track, but you cannot hear it; do not guess at music or speech."
        if has_audio
        else "It has no audio track."
    )
    return ToolReturn(
        return_value=f"The ad is {duration:.1f} seconds long. {audio} "
        f"{AD_FRAMES} frames follow, stamped with their times.",
        content=content,
    )


# --- which tools each job can see ------------------------------------------


def _only_for(task: str):
    async def prepare(ctx: RunContext[AgentDeps], tool: ToolDefinition) -> ToolDefinition | None:
        return tool if ctx.deps.task == task else None

    return prepare


async def _unless_products_known(
    ctx: RunContext[AgentDeps], tool: ToolDefinition
) -> ToolDefinition | None:
    return None if ctx.deps.known_products is not None else tool


AD_PRODUCTS_CACHE_PATH = OUTPUT_DIR / "ad_products.json"
_AD_PRODUCTS = TypeAdapter(dict[str, list[AdProductMatch]])


def video_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_known_products(video: Path) -> list[AdProductMatch] | None:
    """Products identified in this exact video on an earlier run; None if never identified."""

    if not AD_PRODUCTS_CACHE_PATH.is_file():
        return None
    cache = _AD_PRODUCTS.validate_json(AD_PRODUCTS_CACHE_PATH.read_text(encoding="utf-8"))
    return cache.get(video_fingerprint(video))


def save_known_products(video: Path, products: list[AdProductMatch]) -> None:
    cache = (
        _AD_PRODUCTS.validate_json(AD_PRODUCTS_CACHE_PATH.read_text(encoding="utf-8"))
        if AD_PRODUCTS_CACHE_PATH.is_file()
        else {}
    )
    cache[video_fingerprint(video)] = products
    write_text(AD_PRODUCTS_CACHE_PATH, _AD_PRODUCTS.dump_json(cache, indent=2).decode() + "\n")


# The catalogue search and reference photos serve both jobs: the ad job also identifies
# catalogue products on screen, at the user's request. In the ad job the cart is filled by
# code from the confirmed matches, which saves a model request, so add_to_cart is hidden.
# Which products are in a video does not depend on the customer, so once a video's products
# are known the catalogue tools are hidden and later profiles reuse the answer.
AGENT_TOOLS = [
    Tool(search_catalogue, prepare=_unless_products_known),
    Tool(view_catalogue_images, prepare=_unless_products_known),
    Tool(add_to_cart, prepare=_only_for("identify")),
    Tool(read_customer_profile, prepare=_only_for("ad")),
    Tool(watch_ad_video, prepare=_only_for("ad")),
]


# --- cart and sidebar ------------------------------------------------------


def product_card(entry: CatalogueEntry) -> ProductCard:
    return ProductCard(**entry.model_dump(include=set(ProductCard.model_fields)))


def build_cart(entries: list[CatalogueEntry]) -> Cart:
    return Cart(
        items=[
            CartItem(product_id=e.product_id, name=e.name, image_file=e.image_file)
            for e in entries
        ]
    )


def write_text(path: Path, text: str) -> None:
    path = inside_sandbox(path, OUTPUT_DIR)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def data_uri(path: Path, max_side: int) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes(path, max_side, 80)).decode()


def card_html(card: ProductCard, badge: str, note: str = "") -> str:
    e = html.escape
    return (
        '<article class="card">'
        f'<img src="{data_uri(PROJECT_DIR / card.image_file, 420)}" alt="{e(card.name)}">'
        f'<span class="badge">{e(badge)}</span>'
        f"<h3>{e(card.name)}</h3>"
        f'<p class="meta">{e(card.brand)} &middot; {e(card.color_detail)}</p>'
        f"<p>{e(card.description)}</p>"
        + (f'<p class="note">{e(note)}</p>' if note else "")
        + f'<p class="id">{e(card.product_id)}</p></article>'
    )


SIDEBAR_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs product check</title>
<style>
  :root { --desk:#1b1410; --leather:#2a1d16; --oak:#3b2a1e; --brass:#c9a227; --glass:#4fa97c;
          --cream:#f5e6c8; --muted:#b9ad93; --rule:#5a4330; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--desk); color:var(--cream); font:16px/1.55 Georgia, serif; }
  .layout { display:grid; grid-template-columns:minmax(0,1fr) 360px; min-height:100vh; }
  main { padding:28px 24px; }
  aside { background:var(--leather); border-left:2px solid var(--brass); padding:24px 20px; }
  h1 { margin:0 0 4px; color:var(--brass); font-size:26px; }
  h2 { margin:0 0 12px; color:var(--glass); font-size:14px; letter-spacing:1.2px; text-transform:uppercase; }
  h3 { margin:10px 0 2px; font-size:18px; }
  .photo { width:100%; max-width:720px; border:1px solid var(--rule); border-radius:6px; display:block; margin:16px 0; }
  .verdict { display:inline-block; padding:4px 14px; border-radius:14px; border:1px solid var(--brass);
             color:var(--brass); font-size:15px; letter-spacing:.6px; text-transform:uppercase; }
  .verdict.match { background:var(--glass); color:#10231a; border-color:var(--glass); }
  ul { padding-left:20px; } li { margin-bottom:6px; }
  .question { border-left:3px solid var(--brass); padding:8px 14px; background:var(--leather); }
  .card { background:var(--oak); border:1px solid var(--rule); border-radius:6px; padding:14px; margin-bottom:16px; }
  .card img { width:100%; background:#fff; border-radius:4px; display:block; }
  .badge { display:inline-block; margin-top:10px; padding:1px 10px; border-radius:10px; font-size:12px;
           letter-spacing:.8px; text-transform:uppercase; background:var(--glass); color:#10231a; }
  .meta, .note, .muted { color:var(--muted); font-size:14px; margin:2px 0 8px; }
  .id { font:12px Consolas, monospace; color:var(--muted); margin:8px 0 0; }
  .cart li { list-style:none; margin:0 0 8px; padding:8px 10px; border:1px solid var(--rule); border-radius:4px; }
  .cart ul { padding:0; margin:0 0 12px; }
  button { width:100%; padding:11px; font:inherit; border-radius:4px; border:1px solid var(--rule);
           background:#2c2420; color:var(--muted); cursor:not-allowed; }
  @media (max-width:820px) { .layout { grid-template-columns:1fr; }
    aside { border-left:0; border-top:2px solid var(--brass); } }
</style></head>
<body><div class="layout">
<main>
  <h1>Campus Customs product check</h1>
  <p class="muted">__IMAGE_PATH__ &middot; checked __CHECKED__ &middot; __MODEL__</p>
  <span class="verdict __VERDICT_CLASS__">__VERDICT__</span>
  <span class="muted">&nbsp;confidence: __CONFIDENCE__</span>
  <img class="photo" src="__PHOTO__" alt="Submitted photo">
  __OBSERVED__
  <h2>Why</h2><ul>__REASONS__</ul>
  __QUESTION__
</main>
<aside aria-label="Products and shopping cart">
  <h2>__SIDEBAR_TITLE__</h2>
  __CARDS__
  <section class="cart">
    <h2>Shopping cart (__CART_COUNT__)</h2>
    __CART__
    <button type="button" disabled aria-disabled="true">Checkout unavailable</button>
    <p class="note">__CART_NOTE__</p>
  </section>
</aside>
</div></body></html>
"""


def render_sidebar(result: IdentifyResult, path: Path = SIDEBAR_PATH) -> Path:
    """Write the page that shows the photo with the product pulled up beside it."""

    e = html.escape
    if result.matched_product:
        title = "Matched product"
        cards = card_html(result.matched_product, "In your cart")
    elif result.candidate_products:
        title = "Possible matches"
        notes = {c.product_id: c.differences for c in result.candidates}
        in_cart = {item.product_id for item in result.cart.items}
        cards = "".join(
            card_html(
                card,
                "In your cart" if card.product_id in in_cart else "Possible match",
                notes.get(card.product_id, ""),
            )
            for card in result.candidate_products
        )
    else:
        title = "No catalogue product"
        cards = '<p class="muted">Item is not carried by Campus Customs.</p>'
    cart = (
        "<ul>"
        + "".join(
            f"<li>{e(item.name)}<div class='muted'>Qty {item.quantity} &middot; size not chosen "
            "&middot; price shown at checkout</div></li>"
            for item in result.cart.items
        )
        + "</ul>"
        if result.cart.items
        else '<p class="muted">The cart is empty.</p>'
    )
    observed = (
        f"<h2>Garment seen</h2><p>{e(result.observed_garment.description)}</p>"
        if result.observed_garment
        else ""
    )
    question = (
        f'<p class="question">{e(result.question_for_user)}</p>' if result.question_for_user else ""
    )
    page = SIDEBAR_PAGE
    for key, value in {
        "__IMAGE_PATH__": e(result.image_path),
        "__CHECKED__": e(result.checked_at_utc),
        "__MODEL__": e(result.model),
        "__VERDICT_CLASS__": "match" if result.verdict == "match" else "",
        "__VERDICT__": e(result.verdict.replace("_", " ")),
        "__CONFIDENCE__": e(result.confidence),
        "__PHOTO__": data_uri(PROJECT_DIR / result.image_path, 900),
        "__OBSERVED__": observed,
        "__REASONS__": "".join(f"<li>{e(reason)}</li>" for reason in result.reasons),
        "__QUESTION__": question,
        "__SIDEBAR_TITLE__": title,
        "__CARDS__": cards,
        "__CART_COUNT__": str(len(result.cart.items)),
        "__CART__": cart,
        "__CART_NOTE__": e(result.cart.note),
    }.items():
        page = page.replace(key, value)
    write_text(path, page)
    return path


AD_PAGE_PATH = OUTPUT_DIR / "ad_effectiveness.html"
PAGE_STYLE = SIDEBAR_PAGE.split("<style>")[1].split("</style>")[0] + """
  h2 { margin-top:22px; }
  aside h2 { margin-top:0; }
  .sheet { width:100%; border:1px solid var(--rule); border-radius:6px; display:block; margin:10px 0; }
  .score { font-size:34px; color:var(--brass); margin-right:10px; }
  .helps { color:var(--glass); } .hurts { color:#ff8a80; }
  .none { padding:16px; border:1px dashed var(--brass); border-radius:6px; color:var(--brass); margin-bottom:16px; }
  .meters { display:flex; flex-wrap:wrap; gap:18px; margin:14px 0 4px; }
  .meter { width:300px; max-width:100%; margin:0; }
  .meter svg { width:100%; height:auto; display:block; }
  .meter figcaption { margin-top:6px; color:var(--muted); font-size:14px; }
"""

# The four colour bands on the dial, from 0 (red) to 10 (green).
METER_BANDS = [(0, 2.5, "#c0392b"), (2.5, 5, "#e67e22"), (5, 7.5, "#f1c40f"), (7.5, 10, "#2e9e5b")]


def meter_svg(label: str, score: int) -> str:
    """An analog needle meter, 0 at the left in red to 10 at the right in green."""

    cx, cy, radius = 150.0, 150.0, 104.0

    def point(value: float, r: float) -> tuple[float, float]:
        angle = math.radians(180 - 18 * value)  # 0 points left, 10 points right
        return cx + r * math.cos(angle), cy - r * math.sin(angle)

    bands = ""
    for start, end, colour in METER_BANDS:
        (x1, y1), (x2, y2) = point(start, radius), point(end, radius)
        bands += (
            f'<path d="M{x1:.1f} {y1:.1f} A{radius} {radius} 0 0 1 {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{colour}" stroke-width="16"/>'
        )
    ticks = ""
    for value in range(11):
        (x1, y1), (x2, y2) = point(value, radius - 12), point(value, radius - 22)
        tx, ty = point(value, radius - 36)
        ticks += (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#2a1d16" stroke-width="2"/>'
            f'<text x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="bold" fill="#2a1d16">{value}</text>'
        )
    nx, ny = point(score, radius - 8)
    name = html.escape(label)
    return (
        f'<figure class="meter"><svg viewBox="0 0 300 190" role="img" '
        f'aria-label="{name}: {score} out of 10">'
        '<rect x="2" y="2" width="296" height="186" rx="12" fill="#f3e6c4" stroke="#c9a227" stroke-width="4"/>'
        f"{bands}"
        f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1b1410" stroke-width="3.5" stroke-linecap="round"/>'
        f'<g paint-order="stroke" stroke="#f3e6c4" stroke-width="3">{ticks}</g>'
        f'<circle cx="{cx}" cy="{cy}" r="9" fill="#1b1410"/><circle cx="{cx}" cy="{cy}" r="3.5" fill="#c9a227"/>'
        f'<text x="{cx}" y="178" text-anchor="middle" font-size="13" letter-spacing="1.5" fill="#2a1d16">'
        f"{name.upper()}</text></svg>"
        f"<figcaption>{name}: <strong>{score} / 10</strong></figcaption></figure>"
    )


def render_ad_page(result: "AdEffectivenessResult", path: Path = AD_PAGE_PATH) -> Path:
    """Write the page that shows the ad judgement with any identified products beside it."""

    e = html.escape
    in_cart = {item.product_id for item in result.cart.items}
    notes = {match.product_id: match for match in result.catalogue_products}
    cards = "".join(
        card_html(
            card,
            "In your cart" if card.product_id in in_cart else "Possible match",
            f"Seen at {notes[card.product_id].seen_at_seconds:.1f}s. {notes[card.product_id].reason}",
        )
        for card in result.identified_products
    ) or '<p class="none">Item is not carried by Campus Customs</p>'
    cart = (
        "<ul>"
        + "".join(
            f"<li>{e(item.name)}<div class='muted'>Qty {item.quantity} &middot; size not chosen "
            "&middot; price shown at checkout</div></li>"
            for item in result.cart.items
        )
        + "</ul>"
        if result.cart.items
        else '<p class="muted">The cart is empty.</p>'
    )
    sheets = "".join(
        f'<img class="sheet" src="{data_uri(PROJECT_DIR / sheet, 1536)}" alt="Frames from the ad, sheet {n}">'
        for n, sheet in enumerate(result.video.frame_sheets, start=1)
    )
    fit = "".join(
        f'<li><strong class="{e(item.effect)}">{e(item.effect.capitalize())}:</strong> '
        f"{e(item.profile_trait)} <span class='muted'>&mdash; {e(item.ad_element)}</span></li>"
        for item in result.profile_fit
    )

    def bullets(items: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"

    body = f"""<div class="layout"><main>
  <h1>Campus Customs ad check</h1>
  <p class="muted">{e(result.video_path)} &middot; for: {e(result.profile.label)} &middot;
     {e(result.checked_at_utc)} &middot; {e(result.model)}</p>
  <div class="meters">{meter_svg("Appropriateness", result.appropriateness_score)}
     {meter_svg("Effectiveness", result.effectiveness_score)}</div>
  <p><span class="verdict {'match' if result.verdict == 'effective' else ''}">{e(result.verdict)}</span>
     <span class="muted">&nbsp;confidence: {e(result.confidence)}</span></p>
  <h2>Appropriateness for this customer</h2>{bullets(result.appropriateness_reasons)}
  <h2>What the agent saw ({result.video.frames_sampled} frames, no audio)</h2>{sheets}
  <p>{e(result.ad_summary)}</p>
  <h2>Key moments</h2>{bullets([f"{m.timestamp_seconds:.1f}s: {m.observation}" for m in result.key_moments])}
  <h2>Fit with this customer</h2><ul>{fit}</ul>
  <h2>Recommendations</h2>{bullets(result.recommendations)}
  <h2>Limitations</h2>{bullets(result.limitations)}
</main>
<aside aria-label="Products and shopping cart">
  <h2>Catalogue products in the ad</h2>{cards}
  <section class="cart"><h2>Shopping cart ({len(result.cart.items)})</h2>{cart}
    <button type="button" disabled aria-disabled="true">Checkout unavailable</button>
    <p class="note">{e(result.cart.note)}</p></section>
</aside></div>"""
    write_text(
        path,
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Campus Customs ad check</title><style>{PAGE_STYLE}</style></head>"
        f"<body>{body}</body></html>",
    )
    return path


# --- audit trail -----------------------------------------------------------

AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
_AUDIT = TypeAdapter(list[AuditEntry])


def load_audit(path: Path = AUDIT_PATH) -> list[AuditEntry]:
    if not path.is_file():
        return []
    return _AUDIT.validate_json(path.read_text(encoding="utf-8"))


def append_audit(entry: AuditEntry, path: Path = AUDIT_PATH) -> None:
    """Add one entry to the audit trail. Earlier entries are never removed or changed.

    The file is a JSON list, so it is rewritten with the new entry at the end and swapped
    into place in one step; an interrupted write cannot leave it half-written.
    """

    write_text(path, _AUDIT.dump_json([*load_audit(path), entry], indent=2).decode() + "\n")
