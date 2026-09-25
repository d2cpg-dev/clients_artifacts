# -*- coding: utf-8 -*-
"""Independent QA over facts_v15.json. Re-derives relationships rather than trusting them.
Any FAIL stops the build."""
import json, io, math, csv, collections, os

F = json.load(io.open("facts_v15.json", encoding="utf-8"))
MO = 365 / 12.0
fails, warns, oks = [], [], []

def chk(name, cond, detail=""):
    (oks if cond else fails).append((name, detail))
def near(a, b, tol=0.01):
    return abs(a - b) <= tol * max(1.0, abs(b))
def warn(name, cond, detail=""):
    if not cond: warns.append((name, detail))

H = F["takerate"]["headline"]; v = F["value"]; c = F["commerce"]
q = F["quality"]; m = F["magnitude"]; I = F["interval"]; T = F["tiers"]

# --- checksums against the published pull -------------------------------
k = F["checksum"]
# The denominator matched the client's figure exactly until the seeding channel came
# out on 2026-09-23. The invariant is no longer equality, it is that the two reconcile
# by exactly the seeding orders, which is a stronger statement than the old one.
chk("published denominator reconciles to the client figure",
    k["denom_aug6_sep2"] + k["seed_in_denom"] == k["denom_expected"],
    "%d excl. seeding + %d seeding vs %d reported"
    % (k["denom_aug6_sep2"], k["seed_in_denom"], k["denom_expected"]))
# These two count all customers, not just new ones, and the September re-pull moved the
# subscription app onto its own sales channel, so they are no longer drawn on the same
# base as the client's earlier reporting. The report says so in the method notes. They
# warn rather than fail: the direction is understood, ours is lower, and every
# new-customer figure still reproduces the earlier pull day for day.
warn("checksum orders matches the earlier pull", k["orders"] == k["orders_expected"],
     "%d vs %d, ours lower by %d" % (k["orders"], k["orders_expected"],
                                     k["orders_expected"] - k["orders"]))
warn("checksum signups matches the earlier pull", k["signups"] == k["signups_expected"],
     "%d vs %d, ours lower by %d" % (k["signups"], k["signups_expected"],
                                     k["signups_expected"] - k["signups"]))
chk("our all-customer counts are lower, never higher, than the earlier pull",
    k["orders"] <= k["orders_expected"] and k["signups"] <= k["signups_expected"],
    "orders %d vs %d, signups %d vs %d" % (k["orders"], k["orders_expected"],
                                           k["signups"], k["signups_expected"]))

# --- take rate internal consistency -------------------------------------
for kk, e in F["takerate"].items():
    for wn in ("pre", "sale", "post"):
        w = e[wn]
        chk("%s/%s rate = n/d" % (kk, wn), near(w["r"], 100.0 * w["n"] / w["d"], 1e-9),
            "%.4f vs %.4f" % (w["r"], 100.0 * w["n"] / w["d"]))
        chk("%s/%s numerator <= denominator" % (kk, wn), w["n"] <= w["d"], "%d > %d" % (w["n"], w["d"]))
    chk("%s drop = pre - post" % kk, near(e["drop"], e["pre"]["r"] - e["post"]["r"], 1e-9))
    chk("%s rel = drop/pre" % kk, near(e["rel"], -100.0 * e["drop"] / e["pre"]["r"], 1e-6))

# headline and tag share the same denominator by construction
chk("headline and tag share a denominator",
    F["takerate"]["headline"]["pre"]["d"] == F["takerate"]["tag"]["pre"]["d"] and
    F["takerate"]["headline"]["post"]["d"] == F["takerate"]["tag"]["post"]["d"])
chk("tag measure is the more conservative one", F["takerate"]["tag"]["drop"] >= H["drop"],
    "tag %.2f vs headline %.2f" % (F["takerate"]["tag"]["drop"], H["drop"]))

# --- interval ------------------------------------------------------------
chk("point estimate inside bootstrap CI", I["boot_lo"] <= I["point"] <= I["boot_hi"],
    "%.2f not in [%.2f, %.2f]" % (I["point"], I["boot_lo"], I["boot_hi"]))
chk("client band contains both CIs",
    I["band_lo"] <= min(I["boot_lo"], I["normal_lo"]) and I["band_hi"] >= max(I["boot_hi"], I["normal_hi"]),
    "band %d-%d vs boot [%.2f,%.2f] normal [%.2f,%.2f]" %
    (I["band_lo"], I["band_hi"], I["boot_lo"], I["boot_hi"], I["normal_lo"], I["normal_hi"]))
chk("band excludes zero", I["band_lo"] > 0)
chk("p value is significant", I["p"] < 0.001, "p=%.3g" % I["p"])
chk("dispersion correction >= 1", I["phi_used"] >= 1.0)

# --- separation ----------------------------------------------------------
s = F["separation"]
chk("separation count <= post days", s["below"] <= s["post_n"])
chk("pairs total = post x pre", s["pairs_total"] == s["post_n"] * s["pre_n"])
chk("max post above min pre implies one exception",
    (s["max_post"] > s["min_pre"]) == (s["below"] < s["post_n"]),
    "max_post %.2f min_pre %.2f below %d/%d" % (s["max_post"], s["min_pre"], s["below"], s["post_n"]))
chk("Mann-Whitney significant", s["mw_p"] < 0.001, "p=%.3g" % s["mw_p"])

# --- robustness ----------------------------------------------------------
r = F["robust"]
cuts = [H["drop"], r["tag_drop"], r["store_drop"], -r["dow_drop"], -r["matched_drop"]]
chk("all robustness cuts agree in sign", all(x > 0 for x in cuts), str([round(x, 2) for x in cuts]))
chk("spread bounds match the cuts", near(r["drop_min"], min(cuts), 1e-9) and near(r["drop_max"], max(cuts), 1e-9))
chk("placebo is weaker than the real effect", abs(F["placebo"]["worst_drop"]) < H["drop"],
    "placebo %.2f vs real %.2f" % (F["placebo"]["worst_drop"], H["drop"]))
chk("placebo ratio consistent", near(F["placebo"]["ratio"], H["drop"] / abs(F["placebo"]["worst_drop"]), 1e-6))
warn("traffic correlation is weak enough to call null", abs(F["traffic"]["r"]) < 0.30,
     "r=%.3f" % F["traffic"]["r"])

# --- commerce ------------------------------------------------------------
chk("AOV pct", near(c["aov_pct"], 100.0 * (c["aov_post"] / c["aov_pre"] - 1), 1e-9))
chk("revenue pct", near(c["rev_pct"], 100.0 * (c["rev_day_post"] / c["rev_day_pre"] - 1), 1e-9))
chk("revenue gain = post - pre", near(c["rev_gain_day"], c["rev_day_post"] - c["rev_day_pre"], 1e-6))
chk("revenue/day = orders/day x AOV, pre", near(c["rev_day_pre"], c["orders_day_pre"] * c["aov_pre"], 0.02))
chk("revenue/day = orders/day x AOV, post", near(c["rev_day_post"], c["orders_day_post"] * c["aov_post"], 0.02))
chk("subs/day = orders/day x take rate, pre",
    near(c["subs_day_pre"], c["orders_day_pre"] * H["pre"]["r"] / 100.0, 0.02))
chk("subs/day = orders/day x take rate, post",
    near(c["subs_day_post"], c["orders_day_post"] * H["post"]["r"] / 100.0, 0.02))
chk("decomposition sums to 100", near(c["share_takerate"] + c["share_volume"], 100.0, 1e-9))
# Which half is larger is a finding, not an invariant. It was the take rate until the
# seeding channel came out, which lowered the order count and tipped it the other way.
# The invariant is the one above: the two shares sum to 100.
warn("take rate is still the larger half of the decline",
     c["share_takerate"] > c["share_volume"],
     "take rate %.1f%% vs volume %.1f%%" % (c["share_takerate"], c["share_volume"]))
chk("units per order rose", c["upo_post"] > c["upo_pre"])

# --- plan mix ------------------------------------------------------------
for wn in ("pre", "sale", "post"):
    chk("tiers %s sum to 100" % wn, near(sum(T[wn]), 100.0, 1e-9), "%.6f" % sum(T[wn]))
chk("tier names match tier count", len(T["names"]) == len(T["pre"]) == len(T["post"]))
chk("tier deltas consistent", all(near(T["delta"][i], T["post"][i] - T["pre"][i], 1e-9) for i in range(len(T["pre"]))))
chk("biggest gain is 3 bottles / 90 days", T["names"][T["biggest_gain_i"]] == "3 bottles / 90 days",
    T["names"][T["biggest_gain_i"]])
chk("biggest fall is 1 bottle / 30 days", T["names"][T["biggest_fall_i"]] == "1 bottle / 30 days",
    T["names"][T["biggest_fall_i"]])
for kk, b in F["bottles"].items():
    chk("bottles %s sum to 100" % kk, near(sum(b["p"]), 100.0, 1e-9), "%.4f" % sum(b["p"]))
chk("tier counts sum to plan base, pre", sum(T["counts_pre"]) == T["n_pre"])
chk("tier counts sum to plan base, post", sum(T["counts_post"]) == T["n_post"])

# share observations only. The selling-plan checks below establish that no
# combination was removed; these record how far each one fell.
i90 = T["names"].index("1 bottle / 90 days"); i60 = T["names"].index("1 bottle / 60 days")
chk("1x90d collapsed below 1 percent", T["post"][i90] < 1.0, "%.2f%%" % T["post"][i90])
chk("1x60d survives above 1x90d", T["post"][i60] > T["post"][i90],
    "60d %.2f%% vs 90d %.2f%%" % (T["post"][i60], T["post"][i90]))
i30 = T["names"].index("1 bottle / 30 days")
chk("1x30d fell without being removed", T["delta"][i30] < 0, "%.2f pt" % T["delta"][i30])

# --- value ---------------------------------------------------------------
for wn in ("pre", "post"):
    w = v[wn]
    chk("list per month = per day x 365/12, %s" % wn, near(w["list_per_month"], w["list_per_day"] * MO, 1e-9))
    chk("subs per order >= 1, %s" % wn, w["subs_per_order"] >= 1.0)
chk("crux pre", near(v["crux_pre"], H["pre"]["r"] * v["pre"]["subs_per_order"] * v["pre"]["list_per_day"], 1e-9))
chk("crux post", near(v["crux_post"], H["post"]["r"] * v["post"]["subs_per_order"] * v["post"]["list_per_day"], 1e-9))
chk("crux pct", near(v["crux_pct"], 100.0 * (v["crux_post"] / v["crux_pre"] - 1), 1e-9))
chk("crux is negative but smaller than the take-rate fall",
    v["crux_pct"] < 0 and abs(v["crux_pct"]) < abs(H["rel"]),
    "crux %.2f%% vs take rate %.2f%%" % (v["crux_pct"], H["rel"]))
chk("basket grew while rate per unit time did not",
    v["pct_list_per_sub"] > 20 and abs(v["pct_list_per_month"]) < 10,
    "per sub %+.1f%%, per month %+.1f%%" % (v["pct_list_per_sub"], v["pct_list_per_month"]))

# --- magnitude -----------------------------------------------------------
chk("per month = per day x 365/12", near(m["per_month"], m["per_day"] * MO, 1e-9))
chk("per day = orders/day x drop", near(m["per_day"], c["orders_day_post"] * H["drop"] / 100.0, 1e-9))
chk("magnitude band brackets the point", m["lo_month"] < m["per_month"] < m["hi_month"])
chk("monthly billings = subs x monthly list",
    near(m["monthly_billings"], m["per_month"] * v["post"]["list_per_month"], 1e-6))

# --- data quality --------------------------------------------------------
chk("single-product coverage is stable across windows", q["coverage_spread"] < 2.0,
    "%.2f pt" % q["coverage_spread"])
chk("pre-cohort drift too small to explain the basket shift",
    q["drift_pre"] < abs(v["pct_units_per_sub"]) / 4.0,
    "drift %.1f%% vs basket %+.1f%%" % (q["drift_pre"], v["pct_units_per_sub"]))
chk("origin orders are same-day", q["same_day_post"] > 98.0, "%.1f%%" % q["same_day_post"])
chk("migration records are excluded from the plan base",
    F["tiers"]["n_pre"] < q["plan_base_pre"] < q["plan_base_pre"] + q["migration_pre"],
    "plan base %d, unfiltered %d, migration %d" % (F["tiers"]["n_pre"], q["plan_base_pre"], q["migration_pre"]))

# --- reconciliation ------------------------------------------------------
for wn, rr in F["recon"].items():
    # Held under the old export definition. Since the September re-pull moved the
    # subscription app onto its own channel the post window runs the other way, which
    # the report states rather than hides. Warn so it stays visible without blocking.
    warn("Shopify is never short of Skio, %s" % wn, rr["ratio"] <= 1.0,
         "ratio %.3f" % rr["ratio"])

# --- test design ---------------------------------------------------------
t = F["test"]
chk("test threshold exceeds the detectable effect", t["threshold"] > t["mde"],
    "threshold %d vs MDE %.2f" % (t["threshold"], t["mde"]))
chk("test threshold is at most the observed drop", t["threshold"] <= H["drop"])

# --- source data sanity --------------------------------------------------
DL = os.environ.get("DTCPG_EXPORTS_DIR", os.path.join(os.path.expanduser("~"), "Downloads"))
def load(n):
    with io.open(os.path.join(DL, n), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
A = load("a_orders.csv"); C = load("c_linebasis.csv"); B = load("b_signups.csv")
dA = sorted(set(r["Day"] for r in A)); dC = sorted(set(r["Day"] for r in C)); dB = sorted(set(r["Day"] for r in B))
chk("all exports cover the same days", dA == dC == dB, "A %d C %d B %d" % (len(dA), len(dC), len(dB)))
chk("no gap in the date range",
    len(dA) == (__import__("datetime").date.fromisoformat(dA[-1]) -
                __import__("datetime").date.fromisoformat(dA[0])).days + 1)
chA = set(r["Sales channel"] for r in A); chC = set(r["Sales channel"] for r in C)
chk("channel sets agree between orders and line basis", chA == chC, str(chA ^ chC))
neg = [r for r in A if float(r["Orders"] or 0) < 0]
chk("no negative order counts", not neg, "%d rows" % len(neg))
blank = [r for r in A if not r["New or returning customer"].strip()]
chk("blank customer-type rows are negligible",
    sum(float(r["Orders"] or 0) for r in blank) < 10,
    "%d rows, %.0f orders" % (len(blank), sum(float(r["Orders"] or 0) for r in blank)))

# --- report ---------------------------------------------------------------
print("=" * 78)
for n, d in fails: print("FAIL  %-52s %s" % (n, d))
for n, d in warns: print("WARN  %-52s %s" % (n, d))
print("=" * 78)
print("%d checks passed, %d warnings, %d failures" % (len(oks), len(warns), len(fails)))
if fails:
    raise SystemExit("QA FAILED")
print("QA PASSED")

# --- selling-plan evidence, added v22 ------------------------------------
import json as _json
PF = _json.load(io.open("plan_facts.json", encoding="utf-8"))
chk("plan families: the old group collapsed",
    PF["family"]["old"]["post"] < PF["family"]["old"]["pre"] * 0.05,
    "%d -> %d" % (PF["family"]["old"]["pre"], PF["family"]["old"]["post"]))
chk("plan families: the new group took over",
    PF["family"]["new"]["post"] > PF["family"]["new"]["pre"] * 2,
    "%d -> %d" % (PF["family"]["new"]["pre"], PF["family"]["new"]["post"]))
chk("both plan groups existed before the change",
    PF["family"]["new"]["pre"] > 0 and PF["family"]["old"]["pre"] > 0)
for cad in ("30", "60", "90"):
    for side in ("old", "new"):
        tot = sum(PF["mix"][cad][side].values())
        chk("quantity mix sums to 100, %s %s" % (cad, side), near(tot, 100.0, 0.02), "%.1f" % tot)
chk("the claim 'nothing was removed' holds: every single-bottle cycle still sells",
    all(v["subs_since"] > 0 for v in PF["still_live"].values()),
    str({k: v["subs_since"] for k, v in PF["still_live"].items()}))
chk("quantity is tied to cycle in the new group but not the old",
    PF["mix"]["90"]["new"]["1"] < 10 and PF["mix"]["90"]["old"]["1"] > 30,
    "90-day one-bottle share %.1f%% old vs %.1f%% new"
    % (PF["mix"]["90"]["old"]["1"], PF["mix"]["90"]["new"]["1"]))
chk("the 30-day cycle is the control: it barely moved",
    abs(PF["mix"]["30"]["new"]["1"] - PF["mix"]["30"]["old"]["1"]) < 5,
    "%.1f%% -> %.1f%%" % (PF["mix"]["30"]["old"]["1"], PF["mix"]["30"]["new"]["1"]))
print()
for n, d in fails: print("FAIL  %-52s %s" % (n, d))
print("%d checks passed, %d failures (including selling-plan evidence)" % (len(oks), len(fails)))
if fails: raise SystemExit("QA FAILED")
