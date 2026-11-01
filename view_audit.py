"""Write output/audit_trail.html: the safety rules beside the audit trail that shows them at work."""

from __future__ import annotations

import html
import re
from decimal import Decimal
from itertools import groupby

from agent import PROMPT_PATH
from config import MAX_LOOP_USD, OUTPUT_DIR, PROJECT_DIR
from models import AuditEntry
from tools import AUDIT_PATH, MAX_REFERENCE_IMAGES, load_audit, write_text

PAGE_PATH = OUTPUT_DIR / "audit_trail.html"
ALLOWED_TOOLS = {
    "identify": {"search_catalogue", "view_catalogue_images", "add_to_cart"},
    "ad": {"read_customer_profile", "watch_ad_video", "search_catalogue", "view_catalogue_images"},
}
CODE_SAFEGUARDS = [
    ("Files are checked before the agent starts",
     "A photo or video must be inside data/ and a profile inside profiles/, of an allowed type "
     "and size. Anything else is refused and logged as input_rejected with no model call."),
    ("Hidden data is stripped from images",
     "Every photo is re-encoded before it is sent, which drops embedded metadata such as GPS "
     "position, camera, and capture time."),
    ("Photo file names are not shown to the agent",
     "In photo identification the agent receives pixels only, never the file name or path."),
    ("The agent can only call the tools it was given",
     "There is no tool to send a message, look anyone up, browse the web, save an image, or "
     "check out a cart."),
    ("Answers are held to a fixed shape",
     "The answer must fit the structured model, which has no field for a person's name or "
     "traits. Safety flags come from a fixed list."),
    ("Every loop has a spending cap",
     f"Request, tool-call, and token limits keep each run under ${MAX_LOOP_USD}."),
    ("Every step is written to the audit trail as it happens",
     "Entries are appended, never overwritten, including runs that are refused or stopped."),
]

STYLE = """
  :root { --desk:#1b1410; --leather:#2a1d16; --oak:#3b2a1e; --brass:#c9a227; --glass:#4fa97c;
          --cream:#f5e6c8; --muted:#b9ad93; --rule:#5a4330; --wrong:#ff8a80; }
  * { box-sizing:border-box; }
  body { margin:0; padding:26px 20px 60px; background:var(--desk); color:var(--cream);
         font:16px/1.55 Georgia, serif; }
  .wrap { max-width:1150px; margin:0 auto; }
  h1 { margin:0 0 4px; color:var(--brass); font-size:27px; }
  h2 { margin:34px 0 10px; color:var(--brass); font-size:21px; border-bottom:1px solid var(--rule); padding-bottom:6px; }
  h3 { margin:18px 0 6px; color:var(--glass); font-size:14px; letter-spacing:1.2px; text-transform:uppercase; }
  .muted { color:var(--muted); font-size:14px; }
  code { font:13px Consolas, monospace; color:var(--brass); }
  .cols { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr)); gap:18px; }
  .panel { min-width:0; background:var(--leather); border:1px solid var(--rule); border-radius:6px; padding:6px 18px 14px; }
  .panel.must { border-top:4px solid var(--glass); } .panel.mustnot { border-top:4px solid var(--wrong); }
  ol { padding-left:22px; margin:6px 0; } ol li { margin-bottom:9px; }
  dl { margin:0; } dt { color:var(--cream); font-weight:bold; margin-top:10px; } dd { margin:2px 0 0; color:var(--muted); }
  .run { background:var(--leather); border:1px solid var(--rule); border-left:4px solid var(--brass);
         border-radius:6px; padding:14px 18px; margin:18px 0; }
  .run.bad { border-left-color:var(--wrong); }
  .run h3 { margin-top:0; color:var(--cream); font-size:17px; letter-spacing:0; text-transform:none; }
  .chips span { display:inline-block; margin:0 8px 8px 0; padding:2px 11px; border-radius:13px;
      border:1px solid var(--rule); font-size:13px; }
  .chips .ok { background:var(--glass); color:#10231a; border-color:var(--glass); }
  .chips .stop { background:var(--wrong); color:#2b0b08; border-color:var(--wrong); }
  ul.checks { list-style:none; padding:0; margin:6px 0 12px; }
  ul.checks li { padding:3px 0 3px 26px; position:relative; }
  ul.checks li::before { position:absolute; left:0; font-weight:bold; }
  ul.checks li.pass::before { content:"\\2713"; color:var(--glass); }
  ul.checks li.fail::before { content:"\\2717"; color:var(--wrong); }
  ul.checks li.info::before { content:"\\2022"; color:var(--brass); }
  .scroll { overflow-x:auto; }
  table { border-collapse:collapse; width:100%; min-width:900px; font-size:14px; }
  th { text-align:left; color:var(--brass); font-size:12px; text-transform:uppercase; letter-spacing:.8px;
       padding:7px 9px; background:var(--oak); white-space:nowrap; }
  td { padding:8px 9px; border-top:1px solid var(--rule); vertical-align:top; }
  td.n, td.t { white-space:nowrap; color:var(--muted); }
  .tool { margin:0 0 6px; } .args { color:var(--muted); font:12px Consolas, monospace; word-break:break-word; }
  .stopmsg { color:var(--wrong); }
"""


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", text)


def safety_rules_html() -> str:
    """The safety section exactly as the agent receives it, laid out as two panels."""

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    section = prompt.split("<!-- SAFETY RULES: START -->")[1].split("<!-- SAFETY RULES: END -->")[0]
    intro, *parts = re.split(r"\n### ", section)
    intro_text = " ".join(line for line in intro.splitlines() if line and not line.startswith("## "))
    panels = ""
    for part in parts:
        title, _, body = part.partition("\n")
        items = re.split(r"\n(?=\d+\. )", body.strip())
        rules = "".join(
            f"<li>{inline(' '.join(re.sub(r'^\d+\. ', '', item).split()))}</li>" for item in items
        )
        kind = "mustnot" if "not" in title.lower() else "must"
        panels += f'<section class="panel {kind}"><h3>{html.escape(title.strip())}</h3><ol>{rules}</ol></section>'
    return f"<p>{inline(intro_text)}</p><div class='cols'>{panels}</div>"


def rule_checks(entries: list[AuditEntry]) -> list[tuple[str, str]]:
    """Checks that can be read straight off a run's audit entries: (pass|fail|info, text)."""

    first, last = entries[0], entries[-1]
    if last.stop_reason == "input_rejected":
        return [
            ("pass", "Refused by a code check before any model call; no tokens were spent."),
            ("info", f"Reason recorded: {last.stop_message}"),
        ]
    checks: list[tuple[str, str]] = []
    called = [call.name for entry in entries for call in entry.tool_calls
              if not call.name.startswith("final_result")]
    extra = set(called) - ALLOWED_TOOLS[first.task]
    checks.append(
        ("fail", f"Called tools outside its permitted set: {sorted(extra)}")
        if extra
        else ("pass", "Called only its permitted tools: " + (", ".join(dict.fromkeys(called)) or "none")
              + ". No contact, lookup, or checkout tool exists.")
    )
    if first.task == "identify":
        name = first.subject.rsplit("/", 1)[-1]
        leaked = any(name in thought for thought in first.thoughts)
        checks.append(
            ("fail", "The photo's file name appears in the request sent to the agent.")
            if leaked
            else ("pass", "The request sent to the agent contains the image only, not its file name.")
        )
        opened = sum(
            len(str(call.args.get("product_ids", "")).split())
            for entry in entries for call in entry.tool_calls if call.name == "view_catalogue_images"
        )
        checks.append(
            ("pass" if opened <= MAX_REFERENCE_IMAGES else "fail",
             f"Opened {opened} catalogue reference photo(s); the limit is {MAX_REFERENCE_IMAGES}.")
        )
    cost = Decimal(last.usage_so_far.cost_usd or "0")
    checks.append(
        ("pass" if cost <= MAX_LOOP_USD else "fail",
         f"Spent ${cost} in {last.usage_so_far.requests} request(s); the cap is ${MAX_LOOP_USD}.")
    )
    flags = [flag for entry in entries for flag in entry.safety_flags]
    checks.append(
        ("info", "Safety flags raised by the agent: " + ", ".join(flags))
        if flags
        else ("info", "The agent raised no safety flags on this run.")
    )
    if last.stop_reason == "finished":
        checks.append(("pass", f"Ended normally: {last.stop_message}"))
    else:
        checks.append(("fail", f"Stopped early ({last.stop_reason}): {last.stop_message}"))
    return checks


def run_html(number: int, entries: list[AuditEntry]) -> str:
    e = html.escape
    first, last = entries[0], entries[-1]
    finished = last.stop_reason == "finished"
    rows = ""
    for entry in entries:
        calls = "".join(
            f'<p class="tool"><code>{e(call.name)}</code><br><span class="args">'
            f"{e(', '.join(f'{k}={v}' for k, v in call.args.items()))}</span></p>"
            for call in entry.tool_calls
        )
        results = "".join(
            f'<p class="tool"><code>{e(result.name)}</code><br><span class="args">{e(result.result)}</span></p>'
            for result in entry.tool_results
        ) + "".join(f'<p class="tool stopmsg">Rejected: {e(retry)}</p>' for retry in entry.retries)
        stop = (
            f'<br><span class="{"" if entry.stop_reason == "finished" else "stopmsg"}">'
            f"<strong>{e(entry.stop_reason)}</strong>: {e(entry.stop_message or '')}</span>"
            if entry.stop_reason
            else ""
        )
        rows += (
            f'<tr><td class="n">{entry.iteration}</td><td class="t">{e(entry.timestamp_utc[11:19])}</td>'
            f"<td>{e(entry.event.replace('_', ' '))}</td>"
            f"<td>{'<br>'.join(e(thought) for thought in entry.thoughts)}{stop}</td>"
            f"<td>{calls}</td><td>{results}</td>"
            f'<td class="n">{entry.usage_so_far.requests} req<br>{entry.usage_so_far.input_tokens:,} in<br>'
            f"{entry.usage_so_far.output_tokens:,} out<br>${e(entry.usage_so_far.cost_usd or '?')}</td></tr>"
        )
    checks = "".join(f'<li class="{kind}">{e(text)}</li>' for kind, text in rule_checks(entries))
    return f"""
<section class="run {'' if finished else 'bad'}">
  <h3>Run {number}: {e('Photo identification' if first.task == 'identify' else 'Ad effectiveness')}</h3>
  <div class="chips"><span>{e(first.subject)}</span><span>{e(first.timestamp_utc)}</span>
    <span>{e(first.model)}</span><span>run id {e(first.run_id)}</span>
    <span class="{'ok' if finished else 'stop'}">{e(last.stop_reason or 'no stop recorded')}</span></div>
  <h3>Rules shown by this run</h3><ul class="checks">{checks}</ul>
  <h3>Loop iterations ({len(entries)})</h3>
  <div class="scroll"><table><thead><tr><th>#</th><th>Time (UTC)</th><th>Event</th><th>Thoughts and stop reason</th>
  <th>Tool calls and arguments</th><th>Tool results</th><th>Usage so far</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
</section>"""


def main() -> None:
    entries = load_audit()
    runs = [list(group) for _, group in groupby(entries, key=lambda entry: entry.run_id)]
    safeguards = "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>" for t, d in CODE_SAFEGUARDS)
    body = f"""<div class="wrap">
<h1>Campus Customs agent: safety rules and audit trail</h1>
<p class="muted">{len(entries)} entries from {len(runs)} runs in
  <code>{html.escape(AUDIT_PATH.relative_to(PROJECT_DIR).as_posix())}</code>. Newest run last.</p>
<h2>1. Safety rules the agent is given</h2>
<p class="muted">Loaded from the marked safety section of <code>prompts/prompt.md</code> into the system
  prompt of every run.</p>
{safety_rules_html()}
<h2>2. Safeguards enforced in code</h2>
<p class="muted">These do not rely on the agent choosing to comply.</p>
<div class="panel"><dl>{safeguards}</dl></div>
<h2>3. The audit trail</h2>
<p class="muted">One row per agent-loop iteration, written as the agent ran. "Thoughts" are what the agent
  said plus a plain statement of what it decided; the model's private reasoning is not available.</p>
{''.join(run_html(number, run) for number, run in enumerate(runs, start=1))}
</div>"""
    write_text(
        PAGE_PATH,
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Safety rules and audit trail</title><style>{STYLE}</style></head><body>{body}</body></html>",
    )
    print(f"Wrote {PAGE_PATH.relative_to(PROJECT_DIR).as_posix()} ({len(entries)} entries, {len(runs)} runs)")


if __name__ == "__main__":
    main()
