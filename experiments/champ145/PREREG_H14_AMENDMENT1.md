# PREREG H14 — AMENDMENT 1: the H14a configuration choice rule

Written 2026-08-21 ~20:2x EDT, AFTER team-lead sign-off (riders 1+2),
BEFORE reading out/screen_result.json (the final 1,500-seed screen). Timing
proof: this file is committed in the same tree state in which
out/screen_result.json has never been opened by this lane; the analyze
chain wrote it minutes ago and only its n=62 INTERIM precursor was ever
displayed (disclosed below).

## Disclosure (rider 2 honesty)

The interim analyzer output at n=62 games was seen by this lane before this
amendment: gate_open 51.4%, tie_dedup_of_all 2.5%, theta_dose table
(0.0:18.47%, 0.5:18.47%, 1.0:18.94%, 1.5:18.94%, 2.0:19.53%, 5.0:21.27%,
10.0:23.85%), strat tie rates, and the h14c "always" flip column for doses
1-16. NO outcome-linked column exists anywhere in the screen (the screen
banks champion-const games only; no rollout, no fork label, no fair gain),
so nothing verdict-relevant CAN be unblinded by the screen — the choice
rule below therefore keys only on dose/population columns by construction.

## The H14a configuration (one variable vs certified H12)

All certified knobs FROZEN: topk=4, horizon=15, fork_samples=5,
theta_margin (fork-progress override gate) = 0.5, future=dist, gate
predicate unchanged (d_spawn_h>=12 OR viruses<=8).

ONE change: the TRIGGER widens from "exact top-2 champion-value tie" to
"top-2 champion-value margin <= eps" (eps=0 is bit-identical to certified
H12 — the identity gate proves it).

## The registered choice rule for eps (mechanical, dose-columns only)

estimated_dose(eps) = tie_dedup_rate_of_all
                      + (theta_dose_of_all_plies[eps] - theta_dose_of_all_plies[0.0])

(the theta_dose column is raw-margin based; its eps=0 bucket is
mirror-duplicate-inflated ~7.5x, so the exact-tie mass is replaced by the
board-dedup'd rate and only the INCREMENT above eps=0 — genuinely distinct
values, hence distinct boards — is added.)

eps* = the LARGEST eps in {0.5, 1.0, 1.5, 2.0} with estimated_dose(eps) <= 4.0%.
If estimated_dose(0.5) > 4.0%: NO eps qualifies -> do not improvise; report
to team-lead and re-amend. If estimated_dose(eps*) < 2.0%: the candidate is
below the testability floor -> same escalation.

Window rationale (pre-stated): floor 2% = the argmax-flip testability bar
(dr-mario-spawn-lane-gate-probe). Cap 4% = the churn wall — stage-2 measured
~2% ply dose reshuffling ~20% of game outcomes and making a 1pp clear guard
unreachable at N=3,000; at >4% the L11 guard CI at feasible N cannot close
and undirected churn dominates any directed signal. Largest-within-window
because the trigger's overrides remain filtered by the UNCHANGED
theta-margin fork-progress gate (the directed part of H12), so added
trigger dose is opportunity, and dose buys MDE.

## Implementation note

H12Arm gains trigger_eps=0.0 (additive; default reproduces fv[0]!=fv[1]
exactly since eps=0 makes `fv[0]-fv[1] > 0` the same predicate);
run_h14.py threads --trt-trigger-eps. Base arm never sets it.

## Rider 1 (carried into the registered prereg verbatim)

The -2.0pp L11 guard margin is the statistical bar; if the realized L11
delta point estimate is worse than -1.0pp, the H14 verdict reports GO/NO_GO
as registered while the PROMOTION decision escalates to the owner with both
numbers side by side.
