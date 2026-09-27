# CHAIN540 + REACH core and carts — build record (2026-09-25, Claude; STEER2 passed its pre-registered bar)

**Why:** under the steering-faithful simulator (RESULT_STEER1/STEER2), a root that only aims where the couch driver
can land the pill:
- cuts couch-like early tap-outs from 28.8% to 9.8% (−19.0 pp [−22.7, −15.3]);
- wins more races: +17.0 pp [+12.0, +22.3] vs a 177-s human.

Pair it with DRCHAIN 540 (the pre-registered rule keeps the incumbent).

## ⚠ PAIRING RULE — the filter is live ONLY with BOTH halves
| cart | firmware | behaviour |
|---|---|---|
| DRREACHTX=1 | DRREACH=1 | **reach-filtered root** (the intended build) |
| DRREACHTX=1 | old (CHAIN540 / Childproof) | today's search: the old firmware masks the nibbles (gate G1a) |
| old cart | DRREACH=1 | today's search: NB high nibble 0 → no filter (gate G1b) |

Always deploy the pair below together. Mixing is safe but silently turns the feature off.

## Artifacts (staged `dr_mario_rl/tmp/rtl_chain/ship/chain540-reach/`, NOT deployed)
| artifact | md5 | recipe |
|---|---|---|
| firmware hex | `d8014d77a453780fc8f6d230c07cc617` | reach-wt `experiments/reach/build_fw.py 540 <out> 1` (CHAIN540 recipe + DRREACH=1) |
| **rbf** `NES_childproof_chain540_reach_20260925.rbf` | `55caf0a3185707a432e298846ec5dc52` | `chain540_reach_build.sh`: RTL 08f2343 + Childproof `NES.qsf.used`, SEED 13, fw above |
| **couch TE cart** | `09cdb6ae8aaba19f5c8464cdcb70a4b5` | couch recipe (below) + `DRNMITMP=1 DRREACHTX=1` |
| **CvC soak cart** | `2291a61dd110e9da8caa72837145ed07` | cvc_tg1_L20 flag snapshot + `DRNMITMP=1 DRREACHTX=1` |

Builders: `~/projects/dr-mario-reach-wt`, branch `reach-root` @ `b04a130` (= drveto 0140db3 + DRREACH/DRREACHTX).
- **Couch:** from reach-wt, `env $(cat h16-wt/tmp/flags_b_control.env) DRSTUDY=1 DRSTUDY2P=1 DRSTUDY2P_INV=1
  DRSTUDYCOUNTS=1 TE_FOOTER=0 DRSTUDY_Y=0x98 DRNMITMP=1 DRREACHTX=1 TE_DIR=~/projects/dr-mario-te-v8.2
  python ~/projects/dr-mario-te-v8.2/build_copro_branded_env.py drmario_v28cs.nes <out>`.
  With `DRREACHTX=0` the same line reproduces **4b4fce5e** (the staged freeze-fixed couch cart) byte-exact.
- **CvC:** from reach-wt, `env <every key of the ##DRFLAGSNAPSHOT## in tempo-wt tmp/tuckguard/b_cvc_tg1_L20.log>
  DRNMITMP=1 DRREACHTX=1 python patch_cartridge_copro.py` (it writes `drmario_copro_L20s1.nes`).
  Without the two extra flags this reproduces **08211ef4** byte-exact; with `DRNMITMP=1` only, **9f20c795**.

## Gates (reach-wt `experiments/reach/`, all PASS)
- **G0 identity:** DRREACH=0 gives the CHAIN540 hex 6d13e6a1 (and Childproof a2b2e4ac at 180). DRREACHTX=0 gives
  couch 4b4fce5e and CvC 9f20c795.
- **G2, 6502 mask = `reach_fw.py`** (py65):
  - 7,412 boards (1,412 real L11/L15 couch-steering game boards + 6,000 synthetic), 404,536 legal-candidate
    checks under both empty encodings: 0 mismatches.
  - Transport decode 150/150.
  - Mutants T_LAT±1 / DISTGATE-off / fallback-off killed.
  - The gate caught one real port bug before passing: the DISTGATE span must use the CURRENT column each step.
- **G1a:** random nibbles are inert under DRREACH=0, 120/120, with every colour-arg write < 16. **G1b:** old cart
  plus DRREACH=1 equals today's search, 120/120.
- **G3:** whole search (py65 engine emu, ship recipe) equals the verbatim golden mirror with the reach mask,
  240/240. Boards were real game boards at their own and at fast gravity, plus fewlegal. The filter moved the
  argmax on 51.
- **Mutant kills:** PENALTY (−20000 at o_cand instead of the skip) is killed on a synthesized masked-winner
  board. NOAND (a missed AND #$0F) is killed.
- **Static audit:** all 8 S_NA/S_NB reads in search/tuck/stub are `LDA; AND #$0F`. The reach routine does exactly
  its 2 decode reads. The shipped RTL takes colour args as DO[1:0] anyway.
- **Cart transport:** the py65 nibble code equals `pack_nibbles` for all (speed, speedUps); the NB high nibble is
  never 0. Opcode-level diff vs the DRREACHTX=0 cart = exactly the inserted runs (couch 2 sites, +96 B; CvC 1 site,
  +48 B).
- **Cart hazard gates:** ALL PASS.
- **NMI census:**
  - Couch: 14/14 OK; worst spawn edge 15,156 → 15,234 cycles; same-frame pair 27,728 < 29,780.
  - CvC: bounds +71 cycles; no certification section applies to it.

## rbf gates (Quartus 23.1std, seed 13, 17:21-17:40 local)
- **ship_build verdict SHIP AS-IS.**
  - ALMs **37,664** / 41,910 (4,246 free) — identical to CHAIN540.
  - **copro slack +0.127 ns** (bar +0.10) PASS.
  - **pll_hdmi +0.140 ns** (baseline −0.012) PASS.
  - The rbf is unique across 21 archived builds.
- ⚠ **The placement did NOT reproduce CHAIN540's +0.165 / +0.381.** CHAIN540 changed 1 ROM byte; this build changes
  ~1.5 KB of copro ROM content (the $A800 routine plus the shifted search). It still clears the bar, with a
  0.027 ns copro margin. Per [[leaf-has-no-timing-budget]], one fit is n=1: soak before trusting.
- **FW-in-image proof** (`chain540_reach_eda_proof.sh`: `quartus_eda --format=verilog` on the compiled db, with the
  fork in the build's state): **PERFECT BIJECTION 16/16 slices == d8014d77**. The control fw540 matches 0/16.
- The original build script ran EDA without `--format=verilog` (rc=3). The script is now fixed, and the proof was
  re-run separately from the same compiled db.
- Fork restored after both steps: HEAD 18cf064, hex f78f1e93, qsf 701f6962, rtl clean.

## Deviations from the STEER2 spec
0. The rbf timing is not a bit-for-bit placement reproduction of CHAIN540 (see above); it passes the ship bar.
1. **Speed is sent as speed+1** in NB bits 2-3, so a transport cart never sends NB high = 0. That is how the firmware
   distinguishes an old cart (→ no filter).
2. **Frames are 16-bit, not saturated.** A deep narrow well at LOW speed can keep rotation retrying past frame 255.
3. **Pass-0 fallback:** the unfiltered rerun is a safety net on top of reach_fw's own any() fallback. It is
   equivalent when legality agrees, which G3 checks.

## Not done here (owner / next steps)
- The bluemage soak of the new pair: the CvC cart above + the new rbf. The coordinating session switches the soak.
- rivalmage deployment: the owner's box, owner's call.
- A couch check with steering-model predictions.
