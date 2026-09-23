# -*- coding: utf-8 -*-
"""Rebuild rev_facts.json: the revenue-weighted subscription share.

Reads one export, f_linerevenue.csv, the line-basis sales query with net_sales
added:

    FROM sales
    SHOW net_sales, orders
    GROUP BY subscription_or_one_time, new_or_returning_customer, sales_channel
    TIMESERIES day
    SINCE 2026-07-20 UNTIL 2026-09-20

That export is NOT committed; only the aggregates below are. It is grouped by
line type, so a cart holding a subscription and a one-off contributes its
subscription lines to one group and its one-off lines to the other. Its `orders`
column therefore double-counts mixed carts and is deliberately ignored here: the
order counts stay with facts_v15.json, and only the revenue split is taken.

The gate at the bottom is the point of this file. The same windows, channel
filters and customer filter as facts_v15.py must reproduce that ledger's
new-customer revenue per day exactly. If they do not, the split is measuring
something else and the build stops.
"""
import csv, io, json, os, collections

DL = r"C:\Users\PietroS\Downloads"
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(io.open(os.path.join(HERE, "facts_v15.json"), encoding="utf-8"))

rows = list(csv.DictReader(io.open(os.path.join(DL, "f_linerevenue.csv"),
                                   encoding="utf-8-sig", newline="")))
num = lambda x: float((x or "").strip() or 0)

# identical to facts_v15.py: the buy box never appears on TikTok, and the two
# channels the subscription app bills renewals through are not placed orders
TT = "AfterShip for TikTok"
RENEW = {"Skio Subscriptions (YC S20)", "Heart & Soil Subscriptions"}
# The Lobby is creator seeding, excluded from facts_v15.py since 2026-09-23. It books
# $0 gross and $0 net, so dropping it changes nothing here today. It is filtered
# anyway, so the two ledgers cannot drift apart if that channel ever books revenue.
SEED = {"The Lobby"}
R = F["range"]
CHANGE_DAY, SALE_END = R["change_day"], R["sale_end"]
PROMO0, PROMO1 = R["promo_start"], R["promo_end"]

days = sorted(set(r["Day"] for r in rows))
PRE = [d for d in days if d < CHANGE_DAY and not (PROMO0 <= d <= PROMO1)]
POST = [d for d in days if d > SALE_END]
assert len(PRE) == R["pre_days"] and len(POST) == R["post_days"], \
    "windows do not match the ledger: %d/%d pre, %d/%d post" % (
        len(PRE), R["pre_days"], len(POST), R["post_days"])

keep = lambda r: (r["New or returning customer"].strip() == "New"
                  and r["Sales channel"].strip() != TT
                  and r["Sales channel"].strip() not in RENEW
                  and r["Sales channel"].strip() not in SEED)

sub, one = collections.defaultdict(float), collections.defaultdict(float)
for r in rows:
    if not keep(r):
        continue
    kind = r["Subscription or one-time"].strip()
    v = num(r["Net sales"])
    if kind == "subscription":
        sub[r["Day"]] += v
    else:
        # one_time, plus a small negative residue of refunds carrying no line
        # type at all. It is 0.04 percent of revenue and lives with the
        # non-subscription side so that the two groups sum to the ledger total.
        one[r["Day"]] += v

tot = lambda ds, b: sum(b[d] for d in ds)
c = F["commerce"]
W = {}
for name, ds, want in (("pre", PRE, c["rev_day_pre"]), ("post", POST, c["rev_day_post"])):
    s, o = tot(ds, sub), tot(ds, one)
    n = float(len(ds))
    got = (s + o) / n
    assert abs(got - want) < 0.005, \
        "%s revenue per day is %.4f here and %.4f in facts_v15.json" % (name, got, want)
    W[name] = {
        "days": len(ds),
        "sub_total": round(s, 2), "one_total": round(o, 2),
        "sub_day": round(s / n, 2), "one_day": round(o / n, 2), "tot_day": round(got, 2),
        "share": round(100.0 * s / (s + o), 4),
    }

subord = {"pre": c["subs_day_pre"], "post": c["subs_day_post"]}
aov = {"pre": c["aov_pre"], "post": c["aov_post"]}
tr = {k: F["takerate"]["headline"][k]["r"] for k in ("pre", "post")}
for k in ("pre", "post"):
    W[k]["sub_per_order"] = round(W[k]["sub_day"] / subord[k], 4)
    # the share is take rate x (subscription dollars per subscribing order) / AOV.
    # It is an identity, not a model, so it has to close to the rounding floor.
    ident = tr[k] / 100.0 * W[k]["sub_per_order"] / aov[k] * 100.0
    assert abs(ident - W[k]["share"]) < 0.01, \
        "%s identity does not close: %.4f vs %.4f" % (k, ident, W[k]["share"])

OUT = {
    "_provenance": {
        "source": "Shopify line-basis sales export with net_sales, f_linerevenue.csv",
        "pulled": R["pulled"],
        "range": "%s to %s" % (R["start"], R["end"]),
        "note": ("New-customer net sales split by line type. Reproduces "
                 "facts_v15.json new-customer revenue per day exactly on both "
                 "windows, and the take-rate identity closes on both."),
    },
    "windows": W,
    "delta": {
        "share_pt": round(W["post"]["share"] - W["pre"]["share"], 4),
        "sub_day_pct": round(100.0 * (W["post"]["sub_day"] / W["pre"]["sub_day"] - 1), 4),
        "one_day_pct": round(100.0 * (W["post"]["one_day"] / W["pre"]["one_day"] - 1), 4),
        "sub_per_order_pct": round(
            100.0 * (W["post"]["sub_per_order"] / W["pre"]["sub_per_order"] - 1), 4),
    },
}
io.open(os.path.join(HERE, "rev_facts.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(OUT, indent=2, ensure_ascii=False) + "\n")

print("gate passed: revenue per day reproduces facts_v15.json on both windows")
print("identity passed: take rate x sub-dollars-per-subscribing-order / AOV = share")
print()
print("  %-28s %12s %12s %10s" % ("", "before", "since", "change"))
print("  %-28s %11.2f%% %11.2f%% %+9.2f pt"
      % ("orders with a subscription", tr["pre"], tr["post"], tr["post"] - tr["pre"]))
print("  %-28s %11.2f%% %11.2f%% %+9.2f pt"
      % ("subscription share of revenue", W["pre"]["share"], W["post"]["share"],
         OUT["delta"]["share_pt"]))
print("  %-28s %12.2f %12.2f %+9.2f%%"
      % ("sub $ per subscribing order", W["pre"]["sub_per_order"],
         W["post"]["sub_per_order"], OUT["delta"]["sub_per_order_pct"]))
print("  %-28s %12.2f %12.2f %+9.2f%%"
      % ("subscription revenue / day", W["pre"]["sub_day"], W["post"]["sub_day"],
         OUT["delta"]["sub_day_pct"]))
print("  %-28s %12.2f %12.2f %+9.2f%%"
      % ("other revenue / day", W["pre"]["one_day"], W["post"]["one_day"],
         OUT["delta"]["one_day_pct"]))
print("\nwrote rev_facts.json")
