# RESULT (pocketclk lane, 2026-10-13): what the Pocket's copro clock costs the FAIR2PLUS bot. SIM / EMULATOR ONLY

Question (Pocket revival plan, step 3): the Pocket core clocks the copro at **54.669 MHz** (mf_pllbase VCO 601.362942 / 11,
outclk_4; its copro Fmax is ~53-60 MHz, so 85.9 is out of reach), against **85.909 MHz** on MiSTer. What does that do to the
current MiSTer configuration: FAIR2PLUS cart 5a1695da, V11 firmware c51d2e21 (and A16 b545d740), LeafEval holes 80?
No Quartus, no hardware, no RTL/firmware/cart builds. Every cart used here was already built by the u8slam lane.

## Short answer
1. **The search is ~1.57x slower, and almost all of the cost is TEMPO, not placement.** On the real cart the Pocket clock
   locks every pill **+13.4 f later** [95 % game-cluster bootstrap +11.2, +15.1] (V11; A16 +13.5 {+11.3, +15.2}).
2. **Placement barely changes:** 14 of 1,197 pills (1.2 %) land somewhere else (12 / 1,197 on A16). Landing on a non-final
   published answer goes 4.3 % -> 5.3 % (V11) and 4.7 % -> 5.5 % (A16); 0 hybrids. LATEGUARD freezes 17 -> 27 pills.
   SLAM_ARM disarms 9.1 % -> 23.8 % of pills (the previous search is still running at the next spawn).
3. **In the STEER14 race model that tempo is expensive:** loss vs dr. lulu **+18.1 pp [+14.5, +21.8]** for V11 / FAIR2PLUS
   (31.8 % -> 49.9 %, n 1,000 paired seeds), **+28.6 pp [+25.1, +32.1]** for A16 (21.4 % -> 50.0 %). The extra losses are
   slow (race) losses; kills fall slightly. A16's advantage is wiped out on the Pocket.
4. **A Pocket-specific slam-gate retune buys most of the tempo back on the cart** (replays, V11): u8 (KOPEN 8 / KEND 8) on
   the Pocket clock is +3.6 f/pill vs MiSTer FAIR2PLUS [+1.3, +6.5], at a cost of 33 / 1,197 different landings
   (non-final 4.3 % -> 6.6 %). Its race-model price is in "Pending" below.
5. **Verdict:** a Pocket build of TODAY's MiSTer bot will play **identically in where it puts pills but clearly slower**,
   and in the model that is a large strength loss (~+18 pp loss vs dr. lulu). Reviving the Pocket is worth it only as a
   deliberately slower "travel" bot, or together with a Pocket-tuned slam gate (u8 class), and NOT as a like-for-like
   copy of the MiSTer bot.

## 1. Method
- **Clock model.** The copro is a free-running 6502 + LeafEval on its own clock, PPU-blind; the host only uploads the
  board, pulses GO (2FF sync) and polls the BRAM mailbox. The NES CPU/PPU (21.477 MHz master) is the same on both cores.
  So every copro event time since GO scales by K = 85.909088 / 54.669358 = **1.57143** (exactly 11/7).
  `tools/pocketclk/scale_cases.py` multiplies every publish time and `done_f` in the a16mt lane's case files
  (12 couch games, 1,197 pills, V11 and A16 Verilator co-sim timelines of the shipped RTL); answers, finals and tuck
  descriptors are untouched. Not modelled: the 2FF GO sync (+2 copro clocks) and the ~72-cycle stale-mailbox window,
  both well under a frame.
- **Replays** (`tools/pocketclk/replay_batch.sh`, = the u8slam harness, `execfid_probe.lua`): Mesen, real cart,
  chained, silicon garbage delivered, one Mesen at a time, nice 19 user units. The 85.9 MHz arm is the u8slam lane's
  banked FAIR2PLUS run of the same cases (that lane showed it reproduces the a16mt bank pill for pill). Analysis:
  `tools/u8slam/analyze.py` unchanged. Records: `REPLAYS_v11.txt`, `REPLAYS_a16.txt`, `REPLAYS_v11_retune.txt`,
  `pills_{v11,a16}.jsonl`.
- **Race model** (`tools/pocketclk/steer14_pocket.py`): STEER14 (`dr-mario-h16-wt` experiments/cvx, b18a251e, run
  read-only) with the ARM's publish schedule and DONE leaf term multiplied by K; today's-cart reference (fw 1488) is
  untouched, so the rows pair by seed with the banked MiSTer rows (`steer14/main`). The co-sim DONE residual eps is not
  scaled. **Identity control:** with K = 1 the wrapper reproduces the banked S14_d4_k32 rows 50/50 exactly. Seeds
  44300..46298 (first 1,000 of the STEER14 main block), LULU race at M 167.5, analyze_steer14's win rule and bootstrap.
  Record: `SIM_STEER14.txt`.

## 2. Replays (real cart, 1,197 pills)

| firmware | arm | ==final | non-final pub | hybrid | frozen | lock mean | GO->lock | disarmed |
|---|---|---|---|---|---|---|---|---|
| V11 | MiSTer 85.9 | 1,145 (95.66 %) | 52 | 0 | 17 | 41.8 f | 40.7 f | 9.1 % |
| V11 | Pocket 54.7 | 1,133 (94.65 %) | 64 | 0 | 27 | 55.1 f | 54.8 f | 23.8 % |
| A16 | MiSTer 85.9 | 1,141 (95.32 %) | 56 | 0 | 21 | 41.6 f | 40.6 f | 8.9 % |
| A16 | Pocket 54.7 | 1,131 (94.49 %) | 66 | 0 | 29 | 55.1 f | 54.8 f | 23.7 % |

- Paired lock-frame change, Pocket - MiSTer, V11: **+13.38 f** [t +12.35, +14.41] {cluster +11.24, +15.06}; >= 10 viruses
  +13.4, < 10 viruses +13.4 (endgame GO->lock 49 -> 63 f, the cart waits for DONE there).
- Landing class MiSTer -> Pocket (V11): final->final 1,132, final->pub 13, pub->final 1, pub->pub 51. The 14 moved pills
  are mostly tuck finals that only exist at DONE and late endgame finals that LATEGUARD now refuses.

## 3. Race model vs dr. lulu (n 1,000 paired seeds each)

| arm | MiSTer loss | Pocket loss | delta [95 %] | slow / kill MiSTer -> Pocket | GO->lock per pill |
|---|---|---|---|---|---|
| V11, FAIR2PLUS gate (S14_d4_k32) | 31.8 % | 49.9 % | **+18.1 [+14.5, +21.8]** | 220/98 -> 442/57 | 42.1 -> 55.9 f |
| A16, FAIR2PLUS gate (S14_d16_k32) | 21.4 % | 50.0 % | **+28.6 [+25.1, +32.1]** | 143/71 -> 441/59 | 43.5 -> 57.1 f |

- The model's GO->lock shift (+13.8 f) matches the cart replays (+13.4 f), which is the main check on the model's tempo.
- The model's endgame landed-on-final rate barely moves (96.7 -> 97.2 % V11): the loss is the race, not the play.
- On these seeds MiSTer's V11 loss (31.8 %) is above STEER14's full-block 24.4 %: a seed-subset effect, the contrast is paired.

## 4. Pocket retune of the slam gate (replays, V11, vs MiSTer FAIR2PLUS)

| Pocket cart | lock vs MiSTer f2p [cluster 95 %] | ==final | landings differing |
|---|---|---|---|
| FAIR2PLUS (KOPEN 32 / KEND 255) | +13.4 {+11.2, +15.1} | 1,133 | 14 |
| k8 (KOPEN 8) | +10.2 {+7.7, +12.3} | 1,125 | 24 |
| e8 (KEND 8) | +6.8 {+4.3, +10.3} | 1,126 | 23 |
| **u8 (KOPEN 8 / KEND 8)** | **+3.6 {+1.3, +6.5}** | 1,118 (1 hybrid) | 33 |

u8 is the obvious Pocket gate; on MiSTer the same cart is the u8slam lane's soak candidate (PR #44), so a "u8 everywhere"
plan keeps one cart line. A16 retune replays were not run (dropped for box load; A16 tracks V11 everywhere above).

## 5. Pending (running in the background when this was committed)
- Race model of the Pocket u8 retune (S14_d4_u8 at 54.669 MHz, n 1,000) vs MiSTer S14_d4_k32: unit
  `grok-pocketclk-sim2`, rows `dr_mario_rl/tmp/pocketclk/steer14/pk_S14_d4_u8_*.jsonl`; `tools/pocketclk/analyze_sim.py`
  prints it.

## 6. What this does not cover
- Silicon: the R47-era Pocket freeze, fit/timing at 99 % ALM, and the $5000 cart window are all untested here.
- The model's opponent pace is dr. lulu's measured pace; slower human opponents feel less of the tempo loss.
- Copro clock alternatives: C = 12 (50.1 MHz) would be worse; anything above ~60 MHz does not close on the 5CEBA4.
