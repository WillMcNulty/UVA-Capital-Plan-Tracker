"""Build the site's data file from the dataset.

Links every project across the six plans (tracker/linking.py), writes data/project_tracks.csv, and writes
site/data.js (`window.DATA = {...}`, a script rather than JSON so the page also works opened straight from disk).

Before writing, it checks the totals against the published findings (yearly totals, funding shares, drift counts),
so a change to the data or the linking can't silently change the numbers the site reports. It also stores the
Python model's NPV, IRR and cash flows for a set of feasibility cases; tests/parity.js runs the page's JavaScript
port on the same cases and fails if they differ.

Usage: python build.py   (standard library only)
"""
import json
import os
import statistics
from collections import defaultdict
from dataclasses import asdict

from tracker import examples as ex
from tracker import linking as lk
from tracker import model as md

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "site", "data.js")
FUND = lk.FUND

EXAMPLE_NOTES = {
    "course": {
        "label": "Course example",
        "title": "The debt-financed example from UVA's CE 3010 course (lecture S19)",
        "note": "A teaching case from CE 3010 (Capital Projects), University of Virginia, Fall 2025, reproduced from "
                "the lecture slide's printed values: equity in years 0-1, a 20-year loan drawn in year 2, "
                "construction in years 2-3, then 20 years of operations. Used with attribution; not a real UVA project.",
    },
    "hall": {
        "label": "Made-up example",
        "title": "A made-up 400-bed residence hall",
        "note": "Written for this site; not a real project. $56M of construction over two years, $11M of equity and a "
                "$45.9M 25-year loan at 4.5% drawn during construction, then 30 years of operations: $5.6M of "
                "first-year rent against $1.9M of operating cost, so first-year debt-service coverage is about 1.20.",
    },
}


def projects_and_years():
    rows = lk.load_rows()
    _, conf_of = lk.link(rows, lk.load_overrides())
    tracks = lk.tracks_by_project(rows)
    lk.write_tracks(rows)
    drift = {d["pid"]: d for d in lk.drift_table(tracks, conf_of)}

    years = sorted({r["year"] for r in rows})
    funding = {y: {c: 0.0 for c in FUND} for y in years}
    division = {y: defaultdict(float) for y in years}
    for r in rows:
        for c in FUND:
            funding[r["year"]][c] += r[c]
        division[r["year"]][r["division"]] += r["total"]

    projects = []
    for pid, rs in sorted(tracks.items()):
        last = rs[-1]
        d = drift.get(pid)
        projects.append({
            "id": pid,
            "division": last["division"],
            "status": last["status"],
            "conf": conf_of[pid],
            "years": [r["year"] for r in rs],
            "latest_total": round(last["total"], 3),
            "rows": [{"year": r["year"], "phase": r["phase"], "link": r["link"], "status": r["status"],
                      "name": r["name"], "total": round(r["total"], 3),
                      **{c: round(r[c], 3) for c in FUND}} for r in rs],
            "drift": None if d is None else {
                "first_year": d["first_year"], "last_year": d["last_year"], "n_years": d["n_years"],
                "first": round(d["first"], 3), "last": round(d["last"], 3), "delta": round(d["delta"], 3),
                "pct": round(d["pct"], 2), "revisions": len(d["revisions"]), "peak": round(d["peak"], 3)},
        })
    return rows, years, funding, division, projects, list(drift.values())


def drift_summary(drift):
    """Confirmed links only."""
    conf = [d for d in drift if d["conf"] == "confirmed"]
    up = [d for d in conf if d["delta"] > 0.005]
    down = [d for d in conf if d["delta"] < -0.005]
    first, last = sum(d["first"] for d in conf), sum(d["last"] for d in conf)
    return {"tracked": len(conf), "increased": len(up), "decreased": len(down),
            "unchanged": len(conf) - len(up) - len(down),
            "first_sum": round(first, 1), "last_sum": round(last, 1),
            "net_pct": round((last - first) / first * 100, 1),
            "median_increase_pct": round(statistics.median(d["pct"] for d in up), 1)}


def check(years, funding, projects, summary):
    """The published findings; stop if the site would disagree with them."""
    total = {y: sum(funding[y].values()) for y in years}
    expect_total = {2021: 2247, 2022: 2839, 2024: 1976, 2026: 1988}
    for y, v in expect_total.items():
        assert abs(total[y] - v) < 1, f"{y} total {total[y]:.1f} vs expected {v}"
    share = lambda y, c: funding[y][c] / total[y] * 100
    assert round(share(2021, "state_gf")) == 26 and round(share(2021, "debt")) == 40, "2021 funding shares"
    assert 9 <= round(share(2026, "state_gf")) <= 11, "2026 State GF share"
    assert len(projects) == 94, f"{len(projects)} projects, expected 94"
    assert (summary["tracked"], summary["increased"], summary["unchanged"], summary["decreased"]) == (64, 23, 40, 1), summary
    assert summary["net_pct"] == 9.3 and round(summary["median_increase_pct"]) == 17, summary
    return total


def case_json(c):
    d = asdict(c)
    for k in ("equity", "expenses", "loan"):
        d[k] = {str(y): v for y, v in d[k].items()}
    return d


def feasibility_block():
    out = {"examples": {}, "checks": []}
    for key, make in ex.EXAMPLES.items():
        base = make()
        out["examples"][key] = {**EXAMPLE_NOTES[key], "case": case_json(base)}
        cases = [("base", base)]
        for label, lo, hi in md.drivers(base):
            cases += [(label + " (low)", lo), (label + " (high)", hi)]
        cases += [("overrun +30%", md.overrun(base, 0.30)), ("delay 3 years", md.delayed(base, 3))]
        for label, c in cases:
            n, i = md.summarize(c)
            out["checks"].append({"label": f"{key}: {label}", "case": case_json(c), "npv": n, "irr": i,
                                  "ncf": md.cash_flows(c)["ncf"]})
    return out


def main():
    rows, years, funding, division, projects, drift = projects_and_years()
    summary = drift_summary(drift)
    total = check(years, funding, projects, summary)
    data = {
        "source": "UVA Major Capital Plans 2021-2026 (public Board of Visitors documents)",
        "years": years,
        "fund_keys": FUND,
        "fund_labels": lk.FUND_LABELS,
        "funding": {str(y): {c: round(v, 2) for c, v in funding[y].items()} for y in years},
        "totals": {str(y): round(total[y], 2) for y in years},
        "division": {str(y): {k: round(v, 2) for k, v in division[y].items()} for y in years},
        "drift_summary": summary,
        "projects": projects,
        "feasibility": feasibility_block(),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("// Generated by build.py from data/; do not edit by hand.\n")
        f.write("window.DATA = " + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"{len(rows)} rows, {len(projects)} projects, {len(years)} years -> {os.path.relpath(OUT, HERE)} "
          f"({os.path.getsize(OUT) / 1024:.0f} KB)")
    print("drift (confirmed links):", summary)


if __name__ == "__main__":
    main()
