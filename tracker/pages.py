"""A static page for every project, an index of them, and a sitemap.

Each page works without JavaScript (the chart is drawn here as SVG and themed by CSS classes in site/pages.css), so
the pages can be shared, previewed by link unfurlers and indexed. The interactive tracker opens the same project at
`#project=<slug>`.

Slugs come from the project's name in its latest plan. If a later plan renames a project, its slug changes too; add
the old slug to REDIRECTS when that happens so shared links keep working.
"""
import html
import math
import os
import re
import shutil
from xml.sax.saxutils import escape as xml_escape

SITE_URL = "https://willmcnulty.github.io/UVA-Capital-Plan-Tracker/"
STACK = ["state_gf", "debt", "gifts", "other_funds"]  # bottom to top, same order and colors as the app
LINK_TEXT = {
    "single-name": "same name every year",
    "exact-key": "same name, spelling or punctuation differs",
    "fuzzy": "near-identical name (fuzzy match, checked by hand)",
    "override-confirmed": "renamed; link confirmed from the plans",
    "override-probable": "probable link; kept out of totals",
}
REDIRECTS = {}  # old slug -> current slug, for projects renamed after their page was published

e = html.escape


def slugify(name):
    s = name.lower().replace("&", " and ").replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def assign_slugs(projects):
    seen = {}
    for p in projects:
        s = slugify(p["id"])
        seen[s] = seen.get(s, 0) + 1
        p["slug"] = s if seen[s] == 1 else f"{s}-{seen[s]}"


def money(v):
    """Millions, as the plans print them."""
    a = abs(v)
    s = f"{a:,.0f}" if a >= 1000 else f"{a:,.1f}"
    return ("−$" if v < 0 else "$") + s + "M"


def pct(v, d=1):
    return ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.{d}f}%"


def nice_ticks(v, n=4):
    """Round tick values from 0 to at least v, about n steps."""
    if v <= 0:
        return [0.0, 1.0]
    raw = v / n
    p = 10 ** math.floor(math.log10(raw))
    step = next(m * p for m in (1, 2, 2.5, 5, 10) if m * p >= raw)
    k = math.ceil(v / step - 1e-9)
    return [round(step * i, 10) for i in range(k + 1)]


def tick_label(v):
    if v == 0:
        return "$0"
    return f"${v:,.0f}M" if v == int(v) else f"${v:,.1f}M"


def chart(p, years, labels, W, font):
    """Stacked columns of each year's budget by funding source, as SVG, `W` units wide."""
    H, ml, mr, mt, mb = 250, 14 + 4.2 * font, 8, 16, 40
    iw, ih = W - ml - mr, H - mt - mb
    by_year = {r["year"]: r for r in p["rows"]}
    ticks = nice_ticks(max(r["total"] for r in p["rows"]))
    top = ticks[-1]
    y = lambda v: mt + ih - v / top * ih
    slot = iw / len(years)
    bw = min(56, slot * 0.62)
    out = [f'<svg viewBox="0 0 {W} {H}" style="font-size:{font}px" role="img" aria-label="Stacked column chart of '
           f'the budget for {e(p["id"])} by funding source in each plan year; the table below has the same numbers">']
    for i, v in enumerate(ticks):
        out.append(f'<line class="{"axis" if i == 0 else "grid"}" x1="{ml:.1f}" x2="{W - mr}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>')
        out.append(f'<text class="tick" x="{ml - 7:.1f}" y="{y(v) + 4:.1f}" text-anchor="end">{tick_label(v)}</text>')
    for i, yr in enumerate(years):
        cx = ml + slot * (i + 0.5)
        r = by_year.get(yr)
        out.append(f'<text class="tick" x="{cx:.1f}" y="{H - mb + 17}" text-anchor="middle">{yr}</text>')
        if r is None:
            out.append(f'<text class="tick note" x="{cx:.1f}" y="{H - mb + 31}" text-anchor="middle">not listed</text>')
            continue
        if r["phase"] == "planning":
            out.append(f'<text class="tick note" x="{cx:.1f}" y="{H - mb + 31}" text-anchor="middle">planning</text>')
        base = 0.0
        for k in STACK:
            v = r[k]
            if v <= 0:
                continue
            out.append(f'<rect class="f-{k}" x="{cx - bw / 2:.1f}" y="{y(base + v):.1f}" width="{bw:.1f}" '
                       f'height="{max(0.5, y(base) - y(base + v)):.1f}"><title>{yr} {labels[k]}: {money(v)}</title></rect>')
            base += v
        out.append(f'<text class="val" x="{cx:.1f}" y="{y(base) - 6:.1f}" text-anchor="middle">{money(r["total"])}</text>')
    out.append("</svg>")
    return "\n".join(out)


def charts(p, years, labels):
    """A wide and a narrow drawing; pages.css shows the one that fits, so the text stays readable on a phone."""
    return (f'<div class="chart wide">{chart(p, years, labels, 640, 11)}</div>\n'
            f'<div class="chart narrow">{chart(p, years, labels, 340, 10)}</div>')


def story(p, real_year):
    d = p["drift"]
    if d is None:
        s = "The plans give fewer than two full budgets for this project, so there is no budget change to measure."
    elif abs(d["delta"]) > 0.005:
        s = (f'Its full budget went from {money(d["first"])} in the {d["first_year"]} plan to {money(d["last"])} in '
             f'the {d["last_year"]} plan ({pct(d["pct"])}), over {d["revisions"]} '
             f'revision{"" if d["revisions"] == 1 else "s"}.')
        if d["peak"] > max(d["first"], d["last"]) + 0.005:
            s += f' It peaked at {money(d["peak"])}.'
    else:
        s = f'Its full budget stayed at {money(d["last"])} across {d["n_years"]} plans ({d["first_year"]}-{d["last_year"]}).'
    if d is not None:
        s += (f' In {real_year} dollars, adjusted for construction-cost inflation, that is {money(d["first_real"])} '
              f'to {money(d["last_real"])} ({pct(d["pct_real"])}).')
    if p["conf"] == "probable":
        s += " This project is joined to an earlier name by a probable match, so it is left out of the site's totals."
    return s


def head(title, desc, url, depth, kind="article"):
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="UVA Capital Plan Tracker">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#232d4b">
<script src="{up}theme.js?v={{theme}}"></script>
<link rel="stylesheet" href="{up}pages.css?v={{css}}">
</head>
<body>
<header class="topbar band"><div class="wrap">
  <a class="brand" href="{up}">UVA Capital Plan Tracker</a>
  <nav aria-label="Links">
    <a href="{up}projects/">All projects</a>
    <a href="https://github.com/WillMcNulty/UVA-Capital-Plan-Tracker">Code on GitHub</a>
    <button type="button" class="theme-btn" data-theme-toggle>◐ Auto</button>
  </nav>
</div></header>
"""


def foot(source):
    return f"""<footer class="band"><div class="wrap">
  <div>Independent student project; not affiliated with or endorsed by the University of Virginia.</div>
  <div>Source: {e(source)}. <a href="https://github.com/WillMcNulty/UVA-Capital-Plan-Tracker">Code and data on GitHub</a> · <a href="https://willmcnulty.github.io/">More projects by William McNulty</a></div>
</div></footer>
</body>
</html>
"""


def project_page(p, data, real_year):
    years, labels = data["years"], data["fund_labels"]
    names = []
    for r in p["rows"]:
        if r["name"] not in names:
            names.append(r["name"])
    earlier = [n for n in names if n != p["rows"][-1]["name"]]
    d = p["drift"]
    first_listed, last_listed = p["years"][0], p["years"][-1]
    desc = (f'{p["id"]}: {p["division"]}, {p["status"].lower()}. Latest budget {money(p["latest_total"])} '
            f'in the {last_listed} UVA Major Capital Plan'
            + (f'; {pct(d["pct"])} since {d["first_year"]}' if d and abs(d["delta"]) > 0.005 else "")
            + ". Budget and funding year by year.")
    url = f'{SITE_URL}projects/{p["slug"]}/'
    tiles = [("Latest budget", money(p["latest_total"]), f'{last_listed} plan')]
    if d is not None:
        tiles.append(("Budget change, as published", pct(d["pct"]), f'{d["first_year"]} to {d["last_year"]}'))
        tiles.append((f"In {real_year} dollars", pct(d["pct_real"]), "After construction-cost inflation"))
    tiles.append(("In the plans", f'{len(p["years"])} of {len(years)}', f"{first_listed}-{last_listed}" if first_listed != last_listed else str(first_listed)))
    rows = []
    for r in p["rows"]:
        cells = [str(r["year"]), e(r["name"]) + (' <span class="muted">(planning authorization)</span>' if r["phase"] == "planning" else ""),
                 e(r["status"])] + [money(r[k]) if r[k] else "—" for k in data["fund_keys"]] + [money(r["total"]), e(LINK_TEXT.get(r["link"], r["link"]))]
        rows.append("<tr>" + "".join(f'<td{" class=\"num\"" if 3 <= i < 3 + len(data["fund_keys"]) + 1 else ""}>{c}</td>'
                                     for i, c in enumerate(cells)) + "</tr>")
    head_cells = ["Year", "Name in that plan", "Status"] + [labels[k] for k in data["fund_keys"]] + ["Total", "How it was linked"]
    thead = "".join(f'<th{" class=\"num\"" if 3 <= i < 3 + len(data["fund_keys"]) + 1 else ""}>{e(h)}</th>' for i, h in enumerate(head_cells))
    used = [k for k in STACK if any(r[k] > 0 for r in p["rows"])]
    legend = "".join(f'<span><i class="f-{k}"></i>{e(labels[k])}</span>' for k in used)
    tile_html = "".join(f'<div class="stat"><div class="label">{e(a)}</div><div class="value">{e(b)}</div><div class="note">{e(c)}</div></div>'
                        for a, b, c in tiles)
    renamed = ""
    if earlier:
        renamed = ('<p class="sub">Also listed as: ' + "; ".join(f"<q>{e(n)}</q>" for n in earlier) + ".</p>")
    return (head(f'{p["id"]} · UVA Capital Plan Tracker', desc, url, 2)
            + f"""<main class="wrap">
<nav class="crumbs" aria-label="Breadcrumb"><a href="../">All projects</a> › {e(p["division"])}</nav>
<h1>{e(p["id"])}</h1>
<p class="meta">{e(p["division"])} · latest status: {e(p["status"])}</p>
{renamed}
<div class="tiles">{tile_html}</div>
<section class="card">
  <h2>Budget by funding source</h2>
  <p>{e(story(p, real_year))}</p>
  <div class="legend">{legend}</div>
  {charts(p, years, labels)}
</section>
<section class="card">
  <h2>Year by year</h2>
  <p class="sub">Amounts in millions of dollars, as printed in each plan.</p>
  <div class="tablewrap"><table><thead><tr>{thead}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
</section>
<p class="actions"><a class="btn" href="../../#project={p["slug"]}">Open in the interactive tracker</a>
  <a class="btn ghost" href="../">See all {len(data["projects"])} projects</a></p>
</main>
""" + foot(data["source"]))


def index_page(data):
    groups = {}
    for p in data["projects"]:
        groups.setdefault(p["division"], []).append(p)
    parts = []
    for div in sorted(groups, key=lambda k: (-len(groups[k]), k)):
        trs = []
        for p in sorted(groups[div], key=lambda p: p["id"].lower()):
            d = p["drift"]
            change = pct(d["pct"]) if d else "—"
            trs.append(f'<tr><td><a href="{p["slug"]}/">{e(p["id"])}</a></td><td>{e(p["status"])}</td>'
                       f'<td class="num">{money(p["latest_total"])}</td><td class="num">{change}</td></tr>')
        parts.append(f"""<section class="card">
  <h2>{e(div)} <span class="count">{len(groups[div])}</span></h2>
  <div class="tablewrap"><table><thead><tr><th>Project</th><th>Latest status</th><th class="num">Latest budget</th><th class="num">Change, as published</th></tr></thead>
  <tbody>{"".join(trs)}</tbody></table></div>
</section>""")
    n = len(data["projects"])
    desc = (f"All {n} projects in the University of Virginia's Major Capital Plans, 2021-2026, each with its budget "
            "and funding year by year.")
    return (head(f"All {n} projects · UVA Capital Plan Tracker", desc, f"{SITE_URL}projects/", 1, "website")
            + f"""<main class="wrap">
<h1>All {n} projects</h1>
<p class="lede">Every project in UVA's Major Capital Plans from 2021 through 2026, followed across its renames. Each
page shows the project's budget and funding in every plan. <a href="../#projects">Search and sort them in the
tracker</a>.</p>
{"".join(parts)}
</main>
""" + foot(data["source"]))


def redirect_page(target):
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Moved</title>
<link rel="canonical" href="{SITE_URL}projects/{target}/">
<meta http-equiv="refresh" content="0; url=../{target}/"></head>
<body><p>This project was renamed. <a href="../{target}/">Go to its page</a>.</p></body></html>
"""


def sitemap(data):
    urls = [SITE_URL, SITE_URL + "projects/"] + [f'{SITE_URL}projects/{p["slug"]}/' for p in data["projects"]]
    body = "".join(f"  <url><loc>{xml_escape(u)}</loc></url>\n" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n'


def write_all(site_dir, data, real_year, versions):
    """Write site/projects/ (replacing it) and site/sitemap.xml. `versions` fills the asset hashes."""
    out = os.path.join(site_dir, "projects")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    def put(rel, text):
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace("{theme}", versions["theme.js"]).replace("{css}", versions["pages.css"]))

    for p in data["projects"]:
        put(os.path.join(p["slug"], "index.html"), project_page(p, data, real_year))
    for old, new in REDIRECTS.items():
        put(os.path.join(old, "index.html"), redirect_page(new))
    put("index.html", index_page(data))
    with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(sitemap(data))  # robots.txt only counts at the domain root, so submit this one directly
    return len(data["projects"])
