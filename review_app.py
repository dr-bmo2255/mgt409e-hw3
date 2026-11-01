"""Local review form for the agent evaluation.

    python review_app.py        then open http://127.0.0.1:8765
    python review_app.py --export    save the pages as plain HTML files in output/

Part 1 shows each test photo with what the agent saw, the steps it took, its answer, and
the product sidebar. Part 2 shows the ad video and the frames the agent saw, with the
agent's judgement for each customer profile. Submitting a comment saves it, rewrites
output/agent_evaluation.md, and moves to the next item. Standard library only; listens on
this machine only.
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import imageio_ffmpeg
from pydantic import TypeAdapter

from agent import IDENTIFY_OUTPUT_PATH, load_ad_results
from config import OUTPUT_DIR, PROJECT_DIR, inside_sandbox
from evaluate import EVALUATION_PATH
from models import (
    AdCommentary,
    AdEffectivenessResult,
    AgentStep,
    Cart,
    EvaluationReport,
    EvaluationRow,
    IdentifyResult,
    PhotoCommentary,
)
from tools import card_html, data_uri, meter_svg, now_iso, write_text

HOST, PORT = "127.0.0.1", 8765
COMMENTS_PATH = OUTPUT_DIR / "agent_evaluation_comments.json"
AD_COMMENTS_PATH = OUTPUT_DIR / "agent_evaluation_ad_comments.json"
MARKDOWN_PATH = OUTPUT_DIR / "agent_evaluation.md"
PREVIEW_DIR = OUTPUT_DIR / "ad_preview"
MAX_BODY_BYTES = 100_000
MAX_FIELD_CHARACTERS = 5_000
NOT_CARRIED = "Item is not carried by Campus Customs"
QUESTIONS = [
    ("did_well", "What did the agent do well?"),
    ("was_bad", "What was bad, or weaker than you would want?"),
    ("mistakes", "Were there any mistakes? Describe them."),
    ("how_to_fix", "If there were mistakes, how would you try to fix them?"),
]
COMMENTS = TypeAdapter(dict[str, PhotoCommentary])
AD_COMMENTS = TypeAdapter(dict[str, AdCommentary])
RESULTS = TypeAdapter(list[IdentifyResult])


# --- data ------------------------------------------------------------------


def load_results() -> tuple[list[IdentifyResult], EvaluationReport]:
    results = RESULTS.validate_json(IDENTIFY_OUTPUT_PATH.read_text(encoding="utf-8"))
    report = EvaluationReport.model_validate_json(EVALUATION_PATH.read_text(encoding="utf-8"))
    return results, report


def load_comments() -> dict[str, PhotoCommentary]:
    if not COMMENTS_PATH.is_file():
        return {}
    return COMMENTS.validate_json(COMMENTS_PATH.read_text(encoding="utf-8"))


def load_ad_comments() -> dict[str, AdCommentary]:
    if not AD_COMMENTS_PATH.is_file():
        return {}
    return AD_COMMENTS.validate_json(AD_COMMENTS_PATH.read_text(encoding="utf-8"))


def write_markdown() -> None:
    results, report = load_results()
    write_text(
        MARKDOWN_PATH,
        evaluation_markdown(results, report, load_comments())
        + ad_markdown(load_ad_results(), load_ad_comments()),
    )


def save_comment(comment: PhotoCommentary) -> None:
    comments = load_comments()
    comments[comment.image_path] = comment
    write_text(COMMENTS_PATH, COMMENTS.dump_json(comments, indent=2).decode() + "\n")
    write_markdown()


def save_ad_comment(comment: AdCommentary) -> None:
    comments = load_ad_comments()
    comments[comment.profile_id] = comment
    write_text(AD_COMMENTS_PATH, AD_COMMENTS.dump_json(comments, indent=2).decode() + "\n")
    write_markdown()


def preview_video(video: Path) -> Path:
    """An H.264 copy of the ad that any browser can play; made once and reused."""

    preview = inside_sandbox(PREVIEW_DIR / f"{video.stem}_preview.mp4", OUTPUT_DIR)
    if not preview.is_file() or preview.stat().st_mtime < video.stat().st_mtime:
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-y", "-i", str(video),
                "-vf", "scale=1280:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(preview),
            ],
            check=True,
        )
    return preview


# --- markdown --------------------------------------------------------------


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _quote(text: str) -> str:
    text = text.strip()
    return "\n".join(f"> {line}" for line in text.splitlines()) if text else "> _No comment._"


def _product(row: EvaluationRow) -> str:
    ids = [row.agent_product_id] if row.agent_product_id else row.agent_candidate_ids
    return ", ".join(f"`{pid}`" for pid in ids) or "none"


def _commentary_lines(comment: PhotoCommentary | AdCommentary | None) -> list[str]:
    if comment is None:
        return ["", "_Not yet reviewed._"]
    lines = ["", f"**User commentary** (submitted {comment.submitted_at_utc})"]
    for key, question in QUESTIONS:
        lines += ["", f"*{question}*", "", _quote(getattr(comment, key))]
    return lines


def _step_lines(steps: list[AgentStep]) -> list[str]:
    return [f"  {n}. `{step.tool}` — {_cell(step.outcome)}" for n, step in enumerate(steps, 1)]


def evaluation_markdown(
    results: list[IdentifyResult],
    report: EvaluationReport,
    comments: dict[str, PhotoCommentary],
) -> str:
    rows = {row.image_path: row for row in report.rows}
    lines = [
        "# Agent evaluation",
        "",
        "## Part 1 — product identification",
        "",
        f"Run at {report.run_at_utc} with `{report.model}` by `evaluate.py`. The agent was given "
        "only the pixels of each photo. The \"actual\" column comes from the word \"true\" or "
        "\"false\" in the file name, which was read after the agent had answered.",
        "",
        "### Results: agent vs actual",
        "",
        "| Photo | Actual | Agent | Verdict | Product identified | Result | Cost |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.rows:
        lines.append(
            f"| `{Path(row.image_path).name}` | {'yes' if row.expected_product_in_photo else 'no'} "
            f"| {row.agent_answer} | {row.agent_verdict.replace('_', ' ')}, {row.confidence} "
            f"confidence | {_product(row)} | {'Correct' if row.correct else '**Wrong**'} "
            f"| ${row.cost_usd} |"
        )
    lines += [
        "",
        f"**{report.correct} of {report.total} correct.** Total cost ${report.total_cost_usd}.",
        "",
        "### Limits of this test",
        "",
        "- The file names say only whether a Campus Customs product is present, not which one.",
        "- Four photos is a small sample. It has no Yale garment that is absent from the "
        "catalogue, no colour variant, and no pair of products the agent could not separate, "
        "so the `possible_match` paths were not exercised.",
        "",
        "### Photo by photo, with the user's commentary",
        "",
        f"Commentary was entered by the user in the review form (`review_app.py`). "
        f"{len(comments)} of {len(results)} photos reviewed.",
    ]
    for result in results:
        row = rows[result.image_path]
        lines += ["", f"#### `{Path(result.image_path).name}`", ""]
        lines.append(
            f"- **Actual:** {'product present' if row.expected_product_in_photo else 'no product'}"
            f" · **Agent:** {result.verdict.replace('_', ' ')} ({result.confidence} confidence)"
            f" · **{'Correct' if row.correct else 'Wrong'}**"
        )
        seen = result.observed_garment.description if result.observed_garment else "No apparel to check."
        lines.append(f"- **What the agent saw:** {_cell(seen)}")
        if result.steps:
            lines += ["- **Steps it took:**", *_step_lines(result.steps)]
        else:
            lines.append("- **Steps it took:** answered from the photo alone; no catalogue search.")
        lines.append("- **Its reasons:** " + " ".join(_cell(reason) for reason in result.reasons))
        lines.append(
            "- **Sidebar:** "
            + (
                f"{result.matched_product.name} (`{result.matched_product.product_id}`), added to the cart."
                if result.matched_product
                else "possible matches: " + ", ".join(f"`{c.product_id}`" for c in result.candidate_products)
                if result.candidate_products
                else NOT_CARRIED + "."
            )
        )
        lines += _commentary_lines(comments.get(result.image_path))
    return "\n".join(lines) + "\n"


def ad_markdown(results: list[AdEffectivenessResult], comments: dict[str, AdCommentary]) -> str:
    if not results:
        return ""
    lines = [
        "",
        "## Part 2 — ad effectiveness runs",
        "",
        f"The agent judged `{results[0].video_path}` for {len(results)} customer profiles with "
        f"`{results[0].model}`. It saw 12 still frames of the ad and could not hear the audio. "
        "Both scores run from 0 to 10. There is no answer key for these runs; the user's "
        "commentary below is the evaluation.",
        "",
        "### Results by profile",
        "",
        "| Profile | Appropriateness | Effectiveness | Verdict | Confidence | Cost |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result.profile.label} (`{result.profile.profile_id}`) | "
            f"{result.appropriateness_score} | {result.effectiveness_score} | {result.verdict} | "
            f"{result.confidence} | ${result.cost.cost_usd} |"
        )
    products = ", ".join(f"`{p.product_id}`" for p in results[0].catalogue_products) or "none"
    lines += [
        "",
        f"Catalogue item identified in the ad: {products}.",
        "",
        "### Profile by profile, with the user's commentary",
        "",
        f"Commentary was entered by the user in the review form (`review_app.py`). "
        f"{sum(r.profile.profile_id in comments for r in results)} of {len(results)} runs reviewed.",
    ]
    for result in results:
        lines += ["", f"#### {result.profile.label} (`{result.profile_path}`)", ""]
        lines.append(
            f"- **Scores:** appropriateness {result.appropriateness_score} / 10 · effectiveness "
            f"{result.effectiveness_score} / 10 ({result.verdict}, {result.confidence} confidence)"
        )
        lines.append(f"- **What the agent saw:** {_cell(result.ad_summary)}")
        lines += ["- **Steps it took:**", *_step_lines(result.steps)]
        if result.products_reused_from_earlier_run:
            lines.append("  - Catalogue items were reused from the earlier identification of this video.")
        lines.append("- **Appropriateness reasons:**")
        lines += [f"  - {_cell(reason)}" for reason in result.appropriateness_reasons]
        lines.append("- **Fit with this customer:**")
        lines += [
            f"  - *{fit.effect.capitalize()}:* {_cell(fit.profile_trait)} — {_cell(fit.ad_element)}"
            for fit in result.profile_fit
        ]
        lines.append("- **Recommendations:** " + " ".join(_cell(r) for r in result.recommendations))
        lines.append("- **Limitations:** " + " ".join(_cell(r) for r in result.limitations))
        lines += _commentary_lines(comments.get(result.profile.profile_id))
    return "\n".join(lines) + "\n"


# --- pages -----------------------------------------------------------------

STYLE = """
  :root { --desk:#1b1410; --leather:#2a1d16; --oak:#3b2a1e; --brass:#c9a227; --glass:#4fa97c;
          --cream:#f5e6c8; --muted:#b9ad93; --rule:#5a4330; --wrong:#ff8a80; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--desk); color:var(--cream); font:16px/1.55 Georgia, serif; }
  .layout { display:grid; grid-template-columns:minmax(0,1fr) 360px; min-height:100vh; }
  main { padding:26px 24px 40px; max-width:900px; }
  aside { background:var(--leather); border-left:2px solid var(--brass); padding:24px 20px; }
  h1 { margin:0; color:var(--brass); font-size:25px; }
  h2 { margin:22px 0 8px; color:var(--glass); font-size:14px; letter-spacing:1.2px; text-transform:uppercase; }
  aside h2 { margin-top:0; }
  h3 { margin:10px 0 2px; font-size:18px; }
  a { color:var(--brass); }
  .steps { display:flex; gap:8px; margin:12px 0 14px; padding:0; list-style:none; flex-wrap:wrap; }
  .steps a, .steps span { display:block; padding:3px 12px; border:1px solid var(--rule); border-radius:12px;
      font-size:14px; text-decoration:none; color:var(--muted); }
  .steps .part { border:0; padding-left:0; color:var(--glass); text-transform:uppercase; letter-spacing:1px; font-size:12px; }
  .steps .here { border-color:var(--brass); color:var(--brass); }
  .steps .done::after { content:" \\2713"; color:var(--glass); }
  .chips span { display:inline-block; margin:0 8px 8px 0; padding:3px 12px; border-radius:14px;
      border:1px solid var(--rule); font-size:14px; }
  .chips .ok { background:var(--glass); color:#10231a; border-color:var(--glass); }
  .chips .bad { background:var(--wrong); color:#2b0b08; border-color:var(--wrong); }
  .photo, video, .sheet { width:100%; border:1px solid var(--rule); border-radius:6px; display:block; }
  .photo { max-width:640px; }
  video { background:#000; }
  ol, ul { padding-left:22px; margin:6px 0; } li { margin-bottom:6px; }
  code { font:13px Consolas, monospace; color:var(--brass); }
  .muted, .meta, .note { color:var(--muted); font-size:14px; }
  .helps { color:var(--glass); } .hurts { color:var(--wrong); }
  details { margin:8px 0; padding:8px 12px; border:1px solid var(--rule); border-radius:6px; }
  summary { cursor:pointer; color:var(--brass); }
  .meters { display:flex; flex-wrap:wrap; gap:18px; margin:6px 0; }
  .meter { width:300px; max-width:100%; margin:0; }
  .meter svg { width:100%; height:auto; display:block; }
  .meter figcaption { margin-top:6px; color:var(--muted); font-size:14px; }
  form { margin-top:8px; padding:18px; background:var(--leather); border:1px solid var(--brass); border-radius:6px; }
  label { display:block; margin:14px 0 5px; }
  label:first-of-type { margin-top:0; }
  textarea { width:100%; min-height:78px; padding:9px; background:var(--oak); color:var(--cream);
      border:1px solid var(--rule); border-radius:4px; font:15px/1.45 Georgia, serif; resize:vertical; }
  textarea:focus { outline:2px solid var(--glass); outline-offset:1px; }
  .submit { margin-top:16px; padding:11px 26px; font:inherit; font-weight:bold; cursor:pointer;
      background:var(--brass); color:#1b1410; border:0; border-radius:4px; }
  .submit:focus { outline:2px solid var(--glass); outline-offset:2px; }
  .card { background:var(--oak); border:1px solid var(--rule); border-radius:6px; padding:14px; margin-bottom:16px; }
  .card img { width:100%; background:#fff; border-radius:4px; display:block; }
  .badge { display:inline-block; margin-top:10px; padding:1px 10px; border-radius:10px; font-size:12px;
      letter-spacing:.8px; text-transform:uppercase; background:var(--glass); color:#10231a; }
  .id { font:12px Consolas, monospace; color:var(--muted); margin:8px 0 0; }
  .none { padding:16px; border:1px dashed var(--brass); border-radius:6px; color:var(--brass);
      font-size:17px; margin-bottom:16px; }
  .cart ul { padding:0; margin:0 0 12px; }
  .cart li { list-style:none; margin:0 0 8px; padding:8px 10px; border:1px solid var(--rule); border-radius:4px; }
  .cart button { width:100%; padding:11px; font:inherit; border-radius:4px; border:1px solid var(--rule);
      background:#2c2420; color:var(--muted); cursor:not-allowed; }
  table { border-collapse:collapse; width:100%; margin:12px 0; }
  th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--rule); }
  th { color:var(--brass); font-size:13px; text-transform:uppercase; letter-spacing:.8px; }
  @media (max-width:860px) { .layout { grid-template-columns:1fr; }
    aside { border-left:0; border-top:2px solid var(--brass); } }
"""


def page(title: str, body: str) -> bytes:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head><body>{body}</body></html>"
    ).encode("utf-8")


def progress(current: str) -> str:
    """Navigation across both parts; `current` is the path of the page being shown."""

    results, _ = load_results()
    comments, ad_comments = load_comments(), load_ad_comments()

    def item(path: str, text: str, done: bool) -> str:
        classes = " ".join(n for n, on in (("here", path == current), ("done", done)) if on)
        return f'<li><a class="{classes}" href="{path}">{html.escape(text)}</a></li>'

    items = ['<li><span class="part">Photos</span></li>']
    items += [
        item(f"/photo/{i}", f"Photo {i + 1}", r.image_path in comments) for i, r in enumerate(results)
    ]
    ads = load_ad_results()
    if ads:
        items.append('<li><span class="part">Ad</span></li>')
        items += [
            item(f"/ad/{i}", r.profile.profile_id.replace("_", " "), r.profile.profile_id in ad_comments)
            for i, r in enumerate(ads)
        ]
    items.append(item("/done", "Summary", False))
    return f'<ul class="steps" aria-label="Review progress">{"".join(items)}</ul>'


def cart_html(cart: Cart) -> str:
    e = html.escape
    lines = (
        "<ul>"
        + "".join(
            f"<li>{e(item.name)}<div class='muted'>Qty {item.quantity} &middot; size not chosen "
            "&middot; price shown at checkout</div></li>"
            for item in cart.items
        )
        + "</ul>"
        if cart.items
        else '<p class="muted">The cart is empty.</p>'
    )
    return (
        f'<section class="cart"><h2>Shopping cart ({len(cart.items)})</h2>{lines}'
        '<button type="button" disabled aria-disabled="true">Checkout unavailable</button>'
        f'<p class="note">{e(cart.note)}</p></section>'
    )


def sidebar(result: IdentifyResult) -> str:
    if result.matched_product:
        title, cards = "Matched product", card_html(result.matched_product, "In your cart")
    elif result.candidate_products:
        notes = {c.product_id: c.differences for c in result.candidates}
        title = "Possible matches"
        cards = "".join(
            card_html(card, "Possible match", notes.get(card.product_id, ""))
            for card in result.candidate_products
        )
    else:
        title, cards = "Catalogue item", f'<p class="none">{html.escape(NOT_CARRIED)}</p>'
    return (
        f'<aside aria-label="Catalogue item and shopping cart"><h2>{title}</h2>{cards}'
        f"{cart_html(result.cart)}</aside>"
    )


def ad_sidebar(result: AdEffectivenessResult) -> str:
    in_cart = {item.product_id for item in result.cart.items}
    notes = {match.product_id: match for match in result.catalogue_products}
    cards = "".join(
        card_html(
            card,
            "In your cart" if card.product_id in in_cart else "Possible match",
            f"Seen at {notes[card.product_id].seen_at_seconds:.1f}s. {notes[card.product_id].reason}",
        )
        for card in result.identified_products
    ) or f'<p class="none">{html.escape(NOT_CARRIED)}</p>'
    return (
        '<aside aria-label="Catalogue item and shopping cart"><h2>Catalogue item in the ad</h2>'
        f"{cards}{cart_html(result.cart)}</aside>"
    )


def steps_html(steps: list[AgentStep], none_text: str) -> str:
    e = html.escape
    if not steps:
        return f"<p>{e(none_text)}</p>"
    return (
        "<ol>"
        + "".join(
            f"<li><code>{e(step.tool)}</code> "
            f"<span class='muted'>{e(', '.join(f'{k}={v}' for k, v in step.arguments.items()))}</span>"
            f"<br>{e(step.outcome)}</li>"
            for step in steps
        )
        + "</ol>"
    )


def comment_form(action: str, saved: PhotoCommentary | AdCommentary | None, button: str) -> str:
    e = html.escape
    fields = "".join(
        f'<label for="{key}">{e(question)}</label>'
        f'<textarea id="{key}" name="{key}" maxlength="{MAX_FIELD_CHARACTERS}">'
        f"{e(getattr(saved, key) if saved else '')}</textarea>"
        for key, question in QUESTIONS
    )
    note = (
        "Already submitted; submitting again replaces it."
        if saved
        else "Saved to output/agent_evaluation.md."
    )
    return (
        f'<form method="post" action="{action}">{fields}'
        f'<button class="submit" type="submit">{e(button)}</button>'
        f'<span class="muted">&nbsp;{note}</span></form>'
    )


def photo_page(index: int) -> bytes:
    results, report = load_results()
    result = results[index]
    row = {r.image_path: r for r in report.rows}[result.image_path]
    saved = load_comments().get(result.image_path)
    e = html.escape
    seen = result.observed_garment
    seen_html = (
        f"<p>{e(seen.description)}</p><p class='muted'>Printed text read: "
        f"{e(' / '.join(seen.printed_text) or 'none')}</p>"
        if seen
        else "<p>No apparel to check.</p>"
    )
    last = index == len(results) - 1
    button = "Submit and show next photo" if not last else (
        "Submit and go on to the ad" if load_ad_results() else "Submit and finish"
    )
    body = f"""
<div class="layout"><main>
  <h1>Agent evaluation: photos</h1>
  {progress(f"/photo/{index}")}
  <div class="chips">
    <span>{e(Path(result.image_path).name)}</span>
    <span>Actual: {'product present' if row.expected_product_in_photo else 'no product'}</span>
    <span>Agent: {e(result.verdict.replace('_', ' '))}, {e(result.confidence)} confidence</span>
    <span class="{'ok' if row.correct else 'bad'}">{'Correct' if row.correct else 'Wrong'}</span>
  </div>
  <img class="photo" src="{data_uri(PROJECT_DIR / result.image_path, 900)}" alt="Test photo {index + 1}">
  <h2>What the agent saw</h2>{seen_html}
  <h2>Steps it took</h2>{steps_html(result.steps, "It answered from the photo alone. No catalogue search was needed.")}
  <h2>Its reasons</h2><ul>{''.join(f'<li>{e(reason)}</li>' for reason in result.reasons)}</ul>
  {f'<p><strong>Question it asked:</strong> {e(result.question_for_user)}</p>' if result.question_for_user else ''}
  <p class="muted">{result.cost.requests} model request(s), {len(result.reference_images_viewed)} of 102
     catalogue photos opened, ${e(result.cost.cost_usd or '?')}. The agent's private reasoning is not
     recorded; these are its tool calls and stated reasons.</p>
  <h2>Your comments on this photo</h2>
  {comment_form(f"/photo/{index}", saved, button)}
</main>{sidebar(result)}</div>"""
    return page(f"Agent evaluation: photo {index + 1}", body)


def ad_page(index: int) -> bytes:
    results = load_ad_results()
    result = results[index]
    profile = result.profile
    saved = load_ad_comments().get(profile.profile_id)
    e = html.escape

    def bullets(items: list[str]) -> str:
        return "<ul>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"

    profile_details = "".join(
        f"<p><strong>{e(name.replace('_', ' ').capitalize())}:</strong> "
        f"{e('; '.join(value) if isinstance(value, list) else str(value))}</p>"
        for name, value in profile.model_dump().items()
        if name not in ("profile_id", "label", "summary")
    )
    sheets = "".join(
        f'<img class="sheet" src="{data_uri(PROJECT_DIR / sheet, 1792)}" '
        f'alt="The 12 frames of the ad that the agent saw">'
        for sheet in result.video.frame_sheets
    )
    fit = "".join(
        f'<li><strong class="{e(item.effect)}">{e(item.effect.capitalize())}:</strong> '
        f"{e(item.profile_trait)} <span class='muted'>&mdash; {e(item.ad_element)}</span></li>"
        for item in result.profile_fit
    )
    reused = (
        "<p class='muted'>The catalogue item was identified on the first run for this video and "
        "reused here, so this run made no catalogue search.</p>"
        if result.products_reused_from_earlier_run
        else ""
    )
    last = index == len(results) - 1
    body = f"""
<div class="layout"><main>
  <h1>Agent evaluation: ad for {e(profile.label)}</h1>
  {progress(f"/ad/{index}")}
  <div class="chips">
    <span>{e(Path(result.video_path).name)}</span>
    <span>Profile {index + 1} of {len(results)}: {e(profile.profile_id)}</span>
    <span>Agent: {e(result.verdict)}, {e(result.confidence)} confidence</span>
  </div>
  <h2>The customer</h2>
  <p>{e(profile.summary)}</p>
  <details><summary>Full profile ({e(result.profile_path)})</summary>{profile_details}</details>
  <h2>The ad</h2>
  <video controls preload="metadata" src="/video/{index}" aria-label="The Campus Customs ad"></video>
  <p class="muted">{result.video.duration_seconds:.1f} seconds. You can hear the audio here; the agent could not.</p>
  <h2>The {result.video.frames_sampled} frames the agent saw</h2>{sheets}
  <h2>The agent's scores</h2>
  <div class="meters">{meter_svg("Appropriateness", result.appropriateness_score)}
     {meter_svg("Effectiveness", result.effectiveness_score)}</div>
  <h2>What the agent saw</h2><p>{e(result.ad_summary)}</p>
  {bullets([f"{m.timestamp_seconds:.1f}s: {m.observation}" for m in result.key_moments])}
  <h2>Steps it took</h2>{steps_html(result.steps, "No tool calls were recorded.")}{reused}
  <h2>Why it scored appropriateness {result.appropriateness_score}</h2>{bullets(result.appropriateness_reasons)}
  <h2>Fit with this customer (effectiveness {result.effectiveness_score})</h2><ul>{fit}</ul>
  <h2>Its recommendations</h2>{bullets(result.recommendations)}
  <h2>Limitations it stated</h2>{bullets(result.limitations)}
  <p class="muted">{result.cost.requests} model request(s), ${e(result.cost.cost_usd or '?')}. The agent's
     private reasoning is not recorded; these are its tool calls and stated reasons.</p>
  <h2>Your comments on this judgement</h2>
  {comment_form(f"/ad/{index}", saved, "Submit and finish" if last else "Submit and show next profile")}
</main>{ad_sidebar(result)}</div>"""
    return page(f"Agent evaluation: ad for {profile.profile_id}", body)


def done_page() -> bytes:
    results, report = load_results()
    comments, ad_comments = load_comments(), load_ad_comments()
    ads = load_ad_results()
    e = html.escape
    rows = "".join(
        f"<tr><td><a href='/photo/{index}'>{e(Path(row.image_path).name)}</a></td>"
        f"<td>{'yes' if row.expected_product_in_photo else 'no'}</td><td>{e(row.agent_answer)}</td>"
        f"<td>{e(row.agent_product_id or '-')}</td><td>{'Correct' if row.correct else 'Wrong'}</td>"
        f"<td>{'Reviewed' if row.image_path in comments else 'Not reviewed'}</td></tr>"
        for index, row in enumerate(report.rows)
    )
    ad_rows = "".join(
        f"<tr><td><a href='/ad/{index}'>{e(result.profile.label)}</a></td>"
        f"<td>{result.appropriateness_score}</td><td>{result.effectiveness_score}</td>"
        f"<td>{e(result.verdict)}</td>"
        f"<td>{'Reviewed' if result.profile.profile_id in ad_comments else 'Not reviewed'}</td></tr>"
        for index, result in enumerate(ads)
    )
    ad_table = (
        f"<h2>Ad runs: {len(ad_comments)} of {len(ads)} reviewed</h2>"
        "<table><thead><tr><th>Profile</th><th>Appropriateness</th><th>Effectiveness</th>"
        f"<th>Verdict</th><th>Your review</th></tr></thead><tbody>{ad_rows}</tbody></table>"
        if ads
        else ""
    )
    body = f"""
<main style="margin:0 auto">
  <h1>Agent evaluation</h1>
  {progress("/done")}
  <p>Your commentary is saved in <code>output/agent_evaluation.md</code>.</p>
  <h2>Photos: {len(comments)} of {len(results)} reviewed, agent correct on {report.correct} of {report.total}</h2>
  <table><thead><tr><th>Photo</th><th>Actual</th><th>Agent</th><th>Product</th><th>Result</th>
  <th>Your review</th></tr></thead><tbody>{rows}</tbody></table>
  {ad_table}
  <p class="muted">Select an item to read or change your comments.</p>
</main>"""
    return page("Agent evaluation: summary", body)


# --- server ----------------------------------------------------------------


def _form_fields(form: dict[str, list[str]]) -> dict[str, str]:
    return {
        key: form.get(key, [""])[0].replace("\r\n", "\n").strip()[:MAX_FIELD_CHARACTERS]
        for key, _ in QUESTIONS
    }


class ReviewHandler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _index(self, kind: str, count: int) -> int | None:
        parts = self.path.split("?")[0].strip("/").split("/")
        if len(parts) == 2 and parts[0] == kind and parts[1].isdigit() and int(parts[1]) < count:
            return int(parts[1])
        return None

    def _send_video(self, video: Path) -> None:
        """Serve the preview with byte ranges so the player can seek."""

        data = preview_video(video).read_bytes()
        start, end = 0, len(data) - 1
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        if match and (match.group(1) or match.group(2)):
            if match.group(1):
                start = int(match.group(1))
                end = min(int(match.group(2)), end) if match.group(2) else end
            else:
                start = max(0, len(data) - int(match.group(2)))
            if start > end:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{len(data)}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        try:
            self.wfile.write(data[start : end + 1])
        except (BrokenPipeError, ConnectionError):
            pass  # The player closed the connection after getting what it needed.

    def do_GET(self) -> None:  # noqa: N802 - name required by http.server
        path = self.path.split("?")[0]
        photos, _ = load_results()
        ads = load_ad_results()
        if path == "/":
            comments, ad_comments = load_comments(), load_ad_comments()
            pending = [f"/photo/{i}" for i, r in enumerate(photos) if r.image_path not in comments]
            pending += [f"/ad/{i}" for i, r in enumerate(ads) if r.profile.profile_id not in ad_comments]
            self._redirect(pending[0] if pending else "/done")
        elif path == "/done":
            self._send(done_page())
        elif (index := self._index("photo", len(photos))) is not None:
            self._send(photo_page(index))
        elif (index := self._index("ad", len(ads))) is not None:
            self._send(ad_page(index))
        elif (index := self._index("video", len(ads))) is not None:
            self._send_video(PROJECT_DIR / ads[index].video_path)
        else:
            self._send(page("Not found", "<main><h1>Not found</h1><p><a href='/'>Back</a></p></main>"), 404)

    def do_POST(self) -> None:  # noqa: N802 - name required by http.server
        photos, _ = load_results()
        ads = load_ad_results()
        photo, ad = self._index("photo", len(photos)), self._index("ad", len(ads))
        length = int(self.headers.get("Content-Length") or 0)
        if (photo is None and ad is None) or not 0 <= length <= MAX_BODY_BYTES:
            self._send(page("Rejected", "<main><h1>Request rejected</h1></main>"), 400)
            return
        form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"), keep_blank_values=True)
        if photo is not None:
            save_comment(
                PhotoCommentary(
                    image_path=photos[photo].image_path, submitted_at_utc=now_iso(), **_form_fields(form)
                )
            )
            after = "/ad/0" if ads else "/done"
            self._redirect(f"/photo/{photo + 1}" if photo + 1 < len(photos) else after)
        else:
            save_ad_comment(
                AdCommentary(
                    profile_id=ads[ad].profile.profile_id,
                    video_path=ads[ad].video_path,
                    submitted_at_utc=now_iso(),
                    **_form_fields(form),
                )
            )
            self._redirect(f"/ad/{ad + 1}" if ad + 1 < len(ads) else "/done")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        print(f"{self.command} {self.path.split('?')[0]}", flush=True)


def export_static() -> list[Path]:
    """Save the review pages as plain HTML files in output/, with the comments as submitted.

    The saved copies open without the server: links point at the other saved pages, the ad
    plays from output/ad_preview/, and the comment boxes are read-only.
    """

    photos, _ = load_results()
    ads = load_ad_results()
    names = {f"/photo/{i}": f"review_photo_{i + 1}.html" for i in range(len(photos))}
    names |= {f"/ad/{i}": f"review_ad_{ad.profile.profile_id}.html" for i, ad in enumerate(ads)}
    names["/done"] = "review_summary.html"
    pages = {f"/photo/{i}": photo_page(i) for i in range(len(photos))}
    pages |= {f"/ad/{i}": ad_page(i) for i in range(len(ads))}
    pages["/done"] = done_page()

    written = []
    for route, body in pages.items():
        text = body.decode("utf-8")
        text = re.sub(r"""href=(["'])(/(?:photo|ad)/\d+|/done)\1""",
                      lambda m: f'href="{names[m.group(2)]}"', text)
        for index, ad in enumerate(ads):
            preview = preview_video(PROJECT_DIR / ad.video_path).relative_to(OUTPUT_DIR).as_posix()
            text = text.replace(f'src="/video/{index}"', f'src="{preview}"')
        text = re.sub(r'<form method="post" action="[^"]*">', '<form onsubmit="return false">', text)
        text = text.replace("<textarea ", "<textarea readonly ")
        text = re.sub(
            r'<button class="submit" type="submit">.*?</button><span class="muted">.*?</span>',
            '<p class="muted">Saved copy of the review form. These are the comments as submitted; '
            "run review_app.py to edit them.</p>",
            text,
            flags=re.S,
        )
        path = OUTPUT_DIR / names[route]
        write_text(path, text)
        written.append(path)
    return written


def main() -> int:
    if not IDENTIFY_OUTPUT_PATH.is_file() or not EVALUATION_PATH.is_file():
        print("Run evaluate.py first.", file=sys.stderr)
        return 2
    if "--export" in sys.argv[1:]:
        write_markdown()
        for path in export_static():
            print(f"Wrote {path.relative_to(PROJECT_DIR).as_posix()}")
        return 0
    for result in load_ad_results():
        preview_video(PROJECT_DIR / result.video_path)
    write_markdown()
    server = ThreadingHTTPServer((HOST, PORT), ReviewHandler)
    print(f"Review form: http://{HOST}:{PORT}  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
