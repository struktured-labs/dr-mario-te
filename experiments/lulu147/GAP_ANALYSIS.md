# The Lulu Gap — why a 4-6% error rate coexists with ~100% losses

Lane: lulu-147, off `v8-rematch`. Author: lulu lane. Date: 2026-08-21 (EDT) / 2026-08-22 UTC.
Status: **DESIGN + INVENTORY. No new compute was run for this document.** Every number below is
either read off an existing on-disk artifact or recomputed from per-seed rows already in
`experiments/eval47/results/*.json`; provenance is given per number.

---

## 0. The owner's sentence, restated as a measurable claim

> "our stats claim 4-6% error rate but it loses almost 100% of the time to my dr. lulu — the
> metric is crap. Are we not simulating opponent pressure well enough?"

Two separable questions live in there:

1. **Is the metric crap?** — Yes, and the reason is not subtle. Every headline the program ships
   is a **solo, un-raced statistic**. Nothing in the tree measures the thing he loses.
2. **Is it the pressure model?** — **Partly, and less than expected.** The pressure model is a
   real gap (§4), but it is not the biggest one. The biggest one is that **there is no opponent
   clock anywhere in the lab.** We have never measured a race.

The answer to "are we simulating opponent pressure well enough" is therefore: *we simulate her
pressure imperfectly, but we do not simulate her **at all** as a racer, and the race is where
most of the losses come from.*

---

## 1. The metric is crap — precisely how

The champion's shipped numbers are measured where the failure does not exist.

| instrument | regime | champion result | path |
|---|---|---|---|
| clean census | solo, no garbage, L11 | **0 failures / 1,474 games** (<0.20%) | [[dr-mario-clean-failure-rate]] |
| blunder battery corpus | solo, no garbage, L11, ws=20 | **250/250 won**, 0 topout, 0 stall, mean 95.1 pills | `results/blunder_battery.json` `/ai/corpus` |
| canonical drip rig | solo + scripted drip | 119/120 won | `results/n120_wt0_ws20.json` |
| bursty v1.1 rig | solo + struktured-fitted volleys | 100/120 won, dies-ahead 9/120 = 7.5% | `results/bursty_v1_1_n120_wt0_ws20.json` |
| **lulu-fitted rig** | solo + lulu volleys (POOLED fit) | **90/120 won, dies-ahead 17/120 = 14.2%** | `results/dr_lulu_20260808_rig_n120_wt0_ws20.json` |
| **real lulu, on silicon** | actual VS match, Pocket | **0–3** (and undefeated vs Combo Stomper) | `player_styles/dr_lulu.md` |

Whatever the specific "4-6%" refers to — a leaf/label disagreement rate, an argmax-flip rate, a
blunder-class rate — **it is computed on the row of this table where the champion wins 250 out of
250 games.** That is the whole indictment. It is not that the number is wrong; it is that its
scope does not contain the claim. ([[dr-mario-measurement-rules]] #24.)

⚠ **Caveat that must travel with the table** ([[caveat-next-to-data-not-number]]): the top rows
are solo and the bottom row is a two-sided match on different silicon at L11 MED. The rig rows
are *not* a VS win rate and must never be quoted as one.

---

## 2. Decomposition: what "loses ~100%" is actually made of

Four candidate mechanisms. The evidence assigns weight to two of them and rules out a third.

### (a) PRESSURE-KILL — real, and the *smaller* half. ~25% of games.

On the lulu-fitted rig the shipped champion (`wt0 ws20`) ends badly in **30/120 games (25%)**,
of which **17 are dies-ahead** (topped out with ≤12 viruses left — i.e. it was winning the race
and died anyway). Source: `results/dr_lulu_20260808_rig_n120_wt0_ws20.json` `summary`.

This corroborates directly on silicon: of her three recorded wins on 2026-08-08, **two were
AI dies-ahead topouts** (`player_styles/dr_lulu.md`: m1 "AI up 8, twin-column tower to the bottle
neck"; m2 "AI up 3, four-column comb vs her near-empty board"). Four independent lanes already
converged on this diagnosis — the champion is **risk-neutral near an absorbing state**
([[dr-mario-clean-failure-rate]], [[dr-mario-adversary-t3-champion-robust]]).

**Instrumented?** YES. `pressure_rig.py` + `lulu_proxy/striker_model.py` measure exactly this.
This is the one component we can already see.

### (b) PRESSURE-INDUCED TEMPO TAX — real, and the ★ **larger** half. Newly quantified here.

Pressure does not only kill. It **slows the champion down**, and nobody has priced that.
Recomputed from the per-seed `pills` arrays already on disk (wins only, so this is *conditional
on surviving* — the survivorship bias makes it a **floor**):

| stream | n won / 120 | p25 | **median pills** | p75 | p90 |
|---|---|---|---|---|---|
| clean (blunder corpus, n=250) | 250/250 | — | — (mean **95.1**) | — | — |
| canonical drip | 119 | 85 | **96** | 110 | 123 |
| bursty v1.1 (struktured) | 100 | 103 | **128** | 172 | 223 |
| **lulu-fitted (POOLED)** | **90** | 104 | **127** | 165 | 199 |

**Under lulu-shaped pressure the champion's median time-to-clear inflates +32% (96 → 127 pills)
and its p90 inflates +62% (123 → 199).** At the project's own working constant of **~2.5 s per
placement at L11** (`lulu_proxy/striker_model.py:59`, where `BANK_TIMEOUT_PILLS=9` is derived
from it), that is a median **4.0 min → 5.3 min**, p90 **5.1 min → 8.3 min**.

**The race number to beat.** The single race lulu actually won on film (m3) ran from the m2
boundary at 9:09 to the m3 boundary at 12:19 in `20260808_162820_dr_lulu.mkv` — **~190 s ≈ 3.2
min**, including countdown and dead time, so her true clear time is *shorter* than that.

> ★ **The headline of this analysis: the champion needs ~5.3 min median to clear under her
> pressure; her one filmed clear took under 3.2 min. That is not a close race.**

⚠⚠ **This comparison is the weakest strong thing in the document and must be labelled every
time it is used.** It is **n=1** on her side; her time includes non-play frames; the champion's
side is a *solo* rig with injected garbage, not a real VS board; and 2.5 s/pill is a project
constant, not a measurement of this build. It is an **anchor and a hypothesis**, not a finding.
Making it a finding is exactly what the pre-registration in `PREREG_L1.md` is for.

**Instrumented?** **NO.** No rig in the tree reports a time-to-clear or a pills-to-clear
*distribution* — every solo rig reports only a paired mean delta + bootstrap CI
(`ab47.compare()`, `pressure_rig.compare()`). The table above did not exist until this document;
it was recovered from raw rows. **This is the cheapest new instrument on the list and it needs
zero new compute.**

### (c) ATTACK ABSENCE — ★ **DE-PRIORITIZE. The evidence says this is not why we lose.**

The intuitive story ("we lose because we never punch back") is the one the record does *not*
support:

- The shipped brain **out-attacks humans**: attack-given-clear 25.0-26.4% vs human 18.6%
  ([[dr-mario-ai-never-attacks]], inverted 2026-07-26 — the old 8.9% was a wrong-brain artifact).
- Two arms that both **beat** the shipped winner moved attack rate in **opposite directions**
  (lnk1 +9%, lnkfix −11%) — attack rate does not predict win rate at all
  ([[dr-mario-lnk1-vs-confirmed]]).
- The one confirmed VS win in program history wins **by clearing first in 99.2% of its wins**;
  garbage decided **5 of 800** matches (ibid.).
- Simultaneity-buying levers are refuted causally ([[dr-mario-selfplay-vs-negative]]).

⚠ **Scope this correctly** — the one live exception is that **85% of real ROM attacks are
cascade-formed**, and *the cascade lever has never been tested*, because the shipped leaf is
cap-1 and structurally cannot score chain depth. So "attack-shaping is refuted" is licensed;
"offense is a dead end" is **not**. It is deferred behind a physics prerequisite, not closed.

### (d) EXECUTION FAULTS UNDER PRESSURE — open, uninstrumented, and plausibly large.

The north-star memory ranks execution defects HIGH precisely because offline eval metrics
cannot see them ([[dr-mario-north-star-beat-human]]), and the exec-fidelity census + VOD
adjudication lanes have repeatedly found real orientation/latch faults on silicon. Nothing
measures whether their **rate rises when garbage is arriving** — which is the version of the
question that matters for beating her.

**Instrumented?** Partially. The census exists; a pressure-stratified version does not.

### Decomposition summary

| component | share of the ~100% | can we measure it today? |
|---|---|---|
| (a) pressure-kill / dies-ahead | ~25% of games, directly | **YES** — `pressure_rig` + striker |
| (b) tempo tax → race loss | the remaining ~75% | **NO** — no distribution, no clock, no race |
| (c) attack absence | ~0, on current evidence | yes, and it says "not this" |
| (d) execution faults under pressure | unknown, plausibly non-trivial | **NO** — census is un-stratified |

---

## 3. What our instruments can and cannot see

**CAN measure today (code exists, validated, on disk):**
- Solo survival under a fitted human volley stream (`pressure_rig.py`, bursty + drip modes).
- **Timed** pressure vs volume-matched blind pressure — `lulu_proxy/striker_model.py` banks
  volleys and releases them on the defender's scaffold height. It carries killed-mutant gates
  (`check_release_log`, `check_pairing`, `check_matched_volume`) and a blind control
  (`build_blind_schedule`). This is the best pressure instrument in the tree and it already
  demonstrated **timing beats volume** (champion H8: striker 38 dies-ahead vs blind 15, p=0.0014).
- ROM-true VS between **two deciders**, with real win/loss and side-swap
  (`vs_harness.py` / `h2h_vs.py`).
- ROM-true garbage column phase (`rom_attack_rule.garbage_columns`).

**CANNOT measure today (must be built):**
1. **A race against a human-shaped opponent.** `pressure_rig` has one board and no opponent
   clock — in bursty mode *the AI's own clear stands in for the opponent's clear*
   (`pressure_rig.py:222-240`, candidly commented in the source). The "opponent" has no virus
   count, no board, and cannot lose. `vs_harness` has a real race but the opponent is always
   another decider, never a fitted human. **No rig in the tree crosses these two.** This is
   gap #1 and it is the whole reason the lab has never predicted a lulu result.
2. **Time-to-clear, or any pills-to-clear distribution.** Only paired mean deltas exist.
3. **Aim.** Nothing models which columns garbage lands in. `bursty_model.sample()` picks
   uniform-random columns; the striker picks random columns *deliberately*, to avoid conflating
   timing with targeting. Yet the adversarial-scheduler lane already found that **aiming garbage
   at spawn columns 3-4 raises dies-ahead** — so aim is known to matter and is unfitted.
   ★ Sharp irony worth fixing: `bursty_model.extract_volleys()` *detects* volleys **by** their
   paired-column geometry and then throws the geometry away at sample time.
4. **Lulu's own tempo**, beyond n=1. No pills-per-clear, no declined-clear rate, no latency
   distribution for her (§4).
5. **Execution fidelity stratified by incoming pressure.**

---

## 4. The pressure model gap, specifically

Her fit — `results/dr_lulu_20260808_fit.json`, 59 volleys / 175 clears / 3 matches — has three
defects, in descending order of how much they matter:

1. ★★ **It is POOLED**, so it mixes her sending stream with the AI copro's, whose cadence is a
   near-deterministic ROM rule. This is the identical contamination that forced struktured's
   v1 → v1.1 refit (33 of his 61 pooled volleys were the copro's).
   **Consequence, already documented:** her apparent lethality is mostly *scope*, not skill —
   scope-matched (both pooled) the champion's dies-ahead is **14.2% under her vs 13.3% under
   struktured**, not the "twice as lethal" that reading her pooled row against his separated
   row suggests ([[dr-mario-lulu-fit-is-pooled]]). **No `dr_lulu_*_sending_fit.json` exists.**
2. **It has no aim** (uniform-random columns) and **no phase** (no dependence on how far into
   the game either player is).
3. **It has no clock.** It is a garbage generator, not an opponent.

Her fitted parameters, for the record (vs struktured, same instrument):
volley_size_mean 2.390 (2.541) · inter_volley_gap_mean 21.85 s (22.70) ·
p(volley | 4-6-cell clear) **40.8% n=157** (32.1% n=156) · p(| 7-10) 56.2% n=16 (74.1% n=27).
Her dossier's own reading: *"she is the existence proof that timing beats volume."*

---

## 5. Verdict

- **The metric is crap in a specific, fixable way:** it is scoped to a regime (clean solo) in
  which the champion has literally never failed, and the program has no endpoint scoped to the
  regime the owner cares about (a race, under her pressure, on silicon).
- **"Are we simulating opponent pressure well enough?" — the pressure model is the second
  problem, not the first.** Her volley model is pooled, aimless and phaseless, and fixing that
  is cheap and already tooled. But even a perfect volley model would not have predicted these
  losses, because ~75% of them are **races we are losing on tempo**, and nothing in the lab
  races.
- **Ranked build order** (detail in `VS_RACE_ENDPOINT.md`, `PRESSURE_MODEL_PLAN.md`):
  1. Time-to-clear / pills-to-clear **distribution** reporting. Zero new compute; recover from
     rows already on disk. Unblocks every tempo claim.
  2. **A race endpoint** — a two-clock VS rig where the opponent is a lulu-parameterized
     pressure+clock model with a real win/loss.
  3. **Lulu's SENDING fit** (split her raw events with `fit_ensemble_source.fit_per_player`).
     Small, already tooled, removes the largest known bias in her model.
  4. **Aim**, fitted from the paired-column geometry the detector already computes.
  5. Pressure-stratified execution-fidelity census.

Rule-10 scoping, stated up front: until (2) exists, **the lab cannot claim any VS win rate
against dr. lulu, and must not present dies-ahead as a proxy for one.** Dies-ahead is a
survival statistic on a board with no opponent.
