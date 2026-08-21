# PREREG — c5 home-regime PRECISION EXTENSION on the rented Hetzner node (hetzfarm-143)

Registered 2026-08-21 (UTC), BEFORE any extension row is produced. Branch
`hetzfarm-143` (off `regime-141` at d55c3d9), worktree
`/home/struktured/projects/dr-mario-hetzfarm-wt`. The commit hash of this file
is the registration.

## 1. Question

The regime map's stage 1 put the champion's failure rate in the c5 home regime
(L20 + honest bursty v1.1) at 14/50 = 28% [16.2, 42.5] (exact CP). That CI is
too wide to anchor power math for future survival experiments. This lane buys
PRECISION on the same cell: a standing n=500 (stretch 1000) run on the rented
CCX23 `rbm-train-2` — the long/cheap/single-stream niche that box exists for
($0 marginal, flat rate).

## 2. Component per measurement (rule 10) — byte-identical to the local c5 spec

Everything below is THE SAME OBJECT as PREREG_REGIME_MAP.md sec 2-4, cell
c5_L20_bursty, not a re-implementation:

* decisions: real RTL — verilated CoproDrMario `farm_vsim`
  md5 `3e6569f1b7cd254bac9029ea9c9d8d0f`, shipped as the SAME BYTES to the
  remote host (built portably: -O2, no -march=native; deploy_node.sh header).
  No re-verilation unless the shipped binary fails a gate; a re-verilated
  binary would need the full gate suite AND the cross-host row gate before any
  row counts.
* firmware: champion s20b `copro_rom.hex` md5 `e970e9ab0208cdbce1d39ed33e2f51ee`,
  confirmed per row from the RTL handshake (`fw_md5` field), never from a path.
* harness: the committed `run_regime.py` + `cosim_farm/game.py` + `cosim.py`
  from THIS branch (= regime-141 bytes, unmodified), pressure variant `bursty`
  (honest v1.1 refit, never v1), level 20 (84 viruses), max_pills 400,
  exec_mode drop, trace on.
* environment: remote venv pinned numpy==2.4.6 numba==0.66.0 llvmlite==0.48.0
  scipy==1.18.0 (PROVISIONING.md); absolute source paths mirrored on the
  remote so no code forks.
* arm label: `c5ext_L20_bursty` — distinct from `c5_L20_bursty` so the two
  populations can never silently mix in a rows file; pooling only via sec 6.

## 3. Seed block (fresh, even, stride 2)

Consumed to date: 300-699, 0-19999 (pressured census), 30000-33002 (regime map
incl. instrument seeds 33000/33002), 41100-53099, 60000+, 63000-63079,
63900-63907. This lane registers the EVEN block **34000-35998**:

* primary target n=500 → seeds 34000, 34002, …, 34998;
* stretch to n=1000 → continue 35000, …, 35998, same rules, no new
  registration required (the whole block is registered now).

Cross-host instrument-gate games use seeds 33000/33002 (already registered as
instrument seeds, outside every counting block) — gate games never touch a
seed any estimate reports on.

## 4. Endpoint and reading rule

Primary: failure rate = P(result in {topout, stall}) with **exact
Clopper-Pearson 95% CI**; one game = one seed = one independent unit (solo,
even-stride), so the game-clustered bootstrap CI (10,000 resamples over games,
seeded 20260821) is reported ALONGSIDE and must bracket the same story — a
material disagreement between the two intervals is itself a reportable
instrument anomaly, not a choice of the prettier one.
Secondary (report-only): topout/stall split, dies_ahead, garbage cells/game,
median pills to clear, wall secs. ERROR rows excluded from denominators; the
run FAILS if ERROR rows exceed 2%. Censoring flag inherited: if median clear
pills > 2/3 x 400, the stall count is CENSORING-SUSPECT.

Interim readings (the progress log / report line) are allowed at any n — an
interim is a rate with its CI at current n, never a stopping decision: the run
stops at n=500. The stretch to 1000, if taken, is taken by the team lead on
the 500 reading and reported as a registered continuation of the same block
(sec 3 registers the whole block now precisely so that continuation adds no
new researcher degree of freedom beyond the go/no-go itself).

## 5. Population gate (rule 7) — mutants must die before the burn

`analyze_c5ext.py --selftest` constructs and must REJECT: (M-a) out-of-block
seed, (M-b) odd seed, (M-c) mislabeled pressure_model, (M-d) wrong fw_md5,
(M-e) duplicate (arm,seed) row, (M-f) wrong level. The same validate() runs
inside every analysis pass on every row — a bad row fails the run, not the row.

## 6. POOLING RULE (registered up front)

Extension rows are poolable with local `c5_L20_bursty` rows ONLY if the
cross-host bit-exactness gate passes: seeds **33000 and 33002** played under
the FULL c5 config (bursty, L20, max_pills 400, s20b, drop, trace on) on BOTH
hosts; canonical row = the row JSON with host-varying keys {`wall_secs`,
`host`} removed, keys sorted; sha256 over that canonical form must be EQUAL on
both hosts for BOTH seeds (`xhost_gate.py`, hashes committed). Otherwise the
extension is reported as its own estimate and never pooled. Partial agreement
(1 of 2) is a FAIL.

## 7. Instrument gates on the REMOTE host (all before the burn; no gate, no rows)

Same suite the local burn was gated on, re-run ON rbm-train-2 against the
shipped binary + mirrored tree: (e) orientation, (d) physics, (a1/a2)
determinism (gate_validate.py); pure gates g1-g6 with all 7 mutants killed
(gate_regime.py); RTL gates g7/g8 (gate_regime.py --rtl); then the sec-6
cross-host gate. The gate sheet's last line is quoted verbatim in the report.

## 8. Execution

systemd unit **drm-c5precision** on rbm-train-2 (system unit, Restart=no;
resumability comes from per-seed atomic JSONL rows + banked-seed resume in
run_regime.py, so a manual restart loses nothing). 2 workers (the box's 2 real
cores; memory hetzner-keep-useful). `set -eo pipefail`, every stage gated on
the previous stage's success marker (NUL-safe `command grep -a`). Rows:
`/root/drm/c5ext/out/farm.jsonl`; progress line appended per game to
`/root/drm/c5ext/out/progress.log`; chained analysis writes
`/root/drm/c5ext/out/c5ext_summary.{json,txt}` after every completed slice.
Start time and purpose recorded in the report (ledger's spirit; box is
flat-rate, $0 marginal).
