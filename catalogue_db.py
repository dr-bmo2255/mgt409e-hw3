"""SQLite index over the catalogue so matching never has to open every product photo."""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from config import CATALOGUE_DB_PATH
from models import CatalogueEntry

# Indexed columns and how much a match on each one counts when ranking candidates.
# Printed affiliation is the strongest signal; colour is the weakest because lighting
# and heathered fabrics make it the easiest thing to misjudge in a street photo.
FACET_WEIGHTS: dict[str, int] = {
    "garment_category": 2,
    "garment_type": 2,
    "sleeve_length": 1,
    "has_hood": 1,
    "closure": 1,
    "primary_color": 1,
    "design_placement": 1,
    "affiliation_type": 2,
    "sport": 4,
    "residential_college": 4,
    "school": 4,
    "family_member": 4,
    "event": 3,
    "brand": 2,
}
TERM_WEIGHT = 2

SCHEMA = f"""
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    {", ".join(f"{column} TEXT" for column in FACET_WEIGHTS)},
    entry_json TEXT NOT NULL
);
CREATE TABLE product_terms (
    product_id TEXT NOT NULL REFERENCES products(product_id),
    term TEXT NOT NULL,
    PRIMARY KEY (term, product_id)
);
{"".join(f"CREATE INDEX idx_{column} ON products({column});" for column in FACET_WEIGHTS)}
"""


def _facet_value(value: object) -> str | None:
    """Store every facet as lower-case text so lookups are case-insensitive."""

    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value).strip().lower() or None


def build_database(entries: list[CatalogueEntry], path: Path = CATALOGUE_DB_PATH) -> Path:
    """Rebuild the index from scratch; it is derived data and cheap to recreate."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript(SCHEMA)
        columns = ["product_id", "name", *FACET_WEIGHTS, "entry_json"]
        connection.executemany(
            f"INSERT INTO products ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
            [
                (
                    entry.product_id,
                    entry.name,
                    *(_facet_value(getattr(entry, column)) for column in FACET_WEIGHTS),
                    entry.model_dump_json(),
                )
                for entry in entries
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO product_terms (product_id, term) VALUES (?, ?)",
            [(entry.product_id, term) for entry in entries for term in entry.search_terms],
        )
        connection.commit()
    finally:
        connection.close()
    temporary.replace(path)
    return path


def facet_counts(path: Path = CATALOGUE_DB_PATH) -> dict[str, dict[str, int]]:
    """How many products fall under each value of each facet."""

    connection = sqlite3.connect(path)
    try:
        return {
            column: {
                str(value): count
                for value, count in connection.execute(
                    f"SELECT {column}, COUNT(*) FROM products WHERE {column} IS NOT NULL "
                    f"GROUP BY {column} ORDER BY COUNT(*) DESC, {column}"
                )
            }
            for column in FACET_WEIGHTS
        }
    finally:
        connection.close()


def get_entries(product_ids: list[str], path: Path = CATALOGUE_DB_PATH) -> list[CatalogueEntry]:
    """Fetch catalogue entries by id, in the order asked; unknown ids are skipped."""

    connection = sqlite3.connect(path)
    try:
        rows = [
            connection.execute(
                "SELECT entry_json FROM products WHERE product_id = ?", (product_id,)
            ).fetchone()
            for product_id in product_ids
        ]
    finally:
        connection.close()
    return [CatalogueEntry.model_validate_json(row[0]) for row in rows if row]


def find_candidates(
    facets: dict[str, object] | None = None,
    terms: list[str] | None = None,
    limit: int = 6,
    path: Path = CATALOGUE_DB_PATH,
) -> list[tuple[CatalogueEntry, int]]:
    """Rank products by how many observed characteristics they share.

    Scoring is additive rather than a hard filter, so one misjudged characteristic
    (a navy shirt that photographs as black) lowers a product's rank instead of
    removing the right answer.
    """

    scores: Counter[str] = Counter()
    connection = sqlite3.connect(path)
    try:
        for column, value in (facets or {}).items():
            if column not in FACET_WEIGHTS:
                raise ValueError(f"Unknown catalogue facet: {column}")
            wanted = _facet_value(value)
            if wanted is None:
                continue
            for (product_id,) in connection.execute(
                f"SELECT product_id FROM products WHERE {column} = ?", (wanted,)
            ):
                scores[product_id] += FACET_WEIGHTS[column]
        for term in {term.strip().lower() for term in terms or [] if term.strip()}:
            for (product_id,) in connection.execute(
                "SELECT product_id FROM product_terms WHERE term = ?", (term,)
            ):
                scores[product_id] += TERM_WEIGHT
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
        results = []
        for product_id, score in ranked:
            (entry_json,) = connection.execute(
                "SELECT entry_json FROM products WHERE product_id = ?", (product_id,)
            ).fetchone()
            results.append((CatalogueEntry.model_validate_json(entry_json), score))
        return results
    finally:
        connection.close()
