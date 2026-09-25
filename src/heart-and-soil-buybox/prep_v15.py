# -*- coding: utf-8 -*-
"""Chart payload for the v15 report. Series come from the exports; every window figure
is taken from facts_v15.json so the charts and the prose cannot disagree."""
import csv, json, collections, datetime, io, os

DL = os.environ.get("DTCPG_EXPORTS_DIR", os.path.join(os.path.expanduser("~"), "Downloads"))
def load(n):
    with io.open(os.path.join(DL, n), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
def num(x):
    x = (x or "").strip()
    return float(x) if x else 0.0

F = json.load(io.open("facts_v15.json", encoding="utf-8"))
A = load("a_orders.csv"); B = load("b_signups.csv"); C = load("c_linebasis.csv"); E = load("e_sessions.csv")

# These must match facts_v15.py exactly. They did not, and the plotted series drifted
# from the prose for a long time without anything catching it:
#   - renewal channels were never dropped here, so the returning-customer line plotted
#     about 88 percent against a true 49 percent, since a renewal is always a returning
#     customer and always a subscription
#   - the seeding channel was dropped from the ledger on 2026-09-23 but not from here,
#     leaving the headline and order-tag lines about two points under their own
#     reference lines
# The window figures always came from facts_v15.json, which is why the summary numbers
# looked right while the line drawn through them did not. The assertion at the bottom
# now ties the series back to the ledger so this cannot happen silently again.
_DROP = {"Skio Subscriptions (YC S20)", "Heart & Soil Subscriptions", "The Lobby"}
A = [r for r in A if r["Sales channel"] not in _DROP]
B = [r for r in B if r["Sales channel"] not in _DROP]
C = [r for r in C if r["Sales channel"] not in _DROP]

DAYS = sorted(set(r["Day"] for r in A))
TT = "AfterShip for TikTok"
cust = lambda r: r["New or returning customer"].strip()
issub = lambda r: r["Subscription or one-time"].strip() == "subscription"
R = F["range"]
inpromo = lambda d: R["promo_start"] <= d <= R["promo_end"]
PRE  = [d for d in DAYS if d < R["change_day"] and not inpromo(d)]
SALE = [d for d in DAYS if R["change_day"] <= d <= R["sale_end"]]
POST = [d for d in DAYS if d > R["sale_end"]]

def bag(rows, pred, field="Orders"):
    o = collections.defaultdict(float)
    for r in rows:
        if pred(r): o[r["Day"]] += num(r[field])
    return o
okc = lambda r: r["Sales channel"] != TT

SRC = {
 "headline": (bag(C, lambda r: cust(r)=="New" and okc(r) and issub(r)),
              bag(A, lambda r: cust(r)=="New" and okc(r)),
              "new-customer orders on every channel but TikTok"),
 "tag":      (bag(B, lambda r: cust(r)=="New" and okc(r)),
              bag(A, lambda r: cust(r)=="New" and okc(r)),
              "new-customer orders, counted from the subscription first-order tag"),
 "store":    (bag(C, lambda r: cust(r)=="New" and r["Sales channel"]=="Online Store" and issub(r)),
              bag(A, lambda r: cust(r)=="New" and r["Sales channel"]=="Online Store"),
              "new-customer orders placed on the online store"),
 "ret":      (bag(C, lambda r: cust(r)=="Returning" and okc(r) and issub(r)),
              bag(A, lambda r: cust(r)=="Returning" and okc(r)),
              "returning-customer orders, excluding TikTok"),
}

def monday(d):
    dt = datetime.date.fromisoformat(d)
    return (dt - datetime.timedelta(days=dt.weekday())).isoformat()
WK = sorted(set(monday(d) for d in DAYS))
WKD = {k: [d for d in DAYS if monday(d) == k] for k in WK}
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def lab(k):
    dt = datetime.date.fromisoformat(k)
    return MON[dt.month - 1] + " " + str(dt.day)
WEEKS = [dict(label=lab(k), n=len(WKD[k]), full=len(WKD[k]) == 7) for k in WK]

DEFS = {}
for key, (n, d, denlabel) in SRC.items():
    e = dict(name=F["takerate"][key]["label"], den=denlabel)
    e["rate"] = [round(100.0*n[x]/d[x], 3) if d[x] else None for x in DAYS]
    e["num"]  = [int(n[x]) for x in DAYS]
    e["dn"]   = [int(d[x]) for x in DAYS]
    e["wnum"] = [int(sum(n[x] for x in WKD[w])) for w in WK]
    e["wden"] = [int(sum(d[x] for x in WKD[w])) for w in WK]
    e["wrate"]= [round(100.0*a/b, 3) if b else None for a, b in zip(e["wnum"], e["wden"])]
    f = F["takerate"][key]
    e["win"] = {"before": dict(r=f["pre"]["r"], d=f["pre"]["d"]),
                "sale":   dict(r=f["sale"]["r"], d=f["sale"]["d"]),
                "after":  dict(r=f["post"]["r"], d=f["post"]["d"])}
    DEFS[key] = e

sess = {r["Day"]: float(r["Sessions"]) for r in E}
cvr  = {r["Day"]: float(r["Conversion rate"])*100 for r in E}
denN = SRC["headline"][1]; numN = SRC["headline"][0]
nsN  = bag(A, lambda r: cust(r)=="New" and okc(r), "Net sales")
W = lambda fn: [fn(WKD[w]) for w in WK]
take = W(lambda ds: round(100.0*sum(numN[d] for d in ds)/sum(denN[d] for d in ds), 3))
aov  = W(lambda ds: round(sum(nsN[d] for d in ds)/sum(denN[d] for d in ds), 2))
conv = W(lambda ds: round(sum(cvr[d] for d in ds)/len(ds), 3))
ses  = W(lambda ds: round(sum(sess[d] for d in ds)/len(ds)))
subd = W(lambda ds: round(sum(numN[d] for d in ds)/len(ds), 1))
PREW = [i for i, k in enumerate(WK) if all(d < R["change_day"] for d in WKD[k])]
base = lambda v: round(sum(v[i] for i in PREW)/float(len(PREW)), 4)
SERIES = [
 dict(lab="Take rate",        sub="new customers",        col="var(--core-black)", unit="%", v=take, base=base(take), on=True,  w=3.0),
 dict(lab="New subscriptions",sub="started per day",      col="var(--deep)",       unit="n", v=subd, base=base(subd), on=True,  w=2.2),
 dict(lab="Order value",      sub="new-customer AOV",     col="var(--orange)",     unit="$", v=aov,  base=base(aov),  on=True,  w=2.2),
 dict(lab="Conversion",       sub="store-wide",           col="var(--s-green)",    unit="%", v=conv, base=base(conv), on=False, w=2.0),
 dict(lab="Sessions",         sub="store-wide, per day",  col="var(--s-sess)",     unit="n", v=ses,  base=base(ses),  on=False, w=2.0),
]

P = dict(defs=DEFS, days=DAYS, weeks=WEEKS,
         launch_day=DAYS.index(R["change_day"]), sale_end=DAYS.index(R["sale_end"]),
         ld=DAYS.index(R["labor_day"]),
         launch_week=WK.index(monday(R["change_day"])), sale_week=WK.index(monday(R["sale_end"])),
         tiers=dict(before=F["tiers"]["pre"], sale=F["tiers"]["sale"], after=F["tiers"]["post"]),
         tier_names=F["tiers"]["names"],
         bottles={("before_%s" % k.split("_")[1]) if k.startswith("pre") else ("after_%s" % k.split("_")[1]): v
                  for k, v in F["bottles"].items()},
         series=SERIES, grid=[w["label"] for w in WEEKS],
         prew=dict(start=lab(WK[PREW[0]]), end=lab(WK[PREW[-1]]), n=len(PREW)))
# The window figures are copied from the ledger and the daily series are computed here,
# so the only thing that proves the line matches the number printed on it is summing the
# series back up. Every measure, both windows, numerator and denominator.
_FAIL = []
for _k in sorted(DEFS):
    _d = DEFS[_k]
    for _lab, _days, _fk in (("before", PRE, "pre"), ("after", POST, "post")):
        _idx = [DAYS.index(_x) for _x in _days]
        _n = int(round(sum(_d["num"][i] for i in _idx)))
        _den = int(round(sum(_d["dn"][i] for i in _idx)))
        _f = F["takerate"][_k][_fk]
        if _n != _f["n"] or _den != _f["d"]:
            _FAIL.append("%s %s: series n=%d d=%d, ledger n=%d d=%d"
                         % (_k, _lab, _n, _den, _f["n"], _f["d"]))
assert not _FAIL, ("the plotted series do not sum to the ledger, so the charts would "
                   "disagree with the prose:\n  " + "\n  ".join(_FAIL))
print("series reconcile to facts_v15.json on every measure and both windows")

json.dump(P, io.open("payload_v15.json", "w", encoding="utf-8"), ensure_ascii=False)
print("payload_v15.json: %d days, %d weeks, defs %s" % (len(DAYS), len(WEEKS), sorted(DEFS)))
print("  launch_week=%d sale_week=%d  pre-launch weeks %d (%s to %s)"
      % (P["launch_week"], P["sale_week"], len(PREW), P["prew"]["start"], P["prew"]["end"]))
print("  bottles keys:", sorted(P["bottles"]))
for k in sorted(DEFS):
    w = DEFS[k]["win"]
    print("  %-9s before %6.2f%%  sale %6.2f%%  after %6.2f%%" % (k, w["before"]["r"], w["sale"]["r"], w["after"]["r"]))
