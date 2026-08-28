# REGISTRATION — M2 offline distillation screens (DRAFT)
distill-coproc lane · drafted 2026-08-26 while M1 banks · Status: DRAFT —
no fitting runs until (a) M1 analyze passes E-M1a/b, (b) team-lead signs this
off with the bracketed numbers filled from MEASURED instrument headroom
(R38: no bar is stated against an imagined instrument). Cost tier <= EUR 1.

## 0. Claim structure (the honesty frame, fixed now)
Off-policy reproduction of the teacher is an UPPER BOUND on decider quality
(the LAW). M2 can therefore only KILL or LICENSE-M3-REGISTRATION — never
promote. **H0 = the 6.8% function-class wall** (fitted-LUT precedent). Every
verdict statistic below is held-out BY SEED and seed-clustered (B>=2000).
Strata (L20 / L11M) never pooled; smoke rows excluded; R52 degenerate states
excluded-and-counted.
**Effective-n rider (from M1's A4 diagnosis, team-lead 2026-08-27)**: the
campaign population is 62-80% SATURATED states (all candidates survive,
spread <= 1) — the informative label mass is the non-saturated minority, and
the guard fit's effective n is E-M1d's DANGER-STATE count, not the raw state
count. Every power/CI statement in this document is stated against the
non-saturated/danger-state counts; if the banked danger yield is under
[300]/stratum, M2 reports the shortfall and the options (reserve-block
top-up games vs proceeding underpowered) to team-lead BEFORE fitting.

## 1. Instruments measured BEFORE any bar is read (R38)
- **CEILING = split-sample tribunal self-transfer**: the tribunal's verdict
  and pick recomputed from a fork half, scored on the other half (R40
  discipline; the bank stores 8 forks/candidate exactly for this). This is
  the number any distilled g is chasing; nothing can honestly beat it.
- **FLOOR = label-shuffle fit**: identical pipeline on within-state permuted
  labels, **20 draws**, mean and sd reported (R38a).
- Headroom := ceiling − floor, per stratum. All GO/KILL fractions below are
  fractions of THIS measured headroom, not absolute AUCs.

## 2. Track A screens (the danger guard)
Function family, enumerated up front (multiplicity closed by enumeration +
held-out): (a) integer-threshold ruleset (depth<=3) and (b) int-linear+margin,
both over the FROZEN feature menu (DESIGN §C + M0's neighborhood finding:
post-move spawn-NEIGHBORHOOD heights/relief (c2-c5), throat occupancy rows
0-3 cols 2-5, a_topout_dist, e_escape_routes, adjacent-column deltas,
cur/next colours vs lane). Firmware constraint carried: <= ~1.7 KB, integer
ops only.
- **S-WHETHER**: g classifies the tribunal verdict at danger plies.
  Reported as an operating-point table at the tribunal's own realized
  override rate (dose-matched) — never AUC alone (distill-pivot rule).
- **S-CAPTURE (primary)**: realized surv-gain of g's decisions scored
  against the CHAMPION PICK (the baseline; boards never slot indices), on
  held-out states, as a fraction of MEASURED headroom.
  **MEASURED ANCHORS (2026-08-28, m2_screens.py instruments — L20, 3,587
  non-degenerate states / 353 danger; eval scale = eval-half surv points
  0..3):** danger-subset CEILING 0.269 (tribunal self-transfer, dose 0.405) ·
  danger-subset FLOOR **+0.069 +/- 0.021** (20 draws — NOT zero: at danger
  states a random alternative already beats the champion pick, exactly H16's
  premise; the matched-control lesson makes this floor load-bearing) ⇒
  **HEADROOM = 0.200**. All-states: ceiling 0.0248 CI[0.0178,0.0328], floor
  −0.004 (secondary/exposure view).
  **PROPOSED BARS (0.30/0.15 fractions as drafted; pending sign-off):
  GO iff held-out danger-subset capture >= 0.069 + 0.30 x 0.200 = 0.129 with
  seed-clustered CI lower bound > 0.069 + 0.15 x 0.200 = 0.099; KILL iff CI
  upper < 0.099.** H0 (6.8%-wall analog) predicts ~0.083 — below the KILL
  line, so the wall and a GO are distinguishable here.
  **L11M: NO SCREENING THIS ROUND — measured ceiling is on/below its floor
  (−0.036 vs +0.021, n=55 danger) — no headroom at current fork budget/n;
  pending the A5 danger back-fill decision.**
- **S-VETO-ONLY**: the WHETHER-only variant (veto -> champion's next-best
  passing g) scored on the same statistic — the minimum-risk deployable.
- **Forbidden predictions (both must hold or the machinery is unjustified)**:
  (i) g beats DO-NOTHING (champion pick) on its own firing set, CI excluding
  zero favourably; (ii) g beats the best SINGLE raw-feature threshold rule
  fitted identically (the S3 lesson: the baseline-you-replace includes the
  cheap version of yourself).
- **Inactivity guard (the 24/24 mechanism)**: capture is always reported
  WITH dose; a candidate at ~0 dose is INERT, not safe, and cannot pass.
  Two-sided plausibility bands on every gate stat (R53).

## 2b. Standing characterization + composite-catch gate (team-lead riders)
- E-M1a's lead result travels as design fact: at L11M the trigger is a
  **REGIME DETECTOR (lead p50 = 191 plies), not a death alarm** — g's option
  space includes acting far upstream of the brink, and fits should not assume
  brink-only features carry the signal.
- **Deployed-composite catch gate (R1 rider b)**: trigger × g must catch the
  silicon death class END-TO-END; g's contribution to catch is measured (on
  the spawn-plug suite below + M3), never assumed from E-M1a's 63/63.

## 3. Spawn-plug suite (design gate, not promotion evidence)
On the read-only silicon import stratum (2 owner-match death boards + corpus
pre-death states + their healthy-tall controls): g must veto the fatal
placement on **>= [0.60]** of tribunal-certified danger states AND false-veto
**<= [0.10]** on matched healthy-tall controls (the half that can fail, R36).
Both match boards vetoed = reported by name (owner-legible).

## 4. Track B (secondary, offline only)
Same pipeline, target = per-candidate PROGRESS ranking at pressured plies
(the corrected aim from the stage-2 closure). Same floor/ceiling discipline.
A GO here licenses nothing but a design note for the next-evaluator lane.

## 5. Outputs
`m2_screens.py` (fits + scores, emits every gate line greppable), committed
with results JSON; the verdict quotes ceiling, floor, capture, dose, and the
forbidden-prediction contrasts in one table. KILL and GO are both deliverable
outcomes; only M3's on-policy A/B can promote.
