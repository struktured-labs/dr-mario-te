# PRE-REGISTRATION — vocab2 Phase 2 feature battery (written BEFORE any statistic was computed)

Date: 2026-08-09. Dataset frozen at commit f9c502f (fatal_windows.npz / controls.npz,
census sha256 349f81d7...). This file is committed before `feature_battery.py --stats`
is run; any deviation must be reported as such.

## Contrast

PRIMARY: decisions of TOPOUT games (890 games x last K=10) vs decisions of CLEARED
games (1,000-game pool, all decisions), matched within the phase-1 pre-registered
stratum key (stratum_h, stratum_v, stratum_g) = (max_height, min(vir,30)//3,
min(garbage_cum,48)//8) measured on the PRE-decision board. Only strata containing
both classes enter; the excluded fatal fraction is reported (it is the
extreme-height region cleared games never visit — itself signal, reported not
scored).

SECONDARY (reported, no verdict): (s1) stall-game decisions, same battery;
(s2) topout decisions with t_to_end<=2; (s3) top-3 candidates split by height band
h<=9 / 10-12 / >=13 (the explicit height-x-pressure interaction check).

## Statistic

Stratified AUC, per-fatal-decision weighted: mean over eligible fatal decisions of
P(feature_fatal > feature_control within stratum) + 0.5*P(tie). Effect = |AUC-0.5|.
CI: cluster bootstrap over GAMES (fatal seeds and control seeds resampled
independently, B=200, rng=20260810), percentile 95%.

## Features

BASELINE 11 (the wall re-test): MAXH HOLES TOPRISK SPAWN SETUP MATCHED BURIED
RDYEXT VRDY CROSS POLL via fast_rtl_x._base_scan(variant "winner" flags) on the
POST-placement board of the CHOSEN move (identical to holepoker/
feature_separability.py's definition). Also reported in champion-preferred
orientation (does the fatal move look BETTER on the champion's own terms?).
Preferred signs: MAXH- HOLES- TOPRISK- SPAWN- SETUP+ MATCHED+ BURIED- RDYEXT+
VRDY+ CROSS+ POLL-.

BASELINE FLOOR = max over the 11 of |AUC-0.5| (point estimate).

CANDIDATES (post board of chosen move; H = column height profile, row 0 = top;
"pre" = board before the decision):
- a_topout_dist = 16 - max(H)            [mirror of MAXH; internal consistency: AUC must equal 1-AUC(MAXH)]
- a_d_maxh      = max(H_post) - max(H_pre)   [the DELTA is the new content]
- b_spawn_prox        = occupied cells rows 0-2 x cols 2-5
- b_spawn_prox_strict = occupied cells rows 0-1 x cols 3-4
- c_das_reach   = # columns path-reachable under the geometric DAS proxy:
                  col c reachable iff for all j on the path from col 3 to c,
                  H[j] <= 15 - |j-3|//2  (L11: fall 13f/row vs DAS ~6f/col => ~2
                  cols per row of fall; single-cell proxy, declared as such)
- c_d_das_reach = das_reach(post) - das_reach(pre)
- c_nlegal_probe = engine-true legal placement count on the post board
                  = 2*#{c in 0..6: max(H[c],H[c+1]) < 16} + 2*#{c: H[c] <= 14}
                  (proved identical to the chooser's n_legal on all pre boards, G4)
- c_d_nlegal    = c_nlegal_probe(post) - n_legal(pre, stored)
- d_gvuln_mass  = sum_c max(0, H[c]-11)   [volley-vulnerability mass; drip volleys
                  land uniformly, each adds 1 to a column]
- d_crit_cols   = #{c: H[c] >= 14}
- d_spawn_h     = max(H[3], H[4])
- e_escape_routes = #{c: H[c] <= 10}      [two vertical pills land below row 4]
- e_escape_reach  = #{c: H[c] <= 10 AND path-reachable}
- x_hvar        = population variance of H  [the Mode-B named candidate]
- x_jagged      = sum_c |H[c+1]-H[c]|

## Verdict rule (pre-registered)

A candidate SEPARATES WHERE THE 11 FAIL iff BOTH:
 1. lower bound of its 95% cluster-bootstrap CI for |AUC-0.5| > BASELINE FLOOR
    (point estimate), AND
 2. its point |AUC-0.5| > 95th percentile of the family-wise max-|AUC-0.5| from
    200 within-stratum label permutations over ALL battery features.
Otherwise: NONE SEPARATES. CI-overlap alone is NOT a verdict in either direction.

## Gates (all must pass BEFORE results are read; results discarded otherwise)

G1 positive control: leak feature = label + N(0,0.1) must give AUC > 0.95.
G2 negative control: 200 within-stratum label shuffles -> every real feature's
   shuffled AUC within the permutation band (pipeline does not invent separation).
G3 implementation killed-mutants on synthetic boards (each new feature has a
   hand-computed case AND a deliberately-broken variant that must give a
   DIFFERENT answer on it): das_reach (allow=16-d//2 mutant), escape_routes
   (<=11 mutant), spawn_prox (rows 0-3 mutant), gvuln (threshold-12 mutant),
   hvar (ddof=1 mutant), jagged (signed-sum mutant, asymmetric board).
G4 cross-checks vs independent stored data, ALL 133,690 decisions: base_scan
   MAXH(pre board) == stored max_height; NVIR(pre) == stored viruses;
   c_nlegal_probe(pre) == stored n_legal; chosen action == nanargmax(cand_vals);
   chosen action legal (expand ok) for every decision.

## Quick screen (only if verdict = separates)

Winner wired into choose_base32 as a penalty term, n=240 paired seeds vs base
under the same drip regime; PRIMARY endpoints pre-registered as dies-ahead count
+ bad-ends (topout+stall) count, paired. To be pre-registered in detail (dose,
seeds) in this file BEFORE that run starts.
