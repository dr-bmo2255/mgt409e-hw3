"""Write output/catalogue_review.html: a filterable table of the catalogue database."""

from __future__ import annotations

import base64
import html
import io
import json
import sqlite3

from PIL import Image

from catalogue_db import FACET_WEIGHTS, facet_counts
from config import CATALOGUE_DB_PATH, OUTPUT_DIR, PROJECT_DIR
from models import CatalogueEntry

REVIEW_PATH = OUTPUT_DIR / "catalogue_review.html"
THUMBNAIL_SIDE = 96
FILTERS = ["garment_category", "garment_type", "sleeve_length", "primary_color", "affiliation_type"]

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs catalogue</title>
<style>
  :root { --desk:#1b1410; --leather:#2a1d16; --oak:#3b2a1e; --brass:#c9a227; --glass:#4fa97c;
          --cream:#f5e6c8; --muted:#b9ad93; --rule:#5a4330; }
  * { box-sizing:border-box; }
  body { margin:0; padding:24px 16px 48px; background:var(--desk); color:var(--cream);
         font:15px/1.5 Georgia, "Times New Roman", serif; }
  h1 { margin:0 0 4px; color:var(--brass); font-size:26px; letter-spacing:.5px; }
  .sub { color:var(--muted); margin:0 0 20px; }
  .facets { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; margin-bottom:20px; }
  .facet { background:var(--leather); border:1px solid var(--rule); border-radius:6px; padding:10px 12px; }
  .facet h2 { margin:0 0 6px; font-size:13px; text-transform:uppercase; letter-spacing:1px; color:var(--glass); }
  .chip { display:inline-block; margin:2px 4px 2px 0; padding:1px 8px; border:1px solid var(--rule);
          border-radius:10px; font-size:13px; white-space:nowrap; }
  .chip b { color:var(--brass); font-weight:normal; }
  .controls { display:flex; flex-wrap:wrap; gap:10px; align-items:end; margin-bottom:12px; }
  label { display:flex; flex-direction:column; gap:3px; font-size:12px; color:var(--muted);
          text-transform:uppercase; letter-spacing:.8px; }
  input, select { background:var(--oak); color:var(--cream); border:1px solid var(--brass);
          border-radius:4px; padding:7px 9px; font:inherit; font-size:14px; min-width:150px; }
  input { min-width:240px; }
  input:focus, select:focus { outline:2px solid var(--glass); outline-offset:1px; }
  #count { margin-left:auto; color:var(--brass); }
  .wrap { overflow-x:auto; border:1px solid var(--rule); border-radius:6px; }
  table { border-collapse:collapse; width:100%; min-width:1250px; background:var(--leather); }
  th { position:sticky; top:0; background:var(--oak); color:var(--brass); text-align:left; font-size:12px;
       text-transform:uppercase; letter-spacing:.8px; padding:9px 10px; cursor:pointer; white-space:nowrap; }
  td { padding:9px 10px; border-top:1px solid var(--rule); vertical-align:top; }
  tr:hover td { background:#33241b; }
  td img { width:72px; height:72px; object-fit:contain; background:#fff; border-radius:4px; display:block; }
  .id { color:var(--muted); font:12px Consolas, monospace; }
  .text { color:var(--glass); }
  .note { color:var(--muted); font-size:13px; }
</style>
</head>
<body>
<h1>Campus Customs catalogue</h1>
<p class="sub">__COUNT__ products from output/catalogue.db. Click a column heading to sort.</p>
<div class="facets">__FACETS__</div>
<div class="controls">
  <label>Search<input id="q" type="search" placeholder="text, sport, college, brand..."></label>
  __SELECTS__
  <span id="count" role="status"></span>
</div>
<div class="wrap"><table>
  <thead><tr>__HEAD__</tr></thead>
  <tbody id="rows"></tbody>
</table></div>
<script>
const ROWS = __ROWS__;
const COLUMNS = __COLUMNS__;
const FILTERS = __FILTER_KEYS__;
let sortKey = "product_id", ascending = true;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function cell(row, key) {
  if (key === "image") return `<img src="${row.image}" alt="${esc(row.name)}">`;
  if (key === "product") return `${esc(row.name)}<div class="id">${esc(row.product_id)}</div><div class="note">${esc(row.description)}</div>`;
  if (key === "printed_text") return `<span class="text">${esc(row.printed_text)}</span><div class="note">${esc(row.graphic_elements)}</div>`;
  if (key === "primary_color") return `${esc(row.primary_color)}<div class="note">${esc(row.color_detail)}</div>`;
  return esc(row[key]);
}
function draw() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const shown = ROWS.filter(row =>
    FILTERS.every(key => { const v = document.getElementById("f_" + key).value; return !v || row[key] === v; })
    && (!q || row.haystack.includes(q)));
  const key = sortKey === "product" ? "product_id" : sortKey;
  shown.sort((a, b) => String(a[key] ?? "").localeCompare(String(b[key] ?? "")) * (ascending ? 1 : -1));
  document.getElementById("rows").innerHTML = shown.map(row =>
    "<tr>" + COLUMNS.map(([key]) => `<td>${cell(row, key)}</td>`).join("") + "</tr>").join("");
  document.getElementById("count").textContent = `${shown.length} of ${ROWS.length} shown`;
}
document.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
  if (th.dataset.key === "image") return;
  ascending = sortKey === th.dataset.key ? !ascending : true;
  sortKey = th.dataset.key; draw();
}));
document.querySelectorAll("input, select").forEach(el => el.addEventListener("input", draw));
draw();
</script>
</body>
</html>
"""

COLUMNS = [
    ("image", "Photo"),
    ("product", "Product"),
    ("garment_category", "Category"),
    ("garment_type", "Type"),
    ("sleeve_length", "Sleeve"),
    ("has_hood", "Hood"),
    ("closure", "Closure"),
    ("primary_color", "Colour"),
    ("design_placement", "Placement"),
    ("affiliation_type", "Affiliation"),
    ("made_for", "Sport / college / school / family / event"),
    ("brand", "Brand"),
    ("printed_text", "Printed text and graphics"),
    ("described_by_model", "Described by"),
]


def thumbnail(entry: CatalogueEntry) -> str:
    with Image.open(PROJECT_DIR / entry.image_file) as image:
        image = image.convert("RGBA")
        flattened = Image.new("RGB", image.size, "white")
        flattened.paste(image, mask=image.getchannel("A"))
        flattened.thumbnail((THUMBNAIL_SIDE, THUMBNAIL_SIDE))
        buffer = io.BytesIO()
        flattened.save(buffer, format="JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def row(entry: CatalogueEntry) -> dict[str, str]:
    made_for = [entry.sport, entry.residential_college, entry.school, entry.family_member, entry.event]
    data = {
        "image": thumbnail(entry),
        "product_id": entry.product_id,
        "name": entry.name,
        "description": entry.description,
        "garment_category": entry.garment_category,
        "garment_type": entry.garment_type,
        "sleeve_length": entry.sleeve_length,
        "has_hood": "yes" if entry.has_hood else "no",
        "closure": entry.closure,
        "primary_color": entry.primary_color,
        "color_detail": entry.color_detail,
        "design_placement": entry.design_placement,
        "affiliation_type": entry.affiliation_type,
        "made_for": ", ".join(value for value in made_for if value),
        "brand": entry.brand or "",
        "printed_text": " / ".join(entry.printed_text),
        "graphic_elements": ", ".join(entry.graphic_elements),
        "described_by_model": entry.described_by_model,
    }
    data["haystack"] = " ".join(v for k, v in data.items() if k != "image").lower()
    return data


def main() -> None:
    connection = sqlite3.connect(CATALOGUE_DB_PATH)
    try:
        entries = [
            CatalogueEntry.model_validate_json(entry_json)
            for (entry_json,) in connection.execute(
                "SELECT entry_json FROM products ORDER BY product_id"
            )
        ]
    finally:
        connection.close()

    counts = facet_counts()
    facets = "".join(
        f'<div class="facet"><h2>{html.escape(column.replace("_", " "))}</h2>'
        + "".join(
            f'<span class="chip">{html.escape(value)} <b>{count}</b></span>'
            for value, count in counts[column].items()
        )
        + "</div>"
        for column in FACET_WEIGHTS
    )
    selects = "".join(
        f'<label>{html.escape(key.replace("_", " "))}<select id="f_{key}"><option value="">All</option>'
        + "".join(f"<option>{html.escape(value)}</option>" for value in counts[key])
        + "</select></label>"
        for key in FILTERS
    )
    head = "".join(f'<th data-key="{key}" scope="col">{html.escape(label)}</th>' for key, label in COLUMNS)
    page = (
        PAGE.replace("__COUNT__", str(len(entries)))
        .replace("__FACETS__", facets)
        .replace("__SELECTS__", selects)
        .replace("__HEAD__", head)
        .replace("__ROWS__", json.dumps([row(entry) for entry in entries]).replace("</", "<\\/"))
        .replace("__COLUMNS__", json.dumps(COLUMNS))
        .replace("__FILTER_KEYS__", json.dumps(FILTERS))
    )
    REVIEW_PATH.write_text(page, encoding="utf-8")
    print(f"Wrote {REVIEW_PATH.relative_to(PROJECT_DIR)} ({len(entries)} products)")


if __name__ == "__main__":
    main()
