# Data sources

`capital_plans.csv` holds every project row from six years of the University of Virginia's Major Capital Plan, the
Board of Visitors-approved list of authorized capital projects with each project's total budget and funding split
(State General Fund, gifts, debt, institutional/cash). All six are public documents.

| Plan year | Document | Public copy |
|---|---|---|
| 2021 | 2021 Major Capital Plan | Proposed plan, pages 14-16 of the Buildings and Grounds Committee book, June 4, 2021: https://bov.virginia.edu/sites/bov/files/2023-01/%252721%2520JUN%2520B%2526G%2520BOOK_0.pdf |
| 2022 | 2022 Major Capital Plan, pages 12-18 of the Buildings and Grounds Committee book, June 2-3, 2022 Board meeting | https://bov.virginia.edu/sites/bov/files/2023-01/B%26G%20Book.pdf |
| 2023 | 2023 Major Capital Plan | Proposed plan, pages 14-16 of the B&G book, June 2, 2023: https://bov.virginia.edu/sites/bov/files/2023-10/%252723%2520JUN%25202%2520B%2526G%2520BOOK.pdf |
| 2024 | 2024 Major Capital Plan | Proposed plan, pages 11-13 of the B&G book, June 7, 2024: https://bov.virginia.edu/sites/bov/files/2024-06/B%26G%20Committee%20Book%20June%202024_0.pdf |
| 2025 | 2025 Major Capital Plan | Proposed plan, pages 13-15 of the B&G book, June 5, 2025: https://bov.virginia.edu/sites/bov/files/2025-06/5%20-%20%2725%20JUN%205%20B%26G%20BOOK.pdf |
| 2026 | FY2027 Major Capital Plan, approved June and September 2026 | https://svpo.virginia.edu/sites/svpo/files/2026-09/capitalplan_0.pdf (the "Current Plan" on https://svpo.virginia.edu/capital; fetched 2026-09-23) |

### How the 2021 and 2023-2025 rows compare with the public copies

The rows for 2021 and 2023-2025 were parsed from copies of each year's plan distributed in a UVA course (CE 3010,
Fall 2025). Checked on 2026-10-13 against the public June Board books linked above (2024 and 2025 read by OCR,
since their tables are images): of 191 rows, 184 match a public row by name and 176 of those have the same total.
The course copies are later revisions of the same year's plan, so they differ in three ways:

- **8 totals differ:** 2021 School of Data Science $53.5M here vs $48.0M in June, UVA Hotel & Conference Center
  $133.5M vs $130.5M, Darden Hall Renovation (College at Wise) $31.22M vs $24.7M; 2023 North Grounds Parking Garage
  $50M vs $54M, Replacement of the Chemistry Addition Chillers $10M vs $20M, Fontaine Research Park Central Energy
  Plant $70M vs $65M; 2024 Karsh Institute of Democracy $82M vs $80M; 2025 Low Temperature Hot Water Conversion
  $38.49M vs $38.4M.
- **Later names:** e.g. the June 2021 book says "Democracy Institute" and "Contemplative Sciences Center" where this
  table has "Karsh Institute of Democracy" and "Contemplative Commons".
- **Finished projects dropped:** the June 2021 table still lists Ivy Mountain Musculoskeletal Center ($174.7M),
  University Hospital Expansion ($391.6M), Student Health and Wellness Center ($100M) and three smaller projects,
  and the June 2024 table still lists Physics Building Renewal ($62.51M), Physics Building Classrooms ($7M) and the
  Scott Stadium scoreboard ($13.4M). So the 2021 and 2024 totals here are lower than the June-approved plans,
  mostly because completed projects had already been taken off.

The site keeps the course revisions, because they are consistent with the 2022 and 2026 documents and every row
reconciles, but anyone checking a number against the June books should expect these differences.

## How the table was made

Each plan PDF was converted to markdown and parsed into one row per project per year. The six documents use at
least three different table layouts, so the parser classifies divisions, statuses and money cells by keyword
rather than position. Two checks hold for every row:

- **Every row reconciles:** its stated total equals the sum of its funding-source columns (tested in
  `tests/test_model.py`).
- **Every year reconciles:** each year's rows add up to the plan's own stated totals.

Rows with no budget assigned (e.g. marked "TBD" in the source) are left out. `project_raw` keeps each name exactly as
extracted, next to the cleaned `project` name, so a bad split stays visible.

The parser itself lives in the author's private coursework repository, because four of the six source files came
through a course site (UVA CE 3010, Capital Projects, Fall 2025). Public versions of all six years are now linked
above, but for four of them the parsed files are the course's later revisions, not the linked June books (see
above), so the parser stays private for now; moving it here would mean re-parsing from the public versions.

## Other files

- `project_overrides.csv`: hand-checked links between project names across years (renames, confirmed or probable)
  and names that must never be linked, each with the reason. Used by `tracker/linking.py`. Three links that were
  probable became confirmed on 2026-10-13 from the Board books (2022's "Parking Garage" is the North Grounds
  Parking Garage; the Research Data Center and The Park Renovation continue the 2023 and 2024 planning
  authorizations); the note on each row cites the page.
- `construction_ppi.csv`: monthly values of two Bureau of Labor Statistics producer price indexes, used to show
  budgets in 2026 dollars: **PCU236222236222, New school building construction** (Academic Division and College
  at Wise) and **PCU236224236224, New health care building construction** (UVA Health System). Each plan year is
  deflated with that year's June value, when the Board approves the plan. Fetched from the BLS public API
  (https://api.bls.gov/publicAPI/v1/timeseries/data/) on 2026-10-06; refresh with
  `python -m tracker.inflation --refresh`.
- `project_locations.csv`: where each project is, for the map. The plans don't give locations, so each project was
  matched by hand to an [OpenStreetMap](https://www.openstreetmap.org/) feature (data © OpenStreetMap contributors,
  available under the ODbL), found with the Overpass API on 2026-10-06. `basis` is `building` (the project is that
  building, or its renovation or addition), `site` (placed at a named site, such as Fontaine Research Park or the
  Darden School's grounds) or `unmapped`, with the reason in `note`. Name matches were never accepted blindly: two
  College at Wise projects share names with Charlottesville buildings (Zehmer Hall, Darden Hall), and renamed
  buildings (Alderman Library, now Shannon Library) were matched by their current names.
- `project_tracks.csv`: generated by `build.py`. Every row with the stable project it belongs to and how that link
  was made.
