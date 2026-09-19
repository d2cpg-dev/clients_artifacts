# -*- coding: utf-8 -*-
"""Assembles the v15 report. Every number comes from facts_v15.json.
A guard strips HTML tags from the template and fails if any digit survives in the prose,
which is what keeps the copy grounded in the data rather than typed by hand."""
import json, io, re, datetime, math

F = json.load(io.open("facts_v15.json", encoding="utf-8"))
P = json.load(io.open("payload_v15.json", encoding="utf-8"))
BQF = json.load(io.open("bq_facts.json", encoding="utf-8"))
# selling-plan evidence: which plan group the box presents, and how quantity is chosen at each cycle
PF = json.load(io.open("plan_facts.json", encoding="utf-8"))
BODY = io.open("page_v15_body.html", encoding="utf-8").read()
TPL = io.open("page_v10_template.html", encoding="utf-8").read()
STYLE = TPL[TPL.index("<style>"):TPL.index("</style>") + len("</style>")]
SCRIPT = TPL[TPL.index("<script>"):TPL.index("</script>") + len("</script>")]

# --------------------------------------------------------------- single theme
# This page is light only, by decision. Carrying a second theme meant carrying a set of
# colours nobody could verify, so both dark blocks come out of the inherited stylesheet.
_before = len(STYLE)
STYLE = re.sub(r"\n  @media \(prefers-color-scheme: dark\)\{[^}]*\{.*?color-scheme: dark; \} \}",
               "", STYLE, flags=re.S)
STYLE = re.sub(r"\n  :root\[data-theme=\"dark\"\]\{.*?color-scheme: dark; \}",
               "", STYLE, flags=re.S)
assert "prefers-color-scheme" not in STYLE, "dark media block survived"
assert 'data-theme="dark"' not in STYLE, "dark theme block survived"
print("single theme: removed %d bytes of dark-mode tokens" % (_before - len(STYLE)))

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
    "var L = 210, R = 840, T = 16, rowH = 28;", "c3 row height")
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
SCRIPT = patch(SCRIPT, "var L = 250, R = 790, T = 14, rowH = 48, gap = 14, MAX = 65;",
    "var L = 250, R = 790, T = 14, rowH = 40, gap = 12, MAX = 50;",
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
SCRIPT = patch(SCRIPT, "'Take rate, ' + m.name.toLowerCase();",
    "'Take rate, ' + m.name.charAt(0).toLowerCase() + m.name.slice(1);", "c1 title casing")
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
# c1: the post-sale mean was drawn in blue inside an orange-shaded window
SCRIPT = patch(SCRIPT,
    "[post, 'var(--blue)', 'AFTER THE SALE ' + post.toFixed(1) + '%']",
    "[post, 'var(--core-black)', 'AFTER THE SALE ' + post.toFixed(1) + '%']",
    "c1 post-sale mean line")
# c4: the PRE-LAUNCH marker was right-anchored outside the drawing and clipped by 25px
SCRIPT = patch(SCRIPT,
    "s.appendChild(txt(L - 10, yOf(100) - 12, 'PRE-LAUNCH', { anchor: 'end', size: 9, weight: 900, ls: '.08em' }));",
    "s.appendChild(txt(L + 4, yOf(100) - 9, 'PRE-LAUNCH', { anchor: 'start', size: 9, weight: 900, ls: '.08em' }));",
    "c4 pre-launch label inside the plot")
# the payload is injected further down, once the schedule and forecast series exist

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

GANTT_LABEL_PX = 11.5
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
EXTRA_JS = """
  /* ---------- chart 5 : schedule gantt ---------- */
  (function () {
    var s = document.getElementById('c5'); if (!s) return;
    var G = P.gantt, L = G.gutter, R2 = 856, T = 34, rowH = 34, gap = 10;
    var col = {}; G.who.forEach(function (w) { col[w.k] = w.col; });
    var xOf = function (f) { return L + (R2 - L) * f; };
    G.ticks.forEach(function (t) {
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
    });
    var yb = T + G.rows.length * (rowH + gap);
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
      if (i % 2 === 0 || i === N - 1)
        s.appendChild(txt(xOf(i), B + 20, F6.labels[i].toUpperCase(),
          { size: 9.5, weight: 700, ls: '.04em' }));
    });
    s.appendChild(el('line', { x1: L, x2: R2, y1: B, y2: B, stroke: 'var(--rule)', 'stroke-width': 1.5 }));
    s.appendChild(txt(R2 + 12, yOf(F6.mid[N - 1]) - 2, F6.mid[N - 1].toLocaleString(),
      { anchor: 'start', size: 15, weight: 900, fill: 'var(--ink)' }));
    s.appendChild(txt(R2 + 12, yOf(F6.mid[N - 1]) + 12, 'SUBSCRIPTIONS',
      { anchor: 'start', size: 9, weight: 900, ls: '.07em' }));
    s.appendChild(txt(R2 + 12, yOf(F6.mid[N - 1]) + 24, 'AT 12 MONTHS',
      { anchor: 'start', size: 9, weight: 900, ls: '.07em' }));
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
for _a, _b in (("size: 9,", "size: 11,"), ("size: 9.5,", "size: 11,"),
               ("size: 10,", "size: 11,"), ("size: 10.5,", "size: 11,")):
    SCRIPT = SCRIPT.replace(_a, _b)
for _bad in ("size: 9,", "size: 9.5,", "size: 10,", "size: 10.5,"):
    assert _bad not in SCRIPT, "chart type below the 11px floor: " + _bad

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
EXTRA = ("<style>\n"
         "  .cell .val .u{font-size:14px}\n"
         # executive summary: the numbers come from a CSS counter, never typed into the markup
         "  .exec{counter-reset:ex;margin:26px 0 0;max-width:90ch;"
         "border-top:1.5px solid var(--core-black)}\n"
         "  .exec-row{counter-increment:ex;display:grid;"
         "grid-template-columns:2.2em minmax(0,1fr) auto;gap:6px 18px;align-items:baseline;"
         "padding:15px 0;border-bottom:1px solid var(--rule)}\n"
         "  .exec-row::before{content:counter(ex,decimal-leading-zero);"
         "font-family:'Archivo',sans-serif;font-weight:900;font-size:11px;letter-spacing:.1em;"
         "color:var(--orange);font-variant-numeric:tabular-nums}\n"
         "  .exec-t{font-size:16.5px;line-height:1.55;color:var(--ink-2)}\n"
         "  .exec-t b{color:var(--ink);font-weight:600}\n"
         "  .exec-l{font-family:'Archivo',sans-serif;font-weight:700;font-size:11px;"
         "letter-spacing:.08em;text-transform:uppercase;color:var(--blue);text-decoration:none;"
         "white-space:nowrap;border-bottom:1.5px solid transparent;padding-bottom:1px}\n"
         "  .exec-l:hover{border-bottom-color:var(--blue)}\n"
         "  .exec-act .exec-t{color:var(--ink);font-weight:500}\n"
         "  @media(max-width:640px){.exec-row{grid-template-columns:2.2em minmax(0,1fr)}\n"
         "    .exec-l{grid-column:2;justify-self:start;margin-top:4px}}\n"
         "  html{scroll-behavior:smooth}\n"
         "  @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}\n"
         "  h2[id]{scroll-margin-top:18px}\n"
         # orange on cream is 2.2:1, too weak for a 33px figure; the label above carries the colour
         "  .cell .val.o{color:var(--ink)}\n"
         "  .ranges{margin:0 0 16px}\n"
         # one accent system, brand tokens only, shared by every card block
         "  .a-orange{--ac:var(--orange);--ac-t:var(--tint-orange)}\n"
         "  .a-blue{--ac:var(--blue);--ac-t:rgba(54,54,204,.13)}\n"
         "  .a-ret{--ac:var(--retention);--ac-t:var(--tint-blue)}\n"
         "  .a-deep{--ac:var(--deep);--ac-t:rgba(38,38,143,.13)}\n"
         "  .a-green{--ac:var(--s-green);--ac-t:rgba(47,125,79,.14)}\n"
         "  .a-neutral{--ac:var(--ink-3);--ac-t:rgba(42,33,28,.07)}\n"
         # the pill and its border carry the hue; the label stays ink so it is legible
         "  .chip{display:inline-flex;align-items:center;font-family:'Archivo',sans-serif;"
         "font-weight:900;font-size:10px;letter-spacing:.11em;text-transform:uppercase;"
         "color:var(--ink);background:var(--ac-t);border:1px solid var(--ac);border-radius:999px;"
         "padding:4px 10px;align-self:flex-start}\n"
         "  .quad,.trio{display:grid;gap:14px;margin:18px 0 4px}\n"
         "  .quad{grid-template-columns:repeat(4,minmax(0,1fr))}\n"
         "  .trio{grid-template-columns:repeat(3,minmax(0,1fr))}\n"
         "  .trio.vgap{margin-top:16px}\n"
         "  .box.ac{border-top:4px solid var(--ac);display:flex;flex-direction:column;"
         "padding:18px 20px 20px}\n"
         "  .box.ac .lbl{font-size:14.5px;line-height:1.3;letter-spacing:0;text-transform:none;"
         "color:var(--ink);font-weight:700;margin:11px 0 7px}\n"
         "  .box.ac p{font-size:14px;line-height:1.5}\n"
         # value read-at-a-glance cards
         "  .stat{background:var(--card);border:1px solid var(--rule);border-top:4px solid var(--ac);"
         "border-radius:18px;padding:18px 20px 20px;display:flex;flex-direction:column;"
         "box-shadow:var(--shadow-sm)}\n"
         "  .stat-k{font-size:13.5px;color:var(--ink-2);margin:11px 0 10px;line-height:1.35}\n"
         "  .stat-v{font-family:'Archivo',sans-serif;font-weight:900;font-size:25px;"
         "letter-spacing:-.02em;color:var(--ink);font-variant-numeric:tabular-nums;line-height:1.1}\n"
         "  .stat-v i{font-style:normal;color:var(--ink-3);font-weight:600;padding:0 3px}\n"
         "  .stat-d{font-family:'Archivo',sans-serif;font-weight:900;font-size:13px;margin-top:8px}\n"
         "  .stat-d.up{color:var(--blue)} .stat-d.nc{color:var(--ink-3)}\n"
         "  .stat.lead{border-width:1px;border-top-width:4px;box-shadow:0 2px 10px rgba(236,142,40,.16)}\n"
         # recommendations: the one action runs full width, the four holds sit under it
         "  .recs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:18px 0 4px}\n"
         "  .rc{background:var(--card);border:1px solid var(--rule);border-top:4px solid var(--ac);"
         "border-radius:18px;padding:18px 20px 20px;display:flex;flex-direction:column;"
         "box-shadow:var(--shadow-sm)}\n"
         "  .rc h3{font-size:15px;line-height:1.3;margin:11px 0 7px}\n"
         "  .rc p{font-size:14px;line-height:1.5;margin:0;max-width:none;color:var(--ink-2)}\n"
         "  .rc .who{font-family:'Archivo',sans-serif;font-weight:700;font-size:10.5px;"
         "letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);margin-top:auto;"
         "padding-top:12px;border-top:1px solid var(--rule);display:block;line-height:1.4}\n"
         "  .rc.primary{grid-column:1 / -1;display:grid;"
         "grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:6px 30px;align-items:start}\n"
         "  .rc.primary .chip{grid-column:1}\n"
         "  .rc.primary h3{grid-column:1;font-size:22px;line-height:1.15;margin:12px 0 0}\n"
         "  .rc.primary p{grid-column:2;grid-row:1 / span 3;font-size:15px;align-self:center}\n"
         "  .rc.primary .who{grid-column:1;border-top:none;padding-top:10px;margin-top:8px;"
         "color:var(--orange)}\n"
         "  @media(max-width:900px){.quad,.recs{grid-template-columns:repeat(2,minmax(0,1fr))}\n"
         "    .rc.primary{grid-template-columns:minmax(0,1fr)}\n"
         "    .rc.primary p{grid-column:1;grid-row:auto}\n"
         "    .rc.primary h3{font-size:19px}}\n"
         "  @media(max-width:700px){.trio{grid-template-columns:minmax(0,1fr)}}\n"
         "  @media(max-width:560px){.quad,.recs{grid-template-columns:minmax(0,1fr)}}\n"
         "  :root{--ramp-lo:#E8E1CE;--ramp-mid:#BBA173;color-scheme:light}\n"
         "  .rc.primary .who{color:var(--ink)}\n"
         "  .exec-row::before{color:var(--ink-2)}\n"
         "  .up,.dn{color:var(--ink);font-weight:700}\n"
         "  .ro .g.u,.ro .g.w{color:var(--ink)}\n"
         "  .fold-ind{color:var(--ink);border-color:var(--orange);background:var(--tint-orange)}\n"
         "  li::marker{color:var(--ink-2)}\n"
         "  .cell .val.b{color:var(--ink)}\n"
         "  .wrap > p{color:var(--ink);font-size:16.5px;line-height:1.6}\n"
         "  .box.ac .lbl{font-size:15px}\n"
         "  .ch-t{font-size:16px}\n"
         "  figure,.quad,.trio,.recs{margin:20px 0 18px}\n"
         "  figure + figure{margin-top:34px}\n"
         "  .trio.vgap{margin-top:20px}\n"
         "  .recs{grid-template-columns:repeat(2,minmax(0,1fr))}\n"
         "  .rc.primary h3{font-size:24px;font-weight:900;letter-spacing:-.01em;line-height:1.12}\n"
         "  .rc.primary{box-shadow:0 3px 14px rgba(236,142,40,.20);border-top-width:6px;margin-bottom:8px}\n"
         "  @media(max-width:900px){.recs{grid-template-columns:minmax(0,1fr)}}\n"
         "  .chips label .nm{color:var(--ink)}\n"
         "  .chips label:not(.on) .nm{color:var(--ink-3)}\n"
         "  .chips label.on .q{color:var(--ink-2)}\n"
         "  h1 em{color:var(--ink);box-shadow:inset 0 -0.16em 0 var(--tint-orange)}\n"
         # laptop-first composition: wider wrapper, chart pinned to its viewBox scale
         "  .wrap{max-width:1360px;padding-left:clamp(20px,2vw,28px);"
         "padding-right:clamp(20px,2vw,28px);padding-bottom:48px;"
         "container-type:inline-size;container-name:wrap}\n"
         "  svg{min-width:0}\n"
         "  .ch-scroll{overflow-x:auto;scrollbar-width:thin}\n"
         "  .ch-scroll > svg{width:880px;min-width:880px;margin-inline:auto}\n"
         "  figure{padding:16px 20px 12px;margin:14px 0 12px}\n"
         "  figure + figure{margin-top:18px}\n"
         "  .quad,.trio,.recs{margin:14px 0 12px}\n"
         "  h2{margin:28px 0 8px}\n"
         "  .ch-t{margin:0 0 2px}\n"
         "  .ch-s{margin:0 0 10px}\n"
         "  details.fold{margin:24px 0 0}\n"
         "  footer{margin-top:40px}\n"
         # the explanation sits beside the chart so both fit in one viewport
         "  figure{display:grid;grid-template-columns:minmax(0,1fr);column-gap:24px}\n"
         "  figure > *{grid-column:1;min-width:0}\n"
         "  @container wrap (min-width:1194px){\n"
         "    figure{grid-template-columns:880px minmax(248px,1fr)}\n"
         # -1 with no explicit rows resolves to line 1, which pinned the caption to row 1
         # and stretched the figure title to the caption's height. Span instead.
         "    figure > figcaption{grid-column:2;grid-row:1 / span 20;align-self:start;margin:0;"
         "border-top:none;border-left:1px solid var(--rule);padding:2px 0 0 24px;font-size:14px}\n"
         "    figure.noside{grid-template-columns:minmax(0,1fr)}\n"
         "    figure.noside > figcaption{grid-column:1;grid-row:auto;border-left:none;"
         "border-top:1px solid var(--rule);padding:13px 0 0;margin-top:14px}\n"
         "  }\n"
         # the measure row overflowed 880px by a single pixel and wrapped to two rows
         "  .seg button{padding:8px 12px}\n"
         "  .seg{margin:0 0 10px;gap:5px}\n"
         "  .seg-row{gap:6px 14px}\n"
         # a disclosure nested inside a figure, sized down from the page-level one
         "  details.fold.sub{margin:12px 0 0}\n"
         "  details.fold.sub > summary{font-family:'Archivo',sans-serif;font-weight:900;"
         "font-size:11px;letter-spacing:.11em;text-transform:uppercase;padding:0 0 4px;"
         "color:var(--ink-2)}\n"
         "  details.fold.sub > summary .fold-ind{width:20px;height:20px;font-size:12px}\n"
         "  details.fold.sub .readout{margin-top:10px}\n"
         "  details.fold.sub p{font-size:14.5px;margin:8px 0 0;max-width:86ch}\n"
         # the jump links the deleted summary rows used to carry
         "  .secnav{display:flex;flex-wrap:wrap;gap:4px 18px;margin:6px 0 0}\n"
         "  .secnav a{font-family:'Archivo',sans-serif;font-weight:700;font-size:11px;"
         "letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);text-decoration:none;"
         "border-bottom:1.5px solid transparent;padding-bottom:1px}\n"
         "  .secnav a:hover{color:var(--ink);border-bottom-color:var(--orange)}\n"
         "  .mast{align-items:flex-end}\n"
         # keyboard access: a way past the masthead, and a visible focus ring on everything
         "  .skip{position:absolute;left:-9999px;top:0;z-index:100;background:var(--core-black);"
         "color:var(--base-white);font-family:'Archivo',sans-serif;font-weight:700;font-size:13px;"
         "padding:10px 16px;border-radius:0 0 10px 0;text-decoration:none}\n"
         "  .skip:focus{left:0}\n"
         "  a:focus-visible,summary:focus-visible,button:focus-visible,"
         "input:focus-visible + .dot{outline:3px solid var(--blue);outline-offset:2px;"
         "border-radius:4px}\n"
         "  summary{cursor:pointer}\n"
         # a client report gets printed; make that not embarrassing
         "  @media print{\n"
         "    @page{margin:14mm}\n"
         "    .skip,.secnav,#tip,.seg-row,.chips{display:none}\n"
         "    .wrap{max-width:none;padding:0}\n"
         "    details>*{display:block}\n"
         "    details.fold>summary{list-style:none}\n"
         "    details.fold>summary .fold-ind{display:none}\n"
         "    figure,.box,.stat,.rc,.tbl-wrap,.exec-row{break-inside:avoid;box-shadow:none}\n"
         "    h2{break-after:avoid}\n"
         "    figure{grid-template-columns:minmax(0,1fr)}\n"
         "    figure>figcaption{grid-column:1;grid-row:auto;border-left:none;"
         "border-top:1px solid var(--rule);padding:10px 0 0;margin-top:10px}\n"
         "    .ch-scroll{overflow:visible}\n"
         "    .ch-scroll>svg{width:100%;min-width:0}\n"
         "  }\n"
         "</style>\n")
doc = HEAD + STYLE + EXTRA + "\n" + out + "\n" + SCRIPT + "\n"

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
io.open("page_v15.html", "w", encoding="utf-8", newline="\n").write(doc)
print("written page_v15.html (%d bytes)" % len(doc))
print("take rate %s%% -> %s%%, drop %s pt (%s), band %s-%s" % (TOK["pre"], TOK["post"], TOK["drop"], TOK["rel"], TOK["band_lo"], TOK["band_hi"]))
print("plan: 1x90d %s%% -> %s%% | 3x90d %s%% -> %s%% | 1x30d %s%% -> %s%%" % (TOK["gone_pre"], TOK["gone_post"], TOK["big_pre"], TOK["big_post"], TOK["m30_pre"], TOK["m30_post"]))
print("magnitude: %s/day, %s/month, $%s monthly billings, +$%s/day revenue" % (TOK["lost_day"], TOK["lost_mo"], TOK["mo_bill"], TOK["rev_gain"]))
