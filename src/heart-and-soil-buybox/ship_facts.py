# -*- coding: utf-8 -*-
"""Rebuild ship_facts.json: shipping protection, and the revenue split with it removed.

Reads two exports, the same line-basis sales query run once per line type, with a
product and a channel dimension and a daily timeseries:

    FROM sales
    SHOW orders, net_sales, ordered_item_quantity
    WHERE new_or_returning_customer = 'new' AND subscription_or_one_time = '<type>'
    GROUP BY product_title, sales_channel
    TIMESERIES day
    SINCE 2026-07-20 UNTIL 2026-09-20

Both are needed, and daily. Shipping protection is written as a subscription line
before 2026-09-03 and as a one-time line after it: 115 a day to 13 on the subscription
side, 81 a day to 207 on the one-time side, switching over on the day the new buy box
went live. In total it barely moved. Reading either side alone therefore says something
false, and reading it weekly blurs the switch across the Labor Day week.

That matters because the revenue split in the report is subscription against everything
else. A line that crosses that boundary mid-analysis is not comparable across the two
windows, exactly as the seeding channel was not comparable across them. So the split is
also computed with shipping protection removed from both buckets and both windows,
which is the like-for-like measure of product revenue and what the report states.

The gate: filtered to the report's channels, each export must reproduce the net sales
that rev_facts.py reads from the line-basis export for its own line type, on both
windows, or it is measuring a different population and nothing is written.
"""
import csv, io, json, os

DL = os.environ.get("DTCPG_EXPORTS_DIR", os.path.join(os.path.expanduser("~"), "Downloads"))
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(io.open(os.path.join(HERE, "facts_v15.json"), encoding="utf-8"))
RV = json.load(io.open(os.path.join(HERE, "rev_facts.json"), encoding="utf-8"))

def load(n):
    with io.open(os.path.join(DL, n), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

ONE = load("sales_daily.csv")                             # one_time lines by product
SUB = load("Q-tests - 2026-07-20 - 2026-09-20 (1).csv")   # subscription lines by product
num = lambda x: float((x or "").strip() or 0)

DROP = {"Skio Subscriptions (YC S20)", "Heart & Soil Subscriptions",
        "The Lobby", "AfterShip for TikTok"}
SP = "Shipping Protection"
R, c = F["range"], F["commerce"]
days = sorted(set(r["Day"] for r in ONE))
PRE = [d for d in days if d < R["change_day"] and not (R["promo_start"] <= d <= R["promo_end"])]
POST = [d for d in days if d > R["sale_end"]]
assert len(PRE) == R["pre_days"] and len(POST) == R["post_days"], "windows do not match the ledger"

def tally(rows, ds, only_sp=False):
    o = ns = 0.0
    for r in rows:
        if r["Sales channel"] in DROP or r["Day"] not in ds:
            continue
        if only_sp and r["Product title"] != SP:
            continue
        o += num(r["Orders"]); ns += num(r["Net sales"])
    return o, ns

W, PROD = {}, {}
for k, ds in (("pre", PRE), ("post", POST)):
    n = float(len(ds))
    for rows, side, want in ((ONE, "one", RV["windows"][k]["one_time_total"]),
                             (SUB, "sub", RV["windows"][k]["sub_total"])):
        _, all_ns = tally(rows, ds)
        assert abs(all_ns - want) < 0.01, \
            "%s %s net sales are %.2f here and %.2f in rev_facts.json" % (k, side, all_ns, want)
    o_one, r_one = tally(ONE, ds, only_sp=True)
    o_sub, r_sub = tally(SUB, ds, only_sp=True)
    W[k] = {"one_lines_day": round(o_one / n, 2), "sub_lines_day": round(o_sub / n, 2),
            "all_lines_day": round((o_one + o_sub) / n, 2),
            "one_rev_day": round(r_one / n, 2), "sub_rev_day": round(r_sub / n, 2),
            "all_rev_day": round((r_one + r_sub) / n, 2),
            "per_line": round((r_one + r_sub) / (o_one + o_sub), 4)}
    # the split with shipping protection out of both buckets: product revenue only
    ps = RV["windows"][k]["sub_day"] - r_sub / n
    po = RV["windows"][k]["one_day"] - r_one / n
    PROD[k] = {"sub_day": round(ps, 2), "one_day": round(po, 2),
               "share": round(100.0 * ps / (ps + po), 4)}

# the switch is a single day, so state which one rather than leaving it to be inferred
_sw = None
for i in range(1, len(days)):
    a, b = days[i - 1], days[i]
    pa = tally(SUB, [a], True)[0]; pb = tally(SUB, [b], True)[0]
    if pa > 100 and pb < pa * 0.5:
        _sw = b
        break
assert _sw == R["change_day"], "the switch lands on %s, not the change day" % _sw

OUT = {
    "_provenance": {
        "source": "Shopify line-basis sales exports by product and channel, one per line type",
        "pulled": R["pulled"], "switch_day": _sw,
        "note": ("Shipping protection moves from a subscription line to a one-time line on "
                 "the day the new buy box goes live. Total volume barely changes. Both "
                 "exports reproduce rev_facts.json on both windows."),
    },
    "windows": W,
    "product_only": PROD,
    "total_lines_pct": round(100.0 * (W["post"]["all_lines_day"] / W["pre"]["all_lines_day"] - 1), 4),
    "aov_part_pre": round(W["pre"]["all_rev_day"] / c["orders_day_pre"], 4),
    "aov_part_post": round(W["post"]["all_rev_day"] / c["orders_day_post"], 4),
}
OUT["share_of_aov_rise"] = round(
    100.0 * (OUT["aov_part_post"] - OUT["aov_part_pre"]) / (c["aov_post"] - c["aov_pre"]), 4)
assert 0 < OUT["share_of_aov_rise"] < 100, "AOV share is outside a sane range"

io.open(os.path.join(HERE, "ship_facts.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(OUT, indent=2, ensure_ascii=False) + "\n")
print("gate passed: both exports reproduce rev_facts.json on both windows")
print("switch lands on %s, the day the buy box went live\n" % _sw)
print("%-30s %10s %10s"%("shipping protection /day","before","since"))
for lab, key in (("as a one-time line","one_lines_day"),("as a subscription line","sub_lines_day"),
                 ("total lines","all_lines_day"),("total revenue","all_rev_day")):
    print("  %-28s %10.1f %10.1f" % (lab, W["pre"][key], W["post"][key]))
print("  %-28s %9.1f%%" % ("total lines, change", OUT["total_lines_pct"]))
print()
print("%-30s %10s %10s %9s"%("product revenue only","before","since","change"))
print("  %-28s %10.2f %10.2f %+8.2f%%"%("subscription /day",PROD["pre"]["sub_day"],PROD["post"]["sub_day"],
      100*(PROD["post"]["sub_day"]/PROD["pre"]["sub_day"]-1)))
print("  %-28s %10.2f %10.2f %+8.2f%%"%("non-subscription /day",PROD["pre"]["one_day"],PROD["post"]["one_day"],
      100*(PROD["post"]["one_day"]/PROD["pre"]["one_day"]-1)))
print("  %-28s %9.2f%% %9.2f%% %+8.2f pt"%("subscription share",PROD["pre"]["share"],PROD["post"]["share"],
      PROD["post"]["share"]-PROD["pre"]["share"]))
print("\nwrote ship_facts.json")
