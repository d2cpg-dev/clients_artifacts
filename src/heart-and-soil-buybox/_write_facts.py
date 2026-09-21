# -*- coding: utf-8 -*-
"""Write bq_facts.json from the 2026-09-22 Skio pull.

Window 4 runs Sep 8 - Sep 20 (13 days) instead of Sep 8 - Sep 16 (9).
list_per_day is the daily rate of committed spend, sum(list_value / cadence),
verified to reproduce the previous pull exactly on all four windows.
"""
import csv, io, json, collections

# from the window-scalars query, 2026-09-22
SCALARS = {
    #            all_subs all_orig  migration  same_day avg_days  sp_subs sp_orig  sp_units  sp_list_value  days
    "1_pre":      (15388,  14931,     17326,    15354,   0.002,   12949,  12556,   20364,   1192959.1,  40),
    "2_augpromo": ( 2414,   2342,     55410,     2411,   0.001,    2088,   2026,    3509,    204687.0,   5),
    "3_sale":     ( 2893,   2691,         0,     2886,   0.002,    2467,   2299,    6151,    356344.2,   5),
    "4_after":    ( 4357,   4080,         0,     4336,   0.003,    3689,   3452,    8142,    474567.3,  13),
}
# line edits, variant or quantity, from AnalyticsSubscriptionLineStateChangeTable
EDITS = {"1_pre": (481, 92), "2_augpromo": (100, 9), "3_sale": (41, 36), "4_after": (26, 25)}

plan = list(csv.DictReader(io.open("bq_plan.csv", encoding="utf-8")))
rate = collections.defaultdict(float)
for r in plan:
    rate[r["win"]] += float(r["list_value"]) / int(r["cadence"])

prev = json.load(io.open("bq_facts.json", encoding="utf-8"))
B = {
    "_provenance": {
        "source": "largedata-380204.skio_heart_and_soil via dtcpg-platform billing",
        "pulled": "2026-09-22",
        "note": ("Window 4 extended to Sep 8 - Sep 20. Single-product set re-derived from "
                 "product titles and pinned in single_products.csv; it yields 21 products, "
                 "matching the prior count, and reproduces coverage to within 0.11 percent. "
                 "Line-edit drift is now counted from AnalyticsSubscriptionLineStateChangeTable "
                 "as a variant or quantity change, excluding price changes, which the earlier "
                 "pull defined differently and which moves drift_pre from 4.4 to 3.1 percent."),
        "queries": 14,
        "approx_cost_usd": 0.002,
    },
    "windows": {}, "window_days": {}, "all_subs_unfiltered": {},
    "migration_records": {}, "origin_order_lag": {"avg_days": {}, "same_day": {},
                                                  "lag_7plus": {}, "no_shopify_platform_id": {}},
    "prepaid": prev.get("prepaid"), "gift": prev.get("gift"), "digital": prev.get("digital"),
    "totals_crosscheck": prev.get("totals_crosscheck"),
    "schema_facts": prev.get("schema_facts"),
    "single_product_ids": 21,
}
for w, (a_subs, a_ord, mig, same, lag, s_subs, s_ord, s_units, s_lv, days) in SCALARS.items():
    ec, e9 = EDITS[w]
    B["windows"][w] = {"subs": s_subs, "origin_orders": s_ord, "units": s_units,
                       "list_value": round(s_lv, 1), "list_per_day": round(rate[w], 4)}
    B["window_days"][w] = days
    B["all_subs_unfiltered"][w] = {"subs": a_subs, "origin_orders": a_ord,
                                   "ever_changed": ec, "changed_within_9d": e9}
    B["migration_records"][w] = mig
    B["origin_order_lag"]["avg_days"][w] = lag
    B["origin_order_lag"]["same_day"][w] = same
    B["origin_order_lag"]["lag_7plus"][w] = 0
    B["origin_order_lag"]["no_shopify_platform_id"][w] = \
        prev["origin_order_lag"].get("no_shopify_platform_id", {}).get(w, 0)

io.open("bq_facts.json", "w", encoding="utf-8", newline="\n").write(
    json.dumps(B, indent=2, ensure_ascii=False) + "\n")
print("wrote bq_facts.json")
print()
print("%-12s %7s %9s %12s %12s %6s" % ("window", "sp_subs", "coverage", "list/day", "list/sub", "days"))
for w in sorted(SCALARS):
    ws, au = B["windows"][w], B["all_subs_unfiltered"][w]
    print("%-12s %7d %8.2f%% %12.2f %12.2f %6d"
          % (w, ws["subs"], 100.0*ws["subs"]/au["subs"], ws["list_per_day"],
             ws["list_value"]/ws["subs"], B["window_days"][w]))
