# RESULT (silicon-fidelity lane, 2026-10-07): PUBLOG capture #2, the tall-endgame regime

## Why
- **Capture #1 never reached the target cell.** That was the DRPUBLOG cart 8355ddc7 on bluemage, 10/06: 2,251 pills
  replayed on Verilator.
  - It logged **zero** P2 pills at **≤ 20 viruses on boards of height 14–16**.
  - That cell holds **50 of the 77** unexplained 10/05 couch misses.
- **Two causes, both measured on the capture:**
  - **P1 ended every round early.** The native P1 won **45/45** rounds, with P2 still at 3–31 viruses (median round 50
    P2 pills).
  - **No garbage reached P2.** The tall boards on the couch are garbage-driven: dr. lulu sent 2.84 volleys/min, 83 / 7 / 10 %
    2 / 3 / 4.
- **Capture #1's one silicon-only signature: EARLY DONE.**
  - On 13 of the first 157 endgame searches, silicon read DONE 4–33 f before Verilator's DONE on the identical upload.
  - The publications and the final were the same.
  - A chained co-sim (one copro process on silicon's GO spacing, 3 lead pills) gives the fresh co-sim's DONE to 0.01 f on
    all 13, so carried-over copro state is not the cause.
  - The log cannot tell a genuine early finish from a false DONE read: the cart stops reading the mailbox after DONE.

## Options evaluated (predicted before any hardware time)
**Instrument:** `h16 experiments/silfid/pump_sim.py` + `pump_an.py`.
- It runs the STEER10–12 FAIR arm verbatim (`steer10_run.make("s10_base")`): the FAIR couch decider, timing and TAP-2
  steering.
- It plays to P2's OWN end on the couch-calibrated clock (steer11 `couch11`), with Poisson volleys at λ/min and dr. lulu's
  size mix.
- It records (viruses, max height) at every GO.
- q is optional: STEER12's silicon-like execution misses, a random other reachable root with probability q.

**CELL** = a GO at ≤ 20 viruses on a height-14–16 board.

**Calibration anchors.** The sim must reproduce silicon before its predictions count.

| anchor | silicon | sim q 0 | sim q 0.03 | sim q 0.06 |
|---|---|---|---|---|
| A: capture #1, λ 0, each sim game cut at a capture round length | ≤20 18.6 %, CELL **0 %** | 19.1 %, 0.14 % | 16.9 %, **0.00 %** | 13.5 %, 0.80 % |
| B: the 10/05 couch, λ 2.84, cut at each couch game's duration | ≤20 61.2 %, CELL **30.7 %** | 55.7 %, 8.8 % | 54.6 %, 17.2 % | 50.5 %, 18.4 % |

- Anchor A fits at q 0–0.03.
- Under the couch's garbage the sim makes **too few** tall endgames at every q: 9–18 % against 30.7 %.
- So the sim's CELL yields below are a **lower bound** for any garbage arm.

**Arms.** P1 is held, so every game runs to P2's own clear or top-out. CELL/h counts sim time plus 8 s per round.
`pump_an_20261007.txt` has the full table.

| option | arm | CELL / h (q 0 / 0.03 / 0.06) | note |
|---|---|---|---|
| (a) P1 can't win, no garbage (DRP1HOLD alone) | L11 λ 0 | 30 / 142 / 558 | wholly dependent on execution misses; ~0 at the dose that fits capture #1 |
| (a) asymmetric level, no garbage | L20 λ 0 | 37 (q 0) | taller viruses but P2 still clears flat; not useful |
| (b) a stronger P1 (a copro bot) | FAIR's own send rate 5.9/min, round cut at a FAIR clear | 98 / 269 / 138 | the bot P1 ends rounds before P2's endgame |
| **(d) DRP1HOLD + DRGPUMP 1x** | **L11 λ 2.84** | **357 / 716 / 547** | **chosen**: the couch's own garbage rate; the couch itself ran 655 CELL/h of play |
| (d) the same, 2x | L11 λ 5.68 | 523 / – / 345 | more top-outs before ≤ 20; not better |
| (d) the same, 3x | L11 λ 8.52 | 491 (q 0) | 39 / 49 games top out |
| (c) seeded layouts | – | – | not evaluated: virus layout comes from the ROM's level RNG, and level height is option (a)'s L20 arm |

**Prediction for a 60-min capture on the 1x cart:**
- about 2,200 P2 pills (capture #1's pace), of which about 65 % at ≤ 20 viruses;
- **≥ 360 and most likely ~700 CELL pills**, against 0 in capture #1.
- At the couch's silicon-only miss rate in that cell (50 / 365 = 13.7 %), a regime-specific copro divergence would show
  up as dozens of DIVERGED pills per hour.

## The cart (dr-mario-te `claude/silfid-publog2`, stacked on `claude/silfid-publog`)
Capture #1's cart (`cvcp2` + DRP1AIHI + DRSLICEGUARD2 + DRPUBLOG) plus three default-off flags. P2's driver is untouched.
- **`DRP1HOLD=1`** (needs DRP1NATIVE):
  - In act_p1, after the spectator search's slice bookkeeping, P1 is held: GRAV_P1 ($0312) ← 0 and an empty P1 pad
    ($F5/$F7) on every hook.
  - P1 never falls, locks, clears or tops out. A round ends only on P2's clear or top-out.
- **`DRGPUMP=1`** (needs DRP1HOLD): the synthetic P1 attack, a ROM-native volley through P1's own attack slot.
  - Write order: colours $0329–$032C, then size $0318 last.
  - Delivery is only into an EMPTY slot. Back-to-back volleys merge in a pending store (cap 4), like vs_race's store.
  - Rate: a Poisson process in play time. A 16-bit xorshift (7,9,8) steps every act_p1 hook and fires on states 1..T-1:
    (T-1)/65535 per hook = **2.86/min at T 27** (5.72 at T 53).
  - Sizes: a fixed 32-entry shuffle, 84 / 6 / 9 %.
  - Colours: a fixed 64-entry 0..2 sequence. Tables, because a small xorshift state's successor is small too, and to keep
    the worst hook cheap.
  - No volley while P2's virus count is 0.
  - Telemetry: $6633/34 = volleys fired, $6635/36 = cells delivered.
- **`DRPUBLOG_PDW=1`**: the post-DONE watch, aimed at EARLY DONE.
  - At the DONE read the cart re-reads $5284 at once. If that reads 0, the DONE event is type $42 (decoders mask $3F).
  - Until the next GO, pl_hook keeps reading $5284/$5285/$5286. The first time DONE reads 0 or the answer changes, it
    logs ONE type-6 event (a = $5284, b = col, c = orient4). This is the lowest priority in the one-event-per-hook
    chain.
  - **Reading the result:**
    - a false DONE read is flagged by one or the other;
    - a genuine early finish by the silicon copro never is.

**Carts:**
- `pump_cvcp2` **d84436ff** (1x + PDW): **the capture cart**;
- `pump2x_cvcp2` 9841ba14 (2x + PDW);
- `pump_nopdw_cvcp2` 35ef421a;
- `hold_cvcp2` f9bb6520.

Kit: `dr_mario_rl/tmp/couch_kit/publog2_20261007/` (BUILD.md has the install, load, verify and capture steps). Same rbf
318607aa.

## Gates (`GATES_PUBLOG2.txt`, `MESEN_PUBLOG2.txt`)
- **Negative controls:** with every new flag at 0, the shipped / staged carts rebuild byte-identically, as does capture
  #1's PUBLOG cart (8355ddc7). T 27 explicit = the default build.
- **NMI census, worst admissible frame** (pp_ph4 + pp_idle):
  - publog: 29,217 (+563);
  - hold: 29,175 (+605);
  - pump: 29,622 (+158);
  - **pump + PDW (the capture cart): 29,672 (+108)**; 2x is the same.
  - The census is a sound upper bound, so the margin is thin but certified.
- `run_cart_gates.sh`: ALL PASS.
- **Gravity fidelity** (P2 only; the pump's $0318 stores are replayed into run B as opponent actions), seeds 5/11/23:
  - cvcp2_publog / hold / pump(+PDW) / pump_t255 PASS;
  - couch_464a4b75 KILLED.
- **lgcut** on the capture flag set: PASS, 5 mutants killed.
- **`tests/test_gpump.py`** (new), seeds 5/11 × 4000 frames:
  - An exact reference model of the pump (xorshift, tables, pending store, empty-slot delivery, round-over gate) predicts
    every driver store to $0318/$0329–$032C and the GP_N/GP_C telemetry.
  - `gp_pump` runs on every play hook. P1 is held on every play hook.
  - Arms hold / pump / pump_t255 PASS. Mutants M_overwrite (delivery into a pending slot) and M_nohold (no gravity pin)
    are KILLED.
- **`tests/test_publog.py`** (ring vs truth):
  - on capture #1's flags, ALL PASS;
  - on the capture flags with `--pdw` false-DONE injection:
    - single-read false DONEs are all flagged by the re-read;
    - frame-long false DONEs with ≥ 6 play hooks before the next GO are all logged as type 6;
    - 0 flags on genuine DONEs.
  - Truth fixes in the harness:
    - LIVE truth counts play hooks only;
    - a lock first observed in the next search's GO hook is accepted in that next slot.
- **Mesen**, free-running (stand-in copro brain), 36,000 frames per run:
  - P1 held: 0 violations across every round;
  - every round ended by P2;
  - deliveries == releases == GP_N, cells == GP_C, about 3 volleys per play-minute;
  - autonav cycled 20+ rounds;
  - the ring decodes 25 consecutive pills with no gaps.
  - MESEN_PUBLOG2.txt has both runs (35ef421a and the capture cart d84436ff).

## Offline after the capture
Unchanged from capture #1:
```
publog.py --json pills.json <dir>/*.ss
publog_run.py pills.json publog_cosim.jsonl -j 5
```
- Plus: the type-6 / $42 tallies on the early-DONE pills.
- Plus: GP_N/GP_C from the states, to measure the realised volley rate on silicon.
