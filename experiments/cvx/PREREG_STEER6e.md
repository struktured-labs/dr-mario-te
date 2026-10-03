# PREREG (2026-10-03): STEER6e — "comboing instead of clearing" endgame fix screen on ANTIBODY_DIST

Written and committed BEFORE any STEER6e screen game. Only the identity smoke (2 seeds, 37934/37936, rows
byte-identical to the banked STEER6 screen rows) and the wiring guard have run.

## Why (couch forensics, `couch_forensics/RESULT_COUCH_DIST60.md`, cases `cases_*dist60_20261003.jsonl`)
- 10/03 couch, owner vs ANTIBODY_DIST: the owner said the bot "was comboing more than deliberately clearing".
- Replaying the couch endgame decisions through the sim brain:
  - When a root move existed that FINISHED the DIST target, DIST60 declined it on **5/14 (10/03)** and **27/49
    (prior ANTIBODY couch endgames)** positions.
  - The chosen move vs the best finishing move, PV term decomposition (mean, 10/03): CHAIN +256, root EXCAV/HANG
    +96, base LEAF +77, against VIR −153 and DIST −42.
  - EXCAV pays min(run,3)² × 24 = **+96 for leaving a same-colour 2-stack on a virus**. That is exactly the D = 1
    vertical-finish position, so it is a built-in anti-finish term.
- Offline, on the same banked couch positions, finishing-move take rate:

  | variant | 10/03 | prior |
  |---|---|---|
  | DIST60 | 9/14 | 22/49 |
  | chain0@≤4 | 9/14 | 22/49 |
  | exh0+chain0@≤4 | 13/14 | 34/49 |

  These are position-level counts, not outcomes. This screen tests outcomes.

## Arms (`steer6e_run.py`; every gate keys off the ROOT virus count, firmware-side, like DIST's own)
- **s6e_chain0:** ANTIBODY_DIST (`s6_dist_target60`) with w_chain 540 → 0 while root viruses ≤ 4. This is the owner's
  hypothesis.
- **s6e_fin:** the same, AND w_excav 24 → 0, w_hang 40 → 0 while root viruses ≤ 4. This is the measured mechanism.
- **s6_dist_target60 (identity):** re-run, because the new endgame-tempo fields need it. Its outcome fields must
  equal the banked STEER6 screen rows on all 600 seeds × 2 instruments. That is the exactness gate. Any mismatch
  voids the screen.

## Instruments and seeds (identical to the STEER6 screen)
- **Gate (b):** OWNER-0804, L11 MED, cap 600, unified DRTAPP=2 steering, stuck probe (`stuck_probe.play_gb`).
- **Race:** vs_race lam 6, unified tap steering, stuck probe; scored at M 177 δ 2.65 (and δ 2.0, reported).
- **Seeds:** 37934–39132 even, **600 paired**.
  - DECLARED REUSE. `seed_registry --check` says DO NOT USE: STEER5d / OPP1 / STEER6 screen.
  - Pairing against the STEER6 baseline requires this block, and the seed space is exhausted.
  - No STEER6e design choice used these seeds: the arms were shaped on couch boards only.
- **Execution:** local only, nice 19, ≤ 10 workers. Fresh NUMBA_CACHE_DIR per arm. The wiring guard (variant ≠
  DIST60 on the banked couch endgame boards; identity == DIST60 on all of them) runs at every job start.

## Endpoints (per arm vs the identity arm, paired, seed bootstrap 4,000, 95% CIs)
- **E1, endgame tempo (primary for the owner's complaint):** endgame pills = pills − k4, where k4 = the pill index
  of the first decision with root viruses ≤ 4. Measured in gate-(b) games that BOTH arms won (paired mean Δ).
- **E2:** race win at M 177 δ 2.65.
- **E3:** gate-(b) whole-game tap-out.

**PASS iff all three hold:**
1. E1 upper CI < 0 (faster endgames);
2. E2 lower CI ≥ −2 pp (race non-inferior);
3. E3 upper CI ≤ +2 pp (tap-out non-inferior).

**Reported, no gate:**
- Endgame stall-pills per game: board-level act-stalls ≥ 10 that start at ≤ 4 viruses, all games.
- Last-virus pills (k1 → clear, both won).
- Race endgame seconds (t_end − t4, both won).
- Tiles sent.
- tap≤100: must be IDENTICAL, because the gates are off above 4 viruses.
- Brain finishing-move take rate (fin_taken / fin_avail) and D-reducing take rate.
- Churn on tap-out (fixed / new) and race at δ 2.0.

**Multiplicity:** 2 arms. A PASS is a screen pass, not a ship. It needs a disjoint-seed holdout plus the opponent
suite (LULU race), and an RTL / firmware note:
- chain gating = whether DRCHAIN is a writable register;
- excav / hang = root-side firmware terms.

**Reading declared now:**
- If s6e_fin passes and s6e_chain0 does not, the owner's chain hypothesis is not sufficient: the root EXCAV term
  is part of the mechanism.
- If neither moves E1, finishing deferrals are not what makes sim endgames slow (colour waits and seals dominate),
  and the couch complaint is mostly the colour-wait / garbage-seal mechanism.
