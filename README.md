# UVA Capital Plan Tracker

**Live site: https://willmcnulty.github.io/UVA-Capital-Plan-Tracker/**

An independent look at six years (2021-2026) of the University of Virginia's public Major Capital Plans: where
the money comes from, how individual project budgets change from one plan to the next, and what moves a
project's financial feasibility. Not affiliated with or endorsed by the University.

## What it found

- **The funding mix moved from state money to debt.** The State General Fund's share of the plan fell from 26%
  (2021) to 9-11% (2024-2026). Debt rose from 40% to a 58% peak (2025), and institutional/cash funding from 12% to
  24-29%.
- **Budgets that move mostly go up.** Of 64 projects with two or more full budgets, 23 increased, 40 stayed flat
  and 1 fell. Together their budgets rose 9.3%, and the median increase was 16.6%. Most revisions came before
  construction started, and the increases were paid with debt while gifts fell away.
- **A 16.6% overrun is expensive.** On the course's example project, an overrun the size of that median cuts the
  NPV from $5.04M to $2.28M.

## What's on the site

- **Overview:** the plan total and funding mix by year, in dollars or shares, with a table view.
- **Projects:** all 94 projects, searchable by any name they've had, filterable, with each project's budget and
  funding year by year and how each year's entry was linked to the others.
- **Feasibility:** a cash-flow model with sliders (discount rate, revenue and cost growth, first-year revenue,
  cost overrun, construction delay) on two example projects. The first is from UVA's CE 3010 course, used with
  attribution; the second is made up.
- **Method:** sources, parsing, linking and limits.

## How it works

```
data/capital_plans.csv  ->  tracker/linking.py  ->  build.py  ->  site/data.js  ->  site/ (static page)
data/project_overrides.csv      tracker/model.py + examples.py  ->  (feasibility cases)
```

- **Linking projects across years** (`tracker/linking.py`). Project names drift between plans: PDF spacing damage,
  added donor names, outright renames like "UVA Hotel & Conference Center" -> "Virginia Guesthouse". Three passes:
  an exact match on a normalized name; a fuzzy match (difflib ratio >= 0.85) allowed only between names that never
  appear in the same plan, since two names in one plan are two projects; and hand-checked overrides with a reason
  for each. 286 rows become 94 projects. Links the plans don't prove are marked "probable" and kept out of every
  total.
- **The feasibility model** (`tracker/model.py`) follows the CE 3010 course template: yearly equity, loan
  proceeds, project expenses, revenue, operating cost, debt service and net cash flow, with Excel-convention NPV
  and IRR. `site/finance.js` is a line-for-line JavaScript port so the sliders can recompute in the browser.
- **The page** is plain HTML, CSS and JavaScript: no framework, no libraries, no network requests, and light and
  dark themes. Charts are hand-built SVG with hover and keyboard tooltips and a table view for each.
- **The design** matches [willmcnulty.github.io](https://willmcnulty.github.io/): UVA Blue and Orange, system fonts.
  Chart colors come from UVA's brand palette (Link Blue, Orange, Cyan, Green), stacked in an order where every pair
  of neighbors passes colorblind-separation checks, with darker steps of the same hues for dark mode. There are no
  UVA logos or marks; the site is independent.

## How it's checked

On every push, GitHub Actions rebuilds the data, runs the tests, and only then deploys:

- `build.py` refuses to write the site if the totals stop matching the findings above (yearly totals, funding
  shares, project and drift counts).
- `tests/test_model.py`: the model reproduces the course example's printed values (cash flows to the dollar, NPV
  within $5 of the slide), every data row reconciles to its funding sources, and the linking gives 94 projects.
- `tests/parity.js`: the JavaScript model matches the Python model on 26 cases (both examples, every slider driver
  at a low and a high setting, a 30% overrun, a 3-year delay), to within a millionth of a dollar.
- CI also fails if the committed `site/data.js` isn't what a fresh build produces.

## Run it locally

Python 3.10+ (standard library only) and Node 18+ for the parity test.

```bash
python build.py
python -m unittest discover tests
node tests/parity.js
python -m http.server 8000 --directory site
```

Then open http://localhost:8000. Opening `site/index.html` directly also works.

## Limits

Six plans is a short series. A capital plan authorizes budgets; it doesn't report what was spent, so a budget
increase isn't the same as a final cost overrun. Projects that never changed were also watched for fewer years on
average. Neither feasibility example is a real UVA project. See [`data/sources.md`](data/sources.md) for where every
number comes from.
