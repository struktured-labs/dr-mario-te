# RESULT (2026-10-04/05, execution-fidelity lane): the 18-frame gap, the p107 early drop, the p13/p84 "DAS carry"

**Inputs:**
- The 10/04 couch recordings: tracker reads and cases from the couch-forensics pipeline, built per game by
  `build_cases.py` (the `m4g2_fair_20261004.cases` code path).
- Verilator co-sim publish timelines of the real copro RTL per build: FAIR fw 1488e158, FAIR2 fw c51d2e21
  (`timelines/`).
- Mesen replays of the REAL carts (FAIR = dbbb5007, FAIR2 = b1b57638) fed those timelines.
- No MiSTer. A silicon claim is a tracker read of the recording; a Mesen claim is a frame trace of the real cart.

**Replay method used here:** CHAINED, plus each silicon garbage volley delivered through the ROM's own path.
- The volley goes in as P2's incoming attack, `$0318` / `$0329`, written during the receiving pill's fall. The
  cart's DRPRESTART garbage-window path then really runs, and its GO is served the next case's co-sim timeline.
- Probe: dr-mario-te `tools/execfid/execfid_probe.lua`.
- The forensics lane's M4 G2 runs were unchained and garbage-free.

## Q1. The "18-frame gap": NOT a silicon timing lag

**Verdict:**
- The median 18 f is an instrument artefact.
- On the same event, silicon and Mesen agree to a constant +1 f (the video vs endFrame offset), on every game of both
  builds and on the 10/03 ANTIBODY_DIST games.
- The real per-pill outliers are cart state that the unchained, garbage-free replay did not carry.

**Discriminating test 1: compare the SAME event.** The forensics "lock" is not a lock.
- It is `cosim_m4g2 lock_f` = `traj[-1] - t_spawn`, the tracker's LAST frame before the next spawn. That includes
  the ROM's lock-to-next-spawn interval: 12-16 f without a clear, 30-37 f with one.
- Mesen LAND is the `$0397` lock frame. `lock_f - Mesen LAND` reproduces the reported number exactly: median 18, p10
  11, p90 35.
- The spawn-to-next-spawn period agrees on both sides (41/41, 173/173, 79/79 ...).
- Arrival at the final pose (orientation, bottom row, column), the first gravity drop and the first lateral are all
  **+1 f**.

| game | build | old metric (last − lock), median (p10-p90) | ARRIVAL median | ARRIVAL within ±2 f | STALE-predicted pills |
|---|---|---|---|---|---|
| M1 G1 | FAIR | 21 (15-35) | +1 | 127/156 | 9/181 |
| M1 G2 | FAIR | 21 (14-33) | +1 | 97/115 | 9/130 |
| M3 G1 / G2 / G3 | FAIR | 30.5 / 26 / 31 | +1 | 20/22, 14/17, 12/14 | 2, 3, 1 |
| M5 G2 | FAIR | 22 (17-34) | +1 | 90/107 | 6/143 |
| M2 G1 / G2 / G3 | FAIR2 | 15.5 / 20.5 / 23 | +1 | 30/40, 74/92, 66/85 | 15/46, 8/117, 9/98 |
| M4 G1 / G2 | FAIR2 | 22.5 / 18 | +1 | 86/110, 81/94 | 17/134, 12/107 |
| 10/03 G2 / G3 / G4 | ANTIBODY_DIST (c960dd49 + 1488, late-flip lane's unchained runs) | 20 / 24 / 22 | +1 | 85/102, 54/80, 85/114 | 4, 2, 4 |


**Each candidate source, measured:**

| source | measurement | result |
|---|---|---|
| spawn-to-first-move, gravity | first drop vs Mesen | +1 f |
| lateral pace | 24 spawn-row H pills | first lateral +1 on 20/24; tap-to-tap intervals identical |
| gravity fidelity | positive control: the 10/03 boards replayed on the UNPINNED D cart | +7 f on every arrival (the 5-6 f gravity pin + settle), so the instrument sees few-frame differences |
| hook rate | armed slams fire 32 hooks (16 f) after a stable publish | +1 f on 69/73 armed M4 G2 pills; a different hook rate would stretch that window |
| copro answer timing / clock / PLL | silicon − co-sim DONE on 255 DONE-gated slams, all games | median **0 f**, IQR −1..+2, no positive slope against done_f (`donegap.py`) |
| tracker alignment | | the constant +1 |

**Discriminating test 2: the outliers are cart STATE.** The state is predicted from silicon spawn times and co-sim DONE
(`timing.py compare`).
- **SLAM_ARM** (DRSLAM_MATURE, `patch_cartridge_copro.py`):
  - A pill whose predecessor's search is still ARMED at its spawn edge is disarmed (lock-while-armed / the
    `abort_stale` disarm). It holds for DONE instead of slamming 16 f after a stable publish.
  - The first pill of a game starts disarmed.
  - The unchained harness's filler pills (`done_f` = 3) re-arm it before every case.
  - M4 G2 unchained: 9/12 STALE pills read +14..+38 f. Chained: the STALE median is +1; 69/73 armed pills are within
    ±2.
  - The leftover STALE mismatches follow a previous-pill landing difference, or a DONE that lands within 0.6-3.4 f of
    the next spawn.
- **Garbage-window PRESTART:** the answer is ready at the spawn, so silicon slams early (−9..−37 f). Delivering the
  volleys makes M4 G2's armed+GARB pills agree 7/8.
- **Build dependence:** the mechanism is old. Its frequency is not: FAIR2 (V11 + abort + fair settle) has 8-33%
  STALE-disarmed pills, vs 1-4% on FAIR and 10/03. V11 publishes early, so the armed slam locks the pill before the
  search DONEs.
- **Consequence for replays:** chained, unchained and garbage-free replays land identically on M4 G2 (0/109 differ
  without garbage). The STALE states move tempo, not landings. Missing garbage, though, hid the day's largest execution
  defect (Q3).

## Q2. p107 early drop: a DISTGATE rule, not PROPH and not LATEGUARD

**Verdict: a driver rule.**
- DRDISTGATE substitutes its clamped target `EFF_DIST2` for the steering target, and "everything below" reads it,
  including the slam gate.
- On a ledge no row below the span is empty, so the budget is 0 and EFF = the current column. The capsule reads as
  "aligned", and with DONE `dn_p2` (`LDA ARMED2; BEQ dn_p2_go`) holds DOWN.
- PROPH-first only supplied the first column (3→2). The early DONE (f4.45) ended its window.
- LATEGUARD was not involved (`lg=1,0`, nothing frozen).

**Mesen frame trace** (real b1b57638; identical unchained, chained and with garbage):
- f1/f3: PROPH taps left.
- f4: the answer H col 0 is DONE.
- f5: commit with `eff=2 bud=0`, then DOWN.
- f6: one row down; f8: lock at col 2.
- Silicon shows the same, +1 f.
- At f5 the gravity counter is 4 of thr 9 (speedUps 10): 5 frames left, enough for the 2 taps.

**Prevalence** (`clampslam.py`; a clamp = the committed capsule parked at a clamped column whose budget is short of the
answer):
- **10/04, all 11 games replayed:**
  - PROPH-armed pills: FAIR 0 in 6 games; FAIR2 8 (M2 G1 6, M4 G2 2).
  - p107-type (PROPH-armed, reachable in the current row, slammed): FAIR2 **1/8** (M4 G2 p107, Mesen == silicon);
    FAIR 0.
  - Clamps on non-PROPH pills (M2 G2 p22/p82, M4 G2 p108) are Mesen-only: silicon landed elsewhere.
- **10/03 G2 boards** (16-17 PROPH-armed throat-ledge spawns, the tall endgame) on the fair carts:
  - D + 1488: 1 PROPH clamp, unreachable (2 f left, 5 columns).
  - A + V1 (the FAIR2 firmware class): **2/17 reachable clamp-slams** (p101, p115).
- **It is firmware-dependent.** It needs the answer DONE before PROPH-first carries the capsule to the target. V1/V11
  publish early, so FAIR2 is the exposed build.

**Fix: `DRDISTROW=2`** (new value of the settle lane's default-off flag; real pad inputs only).
- With no empty row below the span, DISTGATE credits the frames left before the gravity tick, min(7, (thr − $0392)/2)
  columns, but ONLY when that covers the whole |target − X|. Otherwise the budget stays 0, exactly as without the flag.
- Why not `DRDISTROW=1`: the settle lane's B (byte-identical, 78bc8e75 = `couch_fair_DB`) also fixes p107. But it
  starts PARTIAL moves: on 10/03 p101 on D, a late 5-column tuck with 1 tap of frames left lands one column over, a new
  hybrid. =2 keeps it on the earlier answer.
- A "don't slam while clamped" hold was rejected: it changes no landing, because the gravity tick locks the capsule in
  the same column. The budget was the bug.
- **Replay effect** (chained + garbage):
  - p107 → a0 (the copro final); 10/03 A+V1 p101 → a0 and p115 → a6.
  - M2 G2 p22/p82 → the final.
  - On top of DRLGPRESTART it removes the residual hybrids (table below). Alone it changes 1-2 pills per FAIR2 game
    and nothing on FAIR.

## Q3. p13/p84: NOT DAS carry; a LATEGUARD × PRESTART defect, found and reproduced

**Verdict.** DAS carry is impossible on these carts:
- Every lateral is a fresh DRTAPP tap, and L/R is never held two frames.
- horVelocity `$0393` = 0 at 4,130/4,132 logged spawns. The 2 carried a 15 from a blocked tap, which can only fire on
  a held button.
- The CHAINED replay carries the real pad and `$0393` across p12→p13 and p83→p84, and still lands a21/a24, NOT
  silicon's a4/a2.

What silicon did instead: it executed the **previous pill's target** (p12's a4, p83's a2) with DONE semantics. The
cause is a decision defect present in BOTH fair carts.

**Mechanism** (code `lg_gate`; Mesen `W` window trace, M4 G2 p12→p13):
1. p12 locks. Its search DONEs at f2058, the volley releases at f2061 (`atk` 2→0), and the DRPRESTART GO for p13
   follows at f2064.
2. DRLATEGUARD's latches are per-pill, reset only at the next spawn edge: `LG_CMT2` = 1 (p12 had committed).
3. f2067: `lg_gate` prices the prestart's first publish against the LOCKED p12. Its own cells fill the "current row",
   so the move is unfinishable: FREEZE (`lgl=1`).
4. f2100: the prestart DONE (a21) is dropped. TGT stays (4, H).
5. The spawn edge is prestart-owned (no PEND2, no new search). p13 runs TGT = p12's with DONE semantics: tap f1, move
   f3, DOWN f4, lock at col 4. Silicon shows the same, +1 f.

**Silicon census, all 11 games** (`prevtarget.py`; action(k) == action(k−1) ≠ brain after a garbage window):

| | pills after a garbage window | executed the previous pill's target | other pills, same pattern | misses vs brain after garbage / elsewhere |
|---|---|---|---|---|
| FAIR | 40 | **17 (42%)** | 6/515 (1.2%) | 58% / 14% |
| FAIR2 | 32 | **11 (34%)** | 6/470 (1.3%) | 56% / 13% |
| 10/03 ANTIBODY_DIST (no LATEGUARD) | 19 | **0** | 6/310 | 21% / 18% |

- M4 G2: p7, p13, p55, p77 and **p84**, the knife-edge pill of the tap-out per the forensics lane.
- Every one follows a window ≥ 183 f, long enough for the prestart to DONE before the spawn.

**Reproduction:**
- Mesen with garbage delivered reproduces 21 of the 28 silicon cases, frame-exact (p7, p13,
  p77, p84 on M4 G2; M1 G1 7/7; M1 G2 3/3; M3 G1/G2; M2 G1/G2 ...).
- The rest depend on whether the Mesen window (its garbage columns are the ROM's own, not silicon's) lets the prestart
  DONE before the spawn.
- py65 (`test_lgprestart.py`): the shipped D/A flag sets drop 12/18 and 16/25 prestart answers.

**Fix: `DRLGPRESTART=1`** (new, default off, needs DRLATEGUARD + DRPRESTART).
- `lg_gate` adopts while PRE_ACT2 != 0: a prestart answer belongs to a capsule that has committed nothing, which is the
  10/03 behaviour.
- +7 bytes, a pure decision change, no pad / timing / gravity effect.
- After the spawn PRE_ACT2 = 0, and LATEGUARD gates the falling capsule as before (it still refuses 4-20 falling
  changes per 24k py65 frames).
- In replay it lands the copro final on **27/28** of the silicon previous-target pills.
- The CvC carts have DRPRESTART=0, so a CvC soak cannot see this defect.

**Carry across the boundary, fairness and effect:**
- The only input that ever crosses the lock/spawn boundary is a held DOWN: the slam continues when the next pill is
  aligned and DONE from its first hook. A pad does that, and it is the driver's decision for the new pill.
- The "f4 lateral" is a fresh tap toward a stale target: a wrong DECISION, not an input-rate issue.
- **It hurt:** after a garbage window, misses vs the brain run 56-58% vs 13-14% elsewhere. In replay it is the largest
  source of hybrids (table below).

## Replay before/after (chained + silicon garbage; landing == silicon / == copro final / hybrid)

| build (games) | base cart | + DRLGPRESTART | + DRDISTROW=2 | + both |
|---|---|---|---|---|
| FAIR, dbbb5007 + 1488 (M1 G1-2, M3 G1-3, M5 G2; 573 pills) | 483 / 512 / **24** | 476 / 538 / **0** | 483 / 512 / 24 | 476 / **539** / **0** |
| FAIR2, b1b57638 + V11 (M2 G1-3, M4 G1-2; 508 pills) | 431 / 461 / **21** | 426 / 478 / 4 | 430 / 465 / 17 | 426 / **482** / **0** |
| 10/03 G2 boards, D + 1488 (116) | 94 / 98 / 3 | 96 / 100 / 1 | 94 / 98 / 3 | 96 / 100 / 1 |
| 10/03 G2 boards, A + V1 (116) | 89 / 110 / 4 | 91 / 113 / 1 | 90 / 111 / 3 | 92 / **114** / **0** |

- "== silicon" falls with the fixes because silicon had the defects.
- Per-game rows are in `report_20261004.txt`.

## Gates (dr-mario-te `claude/execfid`, `experiments/execfid/GATES.txt`)

| gate | result |
|---|---|
| negative controls (`tools/execfid/build_carts.sh`) | flags unset AND =0 rebuild dbbb5007, b1b57638, 464a4b75 and CvC 821cafdb byte-identically; DRDISTROW=1 is still 78bc8e75 (= settle lane `couch_fair_DB`) and 45e3fe7c |
| `tools/gate/run_cart_gates.sh` | ALL PASS (7 suites; the gravity-fidelity suite covers every arm incl. the new ones) |
| gravity-fidelity: D / D_abort / D+LGP / A+LGP / A+ROW2 / D+LGP+ROW2 / A+LGP+ROW2, seeds 5/11/23 × 6000 f | all PASS; 464a4b75 KILLED (pin detected) on every seed |
| `tests/test_lgprestart.py` (defect gate, 4 seeds × 6000 f, summed) | D 12/18 and A 16/25 prestart answers dropped (DEFECT REPRODUCED); every +DRLGPRESTART arm drops 0, with LATEGUARD still refusing falling capsules (4-20) |
| `tests/test_lateguard_census_cut.py`, A/D + LGP + ROW2 | GATE_LGCUT PASS (5 mutants killed) |
| static NMI census, worst admissible frame / 29,780 | D 27,752; A 27,823; +LGP unchanged (27,751 / 27,823); A+ROW2 = A+LGP+ROW2 28,001 (margin 1,779); D+LGP+ROW2 27,929 |
| TAP interface (P=2, 40k frames) | A+LGP+ROW2 PASS, D+LGP+ROW2 PASS; the `everyframe` mutant KILLED |

## Files
**dr-mario-rl h16 `experiments/execfid/`:**
- Scripts: `timing.py` (Q1 events + state prediction), `donegap.py`, `clampslam.py` (Q2), `prevtarget.py` (Q3),
  `report.py` (roll-up), `build_cases.py`.
- Banked cases: `cases/cases_<game>_fair_20261004.jsonl`, `timelines/pubtrace_<game>_fair_20261004.jsonl`,
  `cases_timing_20261004.jsonl`, `cases_prevtarget_20261004.jsonl`, `cases_clampslam_20261004.jsonl`.
- Output: `replay_20261004.json`, `report_20261004.txt`.

**dr-mario-te `claude/execfid`** (PR #36 into `claude/abort-stale`, not merged; tag `execfid-lgprestart-distrow2-20261004`;
worktree `/home/struktured/projects/dr-mario-execfid-wt`):
- `patch_cartridge_copro.py`: `DRLGPRESTART`, `DRDISTROW=2`.
- Tests: `tests/test_lgprestart.py`, and `tests/test_gravity_fidelity.py` (new arms + a fix to the dead-pill counter's
  false positive).
- `tools/execfid/` (builds, gates, replay probe) and `experiments/execfid/` (RESULT_EXECFID.md, GATES.txt).

**Run logs (not committed):** `~/projects/dr_mario_rl/tmp/execfid/runs/<tag>/`; carts in `tmp/execfid/carts/`.
