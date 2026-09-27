# RESULT (2026-09-25): STEER1 — the couch tap-out gap is STEERING, and a reachability-aware brain is the best human-legal fix

Pre-reg: `PREREG_STEER1.md` (committed `eac2306` BEFORE any arm ran). Instrument: `steer_model.py` (frame-level ROM +
couch P2 driver), hook `gate_b.play(steer=)`. gate (b): fw540 brain, OWNER burst model, L11 MED, cap 600, n=600
paired seeds 36734.. step 2 (declared reuse).

## Headline: steering explains the couch gap
At the lengths of the 7 recorded couch games (24–111 placements), the expected number of AI tap-outs:

| model | expected AI deaths over the 7 couch games | P(≥1 death) |
|---|---|---|
| perfect execution (every offline number to date) | **0.05** | 0.05 |
| couch steering model (arm 1) | **0.97** | 0.62 |
| **observed on the couch** | **1** (9/25 G2) | |

Per placement, the hazard is 0.014% with perfect execution, 0.48% with steering, and 0.21% on the couch
(1 event / 467, 95% CI ≈ 0.005–1.2%). The offline brain almost never taps out; the brain plus the real driver does,
at the rate the couch shows. Per GAME, gate (b)'s numbers are much larger than any couch game (60% vs 2.3%), because
gate-b games are long solo clears (median death at pill 104) under accelerating gravity (speedUps every 10 pills).
Read the per-game column as "long-game stress", and the tap≤100 column as the couch-like exposure.

## Gates
- **G0 PASS**:
  - steer=None is byte-identical: 4/4 vendored fingerprints plus the banked fw540 rows.
  - The couch arm is byte-identical before and after the post-hoc edits (md5 `ec5501cf`).
  - Local and Hetzner agree exactly on couch and reach games.
- **G1 hardware replay**, 431 gated couch placements:
  - MATCH **339/340**
  - PROPH-ESCAPE **4/5**
  - clamp-mechanism short-landing **4/5**
  - Not reproducible by construction, because the hardware brain aimed elsewhere or the driver did something the
    model doesn't have:
    - OTHER 48, LATE-FLIP 15, TUCK 7;
    - short-landings where the brain's target differs, 5;
    - open-board slam-to-intermediate short-landings, 6. Those need the anytime running-best and slam-on-stability,
      which aren't modelled.
- **G2 rates** (couch arm, 60 games, vs the couch):

  | rate | model | couch |
  |---|---|---|
  | overrides | 7.6% | 7.2% |
  | PROPH fires | 6.0% | 5.6% |
  | clamp-short | 3.9% | 2.6% |

- **Fitted, not assumed:**
  - The driver's settle gravity pin is 7|8 frames (silicon first natural drop minus threshold, n=246, every speed
    band).
  - Answer latency is sampled from 384 silicon first-lateral-move frames (median 19).

## Arms (paired vs arm 1 unless noted; seed-bootstrap 95% CI)
| arm | tap-out | Δ tap-out | tap≤100 | Δ tap≤100 | off-target | PROPH | clamp |
|---|---|---|---|---|---|---|---|
| (0) off (perfect execution) | 2.33% | (1)−(0) = **+57.8 [+54.0, +61.8]** | 1.33% | +27.5 [+24.0, +31.2] | — | — | — |
| **(1) couch driver** | **60.17%** | — | **28.83%** | — | 8.5% | 8.4% | 3.9% |
| (2) PROPH toward brain side (oracle) | 57.17% | −3.0 [−4.8, −1.2] | 26.67% | −2.2 [−5.0, +0.5] | 5.5% | 4.9% | 4.4% |
| (3) (2) + DAS pre-hold (oracle side) | 35.83% | **−24.3 [−28.3, −20.3]** | 12.67% | −16.2 [−19.8, −12.7] | 2.6% | 1.9% | 1.8% |
| (4) pulse steering 1 col/2 f (SUPERHUMAN) | 36.33% | −23.8 [−28.0, −19.8] | 13.17% | −15.7 [−19.5, −12.2] | 4.6% | 4.5% | 2.1% |
| **(5) reachability-aware root** | 45.50% | **−14.7 [−18.5, −10.8]** | **9.83%** | **−19.0 [−22.7, −15.3]** | 1.2% | 5.8% | 0.7% |

Every pre-registered arm clears the bar (CI excludes 0 on the primary).

## Post-hoc, labelled as such (not pre-registered)
1. **Latency sensitivity (`lat_mode="byrot"`).** Silicon answer latency depends on rotations needed: median f15 with
   0 rotations, f22 with 1. The pre-registered pooled sampler is ~4 f too slow for H targets and ~2 f too fast for V.
   Conditioning on rotations leaves the conclusions intact:
   - couch − off: **+60.3 [+56.3, +64.2]**
   - prehold − couch: **−26.2 [−30.2, −22.0]**
2. **Realistic pre-hold (`prehold_plan`).** Arm (3) with the direction taken from the PREVIOUS search's ply-2 plan
   for this pill, instead of the oracle final target. `cascade_plan_x` returns root identical to the stranded
   decider on 311/311 boards.
   - Result: **−4.8 [−8.8, −0.8]**, and −6.2 [−10.2, −2.2] with byrot.
   - Why so small: the plan's side matches the final target on only **62.5%** of pills and is wrong on ~20%.
     14.2% point the other way, and 5.8% point to a side when the final target is centre. A wrong-side carry costs
     a mid-pill momentum reset. So most of arm (3)'s −24 needs knowing the answer earlier, not a plan.

## What it means
- **Every offline tap-out number to date measured the brain without its hands.** The sim's ~2% hides the
  mechanism that produces the couch's ~1-in-6. Any future brain A/B aimed at tap-outs should run with
  `steer=Steer(proph="throat")`.
- **Best human-legal lever: arm 5, the reachability-aware root.**
  - It cuts couch-like early deaths from 28.8% to 9.8%.
  - It is realistic, not an oracle: the mask uses only the board, the pill index and the median silicon latency.
    The firmware can compute the same reach table it already uses for DISTGATE, as a root-candidate filter.
    Firmware-only, same species as DRSTRAND/DRVETO.
- **Faster answers** are what an oracle pre-hold really buys. Arm (3) only works if the side is known before the
  search finishes. Realistic sources are a faster first publish or a better plan.
- **Pulse steering (arm 4)** is the ceiling of steering speed. It is superhuman input: owner decision.
- **The PROPH direction fix (arm 2)** is small (−3) on its own.

## Limits
- The model steers the sim brain's FINAL answer. It has no anytime running-best and no slam-on-stability to an
  intermediate target; on silicon, some pills land on nearer reachable spots because of that. The arm contrasts
  share this bias.
- Couch calibration rests on 1 death.
- Garbage and pace are the owner model's, as in all gate-b work.

## Files
- Model: `steer_model.py`, `steer_g1.py`.
- Runner and analysis: `steer_run.py`, `analyze_steer1.py`.
- Brain variants: `cascade_reach_x.py`, `cascade_plan_x.py`.
- Rows: `steer1/{main,remote,sens,plan,g2}/`. Full table: `analyze_steer1.py` output.
