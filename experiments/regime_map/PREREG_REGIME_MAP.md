# PREREG — Champion failure-regime map on the real RTL (regime-141)

Registered 2026-08-21 (UTC), BEFORE any map row is produced. Branch `regime-141`
(off `origin/v8-rematch`), worktree `/home/struktured/projects/dr-mario-regime-wt`.
Committed before the farm runs; the commit hash of this file is the registration.

## 1. Question

Where does the current champion actually FAIL on the real RTL, and how often?
Today's GW pricing experiment was VOID BY SATURATION (memory
`dr-mario-gw-pricing-void`): under honest bursty v1.1 pressure at L11 the
champion cleared 96/96 RTL games, so no survival-endpoint experiment can be
powered there. Before ANY future survival-flavored experiment (GW revival,
DRP1SLICE offline value, eval work) is designed, the program needs a map:
pressure regime x virus load -> failure rate, with honest CIs, on the same
instrument those experiments would use.

## 2. Component per measurement (rule 10)

Every placement decision: **real RTL** — verilated CoproDrMario
(`farm_vsim`, md5 `3e6569f1b7cd254bac9029ea9c9d8d0f`, copied byte-identical
from the gw lane's working build), champion firmware **s20b**
(`/mnt/data/drmario_cosim/fw/s20b/copro_rom.hex`, md5
`e970e9ab0208cdbce1d39ed33e2f51ee`), driven by the committed co-sim farm
(`experiments/cosim_farm/game.py` + `cosim.py` in THIS tree; game.py carries an
additive report-only `volleys` capture, diff committed alongside this file).
Game state / pill stream / garbage injection: the faithful Python env, exactly
as in every prior farm result. Exec mode `drop` (the deployed cart has no tuck
executor). This is firmware-in-the-loop RTL, NOT the mirror, NOT py65.

Per `dr-mario-gw-pricing-void`: NOTHING here is de-duplicated, enriched, or
predicted by mirror play. Every registered seed runs on the RTL, unconditionally.

## 3. Pressure variants (each verified to EXIST and BIND before registration)

| variant | what it is | provenance | binding gate |
|---|---|---|---|
| `clean` | no garbage | — | row `garbage==0` audit |
| `bursty` | bursty **v1.1** honest per-player refit (never v1) | fitted human | gw lane precedent; g7 |
| `bursty_x2` | v1.1 with fire probability x2, capped 1.0; sizes/columns/gaps untouched | SYNTHETIC dial, registered as "honest v1.1 x alpha", NOT a fitted human | g1 + mutant M1 |
| `bursty_aim` | v1.1 honest fire+size; columns redirected to spawn cols (3,4) first, volume-neutral | SYNTHETIC aim, farm-servable analog of the tier-3 adversarial-scheduler finding (aim at spawn lanes, honest volume) | g2/g3 + mutant M2, plus per-row end-to-end volley audit |

The true tier-3 evolved adversary CANNOT be served by this farm (it needs a
live two-sided VS opponent; the farm is solo + injector). `bursty_aim` is the
closest servable analog and is registered as an analog, not as the adversary.

Level axis: `level` binds through `FaithfulDrMarioEnv -> place_viruses(level)`,
count = min(4*(level+1), 84): L11 = 48, L20 = 84 (g4 + mutant M3; g8 end-to-end
on the RTL loop). The bursty v1.1 model was FITTED on L11 human footage; its use
at L20 is registered as an extrapolation of the volley process, not a fitted
claim about L20 humans.

## 4. Cells and seeds (registered, fresh, even-stride)

Seed low bit is dead (`dr-mario-seed-space-is-32767`), so all seeds are EVEN,
stride 2 — no aliased duplicate streams inside or across cells. Blocks
30000-32998 are fresh (consumed to date: 300-699, 0-19999 pressured census,
41100-53099, 60000+, 63000-63079, 63900-63907). Instrument-gate games use
33000/33002, outside every block. **This lane consumes 30000-33002.**

| cell | variant | level | max_pills | even seeds from | max n |
|---|---|---|---|---|---|
| c1_L11_bursty | bursty | 11 | 300 | 30000 | 250 |
| c2_L11_x2 | bursty_x2 | 11 | 300 | 30500 | 250 |
| c3_L11_aim | bursty_aim | 11 | 300 | 31000 | 250 |
| c4_L20_clean | clean | 20 | 400 | 31500 | 250 |
| c5_L20_bursty | bursty | 20 | 400 | 32000 | 250 |
| c6_L20_aim | bursty_aim | 20 | 400 | 32500 | 250 |

max_pills 400 at L20 (vs 300 at L11): 84 viruses at the L11 pills/virus ratio
(~1.8) plus garbage headroom; registered so the `stall` label is a genuine
no-progress outcome, not budget censoring. The final report must show
median clear pills << cap in every cell; if any cell's median clear consumes
>2/3 of its cap, that cell's stall count is flagged CENSORING-SUSPECT.
`bursty_x2 x L20` is registered OUT OF SCOPE (budget; the x2-vs-aim contrast is
taken at L11, the level contrast at honest bursty + aim).

## 5. Endpoints

Primary per cell: **failure rate** = P(result in {topout, stall}), exact
Clopper-Pearson 95% CI. One game = one seed = one independent unit (solo,
even-stride), so game-clustered CI == plain exact binomial; stated per rule.
Secondary (report-only): topout/stall split, dies_ahead, garbage cells/game,
median pills to clear, wall secs. ERROR rows excluded from denominators; run
FAILS if ERROR rows exceed 2% overall.

## 6. Sample size, power, and the ADAPTIVE rule (registered up front)

Stage 1: **n = 50 per cell** (300 games). At true rate 10%, P(>=2 failures) =
96.6%; at 5%, 72%; a 0/50 cell yields exact 97.5% one-sided upper bound 7.1%.
Stage 2 (budget **B2 = 400 games**, allocator is CODE:
`analyze_regime.py --allocate`, deterministic in the stage-1 rows):

1. Eligible = cells with >=2 stage-1 failures. Top eligible cells up to n=250,
   priority |rate - 0.10| ascending (ties: cell name); partial top-up allowed
   on the last when B2 runs out.
2. If <2 eligible: top up the two highest-failure-count cells to 250.
3. If ALL cells 0-failure: top up c5_L20_bursty and c6_L20_aim to n=150 and
   stop; every cell is then reported at its exact CP bound (a saturation-flavored
   answer is still the map's answer).

At n=250, true 10% -> CI ~ [6.6%, 14.4%]; true 5% -> [2.7%, 8.4%]. Enough to
(a) rank regimes and (b) certify a cell as a usable home for survival
experiments (lower CI bound >= 3%, the registered usability bar: an MDE of a
few pp per arm is then affordable at n~200/arm).

Stage-2 cells run SEQUENTIALLY in allocator priority order, so an early cut
(the whole pipeline is per-seed-atomic and resumable) sacrifices the least
informative cells first. Hard analysis cut: whatever is banked by 2026-08-21
20:00 UTC is the final dataset.

## 7. Instrument gates (all must pass BEFORE the burn; sheet by last line)

Pure: g1 amplifier binds (M1 alpha-inert killed), g2 aim binds (M2 aim-inert
killed), g3 aim replay-determinism, g4 level binds (M3 level-inert killed),
g5 reader alive (M4 edited-row), g6 POPULATION gate alive (M5a-e: out-of-block
seed, mislabeled pressure, wrong firmware, duplicate row, unaimed volley — the
rule-7 population mutants). RTL: gate_validate (e) orientation, (d) physics,
(a1/a2) determinism fresh-vs-fresh and fresh-vs-REUSED; g7 end-to-end variant
games with per-row volley audit; g8 L20 through the real farm loop.
Population-level audits also run INSIDE the final analysis on every row
(analyze_regime.validate) — an unregistered arm, out-of-block seed, wrong
firmware, duplicate, or unaimed aim-volley row fails the whole run, not just
the row.

## 8. Deliverable & decision rule

The regime map table (cell x failure rate x CI x n), the gate sheet, and a
recommendation: the right home for survival experiments is the cell (preferring
honest-provenance pressure over synthetic dials, lower level over higher, in
that order) whose failure-rate CI lower bound >= 3%. If NO cell reaches it,
the recommendation is that this farm cannot host survival endpoints for this
champion at any registered regime, and survival work must move to a two-sided
VS instrument (tier-3 adversary) or wait for a weaker/handicapped baseline —
stated as the finding, not padded.

Interpretation constraints registered now: synthetic-dial cells (x2, aim)
measure SENSITIVITY to intensity/aim, not human-realistic rates; cross-level
bursty cells inherit the L11-fit extrapolation caveat; comparisons ACROSS cells
sharing seeds-block structure are unpaired (different blocks by design — this
is a census per cell, not an A/B).

## 9. Execution

`chain_regime.sh` under `systemd-run --user --unit drm-regime-farm`,
`set -eo pipefail`, every stage gated on the previous stage's success marker
(the masked-crash lesson: a gate that dies on line 1 must stop the chain).
22 workers, ~2 cores left free, all local, $0 cash. Wall estimate: stage 1
~6-7 h, stage 2 <= ~12 h at the B2 cap.
