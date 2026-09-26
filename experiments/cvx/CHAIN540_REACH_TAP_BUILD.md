# CHAIN540 + REACH + TAP core and carts — build record (2026-09-25, Claude)

**Why:** owner ruling (memory `owner-ruling-superhuman-input-rate`): the AI may steer at superhuman tap rates up to,
but never beyond, the controller-interface limit. The game samples the pad once per frame and a press edge needs a
released frame before it, so the ceiling is 1 press per 2 frames. Ships as a DIAL whose default is the ceiling.
STEER1's pulse arm (−23.8 pp tap-out) was the ceiling of steering speed; STEER3 (steersim) sweeps the rate.

## Artifacts (staged `dr_mario_rl/tmp/rtl_chain/ship/chain540-reach-tap/`, NOT deployed)
| artifact | md5 | recipe |
|---|---|---|
| firmware hex | `77ec742cf0446b49a7f363b34c522864` | reach-wt `experiments/reach/build_fw.py 540 <out> 1 1` (CHAIN540 + DRREACH=1 + DRREACHTAP=1) |
| **rbf** `NES_childproof_chain540_reach_tap_20260925.rbf` | `77b521b2aa4ecf5bb61b688edce9cb5f` | `chain540_reach_tap_build.sh`: RTL 08f2343 + Childproof `NES.qsf.used`, SEED 13 |
| **couch TE cart** | `198a95e3d5f0ce5b671c1b8d02af54ce` | couch recipe (CHAIN540_REACH_BUILD.md) + `DRNMITMP=1 DRREACHTX=1 DRTAPP=2` |
| **CvC soak cart** | `33062615a9b76fb9233445daa7899caa` | cvc_tg1_L20 flag snapshot + `DRNMITMP=1 DRREACHTX=1 DRTAPP=2` |

Builders: `~/projects/dr-mario-reach-wt`, branch `reach-root` @ `826f4e0`.

## rbf gates (seed 13, 19:49-20:08 local)
- **SHIP AS-IS:**
  - ALMs **37,664** (4,246 free).
  - **copro slack +0.127 ns** (bar +0.10; identical to REACH).
  - pll_hdmi +0.140.
  - The rbf is unique across 22 archived builds.
- **FW-in-image:** PERFECT BIJECTION 16/16 == 77ec742c. The REACH firmware control covers 8/16: the high-half slices
  (the $A800 routine) differ.
- Fork restored (HEAD 18cf064, hex f78f1e93, qsf 701f6962, rtl clean).

## Pairing
| cart | rbf | behaviour |
|---|---|---|
| DRTAPP=2 + DRREACHTX (198a95e3 / 33062615) | **this rbf** | tap driver + tap-model reach mask (the intended build) |
| DRREACHTX only (09cdb6ae / 2291a61d) | this rbf | DAS driver + DAS-model mask; the firmware reads P=0 |
| DRTAPP=2 + DRREACHTX | REACH rbf 55caf0a3 | tap driver, DAS-model mask: over-masks (conservative), safe |
| no DRREACHTX | any reach rbf | no filter (today's search) |

P rides the nA/nB colour LOW-nibble bits 2-3. Every firmware read of those bytes ends in the engine colour args,
and the RTL keeps DO[1:0], so the bits are dead to every search, old or new.

## Gates (reach-wt `experiments/reach/`, details in its README "DRTAPP" section)
- **Identity (dial off):**
  - Carts: 08211ef4 / 9f20c795 / 2291a61d / 4b4fce5e / 09cdb6ae byte-exact.
  - Firmware: DRREACHTAP=0 gives d8014d77; DRREACH=0 gives 6d13e6a1.
- **G2 mask bit-exact (tap routine):** 0 mismatches at P=0/2/3 × 404,536 checks. Mutants killed: T_LAT±1,
  DISTGATE off, fallback off, rot_das.
- **G1/G3 whole search (tap fw):** 102/102 + 102/102; 243/243 == masked golden mirror. Static S_NA/S_NB audit;
  PENALTY and NOAND mutants killed.
- **INTERFACE COMPLIANCE (new, mandatory):** the real emitted driver under py65, closed-loop, two hook passes per
  frame, ROM getInputs semantics.
  - Couch P=2 (3 seeds), couch P=3 (2), CvC P=2 (2): **0 violations / 280,000 frames**. That covers no
    manufactured edge, never a press on consecutive frames, and spacing ≥ P. The minimum gap equals P.
  - **`everyframe` mutant KILLED** on both carts.
  - ⚠ **Today's shipped DAS driver fails this gate:** its rotation forces held := 0 and manufactures an A/B press
    every frame (≈1,600-1,800 violations per 40k frames). Lateral DAS is compliant. DRTAPP fixes it.
- **Transport:** py65 nibble code round-trips thr and P for all speeds; sites couch ×2, CvC ×1.
- **Cart hazard gates:** ALL PASS. **PRG RAM map** regenerated: no collisions; TAP state at $61D0-$61D3.
- **NMI census:** couch tap 14/14 OK (worst spawn edge 15,308; same-frame pair 27,872 < 29,780). CvC +79..+155
  cycles.

## Timing notes for STEER3 (align the sim to this driver)
1. ONE press scheduler shared by rotation, lateral and PROPH: the next press of ANY button comes no sooner than P
   frames after the last one.
2. Rotation taps at P. The current DAS driver rotates 1/frame (the manufactured edge).
3. PROPH: the first press is on the detect frame (F0=3), then every P. The first answer press is at
   max(T_LAT, last PROPH press + P).
4. The first lateral press is P after the last rotation press (or the first free slot), then every P. No DAS.
5. A blocked rotation or lateral press still spends its slot.
6. DISTGATE budget is 2P hooks/column. At P=2 it clamps only at y=0, the same zero condition the mask models.
7. The tap-capable `reach_fw.py` (tap=P; tap=None unchanged) lives in reach-wt `experiments/reach/reach_fw.py`.
   h16-wt's copy was left untouched because steersim may be importing it live.

## Not done here
- Bluemage cadence check (save-state frame clocks), soak, rivalmage deployment: coordinator / owner.
