"""The model reproduces the CE 3010 lecture S19 example, and the linking reproduces the published counts.

Usage: python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tracker import examples, linking, model  # noqa: E402


class CourseExample(unittest.TestCase):
    """Printed values on the lecture slide, years 0-5 (net cash flow is rounded to the dollar there)."""

    def setUp(self):
        self.case = examples.course_example()
        self.rows = model.cash_flows(self.case)

    def test_debt_service_matches_slide(self):
        self.assertAlmostEqual(model.pmt(self.case.loan_rate, 20, 14678140.88), 1116309.29, places=2)

    def test_printed_cells(self):
        printed = {"ncf": [-1764200, -1764200, 4599698, -10078443, 428941, 475299],
                   "noi": [0, 0, 0, 0, 1545250.67, 1591608.19],
                   "net_income": [0, 0, -1116309.29, -1116309.29, 428941.39, 475298.91]}
        for row, values in printed.items():
            for year, v in enumerate(values):
                self.assertLess(abs(self.rows[row][year] - v), 1.0, f"{row} year {year}")

    def test_npv_and_irr(self):
        n, i = model.summarize(self.case)
        # the slide's own inputs are rounded to the cent, so allow $5 (about 1 part per million)
        self.assertLess(abs(n - 5043813.04), 5.0)
        self.assertEqual(round(i, 2), 0.07)


class MadeUpExample(unittest.TestCase):
    def test_debt_service_coverage_about_1_2(self):
        c = examples.residence_hall()
        ds = model.pmt(c.loan_rate, c.loan_term, sum(c.loan.values()))
        self.assertAlmostEqual((c.egi0 - c.om0) / ds, 1.20, places=2)

    def test_funding_covers_cost_plus_issuance(self):
        c = examples.residence_hall()
        cost = sum(c.expenses.values())
        self.assertAlmostEqual(sum(c.equity.values()) + sum(c.loan.values()), cost + 0.02 * 45e6, places=2)


class Replay(unittest.TestCase):
    def test_no_change_is_the_base_npv(self):
        c = examples.course_example()
        self.assertAlmostEqual(model.replay(c, [0.0])[0], model.summarize(c)[0], places=6)

    def test_breakeven_overrun_zeroes_npv(self):
        for make in examples.EXAMPLES.values():
            c = make()
            b = model.breakeven_overrun(c)
            self.assertIsNotNone(b)
            self.assertLess(abs(model.summarize(model.overrun(c, b))[0]), 1e-3)

    def test_course_example_breaks_even_near_30_percent(self):
        self.assertAlmostEqual(model.breakeven_overrun(examples.course_example()), 0.303, places=3)


class Linking(unittest.TestCase):
    def test_published_counts(self):
        rows = linking.load_rows()
        _, conf = linking.link(rows, linking.load_overrides())
        tracks = linking.tracks_by_project(rows)
        drift = [d for d in linking.drift_table(tracks, conf) if d["conf"] == "confirmed"]
        self.assertEqual(len(rows), 286)
        self.assertEqual(len(tracks), 94)
        self.assertEqual(len(drift), 64)
        self.assertEqual(sum(d["delta"] > 0.005 for d in drift), 23)

    def test_every_row_reconciles(self):
        for r in linking.load_rows():
            parts = sum(r[c] for c in linking.FUND)
            self.assertLess(abs(parts - r["total"]), 0.01, f"{r['year']} {r['name']}")


class Inflation(unittest.TestCase):
    def setUp(self):
        from tracker import inflation
        self.inflation = inflation
        self.D = inflation.Deflator(2026)

    def test_every_plan_year_has_both_june_values(self):
        idx = self.inflation.load()
        for key in ("school", "health"):
            for y in range(2021, 2027):
                self.assertIn(y, idx[key], f"{key} June {y}")

    def test_factors(self):
        self.assertEqual(self.D.factor("Academic Division", 2026), 1.0)
        self.assertAlmostEqual(self.D.factor("Academic Division", 2021), 237.482 / 176.9, places=6)
        self.assertAlmostEqual(self.D.factor("College at Wise", 2021), 237.482 / 176.9, places=6)
        self.assertAlmostEqual(self.D.factor("UVA Health System", 2021), 164.277 / 123.8, places=6)

    def test_flat_nominal_budget_loses_real_value(self):
        # a budget unchanged from 2021 to 2026 is worth less in 2026 dollars
        first = self.D.real(100, "Academic Division", 2021)
        last = self.D.real(100, "Academic Division", 2026)
        self.assertLess(last, first)


class Pages(unittest.TestCase):
    def test_slugs(self):
        from tracker import pages
        self.assertEqual(pages.slugify("Virginia Guesthouse (UVA Hotel & Conference Center)"),
                         "virginia-guesthouse-uva-hotel-and-conference-center")
        self.assertEqual(pages.slugify("Children's Hospital"), "childrens-hospital")
        ps = [{"id": "A b"}, {"id": "a-b"}]
        pages.assign_slugs(ps)
        self.assertEqual([p["slug"] for p in ps], ["a-b", "a-b-2"])

    def test_every_project_has_a_page(self):
        import json
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "site", "data.js"), encoding="utf-8") as f:
            src = f.read()
        projects = json.loads(src[src.index("=") + 1:].strip().rstrip(";"))["projects"]
        slugs = [p["slug"] for p in projects]
        self.assertEqual(len(slugs), len(set(slugs)))
        for s in slugs:
            self.assertTrue(os.path.isfile(os.path.join(root, "site", "projects", s, "index.html")), s)


class Locations(unittest.TestCase):
    def setUp(self):
        import csv
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "data", "project_locations.csv"), encoding="utf-8") as f:
            self.locs = list(csv.DictReader(f))
        self.rows = linking.load_rows()
        linking.link(self.rows, linking.load_overrides())  # sets each row's project_id

    def test_every_project_has_a_reviewed_row(self):
        self.assertEqual({r["project_id"] for r in self.locs}, set(linking.tracks_by_project(self.rows)))
        for r in self.locs:
            self.assertIn(r["basis"], ("building", "site", "unmapped"), r["project_id"])
            if r["basis"] == "unmapped":
                self.assertTrue(r["note"], f"{r['project_id']}: an unmapped project needs a reason")
            else:
                self.assertRegex(r["osm"], r"^(node|way|relation)/\d+$")
                self.assertTrue(37.9 < float(r["lat"]) < 38.2 and -78.7 < float(r["lon"]) < -78.3, r["project_id"])

    def test_college_at_wise_is_never_placed_in_charlottesville(self):
        basis = {r["project_id"]: r["basis"] for r in self.locs}
        wise = {r["project_id"] for r in self.rows if r["division"] == "College at Wise"}
        self.assertTrue(wise)
        for pid in wise:
            self.assertEqual(basis[pid], "unmapped", pid)


if __name__ == "__main__":
    unittest.main()
