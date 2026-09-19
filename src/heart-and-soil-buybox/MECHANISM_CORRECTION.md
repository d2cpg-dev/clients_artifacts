# The mechanism was wrong. Corrected from selling-plan data, 2026-09-19.

## What we had claimed

"A single bottle every 90 days went from 7.87% of sign-ups to 0.80%. That option effectively went
away." Recommendation: "Put a single bottle every 90 days back in the buy box."

The share figures were right. The interpretation was an inference, and it was wrong.

## How it was tested

Queried `SubscriptionLine.sellingPlanId` for every single-product subscription created Jul 20 to
Sep 16, grouped by selling plan, cadence and quantity, split into before / sale / since. One query,
66 MB, about $0.0003. If a combination had been removed, its plan would show sign-ups before the
change and none after.

## What the data shows

Nothing was removed. Every single-bottle combination is still selling, with sign-ups as recently as
Sep 16, the last day of data: 1,020 at 30 days, 151 at 60 days, 23 at 90 days.

What changed is which plan group the box presents. Both groups existed before Sep 3.

| plan group | sign-ups before | sign-ups since |
|---|---|---|
| previously dominant | 12,406 | 165 |
| the one that replaced it | 542 | 2,605 |

And the new group ties quantity to cycle length, which the old one did not:

| cycle | one bottle, old group | one bottle, new group |
|---|---|---|
| every 30 days | 72.1% | 72.9% |
| every 60 days | 61.1% | 31.1% |
| every 90 days | 46.9% | 2.4% |

Three bottles at 90 days went from 18.6% to 75.2%. The 30-day cycle barely moved, which is the
control: one bottle is the natural quantity for a month either way.

The only combination with zero sign-ups since the change is a 30-day single bottle on one retired
plan, 89 before and none after. Not the 90-day one.

## What changed in the report

- Headline: "One plan explains most of it" became "The long cycles became bulk".
- Mechanism section rewritten around the plan-group swap and the quantity coupling.
- Summary gained a mechanism row back, since it is no longer a restatement of its section.
- Recommendation: "Put a single bottle every 90 days back in the buy box" became "Let people pick
  one bottle at the longer cycles". Same config change, same 30-day test, honest description.
- Question one now asks whether the bundling was deliberate, not whether a plan was deleted.
- Figures table gained a "Selling plans" section carrying all six figures above.
- QA gained 12 checks on the selling-plan evidence, including one that asserts the "nothing was
  removed" claim by requiring every single-bottle cycle to still have sign-ups. 117 checks total.

## What did not change

No take-rate figure, window, definition or rounding. The fall is still 7.8 points, 59.55% to 51.78%.
