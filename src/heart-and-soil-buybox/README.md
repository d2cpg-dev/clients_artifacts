# Heart & Soil, subscription buy-box review

Source for `/heart-and-soil-buybox-review.html`. The published page is generated, not
hand-edited. Edit the source and rebuild; do not edit the HTML.

## Rebuild

```
python build_v15.py     # writes page_v15.html, the artifact-shaped fragment
python qa_v15.py        # 117 checks, non-zero exit on any failure
python wrap_pages.py    # wraps the fragment into ../../heart-and-soil-buybox-review.html
```

`build_v15.py` runs two guards and will refuse to write if either fails.

- **Grounding guard.** Strips HTML from the copy and fails if any digit survives. Every number in
  the prose must resolve from a token, so a figure can never be typed by hand and drift from the
  ledger. Three literals are allowed and printed at build time: the chart 3 legend labels.
- **Structure guard.** Checks tag balance, that nothing closes outside the layout wrapper, and that
  the named blocks are never nested inside one another. This exists because a misplaced opening tag
  once pushed half the page outside the wrapper while the totals still balanced.

## What each file is

| file | role |
|---|---|
| `page_v15_body.html` | the report copy. Tokens only, no typed numbers |
| `build_v15.py` | the builder: stylesheet, chart-engine patches, token table, guards |
| `page_v10_template.html` | inherited stylesheet and chart engine, patched at build time |
| `facts_v15.json` | the number ledger. Every figure in the prose resolves from here |
| `plan_facts.json` | selling-plan evidence: plan groups and quantity chosen per cycle |
| `payload_v15.json` | the chart data, embedded into the page |
| `bq_facts.json` | Skio scalars with provenance, pulled 2026-09-18 |
| `bq_plan.csv` | Skio plan mix by window, cadence and quantity |
| `selling_plans.csv` | Skio sign-ups by selling plan, the evidence that nothing was removed |
| `qa_v15.py` | 117 checks that re-derive relationships rather than trusting them |
| `facts_v15.py` | rebuilds `facts_v15.json` from the raw exports. See the note below |
| `prep_v15.py` | rebuilds `payload_v15.json` from the raw exports. See the note below |
| `wrap_pages.py` | adds the document shell and crawler directives for GitHub Pages |

## The raw exports are deliberately not committed

`facts_v15.py` and `prep_v15.py` read five Shopify CSV exports from a local `Downloads` folder.
Those files are **not** in this repository and should not be added to it.

This repo is public. It is unlisted and every page carries `noindex, nofollow, noarchive`, but that
is obscurity, not access control. The committed JSON and CSV files hold only the aggregates the
published page already displays. The raw exports hold more than the page shows, including
product-level daily revenue across the whole catalogue, so they stay out.

To re-derive the ledgers from source, put the five exports in a local `Downloads` folder and run
`facts_v15.py` then `prep_v15.py` before `build_v15.py`.

## Reading order for the analysis itself

1. `MECHANISM_CORRECTION.md` — why the first read of the cause was wrong, and the query that settled it
2. `REFACTOR_v20.md` — the laptop-first layout work and what moved the numbers
3. `FRONTEND_QA_v18.md` — the layout bug that was making the charts look enormous

## Things that will bite you

- Numbers live in `facts_v15.json` and `plan_facts.json`. Changing a figure means changing the
  ledger and re-running QA, never editing the copy.
- Charts are drawn into an 880-unit viewBox and the figure column is pinned to 880px so the render
  scale is exactly 1.000. In-SVG type is floored at 11 units, which is therefore 11px. Widening the
  figure column breaks that relationship and makes every chart taller.
- The page is light only, on purpose. Both dark blocks are stripped from the inherited stylesheet at
  build time and `wrap_pages.py` asserts none came back.
