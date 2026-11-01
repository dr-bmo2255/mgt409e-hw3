"""Offline tests for the catalogue models, index, and budget. No model calls."""

from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from build_catalogue import Budget, make_entry, search_terms
from catalogue_db import build_database, facet_counts, find_candidates
from config import PROJECT_DIR, inside_sandbox
from models import ProductVisualFields


def fields(**overrides: object) -> ProductVisualFields:
    base: dict[str, object] = {
        "name": "Yale Dad T-Shirt",
        "description": "Gray tee with YALE DAD across the chest.",
        "garment_type": "t_shirt",
        "sleeve_length": "short",
        "has_hood": False,
        "closure": "pullover",
        "primary_color": "gray",
        "color_detail": "heather gray",
        "secondary_colors": [],
        "print_colors": ["navy"],
        "printed_text": ["YALE", "UNIVERSITY", "DAD"],
        "graphic_elements": [],
        "design_placement": "center_chest",
        "design_style": "block serif between rules",
        "affiliation_type": "family",
        "sport": None,
        "residential_college": None,
        "school": None,
        "family_member": "dad",
        "event": None,
        "brand": None,
        "distinguishing_features": [],
    }
    return ProductVisualFields(**{**base, **overrides})


def entry(product_id: str, **overrides: object):
    path = PROJECT_DIR / "data" / "products" / f"{product_id}.jpg"
    return make_entry(path, "0" * 64, fields(**overrides), "test-model")


class CatalogueTests(unittest.TestCase):
    def test_category_is_derived_from_garment_type(self) -> None:
        self.assertEqual(entry("yale-dad-t-shirt").garment_category, "tee")
        hoodie = entry("yale-dad-hoodie", garment_type="hoodie", sleeve_length="long")
        self.assertEqual(hoodie.garment_category, "sweatshirt")

    def test_text_fields_are_normalised(self) -> None:
        cleaned = fields(sport="  Ice   Hockey ", brand="Hype & Vice")
        self.assertEqual(cleaned.sport, "ice hockey")
        self.assertEqual(cleaned.brand, "Hype and Vice")
        self.assertEqual(fields(brand=None).brand, "House Brand")
        self.assertEqual(fields(brand="Sportswear").brand, "House Brand")
        self.assertEqual(fields(brand="under armor").brand, "Under Armour")

    def test_search_terms_cover_slug_and_printed_text(self) -> None:
        terms = search_terms("yale-dad-t-shirt", fields())
        self.assertIn("dad", terms)
        self.assertIn("university", terms)
        self.assertNotIn("a", terms)

    def test_index_ranks_the_closest_product_first(self) -> None:
        entries = [
            entry("yale-dad-t-shirt"),
            entry("yale-mom-t-shirt", family_member="mom", printed_text=["YALE", "MOM"]),
            entry(
                "dry-zone-long-sleeve",
                garment_type="long_sleeve_tee",
                sleeve_length="long",
                primary_color="navy",
                affiliation_type="general_yale",
                family_member=None,
                printed_text=["YALE", "BULLDOGS"],
            ),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = build_database(entries, Path(folder) / "catalogue.db")
            self.assertEqual(facet_counts(path)["family_member"], {"dad": 1, "mom": 1})
            ranked = find_candidates(
                {"garment_category": "tee", "sleeve_length": "long", "primary_color": "black"},
                ["bulldogs"],
                path=path,
            )
            self.assertEqual(ranked[0][0].product_id, "dry-zone-long-sleeve")
            with self.assertRaises(ValueError):
                find_candidates({"price": 20}, path=path)

    def test_budget_refuses_work_past_the_cap(self) -> None:
        budget = Budget(cap=Decimal("0.02"))
        first = budget.try_reserve()
        second = budget.try_reserve()
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsNone(budget.try_reserve())

    def test_paths_outside_the_project_are_refused(self) -> None:
        with self.assertRaises(PermissionError):
            inside_sandbox(PROJECT_DIR.parent / ".env")


if __name__ == "__main__":
    unittest.main()
