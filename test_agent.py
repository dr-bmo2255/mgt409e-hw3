"""Offline tests for the agent's tools and answer rules. No model calls."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from pydantic_ai import BinaryContent, ModelRetry

from agent import check_decision, prompt_for
from config import CATALOGUE_DB_PATH, OUTPUT_DIR, PROJECT_DIR
from models import (
    AdJudgement,
    AdMoment,
    AuditEntry,
    CandidateProduct,
    IdentifyDecision,
    ProfileFit,
    RunCost,
)
from tools import (
    MAX_REFERENCE_IMAGES,
    AgentDeps,
    add_to_cart,
    append_audit,
    load_audit,
    load_profile,
    meter_svg,
    read_customer_profile,
    resolve_photo,
    resolve_profile,
    resolve_video,
    search_catalogue,
    view_catalogue_images,
    watch_ad_video,
)

PHOTO = PROJECT_DIR / "data" / "test_images" / "image_03_true.jpeg"
VIDEO = PROJECT_DIR / "data" / "videos" / "ad_humble.mp4"
PROFILE = PROJECT_DIR / "profiles" / "profile_student.json"


def context() -> SimpleNamespace:
    return SimpleNamespace(deps=AgentDeps(image_path=PHOTO))


def decision(**overrides: object) -> IdentifyDecision:
    base: dict[str, object] = {
        "verdict": "no_match",
        "observed_garment": None,
        "matched_product_id": None,
        "possible_match_reason": None,
        "candidates": [],
        "reasons": ["No Yale apparel is visible."],
        "confidence": "high",
        "question_for_user": None,
    }
    return IdentifyDecision(**{**base, **overrides})


@unittest.skipUnless(CATALOGUE_DB_PATH.is_file(), "run build_catalogue.py first")
class ToolTests(unittest.TestCase):
    def test_photo_must_be_an_image_under_data(self) -> None:
        self.assertEqual(resolve_photo("data/test_images/image_03_true.jpeg"), PHOTO)
        with self.assertRaises(PermissionError):
            resolve_photo("output/catalogue.json")
        with self.assertRaises(PermissionError):
            resolve_photo("../.env")
        with self.assertRaises(FileNotFoundError):
            resolve_photo("data/test_images/missing.jpg")

    def test_search_shortlists_by_fields_and_is_capped(self) -> None:
        ctx = context()
        shortlist = search_catalogue(
            ctx, ["YALE", "DAD"], garment_category="tee", primary_color="gray", family_member="dad"
        )
        self.assertEqual(shortlist[0]["product_id"], "yale-dad-t-shirt")
        self.assertLessEqual(len(shortlist), 5)
        search_catalogue(ctx, ["YALE"])
        self.assertIsInstance(search_catalogue(ctx, ["YALE"]), str)

    def test_only_a_few_shortlisted_reference_photos_can_be_opened(self) -> None:
        ctx = context()
        with self.assertRaises(ModelRetry):
            view_catalogue_images(ctx, ["yale-dad-t-shirt"])
        ids = [row["product_id"] for row in search_catalogue(ctx, ["YALE"], garment_category="tee")]
        view_catalogue_images(ctx, ids)
        self.assertEqual(len(ctx.deps.viewed), MAX_REFERENCE_IMAGES)

    def test_cart_accepts_only_a_compared_product(self) -> None:
        ctx = context()
        search_catalogue(ctx, ["YALE", "DAD"], family_member="dad")
        with self.assertRaises(ModelRetry):
            add_to_cart(ctx, "yale-dad-t-shirt")
        view_catalogue_images(ctx, ["yale-dad-t-shirt"])
        add_to_cart(ctx, "yale-dad-t-shirt")
        self.assertEqual(ctx.deps.cart, ["yale-dad-t-shirt"])

    def test_answer_rules(self) -> None:
        ctx = context()
        ctx.deps.viewed = ["dry-zone-long-sleeve", "ua-mens-tech-l-s-2-0"]
        check_decision(ctx, decision())
        check_decision(ctx, decision(verdict="match", matched_product_id="dry-zone-long-sleeve"))
        with self.assertRaises(ModelRetry):  # never compared this product's photo
            check_decision(ctx, decision(verdict="match", matched_product_id="yale-dad-t-shirt"))
        pair = [
            CandidateProduct(product_id=pid, similarities="same wording", differences="logo unclear")
            for pid in ctx.deps.viewed
        ]
        with self.assertRaises(ModelRetry):  # two products need a question for the user
            check_decision(
                ctx,
                decision(
                    verdict="possible_match",
                    possible_match_reason="cannot_distinguish",
                    candidates=pair,
                ),
            )
        check_decision(
            ctx,
            decision(
                verdict="possible_match",
                possible_match_reason="color_variant",
                candidates=pair[:1],
            ),
        )


def ad_judgement(**overrides: object) -> AdJudgement:
    base: dict[str, object] = {
        "ad_summary": "People in Yale hoodies under an overpass.",
        "key_moments": [AdMoment(timestamp_seconds=1.0, observation="Navy YALE hoodie close-up.")],
        "products_shown": ["navy YALE hoodie"],
        "call_to_action_seen": False,
        "effectiveness_score": 6,
        "verdict": "mixed",
        "appropriateness_score": 7,
        "appropriateness_reasons": ["Group casting fits the profile's value of belonging."],
        "profile_fit": [
            ProfileFit(profile_trait="likes hoodies", ad_element="hoodie shown", effect="helps"),
            ProfileFit(profile_trait="needs a price", ad_element="no price", effect="hurts"),
        ],
        "recommendations": ["Add where to buy."],
        "confidence": "medium",
        "limitations": ["Audio not heard."],
    }
    return AdJudgement(**{**base, **overrides})


class AdTests(unittest.TestCase):
    def ad_context(self) -> SimpleNamespace:
        return SimpleNamespace(
            deps=AgentDeps(task="ad", video_path=VIDEO, profile_path=PROFILE)
        )

    def test_profile_must_be_json_under_profiles(self) -> None:
        self.assertEqual(resolve_profile("profiles/profile_student.json"), PROFILE)
        with self.assertRaises(PermissionError):
            resolve_profile("output/identify_product.json")
        with self.assertRaises(PermissionError):
            resolve_video("profiles/profile_student.json")

    def test_tools_read_the_profile_and_sample_the_video(self) -> None:
        ctx = self.ad_context()
        self.assertEqual(read_customer_profile(ctx)["profile_id"], "student")
        shown = watch_ad_video(ctx)
        video = ctx.deps.video
        self.assertEqual(video.frames_sampled, 12)
        self.assertTrue(video.has_audio)
        self.assertFalse(video.audio_assessed)
        self.assertLess(max(video.frame_timestamps_seconds), video.duration_seconds)
        self.assertEqual(sum(isinstance(part, BinaryContent) for part in shown.content), 1)

    def test_both_profiles_match_the_profile_model(self) -> None:
        for name in ("student", "parent"):
            profile = load_profile(resolve_profile(f"profiles/profile_{name}.json"))
            self.assertEqual(profile.profile_id, name)
            self.assertTrue(profile.yale_traditions_valued and profile.yale_modern_values)

    def test_meter_needle_tracks_the_score(self) -> None:
        low, high = meter_svg("Appropriateness", 0), meter_svg("Appropriateness", 10)
        self.assertIn('aria-label="Appropriateness: 0 out of 10"', low)
        self.assertIn('x2="54.0" y2="150.0"', low)  # needle points left at 0
        self.assertIn('x2="246.0" y2="150.0"', high)  # and right at 10

    def test_safety_rules_are_in_every_prompt(self) -> None:
        for prompt in (prompt_for("identify"), prompt_for("ad"), prompt_for("ad", True)):
            self.assertIn("## SAFETY RULES FOR PHOTOS AND VIDEO", prompt)
            self.assertIn("## Limits", prompt)
        self.assertNotIn("## Ability 2", prompt_for("identify"))
        self.assertNotIn("## Ability 1", prompt_for("ad", products_known=True))
        self.assertIn("## Ability 1", prompt_for("ad"))

    def test_audit_entries_are_appended_not_overwritten(self) -> None:
        path = OUTPUT_DIR / "_test_audit_trail.json"
        path.unlink(missing_ok=True)
        entry = AuditEntry(
            run_id="test",
            iteration=1,
            timestamp_utc="2026-01-01T00:00:00Z",
            task="identify",
            subject="data/test_images/example.jpg",
            model="test-model",
            event="stopped",
            thoughts=["The input was refused."],
            usage_so_far=RunCost(
                requests=0, tool_calls=0, input_tokens=0, output_tokens=0, cost_usd="0.0000"
            ),
            stop_reason="input_rejected",
        )
        try:
            for number in (1, 2):
                append_audit(entry.model_copy(update={"iteration": number}), path)
            self.assertEqual([saved.iteration for saved in load_audit(path)], [1, 2])
        finally:
            path.unlink(missing_ok=True)

    def test_judgement_rules(self) -> None:
        ctx = self.ad_context()
        with self.assertRaises(ModelRetry):  # judged without reading the profile or the video
            check_decision(ctx, ad_judgement())
        read_customer_profile(ctx)
        watch_ad_video(ctx)
        check_decision(ctx, ad_judgement())
        with self.assertRaises(ModelRetry):  # score and verdict disagree
            check_decision(ctx, ad_judgement(effectiveness_score=9))
        with self.assertRaises(ModelRetry):  # moment after the ad ends
            check_decision(
                ctx, ad_judgement(key_moments=[AdMoment(timestamp_seconds=99, observation="x")])
            )
        with self.assertRaises(ModelRetry):  # wrong kind of answer for the job
            check_decision(ctx, decision())


if __name__ == "__main__":
    unittest.main()
