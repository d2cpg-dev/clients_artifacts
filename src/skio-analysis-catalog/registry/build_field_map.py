#!/usr/bin/env python3
"""Regenerate registry/skio_field_map.csv from the Skio UI maps in the elt-pipeline repo.

Enum samples are left out on purpose: some hold client product names.
The field map is the *raw* Skio-native vocabulary: one row per (section, view, field) as the
Skio analytics UI exports it. It is the ground truth every catalogued metric is matched against.
The curated registry (metric_registry.csv) sits above it and groups these fields into canonical
metrics with stable IDs.

Usage:
    python registry/build_field_map.py [path/to/elt-pipeline/.skio-ui-maps/skio]
"""
import csv, glob, json, os, sys

DEFAULT_MAPS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                            "elt-pipeline", ".skio-ui-maps", "skio")
root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MAPS)
out = os.path.join(os.path.dirname(__file__), "skio_field_map.csv")

rows = []
for f in sorted(glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
    rel = os.path.relpath(f, root)
    section = os.path.dirname(rel).replace("analytics/", "").replace(os.sep, "/")
    view = os.path.basename(rel)[:-5]
    for c in json.load(open(f)):
        rows.append({
            "skio_field_key": f"{section}.{view}.{c['name']}",
            "section": section,
            "view": view,
            "field": c["name"],
            "type": c.get("type", ""),
            "description": (c.get("description") or "").strip(),
        })

with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f"wrote {len(rows)} fields from {root} -> {out}")
