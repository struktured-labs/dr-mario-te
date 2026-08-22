# PRE-REGISTRATION L1 — "Why does she win": tempo and blunder-under-volley

Lane: lulu-147. Status: **DRAFT FOR TEAM-LEAD REVIEW. NOT REGISTERED. NOT RUN.**
Date drafted: 2026-08-21 EDT. Registration requires team-lead sign-off and a commit hash.

---

## 0. One-line question

**Does the champion lose to dr. lulu because it is killed, or because it is slow?**
The gap analysis says both, ~25% killed and ~75% out-raced, and that the ~75% is the part no
instrument in the program has ever measured. L1 measures it.

## 1. Motivation and the specific hole

Every shipped headline is scoped to a regime where the champion wins **250/250**
(`results/blunder_battery.json` `/ai/corpus`). Under a lulu-fitted volley stream on
`pressure_rig` it wins **90/120**. Neither number is a race, and no rig reports a *distribution*
of clear times — only paired mean deltas. L1 builds the distribution on both sides of the
matchup and asks whether tempo alone accounts for the observed 0-3.

## 2. Design — two parts, deliberately unequal in strength

### L1a — CHAMPION tempo and blunder-under-volley. **Zero new compute.**

The per-seed rows already exist in `experiments/eval47/results/*.json` (each has `ctrl`/`arm`
arrays of 120 rows carrying `pills`, `won`, `topout`, `stall`, `dies_ahead`,
`viruses_left_at_end`, `garbage_injected`). L1a is an **analysis of existing artifacts**, not a
run. It reads, it does not execute the sim.

**Outputs (pre-declared):**
1. `pills_to_clear` distribution — p10/p25/median/p75/p90 + seed-clustered bootstrap CI on the
   median — for the shipped champion (`wt0 ws20`) on each of: clean, canonical drip,
   bursty v1.1, lulu-pooled.
2. The same, **conditioned on losing** (`viruses_left_at_end` at termination), which is where the
   dies-ahead games live.
3. **Blunder-under-volley:** per-placement bad-end hazard, stratified by *time since last volley
   received* (0-2 / 3-5 / 6-9 / 10+ placements). The pre-registered question: **is failure
   clustered immediately after a volley lands, or is it uniform?** Clustered ⇒ it is an
   *attack-response* defect. Uniform ⇒ it is cumulative height and the volley timing is
   incidental.
4. **Survivorship correction, stated as a limit.** The distributions in (1) are conditional on
   winning, so they are a **floor** on the tempo tax. Reported with a Kaplan-Meier style
   censored estimate alongside the naive one; if the two disagree in direction, only the censored
   one is quoted.

### L1b — LULU tempo from footage. **Weak by construction; declared as such.**

Her side rests on **12 min 38 s from a single session** (`20260808_162820_dr_lulu.mkv`), of
which only m3 has been tracked and only on P1. L1b re-processes **m1 and m2 on the P1 side**
(the crops for m1/m2 P1 do not exist and must be extracted:
`ffmpeg -ss <t> -to <t> -vf crop=440:704:392:348`, then `film_20260808/tracker_p1.py`).

**Outputs:** her pills-per-clear, virus-clear tempo, and declined-clear rate across all three
matches, plus a **direct time-to-clear** for the one match she won by racing (m3, ~190 s
including dead time).

★ **L1b's honest ceiling: three matches, one filmed race win.** It cannot produce a
distribution. It produces an **anchor with an interval** and it is labelled that way everywhere.

## 3. Pre-registered predictions — BOTH DIRECTIONS, signed before the numbers exist (rule 2)

| # | prediction | what the opposite would mean |
|---|---|---|
| P1 | Champion median pills-to-clear under lulu pressure ≥ 120 (vs 96 canonical drip) | If it is ~96, pressure does not tax tempo, the race story collapses, and the losses are pure kill — re-weight everything toward survival |
| P2 | Lulu's observed clear tempo is **faster** than the champion's median under her pressure | If she is slower, the champion is losing races it should win ⇒ the defect is execution/silicon, not eval tempo — a completely different lane |
| P3 | Bad-end hazard is **elevated in the 0-2 placements after a volley** vs the 10+ stratum | If uniform, "risk-neutral near an absorbing state" is a *height* story, not an *attack-response* story, and the striker's release model is the wrong shape |
| P4 | Her separated-sending p(volley\|4-6 clear) ≤ pooled 40.8% | If higher, the split is suspect and L1b's fit is not usable (see `PRESSURE_MODEL_PLAN.md` §3a) |

★ **Rule 2 compliance:** each row above states the flattering *and* the unflattering
consequence. P2's unflattering branch (she is slower) would **redirect the whole lane** away
from eval work — it is registered precisely so that outcome cannot be quietly discarded.

## 4. Gates and controls

- **G0 — outcome plausibility (rule 7).** Before any distribution is read: assert the recovered
  rows reproduce the *already-published* headline for each file (e.g. `n120_wt0_ws20` ctrl must
  come back 115/120 won; lulu rig arm 90/120 clear, dies-ahead 17). A structural gate cannot see
  a fault applied to both sides; this outcome assertion can. **Failure blocks the analysis.**
- **G1 — incumbent calibration (rule 1).** L1b's tracker must reproduce the existing
  `p1_m3.csv` (75 rows) **exactly** before m1/m2 output is trusted. If the tooling cannot
  reproduce its own known-good output, nothing new it produces may be read.
- **G2 — interpretability floor (rule 5).** The volley-stratified hazard in L1a(3) is reported
  only if each stratum holds ≥100 placements *and* the strata differ on ≥2-3% of the outcome.
  Otherwise the result is published as **"not testable at this stratification"**, never as a null.
- **G3 — tracker control for L1b.** The spawn-row-lock control must pass on the P1 crops
  (reference corpus 1.2%; the P1/m3 side passed at 2.7%; the P2 side **failed at 19.4%**).
  **Any match failing the control is dropped, and its absence is stated in the headline** — not
  averaged away. Her declined-clear rate stays unpublished if the control fails.
- **G4 — virus-count cross-check.** Classifier virus count must agree with the on-screen VIRUS
  box within tolerance. On the P2 side it read 28 vs 41 (~30% undercount); that is the failure
  mode this gate exists to catch.
- **G5 — unit of analysis.** Seed for L1a, **match** for L1b. Per-placement counts in L1a(3)
  must be seed-clustered before any CI is quoted; per-row counts have impersonated independent
  samples three times in this project's history.

## 5. Scope statement (rule 10 / rule 24), written before the run

L1 licenses claims of the form:
- "The shipped champion's median pills-to-clear inflates from A to B under a lulu-fitted volley
  stream **on the solo pressure rig**."
- "Its bad-end hazard is / is not concentrated in the placements following a volley."
- "In her three filmed matches, dr. lulu's observed clear tempo was X."

L1 **does not** license:
- Any win rate, any probability of beating her, or any claim that the champion "would" win a
  race. **L1 has no race in it.** That is `VS_RACE_ENDPOINT.md`.
- Any claim about her *style* beyond three matches on one night.
- Any transfer to silicon.

## 6. Cost and constraints

- **L1a: ~0 core-hours.** Reads JSON already on disk. Runs on 1 core in seconds.
- **L1b: ~2 cores, bounded**, for two ffmpeg crop extractions (m1, m2 P1) plus tracker passes.
  Within the lane's ≤3-core footage-probing budget. **Footage is opened read-only; no file
  newer than 10 minutes is touched** (`20260821_194835_*.mkv` is being written by OBS right now
  and is excluded by name).
- Does not touch `drm-champ-endpoint`, `drm-labels-*`, `drm-sileval-ab`, or Hetzner. $0.

## 7. Decision rule — declared before the run

| outcome | consequence |
|---|---|
| P1 ✓ and P2 ✓ | Tempo-under-pressure is confirmed as the dominant loss channel ⇒ **build the race endpoint** and make pills-to-clear-under-pressure the lane's optimization target |
| P1 ✓, P2 ✗ (she is slower) | The champion is losing races it should win ⇒ **pivot to execution/silicon fidelity under pressure**, not eval |
| P1 ✗ | Pressure does not tax tempo ⇒ the losses are pure kill ⇒ **survival/risk-pricing lane**, and the race endpoint drops in priority |
| P3 ✓ | Attack-response defect confirmed ⇒ the striker's height-gated release model is the right shape; feed it her sending fit |
| P3 ✗ | It is a height story ⇒ re-examine the striker's release predicate before trusting any timed-pressure result |
| G0/G1 fail | **Nothing is published.** The artifacts are not what they claim and that is itself the report. |

## 8. Open questions for team-lead before registration

1. **Is L1b worth its 2 cores tonight**, given its ceiling is n=3 matches and one filmed race?
   My recommendation: **yes, but only m1/m2 P1 extraction** — it triples her tracked-pill count
   (75 → ~220) and it is the only lulu data that can be created without her sitting down again.
2. **Confirm the cap-scoring break.** `VS_RACE_ENDPOINT.md` §2.1 scores a cap as a **LOSS**,
   where `h2h_vs.py` scores it 0.5. This is a deliberate divergence from the incumbent and I want
   it signed off, not discovered later.
3. **Should P4 (her sending split) be folded into L1 or run separately?** It is cheap and it
   changes what L1b's fit means. My recommendation: fold it in, as a gate on L1b rather than a
   result.
