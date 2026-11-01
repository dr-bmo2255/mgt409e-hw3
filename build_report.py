"""Write output/harness_report.html from output/harness.md.

The page opens with an executive summary and headline figures, then offers every section of
the harness document as a fold-out, so a reader can go as deep as they want.
"""

from __future__ import annotations

import html
import json
import math
import re

from agent import load_ad_results
from config import CATALOGUE_JSON_PATH, OUTPUT_DIR, PROJECT_DIR
from evaluate import EVALUATION_PATH
from tools import load_audit, meter_svg, write_text

HARNESS_PATH = OUTPUT_DIR / "harness.md"
REPORT_PATH = OUTPUT_DIR / "harness_report.html"
LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")

# --- markdown to HTML (covers what harness.md uses) -------------------------


def inline(text: str) -> str:
    """Escape, then apply code spans, bold, and emphasis. Code spans are left untouched."""

    spans: list[str] = []

    def hold(match: re.Match[str]) -> str:
        spans.append(f"<code>{match.group(1)}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", hold, html.escape(text.replace("\\|", "|")))
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda match: spans[int(match.group(1))], text)


def render_list(lines: list[str]) -> str:
    """Nested ordered and unordered lists; indented lines continue the item above."""

    out: list[str] = []
    stack: list[tuple[int, str]] = []  # (indent, tag)
    text: list[str] = []  # the current item's wrapped lines, formatted together

    def flush() -> None:
        if text:
            out.append(inline(" ".join(text)))
            text.clear()

    for line in lines:
        match = LIST_ITEM.match(line)
        if not match:
            text.append(line.strip())
            continue
        flush()
        indent, tag = len(match.group(1)), "ul" if match.group(2) in "-*" else "ol"
        while stack and stack[-1][0] > indent:
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and stack[-1][0] == indent:
            out.append("</li>")
        else:
            stack.append((indent, tag))
            out.append(f"<{tag}>")
        out.append("<li>")
        text.append(match.group(3))
    flush()
    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


def render_table(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))] for line in lines]
    head, body = rows[0], rows[2:]
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{inline(cell)}</th>" for cell in head)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in body)
        + "</tbody></table></div>"
    )


def render(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1 : j])) + "</code></pre>")
            i = j + 1
        elif match := re.match(r"^(#{3,4})\s+(.*)$", line):
            level = len(match.group(1))
            out.append(f"<h{level}>{inline(match.group(2))}</h{level}>")
            i += 1
        elif line.startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            out.append(render_table(lines[i:j]))
            i = j
        elif line.startswith(">"):
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                j += 1
            quoted = "\n".join(re.sub(r"^> ?", "", quote) for quote in lines[i:j])
            out.append(f"<blockquote>{render(quoted)}</blockquote>")
            i = j
        elif LIST_ITEM.match(line):
            j = i
            while j < len(lines) and (
                LIST_ITEM.match(lines[j]) or (lines[j].startswith(" ") and lines[j].strip())
            ):
                j += 1
            out.append(render_list(lines[i:j]))
            i = j
        elif not line.strip():
            i += 1
        else:
            j = i
            while j < len(lines) and lines[j].strip() and not re.match(r"^(```|#|\||>|\s*([-*]|\d+\.)\s)", lines[j]):
                j += 1
            j = max(j, i + 1)
            out.append("<p>" + inline(" ".join(part.strip() for part in lines[i:j])) + "</p>")
            i = j
    return "\n".join(out)


def sections(markdown: str) -> list[tuple[int, str, str]]:
    """Split the document at level-1 and level-2 headings: (level, title, body)."""

    found: list[tuple[int, str, list[str]]] = []
    fenced = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        match = None if fenced else re.match(r"^(#{1,2})\s+(.*)$", line)
        if match:
            found.append((len(match.group(1)), match.group(2), []))
        elif found:
            found[-1][2].append(line)
    return [(level, title, "\n".join(body)) for level, title, body in found]


# --- the brass monogram -----------------------------------------------------


def monogram_svg() -> str:
    """A brass seal stamped with the initials BMo."""

    cx = cy = 100.0
    edge = " ".join(
        f"{cx + (96 if step % 2 == 0 else 90) * math.cos(math.radians(step * 5)):.1f},"
        f"{cy + (96 if step % 2 == 0 else 90) * math.sin(math.radians(step * 5)):.1f}"
        for step in range(72)
    )
    stars = "".join(
        f'<text x="{cx + 73 * math.cos(math.radians(angle)):.1f}" '
        f'y="{cy + 73 * math.sin(math.radians(angle)) + 4:.1f}" text-anchor="middle" '
        'font-size="11" fill="#5c430b">&#9733;</text>'
        for angle in (0, 180)
    )
    return f"""<svg class="seal" viewBox="0 0 200 200" role="img" aria-label="BMo brass monogram seal">
  <defs>
    <radialGradient id="brass" cx="35%" cy="28%" r="80%">
      <stop offset="0" stop-color="#fff3b0"/><stop offset="0.3" stop-color="#e3c14e"/>
      <stop offset="0.68" stop-color="#b8891b"/><stop offset="1" stop-color="#6e4f0c"/>
    </radialGradient>
    <linearGradient id="brassDeep" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#d9b23c"/><stop offset="1" stop-color="#8a660f"/>
    </linearGradient>
    <path id="arcTop" d="M 30 100 A 70 70 0 0 1 170 100"/>
    <path id="arcBottom" d="M 23 100 A 77 77 0 0 0 177 100"/>
    <filter id="drop" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000" flood-opacity="0.55"/>
    </filter>
  </defs>
  <g filter="url(#drop)">
    <polygon points="{edge}" fill="url(#brass)" stroke="#5c430b" stroke-width="1"/>
    <circle cx="100" cy="100" r="84" fill="none" stroke="#5c430b" stroke-width="1.5"/>
    <circle cx="100" cy="100" r="81" fill="none" stroke="#fff3b0" stroke-width="0.8" opacity="0.7"/>
    <circle cx="100" cy="100" r="60" fill="url(#brassDeep)" stroke="#5c430b" stroke-width="1.5"/>
    <circle cx="100" cy="100" r="56" fill="none" stroke="#fff3b0" stroke-width="0.8" opacity="0.6"/>
  </g>
  <text font-family="Georgia, serif" font-size="10.5" letter-spacing="2.6" fill="#4a3608" font-weight="bold">
    <textPath href="#arcTop" startOffset="50%" text-anchor="middle">CAMPUS CUSTOMS AGENT</textPath></text>
  <text font-family="Georgia, serif" font-size="10" letter-spacing="2.4" fill="#4a3608" font-weight="bold">
    <textPath href="#arcBottom" startOffset="50%" text-anchor="middle">MGT 409 &#183; HOMEWORK 3</textPath></text>
  {stars}
  <g font-family="Georgia, 'Times New Roman', serif" font-size="46" font-weight="bold" font-style="italic"
     text-anchor="middle">
    <text x="101.5" y="117.5" fill="#fff3b0" opacity="0.75">BMo</text>
    <text x="98.8" y="114.8" fill="#3d2b05" opacity="0.8">BMo</text>
    <text x="100" y="116" fill="#6b4d0d">BMo</text>
  </g>
  <line x1="66" y1="126" x2="134" y2="126" stroke="#4a3608" stroke-width="1.2"/>
  <line x1="66" y1="129" x2="134" y2="129" stroke="#fff3b0" stroke-width="0.7" opacity="0.7"/>
</svg>"""


# --- page -------------------------------------------------------------------

STYLE = """
  :root { --desk:#1b1410; --leather:#2a1d16; --oak:#3b2a1e; --brass:#c9a227; --glass:#4fa97c;
          --cream:#f5e6c8; --muted:#b9ad93; --rule:#5a4330; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--desk); color:var(--cream); font:16px/1.6 Georgia, "Times New Roman", serif; }
  .wrap { max-width:1080px; margin:0 auto; padding:0 20px 70px; }
  header { display:flex; gap:26px; align-items:center; flex-wrap:wrap; padding:34px 0 22px;
           border-bottom:2px solid var(--brass); }
  .seal { width:150px; height:150px; flex:none; }
  header h1 { margin:0; color:var(--brass); font-size:34px; line-height:1.15; }
  header p { margin:6px 0 0; color:var(--muted); }
  h2 { color:var(--brass); font-size:23px; margin:34px 0 10px; }
  h3 { color:var(--glass); font-size:14px; letter-spacing:1.2px; text-transform:uppercase; margin:22px 0 8px; }
  h4 { color:var(--cream); font-size:16px; margin:18px 0 6px; }
  a { color:var(--brass); }
  code { font:13px Consolas, monospace; color:#e8cf7a; }
  pre { background:#120d0a; border:1px solid var(--rule); border-radius:6px; padding:12px 14px; overflow-x:auto; }
  pre code { color:var(--cream); }
  .tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr)); gap:14px; margin:22px 0; }
  .tile { background:var(--leather); border:1px solid var(--rule); border-top:3px solid var(--brass);
          border-radius:6px; padding:14px 16px; }
  .tile b { display:block; font-size:30px; color:var(--brass); line-height:1.1; }
  .tile span { color:var(--muted); font-size:14px; }
  .summary { background:var(--leather); border:1px solid var(--rule); border-radius:8px; padding:6px 24px 18px; }
  .meters { display:flex; flex-wrap:wrap; gap:18px; margin:10px 0 4px; }
  .metergroup { flex:1 1 320px; }
  .metergroup > p { margin:0 0 6px; color:var(--muted); font-size:14px; }
  .pair { display:flex; flex-wrap:wrap; gap:12px; }
  .meter { width:230px; max-width:100%; margin:0; }
  .meter svg { width:100%; height:auto; display:block; }
  .meter figcaption { margin-top:4px; color:var(--muted); font-size:13px; }
  .links { display:flex; flex-wrap:wrap; gap:10px; padding:0; list-style:none; }
  .links a { display:block; padding:6px 14px; border:1px solid var(--brass); border-radius:16px;
             text-decoration:none; font-size:14px; }
  .scroll { overflow-x:auto; margin:10px 0; }
  table { border-collapse:collapse; width:100%; font-size:15px; }
  th { text-align:left; background:var(--oak); color:var(--brass); font-size:12px; letter-spacing:.8px;
       text-transform:uppercase; padding:8px 10px; }
  td { padding:8px 10px; border-top:1px solid var(--rule); vertical-align:top; }
  blockquote { margin:12px 0; padding:4px 16px; border-left:4px solid var(--brass); background:var(--oak);
               border-radius:0 6px 6px 0; }
  ul, ol { padding-left:24px; } li { margin-bottom:6px; }
  .part { margin:46px 0 6px; padding-bottom:6px; border-bottom:1px solid var(--brass); color:var(--cream);
          font-size:26px; }
  .tools { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:10px 0 16px; }
  .tools button { background:var(--oak); color:var(--cream); border:1px solid var(--brass); border-radius:4px;
                  padding:6px 14px; font:inherit; font-size:14px; cursor:pointer; }
  .tools button:focus, summary:focus { outline:2px solid var(--glass); outline-offset:2px; }
  details { background:var(--leather); border:1px solid var(--rule); border-radius:6px; margin:10px 0; }
  details > summary { cursor:pointer; padding:13px 18px; font-size:18px; color:var(--brass); list-style-position:inside; }
  details[open] > summary { border-bottom:1px solid var(--rule); }
  details > .body { padding:4px 22px 18px; }
  footer { margin-top:40px; color:var(--muted); font-size:14px; text-align:center; }
"""

LINKS = [
    ("Catalogue of 102 products", "catalogue_review.html"),
    ("Photo result: Yale Dad tee", "identify_product_image_01_true.html"),
    ("Photo result: long sleeve", "identify_product_image_03_true.html"),
    ("Ad check: student", "ad_effectiveness_student.html"),
    ("Ad check: parent", "ad_effectiveness_parent.html"),
    ("Safety rules and audit trail", "audit_trail.html"),
    ("Review form with the user's comments", "review_summary.html"),
    ("User's evaluation of the agent", "agent_evaluation.md"),
]


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def main() -> None:
    document = sections(HARNESS_PATH.read_text(encoding="utf-8"))
    summary = next(body for _, title, body in document if title == "Executive summary")

    catalogue = json.loads(CATALOGUE_JSON_PATH.read_text(encoding="utf-8"))
    evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    ads = {result.profile.profile_id: result for result in load_ad_results()}
    audit = load_audit()
    tiles = [
        (str(catalogue["product_count"]), "products catalogued and searchable"),
        (f"{evaluation['correct']} of {evaluation['total']}", "test photos identified correctly"),
        ("3 max", "catalogue photos opened per identification, of 102"),
        ("2 scores", "per ad: appropriateness and effectiveness, 0 to 10"),
        ("$0.50", "cost ceiling per agent loop, enforced in code"),
        (str(len(audit)), f"audit entries from {len({entry.run_id for entry in audit})} recorded runs"),
    ]
    meters = "".join(
        f'<div class="metergroup"><p>The ad, for: {html.escape(ads[key].profile.label)}</p><div class="pair">'
        f'{meter_svg("Appropriateness", ads[key].appropriateness_score)}'
        f'{meter_svg("Effectiveness", ads[key].effectiveness_score)}</div></div>'
        for key in ("student", "parent")
        if key in ads
    )

    detail = ""
    for level, title, body in document[1:]:
        if title == "Executive summary":
            continue
        if level == 1:
            detail += f'<h2 class="part" id="{slug(title)}">{inline(title)}</h2>{render(body)}'
        else:
            detail += (
                f'<details id="{slug(title)}"><summary>{inline(title)}</summary>'
                f'<div class="body">{render(body)}</div></details>'
            )

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs agent: harness report</title><style>{STYLE}</style></head>
<body><div class="wrap">
<header>{monogram_svg()}
  <div><h1>Campus Customs agent</h1>
  <p>Harness report &middot; MGT 409, Homework 3</p>
  <p>What the agent does, how it is built, the rules it follows, and how it performed.</p></div>
</header>
<div class="tiles">{''.join(f'<div class="tile"><b>{html.escape(big)}</b><span>{html.escape(small)}</span></div>' for big, small in tiles)}</div>
<section class="summary" aria-label="Executive summary">
  <h2>Executive summary</h2>
  {render(summary)}
  <h3>How the ad scored</h3><div class="meters">{meters}</div>
  <h3>See it working</h3>
  <ul class="links">{''.join(f'<li><a href="{href}">{html.escape(text)}</a></li>' for text, href in LINKS)}</ul>
</section>
<h2 id="detail">Detailed report</h2>
<p>Open any section below. Part 1 is the reference for how the system works; Part 2 holds the working
   notes for each problem.</p>
<div class="tools"><button type="button" id="open">Open all sections</button>
  <button type="button" id="close">Close all sections</button></div>
{detail}
<footer>Built from output/harness.md by build_report.py</footer>
</div>
<script>
  const all = () => document.querySelectorAll("details");
  document.getElementById("open").addEventListener("click", () => all().forEach(d => d.open = true));
  document.getElementById("close").addEventListener("click", () => all().forEach(d => d.open = false));
  const jump = () => {{ const target = document.getElementById(location.hash.slice(1));
    if (target && target.tagName === "DETAILS") target.open = true; }};
  window.addEventListener("hashchange", jump); jump();
</script>
</body></html>"""
    write_text(REPORT_PATH, page)
    print(f"Wrote {REPORT_PATH.relative_to(PROJECT_DIR).as_posix()} "
          f"({sum(level == 2 for level, _, _ in document) - 1} fold-out sections)")


if __name__ == "__main__":
    main()
