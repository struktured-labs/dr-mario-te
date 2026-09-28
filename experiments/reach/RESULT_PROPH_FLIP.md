# PROPH 180° colour flips — driver investigation (2026-09-27, Claude). ANALYSIS + FIX PREP; nothing deployed

**Lead** (h16 `RESULT_COUCH_HSV.md`, `45010b5`): 180° flips (right cells, halves reversed) on PROPH pills, 4/41, vs
2/817 on other pills.

**Hypothesis under test:** the unified DRTAPP=2 press scheduler drops or defers the rotation press(es) that follow
PROPH's escape pulses, so the capsule locks with the wrong orientation parity.

## Verdict
1. **The scheduler hypothesis is NOT reproduced.**
   - Rotations after PROPH are never dropped.
   - The only deferral is the dial's released frame: a rotation press can come no sooner than 2 frames after the last
     pulse (C3, by design).
   - With the answer published ≥ 6 frames before lock, the orientation error on PROPH pills is 0.17–0.34% under TAP and
     0.28–0.51% under DAS: **DAS is no better**.
   - Every traced residual is a rotation the WORLD refused: the capsule escaped into a side pocket where it cannot
     rotate, and the driver kept re-pressing at 1 press / 2 frames.
   - "A blocked press still consumes its slot" is faithful to a physical pad, and costs one retry period.
   - ROT_DONE2 / RELATCH after PROPH behave as designed: the edge clears ROT_DONE2, the first valid answer is adopted,
     the rotation fires in the next press slot, and changed answers re-open the latch while the capsule is above
     CROSS_LOWY.
2. **The silicon flips look like copro-vs-sim colour-order disagreement, not driver execution.**
   - In the video trajectories (tmp/couch_forensics raw_t27_G3), all 3 G3 flips (k81/86/88) track SEVERAL target
     changes:
     - k81: H → H-reversed → H → V (5 rotations);
     - k86: H → H-reversed → V;
     - k88: a single rotation, the other V colour order.
   - k81 then RESTED at its final pose for about 15 frames, with the RELATCH/RECOMMIT window open (Y ≥ 8). Any
     different published orient would have been rotated to.
   - So silicon landed on the copro's latest answer. That answer's colour order differs from the converged sim brain,
     which fits the anytime answer churning in the crowded ledge board.
   - None of the 4 follows a Y=$0F lock, so the bug below is not their cause.
   - Settling this for certain needs a copro-side answer trace on silicon, a mailbox logger like DRSEATLOG.
3. **A REAL latent driver bug in the same regime was found and fixed (behind a new flag): `DRSPAWNEDGE`.**
   - **The bug:**
     - The P2 new-pill edge is `$0386 (fallingPillY) increased`.
     - Per the Nostaljipi disassembly, the ROM writes fallingPillY only in gravity (dec/inc) and in generateNextPill
       at the spawn (`lda #$0F`).
     - So a capsule that LOCKS at Y=$0F leaves Y at $0F, and the next spawn's edge is **missed**. That is a horizontal
       pill in the top row off the spawn cells, or a vertical pill whose bottom half is in the top row.
     - The missed pill gets no search, no PROPH trigger, and a still-latched ROT_DONE2. It is steered to the PREVIOUS
       pill's target without rotating.
     - In the ledge regime a missed pill that locks at the spawn row misses the next edge too: runs of up to 6 in the
       harness, a death spiral.
     - DRCOLDINIT fixed the same family only at MATCH boundaries.
   - **How often it shows on silicon:** 1 top-row horizontal lock in 858 placements (9/26 + 9/27), and that one was
     the top-out itself. It is latent, not the cause of the recorded flips or deaths.

## Harness
`orient_harness.py`:
- It is `gate_tap_interface.py`'s closed loop: the real emitted driver under py65, ROM getInputs semantics, a
  ROM-rule world, and an emulated copro.
- It forces throat/ledge boards (50%) and copro answer flips (60%).
- Each lock is scored against the target the driver was actually given.
- It counts new-pill edge FIRINGS by watching the new-pill block's `STA DELAY2 <- 15`.
- It models each board reset as a ROUND START: level init adds 2 to the counter and sets Y=$0F with no live capsule,
  then the throw.
- Two world fixes were made for fidelity, and are also applied to `gate_tap_interface.py`:
  - the pill counter now increments at SPAWN (it was at lock);
  - p2_nextAction ($0397) is published.

Summary: 4 seeds × 60k frames per arm (`tmp/orient/FINAL_SUMMARY.txt`, `analyze_orient.py`).

| arm | missed edges | flip180, PROPH (% of pills / % of right-col locks) | flip180, other | orient err, answer ≥ 6 f before lock (PROPH / other) |
|---|---|---|---|---|
| TAP, fix off | 900 / 5194 (17.3%) | 1.66% / 6.3% | 0.44% / 0.7% | 0.34% / 0.15% |
| **TAP, DRSPAWNEDGE=1** | **0** | **0.62% / 2.6%** | 0.31% / 0.5% | 0.17% / 0.10% |
| DAS, fix off | 817 / 5044 | 1.21% / 4.9% | 0.52% / 1.1% | 0.51% / 0.09% |
| DAS, DRSPAWNEDGE=1 | 0 | 0.63% / 2.6% | 0.19% / 0.4% | 0.28% / 0.00% |

The residual flips are capsules that locked before any answer, or before the second rotation. At the ledge, lock
comes about 6 frames after spawn, so there is no time. This is interface-bound, not a driver defect.

## The fix: `DRSPAWNEDGE=1` (default 0, byte-identical)
When Y is UNCHANGED at $0F, the fix falls back to the ROM's per-spawn counter `$03A7` (p2_pillsCounter). The same
generateNextPill call that writes Y=$0F increments it, so a change means a new pill.

That fallback fires ONLY if a capsule has FALLEN since the last edge:
- `FELL2`, latched from p2_nextAction `$0397` == pillFalling `$00`.
- This excludes the ROUND START. Level init already leaves Y=$0F, so the stock test fires a pre-throw edge, and the
  throw's counter bump must not fire a second one.

Every other hook takes the stock Y test, so the fix can only ADD edges, and only in the one ambiguous state.

RAM: `LASTPC2 $61D4`, `FELL2 $61D5` (PRG_RAM_MAP regenerated: 0 collisions).

## Gates (all PASS)
- **Identity, fix off** (`build_spawnedge_carts.sh`): couch == **198a95e3**, CvC == **33062615** (the staged TAP carts).
- **`gate_spawnedge.py`** (3 seeds × 40k frames):
  - **off:** the defect is exercised. 438 pills get NO edge, and 438/438 follow a Y=$0F lock.
  - **on:** exactly one edge for every pill, 2605/2605, round starts included.
  - **Mutants killed:**
    - `nostore` (LASTPC2 never written): 2296 pills with > 1 edge;
    - `nofell` (no FELL2 test): 165 double edges at round starts.
- **Interface compliance** (`gate_tap_interface.py --overlay DRSPAWNEDGE=1`): **0 violations**, couch and CvC, 4 seeds ×
  70k frames each. `everyframe` mutant KILLED on both. Details: `tmp/tapgate/GATE_TAP_INTERFACE_SPAWNEDGE.txt`.
- **NMI census:**
  - couch: 14/14 OK. Spawn-edge hook 15,308 → 15,362 (+54). Worst admissible frame 27,452 → 27,550 of 29,780 (margin
    2,230).
  - CvC: +42 cycles on paths no certification section covers (as before).
- **Cart hazard gates** (`tools/gate/run_cart_gates.sh`): ALL PASS. `derive_prg_ram_map.py --check` OK.

## Candidate carts (NOT deployed)
They are built under `tmp/carts/` and pair with the unchanged firmware and RTL, e.g. the HSV rbf 6b73907c.

| cart | md5 |
|---|---|
| couch TAP + DRSPAWNEDGE | `c960dd499e877f01c483af1347ed8df6` |
| CvC TAP + DRSPAWNEDGE | `3b8737a939c19b1d592218f79bbf869c` |

- Recipe: the TAP recipes + `DRSPAWNEDGE=1` (`build_spawnedge_carts.sh`).
- **Before shipping,** confirm the ROUND-START assumption on the real ROM: level init leaves Y=$0F before the first
  throw, and no capsule falls in between. Use a Mesen run that counts DELAY2←15 writes per pill across 2+ round
  boundaries; expect exactly 1. The py65 world models the listing; it is not the ROM.

## Banked files
- `GATE_SPAWNEDGE.txt`, `GATE_TAP_INTERFACE_SPAWNEDGE.txt`, `NMI_CENSUS_SPAWNEDGE.txt`: the gate outputs.
- `ORIENT_HARNESS_SUMMARY.txt`: the table above.
- `cases_ample_time_orient_errors_t2.json`: the 6 traced TAP orientation errors that had ≥ 6 frames of answer. All are
  rotations refused by the world in the escape pocket.
  - Captured before the two world-fidelity fixes (the counter at spawn, and round starts). Neither fix touches
    rotation physics.

## Mesen round-start check on the REAL cart (2026-09-28): PASS
The flagged assumption is now checked on the real ROM:
- **Setup:**
  - The CvC TAP carts: fix off 33062615, fix on 3b8737a9. Their headers are remapped 100 → 1 (MMC1), so the PRG is
    byte-identical.
  - They ran in headless Mesen: P1 is the native AI, and `tools/copro_emu.lua` answers the P2 mailbox. Input is zero;
    the cart's own autonav plays VS rounds and rematches.
  - 30,000 frames per cart, 57 level inits (round starts) and 18 match restarts through the menu.
- **Counting:** `experiments/reach/mesen_spawnedge_probe.lua` counts new-pill edges from the block's own
  `STA DELAY2 <- 15`.
  - handle()'s `DEC DELAY2` in the same hook does a 6502 read-modify-write dummy write of 15. The probe discounts it.
  - `analyze_mesen_spawnedge.py` attributes the edges to live pills (p2_nextAction == 0).
- **How the lock was forced:**
  - The driver itself refuses a zero-fall landing, because DRDISTGATE clamps it.
  - So cols 0–1 are filled from row 1 and the capsule is TELEPORTED to X=0 at Y=$0F at its spawn. It locks at Y=$0F
    off the spawn cells, 3 times per run.

| cart | round-start pills: edges each | their edge timing vs going live | all pills | pill after a forced Y=$0F lock |
|---|---|---|---|---|
| fix off (33062615) | 56 × **1** | −2 f ×53, −3 f ×3 (pre-throw) | 270 × 1 + **3 × 0** | **0, 0, 0 (MISSED — defect on the real ROM)** |
| fix on (3b8737a9) | 57 × **1** | −2 f ×54, −3 f ×3 (identical) | **272 × 1** | **1, 1, 1** (at the spawn) |

- Round starts are UNCHANGED by the fix: same count and same pre-throw timing.
  - Between rounds the cart passes through non-play modes, so DRCOLDINIT's per-match cold init also re-runs per round.
    That zeroes LASTY2, and the stock Y test fires at the first play hook.
  - FELL2 then suppresses the throw's counter bump, exactly as designed.
- Files:
  - `MESEN_SPAWNEDGE_RESULT.txt`;
  - `mesen_logs/spawnedge_cvc_se{0,1}.txt` — `E`=edge, `S`=state change, `F*`=forced lock.
