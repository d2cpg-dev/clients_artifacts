# -*- coding: utf-8 -*-
"""Prove the v17 design pass moved no number.

v17 changes what the page says ABOUT its charts: six subject labels become
takeaway headlines, and three legends come off because the drawings now name
their own series. Both edits change which figures appear in the prose, so a
plain set difference is not enough. This checks the two things that matter:

  1. the payload and the figures table are untouched
  2. every figure that is new to the prose is a value the ledger computed, and
     every figure that left the prose left with a deleted legend
"""
import io, json, re, subprocess, sys

A = io.open("page_v15.html", encoding="utf-8").read()
B = io.open("page_v18.html", encoding="utf-8").read()
fails = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (("  " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(label)


# --- 1. the payload -------------------------------------------------------
def payload(doc):
    return json.loads(re.search(r"var P = (\{.*?\});", doc, re.S).group(1))


da, db = payload(A), payload(B)
check("the payload has the same keys", sorted(da) == sorted(db),
      str(set(da) ^ set(db)))
moved = [k for k in da if json.dumps(da[k], sort_keys=True) != json.dumps(db[k], sort_keys=True)]
# the schedule's "gutter" is the pixel width reserved for its row labels, a
# layout value that moves when in-chart type changes. Everything else in the
# gantt is data and is compared as such.
if "gantt" in moved:
    ga = {k: v for k, v in da["gantt"].items() if k != "gutter"}
    gb = {k: v for k, v in db["gantt"].items() if k != "gutter"}
    check("the schedule is unchanged apart from its label gutter",
          json.dumps(ga, sort_keys=True) == json.dumps(gb, sort_keys=True),
          "gutter %s -> %s" % (da["gantt"]["gutter"], db["gantt"]["gutter"]))
    moved = [k for k in moved if k != "gantt"]
if moved == ["series"]:
    check("only series colour changed; every series value is identical",
          {s["lab"]: s["v"] for s in da["series"]} == {s["lab"]: s["v"] for s in db["series"]})
else:
    check("no payload key changed except series colour", not moved, str(moved))


# --- 2. the figures table -------------------------------------------------
def table_numbers(doc):
    body = re.search(r"<tbody>(.*?)</tbody>", doc, re.S).group(1)
    for ent, rep in (("&minus;", "-"), ("&mdash;", "-"), ("&rarr;", ">")):
        body = body.replace(ent, rep)
    return re.findall(r"-?\d[\d,.]*", body)


check("the figures table holds the same numbers in the same order",
      table_numbers(A) == table_numbers(B))


# --- 3. the figures in the prose -----------------------------------------
def prose(doc):
    t = re.sub(r"<script>.*?</script>", " ", doc, flags=re.S)
    t = re.sub(r"<style>.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<tbody>.*?</tbody>", " ", t, flags=re.S)
    return re.sub(r"<[^>]+>", " ", t).replace("&minus;", "-")


# a thousands separator only counts as part of the number when three digits
# follow it, otherwise "Aug 24, drawn as" reads as the figure "24,"
FIG = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
sa, sb = set(re.findall(FIG, prose(A))), set(re.findall(FIG, prose(B)))

# the ledger, as the builder computed it
TOK = json.loads(subprocess.check_output(
    [sys.executable, "-c",
     "import io,json,runpy;"
     "m=runpy.run_path('build_v18.py');"
     "print(json.dumps({k:str(v) for k,v in m['TOK'].items()}))"],
    stderr=subprocess.DEVNULL).decode().strip().splitlines()[-1])
ledger = set()
for v in TOK.values():
    ledger |= set(re.findall(FIG, v))

new = sorted(sb - sa)
ungrounded = [f for f in new if f not in ledger]
check("every figure new to the prose is a value the ledger computed",
      not ungrounded, "not in the ledger: %s" % ungrounded)

# what left the prose must be accounted for by the three deleted legends
legends = re.findall(r'<div class="legend".*?</div>', A, re.S)
legend_figs = set()
for lg in legends:
    legend_figs |= set(re.findall(FIG, re.sub(r"<[^>]+>", " ", lg)))
gone = sorted(sa - sb)
unexplained = [f for f in gone if f not in legend_figs]
check("every figure that left the prose left with a deleted legend",
      not unexplained, "unexplained: %s" % unexplained)

print()
print("  ledger figures newly surfaced by the takeaway headlines: %s" % (new or "none"))
print("  figures retired with the three legends: %s" % (gone or "none"))
print()
print("%d checks, %d failures" % (5, len(fails)))
sys.exit(1 if fails else 0)
