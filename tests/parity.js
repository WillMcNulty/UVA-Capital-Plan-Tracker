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
console.log(failed ? `${failed} of ${checks.length} cases FAILED` : `all ${checks.length} cases match the Python model`);
process.exit(failed ? 1 : 0);
