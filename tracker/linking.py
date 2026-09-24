"""Link each capital-plan project across the six plans, and measure how its budget drifts.

Project names are not stable across years (PDF spacing damage, "(planning/design)" suffixes, renames such as
"UVA Hotel & Conference Center" -> "Virginia Guesthouse"), so projects are linked in three passes:
  1. an exact match on a normalized key (lowercase, "&" -> "and", parentheticals and punctuation dropped);
  2. difflib fuzzy matching on that key, ratio >= FUZZY and only between groups that never share a year
     (two names in the same plan are two projects, whatever their spelling);
  3. data/project_overrides.csv, hand-checked against the source: renames (confirmed or probable) and names that
     must never be fuzzy-linked (not-linked).

Planning-only authorizations (a name marked "(planning...)") are a different thing from a project budget, so drift
is measured only between full-budget years. Links marked "probable" are shown but kept out of aggregate numbers.
"""
import csv
import difflib
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "data", "capital_plans.csv")
OVERRIDES = os.path.join(ROOT, "data", "project_overrides.csv")
TRACKS = os.path.join(ROOT, "data", "project_tracks.csv")

FUND = ["state_gf", "gifts", "debt", "other_funds"]
FUND_LABELS = {"state_gf": "State GF", "gifts": "Gifts", "debt": "Debt", "other_funds": "Institutional/Cash"}
FUZZY = 0.85


def clean(name):
    name = name.replace("<br>", " ").replace("Mc Intire", "McIntire")  # extract.py's space re-insertion split it
    return re.sub(r"\s+", " ", name).strip()


def key(name):
    n = clean(name).lower().replace("&", " and ")
    n = re.sub(r"\([^)]*\)?", "", n)  # parentheticals, including ones the PDF cut off before the ")"
    return re.sub(r"[^a-z0-9]", "", n)


def is_planning(name):
    return bool(re.search(r"\(\s*planning", name, re.I))


def num(v):
    return float(v) if v else 0.0


def load_rows():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for r in rows:
        r["year"] = int(r["year"])
        r["name"] = clean(r["project"])
        for c in ["total"] + FUND:
            r[c] = num(r[c])
    return rows


def load_overrides():
    return {clean(r["name"]): r for r in csv.DictReader(open(OVERRIDES, encoding="utf-8"))}


class Groups:
    """Union-find over project names."""

    def __init__(self, names):
        self.parent = {n: n for n in names}

    def find(self, n):
        while self.parent[n] != n:
            self.parent[n] = self.parent[self.parent[n]]
            n = self.parent[n]
        return n

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)

    def members(self):
        out = defaultdict(set)
        for n in self.parent:
            out[self.find(n)].add(n)
        return out


def link(rows, overrides):
    years_of = defaultdict(set)
    for r in rows:
        years_of[r["name"]].add(r["year"])
    names = sorted(years_of)
    g = Groups(names)
    how = {}  # name -> how it got linked

    by_key = defaultdict(list)
    for n in names:
        by_key[key(n)].append(n)
    for ns in by_key.values():
        for n in ns[1:]:
            g.union(n, ns[0])
            how[n] = how[ns[0]] = "exact-key"

    for n, o in overrides.items():
        if n not in years_of:
            continue
        if o["canonical"]:
            canon = clean(o["canonical"])
            assert canon in years_of, f"override canonical not in data: {canon}"
            g.union(n, canon)
            how[n] = "override-" + o["confidence"]

    # fuzzy pass: best pairs first, never across a shared year, never touching a hand-assigned name
    hand = set(overrides)
    fuzzy_links = []
    while True:
        groups = g.members()
        gyears = {root: set().union(*(years_of[m] for m in ms)) for root, ms in groups.items()}
        best = None
        roots = sorted(groups)
        for i, a in enumerate(roots):
            if groups[a] & hand:
                continue
            for b in roots[i + 1:]:
                if groups[b] & hand or gyears[a] & gyears[b]:
                    continue
                ratio = max(difflib.SequenceMatcher(None, key(x), key(y)).ratio()
                            for x in groups[a] for y in groups[b])
                if ratio >= FUZZY and (best is None or ratio > best[0]):
                    best = (ratio, a, b)
        if best is None:
            break
        ratio, a, b = best
        fuzzy_links.append((ratio, sorted(groups[a]), sorted(groups[b])))
        for m in groups[a] | groups[b]:
            how.setdefault(m, "fuzzy")
        g.union(a, b)

    groups = g.members()
    pid_of, conf_of = {}, {}
    for ms in groups.values():
        latest = max(ms, key=lambda m: (max(years_of[m]), m))
        pid = re.sub(r"\s*\((planning|includes|project includes)[^)]*\)?", "", latest).strip()
        pid = re.sub(r"(\S)\(", r"\1 (", pid)
        probable = any(overrides.get(m, {}).get("confidence") == "probable" for m in ms)
        for m in ms:
            pid_of[m] = pid
            conf_of[pid] = "probable" if probable else "confirmed"
    for r in rows:
        r["project_id"] = pid_of[r["name"]]
        r["phase"] = "planning" if is_planning(r["name"]) else "full"
        r["link"] = how.get(r["name"], "single-name")
    return fuzzy_links, conf_of


def tracks_by_project(rows):
    out = defaultdict(list)
    for r in rows:
        out[r["project_id"]].append(r)
    for pid, rs in out.items():
        rs.sort(key=lambda r: r["year"])
        ys = [r["year"] for r in rs]
        assert len(ys) == len(set(ys)), f"two rows for one project in one year: {pid} {ys}"
    return out


def drift_table(tracks, conf_of):
    """One record per project with >= 2 full-budget years."""
    out = []
    for pid, rs in tracks.items():
        full = [r for r in rs if r["phase"] == "full"]
        if len(full) < 2:
            continue
        first, last = full[0], full[-1]
        revisions = [(a, b) for a, b in zip(full, full[1:]) if abs(b["total"] - a["total"]) > 0.005]
        out.append({
            "pid": pid, "division": last["division"], "conf": conf_of[pid],
            "first_year": first["year"], "last_year": last["year"], "n_years": len(full),
            "first": first["total"], "last": last["total"], "delta": last["total"] - first["total"],
            "pct": (last["total"] - first["total"]) / first["total"] * 100,
            "revisions": revisions, "peak": max(r["total"] for r in full),
            "fund_delta": {c: last[c] - first[c] for c in FUND},
            "mix_changed": any(abs(last[c] - first[c]) > 0.005 for c in FUND),
        })
    return sorted(out, key=lambda d: -d["pct"])


def write_tracks(rows):
    cols = ["project_id", "year", "phase", "link", "division", "status", "project", "total"] + FUND
    with open(TRACKS, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in sorted(rows, key=lambda r: (r["project_id"], r["year"])):
            w.writerow([r[c] if c not in ["total"] + FUND else (f"{r[c]:g}" if r[c] else "") for c in cols])
