"""A capital project's cash flows, NPV and IRR, following the CE 3010 (UVA) course's P7 feasibility template.

The template is one sheet of yearly rows:

    Equity (-), Loan Proceeds (+), Project Expenses (-), Effective Gross Income (+), Operating Expenses (-),
    NOI = EGI + OpEx, Debt Service (-), Net Income = NOI + Debt Service,
    Net Cash Flow = Equity + Loan Proceeds + Project Expenses + Net Income
    NPV = NPV(discount rate, years 1..N) + year 0        IRR = IRR(years 0..N)

`cash_flows` builds those rows from a `Case`; `npv` and `irr` follow Excel's conventions. site/finance.js is a line
for line JavaScript port, and tests/parity.js checks the two agree.
"""
from dataclasses import dataclass, field, replace

ROWS = ["equity", "loan", "expenses", "egi", "opex", "noi", "debt_service", "net_income", "ncf"]


@dataclass
class Case:
    name: str
    horizon: int                 # last year of the analysis (years 0..horizon)
    equity: dict                 # year -> equity injected, as a positive amount (it is an outflow)
    expenses: dict               # year -> project expense, positive
    op_start: int                # first operating year (first year of revenue and O&M)
    op_years: int                # operating lifespan in years
    egi0: float                  # effective gross income in the first operating year
    egi_growth: float
    om0: float                   # O&M cost in the first operating year
    om_growth: float
    discount: float
    loan: dict = field(default_factory=dict)  # year -> loan proceeds drawn (incl. cost of issuance)
    loan_rate: float = 0.0
    loan_term: int = 0
    debt_start: int = 0
    debt_service: float = None   # annual payment; None -> PMT(loan_rate, loan_term, total proceeds)


def pmt(rate, n, principal):
    return principal / n if rate == 0 else principal * rate / (1 - (1 + rate) ** -n)


def cash_flows(c):
    n = c.horizon + 1
    rows = {k: [0.0] * n for k in ROWS}
    for y, v in c.equity.items():
        rows["equity"][y] -= v
    for y, v in c.loan.items():
        rows["loan"][y] += v
    for y, v in c.expenses.items():
        rows["expenses"][y] -= v
    for i in range(c.op_years):
        y = c.op_start + i
        if y <= c.horizon:
            rows["egi"][y] = c.egi0 * (1 + c.egi_growth) ** i
            rows["opex"][y] = -c.om0 * (1 + c.om_growth) ** i
    ds = c.debt_service if c.debt_service is not None else (
        pmt(c.loan_rate, c.loan_term, sum(c.loan.values())) if c.loan else 0.0)
    for i in range(c.loan_term if c.loan else 0):
        y = c.debt_start + i
        if y <= c.horizon:
            rows["debt_service"][y] = -ds
    for y in range(n):
        rows["noi"][y] = rows["egi"][y] + rows["opex"][y]
        rows["net_income"][y] = rows["noi"][y] + rows["debt_service"][y]
        rows["ncf"][y] = rows["equity"][y] + rows["loan"][y] + rows["expenses"][y] + rows["net_income"][y]
    return rows


def npv(rate, flows):
    """Excel's convention as the template uses it: NPV(rate, years 1..N) + year 0."""
    return flows[0] + sum(v / (1 + rate) ** t for t, v in enumerate(flows) if t > 0)


def irr(flows, lo=-0.99, hi=1.0):
    """Bisection on NPV = 0. Returns None when there is no sign change in the bracket."""
    f_lo, f_hi = npv(lo, flows), npv(hi, flows)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid, flows)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2


def summarize(c):
    flows = cash_flows(c)["ncf"]
    return npv(c.discount, flows), irr(flows)


# ---- sensitivity helpers ------------------------------------------------------------------------------------

def delayed(c, d, escalation=0.03):
    """Construction runs d years long. The last year of project expenses moves d years later and is escalated at
    `escalation` a year; opening moves d years later; the operating lifespan stays the same, so the horizon grows by
    d. Equity, the loan draw and debt service keep their original dates: the debt was issued and must be paid."""
    if d == 0:
        return c
    last = max(c.expenses)
    exp = dict(c.expenses)
    exp[last + d] = exp.pop(last) * (1 + escalation) ** d
    return replace(c, expenses=exp, op_start=c.op_start + d, horizon=c.horizon + d)


def overrun(c, pct):
    """Every project expense grows by pct; the extra is paid in cash (financing unchanged)."""
    return replace(c, expenses={y: v * (1 + pct) for y, v in c.expenses.items()})


def drivers(c):
    """(label, low case, high case) around the base."""
    return [
        ("Discount rate 2% / 4%", replace(c, discount=c.discount - 0.01), replace(c, discount=c.discount + 0.01)),
        ("Construction delay +1 / +2 years", delayed(c, 1), delayed(c, 2)),
        ("O&M growth 2% / 5% a year", replace(c, om_growth=0.02), replace(c, om_growth=0.05)),
        ("Revenue growth 2% / 4% a year", replace(c, egi_growth=0.02), replace(c, egi_growth=0.04)),
        ("Cost overrun +7.5% / +16.6%", overrun(c, 0.075), overrun(c, 0.166)),
    ]
