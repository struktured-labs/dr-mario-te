# PRE-REG (2026-09-25, written BEFORE any arm run): STEER1 — how much does real steering cost, and which driver change recovers it?

## Instrument (built and gated this session)
`steer_model.py` is a frame-level execution layer: ROM gravity/DAS/rotation, plus the couch P2 driver
(latency sampled from silicon, rotate-first, DISTGATE clamp, DRPROPH pulse, settle gravity pin). The
`gate_b.play(..., steer=)` hook places the capsule where it actually lands instead of the brain's target.
- **G0 PASS**: steer=None is byte-identical (4/4 vendored fingerprints + banked fw540 rows).
- **G1 PASS on the modelled mechanisms** (hardware replay, 431 gated couch placements):
  - MATCH 339/340.
  - PROPH-ESCAPE 4/5.
  - clamp-mechanism short-landings 4/5.
  - Not reproducible by construction: the classes where the hardware brain's target differed from the sim's
    (brain-target-differs 5, OTHER 48, LATE-FLIP 15, TUCK 7), and 6 short-landings on open boards. Those are
    consistent with the driver slam-committing to an intermediate anytime running best, which the sim decider
    does not expose.
- **G2 PASS on per-placement rates** (couch arm, 60 games) vs the couch:
  - overrides 7.6% vs 7.2%;
  - PROPH firing 6.0% vs 5.6%;
  - clamp-short 3.9% vs 2.6%;
  - death hazard 0.40% vs 0.21% per placement (1 couch event, P = 0.44).
  - ⚠ Per GAME, gate (b) tap-out is high (33/60) because gate-b games are long solo clears (~140 pills) while
    couch games are races of 24–111 placements. Hence the couch-length secondary below.

## Design
gate (b): fw540 brain, OWNER burst model, L11, cap 600, n=600 paired seeds 36734.. step 2 (declared reuse of
the gate-b block). Latency, phase and gravity pin are keyed by (seed, pill index), so they are common across arms.

| arm | execution |
|---|---|
| (0) off | instant perfect execution (banked `gateb/fw540_*`) |
| (1) couch | steering on, current couch driver: the headline |
| (2) brainproph | PROPH pulses toward the brain's target side (oracle: the brain's final target known before its answer) |
| (3) prehold | (2) + DAS pre-hold toward the target side through the lock when carried v ≥ 10 (human-legal carry) |
| (4) pulse | couch driver, but every column move by alternate-frame press edges (1 col / 2 f), DISTGATE sized for it. SUPERHUMAN input: owner decision pending, reported separately |
| (5) reach | couch driver + a reachability-aware ROOT: the brain skips root actions the driver can't land at the median latency (`cascade_reach_x`, all-ones mask = stranded decider on 311/311 boards) |

## Endpoints
- PRIMARY: paired tap-out difference, seed bootstrap 95% CI.
  - (1) − (0): the cost of real steering.
  - (2)…(5) − (1): does the driver/brain change recover it?
- SECONDARY:
  - tap-out within the first 100 placements (couch-like exposure);
  - death hazard per placement;
  - win / stall(cap) rates;
  - override, PROPH and clamp rates.
- Bar for "worth building": the paired tap-out diff vs (1) is < 0 with the CI excluding 0.
  - (2)/(3) are ORACLE upper bounds: a real build needs the ply-2 plan (a firmware change) and gets less.
  - (4) is reported as the ceiling of steering speed, not a recommendation.

## Honest limits declared up front
- The model steers the sim brain's FINAL answer. It has no anytime running-best and no slam-on-stability to an
  intermediate target. On the couch that behaviour lands some pills on nearer, reachable spots. So arm (1)
  may overstate the cost of steering in long games; the arm-vs-arm contrasts share that bias.
- Garbage and pace are the owner model's, as in every gate-(b) result.
