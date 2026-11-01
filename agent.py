"""Campus Customs agent entry point.

    python agent.py --image "data/test_images/example.jpg"
    python agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"

--image checks each photo for a Campus Customs product, saves the structured answers (a
list, one entry per photo) to output/identify_product.json, fills output/cart.json, and
writes a page per photo that shows the product beside it. It accepts one or more paths.

--video with --profile judges how effective the ad would be at convincing that customer to
shop at Campus Customs. Each run is added to the list in output/ad_effectiveness.json, so
running the command once per profile builds up one file. --profile accepts one or more paths.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
import webbrowser
from pathlib import Path

from pydantic import TypeAdapter
from pydantic_ai import Agent, BinaryContent, ModelRetry, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.usage import RunUsage, UsageLimits
from pydantic_graph import End

from config import (
    CATALOGUE_DB_PATH,
    MAX_LOOP_USD,
    OUTPUT_DIR,
    PROJECT_DIR,
    build_model,
    model_name,
    price_usd,
)
from models import (
    AdEffectivenessResult,
    AdJudgement,
    AuditEntry,
    AuditToolCall,
    AuditToolResult,
    Cart,
    CartItem,
    IdentifyDecision,
    IdentifyResult,
    RunCost,
)
from tools import (
    AGENT_TOOLS,
    CART_PATH,
    PHOTO_MAX_SIDE,
    AgentDeps,
    append_audit,
    build_cart,
    get_entries,
    load_known_products,
    load_profile,
    model_image,
    now_iso,
    product_card,
    render_ad_page,
    render_sidebar,
    resolve_photo,
    resolve_profile,
    resolve_video,
    save_known_products,
    write_text,
)

PROMPT_PATH = PROJECT_DIR / "prompts" / "prompt.md"
IDENTIFY_OUTPUT_PATH = OUTPUT_DIR / "identify_product.json"
AD_OUTPUT_PATH = OUTPUT_DIR / "ad_effectiveness.json"
# At gpt-6-astra rates the worst case under these caps is $0.30, inside the $0.50 rule.
IDENTIFY_LIMITS = UsageLimits(
    request_limit=5, tool_calls_limit=6, input_tokens_limit=22_000, output_tokens_limit=1_500
)
# Worst case $0.41 at gpt-6-astra rates; the frames are re-sent on each request.
AD_LIMITS = UsageLimits(
    request_limit=6, tool_calls_limit=8, input_tokens_limit=28_000, output_tokens_limit=2_500
)

campus_customs_agent = Agent(
    # One agent, two abilities: each has its own structured answer.
    output_type=[IdentifyDecision, AdJudgement],
    deps_type=AgentDeps,
    tools=AGENT_TOOLS,
    # Lets the agent add to the cart and give its final answer in the same turn.
    end_strategy="exhaustive",
)


def prompt_for(task: str, products_known: bool = False) -> str:
    """The system prompt for one job, cut from the single prompt file.

    The introduction, the safety rules, and the limits are always sent. The section for the
    ability that is not in use is left out, because the prompt is re-sent on every request.
    An ad run that still has to identify catalogue products keeps the Ability 1 sections,
    since it follows the same procedure.
    """

    sections = re.split(r"\n(?=## )", PROMPT_PATH.read_text(encoding="utf-8"))
    if task == "identify":
        skip = ("## Ability 2",)
    elif products_known:
        skip = ("## Ability 1", "## Verdict rules")
    else:
        skip = ()
    return "\n".join(section for section in sections if not section.startswith(skip))


@campus_customs_agent.instructions
def load_prompt(ctx: RunContext[AgentDeps]) -> str:
    return prompt_for(ctx.deps.task, ctx.deps.known_products is not None)


def check_ad_judgement(ctx: RunContext[AgentDeps], judgement: AdJudgement) -> AdJudgement:
    """Hold the ad judgement to what the tools actually showed."""

    deps = ctx.deps
    if deps.profile is None or deps.video is None:
        raise ModelRetry("Call read_customer_profile and watch_ad_video before judging the ad.")
    late = [m.timestamp_seconds for m in judgement.key_moments
            if not 0 <= m.timestamp_seconds <= deps.video.duration_seconds]
    if late:
        raise ModelRetry(f"key_moments timestamps {late} are outside the ad's length.")
    unseen = [m.product_id for m in judgement.catalogue_products if m.product_id not in deps.viewed]
    if unseen and deps.known_products is None:
        raise ModelRetry(
            f"catalogue_products {unseen} were not compared with view_catalogue_images. "
            "Compare their reference photos or remove them."
        )
    bands = {"effective": range(8, 11), "mixed": range(4, 8), "ineffective": range(0, 4)}
    if judgement.effectiveness_score not in bands[judgement.verdict]:
        raise ModelRetry("The verdict does not match the score band given in the instructions.")
    return judgement


@campus_customs_agent.output_validator
def check_decision(
    ctx: RunContext[AgentDeps], decision: IdentifyDecision | AdJudgement
) -> IdentifyDecision | AdJudgement:
    """Hold the answer to the matching rules and to products the tools actually returned."""

    deps = ctx.deps
    if isinstance(decision, AdJudgement) != (deps.task == "ad"):
        wanted = "AdJudgement" if deps.task == "ad" else "IdentifyDecision"
        raise ModelRetry(f"This request needs a {wanted} answer.")
    if isinstance(decision, AdJudgement):
        return check_ad_judgement(ctx, decision)
    candidate_ids = [candidate.product_id for candidate in decision.candidates]
    if decision.verdict == "match":
        if decision.matched_product_id not in deps.viewed:
            raise ModelRetry(
                "A 'match' needs a matched_product_id whose reference photo you compared "
                "with view_catalogue_images."
            )
        if candidate_ids or decision.possible_match_reason:
            raise ModelRetry("A 'match' has no candidates and no possible_match_reason.")
    elif decision.verdict == "possible_match":
        if not candidate_ids or any(pid not in deps.viewed for pid in candidate_ids):
            raise ModelRetry(
                "A 'possible_match' lists one or two candidates whose reference photos you compared."
            )
        expected = 1 if decision.possible_match_reason == "color_variant" else 2
        if decision.possible_match_reason is None or len(candidate_ids) != expected:
            raise ModelRetry(
                "Give possible_match_reason: 'color_variant' with one candidate, or "
                "'cannot_distinguish' with two."
            )
        if expected == 2 and not decision.question_for_user:
            raise ModelRetry("Ask the user to choose between the two products in question_for_user.")
        if decision.matched_product_id:
            raise ModelRetry("matched_product_id must be null for a 'possible_match'.")
    elif decision.matched_product_id or candidate_ids:
        raise ModelRetry("A 'no_match' has no matched_product_id and no candidates.")
    return decision


# --- audited agent loop ----------------------------------------------------


def _short(value: object, limit: int = 300) -> str:
    """One-line, bounded text for the audit trail; never image bytes."""

    if isinstance(value, BinaryContent):
        return "[image]"
    if isinstance(value, (list, tuple)):
        text = " ".join(_short(item, limit) for item in value)
    elif isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str)
        except TypeError:
            text = repr(value)
    text = " ".join(text.split())
    return text[:limit] + ("... [shortened]" if len(text) > limit else "")


def _run_cost(usage: RunUsage | None) -> RunCost:
    if usage is None:
        return RunCost(requests=0, tool_calls=0, input_tokens=0, output_tokens=0, cost_usd="0.0000")
    cost = price_usd(usage.input_tokens, usage.output_tokens)
    return RunCost(
        requests=usage.requests,
        tool_calls=usage.tool_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=f"{cost:.4f}" if cost is not None else None,
    )


def _describe_node(node: object) -> dict[str, object]:
    """Turn one loop node into the auditable parts of an entry."""

    thoughts: list[str] = []
    calls: list[AuditToolCall] = []
    results: list[AuditToolResult] = []
    retries: list[str] = []
    event = "model_request"

    if isinstance(node, End):
        return {"event": "finish", "thoughts": ["The answer passed validation, so the run stops."]}

    prompt = getattr(node, "user_prompt", None)
    if prompt is not None:
        event = "run_started"
        thoughts.append(f"Request received: {_short(prompt, 400)}")

    response = getattr(node, "model_response", None)
    if response is not None:
        event = "model_response"
        for part in response.parts:
            if isinstance(part, TextPart) and part.content.strip():
                thoughts.append(f"Agent said: {_short(part.content, 600)}")
            elif isinstance(part, ThinkingPart):
                thoughts.append("The model reasoned privately; that reasoning is not retained.")
            elif isinstance(part, ToolCallPart):
                args = {key: _short(value, 200) for key, value in part.args_as_dict().items()}
                calls.append(AuditToolCall(name=part.tool_name, args=args))
        final = [c.name for c in calls if c.name.startswith("final_result")]
        tools = [c.name for c in calls if not c.name.startswith("final_result")]
        if tools:
            thoughts.append("The agent decided to call: " + ", ".join(tools) + ".")
        if final:
            thoughts.append("The agent gave its final answer.")

    request = getattr(node, "request", None)
    if request is not None:
        for part in request.parts:
            if isinstance(part, ToolReturnPart):
                results.append(AuditToolResult(name=part.tool_name, result=_short(part.content)))
            elif isinstance(part, RetryPromptPart):
                retries.append(f"{part.tool_name or 'answer'}: {_short(part.content)}")
        if results or retries:
            event = "tool_results"
            thoughts.append(
                "Tool results were returned to the model."
                if not retries
                else "An answer or tool call was rejected and sent back for correction."
            )
        elif prompt is None:
            thoughts.append("The request and what has been seen so far were sent to the model.")

    return {
        "event": event,
        "thoughts": thoughts,
        "tool_calls": calls,
        "tool_results": results,
        "retries": retries,
    }


async def _run_audited(
    prompt: object, deps: AgentDeps, limits: UsageLimits, subject: str
) -> tuple[IdentifyDecision | AdJudgement, RunUsage]:
    """Run the agent loop, appending one audit entry per iteration as it happens."""

    common = {"run_id": uuid.uuid4().hex[:12], "task": deps.task, "subject": subject, "model": model_name()}
    iteration, usage = 0, None
    try:
        async with campus_customs_agent.iter(
            prompt, model=build_model(), deps=deps, usage_limits=limits
        ) as agent_run:
            async for node in agent_run:
                iteration += 1
                usage = agent_run.usage
                entry = AuditEntry(
                    **common,
                    iteration=iteration,
                    timestamp_utc=now_iso(),
                    usage_so_far=_run_cost(usage),
                    **_describe_node(node),
                )
                if isinstance(node, End):
                    output = node.data.output
                    entry.stop_reason = "finished"
                    entry.safety_flags = list(output.safety_flags)
                    entry.stop_message = (
                        f"verdict={output.verdict}"
                        + (f", product={output.matched_product_id}" if isinstance(output, IdentifyDecision) else
                           f", effectiveness={output.effectiveness_score}, "
                           f"appropriateness={output.appropriateness_score}")
                    )
                append_audit(entry)
            result = agent_run.result
        return result.output, result.usage
    except Exception as exc:
        append_audit(
            AuditEntry(
                **common,
                iteration=iteration + 1,
                timestamp_utc=now_iso(),
                event="stopped",
                thoughts=["The run was stopped before the agent reached an answer."],
                usage_so_far=_run_cost(usage),
                stop_reason="usage_limit" if isinstance(exc, UsageLimitExceeded) else "error",
                stop_message=f"{type(exc).__name__}: {_short(str(exc))}",
            )
        )
        raise


def audit_rejected_input(task: str, subject: str, exc: Exception) -> None:
    """Record a request that was refused before any model call."""

    append_audit(
        AuditEntry(
            run_id=uuid.uuid4().hex[:12],
            iteration=0,
            timestamp_utc=now_iso(),
            task=task,
            subject=subject,
            model=model_name(),
            event="stopped",
            thoughts=["The input was refused by a code check before the agent was started."],
            usage_so_far=_run_cost(None),
            stop_reason="input_rejected",
            stop_message=f"{type(exc).__name__}: {_short(str(exc))}",
        )
    )


def identify_product(image: str) -> IdentifyResult:
    """Run the agent on one photo and assemble the saved result."""

    try:
        photo = resolve_photo(image)
        if not CATALOGUE_DB_PATH.is_file():
            raise FileNotFoundError("output/catalogue.db is missing. Run build_catalogue.py first.")
    except (FileNotFoundError, ValueError, PermissionError) as exc:
        audit_rejected_input("identify", image, exc)
        raise
    deps = AgentDeps(image_path=photo)
    # The model is given the pixels only, never the file name or path.
    decision, usage = asyncio.run(
        _run_audited(
            ["Check this photo for a Campus Customs product.", model_image(photo, PHOTO_MAX_SIDE)],
            deps,
            IDENTIFY_LIMITS,
            photo.relative_to(PROJECT_DIR).as_posix(),
        )
    )
    cost = price_usd(usage.input_tokens, usage.output_tokens)

    # The cart only ever holds a confirmed match, whatever the model asked for.
    matched = deps.shortlist.get(decision.matched_product_id or "")
    # Two indistinguishable products still mean a catalogue product is present.
    in_photo = {"match": "yes", "no_match": "no"}.get(
        decision.verdict,
        "yes" if decision.possible_match_reason == "cannot_distinguish" else "possibly",
    )
    return IdentifyResult(
        **decision.model_dump(),
        steps=deps.steps,
        image_path=photo.relative_to(PROJECT_DIR).as_posix(),
        campus_customs_product_in_photo=in_photo,
        matched_product=product_card(matched) if matched else None,
        candidate_products=[
            product_card(deps.shortlist[c.product_id]) for c in decision.candidates
        ],
        shortlist_product_ids=list(deps.shortlist),
        reference_images_viewed=deps.viewed,
        cart=build_cart([matched] if matched else []),
        sidebar_file=f"output/identify_product_{photo.stem}.html",
        model=model_name(),
        checked_at_utc=now_iso(),
        cost=RunCost(
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=f"{cost:.4f}" if cost is not None else None,
        ),
    )


def judge_ad(video: str, profile: str, reidentify: bool = False) -> AdEffectivenessResult:
    """Run the agent on one ad video and one customer profile."""

    try:
        video_path, profile_path = resolve_video(video), resolve_profile(profile)
        load_profile(profile_path)  # Reject a malformed profile before spending tokens.
    except (FileNotFoundError, ValueError, PermissionError) as exc:
        audit_rejected_input("ad", f"{video} | {profile}", exc)
        raise
    # The products in a video do not depend on the customer, so they are identified once
    # per video and reused for every later profile.
    known = None if reidentify else load_known_products(video_path)
    deps = AgentDeps(
        task="ad", video_path=video_path, profile_path=profile_path, known_products=known
    )
    request = (
        "Judge how effective this Campus Customs ad video would be at convincing the customer "
        "in the profile to shop at Campus Customs.\n"
        f"Ad file name: {video_path.name}"
    )
    if known is not None:
        deps.shortlist = {e.product_id: e for e in get_entries([m.product_id for m in known])}
        request += (
            "\nCatalogue products in this ad were already identified on an earlier run; skip "
            "step 3, leave catalogue_products empty (it is filled in for you), and do not "
            "mention this reuse in limitations. Identified: "
            + ("; ".join(f"{m.product_id} ({m.verdict}): {m.reason}" for m in known) or "none")
        )
    subject = (
        f"{video_path.relative_to(PROJECT_DIR).as_posix()} | "
        f"{profile_path.relative_to(PROJECT_DIR).as_posix()}"
    )
    judgement, usage = asyncio.run(_run_audited(request, deps, AD_LIMITS, subject))
    cost = price_usd(usage.input_tokens, usage.output_tokens)
    if known is not None:
        judgement = judgement.model_copy(update={"catalogue_products": known})
    else:
        save_known_products(video_path, judgement.catalogue_products)
    limitations = list(judgement.limitations)
    if deps.video.has_audio and not any("audio" in item.lower() for item in limitations):
        limitations.append("The ad's audio track could not be assessed.")
    return AdEffectivenessResult(
        **judgement.model_dump(exclude={"limitations"}),
        limitations=limitations,
        video_path=video_path.relative_to(PROJECT_DIR).as_posix(),
        profile_path=profile_path.relative_to(PROJECT_DIR).as_posix(),
        profile=deps.profile,
        video=deps.video,
        products_reused_from_earlier_run=known is not None,
        identified_products=[
            product_card(deps.shortlist[m.product_id]) for m in judgement.catalogue_products
        ],
        shortlist_product_ids=list(deps.shortlist),
        reference_images_viewed=deps.viewed,
        # As in identification, the cart holds confirmed matches only.
        cart=build_cart(
            [deps.shortlist[m.product_id] for m in judgement.catalogue_products if m.verdict == "match"]
        ),
        page_file=f"output/ad_effectiveness_{deps.profile.profile_id}.html",
        steps=deps.steps,
        model=model_name(),
        checked_at_utc=now_iso(),
        cost=RunCost(
            requests=usage.requests,
            tool_calls=usage.tool_calls,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=f"{cost:.4f}" if cost is not None else None,
        ),
    )


AD_RESULTS = TypeAdapter(list[AdEffectivenessResult])


def load_ad_results() -> list[AdEffectivenessResult]:
    """Every saved ad run; empty if none yet."""

    if not AD_OUTPUT_PATH.is_file():
        return []
    return AD_RESULTS.validate_json(AD_OUTPUT_PATH.read_text(encoding="utf-8"))


def save_ad_result(result: AdEffectivenessResult) -> None:
    """Add this run to output/ad_effectiveness.json, replacing an earlier run of the same
    video and profile so separate commands build up one list."""

    kept = [
        earlier
        for earlier in load_ad_results()
        if (earlier.video_path, earlier.profile_path) != (result.video_path, result.profile_path)
    ]
    write_text(AD_OUTPUT_PATH, AD_RESULTS.dump_json([*kept, result], indent=2).decode() + "\n")


def report_ad(result: AdEffectivenessResult) -> None:
    print(f"\nAd: {result.video_path}   Customer: {result.profile.label}")
    print(f"Effectiveness: {result.effectiveness_score}/10  ({result.verdict},"
          f" confidence: {result.confidence})")
    print(f"Appropriateness: {result.appropriateness_score}/10")
    for reason in result.appropriateness_reasons:
        print(f"  - {reason}")
    print(f"What the ad shows: {result.ad_summary}")
    for match in result.catalogue_products:
        print(f"Catalogue product ({match.verdict}): {match.product_id} at"
              f" {match.seen_at_seconds:.1f}s - {match.reason}")
    if not result.catalogue_products:
        print("Catalogue product: none identified in the ad")
    for fit in result.profile_fit:
        print(f"  [{fit.effect}] {fit.profile_trait} -> {fit.ad_element}")
    for recommendation in result.recommendations:
        print(f"  Recommend: {recommendation}")
    for limitation in result.limitations:
        print(f"  Limitation: {limitation}")
    items = ", ".join(item.name for item in result.cart.items) or "empty"
    print(f"Cart: {items}  (checkout is not available)")
    print(f"Frames viewed: {result.video.frames_sampled}   catalogue photos opened:"
          f" {len(result.reference_images_viewed)} of 102   requests: {result.cost.requests}"
          f"   cost: ${result.cost.cost_usd} of ${MAX_LOOP_USD} cap")
    print(f"Saved output/ad_effectiveness.json, output/cart.json, {result.page_file}")


def ask_user_to_choose(result: IdentifyResult) -> IdentifyResult:
    """For a possible match, let the person at the terminal pick the product for the cart."""

    if result.verdict != "possible_match" or not sys.stdin.isatty():
        return result
    print(result.question_for_user or "Is this the product? Add it to the cart?")
    for number, card in enumerate(result.candidate_products, start=1):
        print(f"  {number}. {card.name}  ({card.product_id})")
    answer = input("Number to add to the cart, or Enter to skip: ").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(result.candidate_products):
        chosen = result.candidate_products[int(answer) - 1]
        result.cart.items.append(
            CartItem(product_id=chosen.product_id, name=chosen.name, image_file=chosen.image_file)
        )
    return result


def save(results: list[IdentifyResult]) -> list[Path]:
    """Write the answers, one combined cart, and a product page per photo.

    Results for photos not in this run are kept, so checking one photo does not discard
    the others already saved.
    """

    adapter = TypeAdapter(list[IdentifyResult])
    earlier = (
        adapter.validate_json(IDENTIFY_OUTPUT_PATH.read_text(encoding="utf-8"))
        if IDENTIFY_OUTPUT_PATH.is_file()
        else []
    )
    fresh = {result.image_path for result in results}
    merged = sorted(
        [*(r for r in earlier if r.image_path not in fresh), *results],
        key=lambda result: result.image_path,
    )
    write_text(IDENTIFY_OUTPUT_PATH, adapter.dump_json(merged, indent=2).decode() + "\n")
    items = {item.product_id: item for result in results for item in result.cart.items}
    write_text(CART_PATH, Cart(items=list(items.values())).model_dump_json(indent=2) + "\n")
    return [render_sidebar(result, PROJECT_DIR / result.sidebar_file) for result in results]


def report(result: IdentifyResult) -> None:
    print(f"\nPhoto: {result.image_path}")
    print(f"Campus Customs product in photo: {result.campus_customs_product_in_photo}"
          f"   (verdict: {result.verdict}, confidence: {result.confidence})")
    if result.matched_product:
        print(f"Product: {result.matched_product.name}  [{result.matched_product.product_id}]")
    for card in result.candidate_products:
        print(f"Possible: {card.name}  [{card.product_id}]")
    for reason in result.reasons:
        print(f"  - {reason}")
    if result.question_for_user:
        print(f"Question: {result.question_for_user}")
    items = ", ".join(item.name for item in result.cart.items) or "empty"
    print(f"Cart: {items}  (checkout is not available)")
    print(f"Catalogue photos opened: {len(result.reference_images_viewed)} of 102"
          f"   requests: {result.cost.requests}   cost: ${result.cost.cost_usd}"
          f" of ${MAX_LOOP_USD} cap")
    print(f"Page: {result.sidebar_file}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Campus Customs agent")
    parser.add_argument("--image", nargs="+", help="Photo(s) to check, under data/.")
    parser.add_argument("--video", help="Campus Customs ad video, under data/.")
    parser.add_argument(
        "--profile",
        nargs="+",
        help="Customer profile JSON file(s) to judge the ad against, under profiles/.",
    )
    parser.add_argument(
        "--reidentify",
        action="store_true",
        help="Identify the ad's catalogue products again instead of reusing the saved answer.",
    )
    parser.add_argument("--no-open", action="store_true", help="Do not open the product page.")
    args = parser.parse_args()
    if bool(args.video) != bool(args.profile):
        parser.error("--video and --profile must be given together.")
    if bool(args.image) == bool(args.video):
        parser.error("Give either --image, or --video with --profile.")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    results: list[IdentifyResult] = []
    try:
        if args.video:
            for profile in args.profile:
                # Each profile is its own agent loop with its own usage limits.
                ad = judge_ad(args.video, profile, args.reidentify)
                save_ad_result(ad)
                write_text(CART_PATH, ad.cart.model_dump_json(indent=2) + "\n")
                page = render_ad_page(ad, PROJECT_DIR / ad.page_file)
                report_ad(ad)
                if not args.no_open:
                    webbrowser.open(page.as_uri())
            return 0
        for image in args.image:
            # Each photo is its own agent loop with its own usage limits.
            results.append(ask_user_to_choose(identify_product(image)))
    except (FileNotFoundError, ValueError, PermissionError, RuntimeError) as exc:
        print(f"Cannot run this request: {exc}", file=sys.stderr)
        return 2
    except UsageLimitExceeded as exc:
        print(f"Stopped at the usage limit before reaching an answer: {exc}", file=sys.stderr)
        return 1
    pages = save(results)
    for result in results:
        report(result)
    print("\nSaved output/identify_product.json and output/cart.json")
    if not args.no_open:
        for page in pages:
            webbrowser.open(page.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
