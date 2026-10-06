# RESULT (execfid lane, 2026-10-04): two fair-cart decision defects behind the 10/04 couch hybrids

The full forensics write-up (the 18-frame "gap", per-game tables) is in dr-mario-rl h16 `experiments/execfid/
RESULT_EXECFID_20261004.md`. This file covers the cart side: the defects, the flags, the gates and the replays.

## 1. DRLGPRESTART (new, default 0): garbage-window PRESTART answers were dropped by DRLATEGUARD

**Defect:** DRLATEGUARD keeps two latches per pill, LG_CMT2 (committed) and LG_LOCK2 (frozen). They are reset only at
the next spawn edge. A DRPRESTART search, though, runs during the garbage window for the NEXT capsule, while those latches
still describe the capsule that just LOCKED. The failure runs:
1. `lg_gate` prices the prestart's first publication against the locked capsule. Its own cells now fill the
   "current row", so the move is unfinishable, and the gate FREEZES.
2. At DONE the answer is dropped.
3. The spawn edge is prestart-owned (no PEND2), so no new search starts.
4. The new capsule executes the PREVIOUS pill's (column, orientation) with DONE semantics: tap at f1, slam at f4.

**Evidence:**
- **Silicon, 10/04:** after a garbage window, the AI executed the previous pill's target on 17/40 FAIR (dbbb5007)
  pills and 11/32 FAIR2 (b1b57638) pills. Other pills show the same pattern at about 1.2%. The 10/03 cart, which has
  no LATEGUARD, shows 0/19.
- **M4 G2:** the defect hit p7, p13, p55, p77 and p84, the knife-edge pill before the AI's tap-out.
- **Mesen, real carts:** a chained replay with the silicon volleys delivered through the ROM's own path (P2's incoming
  attack `$0318` / `$0329`, `tools/execfid/execfid_probe.lua` `garb=`). It reproduces the silicon landings frame for
  frame (+1 f video offset). Trace in the `W` lines: `lgc=1`, then `lgl=1` at the prestart's first publication.
- **py65:** `tests/test_lgprestart.py`, counts summed over 4 seeds × 6000 frames:
  - the shipped flag sets DROP prestart answers: D 12/18, A 16/25 (defect reproduced);
  - +DRLGPRESTART drops 0 while LATEGUARD still refuses falling capsules (D 4, A 20);
  - `lg_cmt=1 lg_lock=1 na=1` at every drop.

**Fix:** `lg_gate` adopts while `PRE_ACT2 != 0`. A prestart answer belongs to a capsule that has not committed anything;
this is the pre-LATEGUARD (10/03) behaviour.
- Size and effect: +7 bytes, a pure decision change, no pad / timing / gravity effect.
- After the spawn PRE_ACT2 is 0 and LATEGUARD gates the falling capsule as before.
- The CvC carts have DRPRESTART=0, so the defect cannot occur there.

## 2. DRDISTROW=2 (new value of the settle lane's flag): all-or-nothing current-row credit

**Defect (M4 G2 p107, PROPH-armed ledge):** the slam gate `dn_p2` reads DISTGATE's clamped target `EFF_DIST2` as
"aligned".
- The answer (H col 0) is DONE at f4 with the capsule at col 2 on its spawn row.
- No row below the span is empty, so the budget is 0 and EFF = col 2. `dn_p2` then slams at f5: lock at col 2, the
  silicon landing.
- 5 frames were left before the gravity tick: enough for the 2 taps to col 0.

**DRDISTROW=1** (settle lane's B, unchanged, byte-identical: 78bc8e75 = `couch_fair_DB`) credits
`min(7, (thr - $0392) / 2)` columns. That fixes p107. It also lets a capsule start a PARTIAL move toward a target it
cannot finish: 10/03 G2 p101 on D, a late 5-column tuck answer with 1 tap of frames left, lands one column over, a new
hybrid.

**DRDISTROW=2** applies the credit only when it covers the whole `|target - X|`; otherwise the budget stays 0 exactly as
without the flag. Results:
- p107 lands on the copro final.
- 10/03 p101 stays on its earlier answer.
- Identical to =1 everywhere else measured.

## 3. Replays (Mesen, real carts, co-sim timelines of the shipped RTL + fw, CHAINED, silicon garbage delivered)

A hybrid is a straight drop on no published candidate.

Each cell is landing == silicon / == copro final / hybrid.

| build (games) | base cart | + DRLGPRESTART | + DRDISTROW=2 | + both |
|---|---|---|---|---|
| FAIR, dbbb5007 + 1488 (10/04 M1 G1-2, M3 G1-3, M5 G2; 573 pills) | 483 / 512 / **24** | 476 / 538 / **0** | 483 / 512 / 24 | 476 / **539** / **0** |
| FAIR2, b1b57638 + V11 (10/04 M2 G1-3, M4 G1-2; 508 pills) | 431 / 461 / **21** | 426 / 478 / 4 | 430 / 465 / 17 | 426 / **482** / **0** |
| 10/03 G2 boards, D + 1488 (116) | 94 / 98 / 3 | 96 / 100 / 1 | 94 / 98 / 3 | 96 / 100 / 1 |
| 10/03 G2 boards, A + V1 (116) | 89 / 110 / 4 | 91 / 113 / 1 | 90 / 111 / 3 | 92 / **114** / **0** |

- "== silicon" drops with the fixes because silicon had the defects.
- Of the 28 silicon previous-target pills, the base-cart replay reproduces 21 frame-exact, and DRLGPRESTART lands the
  copro final on 27.
- DRDISTROW=2 changes 4 FAIR2 pills (M4 G2 p107/p108, M2 G2 p22/p82, all to the final) and no FAIR pill. On the 10/03 A
  + V1 tall endgame it fixes the 2 PROPH ledge clamp-slams (p101, p115).
- Per game: dr-mario-rl h16 `experiments/execfid/report_20261004.txt`.

## 4. Gates (`experiments/execfid/GATES.txt`, `tools/execfid/gates_final.sh`)

| gate | result |
|---|---|
| negative controls (`tools/execfid/build_carts.sh`) | flags unset AND =0 rebuild dbbb5007, b1b57638, 464a4b75 and CvC 821cafdb byte-identically; DRDISTROW=1 still = 78bc8e75 (= settle lane `couch_fair_DB`) and 45e3fe7c |
| `tools/gate/run_cart_gates.sh` | ALL PASS (7 suites, incl. gravity-fidelity over every arm incl. the new ones) |
| gravity-fidelity, D / D_abort / D+LGP / A+LGP / A+ROW2 / D+LGP+ROW2 / A+LGP+ROW2, seeds 5/11/23 × 6000 f | all PASS; 464a4b75 KILLED (pin detected) on every seed |
| `tests/test_lgprestart.py` (defect gate, 4 seeds × 6000 f, summed) | D 12/18 and A 16/25 prestart answers dropped (DEFECT REPRODUCED); every +DRLGPRESTART arm 0 dropped, with LATEGUARD still refusing falling capsules (4-20) |
| `tests/test_lateguard_census_cut.py`, A/D + LGP + ROW2 | GATE_LGCUT PASS (5 mutants killed) |
| static NMI census, worst admissible frame / 29,780 | D 27,752; A 27,823; +LGP unchanged (27,751 / 27,823); A+ROW2 = A+LGP+ROW2 28,001 (margin 1,779); D+LGP+ROW2 27,929 |
| TAP interface (P=2, 40k frames) | A+LGP+ROW2 PASS, D+LGP+ROW2 PASS; the `everyframe` mutant KILLED |

**Gate change:** `tests/test_gravity_fidelity.py`'s dead-pill counter falsely failed `couch_fair_A_row2` at seed 5.
- The flagged "dead-pill upload" was a DRPRESTART GO for the NEXT capsule whose capsule + preview colours collided
  with the locked pill's (2,0,2,0). The diagnosis: `PRE_ACT2` goes 0→1 in the GO's frame; the old check read it before
  the store.
- Prestart GOs are now identified that way and counted separately (`prestart_gos_colour_collision`).
- The counter stays alive: the non-abort D arm still counts its real stale re-uploads (2 at seeds 5 and 23).

## Files
- `patch_cartridge_copro.py`: the `DRLGPRESTART` flag block (after PRE_ATK2) and in `lg_gate`; `DRDISTROW=2` /
  `DISTROW_FULL` in the DISTGATE row-credit block.
- `tests/test_lgprestart.py` (new defect gate); `tests/test_gravity_fidelity.py` (new arms + the dead-pill
  counter fix).
- `tools/execfid/`:
  - `build_carts.sh`: negative controls + candidates;
  - `gates_final.sh`;
  - `execfid_probe.lua` + `run_probe.sh` + `gen_cases_garb.py`: the chained replay with garbage delivery, no
    wall-clock deadline;
  - `cmp_runs.py`.
