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


if __name__ == "__main__":
    unittest.main()
