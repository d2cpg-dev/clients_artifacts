# Heart & Soil, subscription buy-box review

Source for `/heart-and-soil-buybox-review.html`. The published page is generated, not
hand-edited. Edit the source and rebuild; do not edit the HTML.

## Rebuild

```
python build_v18.py     # writes page_v18.html, the artifact-shaped fragment
python qa_v15.py        # 117 checks on the ledger, non-zero exit on any failure
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

## The build that is published

`build_v18.py` is the one `wrap_pages.py` wraps. It is a presentation pass over v15:
same section order, same headings, same analysis, every number identical. `qa_v18_diff.py`
proves that on every build.

The layout is a **twelve-column compound grid**. At the 1280px brand maximum with 48px
outer margins the content field is 1184px, which puts a column at 76.67px: eight columns
is 781px and four is 379px. Reading prose holds the eight-column graphic zone so every
paragraph shares a flowline with the chart beneath it. Each figure is a nested twelve:
the drawing takes the eight-column graphic zone (749px inside the tile's padding) and the
reading takes the four-column narrative rail beside it (363px), a 66/32 split. Below a
1100px container the formation collapses and both take the full field.

Other things it does differently from the sheet it replaced, which was a base stylesheet
plus fifteen patch layers with 143 of 178 spacing declarations off the grid:

- every margin, padding and gap is a multiple of 8, enforced at build time
- nineteen font sizes became six tokens plus two clamped display sizes; thirteen
  letter-spacing values became one for every uppercase label
- six subject labels became takeaway headlines built from ledger tokens, so a headline
  cannot drift from the figure it states
- the three legends came off and the drawings name their own series: chart 2 on its first
  row, chart 3 inside each band on the row where it is widest, chart 5 in an owner column
- colour means one thing each. Orange is the change and nothing else; there is no green
- in-chart type has a 13-unit floor, which lands on 11.07px in the 749px zone

Ten guards run on every build, and each exists because the thing it checks broke once:
one stylesheet with no duplicate declarations or dead rules, spacing on the 8px unit, no
ninth type size or second caps tracking, WCAG ratios against both the cream ground and the
white card, every jump link resolving and `scroll-behavior: smooth` rejected (it once
silently swallowed the entire section nav), sentence case in every heading source, every
`a-*` accent class declared (three verdict cards once shipped with no top rule because
they still carried a retired class), and the figure header stacking in whole 8px units.

```
python build_v18.py      # writes page_v18.html
python qa_v18_diff.py    # proves the design pass moved no number
python wrap_pages.py     # wraps it into ../../heart-and-soil-buybox-review.html
```

`build_v15.py` is kept because it is the reference v18 is checked against, and v17 is the
previous published build. A v16 pass was rejected on its layout and is not in the repository.

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
