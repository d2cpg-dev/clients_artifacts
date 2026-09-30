# Skio analysis catalog

A framework for reverse-engineering Skio subscription analyses onto one shared base, so reports
from different stores, analysts and tools can be compared and fed into one combined product.

Every number in a report is recorded with its original label and value, then linked to a
canonical metric with a fixed definition. Methods, chart forms and report anatomy get the same
treatment. The build validates every cross-reference and produces a single bundle plus CSV
exports and a documentation page.

## What is committed here, and what is not

This repository is public. Only the framework, template and tools live here. The populated
report catalogs hold client figures and are kept outside the repository. Do not add them.

| path | role |
|---|---|
| `framework/taxonomy.json` | 12 domains with subdomains, grains, report archetypes, insight types, QA severities and types |
| `framework/metric_registry.json` | canonical metrics: definition, formula, unit, grain, polarity, Skio export fields, labels seen |
| `framework/dimension_registry.json` | slicing dimensions and their Skio fields |
| `framework/concept_registry.json` | methods, definition choices, bias controls and caveats |
| `framework/chart_patterns.json` | chart forms and report-anatomy elements |
| `registry/skio_field_map.csv` | every field the Skio analytics UI exports, from `elt-pipeline/.skio-ui-maps` |
| `registry/build_field_map.py` | regenerates the field map (enum samples are left out, they hold product names) |
| `templates/report_catalog.template.json` | blank catalog for one report |
| `templates/playbook_catalog.template.json` | blank catalog for one skill or playbook, with a self-evaluation block scored on the rubric in `taxonomy.json` |
| `tools/build.py` | validates catalogs and writes `bundle.json`, `csv/*.csv` and the HTML page |
| `tools/catalog_template.html` | the documentation page; the build injects the bundle |

## Adding a report

1. Copy the template to the private catalog folder as the next free id.
2. Record every number as a metric reading pointing at a canonical metric. Add a canonical
   metric, dimension, concept or chart pattern to `framework/` when nothing fits.
3. Copy chart data arrays and tables from the page source.
4. Recompute headline figures from the report's own inputs and log every mismatch as a QA flag.
5. Record store links, definition differences and shared themes in the folder's `crosscheck.json`.
6. Build:

```
python tools/build.py --catalog <private catalog dir> --out <out dir> --html
```

The build refuses to write when an id, dimension, concept or pattern is unknown, when evidence
points at a missing id, or when a chart series length does not match its labels.
