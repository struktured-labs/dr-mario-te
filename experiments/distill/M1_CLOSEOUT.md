# M1 CLOSE-OUT — label campaign complete (2026-08-28 ~00:40)
Verified by direct file count: L20 696/696 + 4 smoke · L11M 396/396 + 4 smoke.
Units exited clean after their strata; no BLOCK after amendment A4; final
recurring G-CRN (valid full-width form): L20 rho 0.364-0.367 (n=1,838 states),
L11M 0.407-0.414 (n=655) — stable, 2x the 0.18 bar all night.

## Registered endpoint verdicts (pre-stated numbers, read as written)
- **E-M1a wide12 topout-catch (lead >= 5 plies): PASS at the maximum —
  63/63 = 1.000, CI [0.943, 1.000], bar 0.70.** dsh13 comparator 57/63.
  Lead-at-first-fire p10/p50/p90 = 51/191/295 plies — the trigger opens long
  before death (it is a regime detector at L11M, not a moment detector).
- **E-M1b wide12 cleared-ply false-fire: FAIL — 0.264 vs ceiling 0.15.**
  Not an opening artifact: ply>20 rate is 0.279 (opening-only 0.174).
  Per the registration and team-lead's rider this is a STOP on the deployed-
  trigger question — no threshold slide; disposition is a registered decision.
- E-M1c random-quota danger recall 3/3, CI [0.438, 1.000] — n too small to
  quote beyond its CI (as pre-registered).
- **E-M1d yield**: L20 4,889 states (danger 384, overrides 153, degenerate
  1,302) · L11M 3,802 states (danger 58, overrides 21, degenerate 1,901).
  **L11M danger = 58 < the 300 shortfall threshold — the M2 effective-n rider
  FIRES for L11M.** Cause is mostly base-rate, not the cap: L11M-lulu fails
  only 63/396 = 16% of games (vs L20 ~39%); cap_hits median 0/game.

## The cross-regime tension (the honest finding; do not resolve silently)
Held-out variant curve from the banked traces (fresh relative to M0's
selection):
| variant | L11M topout-catch | cleared-ply fire | M0 silicon-corpus catch |
|---|---|---|---|
| wide12 | **63/63** | 0.264 FAIL | **21/31 = 68%** |
| wide13 | 61/63 | 0.146 ok | 12/31 = 39% |
| core13 | 61/63 | 0.099 ok | 9/31 = 29% |
| dsh13 | 57/63 | 0.045 ok | 9/31 = 29% |
**The silicon corpus wants threshold 12 (its 20.4 s window under-reads, and
catch collapses at 13); the lab-lulu false-fire ceiling wants >= 13. No single
threshold passes both as measured.** Candidate resolutions for team-lead:
- **R1 (lane recommendation): split the roles.** wide12 stays the LABELING
  trigger (its job was catch; E-M1a maxed; the bank is built). The DEPLOYED
  exposure is trigger x g — the veto function screens every fired ply — so
  re-scope E-M1b's ceiling onto the deployed quantity (false-VETO rate, gated
  by M3's clean-play guard + a registered veto-rate ceiling), not the raw
  trigger rate. Registration-level amendment; the 0.264 raw rate is priced as
  compute (with cooldown it is bounded) rather than as exposure.
- R2: deployed threshold 13 (wide13/core13), accepting the corpus-catch drop
  and arguing the corpus window's downward bias — weaker: it re-opens the M0
  gate on the silicon class with a number (29-39%) that failed it.

## L11M danger shortfall — top-up proposal (needs sign-off, ~EUR 0.6)
Danger-back-fill pass on the SAME 63 topout games (seeds already consumed,
trajectories already banked): replay each and adjudicate ALL trigger plies in
the final 30-ply window (no thinning, no cap) ⇒ ~+15-20 danger states/game
expected at the death boundary, ~123k forks ≈ 35 cpu-h. Amendment A5 +
~40 lines of runner. L20 (danger 384) clears its rider; M2's L20 screens can
start immediately and independently.

## Cost and honesty ledger
Banked worker-time 270.3 cpu-h (projection 241) — EUR 0 actual (blackmage),
~EUR 4.1 cpx62-equivalent vs the EUR 6 tier. Wall ~24 h. Campaign defects
caught by own gates before damage: vacuous shuffle mutant (smoke #1) ·
META freezing run-scoped fields (launch #1) · mis-scoped G-CRN statistic +
imported bar (both-strata BLOCK, A4; R62 banked). Labels validated above the
certified reference on the same-form statistic; all segments kept.
