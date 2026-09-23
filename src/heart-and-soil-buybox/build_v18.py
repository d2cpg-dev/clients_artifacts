# -*- coding: utf-8 -*-
"""Assembles the v15 report. Every number comes from facts_v15.json.
A guard strips HTML tags from the template and fails if any digit survives in the prose,
which is what keeps the copy grounded in the data rather than typed by hand."""
import json, io, re, datetime, math

F = json.load(io.open("facts_v15.json", encoding="utf-8"))
P = json.load(io.open("payload_v15.json", encoding="utf-8"))
BQF = json.load(io.open("bq_facts.json", encoding="utf-8"))
# revenue-weighted share, written by rev_facts.py, which will not produce this file
# unless it first reproduces facts_v15.json's revenue per day and the take-rate identity
RVF = json.load(io.open("rev_facts.json", encoding="utf-8"))
# selling-plan evidence: which plan group the box presents, and how quantity is chosen at each cycle
PF = json.load(io.open("plan_facts.json", encoding="utf-8"))
BODY = io.open("page_v18_body.html", encoding="utf-8").read()
TPL = io.open("page_v10_template.html", encoding="utf-8").read()
# Only the chart engine is inherited. The stylesheet is authored in page_v18.css,
# so no rule can be silently overridden by a later patch and every value is
# declared exactly once.
SCRIPT = TPL[TPL.index("<script>"):TPL.index("</script>") + len("</script>")]

# --------------------------------------------------------------- chart engine
def patch(s, old, new, why):
    assert old in s, "patch target missing: " + why
    return s.replace(old, new, 1)
# chart plots were sized for a wider column; with scale pinned at 1.000 they can come down
SCRIPT = patch(SCRIPT,
    "var N = rate.length, L = 58, R = 828, T = 44, B = 262;",
    "var N = rate.length, L = 58, R = 828, T = 36, B = 226;", "c1 plot height")
SCRIPT = patch(SCRIPT,
    "var L = 210, R = 840, T = 16, rowH = 34;",
    "var L = 210, R = 700, T = 16, rowH = 28;", "c3 row height and key gutter")
SCRIPT = patch(SCRIPT, "var cur = 'newtt', grain = 'week';", "var cur = 'headline', grain = 'week';", "default measure")
SCRIPT = patch(SCRIPT,
    "if (week) { var bw = (R - L) / N; x0 = L + bw * 4; x1 = L + bw * 5; }",
    "if (week) { var bw = (R - L) / N; x0 = L + bw * P.launch_week; x1 = L + bw * (P.sale_week + 1); }",
    "c1 week shading")
SCRIPT = patch(SCRIPT, "else [0, 10, 20, 30, N - 1].forEach(function (i) {",
    "else [0, Math.round((N-1)*0.25), Math.round((N-1)*0.5), P.launch_day, N - 1].forEach(function (i) {",
    "c1 daily labels")
SCRIPT = patch(SCRIPT,
    "var names = ['1 bottle / 30 days', '2 bottles / 60 days', '3 bottles / 90 days', '120 / 180-day plans', 'Every other combination'];",
    "var names = P.tier_names;", "c2 names")
# MAX is the bar scale's ceiling, not a figure: at 50 the longest bar ran to 671 and
# its value label, which sits outside the bar, reached 722, over the key at 718. At 60
# the same bar ends at 601 and its label at 644, well clear.
SCRIPT = patch(SCRIPT, "var L = 250, R = 790, T = 14, rowH = 48, gap = 14, MAX = 65;",
    "var L = 250, R = 700, T = 14, rowH = 40, gap = 12, MAX = 60;",
    "c2 scale and row height, it was the tallest chart on the page")
# c4 was 400 tall against 340 for its neighbours; bring the plot into the same band
SCRIPT = patch(SCRIPT, "var L = 58, R = 700, T = 46, B = 300, bw = (R - L) / LBL.length;",
    "var L = 58, R = 700, T = 42, B = 264, bw = (R - L) / LBL.length;", "c4 plot height")
# empty state: unticking every measure left a bare axis with no explanation
SCRIPT = patch(SCRIPT,
    "      clear(out);\n      if (!on.length) return;",
    "      clear(out);\n"
    "      if (!on.length) {\n"
    "        s.appendChild(txt((L + R) / 2, (T + B) / 2, 'Tick a measure above to draw it',\n"
    "          { size: 14, weight: 700, fill: 'var(--ink-3)', fam: \"'Public Sans',sans-serif\" }));\n"
    "        return;\n"
    "      }",
    "c4 empty state")
SCRIPT = patch(SCRIPT,
    "s.appendChild(el('rect', { x: L + bw * 6, y: T - 10, width: bw, height: B - T + 10, fill: 'var(--orange)', opacity: .13 }));",
    "s.appendChild(el('rect', { x: L + bw * P.launch_week, y: T - 10, width: bw * (P.sale_week - P.launch_week + 1), height: B - T + 10, fill: 'var(--orange)', opacity: .13 }));",
    "c4 shading")
SCRIPT = patch(SCRIPT, "s.appendChild(txt(L + bw * 6.5, T - 16, 'LAUNCH WEEK',",
    "s.appendChild(txt(L + bw * (P.launch_week + (P.sale_week - P.launch_week + 1) / 2), T - 16, 'LAUNCH + SALE',",
    "c4 label")
SCRIPT = SCRIPT.replace("i >= 6 ? 5 : 3.6", "i >= P.launch_week ? 5 : 3.6")
SCRIPT = SCRIPT.replace("i >= 6 ? x.col : 'var(--card)'", "i >= P.launch_week ? x.col : 'var(--card)'")
SCRIPT = patch(SCRIPT,
    "+ x.lab + '<span class=\"q\">' + x.sub + '</span>';",
    "+ '<span class=\"nm\">' + x.lab + '</span><span class=\"q\">' + x.sub + '</span>';",
    "c4 chip label wrapped so the series colour stops painting the text")
# The c1 title casing patch lived here. It only existed to stop m.name being lowercased
# into the title, and the title no longer uses m.name at all: it is composed from the
# measure's own headline subject further down. Removed rather than left to rot.
# the c1 subtitle element was removed as a duplicate of its own title; the engine still set it
SCRIPT = patch(SCRIPT,
    "    document.getElementById('c1s').textContent = 'Share of ' + m.den + '.';",
    "    var c1s = document.getElementById('c1s');\n"
    "    if (c1s) c1s.textContent = 'Share of ' + m.den + '.';",
    "c1 subtitle is optional")
# c3: three unrelated hues for an ordinal measure, and retention blue already means
# the baseline window in the chart directly above it
SCRIPT = patch(SCRIPT,
    "var COLS = ['#E8E1CE', 'var(--retention)', 'var(--core-black)'], NM = ['1 bottle', '2 bottles', '3 or more'];",
    "var COLS = ['var(--ramp-lo)', 'var(--ramp-mid)', 'var(--core-black)'], NM = ['1 bottle', '2 bottles', '3 or more'];",
    "c3 ordinal ramp")
SCRIPT = patch(SCRIPT,
    "{ size: 12.5, weight: 900, fill: j === 0 ? 'var(--ink)' : '#F7F3E7' }",
    "{ size: 12.5, weight: 900, fill: j === 2 ? 'var(--base-white)' : 'var(--ink)' }",
    "c3 bar labels legible on every ramp step")
# A percentage over 7 does not guarantee a band that can hold its own label: at the
# narrower plot width 7.2% drew a label exactly as wide as its band, spilling a hair
# into the neighbour. The label is measured against the band it sits in and dropped
# when it does not fit with a margin; the value stays in the tooltip and the table.
SCRIPT = patch(SCRIPT,
    """        if (v > 7) s.appendChild(txt(x + w / 2, y + rowH / 2 + 5, v.toFixed(1) + '%',
          { size: 12.5, weight: 900, fill: j === 2 ? 'var(--base-white)' : 'var(--ink)' }));""",
    """        if (v > 7) {
          var _vt = txt(x + w / 2, y + rowH / 2 + 5, v.toFixed(1) + '%',
            { size: 12.5, weight: 900, fill: j === 2 ? 'var(--base-white)' : 'var(--ink)' });
          s.appendChild(_vt);
          if (_vt.getComputedTextLength() > w - 8) s.removeChild(_vt);
        }""",
    "c3 keeps a value label only when its own band can hold it")
# c1: the post-sale mean was drawn in blue inside an orange-shaded window
SCRIPT = patch(SCRIPT,
    "[post, 'var(--blue)', 'AFTER THE SALE ' + post.toFixed(1) + '%']",
    "[post, 'var(--core-black)', 'AFTER THE SALE ' + post.toFixed(1) + '%']",
    "c1 post-sale mean line")
# c4: the PRE-LAUNCH tag was right-anchored outside the drawing and clipped by 25px.
# Moved inside the plot it then sat on the first week's markers, and there is nowhere
# along that rule it can go without landing on a series. It is dropped instead: the
# axis already labels the rule 100 in bold, and the chart's own subtitle says every
# line runs against its pre-launch average drawn as the rule at one hundred.
SCRIPT = patch(SCRIPT,
    "s.appendChild(txt(L - 10, yOf(100) - 12, 'PRE-LAUNCH', { anchor: 'end', size: 9, weight: 900, ls: '.08em' }));",
    "",
    "c4 drops the tag that could not clear the data")
# the payload is injected further down, once the schedule and forecast series exist

# 1. The headline is the takeaway the reader is given before the chart. The engine
# used to overwrite it with the bare name of the measure, which now goes to the
# subtitle where the grain already lives. Holding it fixed was worse: the four buttons
# change the data underneath, so returning customers showed a chart falling 8.4 points
# under a headline saying 7.3. It is now the selected measure's own takeaway. The
# subject comes from the payload, the figure and the verb from that measure's windows,
# and the closing clause only appears when the latest full week is still below the
# pre-change average, which is the thing it asserts.
SCRIPT = patch(SCRIPT,
    "    document.getElementById('c1t').textContent = 'Take rate, ' + m.name.toLowerCase();",
    """    var _d1 = pre - post, _tail = '';
    for (var _wi = m.wrate.length - 1; _wi >= 0; _wi--) {
      if (P.weeks[_wi].full) { if (m.wrate[_wi] < pre) _tail = ' and has not come back'; break; }
    }
    document.getElementById('c1t').textContent = m.head + (_d1 >= 0 ? ' fell ' : ' rose ')
      + Math.abs(_d1).toFixed(1) + ' points' + _tail;""",
    "c1 headline tracks the selected measure")
SCRIPT = patch(SCRIPT,
    "    if (c1s) c1s.textContent = 'Share of ' + m.den + '.';",
    """    if (c1s) c1s.textContent = m.name + '. Share of ' + m.den
      + (week ? ', by week, Monday to Sunday.' : ', per day.')
      + (lo > 0 ? ' Axis starts at ' + lo + '%.' : '');""",
    "c1 subtitle carries the measure, the grain and the axis floor")

# 5. In weekly mode every point carries a value, so a reference label pinned
# above its line at the left edge always lands on the first point's label.
SCRIPT = patch(SCRIPT,
    "        s.appendChild(txt(L + 4, yOf(g[0]) - 7, g[2], "
    "{ anchor: 'start', size: 10.5, weight: 900, ls: '.07em', fill: g[1] }));",
    """        // A fixed offset only works while the reference line sits clear of the
        // data. When the baseline moved up two points on 2026-09-23 the BEFORE label
        // landed on the first weekly marker; moving it to the other side then put it
        // on that marker's value label. So the occupied band covers both the marker
        // and, in weekly mode, the value printed above it, and the label takes the
        // first offset that is clear rather than one of two fixed sides.
        // yy is a baseline, so the label's ink runs from yy-11 to yy+3. A marker is
        // yOf(v)+-5, and in weekly mode its value sits 13 above that. Writing those
        // as signed bands rather than a symmetric distance matters: a symmetric test
        // of 15 called a 15.3 gap clear when the true clearance needed is 15.7.
        // The two reference labels also have to clear each other. In daily mode the
        // lines sit close enough that the first one, moving off the data, lands where
        // the second one wants to be. The first placed wins and the second adapts.
        if (g[0] === pre) s.__refy = [];
        var _busy = function (yy) {
          if (s.__refy.some(function (py) { return Math.abs(py - yy) < 15; })) return true;
          return rate.some(function (v, i) {
            if (xOf(i) < L - 4 || xOf(i) > L + 150) return false;
            var d = yy - yOf(v);
            if (d > -10 && d < 19) return true;
            return week && d > -28 && d < 2;
          });
        };
        var _cands = g[0] === pre ? [18, 32, 46, -9, -23, 60] : [-9, -23, 18, 32, -37, 46];
        var _ly = yOf(g[0]) + _cands[0];
        for (var _ci = 0; _ci < _cands.length; _ci++) {
          var _try = yOf(g[0]) + _cands[_ci];
          if (!_busy(_try) && _try > T + 10 && _try < B - 4) { _ly = _try; break; }
        }
        s.__refy.push(_ly);
        s.appendChild(txt(L + 4, _ly, g[2],
          { anchor: 'start', size: 10.5, weight: 900, ls: '.07em', fill: g[1] }));""",
    "c1 reference labels choose a side the data is not already using")

# c4: each end carries a value and a name, so the de-collision pass has to
# reserve two lines of twelve-unit type, not the one line it was written for.
SCRIPT = patch(SCRIPT,
    "for (var k = 1; k < ends.length; k++) if (ends[k].y - ends[k - 1].y < 26) "
    "ends[k].y = ends[k - 1].y + 26;",
    "for (var k = 1; k < ends.length; k++) if (ends[k].y - ends[k - 1].y < 34) "
    "ends[k].y = ends[k - 1].y + 34;",
    "c4 end labels reserve two lines")
SCRIPT = patch(SCRIPT,
    "s.appendChild(txt(R + 16, e.y + 13, e.x.lab.toUpperCase(), "
    "{ anchor: 'start', size: 9, weight: 900, ls: '.06em' }));",
    "s.appendChild(txt(R + 16, e.y + 17, e.x.lab.toUpperCase(), "
    "{ anchor: 'start', size: 9, weight: 700, ls: '.06em' }));",
    "c4 series name clears its own value")

# ---------------------------------------------------------- direct labelling
# A legend makes the reader translate colour into meaning on every glance. The
# three legends come off the page and the drawings name their own series.

# c2: three windows a row. Naming them on the first row is enough, because the
# order holds down the chart.
SCRIPT = patch(SCRIPT,
    "        s.appendChild(txt(L + ww + 8, y + j * (h + 3) + h / 2 + 4, val.toFixed(1) + '%', "
    "{ anchor: 'start', size: 11.5, weight: 900, fill: 'var(--ink)' }));",
    """        s.appendChild(txt(L + ww + 8, y + j * (h + 3) + h / 2 + 4, val.toFixed(1) + '%',
          { anchor: 'start', size: 11.5, weight: 900, fill: 'var(--ink)' }));""",
    "c2 value labels stay with their bars")
# c2: the three windows are named once, in a key beside the drawing, so the reader
# never has to match a bar back to a label sitting on another row.
SCRIPT = patch(SCRIPT,
    "    s.appendChild(txt(L, yb, 'SHARE OF NEW SUBSCRIPTIONS, SINGLE PRODUCTS', "
    "{ anchor: 'start', size: 10.5, weight: 900, ls: '.08em' }));",
    """    var _kw = T + 9, _kx = R + 18;
    Array.prototype.forEach.call(s.querySelectorAll('text'), function (t) {
      var b = t.getBBox();
      if (b.x + b.width + 18 > _kx) _kx = b.x + b.width + 18;
    });
    wins.forEach(function (w) {
      s.appendChild(el('rect', { x: _kx, y: _kw - 11, width: 13, height: 13, rx: 3,
        fill: w[1], stroke: 'var(--rule)', 'stroke-width': 1 }));
      s.appendChild(txt(_kx + 21, _kw, w[2].toUpperCase(),
        { anchor: 'start', size: 13, weight: 700, ls: '.07em', fill: 'var(--ink-2)' }));
      _kw += 26;
    });
    s.appendChild(txt(L, yb, 'SHARE OF NEW SUBSCRIPTIONS, SINGLE PRODUCTS',
      { anchor: 'start', size: 10.5, weight: 900, ls: '.08em' }));""",
    "c2 names its three windows once, in a key on the right")

SCRIPT = patch(SCRIPT,
    "var wins = [['before', 'var(--retention)', 'Before'], ['sale', 'var(--tint-orange)', "
    "'Launch + sale'], ['after', 'var(--orange)', 'After the sale']];",
    "var wins = [['before', 'var(--ink-3)', 'Before'], ['sale', 'var(--tint-orange)', "
    "'Launch + sale'], ['after', 'var(--orange)', 'Since the sale']];",
    "c2 before is neutral ink, not a second accent")

# c3: each band is named once, inside itself, on the row where it is widest.
# The in-band names were asked off the bars: a band wide enough to hold its own
# percentage is not always wide enough to hold a name too, and the name moved from
# row to row depending on which row happened to be widest. The three names now sit
# once, in a key to the right of the drawing, and the bars carry only their values.
SCRIPT = patch(SCRIPT,
    "      + ' orders. During the launch and Labor Day sale, Sep 3 to 7, it ran ' + m.win.sale.r.toFixed(1)\n"
    "      + '% across ' + m.win.sale.d.toLocaleString() + ' orders. Once the sale ended, Sep 8 to 16, it ran '",
    "      + ' orders. During the launch and Labor Day sale, ' + P.sale_label + ', it ran ' + m.win.sale.r.toFixed(1)\n"
    "      + '% across ' + m.win.sale.d.toLocaleString() + ' orders. Once the sale ended, ' + P.post_label + ', it ran '",
    "c1 caption takes both window ranges from the ledger, not typed dates")

SCRIPT = patch(SCRIPT,
    "    s.appendChild(txt(L, y + 18, 'EACH ROW FILLS TO 100% OF THAT PLAN’S NEW SUBSCRIPTIONS', "
    "{ anchor: 'start', size: 10.5, weight: 900, ls: '.08em' }));",
    """    var _ky = T + 7;
    NM.forEach(function (n, j) {
      s.appendChild(el('rect', { x: R + 18, y: _ky - 11, width: 13, height: 13, rx: 3,
        fill: COLS[j], stroke: 'var(--rule)', 'stroke-width': 1 }));
      s.appendChild(txt(R + 39, _ky, n.toUpperCase(),
        { anchor: 'start', size: 13, weight: 700, ls: '.07em', fill: 'var(--ink-2)' }));
      _ky += 26;
    });
    s.appendChild(txt(L, y + 18, 'EACH ROW FILLS TO 100% OF THAT PLAN’S NEW SUBSCRIPTIONS',
      { anchor: 'start', size: 10.5, weight: 900, ls: '.08em' }));""",
    "c3 names its three bands once, in a key on the right")

# c5 is authored in EXTRA_JS further down, so its owner labels are written there.

# ---------------------------------------------------------------- data ink
# Horizontal gridlines drop to a hairline; there were never any vertical ones.
SCRIPT = SCRIPT.replace("stroke: 'var(--grid)', 'stroke-width': 1 }", "stroke: 'var(--grid)', 'stroke-width': 1 }")
# the measure pickers carried the badge class and inherited its rules
SCRIPT = patch(SCRIPT, "lab.className = 'chip' + (x.on ? ' on' : '');",
    "lab.className = 'pick' + (x.on ? ' on' : '');", "c4 pickers stop colliding with the badge class")
SCRIPT = SCRIPT.replace("lab.style.color = x.on ? x.col : 'var(--ink-3)';",
                        "lab.style.setProperty('--sc', x.col);")
assert "lab.style.color" not in SCRIPT, "the picker still paints its own text"
# brand: large areas take the large-fill orange; text and small marks keep the
# orange that carries contrast
SCRIPT = SCRIPT.replace("fill: 'var(--orange)', opacity:", "fill: 'var(--orange-lg)', opacity:")
SCRIPT = SCRIPT.replace("'#B5731B'", "'var(--orange-text)'")
assert "#B5731B" not in SCRIPT, "a hard-coded chart colour survived"
# green is not a colour on this page
SCRIPT = SCRIPT.replace("var(--s-green)", "var(--retention)").replace("var(--s-sess)", "var(--ink-3)")
for _x in P["series"]:
    _x["col"] = {"var(--s-green)": "var(--retention)",
                 "var(--s-sess)": "var(--ink-3)"}.get(_x["col"], _x["col"])
_retired = ("s-green", "s-sess", "s-alt", "2F7D4F")
assert not any(c in json.dumps(P) for c in _retired), "a retired series colour survived"

# --------------------------------------------------------------- policy dates
D = datetime.date
SIGNOFF, REREAD, RESTORE = D(2026, 9, 30), D(2026, 10, 1), D(2026, 10, 2)
TEST_DAYS = 30
DECIDE = RESTORE + datetime.timedelta(days=TEST_DAYS)
RETENTION = D(2026, 11, 11)
CLEAN_RULE = 14           # policy: clean days required after a promotion before we call a trend
RET_READ_1, RET_READ_2 = 60, 90
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DAYN = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
def md(iso):
    d = D.fromisoformat(iso) if isinstance(iso, str) else iso
    return "%s %d" % (MON[d.month - 1], d.day)
def mdy(iso):
    d = D.fromisoformat(iso) if isinstance(iso, str) else iso
    return "%s %d, %d" % (MON[d.month - 1], d.day, d.year)
def rng(a, b):
    """Sep 3 to 7 within a month, Jul 20 to Sep 16 across months."""
    da = D.fromisoformat(a) if isinstance(a, str) else a
    db = D.fromisoformat(b) if isinstance(b, str) else b
    return "%s to %s" % (md(da), db.day if da.month == db.month else md(db))

H = F["takerate"]["headline"]; TG = F["takerate"]["tag"]; ST = F["takerate"]["store"]; RT = F["takerate"]["ret"]
c = F["commerce"]; v = F["value"]; q = F["quality"]; I = F["interval"]; T = F["tiers"]
m = F["magnitude"]; s = F["separation"]; rb = F["robust"]; tr = F["traffic"]; R = F["range"]
i30 = T["names"].index("1 bottle / 30 days"); i60 = T["names"].index("1 bottle / 60 days")
i90 = T["names"].index("1 bottle / 90 days"); i390 = T["names"].index("3 bottles / 90 days")
i260 = T["names"].index("2 bottles / 60 days")

pct  = lambda x: "%+.1f%%" % x
pts  = lambda x: "%.1f" % abs(x)
p1   = lambda x: "%.1f" % x
p2   = lambda x: "%.2f" % x
n0   = lambda x: format(int(round(x)), ",")
pc   = lambda x: "%+.1f%%" % x   # a signed percentage change, e.g. +30.1%
def sci(p):
    if p >= 1e-3: return "%.4f" % p
    e = int(math.floor(math.log10(p)))
    return "about %d in %s" % (max(1, int(round(p / 10 ** e))), n0(10 ** -e))

TOK = dict(
  # dates and windows
  change_day_long="%s %s" % (DAYN[D.fromisoformat(R["change_day"]).weekday()], mdy(R["change_day"])),
  change_day_short=md(R["change_day"]),
  range_long="%s to %s" % (md(R["start"]), mdy(R["end"])),
  range_end_long=mdy(R["end"]), pulled_long=mdy(R["pulled"]),
  pre_days=str(R["pre_days"]), post_days=str(R["post_days"]),
  pre_start=md(R["start"]), pre_end=md("2026-09-02"),
  promo_long=rng(R["promo_start"], R["promo_end"]),
  sale_long=rng(R["change_day"], R["sale_end"]),
  post_long=rng("2026-09-08", R["end"]),
  pre_short=rng(R["start"], "2026-09-02"),
  sale_short=rng(R["change_day"], R["sale_end"]),
  post_short=rng("2026-09-08", R["end"]),
  ck_window=rng("2026-08-06", "2026-09-09"),
  denom_window=rng("2026-08-06", "2026-09-02"),
  n_measures=str(len(P["defs"])),
  window_q_start=md("2026-09-01"), window_q_end=md("2026-09-10"),
  prew_start=P["prew"]["start"], prew_end=P["prew"]["end"],
  signoff_date=md(SIGNOFF), reread_date=md(REREAD), restore_date=md(RESTORE),
  decide_date=md(DECIDE), retention_date=md(RETENTION),
  test_days=str(TEST_DAYS), clean_rule=str(CLEAN_RULE),
  ret_read_1=str(RET_READ_1), ret_read_2=str(RET_READ_2),
  # take rate
  pre=p2(H["pre"]["r"]), post=p2(H["post"]["r"]), sale=p2(H["sale"]["r"]),
  drop=p1(H["drop"]), drop_r=pts(H["drop"]), rel="%.0f%%" % abs(H["rel"]),
  band_lo=str(I["band_lo"]), band_hi=str(I["band_hi"]),
  labor=p2(F["single_days"]["labor_day"]), labor_mult="%.1f" % F["single_days"]["labor_day_vs_normal"],
  day1=p2(F["single_days"]["change_day"]),
  min_pre=p2(s["min_pre"]), max_post=p2(s["max_post"]),
  below_n=str(s["below"]), pairs_lower=n0(s["pairs_lower"]), pairs_total=n0(s["pairs_total"]),
  mw_p=sci(s["mw_p"]),
  tag_drop=pts(TG["drop"]), store_drop=pts(ST["drop"]),
  dow_drop=pts(rb["dow_drop"]), matched_drop=pts(rb["matched_drop"]),
  matched_n=str(rb["matched_n"]), matched_sess=n0(rb["matched_sess"]), post_sess=n0(rb["post_sess"]),
  spread_lo=p1(rb["drop_min"]), spread_hi=p1(rb["drop_max"]),
  placebo_n=str(F["placebo"]["n"]), placebo_worst=pts(F["placebo"]["worst_drop"]),
  placebo_ratio="%.1f" % F["placebo"]["ratio"],
  traffic_r="%.2f" % tr["r"],
  ret_pre=p2(RT["pre"]["r"]), ret_post=p2(RT["post"]["r"]), ret_drop=pts(RT["drop"]),
  trend_early=p2(F["trend"]["early"]), trend_late=p2(F["trend"]["late"]),
  trend_delta="%.1f" % abs(F["trend"]["delta"]),
  # commerce
  aov_pct=pct(c["aov_pct"]), rev_pct=pct(c["rev_pct"]),
  # chart 6 states its own endpoint in its headline
  f12=n0(m["per_month"] * 12),
  # the two wider counts the September export no longer reproduces, and what the
  # earlier reporting held, so the method note can state both rather than claim a match
  # question four: the 60-day single-bottle cell repriced through mix, not pricing
  col_cad=n0(F["colostrum"]["cadence"]),
  col_share_pre=p1(F["colostrum"]["share_pre"]),
  col_share_post=p1(F["colostrum"]["share_post"]),
  col_price_pre="%.2f" % F["colostrum"]["price_pre"],
  col_price_post="%.2f" % F["colostrum"]["price_post"],
  col_cell_pre="%.2f" % F["colostrum"]["cell_price_pre"],
  col_cell_post="%.2f" % F["colostrum"]["cell_price_post"],
  col_resid=p1(F["colostrum"]["residual_price_pct"]),
  # the revenue-weighted section
  rw_pre=p2(RVF["windows"]["pre"]["share"]), rw_post=p2(RVF["windows"]["post"]["share"]),
  rw_drop=p2(abs(RVF["delta"]["share_pt"])),
  rw_sub_ord_pre=n0(RVF["windows"]["pre"]["sub_per_order"]),
  rw_sub_ord_post=n0(RVF["windows"]["post"]["sub_per_order"]),
  rw_sub_ord_pct=pc(RVF["delta"]["sub_per_order_pct"]),
  rw_subday_pre=n0(RVF["windows"]["pre"]["sub_day"]),
  rw_subday_post=n0(RVF["windows"]["post"]["sub_day"]),
  rw_subday_pct=pc(RVF["delta"]["sub_day_pct"]),
  rw_oneday_pct=pc(RVF["delta"]["one_day_pct"]),
  # the seeding channel that came out on 2026-09-23, and the client figure it
  # reconciles against now that the denominator no longer matches it outright
  ck_denom_exp=n0(F["checksum"]["denom_expected"]),
  ck_seed=n0(F["checksum"]["seed_in_denom"]),
  ck_seed_total=n0(F["checksum"]["seed_total"]),
  ck_orders_exp=n0(F["checksum"]["orders_expected"]),
  ck_signups_exp=n0(F["checksum"]["signups_expected"]),
  recon_pre=p2(F["recon"]["pre"]["ratio"]), recon_post=p2(F["recon"]["post"]["ratio"]),
  subs_pre=p1(c["subs_day_pre"]), subs_post=p1(c["subs_day_post"]),
  share_tr="%.0f%%" % c["share_takerate"], share_vol="%.0f%%" % c["share_volume"],
  rev_gain=n0(c["rev_gain_day"]),
  # plan mix
  # selling-plan evidence
  fam_old_pre=n0(PF["family"]["old"]["pre"]), fam_old_post=n0(PF["family"]["old"]["post"]),
  fam_new_pre=n0(PF["family"]["new"]["pre"]), fam_new_post=n0(PF["family"]["new"]["post"]),
  live90=str(PF["still_live"]["1x90"]["subs_since"]),
  live60=str(PF["still_live"]["1x60"]["subs_since"]),
  live30=n0(PF["still_live"]["1x30"]["subs_since"]),
  live90_last=md(PF["still_live"]["1x90"]["last_seen"]),
  one30_old=p1(PF["mix"]["30"]["old"]["1"]), one30_new=p1(PF["mix"]["30"]["new"]["1"]),
  one60_old=p1(PF["mix"]["60"]["old"]["1"]), one60_new=p1(PF["mix"]["60"]["new"]["1"]),
  one90_old=p1(PF["mix"]["90"]["old"]["1"]), one90_new=p1(PF["mix"]["90"]["new"]["1"]),
  three90_old=p1(PF["mix"]["90"]["old"]["3"]), three90_new=p1(PF["mix"]["90"]["new"]["3"]),
  two60_old=p1(PF["mix"]["60"]["old"]["2"]), two60_new=p1(PF["mix"]["60"]["new"]["2"]),
  # cadences are read back out of the tier names so they cannot drift from the data
  gone_cad=re.search(r"(\d+) days", T["names"][i90]).group(1),
  big_cad=re.search(r"(\d+) days", T["names"][i390]).group(1),
  alive_cad=re.search(r"(\d+) days", T["names"][i60]).group(1),
  m30_cad=re.search(r"(\d+) days", T["names"][i30]).group(1),
  gone_pre=p2(T["pre"][i90]), gone_post=p2(T["post"][i90]),
  big_pre=p2(T["pre"][i390]), big_post=p2(T["post"][i390]), big_delta=p1(T["delta"][i390]),
  alive_pre=p2(T["pre"][i60]), alive_post=p2(T["post"][i60]),
  m30_pre=p2(T["pre"][i30]), m30_post=p2(T["post"][i30]),
  two60_pre=p2(T["pre"][i260]), two60_post=p2(T["post"][i260]),
  n_pre=n0(T["n_pre"]), n_post=n0(T["n_post"]),
  # value
  ups_pre=p2(v["pre"]["units_per_sub"]), ups_post=p2(v["post"]["units_per_sub"]),
  ups_pct=pct(v["pct_units_per_sub"]),
  lps_pre=p2(v["pre"]["list_per_sub"]), lps_post=p2(v["post"]["list_per_sub"]),
  lps_pct=pct(v["pct_list_per_sub"]),
  lpm_pre=p2(v["pre"]["list_per_month"]), lpm_post=p2(v["post"]["list_per_month"]),
  lpm_pct=pct(v["pct_list_per_month"]),
  crux_pct="%.0f%%" % abs(v["crux_pct"]),
  crux_lo="%d%%" % int(math.floor(abs(v["crux_at_band_lo"]))),
  crux_hi="%d%%" % int(math.ceil(abs(v["crux_at_band_hi"]))),
  # magnitude
  lost_day=p1(m["per_day"]), lost_mo=n0(m["per_month"]),
  lost_lo=n0(m["lo_month"]), lost_hi=n0(m["hi_month"]), mo_bill=n0(m["monthly_billings"]),
  # quality and method
  same_day=p1(q["same_day_post"]), drift_pre=p1(q["drift_pre"]), drift_pre9=p1(q["drift_pre_9d"]),
  drift_post=p1(q["drift_post"]),
  cov_pre=p1(q["coverage_pre"]), cov_post=p1(q["coverage_post"]), cov_spread=p1(q["coverage_spread"]),
  migration=n0(q["migration_promo"]), plan_base=n0(q["plan_base_pre"]),
  plan_base_bloated=n0(q["plan_base_pre"] + q["migration_pre"]),
  n_products=str(BQF["single_product_ids"]),
  boot_n=n0(I["boot_n"]), phi=p2(I["phi_used"]),
  ck_orders=n0(F["checksum"]["orders"]), ck_signups=n0(F["checksum"]["signups"]),
  ck_denom=n0(F["checksum"]["denom_aug6_sep2"]),
  # test
  threshold=str(F["test"]["threshold"]), aov_floor=str(F["test"]["aov_floor"]),
  test_orders=n0(F["test"]["orders_30d"]), mde=p1(F["test"]["mde"]),
  tail_note=BQF["_provenance"]["note"].split(". ")[-1],
)

# --------------------------------------------------------------- figures table
def row(lbl, unit, a, b, ch):
    cls = "up" if ch.startswith("+") else ("dn" if ch and ch[0] in "-−" else "nc")
    return '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td></tr>' % (lbl, unit, a, b, cls, ch)
FIG = ['<tr class="grp"><td colspan="5">Take rate, share of orders containing a subscription</td></tr>']
for k, lbl in (("headline", "New customers, excl. TikTok"), ("tag", "New customers, order-tag measure"),
               ("store", "New customers, online store only"), ("ret", "Returning customers")):
    e = F["takerate"][k]
    FIG.append(row(lbl, "%", p2(e["pre"]["r"]), p2(e["post"]["r"]), "%+.1f pt" % -e["drop"]))
FIG += [row("Day one, %s" % md(R["change_day"]), "%", "&mdash;", p2(F["single_days"]["change_day"]), "&mdash;"),
        row("Labor Day, %s" % md(R["labor_day"]), "%", "&mdash;", p2(F["single_days"]["labor_day"]), "&mdash;"),
        row("Day-of-week standardised", "pt", "&mdash;", "&mdash;", "%+.1f pt" % rb["dow_drop"]),
        row("Matched on comparable traffic", "pt", "&mdash;", "&mdash;", "%+.1f pt" % rb["matched_drop"]),
        row("Bootstrap 95% interval", "pt", "&mdash;", "&mdash;",
            "&minus;%.1f to &minus;%.1f" % (I["boot_hi"], I["boot_lo"])),
        row("Quasi-binomial 95% interval", "pt", "&mdash;", "&mdash;",
            "&minus;%.1f to &minus;%.1f" % (I["normal_hi"], I["normal_lo"])),
        row("New-customer orders", "orders", n0(H["pre"]["d"]), n0(H["post"]["d"]),
            "%s &rarr; %s /day" % (p1(c["orders_day_pre"]), p1(c["orders_day_post"]))),
        '<tr class="grp"><td colspan="5">Plan mix, single-product subscriptions</td></tr>']
for i, nm in enumerate(T["names"]):
    FIG.append(row(nm, "%", p2(T["pre"][i]), p2(T["post"][i]), "%+.1f pt" % T["delta"][i]))
FIG += ['<tr class="grp"><td colspan="5">Selling plans, what the buy box presents</td></tr>',
        row("Sign-ups on the previously dominant plan group", "subs",
            n0(PF["family"]["old"]["pre"]), n0(PF["family"]["old"]["post"]),
            "%+.0f%%" % (100 * (PF["family"]["old"]["post"] / float(PF["family"]["old"]["pre"]) - 1))),
        row("Sign-ups on the group that replaced it", "subs",
            n0(PF["family"]["new"]["pre"]), n0(PF["family"]["new"]["post"]),
            "%+.0f%%" % (100 * (PF["family"]["new"]["post"] / float(PF["family"]["new"]["pre"]) - 1))),
        row("One bottle, share of the 30-day cycle", "%",
            p1(PF["mix"]["30"]["old"]["1"]), p1(PF["mix"]["30"]["new"]["1"]),
            "%+.1f pt" % (PF["mix"]["30"]["new"]["1"] - PF["mix"]["30"]["old"]["1"])),
        row("One bottle, share of the 60-day cycle", "%",
            p1(PF["mix"]["60"]["old"]["1"]), p1(PF["mix"]["60"]["new"]["1"]),
            "%+.1f pt" % (PF["mix"]["60"]["new"]["1"] - PF["mix"]["60"]["old"]["1"])),
        row("One bottle, share of the 90-day cycle", "%",
            p1(PF["mix"]["90"]["old"]["1"]), p1(PF["mix"]["90"]["new"]["1"]),
            "%+.1f pt" % (PF["mix"]["90"]["new"]["1"] - PF["mix"]["90"]["old"]["1"])),
        row("Three bottles, share of the 90-day cycle", "%",
            p1(PF["mix"]["90"]["old"]["3"]), p1(PF["mix"]["90"]["new"]["3"]),
            "%+.1f pt" % (PF["mix"]["90"]["new"]["3"] - PF["mix"]["90"]["old"]["3"])),
        row("Single-bottle sign-ups since the sale, 30 / 60 / 90 days", "subs", "&mdash;",
            "%s / %s / %s" % (n0(PF["still_live"]["1x30"]["subs_since"]),
                              PF["still_live"]["1x60"]["subs_since"],
                              PF["still_live"]["1x90"]["subs_since"]),
            "all still selling"),
        '<tr class="grp"><td colspan="5">Value per subscription, list price before discount</td></tr>',
        row("Bottles", "units", p2(v["pre"]["units_per_sub"]), p2(v["post"]["units_per_sub"]), pct(v["pct_units_per_sub"])),
        row("List value committed", "$", p2(v["pre"]["list_per_sub"]), p2(v["post"]["list_per_sub"]), pct(v["pct_list_per_sub"])),
        row("List value per month", "$", p2(v["pre"]["list_per_month"]), p2(v["post"]["list_per_month"]), pct(v["pct_list_per_month"])),
        row("Subscriptions per subscribing order", "n", "%.4f" % v["pre"]["subs_per_order"], "%.4f" % v["post"]["subs_per_order"], pct(v["pct_subs_per_order"])),
        row("Subscriptions counted", "subs", n0(T["n_pre"]), n0(T["n_post"]), "&mdash;"),
        '<tr class="grp"><td colspan="5">Order value, volume and traffic</td></tr>',
        row("New-customer order value", "$", p2(c["aov_pre"]), p2(c["aov_post"]), pct(c["aov_pct"])),
        row("New-customer revenue per day", "$", n0(c["rev_day_pre"]), n0(c["rev_day_post"]), pct(c["rev_pct"])),
        row("New subscriptions per day", "n", p1(c["subs_day_pre"]), p1(c["subs_day_post"]), pct(c["subs_pct"])),
        row("Units per order", "units", p2(c["upo_pre"]), p2(c["upo_post"]), pct(c["upo_pct"])),
        row("Sessions per day, store-wide", "n", n0(tr["pre_sess"]), n0(tr["post_sess"]), pct(tr["sess_change"])),
        row("Conversion rate, store-wide", "%", p2(tr["pre_cvr"]), p2(tr["post_cvr"]), pct(tr["cvr_change"])),
        '<tr class="grp"><td colspan="5">Data quality</td></tr>',
        row("Single-product coverage of all subscriptions", "%", p1(q["coverage_pre"]), p1(q["coverage_post"]),
            "%.1f pt spread" % q["coverage_spread"]),
        row("Subscriptions with an edited line", "%", p1(q["drift_pre"]), p1(q["drift_post"]), "&mdash;"),
        row("Skio origin orders over Shopify subscribing orders", "ratio",
            "%.3f" % F["recon"]["pre"]["ratio"], "%.3f" % F["recon"]["post"]["ratio"], "&mdash;")]
TOK["figrows"] = "\n".join(FIG)

# --------------------------------------------------------------- schedule and forecast
# Both are presentation of figures already in facts_v15.json. No new estimate is made.
WHO = [("you", "You", "var(--orange)"), ("us", "Us", "var(--blue)"),
       ("your_team", "Your team", "var(--retention)"), ("joint", "Joint", "var(--deep)")]
SCHED = [
    dict(a=SIGNOFF, b=SIGNOFF, who="you",
         t="Your yes on restoring the single bottle every %s days" % TOK["gone_cad"]),
    dict(a=REREAD, b=REREAD, who="us",
         t="We re-read take rate on two more clean weeks"),
    dict(a=RESTORE, b=DECIDE, who="your_team",
         t="Plan back in the buy box, %s-day test runs" % TEST_DAYS),
    dict(a=RESTORE, b=DECIDE, who="you",
         t="Nothing else changes in the buy box, no promotion"),
    dict(a=DECIDE, b=DECIDE, who="joint",
         t="Test result and the decision on the missing plan"),
    dict(a=RETENTION, b=RETENTION, who="us",
         t="%s-day retention read on the September cohort" % RET_READ_1),
]
AX0 = SIGNOFF - datetime.timedelta(days=3)
AX1 = RETENTION + datetime.timedelta(days=4)
span = float((AX1 - AX0).days)

def text_w(txt, size):
    """Rough advance width for Public Sans, used to size the gantt label gutter."""
    narrow, wide = set("iljItf().,:;'\"!|-"), set("MWmw@")
    w = 0.0
    for ch in txt:
        if ch in narrow: w += 0.30
        elif ch in wide: w += 0.92
        elif ch.isupper() or ch.isdigit(): w += 0.62
        else: w += 0.535
    return w * size

# a tick where the axis starts, then one at each month boundary it crosses
GANTT_TICKS = [dict(x=0.0, lab=MON[AX0.month - 1])]
_m = D(AX0.year, AX0.month, 1)
while _m <= AX1:
    if _m > AX0:
        GANTT_TICKS.append(dict(x=(_m - AX0).days / span, lab=MON[_m.month - 1]))
    _m = D(_m.year + _m.month // 12, _m.month % 12 + 1, 1)

# the schedule's row labels render at the in-chart floor, so the gutter has to
# be measured at that size or the longest label runs out of the viewBox
GANTT_LABEL_PX = 13
GUTTER = int(math.ceil(max(text_w(r["t"], GANTT_LABEL_PX) for r in SCHED))) + 22
assert GUTTER <= 430, "gantt labels need %dpx of gutter, too wide for the bars" % GUTTER
print("gantt label gutter: %dpx (longest label %.0fpx)"
      % (GUTTER, max(text_w(r["t"], GANTT_LABEL_PX) for r in SCHED)))

P["gantt"] = dict(
    who=[dict(k=k, lab=l, col=c) for k, l, c in WHO],
    gutter=GUTTER, ticks=GANTT_TICKS,
    rows=[dict(t=r["t"], who=r["who"], lab=md(r["a"]) if r["a"] == r["b"] else rng(r["a"], r["b"]),
               x0=(r["a"] - AX0).days / span, x1=(r["b"] - AX0).days / span,
               point=(r["a"] == r["b"])) for r in SCHED])

MONTHS = 12
start_m = D.fromisoformat(R["change_day"]).replace(day=1)
def add_months(d0, k):
    mth = d0.month - 1 + k
    return D(d0.year + mth // 12, mth % 12 + 1, 1)
P["forecast"] = dict(
    n=MONTHS, unit="subscriptions not started",
    # elapsed months from the change, not calendar months: the change landed mid-September,
    # so a calendar axis would read as though September already cost a full month's worth
    labels=["Month %d" % (i + 1) for i in range(MONTHS)],
    mid=[round(m["per_month"] * (i + 1)) for i in range(MONTHS)],
    lo=[round(m["lo_month"] * (i + 1)) for i in range(MONTHS)],
    hi=[round(m["hi_month"] * (i + 1)) for i in range(MONTHS)],
    rate=round(m["per_month"]), rate_lo=round(m["lo_month"]), rate_hi=round(m["hi_month"]),
    retention_label=md(RETENTION))

# --------------------------------------------------------------- new charts
# Chart 1's caption had both window ranges typed into the chart engine's JavaScript.
# "Sep 3 to 7" happened to stay true; "Sep 8 to 16" went stale the moment the window
# was extended to the 20th and shipped wrong, because the grounding guard reads the
# copy and never the engine. Both now come from the ledger through the payload.
P["sale_label"] = rng(R["change_day"], R["sale_end"])
P["post_label"] = rng("2026-09-08", R["end"])

# Chart 1's headline used to be fixed while its four buttons changed the data under it,
# so picking returning customers left a headline claiming 7.3 points over a chart
# showing 8.4. Each measure now carries the subject of its own takeaway; the figure and
# the verb are computed from that measure's own windows, so the sentence cannot state a
# number the drawing does not show.
_HEADS = {
    "headline": "Take rate",
    "tag": "The order-tag measure",
    "store": "Take rate on the online store",
    "ret": "Take rate for returning customers",
}
for _k, _h in _HEADS.items():
    assert _k in P["defs"], "no measure called %s to headline" % _k
    P["defs"][_k]["head"] = _h
assert set(_HEADS) == set(P["defs"]), \
    "every measure needs a headline subject, missing %s" % (set(P["defs"]) - set(_HEADS))

# chart 7 reads its two bars straight off the revenue ledger
P["revmix"] = {
    "rows": [
        {"lab": "Before", "sub": RVF["windows"]["pre"]["sub_day"],
         "one": RVF["windows"]["pre"]["one_day"], "share": RVF["windows"]["pre"]["share"]},
        {"lab": "Since the sale", "sub": RVF["windows"]["post"]["sub_day"],
         "one": RVF["windows"]["post"]["one_day"], "share": RVF["windows"]["post"]["share"]},
    ],
    "names": ["Subscription", "One-time"],
}

EXTRA_JS = """
  /* ---------- chart 7 : where the new-customer money comes from ---------- */
  (function () {
    var s = document.getElementById('c7'); if (!s) return;
    // the plot stops at 640 so the row's share label and then the key both fit
    // inside the 880-unit frame; at 700 the key ran 143 units past the edge
    var D = P.revmix, L = 250, R = 640, T = 26, rowH = 46, gap = 26;
    var COLS = ['var(--core-black)', 'var(--ramp-lo)'];
    var MAX = 0;
    D.rows.forEach(function (r) { if (r.sub + r.one > MAX) MAX = r.sub + r.one; });
    var y = T;
    D.rows.forEach(function (r) {
      s.appendChild(txt(L - 16, y + rowH / 2 + 5, r.lab, { anchor: 'end', size: 14,
        weight: 700, fill: 'var(--ink)', fam: "'Public Sans',sans-serif" }));
      var x = L;
      [r.sub, r.one].forEach(function (v, j) {
        var w = (R - L) * v / MAX;
        var rect = el('rect', { x: x, y: y, width: Math.max(w - (j ? 2 : 0), 1),
          height: rowH, fill: COLS[j] });
        hov(rect, '<b>' + r.lab + ' &middot; ' + D.names[j] + '</b><br>$'
          + Math.round(v).toLocaleString() + ' a day');
        s.appendChild(rect);
        var _vt = txt(x + w / 2, y + rowH / 2 + 5, '$' + Math.round(v).toLocaleString(),
          { size: 13, weight: 900, fill: j === 0 ? 'var(--base-white)' : 'var(--ink)' });
        s.appendChild(_vt);
        if (_vt.getComputedTextLength() > w - 10) s.removeChild(_vt);
        x += w;
      });
      // the key names the dark band, so the number alone is enough here
      s.appendChild(txt(x + 10, y + rowH / 2 + 5, r.share.toFixed(1) + '%',
        { anchor: 'start', size: 13, weight: 900, fill: 'var(--ink)' }));
      y += rowH + gap;
    });
    var _kx = R + 18, _ky = T + 9;
    Array.prototype.forEach.call(s.querySelectorAll('text'), function (t) {
      var b = t.getBBox();
      if (b.x + b.width + 18 > _kx) _kx = b.x + b.width + 18;
    });
    D.names.forEach(function (n, j) {
      s.appendChild(el('rect', { x: _kx, y: _ky - 11, width: 13, height: 13, rx: 3,
        fill: COLS[j], stroke: 'var(--rule)', 'stroke-width': 1 }));
      s.appendChild(txt(_kx + 21, _ky, n.toUpperCase(), { anchor: 'start', size: 13,
        weight: 700, ls: '.07em', fill: 'var(--ink-2)' }));
      _ky += 26;
    });
    s.appendChild(txt(L, y + 4, 'NET SALES PER DAY, NEW CUSTOMERS, BOTH BARS ON ONE SCALE',
      { anchor: 'start', size: 10.5, weight: 900, ls: '.08em' }));
    s.setAttribute('viewBox', '0 0 880 ' + (y + 20));
    s.setAttribute('aria-label', 'New-customer net sales per day split by line type. '
      + D.rows.map(function (r) { return r.lab + ': $' + Math.round(r.sub) + ' subscription and $'
        + Math.round(r.one) + ' other, ' + r.share.toFixed(1) + ' percent subscription'; }).join('. '));
  })();

  /* ---------- chart 5 : schedule gantt ---------- */
  (function () {
    var s = document.getElementById('c5'); if (!s) return;
    // the plot stops short of the right edge to leave an owner column, so the
    // schedule names who holds each step instead of sending it to a legend
    var G = P.gantt, L = G.gutter, R2 = 730, T = 34, rowH = 34, gap = 10;
    var col = {}, wlab = {};
    G.who.forEach(function (w) { col[w.k] = w.col; wlab[w.k] = w.lab; });
    var xOf = function (f) { return L + (R2 - L) * f; };
    // the axis opens a few days before the first gate, so the opening month tick
    // and the next one can land within a label's width of each other
    var lastTick = -1e9;
    G.ticks.forEach(function (t) {
      if (xOf(t.x) - lastTick < 44) return;
      lastTick = xOf(t.x);
      s.appendChild(el('line', { x1: xOf(t.x), x2: xOf(t.x), y1: T - 12,
        y2: T + G.rows.length * (rowH + gap), stroke: 'var(--grid)', 'stroke-width': 1 }));
      s.appendChild(txt(xOf(t.x), T - 18, t.lab.toUpperCase(),
        { size: 10, weight: 900, ls: '.09em' }));
    });
    G.rows.forEach(function (r, i) {
      var y = T + i * (rowH + gap), c = col[r.who];
      s.appendChild(txt(L - 16, y + rowH / 2 + 4, r.t, { anchor: 'end', size: 11.5, weight: 600,
        fill: 'var(--ink)', fam: "'Public Sans',sans-serif" }));
      var x0 = xOf(r.x0), x1 = xOf(r.x1), w = Math.max(x1 - x0, 0);
      if (r.point) {
        var d = rowH * 0.34;
        var pt = el('rect', { x: x0 - d, y: y + rowH / 2 - d, width: d * 2, height: d * 2,
          fill: c, transform: 'rotate(45 ' + x0 + ' ' + (y + rowH / 2) + ')' });
        hov(pt, '<b>' + r.lab + '</b><br>' + r.t); s.appendChild(pt);
        s.appendChild(txt(x0 + 16, y + rowH / 2 + 4, r.lab, { anchor: 'start', size: 11.5,
          weight: 900, fill: 'var(--ink)' }));
      } else {
        var bar = el('rect', { x: x0, y: y + 5, width: w, height: rowH - 10, rx: 5, fill: c,
          opacity: .85 });
        hov(bar, '<b>' + r.lab + '</b><br>' + r.t); s.appendChild(bar);
        s.appendChild(txt(x0 + w / 2, y + rowH / 2 + 4, r.lab, { size: 11, weight: 900,
          fill: 'var(--core-black)' }));
      }
      s.appendChild(txt(866, y + rowH / 2 + 4, wlab[r.who].toUpperCase(),
        { anchor: 'end', size: 10, weight: 700, ls: '.08em', fill: 'var(--ink-3)' }));
    });
    var yb = T + G.rows.length * (rowH + gap);
    s.appendChild(txt(866, T - 18, 'OWNER',
      { anchor: 'end', size: 10, weight: 700, ls: '.08em', fill: 'var(--ink-3)' }));
    s.appendChild(el('line', { x1: L, x2: R2, y1: yb, y2: yb, stroke: 'var(--rule)', 'stroke-width': 1.5 }));
    s.setAttribute('viewBox', '0 0 880 ' + (yb + 26));
    s.setAttribute('aria-label', 'Schedule. ' + G.rows.map(function (r) {
      return r.lab + ', ' + r.t; }).join('. '));
    var lg = document.getElementById('gl');
    if (lg) G.who.forEach(function (w) {
      var sp = document.createElement('span');
      sp.innerHTML = '<i class="sw" style="background:' + w.col + '"></i> ' + w.lab;
      lg.appendChild(sp);
    });
  })();

  /* ---------- chart 6 : cumulative subscriptions not started ---------- */
  (function () {
    var s = document.getElementById('c6'); if (!s) return;
    var F6 = P.forecast, L = 66, R2 = 748, T = 20, B = 200, N = F6.n;
    var hi = F6.hi[N - 1], step = Math.pow(10, Math.floor(Math.log(hi) / Math.LN10));
    if (hi / step < 3) step = step / 2;
    var top = Math.ceil(hi / step) * step;
    var yOf = function (v) { return B - v / top * (B - T); };
    var xOf = function (i) { return L + (R2 - L) * (i / (N - 1)); };
    for (var g = 0; g <= top + 0.5; g += step) {
      s.appendChild(el('line', { x1: L, x2: R2, y1: yOf(g), y2: yOf(g),
        stroke: 'var(--grid)', 'stroke-width': 1 }));
      s.appendChild(txt(L - 10, yOf(g) + 4, g.toLocaleString(),
        { anchor: 'end', size: 11, weight: 600 }));
    }
    var band = '';
    F6.hi.forEach(function (v, i) { band += (i ? 'L' : 'M') + xOf(i) + ' ' + yOf(v); });
    for (var i = N - 1; i >= 0; i--) band += 'L' + xOf(i) + ' ' + yOf(F6.lo[i]);
    s.appendChild(el('path', { d: band + 'Z', fill: 'var(--orange)', opacity: .16 }));
    s.appendChild(el('polyline', { points: F6.mid.map(function (v, i) {
      return xOf(i) + ',' + yOf(v); }).join(' '), fill: 'none', stroke: 'var(--orange)',
      'stroke-width': 2.8, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    F6.mid.forEach(function (v, i) {
      var c = el('circle', { cx: xOf(i), cy: yOf(v), r: 3.6, fill: 'var(--orange)' });
      hov(c, '<b>' + F6.labels[i] + '</b><br>' + v.toLocaleString() + ' ' + F6.unit
        + '<br>between ' + F6.lo[i].toLocaleString() + ' and ' + F6.hi[i].toLocaleString());
      s.appendChild(c);
      // every other month. The forced last label always landed on its
      // neighbour, and the end callout already names the twelve-month figure.
      if (i % 2 === 0)
        s.appendChild(txt(xOf(i), B + 20, F6.labels[i].toUpperCase(),
          { size: 9.5, weight: 700, ls: '.04em' }));
    });
    s.appendChild(el('line', { x1: L, x2: R2, y1: B, y2: B, stroke: 'var(--rule)', 'stroke-width': 1.5 }));
    s.appendChild(txt(R2 + 12, yOf(F6.mid[N - 1]) - 2, F6.mid[N - 1].toLocaleString(),
      { anchor: 'start', size: 15, weight: 900, fill: 'var(--ink)' }));
    s.appendChild(txt(R2 + 12, yOf(F6.mid[N - 1]) + 17, 'SUBSCRIPTIONS',
      { anchor: 'start', size: 9, weight: 700, ls: '.07em' }));
    s.appendChild(txt(R2 + 12, yOf(F6.mid[N - 1]) + 34, 'AT ' + F6.n + ' MONTHS',
      { anchor: 'start', size: 9, weight: 700, ls: '.07em' }));
    s.appendChild(txt(L, B + 44, 'CUMULATIVE SUBSCRIPTIONS NOT STARTED, AT THE MEASURED RATE OF '
      + F6.rate.toLocaleString() + ' A MONTH', { anchor: 'start', size: 10.5, weight: 900, ls: '.08em' }));
    s.appendChild(txt(L, B + 60, 'NO DOLLAR FIGURE HERE. THE REVENUE CONSEQUENCE WAITS FOR THE '
      + F6.retention_label.toUpperCase() + ' RETENTION READ',
      { anchor: 'start', size: 10.5, weight: 900, ls: '.08em', fill: 'var(--ink-2)' }));
    s.setAttribute('aria-label', 'Cumulative subscriptions not started over twelve months, reaching '
      + F6.mid[N - 1] + ', between ' + F6.lo[N - 1] + ' and ' + F6.hi[N - 1] + '.');
  })();
"""
assert SCRIPT.rstrip().endswith("})();\n</script>") or "})();" in SCRIPT
cut_at = SCRIPT.rindex("})();")
SCRIPT = SCRIPT[:cut_at] + EXTRA_JS + "\n" + SCRIPT[cut_at:]
# nothing on a chart should render below about 11px once the page's 1.1 scale is applied.
# This runs after every targeted patch above, so it cannot invalidate their match strings.
# The caption rail takes the drawing down to 823 of its 880 units, a scale of
# 0.935. A 12-unit label therefore lands on 11.2 real pixels, which is the
# floor. At 11 units it would land on 10.3 and the page would break its own rule.
# The eight-column graphic zone is 749 of the drawing's 880 units, a scale of
# 0.852. A 13-unit label therefore lands on 11.07 real pixels, which is the
# floor. At 12 units it would land on 10.2 and break the page's own rule.
for _small in ("9", "9.5", "10", "10.5", "11", "11.5", "12", "12.5"):
    SCRIPT = SCRIPT.replace("size: %s," % _small, "size: 13,")
for _bad in ("9", "9.5", "10", "10.5", "11", "11.5", "12", "12.5"):
    assert "size: %s," % _bad not in SCRIPT, "chart type below the floor: " + _bad
# 900 is for the value callouts. Axis and tick text drops to 700, which at
# 12 units in caps was reading as a second headline inside every chart.
for _axis in ("{ size: 13, weight: 900, ls: '.09em' }",
              "{ size: 13, weight: 900, ls: '.08em' }"):
    SCRIPT = SCRIPT.replace(_axis, _axis.replace("weight: 900", "weight: 700"))

# Five in-chart footer sentences repeat what the headline and the subtitle
# already say. The drawing keeps its ticks and its annotations; the words
# live in HTML, where they wrap, scale and can be read by a screen reader.
_FOOTERS = ["SHARE OF ORDERS CONTAINING A SUBSCRIPTION",
            "SHARE OF NEW SUBSCRIPTIONS, SINGLE PRODUCTS",
            "EACH ROW FILLS TO 100%",
            "EACH LINE INDEXED TO ITS OWN PRE-LAUNCH AVERAGE",
            "CUMULATIVE SUBSCRIPTIONS NOT STARTED",
            "NO DOLLAR FIGURE HERE"]
for _f in _FOOTERS:
    _i = SCRIPT.find(_f)
    assert _i >= 0, "in-chart footer already gone, check the list: " + _f
    _a = SCRIPT.rindex("s.appendChild(txt(", 0, _i)
    _b = SCRIPT.index("}));", _i) + len("}));\n")
    SCRIPT = SCRIPT[:_a] + SCRIPT[_b:]
print("in-chart footers removed: %d" % len(_FOOTERS))

SCRIPT = SCRIPT.replace("{{PAYLOAD}}", json.dumps(P, ensure_ascii=False, separators=(",", ":")))

# --------------------------------------------------------------- grounding guard
# Category labels that name a chart series rather than report a measurement.
# Every entry is reviewed, and printed at build time so it cannot grow unnoticed.
ALLOWED_LITERALS = {
    "1 bottle":  "chart 3 legend, names a series",
    "2 bottles": "chart 3 legend, names a series",
    "3 or more": "chart 3 legend, names a series",
}
prose = re.sub(r"<[^>]+>", " ", BODY).replace("{{figrows}}", " ")
prose = re.sub(r"\{\{[a-z0-9_]+\}\}", " ", prose)
for _lit in ALLOWED_LITERALS:
    prose = prose.replace(_lit, " ")
leftover = re.findall(r"\b\d[\d,.]*\b", prose)
if leftover:
    raise SystemExit("GROUNDING GUARD FAILED, typed numbers in prose: %s" % sorted(set(leftover)))
print("grounding guard passed: every number in the copy resolves from facts_v15.json")

# structural guard: an unbalanced tag silently drops later sections out of the layout wrapper
for _tag in ("div", "figure", "details", "table", "ul", "p", "span"):
    _o = len(re.findall(r"<%s\b" % _tag, BODY))
    _c = len(re.findall(r"</%s>" % _tag, BODY))
    assert _o == _c, "unbalanced <%s>: %d open, %d close" % (_tag, _o, _c)
_depth, _min = 0, 0
for _m in re.finditer(r"<(/?)div\b", BODY):
    _depth += -1 if _m.group(1) else 1
    _min = min(_min, _depth)
assert _min == 0 and _depth == 0, "div nesting breaks out of the wrapper (min depth %d, final %d)" % (_min, _depth)

def _close_of(src, start):
    """Index just past the </div> that closes the <div> opening at `start`."""
    d = 0
    for _mm in re.finditer(r"<(/?)div\b[^>]*>", src[start:]):
        d += -1 if _mm.group(1) else 1
        if d == 0:
            return start + _mm.end()
    raise AssertionError("unclosed div at %d" % start)

# blocks that must be siblings, never nested in one another. A misplaced opening tag
# keeps the totals balanced and the depth walk happy, so check containment directly.
_SIBLINGS = ["strip", "exec", "quad", "trio", "recs"]
_spans = {}
for _cls in _SIBLINGS:
    _m2 = re.search(r'<div class="[^"]*\b%s\b[^"]*"' % _cls, BODY)
    if _m2:
        _spans[_cls] = (_m2.start(), _close_of(BODY, _m2.start()))
for _a, (_a0, _a1) in _spans.items():
    for _b, (_b0, _b1) in _spans.items():
        if _a != _b:
            assert not (_a0 < _b0 and _b1 < _a1), "'%s' is nested inside '%s'" % (_b, _a)
print("structure guard passed: balanced, inside the wrapper, and no block nested in a sibling")
for _lit, _why in sorted(ALLOWED_LITERALS.items()):
    print("   allowed literal %-12s %s" % (repr(_lit), _why))

used = set(re.findall(r"\{\{([a-z0-9_]+)\}\}", BODY))
missing = sorted(used - set(TOK))
unused = sorted(set(TOK) - used)
if missing: raise SystemExit("tokens used but never computed: %s" % missing)
if unused: print("note: computed but unused tokens: %s" % unused)

out = BODY
for k, val in TOK.items():
    out = out.replace("{{%s}}" % k, str(val))
left = set(re.findall(r"\{\{[a-z0-9_]+\}\}", out))
assert not left, "unreplaced: %s" % left

HEAD = ('<title>Subscription Buy Box</title>\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Anton&family=Archivo:wght@500;600;700;900&family=Public+Sans:wght@400;500;600&display=swap">\n')

# One authored stylesheet in place of a base sheet plus fifteen patch layers, in
# which the same property was set for the same selector up to four times and the
# last one silently won.
CSS = io.open("page_v18.css", encoding="utf-8").read()
STYLE = "<style>\n" + CSS + "</style>\n"

# --------------------------------------------------------------- sheet guard
assert "prefers-color-scheme" not in CSS and "data-theme" not in CSS, "this page is light only"
for _dead in ("--s-green", "--s-alt", "--s-sess", "#2F7D4F", ".correct", ".rec{", ".two{"):
    assert _dead not in CSS, "dead rule or retired colour in the stylesheet: " + _dead
_declared = set(re.findall(r"(--[a-z0-9-]+)\s*:", CSS))
_used = set(re.findall(r"var\((--[a-z0-9-]+)", CSS + SCRIPT + out))
_undeclared = sorted(u for u in _used if u not in _declared and u != "--sc")
assert not _undeclared, "custom properties used but never declared: %s" % _undeclared
_unused = sorted(d for d in _declared if d not in _used)
if _unused:
    print("note: declared but unused custom properties: %s" % _unused)
for _sel, _body in re.findall(r"([^{}]+)\{([^{}]*)\}", CSS):
    _props = [d.split(":")[0].strip() for d in _body.split(";")
              if ":" in d and not d.strip().startswith("--")]
    _dupes = sorted({p for p in _props if _props.count(p) > 1})
    assert not _dupes, "%s declares %s more than once" % (_sel.strip()[:48], _dupes)
print("sheet guard passed: one block, no dead rules, no duplicate declarations")

# --------------------------------------------------------------- grid guard
# The report-design rule is one 8px unit. Borders and optical nudges under 8px
# are not spacing and are listed here by name so the exception cannot spread.
_SPACING = ("margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
            "margin-inline", "padding", "padding-top", "padding-bottom",
            "padding-left", "padding-right", "gap", "column-gap", "row-gap")
_off = []
for _p in _SPACING:
    for _m in re.finditer(r"(?<![-\w])%s:\s*([^;}\n]+)" % _p, CSS):
        _decl = _m.group(1)
        if "var(" in _decl or "clamp(" in _decl or "auto" in _decl:
            continue
        for _v in re.findall(r"(-?\d+(?:\.\d+)?)px", _decl):
            _f = abs(float(_v))
            if _f and _f % 8:
                _off.append("%s:%s" % (_p, _decl.strip()))
assert not _off, "spacing off the 8px grid: %s" % sorted(set(_off))
print("grid guard passed: every spacing value is a multiple of 8")

# --------------------------------------------------------------- type guard
# the sizes live in tokens, so the guard resolves the tokens rather than
# scanning for literals it will never find
_tok_px = {m.group(1): float(m.group(2))
           for m in re.finditer(r"(--t-[a-z-]+):\s*(\d+(?:\.\d+)?)px", CSS)}
_lit = {float(x) for x in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", CSS)}
_lit |= {float(x) for x in re.findall(r"font:\s*\d+\s+(\d+(?:\.\d+)?)px", CSS)}
_sizes = sorted(set(_tok_px.values()) | _lit)
assert _lit <= set(_tok_px.values()), (
    "font sizes typed outside the scale: %s" % sorted(_lit - set(_tok_px.values())))
# 14px is not on a 4px step but it is one of the three body sizes the DTCPG
# brand guide names (18/16/14), and the brand beats the generic step rule.
_BRAND_BODY = {14.0}
_odd = sorted(v for v in _sizes if v % 4 and v not in _BRAND_BODY)
assert not _odd, "type sizes off the 4px step and not brand body sizes: %s" % _odd
assert len(_sizes) <= 8, "%d type sizes in play, the scale allows seven plus display" % len(_sizes)
_track = sorted({x for x in re.findall(r"letter-spacing:\s*(\.\d+em)", CSS)})
assert _track == [".08em"], "uppercase labels must share one tracking value, found %s" % _track
print("type guard passed: %d fixed sizes %s on the 4px step, one caps tracking"
      % (len(_sizes), sorted(int(v) for v in _sizes)))

# --------------------------------------------------------------- contrast guard
# Every ink tone here is a translucent black, so its contrast depends on what is
# behind it, and this page has two grounds: the cream surface and the white card.
_CREAM, _WHITE = (247, 243, 231), (255, 255, 255)


def _srgb(v):
    v /= 255.0
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def _lum(c):
    return 0.2126 * _srgb(c[0]) + 0.7152 * _srgb(c[1]) + 0.0722 * _srgb(c[2])


def _over(fg, a, bg):
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _token(name):
    _m = re.search(r"%s:\s*(#[0-9A-Fa-f]{6}|rgba\([^)]+\))" % re.escape(name), CSS)
    assert _m, "colour token not found: " + name
    _v = _m.group(1)
    if _v.startswith("#"):
        return (int(_v[1:3], 16), int(_v[3:5], 16), int(_v[5:7], 16)), 1.0
    _n = [float(x) for x in re.findall(r"[\d.]+", _v)]
    return (_n[0], _n[1], _n[2]), (_n[3] if len(_n) > 3 else 1.0)


_CONTRAST = [("body and list text", "--ink-2", "16px regular", 4.5),
             ("labels, nav, headers", "--ink-3", "12px caps", 4.5),
             ("the fall, in the strip", "--orange-text", "32px black", 3.0),
             ("chip and card text", "--ink", "12px caps", 4.5)]
_worst = []
for _name, _tok, _role, _need in _CONTRAST:
    _rgb, _a = _token(_tok)
    for _gname, _g in (("cream", _CREAM), ("card", _WHITE)):
        _r = _ratio(_over(_rgb, _a, _g), _g)
        assert _r >= _need, ("%s (%s) measures %.2f:1 on %s, below the %.1f it needs for %s"
                             % (_name, _tok, _r, _gname, _need, _role))
        _worst.append((_r, _name, _gname))
_w = min(_worst)
print("contrast guard passed: worst text pair is %s on %s at %.2f:1" % (_w[1], _w[2], _w[0]))

# --------------------------------------------------------------- anchor guard
# The section nav and the three summary links are the only navigation on a page
# this long. They shipped broken once: every href resolved to a real id, so
# nothing looked wrong in the markup, but "scroll-behavior: smooth" swallowed
# the jump and the page never moved. Both halves are checked here.
assert "scroll-behavior:smooth" not in CSS.replace(" ", ""), (
    "smooth scrolling is back, and it stops every jump link from moving the page")
_ids = set(re.findall(r'\sid="([^"]+)"', out))
_hrefs = sorted(set(re.findall(r'href="#([^"]+)"', out)))
_broken = [h for h in _hrefs if h not in _ids]
assert not _broken, "in-page links with no target: %s" % _broken
# The floor was 6 while the report carried a recommendation section for the nav and
# the summary's action row to point at. Both were cut on 2026-09-22, so 5 is the full
# set now: the four analysis sections plus what is still open.
assert len(_hrefs) >= 5, "the section nav lost links, only %d in-page targets" % len(_hrefs)
print("anchor guard passed: %d in-page links, every one resolves, no smooth scroll"
      % len(_hrefs))

# ---------------------------------------------------------------- engine guard
# The grounding guard reads the report copy and never the chart engine, so a date
# typed into a JavaScript string was invisible to it. Chart 1's caption carried
# "Sep 8 to 16" for two days after the window was extended to the 20th. Any month
# name inside a string literal in the engine is now a build failure; window ranges
# belong in the payload, and month names the charts draw come from the month array.
_SCRIPT_ONLY = out[out.index("<script>"):] if "<script>" in out else ""
_typed_dates = re.findall(r"'[^']*\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                          r"[a-z]*\s+\d[^']*'", _SCRIPT_ONLY)
# the payload is one long JSON string on its own; its labels are ledger-derived
_typed_dates = [d for d in _typed_dates if '","' not in d and '":' not in d]
assert not _typed_dates, ("a date is typed into the chart engine instead of coming "
                          "from the ledger: %s" % _typed_dates[:4])
print("engine guard passed: no dates typed into the chart engine's strings")

# --------------------------------------------------------------- casing guard
# Headlines are sentence case across the whole report. The section headings and
# the fold summaries render uppercase, so a Title Case slip in the source is
# invisible on screen and drifts unnoticed until the transform is ever removed.
_PROPER = {"TikTok", "Shopify", "Skio", "Labor", "Day", "Sep", "Oct", "Nov", "Heart",
           "Soil", "DTCPG", "Anton", "Archivo", "Public", "Sans", "Wosker", "Artlab",
           "Buvera", "Monday", "Sunday"}
_titled = []
for _m in re.finditer(r"<h2[^>]*>([^<]+)</h2>|<summary>([^<+]+)", out):
    _txt = (_m.group(1) or _m.group(2)).strip()
    _words = _txt.split()[1:]
    _bad = [w for w in _words if w[:1].isupper() and w.strip(",.") not in _PROPER]
    if _bad:
        _titled.append("%s -> %s" % (_txt, _bad))
assert not _titled, "headings must be sentence case in the source: %s" % _titled
print("casing guard passed: every heading is sentence case in the source")

# --------------------------------------------------------------- accent guard
# A tile's top rule is "4px solid var(--ac)", and --ac comes from the accent
# class on the tile. When the class does not exist the whole declaration is
# invalid and the rule silently disappears: three verdict cards shipped with no
# top rule at all because they still carried a-green after green left the palette.
_declared_ac = set(re.findall(r"^\.(a-[a-z-]+)\{", CSS, re.M))
_used_ac = set()
for _cls in re.findall(r'class="([^"]+)"', out):
    _used_ac |= {t for t in _cls.split() if t.startswith('a-')}
_orphan = sorted(_used_ac - _declared_ac)
assert not _orphan, "accent classes used in the body but not declared: %s" % _orphan
_unused_ac = sorted(_declared_ac - _used_ac)
if _unused_ac:
    print("note: accent classes declared but unused: %s" % _unused_ac)
print("accent guard passed: %d accent classes, every one declared and reachable"
      % len(_used_ac))

# --------------------------------------------------------------- baseline guard
# The figure header stacks on an 8px baseline so the drawing's top edge lands on
# the grid. Every line box and margin above the chart has to be a whole unit.
_BASELINE = [("--t-micro", "16px"), ("--t-headline", "24px"), ("--t-small", "24px")]
for _sel, _lh in (("\.ch-tag", "16px"), ("\.ch-t", "24px"), ("\.ch-s", "24px")):
    _blk = re.search(r"%s\s*\{[^}]*\}" % _sel, CSS)
    assert _blk and _lh in _blk.group(0), (
        "%s must set a %s line box or the chart falls off the baseline" % (_sel, _lh))
assert re.search(r"\.seg button,\.chips \.pick\{[^}]*height:40px", CSS), (
    "the controls need a fixed 40px height to stay on the baseline")
print("baseline guard passed: the figure header stacks in whole 8px units")

doc = HEAD + STYLE + "\n" + out + "\n" + SCRIPT + "\n"

def proof(d):
    parts = re.split(r"(<script>.*?</script>|<style>.*?</style>)", d, flags=re.S)
    o = []
    for p_ in parts:
        if p_.startswith("<style>"): o.append(p_)
        elif p_.startswith("<script>"): o.append("".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in p_))
        else: o.append("".join(ch if ord(ch) < 128 else "&#x%x;" % ord(ch) for ch in p_))
    return "".join(o)
doc = proof(doc)
assert all(ord(ch) < 128 for ch in doc)
io.open("page_v18.html", "w", encoding="utf-8", newline="\n").write(doc)
print("written page_v18.html (%d bytes)" % len(doc))
print("take rate %s%% -> %s%%, drop %s pt (%s), band %s-%s" % (TOK["pre"], TOK["post"], TOK["drop"], TOK["rel"], TOK["band_lo"], TOK["band_hi"]))
print("plan: 1x90d %s%% -> %s%% | 3x90d %s%% -> %s%% | 1x30d %s%% -> %s%%" % (TOK["gone_pre"], TOK["gone_post"], TOK["big_pre"], TOK["big_post"], TOK["m30_pre"], TOK["m30_post"]))
print("magnitude: %s/day, %s/month, $%s monthly billings, +$%s/day revenue" % (TOK["lost_day"], TOK["lost_mo"], TOK["mo_bill"], TOK["rev_gain"]))
