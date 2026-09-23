# -*- coding: utf-8 -*-
"""Rebuild ship_facts.json: what the shipping-protection line does to the figures.

Reads one export, sales_daily.csv, the line-basis sales query with a product and a
channel dimension:

    FROM sales
    SHOW orders, net_sales, ordered_item_quantity
    WHERE new_or_returning_customer = 'new' AND subscription_or_one_time = 'one_time'
    GROUP BY product_title, sales_channel
    TIMESERIES day
    SINCE 2026-07-20 UNTIL 2026-09-20

It has to be daily. The report's post window opens on Sep 8, mid-week, so no run of
whole weeks lines up with it, and the week containing Labor Day pulls the answer from
27 percent to 30 if it is included.

The gate is the point of this file: filtered to the report's channels, this export must
reproduce the one-time net sales that rev_facts.py reads from the line-basis export, on
both windows, or it is measuring a different population and nothing is written.
"""
import csv, io, json, os, collections

DL = r"C:\Users\PietroS\Downloads"
HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(io.open(os.path.join(HERE, "facts_v15.json"), encoding="utf-8"))
RV = json.load(io.open(os.path.join(HERE, "rev_facts.json"), encoding="utf-8"))
rows = list(csv.DictReader(io.open(os.path.join(DL, "sales_daily.csv"),
                                   encoding="utf-8-sig", newline="")))
num = lambda x: float((x or "").strip() or 0)

DROP = {"Skio Subscriptions (YC S20)", "Heart & Soil Subscriptions",
        "The Lobby", "AfterShip for TikTok"}
SP = "Shipping Protection"
R, c = F["range"], F["commerce"]
days = sorted(set(r["Day"] for r in rows))
PRE = [d for d in days if d < R["change_day"] and not (R["promo_start"] <= d <= R["promo_end"])]
POST = [d for d in days if d > R["sale_end"]]
assert len(PRE) == R["pre_days"] and len(POST) == R["post_days"], "windows do not match the ledger"

keep = lambda r: r["Sales channel"] not in DROP
def totals(ds, only_sp=False):
    o = ns = 0.0
    for r in rows:
        if not keep(r) or r["Day"] not in ds:
            continue
        if only_sp and r["Product title"] != SP:
            continue
        o += num(r["Orders"]); ns += num(r["Net sales"])
    return o, ns

W = {}
for k, ds in (("pre", PRE), ("post", POST)):
    _, all_ns = totals(ds)
    want = RV["windows"][k]["one_time_total"]   # one-time lines only, no refund residue
    assert abs(all_ns - want) < 0.01, \
        "%s one-time net sales are %.2f here and %.2f in rev_facts.json" % (k, all_ns, want)
    o, ns = totals(ds, only_sp=True)
    n = float(len(ds))
    W[k] = {"lines_day": round(o / n, 2), "rev_day": round(ns / n, 2),
            "per_line": round(ns / o, 4), "aov_part": round((ns / n) / (
                c["orders_day_pre"] if k == "pre" else c["orders_day_post"]), 4)}

growth = RV["windows"]["post"]["one_day"] - RV["windows"]["pre"]["one_day"]
aov_rise = c["aov_post"] - c["aov_pre"]
OUT = {
    "_provenance": {
        "source": "Shopify line-basis sales export by product and channel, sales_daily.csv",
        "pulled": R["pulled"],
        "note": ("Shipping protection is a one-time line that began appearing on subscription "
                 "orders when the new buy box went live. Reproduces the one-time net sales in "
                 "rev_facts.json exactly on both windows."),
    },
    "windows": W,
    "share_of_nonsub_growth": round(100.0 * (W["post"]["rev_day"] - W["pre"]["rev_day"]) / growth, 4),
    "share_of_aov_rise": round(100.0 * (W["post"]["aov_part"] - W["pre"]["aov_part"]) / aov_rise, 4),
    "aov_cents": round(100.0 * (W["post"]["aov_part"] - W["pre"]["aov_part"]), 2),
}
for _k in ("share_of_nonsub_growth", "share_of_aov_rise"):
    assert 0 < OUT[_k] < 100, "%s is %.2f, outside a sane range" % (_k, OUT[_k])

io.open(os.path.join(HERE, "ship_facts.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(OUT, indent=2, ensure_ascii=False) + "\n")
print("gate passed: one-time net sales reproduce rev_facts.json on both windows")
print("  lines/day          %.1f -> %.1f" % (W["pre"]["lines_day"], W["post"]["lines_day"]))
print("  revenue/day        $%.2f -> $%.2f" % (W["pre"]["rev_day"], W["post"]["rev_day"]))
print("  share of non-sub revenue growth  %.1f%%" % OUT["share_of_nonsub_growth"])
print("  share of the AOV rise            %.1f%%  (%.0f cents of $%.2f)"
      % (OUT["share_of_aov_rise"], OUT["aov_cents"], aov_rise))
print("\nwrote ship_facts.json")
