"""Construction-cost inflation, to show budgets in real (inflation-adjusted) dollars.

Indexes: the Bureau of Labor Statistics producer price indexes for new building construction, matched to the kind
of building each division mostly builds:
  - PCU236222236222  New school building construction       (Academic Division, College at Wise)
  - PCU236224236224  New health care building construction  (UVA Health System)
Each plan is approved by the Board of Visitors around June, so a plan year's budgets are deflated with that year's
June index value. Real figures are in June-of-the-latest-plan-year dollars ("2026 dollars").

The index values live in data/construction_ppi.csv (committed, so builds are reproducible). Refresh them with
    python -m tracker.inflation --refresh
which calls the BLS public API (v1, no key; limited to 25 requests a day).
"""
import argparse
import csv
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "construction_ppi.csv")
SERIES = {
    "school": ("PCU236222236222", "New school building construction"),
    "health": ("PCU236224236224", "New health care building construction"),
}
DIVISION_SERIES = {"UVA Health System": "health"}  # everything else: school
MONTH = "M06"  # June, when the Board approves each plan


def series_for(division):
    return DIVISION_SERIES.get(division, "school")


def load():
    """{series key: {year: June index value}}"""
    out = {k: {} for k in SERIES}
    by_id = {sid: k for k, (sid, _) in SERIES.items()}
    with open(CSV_PATH, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["period"] == MONTH and r["series_id"] in by_id:
                out[by_id[r["series_id"]]][int(r["year"])] = float(r["value"])
    return out


class Deflator:
    def __init__(self, base_year, index=None):
        self.index = index or load()
        self.base_year = base_year
        for k, vals in self.index.items():
            if base_year not in vals:
                raise SystemExit(f"construction index {k} has no June {base_year} value; run the refresh")

    def factor(self, division, year):
        """Multiply a `year` budget by this to express it in base-year dollars."""
        vals = self.index[series_for(division)]
        if year not in vals:
            raise SystemExit(f"construction index {series_for(division)} has no June {year} value")
        return vals[self.base_year] / vals[year]

    def real(self, value, division, year):
        return value * self.factor(division, year)


def refresh(end_year=None):
    import datetime as dt
    end_year = end_year or dt.date.today().year
    start_year = end_year - 9  # the keyless API returns at most 10 years per request
    body = json.dumps({"seriesid": [sid for sid, _ in SERIES.values()],
                       "startyear": str(start_year), "endyear": str(end_year)}).encode()
    req = urllib.request.Request("https://api.bls.gov/publicAPI/v1/timeseries/data/", data=body,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "UVA-Capital-Plan-Tracker/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    if d.get("status") != "REQUEST_SUCCEEDED":
        raise SystemExit(f"BLS API: {d.get('status')} {d.get('message')}")
    rows = []
    for s in d["Results"]["series"]:
        for x in s["data"]:
            if x["period"].startswith("M") and x["period"] != "M13":
                rows.append((s["seriesID"], int(x["year"]), x["period"], x["value"]))
    rows.sort()
    with open(CSV_PATH, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["series_id", "year", "period", "value"])
        w.writerows(rows)
    print(f"wrote {len(rows)} monthly values to {os.path.relpath(CSV_PATH, ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    if ap.parse_args().refresh:
        refresh()
