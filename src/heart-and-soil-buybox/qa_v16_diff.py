# -*- coding: utf-8 -*-
"""QA item 10 and its neighbours: prove the design pass moved no number.

Compares page_v16.html against page_v15.html on the two things that carry data,
the payload object and the figures table, and on the set of numbers in the prose.
"""
import io, re, sys

A = io.open("page_v15.html", encoding="utf-8").read()
B = io.open("page_v16.html", encoding="utf-8").read()
fails = []


def check(label, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label + (("  " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(label)


# --- 1. the payload -------------------------------------------------------
def payload(doc):
    m = re.search(r"var P = (\{.*?\});", doc, re.S)
    return m.group(1) if m else None


pa, pb = payload(A), payload(B)
check("the payload object is present in both", bool(pa) and bool(pb))
if pa and pb:
    import json
    da, db = json.loads(pa), json.loads(pb)
    # v16 adds three keys that describe drawing order, not measurement
    added = sorted(set(db) - set(da))
    check("v16 adds only ordering keys, no data keys",
          added == ["c3mark", "c3rows", "tier_order"], str(added))
    shared = [k for k in da if k in db]
    moved = []
    for k in shared:
        x, y = json.dumps(da[k], sort_keys=True), json.dumps(db[k], sort_keys=True)
        if x != y:
            moved.append(k)
    # the gantt gained a boolean saying which row is the gate; strip it and compare
    if "gantt" in moved:
        ga = json.dumps(da["gantt"], sort_keys=True)
        gb = json.loads(json.dumps(db["gantt"]))
        for r in gb["rows"]:
            r.pop("anchor", None)
        check("the schedule is unchanged apart from the anchor flag",
              ga == json.dumps(gb, sort_keys=True))
        moved = [k for k in moved if k != "gantt"]
    # series carries colour, which the design pass is allowed to change
    if moved == ["series"]:
        sa = {s["lab"]: s["v"] for s in da["series"]}
        sb = {s["lab"]: s["v"] for s in db["series"]}
        check("only series colour changed; every series value is identical", sa == sb)
    else:
        check("no payload key changed except series colour", not moved, str(moved))


# --- 2. the figures table -------------------------------------------------
def table_numbers(doc):
    m = re.search(r"<tbody>(.*?)</tbody>", doc, re.S)
    body = m.group(1)
    body = body.replace("&minus;", "-").replace("&mdash;", "-").replace("&rarr;", ">")
    return re.findall(r"-?\d[\d,.]*", body)


ta, tb = table_numbers(A), table_numbers(B)
check("the figures table holds the same numbers in the same order", ta == tb,
      "%d vs %d values" % (len(ta), len(tb)))

# --- 3. the sign glyph actually changed ----------------------------------
tbody_b = re.search(r"<tbody>(.*?)</tbody>", B, re.S).group(1)
tbody_a = re.search(r"<tbody>(.*?)</tbody>", A, re.S).group(1)
check("negative deltas in the table now use the true minus",
      "&minus;" in tbody_b and re.search(r"<td class=\"dn\">-", tbody_a)
      and not re.search(r"<td class=\"dn\">-", tbody_b))


# --- 4. the numbers in the prose -----------------------------------------
def prose_numbers(doc):
    txt = re.sub(r"<script>.*?</script>", " ", doc, flags=re.S)
    txt = re.sub(r"<style>.*?</style>", " ", txt, flags=re.S)
    txt = re.sub(r"<tbody>.*?</tbody>", " ", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = txt.replace("&minus;", "-")
    return sorted(re.findall(r"\d[\d,.]*", txt))


pna, pnb = prose_numbers(A), prose_numbers(B)
only_a = sorted(set(pna) - set(pnb))
only_b = sorted(set(pnb) - set(pna))
# v16's strip gained the two order-value dollar figures and chart 2's subtitle
# gained the "everything else" shares; nothing left the page as a different value
check("no figure in the prose changed value", not only_a,
      "gone from v16: %s" % only_a)
print("      figures the reorder newly surfaces: %s" % (only_b or "none"))

print()
print("%d checks, %d failures" % (4 + (1 if pa and pb else 0), len(fails)))
sys.exit(1 if fails else 0)
