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
- **After construction-cost inflation, most budgets shrank.** In 2026 dollars (BLS construction price indexes),
  the same 64 budgets fell 7.5% together, and 52 of them lost buying power. The 40 that never changed lost a median
  13.5%. Budgets often build in escalation, and a national index isn't UVA's own costs, so read this as a rough
  measure.
- **A 16.6% overrun is expensive.** On the course's example project, an overrun the size of that median cuts the
  NPV from $5.04M to $2.28M.
- **Against UVA's own history, the example usually survives.** Run through all 64 observed budget changes, the
  course example still clears its 3% discount rate in 58 of them. It breaks even at a +30.3% overrun, which 6 of
  the 64 exceeded.

## What's on the site

- **Overview:** the plan total and funding mix by year, in dollars or shares, with a table view.
- **Projects:** all 94 projects, searchable by any name they've had, filterable, with each project's budget and
  funding year by year and how each year's entry was linked to the others. A switch shows every figure as
  published or in 2026 dollars.
- **Feasibility:** a cash-flow model with sliders (discount rate, revenue and cost growth, first-year revenue,
  cost overrun, construction delay) on two example projects. The first is from UVA's CE 3010 course, used with
  attribution; the second is made up. Below the sliders, each example is replayed through every tracked
  project's real budget change: how often it still clears its discount rate, the break-even overrun, and a chart
  with one dot per project that links to that project.
- **Method:** sources, parsing, linking and limits.
- **A page for every project** ([`/projects/`](https://willmcnulty.github.io/UVA-Capital-Plan-Tracker/projects/)):
  budget and funding year by year, earlier names, and the change as published and in 2026 dollars. The pages are
  plain HTML (no JavaScript needed), so they can be shared and searched; each links into the tracker at
  `#project=<slug>`, and any project opened in the tracker gets that address too.

## How it works

```
data/capital_plans.csv  ->  tracker/linking.py  ->  build.py  ->  site/data.js  ->  site/ (static page)
data/project_overrides.csv      tracker/model.py + examples.py  ->  (feasibility cases)
data/construction_ppi.csv  ->  tracker/inflation.py  ->  (2026-dollar figures)
                                tracker/pages.py  ->  site/projects/<slug>/ + site/sitemap.xml
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
  within $5 of the slide), every data row reconciles to its funding sources, the linking gives 94 projects, and the construction indexes
  cover every plan year with the expected deflators.
- `tests/parity.js`: the JavaScript model matches the Python model on 26 cases (both examples, every slider driver
  at a low and a high setting, a 30% overrun, a 3-year delay) and on all 128 replayed outcomes and both break-even
  overruns, to within a millionth of a dollar.
- CI also fails if the committed `site/data.js`, project pages or sitemap aren't what a fresh build produces. The build stamps each script
  tag with a content hash, so a browser can't mix an old copy of one file with a new copy of another.

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
