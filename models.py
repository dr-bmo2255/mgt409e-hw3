"""Pydantic structured types for the Campus Customs catalogue and agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

GarmentType = Literal[
    "t_shirt",
    "long_sleeve_tee",
    "crewneck_sweatshirt",
    "hoodie",
    "full_zip_hoodie",
    "quarter_zip_pullover",
    "fleece_pullover",
    "jacket",
    "other",
]
GarmentCategory = Literal["tee", "sweatshirt", "jacket", "other"]
SleeveLength = Literal["short", "long", "sleeveless"]
ColorFamily = Literal[
    "navy", "blue", "gray", "black", "white", "cream", "green", "red", "pink", "brown", "other"
]
Closure = Literal["pullover", "quarter_zip", "full_zip", "buttons"]
DesignPlacement = Literal["center_chest", "left_chest", "full_front", "sleeve", "none", "other"]
AffiliationType = Literal[
    "general_yale",
    "sport",
    "residential_college",
    "graduate_or_professional_school",
    "family",
    "event_or_rivalry",
]
FamilyMember = Literal[
    "dad", "mom", "grandma", "grandpa", "aunt", "uncle", "brother", "sister", "cousin"
]

HOUSE_BRAND = "House Brand"
# Recognised garment makers and the spellings they arrive in. Anything else, including
# no maker at all, is Campus Customs' own house brand.
BRAND_NAMES: dict[str, str] = {
    "brooks brothers": "Brooks Brothers",
    "champion": "Champion",
    "district": "District",
    "hype and vice": "Hype and Vice",
    "maple house": "MapleHouse",
    "maplehouse": "MapleHouse",
    "port and company": "Port and Company",
    "russell athletic": "Russell Athletic",
    "sport-tek": "Sport-Tek",
    "sport tek": "Sport-Tek",
    "dry zone": "Sport-Tek",  # Dry Zone is a Sport-Tek line; the neck label reads Sport-Tek.
    "under armour": "Under Armour",
    "under armor": "Under Armour",
}

# The user-facing tee / sweatshirt / jacket split is derived, never asked of the model,
# so garment_type and garment_category can not disagree.
CATEGORY_BY_TYPE: dict[str, GarmentCategory] = {
    "t_shirt": "tee",
    "long_sleeve_tee": "tee",
    "crewneck_sweatshirt": "sweatshirt",
    "hoodie": "sweatshirt",
    "full_zip_hoodie": "sweatshirt",
    "quarter_zip_pullover": "sweatshirt",
    "fleece_pullover": "sweatshirt",
    "jacket": "jacket",
    "other": "other",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


class ProductVisualFields(BaseModel):
    """What the vision model reports after looking at one product photo."""

    name: str = Field(description="Short customer-facing product name, e.g. 'Yale Dad T-Shirt'.")
    description: str = Field(
        description="One or two sentences describing the garment and its design as seen."
    )
    garment_type: GarmentType
    sleeve_length: SleeveLength
    has_hood: bool
    closure: Closure
    primary_color: ColorFamily = Field(description="Colour family of the garment body.")
    color_detail: str = Field(description="Exact shade as seen, e.g. 'heather gray'.")
    secondary_colors: list[str] = Field(
        description="Other garment colours such as contrast sleeves or panels; empty if none."
    )
    print_colors: list[str] = Field(description="Colours of the printed or stitched design.")
    printed_text: list[str] = Field(
        description="Every word or phrase visible on the garment, copied exactly, one per line."
    )
    graphic_elements: list[str] = Field(
        description="Non-text artwork, e.g. 'bulldog', 'shield crest', 'crossed oars'; empty if none."
    )
    design_placement: DesignPlacement
    design_style: str = Field(
        description="Lettering and layout style, e.g. 'arched block serif', 'small embroidered crest'."
    )
    affiliation_type: AffiliationType
    sport: str | None = Field(description="Sport named on the garment, lower case; else null.")
    residential_college: str | None = Field(
        description="Yale residential college named on the garment, e.g. 'Davenport'; else null."
    )
    school: str | None = Field(
        description="Yale graduate or professional school, e.g. 'School of Management'; else null."
    )
    family_member: FamilyMember | None = Field(
        description="Family member the garment is made for, e.g. 'dad'; else null."
    )
    event: str | None = Field(
        description="Specific event, venue or rivalry, e.g. 'Yale vs Harvard 2025'; else null."
    )
    brand: str = Field(
        default=HOUSE_BRAND,
        description=(
            "Garment maker when its name or logo is legible in the photo or named in the "
            "slug, e.g. 'Champion', 'Under Armour', 'Port and Company'; otherwise 'House Brand'."
        ),
    )
    distinguishing_features: list[str] = Field(
        description="Up to three details that separate this item from similar Yale products."
    )

    @field_validator("sport")
    @classmethod
    def _lower_sport(cls, value: str | None) -> str | None:
        value = (_clean(value) or "").lower()
        # Yale's "hockey" merchandise is ice hockey; field hockey is always named in full.
        return "ice hockey" if value == "hockey" else value or None

    @field_validator("residential_college", "school", "event")
    @classmethod
    def _tidy(cls, value: str | None) -> str | None:
        return _clean(value)

    @field_validator("brand", mode="before")
    @classmethod
    def _known_maker_or_house(cls, value: object) -> str:
        key = (_clean(str(value)) if value else None) or ""
        return BRAND_NAMES.get(key.lower().replace("&", "and"), HOUSE_BRAND)


class CatalogueEntry(ProductVisualFields):
    """One product: the model's visual fields plus fields computed in code."""

    product_id: str = Field(description="Filename slug; the stable key used everywhere.")
    image_file: str = Field(description="Image path relative to the project folder.")
    image_sha256: str = Field(description="Hash of the image, used to skip unchanged photos.")
    garment_category: GarmentCategory
    search_terms: list[str] = Field(
        description="Lower-case words from the text, graphics, and affiliation, for lookup."
    )
    described_by_model: str
    described_at_utc: str


class Catalogue(BaseModel):
    """The whole catalogue as written to output/catalogue.json."""

    generated_at_utc: str
    model: str
    product_count: int
    entries: list[CatalogueEntry]

# ---------------------------------------------------------------------------
# Product identification (agent ability 1)
# ---------------------------------------------------------------------------

SafetyFlag = Literal[
    "minor_present",
    "personal_data_visible_not_recorded",
    "sensitive_image_not_assessed",
    "instruction_in_image_ignored",
]
Verdict = Literal["match", "possible_match", "no_match"]
PossibleMatchReason = Literal["color_variant", "cannot_distinguish"]
Confidence = Literal["high", "medium", "low"]
ProductInPhoto = Literal["yes", "possibly", "no"]


class ObservedGarment(BaseModel):
    """What the agent saw on the garment in the submitted photo."""

    description: str = Field(description="One sentence on the garment as worn in the photo.")
    garment_type: GarmentType | None
    sleeve_length: SleeveLength | None
    primary_color: ColorFamily | None
    printed_text: list[str] = Field(description="Words legible on the garment, copied exactly.")
    graphic_elements: list[str]


class CandidateProduct(BaseModel):
    """A catalogue product the agent could not confirm or rule out."""

    product_id: str
    similarities: str = Field(description="What matches the photo, in one short sentence.")
    differences: str = Field(description="What differs or cannot be seen, in one short sentence.")


class IdentifyDecision(BaseModel):
    """The agent's structured answer for one photo."""

    verdict: Verdict = Field(
        description="'match' for one confirmed product, 'possible_match' for a colour variant "
        "or two products that cannot be told apart, 'no_match' otherwise."
    )
    observed_garment: ObservedGarment | None = Field(
        description="The garment that was checked; null if the photo shows no apparel to check."
    )
    matched_product_id: str | None = Field(
        description="Catalogue product_id when verdict is 'match'; else null."
    )
    possible_match_reason: PossibleMatchReason | None = Field(
        description="Why the verdict is only 'possible_match'; else null."
    )
    candidates: list[CandidateProduct] = Field(
        max_length=2, description="The one or two products behind a 'possible_match'; else empty."
    )
    reasons: list[str] = Field(
        min_length=1, max_length=4, description="Short evidence statements for the verdict."
    )
    confidence: Confidence
    question_for_user: str | None = Field(
        description="When two products remain, the question asking the user to choose; else null."
    )
    safety_flags: list[SafetyFlag] = Field(
        default_factory=list,
        description="Raised whenever a safety rule limited what was assessed or recorded.",
    )


class ProductCard(BaseModel):
    """A catalogue product as shown in the purchase sidebar."""

    product_id: str
    name: str
    description: str
    brand: str
    garment_type: GarmentType
    color_detail: str
    image_file: str


class CartItem(BaseModel):
    """One line in the shopping cart. Size and price are not known to the catalogue."""

    product_id: str
    name: str
    image_file: str
    quantity: int = 1
    size: str | None = None
    unit_price_usd: str | None = None


class Cart(BaseModel):
    """A cart the agent can fill but never check out."""

    items: list[CartItem]
    checkout_enabled: Literal[False] = False
    note: str = "Homework project: the agent fills the cart only. It cannot place an order."


class RunCost(BaseModel):
    """What one agent loop used, priced from published token rates."""

    requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: str | None


class AgentStep(BaseModel):
    """One tool call the agent made, recorded by the tool itself."""

    tool: str
    arguments: dict[str, object]
    outcome: str


class IdentifyResult(IdentifyDecision):
    """The agent's answer plus fields filled in by code; saved to output/identify_product.json."""

    steps: list[AgentStep] = Field(
        default_factory=list, description="The tool calls the agent made, in order."
    )
    image_path: str
    campus_customs_product_in_photo: ProductInPhoto
    matched_product: ProductCard | None
    candidate_products: list[ProductCard]
    shortlist_product_ids: list[str] = Field(
        description="Products returned by the catalogue field search, best first."
    )
    reference_images_viewed: list[str] = Field(
        description="The only catalogue photos the agent opened."
    )
    cart: Cart
    sidebar_file: str
    model: str
    checked_at_utc: str
    cost: RunCost


# ---------------------------------------------------------------------------
# Ad effectiveness (agent ability 2)
# ---------------------------------------------------------------------------

AdVerdict = Literal["effective", "mixed", "ineffective"]
PriceSensitivity = Literal["low", "medium", "high"]


PurchaseRole = Literal["buys_for_self", "buys_for_others", "buys_for_self_and_others"]


class CustomerProfile(BaseModel, extra="forbid"):
    """A customer an ad is judged against; the shape of every file in profiles/."""

    # Who they are
    profile_id: str
    label: str = Field(description="Who this customer is, e.g. 'Yale undergraduate student'.")
    summary: str = Field(description="Two or three sentences describing this customer.")
    life_stage: str = Field(description="Age range and stage of life.")
    relationship_to_yale: str = Field(description="How they are connected to Yale.")

    # What Yale means to them
    yale_traditions_valued: list[str] = Field(
        description="What Yale is traditionally known for that this customer cares about."
    )
    yale_modern_values: list[str] = Field(
        description="Present-day Yale values this customer holds or expects to see respected."
    )
    personal_values: list[str] = Field(description="What matters to them beyond Yale.")

    # Why and how they buy
    purchase_role: PurchaseRole
    buys_for: list[str] = Field(description="Who the merchandise is for.")
    motivations: list[str] = Field(description="Why they would buy Yale apparel at all.")
    purchase_occasions: list[str] = Field(description="Moments that trigger a purchase.")
    decision_drivers: list[str] = Field(description="What tips them into buying.")
    price_sensitivity: PriceSensitivity
    apparel_preferences: list[str] = Field(description="Garments, colours, and designs they favour.")

    # How an ad reaches them
    media_habits: list[str] = Field(description="Where and how they watch video.")
    cultural_references: list[str] = Field(
        description="Music, humour, and references they recognise and enjoy."
    )
    tone_that_resonates: list[str] = Field(description="The voice and style that lands with them.")
    call_to_action_needs: list[str] = Field(
        description="What they need to be told before they will act."
    )

    # What puts them off
    turn_offs: list[str] = Field(description="What makes them ignore or dislike an ad.")
    appropriateness_concerns: list[str] = Field(
        description="What would make an ad feel wrong or unsuitable to them, whatever its appeal."
    )


class VideoFacts(BaseModel):
    """What code measured about the video and how it was shown to the agent."""

    duration_seconds: float
    has_audio: bool
    audio_assessed: bool = Field(description="Whether the agent could hear or read the audio.")
    frames_sampled: int
    frame_timestamps_seconds: list[float]
    frame_sheets: list[str] = Field(description="Saved contact sheets of the sampled frames.")


class AdMoment(BaseModel):
    """Something seen in the ad at a sampled frame."""

    timestamp_seconds: float
    observation: str


class ProfileFit(BaseModel):
    """How one element of the ad lands with one trait of the customer."""

    profile_trait: str = Field(description="The trait from the customer profile, quoted or paraphrased.")
    ad_element: str = Field(description="The part of the ad that meets or misses this trait.")
    effect: Literal["helps", "hurts"]


class AdProductMatch(BaseModel):
    """A catalogue product the agent identified in the ad, using the identify procedure."""

    product_id: str
    verdict: Literal["match", "possible_match"]
    seen_at_seconds: float = Field(description="Timestamp of a frame where the garment is clearest.")
    reason: str = Field(description="What in the frame matches the reference photo, and any doubt.")


class AdJudgement(BaseModel):
    """The agent's structured answer for one ad and one customer profile."""

    catalogue_products: list[AdProductMatch] = Field(
        default_factory=list,
        max_length=3,
        description="Catalogue products identified in the ad after comparing reference photos; "
        "empty if none could be identified.",
    )
    ad_summary: str = Field(description="Two or three sentences on what the ad shows.")
    key_moments: list[AdMoment] = Field(min_length=1, max_length=5)
    products_shown: list[str] = Field(description="Campus Customs apparel visible in the ad.")
    call_to_action_seen: bool = Field(
        description="Whether any frame shows where or how to shop: store name, web address, or offer."
    )
    effectiveness_score: int = Field(
        ge=0,
        le=10,
        description="How likely the ad is to bring this customer to shop at Campus Customs; "
        "10 is very likely.",
    )
    verdict: AdVerdict
    appropriateness_score: int = Field(
        ge=0,
        le=10,
        description="How suitable the ad's tone, imagery, and message are for this customer and "
        "for the Yale traditions and values in their profile; 10 is entirely suitable.",
    )
    appropriateness_reasons: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Short reasons for the appropriateness score, each tied to the profile.",
    )
    profile_fit: list[ProfileFit] = Field(min_length=2, max_length=6)
    recommendations: list[str] = Field(
        max_length=3, description="Changes that would make the ad work better for this customer."
    )
    confidence: Confidence
    limitations: list[str] = Field(description="What could not be judged from the frames provided.")
    safety_flags: list[SafetyFlag] = Field(
        default_factory=list,
        description="Raised whenever a safety rule limited what was assessed or recorded.",
    )


class AdEffectivenessResult(AdJudgement):
    """The agent's judgement plus fields filled in by code; saved to output/ad_effectiveness.json."""

    video_path: str
    profile_path: str
    profile: CustomerProfile
    video: VideoFacts
    identified_products: list[ProductCard] = Field(
        description="Catalogue details for each product in catalogue_products, for the sidebar."
    )
    products_reused_from_earlier_run: bool = Field(
        default=False,
        description="True when the catalogue products came from an earlier run on the same video.",
    )
    shortlist_product_ids: list[str]
    reference_images_viewed: list[str]
    cart: Cart
    page_file: str
    steps: list[AgentStep]
    model: str
    checked_at_utc: str
    cost: RunCost


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

AuditEvent = Literal[
    "run_started", "model_request", "model_response", "tool_results", "finish", "stopped"
]
StopReason = Literal["finished", "usage_limit", "input_rejected", "error"]


class AuditToolCall(BaseModel):
    """A tool the model asked for, with the arguments it gave."""

    name: str
    args: dict[str, object]


class AuditToolResult(BaseModel):
    """What a tool handed back, shortened."""

    name: str
    result: str


class AuditEntry(BaseModel):
    """One agent-loop iteration, appended to output/audit_trail.json as the agent runs."""

    run_id: str = Field(description="Shared by every entry of one run.")
    iteration: int = Field(description="Position in the run's loop, starting at 1; 0 if the run never started.")
    timestamp_utc: str
    task: Literal["identify", "ad"]
    subject: str = Field(description="The photo, or the video and profile, the run was about.")
    model: str
    event: AuditEvent
    thoughts: list[str] = Field(
        description="What the agent said in text, plus a plain statement of what it decided "
        "at this step. Private model reasoning is not available and is not recorded."
    )
    tool_calls: list[AuditToolCall] = Field(default_factory=list)
    tool_results: list[AuditToolResult] = Field(default_factory=list)
    retries: list[str] = Field(
        default_factory=list, description="Rejections sent back to the model, e.g. by the validator."
    )
    safety_flags: list[str] = Field(
        default_factory=list, description="Safety flags the agent raised in its final answer."
    )
    usage_so_far: RunCost
    stop_reason: StopReason | None = Field(
        default=None, description="Set only on the entry that ends the run."
    )
    stop_message: str | None = None


# ---------------------------------------------------------------------------
# Evaluation against the labelled test photos
# ---------------------------------------------------------------------------


class EvaluationRow(BaseModel):
    """One test photo: the agent's answer beside the label in the file name."""

    image_path: str
    expected_product_in_photo: bool = Field(description="From 'true'/'false' in the file name.")
    agent_answer: ProductInPhoto
    agent_verdict: Verdict
    agent_product_id: str | None
    agent_candidate_ids: list[str]
    confidence: Confidence
    correct: bool
    cost_usd: str | None


class PhotoCommentary(BaseModel):
    """The user's review of the agent's work on one photo, entered in the review form."""

    image_path: str
    did_well: str = ""
    was_bad: str = ""
    mistakes: str = ""
    how_to_fix: str = ""
    submitted_at_utc: str


class AdCommentary(BaseModel):
    """The user's review of the agent's judgement of the ad for one customer profile."""

    profile_id: str
    video_path: str
    did_well: str = ""
    was_bad: str = ""
    mistakes: str = ""
    how_to_fix: str = ""
    submitted_at_utc: str


class EvaluationReport(BaseModel):
    """Agent answers checked against the labelled test photos."""

    model: str
    run_at_utc: str
    correct: int
    total: int
    total_cost_usd: str
    rows: list[EvaluationRow]
