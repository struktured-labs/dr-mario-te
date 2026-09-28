// Parity check: the JS brain must pick the same placement (and REACH mask) as the Python reference
// (experiments/cvx/cascade_leaf5b_x.py, arm s5b_hsv512) on every golden board.
//   node web/antibody/test/check_parity.js [golden.json]
// Regenerate goldens: python3 web/antibody/test/gen_golden.py 200 7 > web/antibody/test/golden_antibody.json
const path = require("path");
const B = require(path.join(__dirname, "..", "antibody_brain.js"));
const file = process.argv[2] || path.join(__dirname, "golden_antibody.json");
const g = JSON.parse(require("fs").readFileSync(file));
let okA = 0, okM = 0;
g.forEach((c, i) => {
  const m = B.reachMask(Int8Array.from(c.col), c.thr, 2);
  if (m.every((x, j) => x === c.mask[j])) okM++; else console.log("mask mismatch on case", i);
  const a = B.choose(c.col, c.vir, c.lnk, c.ca, c.cb, c.na, c.nb, c.mask);
  if (a === c.action) okA++; else console.log("action mismatch on case", i, "js", a, "py", c.action);
});
console.log(`reach mask ${okM}/${g.length}, action ${okA}/${g.length}`);
process.exit(okA === g.length && okM === g.length ? 0 : 1);
