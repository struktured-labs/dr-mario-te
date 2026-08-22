# CLEAN-FAILURE AUTOPSY PLAN (L11, owner directive 2026-08-21) — DESIGN ONLY

Runs AFTER pilot review + promotion-gate amendment, BEFORE campaign harvest.
Question: for every clean (solo, unpressured) champion failure at L11, was it
AVOIDABLE (some legal candidate at some ply has materially higher
survival/clear probability under rollouts) or DOOMED (no candidate's rollouts
succeed — stream/geometry)? Deliverables: avoidable:doomed split with exact
CIs; per-avoidable-game the deepest avoidable ply, time-before-death, champion
pick vs labeled-better pick; clustered defect list; time-before-death
distribution.

## Population

The clean-failure population is CLOSED: 53 games in the full 65,536-seed solo
census (34 stall / 19 topout; 45/53 die with exactly 1 virus left —
dr-mario-clean-failure-rate). Census rows for failures carry the fatal board +
full move trace (census.py keeps fixtures for failures only) and
verify_fixture.py proves boards reload and traces replay. Sources to
enumerate at build time: hetzner results/full/census.jsonl (upper half ran on
the node — pull if not local; rule-8 discipline: positive-control the search,
list unreachable places) + the local lower-half JSONL. Optionally extend with
the regime map's L11 lab-cell failures (regime-141) as a second stratum —
same machinery, separate reporting.

## Spec fit — three deviations from PREREG_LABELS, so a SHORT ADDENDUM
   (PREREG_AUTOPSY) is required before running. It does NOT fully fit as
   registered:

1. **Replay-gate anchor.** Census games have no per-ply 32-value bank. Gate =
   per-ply ACTION equality against the census move trace + terminal
   (res, pills, viruses_left) equality — same cell-for-cell strength, anchored
   on the trace instead of the value vector. M-stale mutant re-proven against
   this anchor.
2. **Rig config.** Clean solo = NO injection (registered spec is the lulu
   bursty regime). One-line config change; G1-equivalent replay gate certifies
   it reproduces the census outcomes exactly.
3. **Stall failures need a CLEAR-claim, not a survival claim.** 34/53 failures
   are stalls: everything "survives" clean play, so dsurv is vacuous there.
   Label per candidate = (cleared_within_H, viruses_cleared, pills_used);
   claim = candidate clears the remaining virus(es) within H while the
   champion's pick does not. Topouts keep the registered survival claim.
   Stall horizon H_stall = 50 (the notch geometry needs a setup + clear
   sequence; priced in the addendum, re-measured before the run).

## Backward-scan rule (mechanical, in the addendum)

From death ply D (topouts) or from the last virus-count-change ply (stalls —
the 400-ply tail is churn; scanning it buys nothing), label plies at offsets
k = 1..8 every ply, 10..24 every 2, 28..48 every 4 (cap 48, or game start).
AVOIDABLE at k iff the claim rule fires with the addendum's threshold
(topout: dsurv >= 5/8 — stricter than the campaign's 3/8 because the
verdict is per-GAME and unvalidated-by-forcing at first pass; stall:
clear_best >= 6/8 with clear_champ <= 2/8). Game verdict: AVOIDABLE iff any
scanned ply fires; deepest firing k recorded. DOOMED otherwise — an absence
claim, so it gets rule-8 treatment: report the scan coverage explicitly and
run the positive control (an avoidable game's firing ply must re-fire when
re-labeled with fresh sample indices).
VALIDATION of the avoidable set (the lane's own standard): forced-move replay
at the deepest firing ply, arm B forced to the labeled candidate, solo clean
continuation — for topouts B must clear or outlive A materially; for stalls B
must clear. Report the forced confirmation rate; mutants M-mimic (zero
claims) and M-shuffle (dose-matched) re-run in this regime.

## Defect clustering (the deliverable is a DEFECT LIST)

Per avoidable ply, from data already in the label rows (banked vals + child
boards + cdsh): (a) tie-at-the-cliff — champion's pick value-tied with the
labeled-better candidate; (b) deferred-clearing failure — labeled-better
candidate leaves MORE viruses now (the oracle signature); (c) spawn-lane
self-block — champion's child dsh >= labeled-better's + 2; (d) last-virus
notch — 1 virus left in a shallow edge notch (clean-failure geometry);
(e) unclassified residue (reported, not forced into a bucket). Clusters
overlap; report the co-occurrence matrix, not just marginals.

## Budget (priors; re-measured at launch)

~53 games x ~22 scanned plies x ~15 dedup'd candidates x 8 samples x ~0.7
cpu-s (L11 clean forks are cheaper than the pilot's L20 pressured 0.718;
stalls at H=50 ~2x) ≈ 40-60 cpu-h ≈ 2-3 h at 20 workers. Fits one evening
beside the campaign; runs under drm-labels-autopsy with the same chain
discipline.

## Why this may reshape the campaign

If the avoidable share is high with a consistent defect cluster, the campaign
sampler should oversample that cluster's signature states (an addendum, not a
rewrite). If ~all DOOMED, the L11 "embarrassment" is stream geometry and the
campaign stays pointed at the pressured regime where the counterfactuals
live.
