# PREREG_LABELS — pilot registration (labels-146, 2026-08-21)

Registered BEFORE any label data exists. Timing proof for the commit message:
`experiments/labels146/out/` contains zero `labels_*.jsonl.gz` and zero
`claims_*` files at commit time. Scope: THE PILOT ONLY (~80 states). The
campaign's sampling window and horizon are parameterized here and their values
are FIXED BY PRE-STATED RULES from pilot data + team-lead review; no campaign
harvest runs before that review (team-lead rider on the lane).

## 1. Fixed machinery (sealed lineage)

- Rig: `oracle_arm.py` @ champion-145 d3cb836 content, imported into this
  branch. Labeler fork = the sealed `_fork_label` (H12/oracle lineage),
  future_mode=dist via `dist_seed(seed, ply, sample)`, CRN across candidates
  by construction (sample index ↔ fork_seed, candidate-independent).
- Regime: level=20, model=lulu (honest bursty v1.1), ws=20, wt=0, max_pills=400
  — identical to the bank (`screen_home_states.py`).
- Bank (read-only): champ145 `out/states/` as described in DESIGN_LABELS.md.
- Replay gate at EVERY replayed ply: computed 32-value vector (round 3) ==
  banked `vals` AND computed argmax == banked `a`. Any mismatch aborts the
  seed (exit nonzero, no partial row).

## 2. Pilot sampling rule (mechanical, no discretion)

- S-death: the FIRST 12 topout games in ascending seed order with
  n_plies ≥ 30. Target plies: end−k for k ∈ {1, 3, 6, 10, 15, 20} where
  end = n_plies (so end−1 = the last decision ply). 72 states.
- S-clear: the FIRST 8 cleared games in ascending seed order with
  n_plies ≥ 30; target ply for game i = the banked ply of that game whose
  (vir, dsh) is nearest (L1 distance, ties → earliest ply) to the (vir, dsh)
  of the i-th S-death game's end−10 row. 8 states.
- Total: 80 states. Startup asserts: exactly 12+8 games, exactly 80 targets,
  every target ply ∈ [0, n_plies−1], every seed even in [30000, 32998].

## 3. Pilot label dose

- N = 8 rollout samples per unique candidate.
- H (horizon): every state labeled at H=25. Additionally, S-death k∈{6,15}
  states (24 states) labeled at H=15 and H=40 (same fork seeds) for the
  horizon-choice rule (§4).
- Candidates: ALL legal placements, de-dup'd by resulting-board sha1.

## 4. Pre-stated campaign-parameter rules (computed from pilot, applied
     mechanically; values then reviewed by team-lead before any campaign run)

- HORIZON RULE: campaign H = the smallest H ∈ {15, 25, 40} such that on the
  24 dual-labeled states, Kendall tau between candidate survival rankings at
  H and at H=40 is ≥ 0.85 (mean over states with any spread) AND the claim
  set (per §5's rule at that H) has Jaccard ≥ 0.75 vs H=40's. If no H<40
  passes, H=40.
- WINDOW RULE: campaign S-death window = the contiguous k-range containing
  every pilot k whose claim yield (fraction of S-death states at that k
  producing a §5 claim) is ≥ 10%, extended by 5 on the deep end (end−(kmax+5)).
- COST: campaign labels/hour = measured pilot cpu-s/label; quote the ratio to
  the 1.07 cpu-s/fork prior, not wall-clock (measurement-rules).

## 5. Claim rule + validation endpoint (pilot: report-only sign test)

- CLAIM: state where max_c surv_c − surv_champ ≥ 3 (of N=8) with surv_champ
  ≤ 5. Claimed action = argmax_c surv_c, ties by champion value then champion
  scan order.
- VALIDATION: per claim, arm A = banked outcome; arm B = replay under the
  replay gate to the claim ply, force the claimed action, champion-const
  continuation under the true injection, max_pills=400. Endpoint = game
  failure (topout|stall).
- PASS DIRECTION (report-only at pilot n): among discordant pairs,
  rescued > broken, one-sided sign test; report p, the discordant counts, and
  calibration (mean predicted dsurv of claims vs realized rescue−break rate).
  The CAMPAIGN promotion gate (powered n, exact threshold) is set at team-lead
  review using the pilot's realized discordance — stated now so the pilot
  cannot be read as its own confirmation.

## 6. Mutant kills required BEFORE the pilot harvest (gate_labels.py)

1. G-replay positive control: 3 banked seeds (1 topout, 1 stall, 1 clear)
   replay end-to-end with zero gate mismatches, res + n_plies equal.
2. M-stale kill: the same replay with one action skipped MUST abort at the
   gate (proves G-replay can fail — liveness of the negative).
3. M-dedup-off population mutant: probe pilot states until >=1 DOUBLE-capsule
   state is seen; every double state must show slots/unique >= 1.8 (mirror
   orientations collapse => predicted 2.0), and pooled slots > pooled unique.
   AMENDED pre-pilot-data: the first form pooled 6 states at a 1.15 bar, which
   is double-count luck, not a property (measured 1.098 with 1 double of 6).
   Unconditional assert: within the dedup'd set no two candidates share a
   board key.
4. G-CRN/determinism: labeling one state twice yields identical rows
   (byte-equal JSON); fork seeds for sample s are equal across candidates.
5. M-mimic FAIL_NO_CLAIMS: claim extractor fed champion-value labels on all
   pilot states must yield 0 claims and the verdict line
   `MIMIC FAIL_NO_CLAIMS` (absence-is-not-pass: this is a required FAILURE
   verdict, not a skip).
6. M-shuffle: per-state label permutation (seeded rng, recorded) must yield a
   nonempty claim set (dose check) whose validation shows rescue−break ≤ 0
   or |rescue−break| within noise — registered expectation: it must NOT
   outperform the true labels' rescue−break; if it does, the validation
   instrument is broken and NOTHING promotes.

## 7. Void classes (pilot)

- V1: replay gate mismatch on any pilot seed → machinery defect, fix before
  any data is read.
- V2: zero claims from TRUE labels across all 80 states → the sampling rule
  found no counterfactuals; report the dsurv-vs-k profile and STOP (window
  redesign, new prereg amendment).
- V3: M-shuffle validation outperforms true labels → instrument broken, stop.
- V4: measured cpu-s/label > 4x the prior estimate → budget re-review before
  campaign sizing (not a data void; a costing void).

## 8. What this prereg does NOT license

- No campaign harvest, no fit, no evaluator claims. Pilot dsurv numbers are
  machinery-proving data; the only shippable sentence from the pilot is about
  the VALIDATION MACHINERY (claims exist / mutants killed / forced-move
  rescue direction), each quoted with its n.
