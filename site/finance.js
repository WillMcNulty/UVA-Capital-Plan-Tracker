// The CE-3010 P7 cash-flow model, ported line for line from projects/ce3010-capital/feasibility.py so the page
// can recompute NPV and IRR as sliders move. tests/parity.js checks it against the Python model's own output.
// A case is the Python `Case` as JSON: equity/expenses/loan map a year (as a string) to an amount.
(function (root) {
  const ROWS = ["equity", "loan", "expenses", "egi", "opex", "noi", "debt_service", "net_income", "ncf"];

  function pmt(rate, n, principal) {
    return rate === 0 ? principal / n : principal * rate / (1 - Math.pow(1 + rate, -n));
  }

  function sumValues(m) {
    return Object.values(m).reduce((a, b) => a + b, 0);
  }

  function cashFlows(c) {
    const n = c.horizon + 1;
    const rows = {};
    for (const k of ROWS) rows[k] = new Array(n).fill(0);
    for (const [y, v] of Object.entries(c.equity)) rows.equity[+y] -= v;
    for (const [y, v] of Object.entries(c.loan || {})) rows.loan[+y] += v;
    for (const [y, v] of Object.entries(c.expenses)) rows.expenses[+y] -= v;
    for (let i = 0; i < c.op_years; i++) {
      const y = c.op_start + i;
      if (y <= c.horizon) {
        rows.egi[y] = c.egi0 * Math.pow(1 + c.egi_growth, i);
        rows.opex[y] = -c.om0 * Math.pow(1 + c.om_growth, i);
      }
    }
    const hasLoan = c.loan && Object.keys(c.loan).length > 0;
    const ds = c.debt_service != null ? c.debt_service
      : (hasLoan ? pmt(c.loan_rate, c.loan_term, sumValues(c.loan)) : 0);
    for (let i = 0; i < (hasLoan ? c.loan_term : 0); i++) {
      const y = c.debt_start + i;
      if (y <= c.horizon) rows.debt_service[y] = -ds;
    }
    for (let y = 0; y < n; y++) {
      rows.noi[y] = rows.egi[y] + rows.opex[y];
      rows.net_income[y] = rows.noi[y] + rows.debt_service[y];
      rows.ncf[y] = rows.equity[y] + rows.loan[y] + rows.expenses[y] + rows.net_income[y];
    }
    return rows;
  }

  // Excel's convention as the template uses it: NPV(rate, years 1..N) + year 0.
  function npv(rate, flows) {
    let s = flows[0];
    for (let t = 1; t < flows.length; t++) s += flows[t] / Math.pow(1 + rate, t);
    return s;
  }

  // Bisection on NPV = 0; null when there is no sign change in the bracket.
  function irr(flows, lo = -0.99, hi = 1.0) {
    let fLo = npv(lo, flows);
    const fHi = npv(hi, flows);
    if (fLo * fHi > 0) return null;
    for (let k = 0; k < 200; k++) {
      const mid = (lo + hi) / 2;
      const fMid = npv(mid, flows);
      if ((fMid > 0) === (fLo > 0)) { lo = mid; fLo = fMid; } else { hi = mid; }
    }
    return (lo + hi) / 2;
  }

  function summarize(c) {
    const flows = cashFlows(c).ncf;
    return { npv: npv(c.discount, flows), irr: irr(flows) };
  }

  // Construction runs d years longer: the last expense year moves d years later, escalated; opening moves with it;
  // the operating life is kept, so the horizon grows. Equity, the loan draw and debt service keep their dates.
  function delayed(c, d, escalation = 0.03) {
    if (d === 0) return c;
    const last = Math.max(...Object.keys(c.expenses).map(Number));
    const exp = { ...c.expenses };
    const v = exp[String(last)];
    delete exp[String(last)];
    exp[String(last + d)] = v * Math.pow(1 + escalation, d);
    return { ...c, expenses: exp, op_start: c.op_start + d, horizon: c.horizon + d };
  }

  // Every project expense grows by pct; the extra is paid in cash (financing unchanged).
  function overrun(c, pct) {
    const exp = {};
    for (const [y, v] of Object.entries(c.expenses)) exp[y] = v * (1 + pct);
    return { ...c, expenses: exp };
  }

  const api = { ROWS, pmt, cashFlows, npv, irr, summarize, delayed, overrun };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Finance = api;
})(typeof window !== "undefined" ? window : globalThis);
