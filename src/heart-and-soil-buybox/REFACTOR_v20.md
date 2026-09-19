# v20 laptop-first refactor, result

Target: 13-14 inch laptop, 16:10, about 790px usable viewport.

| metric | before | after | change |
|---|---|---|---|
| page height | 10,175px | **7,571px** | −2,604px, −26% |
| screens to scroll at 790px | 12.9 | **9.6** | −3.3 screens |
| largest figure block | 864px, 109% of viewport | **568px, 72%** | fits on screen |
| smallest figure block | 560px | 414px | |
| total figure height | 3,773px | 2,795px | −978px |
| chart render scale | 1.103, emergent | **1.000, pinned** | constant at every breakpoint |
| smallest chart label | 9.9px | **11.0px** | floor enforced in the engine |
| header | 866px | 640px | −226px |
| clipped labels | 2 | 0 | |
| figures scrolling sideways | 2 | 0 | |

## What actually moved the numbers

**The chart scale pin.** Charts were drawn into an 880-unit viewBox and stretched to fill the
column, so width drove height. The figure column is now exactly 880px and the scale is a constant
1.000 rather than an emergent 1.103. That alone is 10% off every chart, and it makes the in-SVG type
floor meaningful: a `size: 11` label now renders at exactly 11px at every breakpoint.

**A grid bug worth naming.** `figcaption{grid-row:1 / -1}` with no explicit rows resolves to line 1,
so the caption was pinned to row 1 and stretching the figure title to its own height. Every figure
title was rendering 108px tall for one line of 16px text. Changing it to `span 20` recovered about
90px per figure.

**The caption rail.** At container widths at or above 1194px the caption moves beside the chart
instead of under it, via a container query on `.wrap`. Verified live: the rail engages at a 1265px
viewport with 268px of rail, which covers 1280x800 and 1366x768 machines with a scrollbar present.
Below that it falls back to single column in source order.

**Content that was saying the same thing twice.** Summary rows 2, 3 and 4 were verbatim restatements
of the sections they linked to; their jump links survive as a masthead nav. Three of four window
pills were stated by the chart shading, the figures table and Method. Chart 1 was labelled four
times.

**Proof folded, argument kept.** The six robustness cuts, the placebo detail, the post-sale trend
hint and the twelve Method bullets are now disclosures. The conclusions stay visible: every cut
lands between 7.0 and 8.6 points, the worst placebo was 1.8 against a real 7.8, and the
fourteen-clean-day rule that reverses the earlier read sits above the fold of the Method section.
All disclosures open adds 2,501px, which is the measure of how much was being shown unasked.

## Not changed

No figure, window, definition or rounding. Grounding guard, structure guard and the 105-check QA all
pass. The accent discipline, the ordinal ramp, the chip contrast fix and the empty state all survive.

## Known limits

Dark mode is still unverified by eye; a local static preview always renders light.
Below a 962px container the chart scrolls horizontally rather than shrinking, which is a deliberate
choice of legibility over scroll avoidance, since shrinking would put axis labels under 9px.

---

# v21 best practices pass

## Single theme, by decision

Dark mode removed entirely: 1,108 bytes of tokens out of the inherited stylesheet, both the
`prefers-color-scheme` block and the `[data-theme="dark"]` block, plus the dark ramp overrides.
`color-scheme:light` is declared and `body` paints an explicit background, so the page renders the
same on any OS setting. This also closes the one risk I had been carrying, which was a second theme
nobody could verify.

## Accessibility, audited in the browser, zero issues remaining

- `<main>` landmark added. The document previously had no main region.
- Skip link to the first section, hidden until focused. Verified by proving the cascade rather than
  by eye: `:focus` cannot match in an unfocused preview document, so I swapped the selector to
  `.skip` and confirmed the computed `left` becomes `0px`, then restored it.
- All six charts carry `role="img"` and an `aria-label`.
- All measure and grain buttons carry `aria-pressed`; all five metric chips are label-wrapped.
- All five table headers now carry `scope="col"`.
- Heading order runs 1, 2, 2 ... 3 with no skipped levels.
- Visible focus ring on every anchor, button and disclosure summary.
- 25 focusable elements, 9 internal links, all resolving.

## Print

A client report gets printed, so there is now a print stylesheet: 14mm page margin, disclosures
forced open, navigation and controls hidden, figures and cards set `break-inside:avoid`, headings
set `break-after:avoid`, the caption rail collapsed back under its chart and charts set to fluid
width so they fit the paper.

## State

Page 7,571px, 9.6 screens. 262 chart nodes drawn, zero clipped labels, no horizontal scroll, every
interaction verified working. Grounding guard, structure guard and 105 QA checks all pass.
