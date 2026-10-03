# STEER7 part 2 (desk analysis, no builds): where could faster answers actually come from?

Sources:
- The couch cart's flag snapshot: `dr-mario-reach-wt/tmp/carts/couch_tap2_se1.log`, md5 c960dd49, ANTIBODY_DIST
  couch.
- The driver: `dr-mario-dist-wt/patch_cartridge_copro.py`.
- The firmware emitter: `dr-mario-dist-wt/tests/test_search_d3.py`.
- reachbuild's endgame co-sim: `dr-mario-dist-wt/tmp/fwcosim_end`, 437 boards, ANTIBODY fw 77ec742c.
- The silicon first-move frames: `couch_forensics/cases_all_games.jsonl`, n = 384.
- The 10/03 couch per-frame tracks: `rawh_dist60_20261003_*`.
- The anytime replay: `steer7_anytime.py` → `steer7/anytime_10games.jsonl`, 1,961 boards; analysed in
  `steer7/anytime_analysis.txt`.

## 2.1 What "answer latency" is on silicon: mostly DRIVER constants, not search time

**Silicon first-lateral frame** (frame 0 = the preview change; 384 placements):

| placement | median | p10 / p90 | n |
|---|---|---|---|
| no rotation | **15** | 14 / 19 | 139 |
| one rotation | **22** | 17 / 26 | 215 |
| all | 19 | | 384 |

- 14 of the 384 placements (3.6%) are at **4–6 f**.
- On the TAP build the median is ≈ 18.

**Decomposition** (driver code + the couch flag snapshot):

| step | frames | what it is |
|---|---|---|
| preview change → driver new-pill edge | ≈ 1.5 | |
| **settle** | **7.5** | `DELAY2 = 15` hooks at the measured 2 hooks/frame. The code comment says "~3 frames settle": it was sized under the retired 5-hooks/frame assumption. Then GO. |
| **MIN_THINK** | **6** | 12 hooks (`DRMINTHINK=12` on the couch cart). No lateral or orient commit before GO + 6 f unless the search is DONE. |
| **total** | **= 15 f** | exactly the no-rotation mode |

- **One-rotation placements take +7 f (median 22).** One tap does not explain this. It is **unexplained**.
- **The 4–6 f answers are `DRPRESTART` hits.** That prestart is garbage-release only: the search ran during the
  garbage animation and finished before spawn.
- **The search's DONE arrives ~26 f AFTER the commit gate** (next section). So at the commit the driver acts on the
  copro's RUNNING BEST, not its answer.

## 2.2 The search: GO → DONE ≈ 32 f, but the answer is usually there by ~3 f

**GO → DONE:**
- 437 endgame boards (co-sim): **median 31.8 f** (p10 18, p90 42).
- 69 whole-game boards: 33.8 f.

**Leaves per search** (golden replay, 1,961 boards): **median 29.9k** (endgame 26.4k).

| phase | leaves | share |
|---|---|---|
| Pass 0 | 30 | 0.1% |
| ply-2 | ~900 | 3% |
| **ply-3** | **28.7k** | **96%** |

Ply-3 is ~30 roots × the top-8 ply-2 children × 4 pill classes × ~30 placements.

**Where the clocks go** (co-sim command counters, endgame median 45.5M clocks):

| share | cost | what |
|---|---|---|
| **63%** | ~20 f | CMD 7 DELTA leaves: 891 cycles each, ~31.7k per search |
| **16%** | ~5 f | CMD 4 NODE: per-root and per-ply-2 replays, plus the fallback for every CLEARING leaf (copy + NODE + copy). The fitted NODE cost is ≈ 3.7k cycles, link-aware. |
| **20%** | ~6.3 f | 6502 orchestration: ~240 clocks per engine command. It runs SERIALIZED with the engine, because the 6502 busy-polls GO. |
| ~3% | | BASE + slot copies |

All-in that is ≈ 1,400 (endgame) to 1,850 (whole game) clocks per leaf, at MiSTer 85.909 MHz.

**ANYTIME behaviour** (firmware order replayed exactly: Pass-0 key ranking, live publish on a strictly better root):

| | all decisions | endgame (1–4 viruses) |
|---|---|---|
| first publish | GO + 1.3 f | GO + 1.3 f |
| **final answer first published** | **median GO + 2.6 f** (p75 9.1, p90 16.9) | 3.9 / 10.4 / 19.3 |
| final answer's position in the processing order | median 2nd root, p90 13th | |
| **running best == final at the couch gate (GO + 6 f)** | **65.8%** | **59.9%** |
| same ORIENT as final at the gate | 77.7% | 71.3% |
| running best == final at GO + 12.5 f | 84.2% | 80.5% |

**So a third of the decisions commit laterally, and lock the orient, toward a NON-final running best.** They then
refine or reverse. This is the "late flip" mechanism the 10/03 forensics blamed for G2's tap-out.

The sim's latency model is optimistic here: it acts on the FINAL answer at t_act.

## 2.3 The copro's idle windows (10/03 couch tracks, garbage-free placements)

| | lock → next spawn |
|---|---|
| **no-clear** placements (n = 136) | **1 f** (p90 7). No idle window. |
| **clearing** placements (n = 74) | **median 54 f**, p75 89. The copro is IDLE through the whole clear animation. |

Spawn → lock: median 71 f.

## 2.4 Candidate speedups (ranked by frames × reach ÷ risk)

| # | lever | frames | where | risk |
|---|---|---|---|---|
| 1 | **Cut the settle**: `DELAY2` 15 → ~3 hooks (one cart immediate) | **−6 f on every searched decision**. Or keep the action frame and spend the 6 f on search: P(final at the commit) 66 → 84%. | cart only, byte-patchable | **low–medium.** First RAM-trace (Mesen) when $0500 and $039A/$039B stop changing after the spawn edge. The settle exists because "preview/board can update a beat after spawn", and its ~3 f design intent became 7.5 f through the hook-rate error. |
| 2 | **Clear-window prestart**: GO at the LOCK of a clearing placement. Firmware resolves the locked capsule on the pre-clear board with the engine's own link-aware NODE, then searches. | **−12 to −19 f (→ ≈ the zero-latency ceiling) on ~35–40% of placements.** The 54 f median window exceeds the ~32 f search, so DONE before spawn and P(final) ≈ 100%. | firmware (root = resolve(board ⊕ locked pill)) + driver (GO at lock; DRPRESTART's ownership / one-step-ahead colour / bail machinery) | **medium–high.** The engine resolve must be ROM-exact including cascades. Bail on garbage arrival and on lock-while-armed. NMI budget (the prestart hook is already the largest spike). |
| 3 | **Overlap the 6502 with the engine**: double-buffered arg/result registers or a small command FIFO, so the 6502 prepares leaf n+1 while leaf n evaluates | **−20% of clocks ≈ −6 f on DONE.** P(final) at the fixed gate ~66 → ~72%. Also −6 f per endgame placement, because endgame slams wait for DONE (`DRSLAM_KEND=255`). | RTL (CoproDrMario control, not the LeafEval datapath) | **medium.** Fit/timing; the copro has thin slack. |
| 4 | **Root ordering — MEASURED offline** (`analyze_steer7_order.py`, same 1,961 boards): a two-pass search — ply-2 for every root first (+3% leaves, ≈ +1.2 f before the first deep root, conservatively not reused), then roots by a DEPTH-2 estimate instead of the ply-1 key | 0 f on DONE, but the FINAL answer is published much earlier: p75 GO + 9.1 → **2.5 f**, p90 16.9 → **6.4 f**. **P(final) at the couch gate (GO + 6 f): 65.8 → 89.0%** (endgame 59.9 → 84.2%). Equivalently, MIN_THINK 12 → 6 hooks (−3 f) still commits a final answer more often (75.5%) than today's gate does (65.8%) | firmware only (Pass-0 key = d2; TK1 holds 30 × 2-byte keys) | **low**: the argmax is unchanged (ties/jitter aside); only WHEN it is published moves. Gate it by replaying the emitted firmware's publish trajectory against this replay |
| 5 | **Ply-3 pruning**: topk2 8 → 4, or a ply-2-margin cut | ply-3 is 96% of leaves; topk2 = 4 ≈ −45% leaves ≈ **−14 f on DONE** | firmware only | **HIGH on quality** (topk1 pruning measured −21 pp clears). Needs a full brain A/B, not a latency-only change. |
| — | NOT recommended: MIN_THINK below 12 hooks | −4 f at 4 hooks | cart | P(final at GO + 2 f) ≈ 46%; the tempo rig measured 1.8–3.6% wrong-column at MT 3–6 |
| — | investigate the +7 f on one-rotation placements | up to −7 f on ~half of placements | driver | unknown mechanism: needs a driver trace first |

**Pricing:** multiply each lever's frames by the STEER7 worth-per-frame curve (`RESULT_STEER7.md`).

**Caveat on that conversion:** the sim curve prices the frame at which the FINAL answer is acted on.
- Levers that only move the action frame (1, done as −6 f) move that frame but keep the 66% final-at-commit rate.
- Levers that buy search time (1 done as "+18 pp final", 3, 4, 5) raise the final-at-commit rate, which the sim does
  not model.
- Lever 2 does both.
