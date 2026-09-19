# -*- coding: utf-8 -*-
"""Single source of truth for every number in the buy-box report.
Reads the five Shopify exports, the Skio plan-mix pull and the Skio scalars,
computes every figure the prose cites, and writes facts_v15.json.
Nothing in the report template may contain a typed number."""
import csv, json, collections, datetime, io, os, math, random

DL = r"C:\Users\PietroS\Downloads"
def load(n):
    with io.open(os.path.join(DL, n), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
def num(x):
    x = (x or "").strip()
    return float(x) if x else 0.0

A = load("a_orders.csv"); B = load("b_signups.csv"); C = load("c_linebasis.csv")
Dp = load("d_products.csv"); E = load("e_sessions.csv")
BQF = json.load(io.open("bq_facts.json", encoding="utf-8"))
PLAN = list(csv.DictReader(io.open("bq_plan.csv", encoding="utf-8")))

DAYS = sorted(set(r["Day"] for r in A))
TT = "AfterShip for TikTok"
RENEW = {"Skio Subscriptions (YC S20)", "Heart & Soil Subscriptions"}
cust = lambda r: r["New or returning customer"].strip()
issub = lambda r: r["Subscription or one-time"].strip() == "subscription"

CHANGE_DAY = "2026-09-03"; SALE_END = "2026-09-07"; LABOR_DAY = "2026-09-07"
PROMO0, PROMO1 = "2026-08-07", "2026-08-11"
inpromo = lambda d: PROMO0 <= d <= PROMO1
PRE   = [d for d in DAYS if d < CHANGE_DAY and not inpromo(d)]
PROMO = [d for d in DAYS if inpromo(d)]
SALE  = [d for d in DAYS if CHANGE_DAY <= d <= SALE_END]
POST  = [d for d in DAYS if d > SALE_END]

def bag(rows, pred, field="Orders"):
    o = collections.defaultdict(float)
    for r in rows:
        if pred(r): o[r["Day"]] += num(r[field])
    return o

okc = lambda r: r["Sales channel"] != TT
denN = bag(A, lambda r: cust(r) == "New" and okc(r))
nsN  = bag(A, lambda r: cust(r) == "New" and okc(r), "Net sales")
numN = bag(C, lambda r: cust(r) == "New" and okc(r) and issub(r))
numT = bag(B, lambda r: cust(r) == "New" and okc(r))
denR = bag(A, lambda r: cust(r) == "Returning" and okc(r))
numR = bag(C, lambda r: cust(r) == "Returning" and okc(r) and issub(r))
denS = bag(A, lambda r: cust(r) == "New" and r["Sales channel"] == "Online Store")
numS = bag(C, lambda r: cust(r) == "New" and r["Sales channel"] == "Online Store" and issub(r))
sess = {r["Day"]: float(r["Sessions"]) for r in E}
cvr  = {r["Day"]: float(r["Conversion rate"]) * 100 for r in E}

def rate(n, d, ds):
    a = sum(n[x] for x in ds); b = sum(d[x] for x in ds)
    return (100.0 * a / b if b else 0.0), a, b
def mean(xs): return sum(xs) / float(len(xs))

F = {}
F["range"] = dict(start=DAYS[0], end=DAYS[-1], days=len(DAYS),
                  change_day=CHANGE_DAY, labor_day=LABOR_DAY,
                  pre_days=len(PRE), promo_days=len(PROMO), sale_days=len(SALE), post_days=len(POST),
                  promo_start=PROMO0, promo_end=PROMO1, sale_end=SALE_END,
                  pulled="2026-09-18")

# ---------------------------------------------------------------- take rate
DEFS = dict(
  headline=("New customers, excl. TikTok", numN, denN),
  tag     =("New customers, order-tag measure", numT, denN),
  store   =("New customers, online store only", numS, denS),
  ret     =("Returning customers", numR, denR),
)
TR = {}
for k, (label, n, d) in DEFS.items():
    e = dict(label=label)
    for wn, ds in (("pre", PRE), ("promo", PROMO), ("sale", SALE), ("post", POST)):
        r, a, b = rate(n, d, ds)
        e[wn] = dict(r=r, n=int(a), d=int(b))
    e["drop"] = e["pre"]["r"] - e["post"]["r"]
    e["rel"] = 100.0 * (e["post"]["r"] / e["pre"]["r"] - 1.0)
    TR[k] = e
F["takerate"] = TR
H = TR["headline"]

F["single_days"] = dict(
    labor_day=rate(numN, denN, [LABOR_DAY])[0],
    labor_day_orders=int(sum(denN[d] for d in [LABOR_DAY])),
    change_day=rate(numN, denN, [CHANGE_DAY])[0],
    change_day_orders=int(sum(denN[d] for d in [CHANGE_DAY])),
    normal_orders_per_day=mean([denN[d] for d in PRE]),
)
F["single_days"]["labor_day_vs_normal"] = F["single_days"]["labor_day_orders"] / F["single_days"]["normal_orders_per_day"]

# daily distribution separation
pre_daily  = [100.0 * numN[d] / denN[d] for d in PRE]
post_daily = [100.0 * numN[d] / denN[d] for d in POST]
below = sum(1 for x in post_daily if x < min(pre_daily))
pairs_lower = sum(1 for a in post_daily if True for b in pre_daily if a < b)
n1, n2 = len(post_daily), len(pre_daily)
U = float(pairs_lower); mu = n1 * n2 / 2.0
sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
z_mw = (U - mu) / sd
p_mw = math.erfc(abs(z_mw) / math.sqrt(2))
F["separation"] = dict(min_pre=min(pre_daily), max_post=max(post_daily),
                       below=below, post_n=n1, pre_n=n2,
                       pairs_lower=int(pairs_lower), pairs_total=n1 * n2,
                       mw_z=z_mw, mw_p=p_mw)

# overdispersion on the clean pre window
def phi_of(n, d, ds):
    N = sum(d[x] for x in ds); K = sum(n[x] for x in ds); p = K / N
    chi = sum((n[x] - d[x] * p) ** 2 / (d[x] * p * (1 - p)) for x in ds if d[x] > 0)
    return chi / (len(ds) - 1)
phi_pre = phi_of(numN, denN, PRE); phi_post = phi_of(numN, denN, POST)
phi_all = phi_of(numN, denN, PRE + POST)
F["dispersion"] = dict(pre=phi_pre, post=phi_post, pooled=phi_all)

# cluster bootstrap on days
random.seed(20260919)
boot = []
for _ in range(40000):
    a = random.choices(PRE, k=len(PRE)); b = random.choices(POST, k=len(POST))
    ra = 100.0 * sum(numN[d] for d in a) / sum(denN[d] for d in a)
    rb = 100.0 * sum(numN[d] for d in b) / sum(denN[d] for d in b)
    boot.append(rb - ra)
boot.sort()
ci_lo, ci_hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]
# phi-adjusted normal interval, for comparison
phi_use = max(phi_pre, phi_post, 1.0)
p1, t1 = H["pre"]["n"] / float(H["pre"]["d"]), H["pre"]["d"]
p2, t2 = H["post"]["n"] / float(H["post"]["d"]), H["post"]["d"]
se = math.sqrt(phi_use * (p1 * (1 - p1) / t1 + p2 * (1 - p2) / t2)) * 100
F["interval"] = dict(point=H["drop"], boot_lo=-ci_hi, boot_hi=-ci_lo,
                     phi_used=phi_use, normal_lo=H["drop"] - 1.96 * se, normal_hi=H["drop"] + 1.96 * se,
                     se=se, boot_n=len(boot))
# client-facing band: widest of the two, rounded outward to whole points
lo = min(F["interval"]["boot_lo"], F["interval"]["normal_lo"])
hi = max(F["interval"]["boot_hi"], F["interval"]["normal_hi"])
F["interval"]["band_lo"] = int(math.floor(lo))
F["interval"]["band_hi"] = int(math.ceil(hi))
zstat = H["drop"] / se
F["interval"]["z"] = zstat
F["interval"]["p"] = math.erfc(abs(zstat) / math.sqrt(2))

# ---------------------------------------------------------------- robustness
# day-of-week standardisation: reweight PRE to the POST day mix
dow = lambda d: datetime.date.fromisoformat(d).weekday()
pre_by = collections.defaultdict(lambda: [0.0, 0.0])
for d in PRE:
    pre_by[dow(d)][0] += numN[d]; pre_by[dow(d)][1] += denN[d]
w_post = collections.Counter(dow(d) for d in POST); tw = sum(w_post.values())
dow_adj = 100.0 * sum((w_post[k] / float(tw)) * (pre_by[k][0] / pre_by[k][1]) for k in w_post if pre_by[k][1])
# matched traffic
post_sess = mean([sess[d] for d in POST])
matched = [d for d in PRE if sess[d] <= 35000]
m_rate = 100.0 * sum(numN[d] for d in matched) / sum(denN[d] for d in matched)
F["robust"] = dict(
    dow_pre=dow_adj, dow_drop=H["post"]["r"] - dow_adj,
    matched_n=len(matched), matched_sess=mean([sess[d] for d in matched]),
    matched_pre=m_rate, matched_drop=H["post"]["r"] - m_rate, post_sess=post_sess,
    store_drop=TR["store"]["drop"], tag_drop=TR["tag"]["drop"],
)
F["robust"]["drop_min"] = min(H["drop"], TR["tag"]["drop"], TR["store"]["drop"],
                              -F["robust"]["dow_drop"], -F["robust"]["matched_drop"])
F["robust"]["drop_max"] = max(H["drop"], TR["tag"]["drop"], TR["store"]["drop"],
                              -F["robust"]["dow_drop"], -F["robust"]["matched_drop"])

# placebo: pretend the change happened on each earlier date
clean = [d for d in DAYS if not inpromo(d)]
plac = []
for X in clean:
    if X >= CHANGE_DAY: break
    pr = [d for d in clean if d < X]
    po = [d for d in clean if d >= X][:len(POST)]
    if len(pr) < 14 or len(po) < len(POST) or po[-1] >= CHANGE_DAY: continue
    ra = 100.0 * sum(numN[d] for d in pr) / sum(denN[d] for d in pr)
    rb = 100.0 * sum(numN[d] for d in po) / sum(denN[d] for d in po)
    plac.append(rb - ra)
F["placebo"] = dict(n=len(plac), worst_drop=min(plac), best_rise=max(plac),
                    sd=(sum((x - mean(plac)) ** 2 for x in plac) / len(plac)) ** 0.5,
                    ratio=H["drop"] / abs(min(plac)))

# post-window trend: is it recovering?
half = len(POST) // 2
F["trend"] = dict(
    early=100.0 * sum(numN[d] for d in POST[:half]) / sum(denN[d] for d in POST[:half]),
    late=100.0 * sum(numN[d] for d in POST[-half:]) / sum(denN[d] for d in POST[-half:]),
)
F["trend"]["delta"] = F["trend"]["late"] - F["trend"]["early"]

# traffic correlation over the clean pre window
xs = [sess[d] for d in PRE]; ys = pre_daily
mx, my = mean(xs), mean(ys)
F["traffic"] = dict(
    r=sum((a - mx) * (b - my) for a, b in zip(xs, ys)) /
      math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)),
    pre_sess=mx, post_sess=post_sess,
    sess_change=100.0 * (post_sess / mx - 1),
    pre_cvr=mean([cvr[d] for d in PRE]), post_cvr=mean([cvr[d] for d in POST]),
)
F["traffic"]["cvr_change"] = 100.0 * (F["traffic"]["post_cvr"] / F["traffic"]["pre_cvr"] - 1)

# ---------------------------------------------------------------- commerce
def aov(ds): return sum(nsN[d] for d in ds) / sum(denN[d] for d in ds)
F["commerce"] = dict(
    aov_pre=aov(PRE), aov_post=aov(POST),
    orders_day_pre=mean([denN[d] for d in PRE]), orders_day_post=mean([denN[d] for d in POST]),
    rev_day_pre=mean([nsN[d] for d in PRE]), rev_day_post=mean([nsN[d] for d in POST]),
    subs_day_pre=mean([numN[d] for d in PRE]), subs_day_post=mean([numN[d] for d in POST]),
)
c = F["commerce"]
c["aov_pct"] = 100.0 * (c["aov_post"] / c["aov_pre"] - 1)
c["orders_pct"] = 100.0 * (c["orders_day_post"] / c["orders_day_pre"] - 1)
c["rev_pct"] = 100.0 * (c["rev_day_post"] / c["rev_day_pre"] - 1)
c["rev_gain_day"] = c["rev_day_post"] - c["rev_day_pre"]
c["subs_pct"] = 100.0 * (c["subs_day_post"] / c["subs_day_pre"] - 1)
lv, lt = math.log(c["orders_day_post"] / c["orders_day_pre"]), math.log(H["post"]["r"] / H["pre"]["r"])
c["share_takerate"] = 100.0 * lt / (lv + lt)
c["share_volume"] = 100.0 * lv / (lv + lt)

# units per order, excluding renewal channels and TikTok
def upo(ds):
    s = set(ds)
    q = sum(num(r["Quantity ordered"]) for r in Dp
            if r["Day"] in s and r["Sales channel"] not in RENEW and r["Sales channel"] != TT)
    o = sum(num(r["Orders"]) for r in A
            if r["Day"] in s and r["Sales channel"] not in RENEW and r["Sales channel"] != TT and cust(r))
    return q / o
c["upo_pre"], c["upo_post"] = upo(PRE), upo(POST)
c["upo_pct"] = 100.0 * (c["upo_post"] / c["upo_pre"] - 1)

# ---------------------------------------------------------------- plan mix
TIERS = [("1 bottle / 30 days", 30, "1"), ("1 bottle / 60 days", 60, "1"),
         ("1 bottle / 90 days", 90, "1"), ("2 bottles / 60 days", 60, "2"),
         ("3 bottles / 90 days", 90, "3")]
WM = {"1_pre": "pre", "3_sale": "sale", "4_after": "post"}
cnt = {v: collections.Counter() for v in WM.values()}
tot = collections.Counter()
for r in PLAN:
    w = WM.get(r["win"])
    if not w: continue
    s = int(r["subs"]); cad = int(r["cadence"]); ub = r["units_b"]
    cnt[w][(cad, ub)] += s; tot[w] += s
def lrr(vals, total, dp=2):
    q = 10 ** dp
    raw = [100.0 * v / total for v in vals]
    fl = [int(x * q) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: -(raw[i] * q - fl[i]))
    for i in range(int(round(100 * q)) - sum(fl)): fl[order[i % len(fl)]] += 1
    return [x / float(q) for x in fl]
rawvals = {w: [cnt[w][(cad, ub)] for _, cad, ub in TIERS] for w in ("pre", "sale", "post")}
for w in rawvals: rawvals[w].append(tot[w] - sum(rawvals[w]))
shares = {w: lrr(rawvals[w], tot[w]) for w in rawvals}
F["tiers"] = dict(names=[t[0] for t in TIERS] + ["Everything else"],
                  pre=shares["pre"], sale=shares["sale"], post=shares["post"],
                  n_pre=tot["pre"], n_sale=tot["sale"], n_post=tot["post"],
                  counts_pre=rawvals["pre"], counts_post=rawvals["post"])
F["tiers"]["delta"] = [b - a for a, b in zip(shares["pre"], shares["post"])]
F["tiers"]["biggest_gain_i"] = max(range(len(TIERS)), key=lambda i: F["tiers"]["delta"][i])
F["tiers"]["biggest_fall_i"] = min(range(len(TIERS)), key=lambda i: F["tiers"]["delta"][i])

# bottles chosen inside each cadence
BOT = {}
for w, wk in (("pre", "1_pre"), ("post", "4_after")):
    for cad in (30, 60, 90):
        v = [0, 0, 0]
        for r in PLAN:
            if r["win"] != wk or int(r["cadence"]) != cad: continue
            j = 0 if r["units_b"] == "1" else (1 if r["units_b"] == "2" else 2)
            v[j] += int(r["subs"])
        BOT["%s_%d" % (w, cad)] = dict(n=sum(v), p=lrr(v, sum(v), 1))
F["bottles"] = BOT

# per-subscription value, from the Skio pull
BW = BQF["windows"]; MO = 365 / 12.0
def pv(k):
    w = BW[k]
    return dict(subs=w["subs"], units_per_sub=w["units"] / float(w["subs"]),
                list_per_sub=w["list_value"] / w["subs"],
                list_per_day=w["list_per_day"] / w["subs"],
                list_per_month=w["list_per_day"] / w["subs"] * MO,
                subs_per_order=w["subs"] / float(w["origin_orders"]))
F["value"] = dict(pre=pv("1_pre"), sale=pv("3_sale"), post=pv("4_after"))
v = F["value"]
for key in ("units_per_sub", "list_per_sub", "list_per_day", "list_per_month", "subs_per_order"):
    v["pct_" + key] = 100.0 * (v["post"][key] / v["pre"][key] - 1)
# committed value per unit time per 100 new-customer orders
v["crux_pre"] = H["pre"]["r"] * v["pre"]["subs_per_order"] * v["pre"]["list_per_day"]
v["crux_post"] = H["post"]["r"] * v["post"]["subs_per_order"] * v["post"]["list_per_day"]
v["crux_pct"] = 100.0 * (v["crux_post"] / v["crux_pre"] - 1)
# Propagate the take-rate interval through the same chain: hold the measured post rate
# fixed and move the pre rate to each end of the confidence band.
def _crux_at(drop_pts):
    pre_r = H["post"]["r"] + drop_pts
    return 100.0 * (v["crux_post"] / (pre_r * v["pre"]["subs_per_order"] * v["pre"]["list_per_day"]) - 1)
v["crux_at_band_lo"] = _crux_at(F["interval"]["band_lo"])
v["crux_at_band_hi"] = _crux_at(F["interval"]["band_hi"])

# drift and coverage, straight from the Skio scalars
U_ = BQF["all_subs_unfiltered"]
F["quality"] = dict(
    drift_pre=100.0 * U_["1_pre"]["ever_changed"] / U_["1_pre"]["subs"],
    drift_pre_9d=100.0 * U_["1_pre"]["changed_within_9d"] / U_["1_pre"]["subs"],
    drift_post=100.0 * U_["4_after"]["ever_changed"] / U_["4_after"]["subs"],
    coverage_pre=100.0 * BW["1_pre"]["subs"] / U_["1_pre"]["subs"],
    coverage_post=100.0 * BW["4_after"]["subs"] / U_["4_after"]["subs"],
    same_day_post=100.0 * BQF["origin_order_lag"]["same_day"]["4_after"] / U_["4_after"]["subs"],
    lag_avg_post=BQF["origin_order_lag"]["avg_days"]["4_after"],
    migration_promo=BQF["migration_records"]["2_augpromo"],
    migration_pre=BQF["migration_records"]["1_pre"],
    plan_base_pre=U_["1_pre"]["subs"],
)
F["quality"]["coverage_spread"] = abs(F["quality"]["coverage_pre"] - F["quality"]["coverage_post"])

# Shopify vs Skio reconciliation, showing Shopify is never short
csub = bag(C, lambda r: issub(r) and cust(r))
F["recon"] = {}
for wn, ds, key in (("pre", PRE, "1_pre"), ("sale", SALE, "3_sale"), ("post", POST, "4_after")):
    sh = sum(csub[d] for d in ds); bq = U_[key]["origin_orders"]
    F["recon"][wn] = dict(shopify=int(sh), skio=bq, ratio=bq / sh)

# ---------------------------------------------------------------- magnitude
opd = c["orders_day_post"]
F["magnitude"] = dict(
    per_day=opd * H["drop"] / 100.0,
    per_month=opd * H["drop"] / 100.0 * MO,
    lo_month=opd * F["interval"]["band_lo"] / 100.0 * MO,
    hi_month=opd * F["interval"]["band_hi"] / 100.0 * MO,
    monthly_billings=opd * H["drop"] / 100.0 * MO * v["post"]["list_per_month"],
    rev_gain_day=c["rev_gain_day"],
)

# ---------------------------------------------------------------- test design
n_test = opd * 30; n_base = float(H["pre"]["d"])
p_ = 0.55
se_t = math.sqrt(phi_use * p_ * (1 - p_) * (1 / n_test + 1 / n_base)) * 100
F["test"] = dict(orders_30d=n_test, se=se_t, mde=2.8 * se_t,
                 threshold=round(H["drop"] / 2.0), aov_floor=95)

# ---------------------------------------------------------------- checksums
CK0, CK1 = "2026-08-06", "2026-09-09"
ck = [d for d in DAYS if CK0 <= d <= CK1]
F["checksum"] = dict(
    orders=int(sum(num(r["Orders"]) for r in A if CK0 <= r["Day"] <= CK1)),
    orders_expected=30740,
    signups=int(sum(num(r["Orders"]) for r in B if CK0 <= r["Day"] <= CK1)),
    signups_expected=14635,
    denom_aug6_sep2=int(sum(denN[d] for d in DAYS if "2026-08-06" <= d <= "2026-09-02")),
    denom_expected=11823,
)

json.dump(F, io.open("facts_v15.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- ledger
def line(k, val, note=""):
    print("  %-34s %14s   %s" % (k, val, note))
print("=" * 90)
print("RANGE  %s to %s  (%d days)   pre %d / promo %d / sale %d / post %d"
      % (DAYS[0], DAYS[-1], len(DAYS), len(PRE), len(PROMO), len(SALE), len(POST)))
print("=" * 90)
print("TAKE RATE")
for k, e in TR.items():
    print("  %-34s pre %6.2f%%  sale %6.2f%%  post %6.2f%%   drop %5.2f pt  (%+.1f%%)"
          % (e["label"], e["pre"]["r"], e["sale"]["r"], e["post"]["r"], e["drop"], e["rel"]))
line("Labor Day", "%.2f%%" % F["single_days"]["labor_day"],
     "%d orders, %.2fx a normal day" % (F["single_days"]["labor_day_orders"], F["single_days"]["labor_day_vs_normal"]))
line("Day one (Sep 3)", "%.2f%%" % F["single_days"]["change_day"])
line("min pre day / max post day", "%.2f%% / %.2f%%" % (F["separation"]["min_pre"], F["separation"]["max_post"]))
line("post days below lowest pre", "%d of %d" % (F["separation"]["below"], F["separation"]["post_n"]))
line("Mann-Whitney", "z=%.2f p=%.2g" % (F["separation"]["mw_z"], F["separation"]["mw_p"]))
line("dispersion phi", "pre %.2f post %.2f" % (phi_pre, phi_post))
line("bootstrap 95% CI", "[%.2f, %.2f]" % (F["interval"]["boot_lo"], F["interval"]["boot_hi"]), "%d reps" % F["interval"]["boot_n"])
line("normal 95% CI", "[%.2f, %.2f]" % (F["interval"]["normal_lo"], F["interval"]["normal_hi"]))
line("client band", "%d to %d points" % (F["interval"]["band_lo"], F["interval"]["band_hi"]))
line("z / p", "%.2f / %.2g" % (F["interval"]["z"], F["interval"]["p"]))
print("ROBUSTNESS")
line("day-of-week standardised", "%.2f pt" % -F["robust"]["dow_drop"])
line("matched traffic", "%.2f pt" % -F["robust"]["matched_drop"], "%d pre days <=35k sessions" % F["robust"]["matched_n"])
line("online store only", "%.2f pt" % F["robust"]["store_drop"])
line("order-tag measure", "%.2f pt" % F["robust"]["tag_drop"])
line("spread across cuts", "%.1f to %.1f pt" % (F["robust"]["drop_min"], F["robust"]["drop_max"]))
line("placebo", "%d dates, worst %.2f" % (F["placebo"]["n"], F["placebo"]["worst_drop"]),
     "real is %.1fx" % F["placebo"]["ratio"])
line("post trend early->late", "%.2f -> %.2f (%+.2f)" % (F["trend"]["early"], F["trend"]["late"], F["trend"]["delta"]))
line("traffic corr (pre)", "r=%.3f" % F["traffic"]["r"])
line("sessions", "%.0f -> %.0f (%+.1f%%)" % (F["traffic"]["pre_sess"], F["traffic"]["post_sess"], F["traffic"]["sess_change"]))
line("conversion", "%.3f%% -> %.3f%% (%+.1f%%)" % (F["traffic"]["pre_cvr"], F["traffic"]["post_cvr"], F["traffic"]["cvr_change"]))
print("COMMERCE")
line("AOV", "$%.2f -> $%.2f (%+.1f%%)" % (c["aov_pre"], c["aov_post"], c["aov_pct"]))
line("orders/day", "%.1f -> %.1f (%+.1f%%)" % (c["orders_day_pre"], c["orders_day_post"], c["orders_pct"]))
line("revenue/day", "$%.0f -> $%.0f (%+.1f%%)" % (c["rev_day_pre"], c["rev_day_post"], c["rev_pct"]))
line("new subs/day", "%.1f -> %.1f (%+.1f%%)" % (c["subs_day_pre"], c["subs_day_post"], c["subs_pct"]))
line("  split", "%.0f%% take rate / %.0f%% volume" % (c["share_takerate"], c["share_volume"]))
line("units/order", "%.3f -> %.3f (%+.1f%%)" % (c["upo_pre"], c["upo_post"], c["upo_pct"]))
print("PLAN MIX  (n pre %s, post %s)" % (format(tot["pre"], ","), format(tot["post"], ",")))
for i, nm in enumerate(F["tiers"]["names"]):
    print("  %-24s pre %6.2f%%  sale %6.2f%%  post %6.2f%%   %+6.2f pt"
          % (nm, shares["pre"][i], shares["sale"][i], shares["post"][i], F["tiers"]["delta"][i]))
print("VALUE PER SUBSCRIPTION (list basis)")
line("units", "%.3f -> %.3f (%+.1f%%)" % (v["pre"]["units_per_sub"], v["post"]["units_per_sub"], v["pct_units_per_sub"]))
line("list value", "$%.2f -> $%.2f (%+.1f%%)" % (v["pre"]["list_per_sub"], v["post"]["list_per_sub"], v["pct_list_per_sub"]))
line("list per month", "$%.2f -> $%.2f (%+.1f%%)" % (v["pre"]["list_per_month"], v["post"]["list_per_month"], v["pct_list_per_month"]))
line("subs per order", "%.4f -> %.4f (%+.1f%%)" % (v["pre"]["subs_per_order"], v["post"]["subs_per_order"], v["pct_subs_per_order"]))
line("committed $/day per 100", "%.2f -> %.2f (%+.1f%%)" % (v["crux_pre"], v["crux_post"], v["crux_pct"]))
print("MAGNITUDE")
m = F["magnitude"]
line("subscribers not started", "%.1f/day, %.0f/month" % (m["per_day"], m["per_month"]),
     "band %.0f to %.0f" % (m["lo_month"], m["hi_month"]))
line("monthly list billings", "$%.0f" % m["monthly_billings"])
line("revenue gain", "$%.0f/day" % m["rev_gain_day"])
print("DATA QUALITY")
q = F["quality"]
line("plan drift, pre cohort", "%.1f%% ever, %.1f%% in 9d" % (q["drift_pre"], q["drift_pre_9d"]))
line("plan drift, post cohort", "%.1f%%" % q["drift_post"])
line("single-product coverage", "%.1f%% / %.1f%%" % (q["coverage_pre"], q["coverage_post"]),
     "spread %.1f pt" % q["coverage_spread"])
line("origin order same day", "%.1f%%" % q["same_day_post"], "avg lag %.3f d" % q["lag_avg_post"])
line("migration records in promo", format(q["migration_promo"], ","))
print("RECONCILIATION  Skio origin orders / Shopify subscribing orders")
for wn in ("pre", "sale", "post"):
    rr = F["recon"][wn]
    line("  " + wn, "%s / %s = %.3f" % (format(rr["skio"], ","), format(rr["shopify"], ","), rr["ratio"]),
         "Shopify short?" if rr["ratio"] > 1 else "Shopify never short")
print("TEST DESIGN")
line("30-day test orders", format(int(F["test"]["orders_30d"]), ","))
line("minimum detectable", "%.2f pt" % F["test"]["mde"])
line("proposed threshold", "%d pt recovery, AOV floor $%d" % (F["test"]["threshold"], F["test"]["aov_floor"]))
print("CHECKSUMS")
k = F["checksum"]
line("Aug 6 - Sep 9 orders", "%s vs %s" % (format(k["orders"], ","), format(k["orders_expected"], ",")),
     "MATCH" if k["orders"] == k["orders_expected"] else "MISMATCH")
line("Aug 6 - Sep 9 sign-ups", "%s vs %s" % (format(k["signups"], ","), format(k["signups_expected"], ",")),
     "MATCH" if k["signups"] == k["signups_expected"] else "MISMATCH")
line("Aug 6 - Sep 2 denominator", "%s vs %s" % (format(k["denom_aug6_sep2"], ","), format(k["denom_expected"], ",")),
     "MATCH" if k["denom_aug6_sep2"] == k["denom_expected"] else "MISMATCH")
print("=" * 90)
print("wrote facts_v15.json")
