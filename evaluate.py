"""Run the agent on every photo in data/test_images and score it against the file names.

The label ("true" or "false" in the file name) is read here, after the agent has answered.
The agent itself is only ever given the image pixels.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from pydantic_ai.exceptions import UsageLimitExceeded

from agent import identify_product, save
from config import DATA_DIR, OUTPUT_DIR, PROJECT_DIR, model_name
from models import EvaluationReport, EvaluationRow, IdentifyResult
from tools import IMAGE_SUFFIXES, now_iso, write_text

TEST_IMAGES_DIR = DATA_DIR / "test_images"
EVALUATION_PATH = OUTPUT_DIR / "identify_evaluation.json"


def expected_label(path: Path) -> bool:
    name = path.stem.lower()
    if ("true" in name) == ("false" in name):
        raise ValueError(f"File name must contain exactly one of 'true' or 'false': {path.name}")
    return "true" in name


def score(result: IdentifyResult) -> EvaluationRow:
    expected = expected_label(Path(result.image_path))
    # A "possibly" still flags a catalogue product for a person to confirm, so it counts as a yes.
    said_yes = result.campus_customs_product_in_photo != "no"
    return EvaluationRow(
        image_path=result.image_path,
        expected_product_in_photo=expected,
        agent_answer=result.campus_customs_product_in_photo,
        agent_verdict=result.verdict,
        agent_product_id=result.matched_product_id,
        agent_candidate_ids=[candidate.product_id for candidate in result.candidates],
        confidence=result.confidence,
        correct=said_yes == expected,
        cost_usd=result.cost.cost_usd,
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    photos = sorted(p for p in TEST_IMAGES_DIR.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    results: list[IdentifyResult] = []
    for photo in photos:
        try:
            results.append(identify_product(str(photo)))
        except UsageLimitExceeded as exc:
            print(f"{photo.name}: stopped at the usage limit ({exc})", file=sys.stderr)
            return 1
        print(f"checked {photo.name}")
    save(results)

    rows = [score(result) for result in results]
    report = EvaluationReport(
        model=model_name(),
        run_at_utc=now_iso(),
        correct=sum(row.correct for row in rows),
        total=len(rows),
        total_cost_usd=f"{sum(Decimal(row.cost_usd or '0') for row in rows):.4f}",
        rows=rows,
    )
    write_text(EVALUATION_PATH, report.model_dump_json(indent=2) + "\n")

    print(f"\n{'photo':<24}{'actual':<8}{'agent':<10}{'verdict':<16}{'result':<8}product")
    for row in rows:
        product = row.agent_product_id or ", ".join(row.agent_candidate_ids) or "-"
        print(
            f"{Path(row.image_path).name:<24}"
            f"{'yes' if row.expected_product_in_photo else 'no':<8}"
            f"{row.agent_answer:<10}{row.agent_verdict:<16}"
            f"{'correct' if row.correct else 'WRONG':<8}{product}"
        )
    print(f"\n{report.correct} of {report.total} correct   total cost ${report.total_cost_usd}")
    print(f"Saved {EVALUATION_PATH.relative_to(PROJECT_DIR)} and output/identify_product.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
