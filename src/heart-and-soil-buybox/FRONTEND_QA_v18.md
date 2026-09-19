# Frontend QA pass, v18

Measured in the browser at a 1265px viewport, 1120px content column, 1016px text measure.

## The bug that was causing most of it

The gantt and forecast figures were rendering **outside** `div.wrap`. A stray `</div>` left behind
by the recommendation reorder closed the layout wrapper early, so every block after the
recommendations escaped the 1016px column and laid out against the full 1265px viewport.

Measured before: c1 to c4 rendered 971px wide at scale 1.10, c5 and c6 rendered **1219px** at scale
1.39. Their internal text therefore drew 26% larger than the charts above them, which is what read as
"enormous charts" and "alignment issues". Fixed by removing the stray tag.

A structure guard now runs at build time. It checks tag balance for div, figure, details, table, ul,
p and span, and walks div depth to assert nothing ever closes out of its wrapper. This class of bug
cannot ship silently again.

## Chart harmony

|      | before        | after        |
|------|---------------|--------------|
| widths | 971 and 1219 | 971 across all six |
| aspect range | 2.14 to 2.93 | 2.49 to 2.93 |
| tallest chart | 454px | 390px |
| total chart height | 2,525px | 2,226px |
| smallest rendered label | 9.9px | 11.0px |
| clipped labels | 2 | 0 |
| figures that scroll sideways | 2 | 0 |

Chart 2 was the tallest on the page; its row height and gap came down. Chart 4's plot was 400 units
against 340 for its neighbours and now sits in the same band. Every chart label below 10 units was
raised so nothing renders under 11px against 16px body text.

## Dynamic behaviour

Exercised every control rather than reading the code.

- Four measure buttons: each switches series, title, subtitle and caption, and exactly one carries
  aria-pressed at a time. Verified across all four.
- Daily and weekly toggle: redraws from 47 to 89 nodes and back.
- Five metric chips on chart 4: toggle and restore cleanly, 65 to 54 to 65 nodes.
- **Defect found and fixed.** Unticking every chip left a bare axis, an empty readout and no
  explanation. It now draws "Tick a measure above to draw it".
- All five executive summary anchors resolve to a real heading.

## Consistency

- All six figures now carry a title, a subtitle and a caption. The gantt was missing a caption.
- One h2 size across the page. Two h3 sizes, 22px for the primary recommendation and 15px for the
  rest, which is intentional hierarchy.
- Block gaps run 4px to 70px with nothing negative and nothing excessive.
- No horizontal scroll at any point.

## Not verified here

Dark mode. A local static preview always renders light, so the dark palette could not be exercised
in the browser. Every colour on the page resolves from a token that has a dark-mode definition, and
the two chip tints that are literal rgba values sit under ink text that flips with the theme.

---

# v19, acting on the PM visual review

Verdict was NOT APPROVED with five visual blockers. All five actioned, plus the three polish items.

## Two corrections to the review, both verified before acting

The review listed `.stat-d.up` and `.cell .val.b` as blue contrast problems. They measure 8.21:1 and
7.40:1, so they pass. Blue was a semantic misuse, not a legibility one, and it was fixed as such.

The proposed chart 3 ramp used `--s-alt` as its middle step. That fails in both themes: 3.81:1
against ink in light and 2.06:1 in dark, for a 12.5px label sitting on the bar. A ramp token pair
was solved for instead, `--ramp-mid` at #BBA173 light and #7A6B4E dark, which measure 6.35:1 and
4.68:1 with clean separation from both ends of the ramp.

## Blockers

1. Six places still set an accent as text, all confirmed failing at 2.24:1 to 2.48:1: the primary
   card's deadline line, the summary counters, the figures-table change column, the chart 4 readout,
   the disclosure indicator and the method bullet markers. All moved to ink. Two more the review did
   not list were found and fixed the same way: the chart 4 metric chips, where the series colour was
   painting the label text, and the h1 emphasis, which is now ink on an orange highlight. An accent
   is now a fill or a rule and never a word.
2. Retention blue meant the baseline window in chart 2 and "2 bottles" in chart 3, fourteen pixels
   apart. Chart 3 is an ordinal measure and now uses a ramp.
3. The recommendation cards carried roughly 230px of dead space each because one long column set the
   height for three short ones. Two columns instead of four: cards went from 244px to 501px wide,
   dead space from about 230px to about 29px, block height unchanged at 670px.
4. The primary recommendation was the fifth largest thing on the page. Now 24px at weight 900 with a
   6px rule and the same orange lift the lead value card already had.
5. Gap grammar was set three different ways for the same relationship, and two 390px charts sat back
   to back with 14px between them. One rule for every block object, 34px between consecutive figures.

## Polish

Connective prose moved to full ink at 16.5px, since it was the only text not on a card and the
lowest contrast on the page. The gantt joined the aspect band at 2.72:1. The four headline numbers
moved above the summary so the summary explains them rather than restating them. The range chip
swatch that encoded nothing, the `flat` figure variant and the chart 1 blue mean line inside an
orange window are all gone.

## A bug the first guard did not catch

Moving the strip block relocated its opening tag without its closing tag. Totals stayed balanced and
depth never went negative, so the structure guard passed while `.exec` was nested inside `.strip`.
The header rendered 5,048px and the page 14,358px.

The guard now also walks each known block to its matching close and asserts no two siblings contain
one another. Verified by reintroducing the exact bug and confirming the build fails with
"'exec' is nested inside 'strip'".

## Final state

Six charts, 357 to 390px, aspect 2.49 to 2.72, zero clipped labels, no horizontal scroll.
Header 866px, page 10,175px. Type ladder 24 / 16 / 15 under the Anton headings. Grounding guard,
structure guard and 105 QA checks all pass.
