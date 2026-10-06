// Checks the page's JavaScript P7 model (site/finance.js) against the Python model (feasibility.py).
// build.py stores the Python NPV, IRR and yearly net cash flow for each case in site/data.js; this re-runs every
// case in JavaScript and fails on any difference beyond floating-point noise.
// Usage: node tests/parity.js   (after python build.py)
const fs = require("fs");
const path = require("path");
const F = require("../site/finance.js");

const src = fs.readFileSync(path.join(__dirname, "..", "site", "data.js"), "utf8");
const window = {};
new Function("window", src)(window);
const checks = window.DATA.feasibility.checks;

let failed = 0;
for (const { label, case: c, npv, irr, ncf } of checks) {
  const got = F.summarize(c);
  const flows = F.cashFlows(c).ncf;
  const worstCell = Math.max(...flows.map((v, i) => Math.abs(v - ncf[i])));
  const npvDiff = Math.abs(got.npv - npv);
  const irrOk = (irr === null && got.irr === null) || (irr !== null && got.irr !== null && Math.abs(got.irr - irr) < 1e-9);
  // Amounts run to ~$280M, so allow a millionth of a dollar for summation-order differences.
  const ok = flows.length === ncf.length && worstCell < 1e-6 && npvDiff < 1e-6 && irrOk;
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${label.padEnd(40)} NPV ${got.npv.toFixed(2).padStart(16)}  diff ${npvDiff.toExponential(1)}  `
    + `IRR ${got.irr === null ? "none" : (got.irr * 100).toFixed(4) + "%"}  worst cell ${worstCell.toExponential(1)}`);
}
// The replay: every tracked project's budget change applied to each example, and the break-even overrun.
const { history, replay, examples } = window.DATA.feasibility;
const changes = history.map((h) => h.pct);
let replayed = 0;
for (const [key, want] of Object.entries(replay)) {
  const got = F.replay(examples[key].case, changes);
  const worst = Math.max(...got.map((v, i) => Math.abs(v - want.npv[i])));
  const be = F.breakevenOverrun(examples[key].case);
  const beOk = (be === null && want.breakeven === null) || (be !== null && want.breakeven !== null && Math.abs(be - want.breakeven) < 1e-9);
  const ok = got.length === want.npv.length && worst < 1e-6 && beOk;
  if (!ok) failed++;
  replayed += got.length;
  console.log(`${ok ? "ok  " : "FAIL"} ${(key + ": replay of " + got.length + " budget changes").padEnd(40)} worst NPV diff ${worst.toExponential(1)}  `
    + `break-even overrun ${be === null ? "none" : (be * 100).toFixed(2) + "%"}`);
}
const total = checks.length + Object.keys(replay).length;
console.log(failed ? `${failed} of ${total} checks FAILED` : `all ${checks.length} cases and ${replayed} replayed outcomes match the Python model`);
process.exit(failed ? 1 : 0);
