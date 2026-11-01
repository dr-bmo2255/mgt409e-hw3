# Homework 3 — Campus Customs agent

An AI agent for Campus Customs, a shop that sells Yale apparel. It identifies Campus Customs
products in photos and judges how well an ad video would work for a given customer.

The full description is in `output/harness.md`. A formatted version with an executive
summary is `output/harness_report.html`.

## Viewing the results (no setup needed)

Every HTML file in `output/` is self-contained: open it in any browser by double-clicking.
No server, API key, or `data/` folder is required. Start with `output/harness_report.html`,
which links to the others.

| Page | What it shows |
| --- | --- |
| `output/harness_report.html` | Executive summary and the full harness report. |
| `output/catalogue_review.html` | All 102 catalogued products, filterable and sortable. |
| `output/identify_product_image_0N_*.html` | Result for each test photo, with the product sidebar and cart. |
| `output/ad_effectiveness_<profile>.html` | The ad judged for each customer profile, with needle meters. |
| `output/audit_trail.html` | The safety rules and the audit trail of real runs. |
| `output/review_summary.html` | Saved copy of the review form, with the user's comments on each photo and ad run. |

The ad on the review pages plays from `output/ad_preview/`, a small H.264 copy of the
course video. The agent's JSON outputs are in `output/` as listed in the assignment.

## Running the code

1. Put the course `data/` folder (with `products/`, `test_images/`, and `videos/`) inside
   this folder, next to `agent.py`. It is not included in the zip.
2. Copy `.env.example` to `.env` and add a Portkey key. No real key is included.
3. Create the environment (pause OneDrive or Dropbox syncing first):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Run:

```powershell
.\.venv\Scripts\python.exe agent.py --image "data/test_images/image_01_true.jpeg"
.\.venv\Scripts\python.exe agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_student.json"
.\.venv\Scripts\python.exe agent.py --video "data/videos/ad_humble.mp4" --profile "profiles/profile_parent.json"
```

Add `--no-open` to stop the result page opening in the browser. Each agent run costs
between about $0.03 and $0.20 on `gpt-6-astra`.

Other commands:

| Command | What it does |
| --- | --- |
| `python build_catalogue.py` | Rebuilds the catalogue. Unchanged photos are reused from `output/catalogue.json` at no cost. |
| `python evaluate.py` | Runs the agent on all four test photos and scores it. |
| `python build_profiles.py` | Rewrites the five profiles in `profiles/`. |
| `python review_app.py` | Starts the review form at `http://127.0.0.1:8765`. |
| `python view_catalogue.py`, `view_audit.py`, `build_report.py` | Rebuild the HTML pages. |
| `python -m unittest` | Runs the 18 offline tests. No model calls, but the tests need `data/`. |

## Files

The agent itself is four files: `prompts/prompt.md`, `agent.py`, `tools.py`, and `models.py`.
They import two small supporting modules: `config.py` (paths, model access, cost cap) and
`catalogue_db.py` (the catalogue search index). `build_catalogue.py` builds the catalogue.
The remaining scripts produce the evaluation, review form, and report pages.

`AI_prompts.md` is the log of the prompts used to build the project.

## Live demo

The site at https://dr-bmo2255.github.io/mgt409e-hw3/ shows saved results from real runs. It makes
no live AI calls, so it uses no tokens and costs nothing to view. To run the agent yourself, follow
"Running the code" above with your own Portkey key and the course data pack.
