# Garbage-reactive mode switch: does a temporary reweight cure what ws=20 can't?

**Date:** 2026-08-05 · **Rig:** `pressure_rig.py` (extended, flags-off byte-identical to the
committed bursty-v1 behavior — verified, see §1) · **n=120 seeds/arm, L11, workers=6**

## 0. TL;DR

**NO-SHIP.** All 3 tested reactive configs are a wash-to-negative against the shipped ws=20
baseline (32/120 bad-ends): K=4/boost=20 → 35/120, K=8/boost=20 → 32/120 (exact tie), K=4/boost=40
→ 39/120. None beat ws=20; McNemar vs ws=20 is non-significant on all three (p=0.76, 1.0, 0.36) and
two of three point in the harmful direction. The likely reason: under bursty pressure the trigger
("garbage landed within the last K placements") re-arms so often that the boosted weights are live
54–79% of the game, not a rare/narrow correction — the "temporary" mechanism collapses toward the
*standing* regime PRESSURE_TAX_RESULTS.md already refuted (static wt), just applied to ws instead.
Separately, the volume-confound check gives a real, useful finding regardless of the reactive
result: matching bursty's ~59-66 halves/game total volume with a smooth drip does **not** reproduce
bursty's damage to ws=20 (drip-volume-matched ws=20: 23/120 bad-ends, 19.2%, vs bursty ws=20's
32/120, 26.7%) even though the two controls are comparably bad (59/120 vs 52/120) — timing/burstiness,
not just raw garbage volume, is what defeats the shipped build.

## 1. Mechanism spec (as tested)

**Trigger (OBSERVABLE, silicon-portable):** "garbage landed within the last K placements." The rig
tracks `last_garbage_landed_pill`, set to `env.pills_placed` any time an injection (drip or bursty)
actually places >0 halves (silently skipped if every candidate column was already full, matching
the existing `_inject_garbage`/`inject_bursty_garbage` behavior). On silicon the equivalent signal
would be the driver's own garbage-write path — see §6, this does not exist in RTL yet.

**Response (PRICED, TEMPORARY):** for the `K` decisions immediately following a garbage-landing
placement, `_choose_base` sees `ws_eff = ws + boost` instead of the base `ws`. This is an *additive*
dose bump (not a multiplier), matching the codebase's existing dose-sweep convention (`ws=20`,
`wt=1/2/4`, etc.) and cheaper in RTL — an adder/mux on the weight path, no multiplier needed. (The
mechanism also supports an independent `wtboost` on the spawn-lane tower tax; not exercised in this
pass — see §5.)

**Decay:** a hard step back to baseline the placement after the K-th boosted decision — a
down-counter armed by the garbage-landed pulse, decrementing once per placement, gating a 2:1 weight
mux while nonzero. No smooth ramp, deliberately: a single register + comparator, not a multiply-per-
step ramp function.

**Flags-off invariance:** `reactive_k=0` (the default) makes `ws_eff==ws` on every decision.
Verified byte-for-byte against the pre-existing `results/bursty_n120_wt0_ws20.json` control+arm
rows for the first 8 seeds (0 mismatches across 208 field comparisons, `reactive_fires==0`
throughout), and re-confirmed at full n=120 in §2 below (exact match to `BURSTY_V1_RESULTS.md`).

Code: `pressure_rig.py` `_init()`/`play()` (`reactive_k`/`reactive_boost`/`reactive_wt_boost`
params, `last_garbage_landed_pill`/`reactive_fires` bookkeeping), arm-spec parser `_parse_arm()`
(`wt:ws:k:boost[:wtboost]`), CLI `--drip-period`/`--drip-k` (volume-matched drip control only).
`analyze_reactive.py` is the paired McNemar/dies-ahead/avg-viruses-at-death analysis script.

## 2. Rig-integrity check: ws=20 reproduction

Fresh run, same code path as the committed bursty-v1 integration (reactive flags off):

| | control wt=0 ws=0 | ws=20 (this run) | ws=20 (BURSTY_V1_RESULTS.md) |
|---|---|---|---|
| bad-ends | 52/120 (43.3%) | **32/120 (26.7%)** | 32/120 (26.7%) |
| topout/stall | 42/10 | 21/11 | 21/11 |
| dies-ahead (v≤12) | 37/120 (37/52=71.2% of bad-ends) | **16/120 (16/32=50.0% of bad-ends)** | 16/120 |
| avg viruses-left-at-end (all games) | 1.91 | 1.44 | 1.91 / 1.44 |
| garbage/game | 58.56 | 63.62 | 58.56 / 63.62 |
| paired pills (both-won) | — | +13.52 [−3.04,+30.50] WASH | +13.52 [−3.04,+30.50] WASH |

**Exact match on every reported number.** Rig integrity confirmed before trusting any of §3-4.

New metric this pass, not in the original doc: **avg viruses-left-AT-DEATH** (bad-end games only,
excludes the 0s wins contribute to the "all games" average) — control 4.40, ws=20 5.41. Note this is
*higher* for ws=20 than control even though ws=20's dies-ahead *fraction of bad-ends* is lower
(50.0% vs 71.2%): ws=20 rarely dies, but when it does, it's a slightly more mixed bag of near-clears
and outright losses rather than control's more uniformly near-the-doorstep pattern. Flagged, not
explained further here.

## 3. Reactive arms (bursty model, n=120, paired vs the ws=20 arm as reference)

| config | bad-ends | topout/stall | dies-ahead | dies-ahead % of bad-ends | avg viruses-at-death | duty cycle¹ | McNemar vs ws=20 | moved | p | paired pills (own ctrl) |
|---|---|---|---|---|---|---|---|---|---|---|
| **ws=20 (baseline)** | 32/120 (26.7%) | 21/11 | 16/120 | 50.0% | 5.41 | 0% | — | — | — | +13.52 [−3.04,+30.50] WASH |
| K=4, boost=+20 | 35/120 (29.2%) | 27/8 | 23/120 | 65.7% | 5.06 | 54.5% | 20 rescued / 23 harmed | 43/120 (35.8%) | 0.761 | +9.40 [−8.15,+27.21] WASH |
| K=8, boost=+20 | 32/120 (26.7%) | 19/13 | 15/120 | 46.9% | 5.38 | 79.3% | 19 rescued / 19 harmed | 38/120 (31.7%) | 1.000 | +15.26 [−1.28,+32.64] WASH |
| K=4, boost=+40 | 39/120 (32.5%) | 23/16 | 19/120 | 48.7% | 4.31 | 54.4% | 18 rescued / 25 harmed | 43/120 (35.8%) | 0.360 | +14.52 [−1.81,+31.12] WASH |

¹ duty cycle = fraction of eligible decisions (pills_placed > 25) made under the boosted weight,
measured directly from `reactive_fires / (pills - 25)` per game, mean over both-arm seeds.

**None of the three configs beat ws=20 on bad-ends.** K=8/boost=20 is an exact wash (32→32, 19
rescued / 19 harmed, p=1.0 — as null as a paired test gets). K=4 at either magnitude trends
*negative* (more seeds harmed than rescued: 23 vs 20, and 25 vs 18) though neither reaches
significance at n=120 (p=0.76, p=0.36) — "moved 35.8% of seeds" is honest language for "a lot of
seeds flipped, in both directions, canceling out to a wash-or-worse." Dies-ahead, the specific
target signature, gets *worse* on 2 of 3 configs (23 and 19 vs baseline's 16) and only marginally
better on the third (15 vs 16, a 1-game difference well inside noise).

**The likely mechanism for the negative/wash result: duty cycle.** Under bursty pressure, garbage
lands often enough (garbage/game 58-64 halves, arriving in volleys keyed to the AI's own clears,
which happen frequently at L11 once material builds) that the K-placement re-arm window rarely
fully decays before the next volley re-arms it. Measured directly from the per-seed data: the
boosted weight is live for **54.5% of eligible decisions at K=4, and 79.3% at K=8** — not the rare,
narrow correction the design aimed for. This is exactly the failure mode
`PRESSURE_TAX_RESULTS.md`'s own "next step" note warned a *reactive* design would avoid ("a
conditional response cannot pay the constant clean-play interference price that killed static wt") —
but at these duty cycles the reactive ws-boost has re-derived something close to a *standing*
elevated-ws regime for well over half the game, for no measured benefit. K=8's near-80% duty cycle
makes it barely distinguishable from "ws=40, mostly on" — consistent with it landing closest to a
pure wash (it most resembles a modest, uniform ws increase, which the existing dose literature
(`ab47.py`/`sweep_n120.log`, referenced in `PRESSURE_TAX_RESULTS.md`) already found doesn't move the
needle much either direction in this range).

## 4. Volume-confound check: drip scaled to bursty's garbage volume

Drip's fixed injection cadence was scaled (`--drip-period 5`, `k=2` unchanged; calibrated by a
small n=40 pilot at periods 4/5/6, landing period=5 closest to target) to approximate bursty's
control garbage volume (~58.6 halves/game):

| | drip-volume-matched (period=5) | bursty |
|---|---|---|
| control wt=0 ws=0 garbage/game | 66.29 | 58.56 |
| control bad-ends | **59/120 (49.2%)** | 52/120 (43.3%) |
| control dies-ahead % of bad-ends | 79.7% | 71.2% |
| ws=20 garbage/game | 57.70 | 63.62 |
| **ws=20 bad-ends** | **23/120 (19.2%)** | **32/120 (26.7%)** |
| ws=20 dies-ahead % of bad-ends | 39.1% | 50.0% |
| ws=20 avg viruses-left-at-end (all games) | 0.88 | 1.44 |

**Verdict: burstiness/timing, not just volume, is what defeats ws=20.** The two controls are in the
same ballpark (drip-volume-matched is if anything *slightly worse*, 49.2% vs 43.3% — so it's not
that the volume-scaled drip is somehow gentler overall). But **ws=20 recovers substantially better
under volume-matched drip** (19.2% bad-ends) **than under bursty** (26.7% bad-ends) at essentially
matched total garbage. If raw volume alone drove the shipped build's failure, the two ws=20 numbers
should track each other; instead there's a 7.5-point gap in bad-ends and an 11-point gap in
dies-ahead-share, in the direction bursty's clustered, clear-timed delivery hurts more than a smooth
drip of the same size. This is consistent with the field observation this whole program started
from: it isn't that garbage arrives, it's specifically that it arrives in bursts synchronized to
moments of commitment.

Honest caveat: volume is not a *zero*-contribution confound either — the drip-volume-matched
control is still clearly worse than the original period=8 baseline drip control (24/120 bad-ends
per `PRESSURE_TAX_RESULTS.md`), and its ws=20 arm still shows a meaningfully elevated dies-ahead
share (39.1%) versus what a fixed-eval tax alone produced historically. Both volume and timing
appear to contribute; timing adds a further, distinct increment on top of volume's own damage.

## 5. Verdict

**NO-SHIP** for the v1 reactive mechanism as specified and tested. It does not cure the dies-ahead
disease beyond what ws=20 alone already achieves, and the mechanism as designed doesn't behave like
the narrow/rare correction it was meant to be under this pressure model — it's live more than half
the game.

**ITERATE, not abandon** — the volume-confound result (§4) says the target mechanism (a
timing-sensitive response) is real and worth pursuing; this specific v1 trigger/response pair just
didn't hit it. Concrete next steps for a v2, in priority order:
1. **Narrow the trigger.** Require accumulated garbage debt (e.g. total un-cleared garbage halves
   above a threshold, or N volleys within a shorter lookback) rather than "any landing," and/or add
   a minimum re-arm cooldown so a K-placement window can fully decay before it's allowed to re-arm.
   Target duty cycle well under the measured 54-79% — closer to what "temporary" implies.
2. **Reconsider the direction of the response.** ws=20 already discourages stranding material; a
   post-garbage moment may call for *encouraging faster clearing/tempo* rather than *more caution*
   — e.g. a temporary bonus for clear-producing placements, or a temporary excavation-term boost
   (`w_excav`, currently hardcoded at `FX._W_EXCAV_SHIP=24` in `_root_value`, not yet exposed as a
   per-arm knob the way wt/ws are) instead of/alongside a stranded-tax boost. Not tested this pass —
   flagging for whoever picks this up next, since it's a different mechanism, not a K/magnitude
   retune of what was tried here.
3. Re-run the same n=120 paired-seed, McNemar-vs-ws=20, volume-confound-controlled protocol before
   trusting any v2 result — this harness is now built and reusable (`--arms wt:ws:k:boost[:wtboost]`,
   `analyze_reactive.py`).

## 6. What the silicon version would need

RTL-side `g_stranded` already exists and is shipped: `fpga/copro/LeafEval.sv` (`CMD 8` FSM, `strand`
output signal, ~line 75/256/267-276/1137-1149 per repo audit), surfaced on the host mailbox at
`$70x3` via `CoproDrMario.sv`'s `lev_strand` wire. **The weight (`DRSTRAND`/ws) is baked into
firmware at build time** (`build_copro_d3.py`'s `DRSTRAND` env var → immediate in the assembled
6502 ROM via the shift-add sequence in `test_search_d3.py` ~lines 541-554), not a runtime-writable
register. A reactive mode switch needs `ws` to become live-adjustable firmware *state* (a variable
the shift-add reads each decision), not a compile-time constant — that's new firmware work, not a
config flip, before any silicon A/B of this mechanism is possible.

**No garbage-landed signal or per-placement counter exists in the RTL/driver today.** The nearest
usable hook is the host `GO` pulse at `$5084`, which already fires once per pill placement — a new
down-counter, firmware-side, decremented on each `GO` and armed whenever the driver detects its own
garbage-write path firing (not yet instrumented — the offline rig's own-clear-stands-in-for-
opponent-volley convention has no silicon equivalent either, since a real two-board VS setup would
supply the real opponent-clear trigger there, which this solo-copro rig can't). Given §5's #1
recommendation (narrow the trigger / add a cooldown), the RTL counter should be built with that
already in mind — e.g. a saturating debt counter rather than a simple k-placements-since-last-pulse
timer — rather than porting the v1 trigger as tested here.

## Provenance

- Rig: `pressure_rig.py` (reactive extension, flags-off byte-identical — see §1/§2).
- Analysis: `analyze_reactive.py` (paired McNemar vs ws=20, dies-ahead, avg-viruses-at-death, duty
  cycle available from raw `reactive_fires`/`pills` fields in the result JSONs).
- Bursty model: `bursty_model.py` `fit_struktured_20260804()` (unchanged from BURSTY_V1_RESULTS.md).
- Runs: `results/reactive_n120_wt0_ws20.json` (reproduction + its own fresh control),
  `results/reactive_n120_wt0_ws20_k4_b20_wtb0.json`, `..._k8_b20_wtb0.json`, `..._k4_b40_wtb0.json`
  (reactive arms), `results/reactive_dripvol_n120_wt0_ws20.json` (volume-matched drip control, its
  own fresh control at period=5).
- Volume calibration pilots (n=40, period 4/5/6): `tmp_logs/smoke/dripcal*.json` (not committed —
  gitignored `tmp_logs/`; period=5 chosen, garbage/g 62.15 at n=40, 66.29/57.70 at n=120).
- Driver logs: `tmp_logs/reactive_n120.log`, `tmp_logs/reactive_dripvol_n120.log` (gitignored).
- Baseline comparisons: `BURSTY_V1_RESULTS.md` (bursty-v1 fit + ws=20 shipped numbers, matched
  exactly in §2), `PRESSURE_TAX_RESULTS.md` (drip baseline; names this mechanism as the next step
  and predicts the exact failure mode observed in §3 for a design that isn't kept narrow).
