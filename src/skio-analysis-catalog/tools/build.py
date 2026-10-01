#!/usr/bin/env python3
"""Validate report catalogs against the framework and build the comparison bundle.

Usage:
    python tools/build.py --catalog <dir with R*.json and crosscheck.json> --out <dir> [--html]

The catalog directory holds client data and is kept outside this repository.
Outputs:
    bundle.json            framework + reports + computed matrices, the single source for any front end
    csv/*.csv              flat exports: metric instances, charts, tables, methods, insights, recommendations, QA flags
    skio_analysis_catalog.html   the documentation page, when --html is given
"""
import argparse, csv, glob, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.join(HERE, "..", "framework")

def load(name): return json.load(open(os.path.join(FW, name)))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--catalog", required=True); ap.add_argument("--out", required=True); ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    tax, mreg, dreg, creg, pats = load("taxonomy.json"), load("metric_registry.json"), load("dimension_registry.json"), load("concept_registry.json"), load("chart_patterns.json")
    M = {m["id"]: m for m in mreg["metrics"]}; D = {d["id"]: d for d in dreg["dimensions"]}
    C = {c["id"]: c for c in creg["concepts"]}; P = {p["id"]: p for p in pats["chart_patterns"]}; U = {u["id"]: u for u in pats["ui_patterns"]}
    DOM = {d["id"] for d in tax["domains"]}; ARCH = {x["id"] for x in tax.get("report_archetypes", [])}
    reports = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(a.catalog, "R*.json")))]
    xpath = os.path.join(a.catalog, "crosscheck.json"); cross = json.load(open(xpath)) if os.path.exists(xpath) else {}
    errs = []
    all_ids = set()
    for r in reports:
        for k, key in [("metrics", "mid"), ("charts", "chart_id"), ("tables", "table_id"), ("insights", "id"), ("recommendations", "id"), ("qa_flags", "id")]:
            for o in r.get(k, []):
                if o[key] in all_ids: errs.append(f"duplicate id {o[key]}")
                all_ids.add(o[key])
    all_ids |= {f["id"] for f in cross.get("qa_flags", [])}
    ref_pat = re.compile(r"^(dim|viz|ui|mth)\.")
    for r in reports:
        rid = r["report_id"]
        if r.get("archetype") not in ARCH: errs.append(f"{rid}: unknown archetype {r.get('archetype')}")
        for m in r["metrics"]:
            if m["metric_id"] not in M: errs.append(f"{m['mid']}: unknown metric {m['metric_id']}")
            for dk in (m.get("slice") or {}):
                if dk not in D: errs.append(f"{m['mid']}: unknown dimension {dk}")
            if m.get("qa") and m["qa"] not in all_ids: errs.append(f"{m['mid']}: unknown qa {m['qa']}")
        for c in r["charts"]:
            if c["pattern"] not in P: errs.append(f"{c['chart_id']}: unknown pattern {c['pattern']}")
            for ds in c["data"]["datasets"]:
                if len(ds["values"]) != len(c["data"]["labels"]): errs.append(f"{c['chart_id']}: dataset '{ds['label']}' length mismatch")
        for t in r["tables"]:
            if t["pattern"] not in P: errs.append(f"{t['table_id']}: unknown pattern {t['pattern']}")
            for dk in t["dims"]:
                if dk not in D: errs.append(f"{t['table_id']}: unknown dimension {dk}")
            for mk in t["metrics"]:
                if mk not in M: errs.append(f"{t['table_id']}: unknown metric {mk}")
            for row in t["rows"]:
                if len(row) != len(t["columns"]): errs.append(f"{t['table_id']}: row width {len(row)} != {len(t['columns'])}")
        for x in r["methods"]:
            if x["concept_id"] not in C: errs.append(f"{rid}: unknown concept {x['concept_id']}")
        for s in r["structure"]:
            for u in s["ui"]:
                if u not in U: errs.append(f"{rid}: unknown ui {u}")
        for u in r["ui_patterns"]:
            if u not in U: errs.append(f"{rid}: unknown ui {u}")
        for i in r["insights"]:
            if i["domain"] not in DOM: errs.append(f"{i['id']}: unknown domain")
            if i["type"] not in tax["insight_types"]: errs.append(f"{i['id']}: unknown type")
            for e in i["evidence"]:
                if e not in all_ids: errs.append(f"{i['id']}: unknown evidence {e}")
        for x in r["recommendations"]:
            if x["domain"] not in DOM: errs.append(f"{x['id']}: unknown domain")
            if x["target_metric"] not in M: errs.append(f"{x['id']}: unknown target {x['target_metric']}")
        for f in r["qa_flags"]:
            if f["severity"] not in tax["qa_severity"]: errs.append(f"{f['id']}: bad severity")
            if f["type"] not in tax["qa_types"]: errs.append(f"{f['id']}: bad type")
            for e in f["evidence"]:
                if e not in all_ids: errs.append(f"{f['id']}: unknown evidence {e}")
    playbooks = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(a.catalog, "P*.json")))]
    RUB = {x["id"] for x in tax.get("playbook_rubric", [])}
    for pb in playbooks:
        pid = pb["playbook_id"]
        for m in pb["metrics_required"]:
            if m["metric_id"] not in M: errs.append(f"{pid}: unknown metric {m['metric_id']}")
        for dk in pb["dimensions"]:
            if dk not in D: errs.append(f"{pid}: unknown dimension {dk}")
        for c in pb["concepts"] + [c for ph in pb["phases"] for st in ph["steps"] for c in st["concepts"]]:
            if c not in C: errs.append(f"{pid}: unknown concept {c}")
        for u in pb["deliverable"]["ui_patterns"]:
            if u not in U: errs.append(f"{pid}: unknown ui {u}")
        for r in pb["self_eval"]["rubric"]:
            if r["id"] not in RUB: errs.append(f"{pid}: unknown rubric dimension {r['id']}")
        for f in pb["self_eval"]["findings"]:
            if f["severity"] not in tax["qa_severity"] or f["type"] not in tax["qa_types"]: errs.append(f"{f['id']}: bad severity or type")
    if errs:
        print("\n".join(errs)); sys.exit(f"{len(errs)} validation errors")

    rids = [r["report_id"] for r in reports]
    dom_of_metric = {k: v["domain"] for k, v in M.items()}
    # coverage matrices
    domain_cov = {d["id"]: {rid: 0 for rid in rids} for d in tax["domains"]}
    metric_cov = defaultdict(lambda: defaultdict(list))
    concept_cov = defaultdict(set); pattern_cov = defaultdict(lambda: defaultdict(int)); dim_cov = defaultdict(set); ui_cov = defaultdict(set)
    for r in reports:
        rid = r["report_id"]
        for m in r["metrics"]:
            domain_cov[dom_of_metric[m["metric_id"]]][rid] += 1
            metric_cov[m["metric_id"]][rid].append(m["mid"])
            for dk in (m.get("slice") or {}): dim_cov[dk].add(rid)
        for t in r["tables"]:
            for mk in t["metrics"]:
                metric_cov[mk][rid].append(t["table_id"]); domain_cov[dom_of_metric[mk]][rid] += 1
            for dk in t["dims"]: dim_cov[dk].add(rid)
        for c in r["charts"]:
            pattern_cov[c["pattern"]][rid] += 1
            for tok in re.findall(r"(?:[a-z]{3})\.[a-z_0-9]+", c["x"] + " " + c["y"] + " " + c.get("y2", "")):
                if tok in M: metric_cov[tok][rid].append(c["chart_id"]); domain_cov[dom_of_metric[tok]][rid] += 1
                if tok.startswith("dim") or ("dim." + tok.split(".", 1)[1]) in D: pass
            for tok in re.findall(r"dim\.[a-z_]+", c["x"] + " " + c["y"]): dim_cov[tok].add(rid)
        for t in r["tables"]: pattern_cov[t["pattern"]][rid] += 1
        for x in r["methods"]: concept_cov[x["concept_id"]].add(rid)
        for u in r["ui_patterns"]: ui_cov[u].add(rid)
    if "MTH" in domain_cov:
        for r in reports: domain_cov["MTH"][r["report_id"]] = len(r["methods"])
    for k in metric_cov:
        for rid in metric_cov[k]: metric_cov[k][rid] = sorted(set(metric_cov[k][rid]))
    # Skio native field coverage
    fmap_path = os.path.join(HERE, "..", "registry", "skio_field_map.csv")
    fields = list(csv.DictReader(open(fmap_path))) if os.path.exists(fmap_path) else []
    used_metrics = set(metric_cov)
    field_to_metrics = defaultdict(list)
    for mid, m in M.items():
        for f in m["skio"]:
            field_to_metrics[re.sub(r"\[.*\]$", "", f)].append(mid)
    native = []
    for f in fields:
        mids = field_to_metrics.get(f["skio_field_key"], [])
        native.append({"key": f["skio_field_key"], "section": f["section"], "view": f["view"], "field": f["field"], "type": f["type"], "metrics": mids,
                       "status": "used" if any(x in used_metrics for x in mids) else ("mapped" if mids else "unmapped")})
    view_cov = defaultdict(lambda: {"used": 0, "mapped": 0, "unmapped": 0})
    for n in native: view_cov[n["section"] + "." + n["view"]][n["status"]] += 1

    qa = [dict(f, report=r["report_id"]) for r in reports for f in r["qa_flags"]] + [dict(f, report="+".join(f["reports"])) for f in cross.get("qa_flags", [])]
    stats = {"reports": len(reports), "metric_instances": sum(len(r["metrics"]) for r in reports), "charts": sum(len(r["charts"]) for r in reports),
             "tables": sum(len(r["tables"]) for r in reports), "insights": sum(len(r["insights"]) for r in reports),
             "recommendations": sum(len(r["recommendations"]) for r in reports), "qa_flags": len(qa),
             "qa_high": sum(1 for f in qa if f["severity"] == "high"), "canonical_metrics": len(M), "canonical_used": len(used_metrics),
             "concepts": len(C), "concepts_used": len(concept_cov), "dimensions": len(D), "skio_fields": len(native),
             "skio_fields_used": sum(1 for n in native if n["status"] == "used")}
    for pb in playbooks:
        pb["report_coverage"] = {m["metric_id"]: sorted(metric_cov.get(m["metric_id"], {}).keys()) for m in pb["metrics_required"]}
        pb["concept_coverage"] = {c: sorted(concept_cov.get(c, set())) for c in pb["concepts"]}
    stats["playbooks"] = len(playbooks)
    bundle = {"playbooks": playbooks, "framework": {"taxonomy": tax, "metrics": mreg["metrics"], "dimensions": dreg["dimensions"], "concepts": creg["concepts"], "concept_kinds": creg["kinds"],
                            "chart_patterns": pats["chart_patterns"], "ui_patterns": pats["ui_patterns"]},
              "reports": reports, "cross": cross, "stats": stats,
              "matrices": {"domain": domain_cov, "metric": {k: dict(v) for k, v in metric_cov.items()}, "concept": {k: sorted(v) for k, v in concept_cov.items()},
                           "pattern": {k: dict(v) for k, v in pattern_cov.items()}, "dimension": {k: sorted(v) for k, v in dim_cov.items()}, "ui": {k: sorted(v) for k, v in ui_cov.items()}},
              "skio_native": {"fields": native, "views": view_cov}, "qa": qa}
    os.makedirs(os.path.join(a.out, "csv"), exist_ok=True)
    json.dump(bundle, open(os.path.join(a.out, "bundle.json"), "w"), separators=(",", ":"))
    def wcsv(name, rows, cols):
        with open(os.path.join(a.out, "csv", name), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(cols)
            for row in rows: w.writerow(row)
    wcsv("metric_instances.csv", [[r["report_id"], m["mid"], m["metric_id"], M[m["metric_id"]]["domain"], m["label"], m["value"], m["unit"], m["window"],
         json.dumps(m.get("slice", {}), ensure_ascii=False), json.dumps(m.get("compare", {}), ensure_ascii=False), m.get("derived", False), m.get("note", "")] for r in reports for m in r["metrics"]],
         ["report", "mid", "metric_id", "domain", "label", "value", "unit", "window", "slice", "compare", "derived", "note"])
    wcsv("charts.csv", [[r["report_id"], c["chart_id"], c["section"], c["title"], c["pattern"], c["library"], c["x"], c["y"], c.get("y2", ""), c["question"], json.dumps(c["data"], ensure_ascii=False), c.get("notes", "")] for r in reports for c in r["charts"]],
         ["report", "chart_id", "section", "title", "pattern", "library", "x", "y", "y2", "question", "data", "notes"])
    wcsv("tables.csv", [[r["report_id"], t["table_id"], t["title"], t["pattern"], "|".join(t["dims"]), "|".join(t["metrics"]), json.dumps(t["columns"], ensure_ascii=False), json.dumps(t["rows"], ensure_ascii=False)] for r in reports for t in r["tables"]],
         ["report", "table_id", "title", "pattern", "dims", "metrics", "columns", "rows"])
    wcsv("methods.csv", [[r["report_id"], x["concept_id"], C[x["concept_id"]]["kind"], x["how"]] for r in reports for x in r["methods"]], ["report", "concept_id", "kind", "how"])
    wcsv("insights.csv", [[r["report_id"], i["id"], i["type"], i["domain"], i["headline"], "|".join(i["evidence"])] for r in reports for i in r["insights"]], ["report", "id", "type", "domain", "headline", "evidence"])
    wcsv("recommendations.csv", [[r["report_id"], x["id"], x["domain"], x["target_metric"], x["action"]] for r in reports for x in r["recommendations"]], ["report", "id", "domain", "target_metric", "action"])
    wcsv("qa_flags.csv", [[f["report"], f["id"], f["severity"], f["type"], f["detail"]] for f in qa], ["report", "id", "severity", "type", "detail"])
    wcsv("metric_coverage.csv", [[k, M[k]["domain"], M[k]["name"]] + ["|".join(metric_cov.get(k, {}).get(rid, [])) for rid in rids] for k in M], ["metric_id", "domain", "name"] + rids)
    wcsv("skio_native_coverage.csv", [[n["key"], n["status"], "|".join(n["metrics"])] for n in native], ["skio_field_key", "status", "metrics"])
    if a.html:
        tpl = open(os.path.join(HERE, "catalog_template.html")).read()
        html = tpl.replace("/*__BUNDLE__*/null", json.dumps(bundle, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/"))
        open(os.path.join(a.out, "skio_analysis_catalog.html"), "w").write(html)
    print(json.dumps(stats, indent=1))

if __name__ == "__main__":
    main()
