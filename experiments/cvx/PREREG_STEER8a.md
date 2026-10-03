# PREREG (2026-10-03): STEER8a — the SILICON-FAITHFUL brain under the corrected send fits (blocks 1–2)

Written and committed BEFORE any STEER8 game (see "Data state at commit").

## Why
The brain-gap lane found that the python sim brain (`cascade_leaf6_x.Leaf6Decider` and its ancestors) picks differently
from silicon on ≈ 5% of decisions, and 7–19% on tall, hang-rich boards (`experiments/braingap/RESULT_BRAINGAP_20261003.md`,
87ba445b).
- **The cause is the firmware `eh_terms` semantics:**
  - R4 hang credit: 40 + 20·gap, virus columns only.
  - eh is scored on a "soft b1" compact-gravity rebuild.
- **The drop-in fix is `Leaf6FwDecider`.** With every switch on, its per-root V1 equals py65 on 9,689/9,689 roots and
  its finals equal the co-sim on 326/326.
- **Every STEER verdict so far used the python brain in both arms.**

## Brain, cells, seeds
**Runner:** `steer8_run.py`. It uses stuck_probe's game loops, unified DRTAPP=2 steering, the reach_fw_tap mask, and
NOMINAL answer latency.

**Arms** (`Leaf6FwDecider`, every switch on: veto, hang=R4, ehb1=soft b1, ehnp, wrap, order):

| arm | brain |
|---|---|
| **fA** | faithful ANTIBODY (mode off) |
| **fD** | faithful DIST60 (dist_target, W 60, vk 4) |

**Cells** (the corrected 2026-10 fits, `refit_opp.py`, all at δ 2.65):

| cell | setting |
|---|---|
| gb10 | gate (b) `owner202610` |
| rc10 | race lam 2.36, M 177 |
| lulu10 | LULU race lam 2.56, M 140 |

**Seeds** (declared reuse): exactly STEER6r's.
- gb10: **1,500** (39134–40932 + 33000–34198).
- Races: **600** (39134–40332).
- So the python ANTIBODY / DIST60 rows from STEER6r pair seed-for-seed.

**Total:** 2 arms × 2,700 = **5,400 games**. 8 workers (Quartus priority), `nice 19`, MemoryMax 20G. Runs after STEER6r.

## Block 1 (descriptive): how far did the brain gap bias the levels?
- **fA − python ANTIBODY** (STEER6r `s5b_hsv512` rows), per cell, paired, 95% CIs, churn (fixed / new).
- The same for **fD − python DIST60**.
- No bar.

## Block 2 (PRIMARY): does DIST60 still win on the real brain? fD vs fA, paired
**CANDIDATE HOLDS iff** (STEER6r's rule, the same code: `analyze_steer6r.verdict`):
1. gb10 tap-out Δ upper 95% CI < 0, AND
2. rc10 race Δ upper CI ≥ 0, AND
3. lulu10 race Δ upper CI ≥ 0.

- The race guards are "no demonstrated loss". Under a null race effect each false-fails 2.5%.
- **Also reported:**
  - whether the race gain itself holds (lower CI > 0);
  - the difference-in-differences (faithful gain − python gain) on the same seeds.
- **Multiplicity:** one primary comparison, its three conditions combined by AND (intersection-union test, no
  adjustment).
- `analyze_steer8a.py --selftest` re-runs the rule's killed-mutant test.

## Gates (done before this commit)
**Identity:** with every switch off, the runner reproduces the banked python rows, every key except the arm label
(`steer8/smoke`):

| arm | reproduces | games |
|---|---|---|
| fA_off | `s5b_hsv512` gb (OWNER-0804) and rc47 | 2 + 2 |
| fD_off | `s6_dist_target60` gb and rc47 | 2 + 2 |

**8/8 identical.**

**Smoke:** fA and fD run under owner202610 (2 + 2 games).

## Data state at commit
- `steer8/` holds only `smoke/` gate rows. There are 0 STEER8 result rows.
- STEER6r is still running. Its rows have not been analysed.
