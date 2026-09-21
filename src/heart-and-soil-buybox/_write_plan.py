# -*- coding: utf-8 -*-
"""Write bq_plan.csv from the 2026-09-22 Skio pull (window 4 extended to Sep 20)."""
import csv, io, collections

ROWS = """1_pre,30,1,false,312,312,18617.4,72
1_pre,30,1,true,5742,5742,338877.5,1139
1_pre,30,2,false,92,184,10882.8,20
1_pre,30,2,true,1418,2836,167033.2,242
1_pre,30,3,false,41,123,6918.3,8
1_pre,30,3,true,553,1659,90241.4,110
1_pre,30,4plus,false,13,64,3453.3,4
1_pre,30,4plus,true,251,1322,72749.0,56
1_pre,60,1,false,162,162,10920.6,28
1_pre,60,1,true,1301,1301,81826.2,123
1_pre,60,2,false,57,114,6532.2,9
1_pre,60,2,true,523,1046,64602.9,49
1_pre,60,3,false,16,48,2517.3,2
1_pre,60,3,true,201,603,33401.7,12
1_pre,60,4plus,false,12,55,3101.4,1
1_pre,60,4plus,true,93,431,23202.9,12
1_pre,90,1,false,112,112,7051.8,20
1_pre,90,1,true,920,920,56276.5,126
1_pre,90,2,false,40,80,4705.2,5
1_pre,90,2,true,495,990,63733.5,63
1_pre,90,3,false,26,78,4205.7,5
1_pre,90,3,true,374,1122,62067.6,41
1_pre,90,4plus,false,12,73,3888.0,1
1_pre,90,4plus,true,181,985,55891.8,22
1_pre,180,1,true,2,2,261.0,0
2_augpromo,30,1,false,43,43,2394.0,10
2_augpromo,30,1,true,918,918,53659.8,238
2_augpromo,30,2,false,9,18,1038.6,4
2_augpromo,30,2,true,201,402,24496.2,48
2_augpromo,30,3,false,7,21,1278.0,5
2_augpromo,30,3,true,99,297,16187.0,29
2_augpromo,30,4plus,false,1,6,446.4,0
2_augpromo,30,4plus,true,57,285,15451.2,16
2_augpromo,60,1,false,22,22,1409.4,4
2_augpromo,60,1,true,190,190,11853.9,20
2_augpromo,60,2,false,7,14,864.9,1
2_augpromo,60,2,true,77,154,9323.1,3
2_augpromo,60,3,false,3,9,462.6,0
2_augpromo,60,3,true,39,117,6504.3,3
2_augpromo,60,4plus,false,1,5,238.5,0
2_augpromo,60,4plus,true,26,129,7469.3,1
2_augpromo,90,1,false,15,15,858.6,1
2_augpromo,90,1,true,139,139,8803.1,19
2_augpromo,90,2,false,10,20,1229.4,3
2_augpromo,90,2,true,86,172,10437.3,18
2_augpromo,90,3,false,7,21,1168.2,1
2_augpromo,90,3,true,84,252,13970.7,13
2_augpromo,90,4plus,false,3,15,851.4,1
2_augpromo,90,4plus,true,42,239,13859.1,7
2_augpromo,120,1,true,1,1,107.1,0
2_augpromo,180,4plus,true,1,5,324.9,0
3_sale,30,1,false,88,88,5222.7,14
3_sale,30,1,true,635,635,37890.1,46
3_sale,30,2,false,22,44,2597.4,5
3_sale,30,2,true,208,416,23832.0,13
3_sale,30,3,false,11,33,1849.5,0
3_sale,30,3,true,60,180,9827.1,2
3_sale,30,4plus,false,7,31,1695.6,3
3_sale,30,4plus,true,27,127,7231.5,4
3_sale,60,1,false,55,55,4252.5,7
3_sale,60,1,true,97,97,8445.8,10
3_sale,60,2,false,37,74,4092.6,6
3_sale,60,2,true,205,410,24650.1,18
3_sale,60,3,false,2,6,376.2,0
3_sale,60,3,true,6,18,1114.2,0
3_sale,60,4plus,false,11,52,2928.6,0
3_sale,60,4plus,true,26,119,6402.6,4
3_sale,90,1,false,7,7,421.2,5
3_sale,90,1,true,25,25,1597.5,6
3_sale,90,2,false,1,2,138.6,0
3_sale,90,2,true,19,38,2388.6,3
3_sale,90,3,false,98,294,15770.7,15
3_sale,90,3,true,540,1620,91213.2,55
3_sale,90,4plus,false,43,334,18062.1,11
3_sale,90,4plus,true,168,1248,68619.0,25
3_sale,120,1,true,2,2,214.2,0
3_sale,120,2,false,3,6,329.4,0
3_sale,120,2,true,4,8,856.8,0
3_sale,180,1,true,2,2,214.2,0
3_sale,180,3,false,20,60,4781.7,4
3_sale,180,3,true,36,108,8513.1,8
3_sale,180,4plus,false,1,6,642.6,0
3_sale,180,4plus,true,1,6,172.8,0
4_after,30,1,false,146,146,8496.0,10
4_after,30,1,true,1215,1215,72254.5,49
4_after,30,2,false,39,78,4203.9,5
4_after,30,2,true,321,642,37103.6,10
4_after,30,3,false,11,33,1663.2,0
4_after,30,3,true,89,267,14265.0,1
4_after,30,4plus,false,9,41,2331.0,0
4_after,30,4plus,true,25,120,6816.6,1
4_after,60,1,false,70,70,6174.0,1
4_after,60,1,true,148,148,12212.1,9
4_after,60,2,false,77,154,8829.0,2
4_after,60,2,true,300,600,36837.0,13
4_after,60,3,true,6,18,882.0,0
4_after,60,4plus,false,10,54,3241.8,2
4_after,60,4plus,true,44,207,11658.6,7
4_after,90,1,false,5,5,295.2,2
4_after,90,1,true,25,25,1427.4,3
4_after,90,2,false,7,14,811.8,1
4_after,90,2,true,11,22,1342.8,1
4_after,90,3,false,87,261,14885.1,13
4_after,90,3,true,732,2196,125590.5,45
4_after,90,4plus,false,48,365,20061.9,7
4_after,90,4plus,true,170,1200,66416.4,10
4_after,120,1,false,3,3,243.0,0
4_after,120,1,true,1,1,107.1,0
4_after,120,2,false,8,16,1177.2,0
4_after,120,2,true,16,32,2017.8,1
4_after,180,1,false,1,1,107.1,0
4_after,180,1,true,2,2,135.9,0
4_after,180,3,false,19,57,3285.9,1
4_after,180,3,true,39,117,8302.5,6
4_after,180,4plus,false,3,17,959.4,1
4_after,180,4plus,true,2,15,432.0,0"""

HEAD = ["win", "cadence", "units_b", "first", "subs", "units", "list_value", "cancelled"]
rows = [l.split(",") for l in ROWS.strip().split("\n")]
assert all(len(r) == 8 for r in rows), "ragged row"

old = list(csv.DictReader(io.open("bq_plan.csv", encoding="utf-8")))
with io.open("bq_plan.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    w.writerows(rows)
print("wrote bq_plan.csv: %d rows (was %d)" % (len(rows), len(old)))

new = list(csv.DictReader(io.open("bq_plan.csv", encoding="utf-8")))
def tot(rs):
    d = collections.Counter()
    for r in rs:
        d[r["win"]] += int(r["subs"])
    return d
o, n = tot(old), tot(new)
print()
print("%-12s %8s %8s %8s" % ("window", "old", "new", "delta"))
for k in sorted(set(o) | set(n)):
    print("%-12s %8d %8d %+8d%s" % (k, o[k], n[k], n[k] - o[k],
          "   <- extended to Sep 20" if k == "4_after" else ""))
