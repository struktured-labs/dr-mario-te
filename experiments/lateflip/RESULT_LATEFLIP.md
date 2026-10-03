# Late flips on tall boards: root cause, DRLATEGUARD, and the emulator before/after (2026-10-03)

Couch match 1, game 2, 2026-10-03 (ANTIBODY_DIST: rbf 318607aa, couch cart c960dd49, fw 1488e158). The AI tapped
out at 10 viruses. Silicon followed the python brain on 77/116 pills; the misses were 22 OTHER, 11 LATE-FLIP, 5
SHORT-LANDING and 1 TUCK. The forensics are in h16 `experiments/couch_forensics/RESULT_COUCH_DIST60_G2.md`.

## Instrument (new): the copro's real publish timeline, replayed into the real cart

1. **Co-sim.** `tools/lateflip/sim_pubtrace.cpp` is a Verilator build of the shipped copro: RTL NES_MiSTer-dist
   3b164c7 with the shipped defines, and fw 1488e158.
   - It polls the result mailbox the way the cart does. It logs every change of the published (col, orient) with
     its clock since GO, then DONE, the final answer and the tuck descriptor.
   - The input is the exact bytes the couch cart uploads: the board, plus cA/cB/nA/nB with the seed,
     DRREACHTX gravity and DRTAPP nibbles.
2. **Replay.** `tools/lateflip/lateflip_probe.lua` runs headless Mesen on the real couch cart.
   - At each P2 spawn it injects the case board, colours, preview, speedUps and virus count.
   - It answers the $5200 mailbox from that timeline, frame-quantised and keyed to the cart's own GO.
   - It checks the cart's upload byte-for-byte against the timeline's input: **UPLOAD MATCH on every case**.
   - It logs the driver's state every frame and the landing.

**Fidelity:**

| game | Mesen + RTL timeline == silicon landing | python brain == silicon |
|---|---|---|
| G2 | **102/116** | 77/116 |
| G3 | 80/86 | 77/86 |
| G4 | 114/133 | 117/133 |

## Root cause, measured

### 1. The driver commits to a running best, not the copro's answer

The commit gate opens at GO + 6 f (MIN_THINK = 12 hooks). DONE comes 20–55 f after GO.

| G2 category | at-gate running best == copro final |
|---|---|
| MATCH | 57/77 |
| **LATE-FLIP** | **0/11** |
| OTHER | 8/22 |

Source: `DISCRIMINATING_TEST_G2.txt`.

### 2. When the published answer changes after the commit, the live path adopts it

The path is `act` → ARMED2 ≠ 0 → read the live mailbox → `nf2_colok`.
- **Column:** TGT_C2 is always replaced.
- **Orientation:** DRRELATCH re-opens the latch whenever `$0386 >= CROSS_LOWY (8)`. That test is floor-relative,
  so on a tall board it is true until lock. `act_p2`'s pre-phase rotates at once.
- **Lateral move:** DISTGATE then clamps it to the current column as soon as no row below the
  [x..target] span is empty.
- **Result:** a **HYBRID** landing, the new orientation at the old column.

**G2 p99, the well cap** (`TRACE_G2_p99_off_on.txt`, flag OFF):
1. f8: GO.
2. f10: the copro publishes V col 3 (the well drop, = the python brain's pick).
3. f14: the driver commits; the capsule is at V col 3.
4. f24 (GO + 16 f): the copro publishes H col 6. RELATCH rotates the capsule to H at col 3.
5. DISTGATE fall over [3..6] is 0, budget 0, so there is no lateral move.
6. f31: DONE, then the slam. **H col 3 at row 2: the well is capped.** This is exactly silicon's a11.

### 3. Where the late answers come from

Two sources:
- **(a) The main search's own argmax.** It is found after the Pass-0 top (p31, p95, p98, …).
  - The running best is monotone in V1, so the at-commit candidate is the earliest full-depth root, not the
    answer.
- **(b) The firmware TUCK extension.** This covers the kill sequence p99, p100, p102 and p111–p114.
  - It runs after every root and overrides the main-search argmax, which is the python brain's pick in 6/8 cases.
  - It live-publishes the tuck's final (col, orient) WITHOUT the descriptor. The cart reads `$5x87/88` only at DONE.
  - It is not reach-masked:
    - all 8 tuck finals fall outside the reach_fw mask;
    - the py65 reach routine on the same upload bytes returns R_FLT = 1 and that same mask;
    - fw 77ec742c (no DIST) gives the same finals.
  - Root re-ordering cannot move these commits.

### 4. Silicon's 11 LATE-FLIPs, in these terms

| outcome | pills |
|---|---|
| completed the final | 3 (p31, p47, p55) |
| stayed on the at-gate answer | 1 (p18) |
| hybrid | 6 (p95, p98, p99, p111, p112, p113) |
| unexplained | 1 (p17) |

- The flips go toward the final (or a later intermediate) answer.
- OTHER pills whose first lateral move is opposite the python target: 10. Of those, 7 match the at-gate RTL best's
  side.
- **11/22 OTHER are simply the RTL final ≠ the python brain.** That is not churn.

### 5. Brain-model gap: the python brain is not the shipped brain on these boards

On the 116 G2 boards the RTL final equals the python Leaf6Decider choice on **87 (75%)**.
- 8 of the 29 disagreements are tuck commits.
- 21 are main-search value differences. The python margin is median 63 and min 5, so tie jitter (≤ 3) cannot
  explain them.

The "brain alone clears the board" counterfactual therefore used a brain that differs from silicon's.

## The fix: `DRLATEGUARD=1` (default off; off rebuilds c960dd49 / 3b8737a9 byte-identical)

**Rule.** Once the pill has committed (p2_commit ran), a published target that differs from the current one, whether
live or at DONE, is adopted only if the move can still be finished:
- `need = (|col'−X| + rotations) · P + M` (M = 0);
- `avail = (thr − $0392) + (thr+1) · (K − [col' ≠ X])`;
- `K` = the fully empty rows below the capsule across `[min(X,col') .. max(X, col'+H')]`, capped at 2;
- the capsule's own row must also be clear across that span.

**Refusal.** The pill is FROZEN: later publishes and the DONE answer are ignored, along with its tuck latch and
RECOMMIT. The capsule finishes the target it was executing.

**Latency.** **0 frames of answer latency.** The gate only refuses; it never waits.

**Cost:**
- +543 B in unit 1 (incl. the 81 B gravity table) and 11 B of PRG-RAM at `$61D6-$61E0`.
- NMI census: steady-play worst +878 cyc, spawn-edge +944.
- Couch certificate: worst admissible frame 27,704 / 29,780, margin 2,076 (it was 2,230).
  - Two proof-carrying cut points (`lg_live` / `lg_done`) exclude the gate from non-committing DRPRESPIPE phase
    hooks.
  - The generic "SAME-FRAME PAIR" line (spawn_edge + steady_play, which is not the certificate on a pipelined image)
    reads 29,801.
- CvC: steady +836, spawn-edge +946.

**Gates (all PASS):**
- `gate_lateguard.py`: the emitted lg_gate under py65 equals the reference rule on 20,000 random states.
  - Mutants `always` and `never` are both KILLED.
  - `DRLATEGUARD=0` emits nothing.
- TAP interface: 0 violations over 80k frames.
- `tools/gate/run_cart_gates.sh`: ALL PASS.
- `derive_prg_ram_map.py --check`: 0 collisions. The new `lateguard-couch` config makes LG_*, TAP_* and SPAWNEDGE_*
  show their writers.
- `test_census`: ALL PASS.

## Mesen before/after (real cart, real RTL timelines; `MESEN_G*_ship_vs_guard.txt`)

| game | landings changed by the guard | hybrids ship → guard | == copro final ship / guard |
|---|---|---|---|
| G2 (tall, the tap-out) | 10/116 | **9 → 1** | 101 / 99 |
| G3 (normal) | 1/86 | 1 → 0 | 82 / 82 |
| G4 (endgame) | 2/133 | 2 → 0 | 131 / 131 |

**G2 changes:**
- p95, p98, p99, p100, p111, p112, p113: hybrid → the at-commit answer, which is the python brain's pick.
- p114: hybrid → an intermediate published candidate.
- p31: the late answer was refused, giving the brain's low H4 instead of silicon's tower-seeding H5.
- p67: now equals silicon.

On normal-height G2 boards (max height < 12), 29/31 landings are identical.

## Cart-rule options

Source: `POLICY_OPTIONS.txt`. The model is `steer_churn.py` (h16), which reproduces the Mesen landing on 111/116 (ship)
and 114/116 (guard). Regret is per scored placement against the python brain's own pick, using the python
evaluator; it is biased toward python-like picks.

| G2 option | hybrids | == final | python regret |
|---|---|---|---|
| ship (Mesen) | 9 | 101 | 48.5 |
| **guard (Mesen)** | **1** | **99** | **17.1** |
| freeze after commit (Mesen, mutant `always`) | 0 | 70 | 46.0 |
| tall-board ignore reversal/rotation (model) | 1 | 89 | 23.0 |
| ship + root re-ordering, upper bound (model) | 7 | 108 | 29.7 |
| guard + root re-ordering, upper bound (model) | 1 | 108 | 11.8 |

On G3/G4 the freeze option drops == final to 60/86 and 89/133. Executing the stale answer costs real moves.

**Recommendation: both.**
- Ship the cart guard: it removes hybrids from either source.
- The firmware fixes reduce how often it has to keep a stale answer:
  - publish tuck commits only at DONE, with the descriptor (and/or reach-mask them);
  - root re-ordering.

## Not established

- **No silicon run yet.**
  - Mesen's publish timing is frame-quantised from the co-sim, with tie-break seed 0. Silicon's seed is unknown.
  - p98's late answer finished in Mesen with 1 frame to spare but fell one column short on silicon. The guard (M = 0)
    refuses it, which is correct for silicon. Margins this thin are where emulation and silicon can disagree.
- **Outcome value is unmeasured.** No game-level A/B was run. The regret column uses the python evaluator, which
  disagrees with the RTL on 25% of G2.
- **The steering sim does not generate churn for new boards.** `steer_churn.py` executes a given timeline; scoring a
  new build in full-game sims needs a running-best and tuck-commit generator.

## Harness invocations (any firmware hex)

- **Build the co-sim:** `tools/lateflip/build_pubtrace.sh [RTL_MAPPERS_DIR] [OUT] [-D...]`. The default is
  NES_MiSTer-dist 3b164c7 with the shipped defines; the output is `tmp/pubtrace/obj_pub2/vsim_pub2`.
  - The firmware is read at runtime from `copro_rom.hex` in the process's working directory.
- **Timeline for the couch cases:** `FW=<hex> J=2 python h16:experiments/lateflip/pubtrace_g2.py OUT.jsonl [p...]`.
  - `CASES=cases_dist60_20261003.jsonl GAME=G3|G4` selects another game.
  - The cart-upload byte encoding lives in `upload()` there.
- **Mesen replay:**
  1. `python tools/lateflip/gen_cases_lua.py OUT.jsonl cases.lua 0 1c 2c ...` (a `c` suffix chains a case after
     the previous pill).
  2. `tools/lateflip/run_lateflip.sh TAG cart.nes cases.lua [maxframes]` (one Mesen at a time; it waits for the seat).
  3. `tools/lateflip/parse_lateflip.py LOG_OFF LOG_ON`.
- **Churn model:** `python h16:experiments/lateflip/steer_churn.py TIMELINE.jsonl MESEN_LOG_OFF [MESEN_LOG_ON]`.
  `execute(..., policy=ship|guard|freeze|tallfreeze)`.
- **Build the carts:** `tools/lateflip/build_couch_lateguard.sh` (identity check against c960dd49 included).
