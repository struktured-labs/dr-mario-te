# PREREG_AUTOPSY — L11 CLEAN-FAILURE AVOIDABLE-vs-DOOMED (addendum to PREREG_LABELS)

Registered 2026-08-22 03:5x UTC, BEFORE any autopsy label row exists.
TIMING PROOF at commit time: `experiments/labels146/autopsy/out/` contains
exactly ONE file — `gate_provenance.json` (the population-provenance gate,
§0) — and zero `labels_*`, zero `claims_*`, zero `census.jsonl`.

Scope: the CLOSED population of clean (solo, unpressured, L11, ws=20)
champion failures. Question per game: AVOIDABLE (some legal candidate at some
scanned ply has materially higher rollout-adjudicated survival/clear
probability than the champion's actual pick) or DOOMED (no scanned ply
produces such a candidate). Deliverable is a DEFECT LIST, not a rate.

This addendum inherits ALL of PREREG_LABELS §1 machinery, §6 mutant kills and
§8 non-licensing, and declares FOUR deviations (§1-§4 below). Everything not
deviated from is unchanged.

## §0 DEVIATION 1 (new, forced by logistics) — POPULATION IS REGENERATED LOCALLY

The 53-game census (`experiments/hetzner/results/full/census.jsonl`, 34 stall
/ 19 topout, 45/53 with exactly 1 virus left) exists ONLY on the Hetzner node,
which is untouchable during the c5 burn. Local search NEGATIVE and enumerated
(rule 8): all 42 `dr-mario-*-wt` worktrees, `/mnt/data`, the 20260727 backup
tarball. What IS local: `experiments/adversary/census/` (a 2,100-seed partial,
1 failure) and `results/pressured_drip/` (wrong regime).

=> The population is REGENERATED locally by re-running the identical
`census.py --lo 0 --hi 65536` over the whole 16-bit seed space (aliased twins
NOT skipped — this harness draws viruses from `numpy(seed)`, so twins are
different boards; census.py carries that warning inline).

**PROVENANCE GATE (RUN AND GREEN BEFORE THIS REGISTRATION):**
`exactness_gate.py --seed-list 33269 33754` on today's tree reproduces the
census-era record hashes BIT-IDENTICALLY — full move trace + fatal board +
terminal fields:

| | census-era (`hetzner/gate_local_failures.json`) | today |
|---|---|---|
| digest | `219e2e1518c4bc23…86410f` | `219e2e1518c4bc23…86410f` |
| 33269 (topout, 231 pills, 1 virus) | `6b43df01bf4efa20` | `6b43df01bf4efa20` |
| 33754 (stall, 300 pills, 1 virus) | `2a70ab635a63f84b` | `2a70ab635a63f84b` |

Artifact: `out/gate_provenance.json`. The decide path has not drifted, so the
regenerated failure set IS the census's 53, not a different population.
(⚠ recorded for the file: `gate_remote_failures.json` shows the REMOTE node
once disagreeing with local on 33754's hash and agreeing on run 2 — a stall
nondeterminism sighting on the node, not on this box. All autopsy compute is
local, single-box, so this cannot contaminate the autopsy; it is a reason NOT
to mix node-produced rows in later.)

**COVERAGE IS AN OUTPUT, NOT AN ASSUMPTION.** The census is a producer and the
autopsy a streaming consumer. The report states, as a headline: seeds scanned
/ 65,536, failures found, and — because DOOMED is an absence claim — the
avoidable:doomed split is reported ONLY over games actually scanned, with the
unscanned remainder named. If the node's `census.jsonl` is retrieved by
team-lead before the regen finishes, the two are cross-checked seed-for-seed
on the overlap (a disagreement VOIDS the population, class V-P below) and the
node file supplies the remainder.

## §1 DEVIATION 2 — REPLAY-GATE ANCHOR IS THE MOVE TRACE

Census games have no per-ply 32-value bank, so PREREG_LABELS §1's "computed
vals == banked vals" gate is unavailable. Substitute, at EVERY replayed ply:
computed champion `argmax` action == the census row's trace action, AND at the
end (result, pills, viruses_left, n_moves) == the census row's. Any mismatch
aborts the seed with no partial row. Cell-for-cell strength is preserved
(the trace IS the decision sequence); only the anchor changes.
**M-stale re-proven against THIS anchor**: replaying with one action skipped
must abort at the gate (liveness of the negative), re-run in-regime.

## §2 DEVIATION 3 — RIG CONFIG IS CLEAN SOLO

`pressure=None`, level=11, ws=20, max_pills=300 (`adversary_harness.play_seed`
defaults) — NOT the registered L20 lulu bursty regime. Certified by §1's gate:
if the config were wrong the replay would not reproduce the census outcome.
Rollout futures remain `future_mode=dist` via `dist_seed(seed, ply, sample)`,
CRN across candidates (PREREG_LABELS §1) — the label asks "would a TYPICAL
future rescue this?", which is the decision-relevant question for an agent
that cannot see the stream. The forced-move confirmation (§5) instead uses the
TRUE NES stream, so the two endpoints are deliberately different instruments.

## §3 DEVIATION 4 — STALLS GET A CLEAR-CLAIM, NOT A SURVIVAL CLAIM

34/53 failures are stalls; in clean play every candidate "survives", so dsurv
is vacuous. For stall games ONLY:
- label per candidate = (cleared_within_H_stall, viruses_cleared, pills_used),
  H_stall = 50 plies, forked with `max_pills = ply + H_stall` so the horizon is
  not truncated by the original 300-pill cap;
- CLAIM (stall) = `clear_best >= 6` of N=8 AND `clear_champ <= 2` of N=8.
Topout games keep the registered survival claim, thresholded at §4.
N = 8 samples, H_topout = 25 (the pilot's mechanically-chosen campaign H).

## §4 BACKWARD-SCAN RULE AND PER-GAME VERDICT (mechanical, no discretion)

Anchor ply D: for topouts, the death ply (last trace ply); for stalls, the LAST
ply at which `viruses_left` changed (the 400/300-ply churn tail buys nothing).
Scan plies D−k for k in: 1..8 every ply, 10..24 every 2, 28..48 every 4 —
cap 48 or game start, whichever comes first (~22 plies/game).
- AVOIDABLE at k iff the claim rule fires: topout `surv_best − surv_champ >= 5`
  of 8; stall `clear_best >= 6` and `clear_champ <= 2` of 8. (Topout bar is
  5/8, STRICTER than the campaign's 3/8, because this verdict is per-GAME and
  unvalidated-by-forcing at first pass.)
- GAME VERDICT: AVOIDABLE iff ANY scanned ply fires. Record the DEEPEST firing
  k (largest k = earliest ply = most time before death) and every firing k.
- DOOMED otherwise. DOOMED IS AN ABSENCE CLAIM (rule 8): report the scan
  coverage per game (plies scanned / plies available, candidates enumerated,
  samples), and run the POSITIVE CONTROL — an avoidable game's firing ply must
  re-fire when re-labeled with FRESH sample indices (sample offset +1000).
  If the positive control fails, no DOOMED verdict is reportable.

## §5 VALIDATION OF THE AVOIDABLE SET (forced-move, the lane's own standard)

Per avoidable game, at its deepest firing ply: arm A = the census outcome;
arm B = replay under the §1 gate to that ply, FORCE the claimed action
(argmax of the label, ties by champion value then champion scan order), then
champion-const continuation on the TRUE clean stream to max_pills=300.
- topout: B confirms iff B clears, or B's n_plies exceeds A's by >= H_topout.
- stall: B confirms iff B CLEARS (viruses_left == 0).
Report the confirmation rate with an exact binomial CI. Per PILOT_RESULTS
finding 2, BOTH endpoints are recorded: the label's own claim
(survived/cleared past ply+H) and the game endpoint.

## §6 MUTANTS RE-RUN IN THIS REGIME (required, before any verdict is read)

- **M-mimic** (labels := champion values): must yield ZERO claims and print
  `MIMIC FAIL_NO_CLAIMS`. Absence-is-not-pass: this is a required FAILURE.
- **M-shuffle** (per-state seeded label permutation, seed recorded): must
  produce a nonempty claim set (dose check) and must NOT outperform the true
  labels on §5's forced confirmation rate. If it does, the instrument is broken
  and NOTHING is reported.
- **M-stale** (§1): the trace-anchored replay gate must abort on a skipped ply.

## §7 DEFECT CLUSTERING (the deliverable)

Per FIRING ply, from data in the label rows (champion vals, per-candidate child
boards, child spawn heights `dsh`, virus counts):
(a) **tie-at-the-cliff** — champion pick within 1e-6 of the labeled-better
    candidate's champion value;
(b) **deferred-clearing failure** — labeled-better candidate leaves MORE
    viruses immediately than the champion's pick (the oracle signature);
(c) **spawn-lane self-block** — champion child `dsh` >= labeled-better child
    `dsh` + 2;
(d) **last-virus notch** — game ends with exactly 1 virus, and at the firing
    ply that virus is in a column shorter than the board median height
    (clean-failure-geometry's controlled statistic, not the refuted "buried");
(e) **unclassified residue** — reported as its own bucket, never forced.
Clusters OVERLAP by construction: report the CO-OCCURRENCE MATRIX, not just
marginals. Every board property claimed about the fatal boards carries a
MATCHED WITHIN-BOARD CONTROL (random occupied cells, same board, same count) —
the standing rule for this corpus, which has already overturned two confident
findings.

## §8 VOID CLASSES

- **V-P** (population): regenerated census disagrees with the node's
  `census.jsonl` on any overlapping seed => population void, stop and report.
- **V1**: replay-gate mismatch on any failure seed => machinery defect.
- **V2**: zero claims from TRUE labels across ALL scanned games => report the
  dsurv/clear-vs-k profile and STOP; "all doomed" is then reportable ONLY if
  the §4 positive control fired (otherwise the instrument is untested).
- **V3**: M-shuffle outperforms true on §5 => instrument broken, stop.
- **V4**: M-mimic produces any claim => stop.

## §9 WHAT THIS PREREG DOES NOT LICENSE

No evaluator change, no fit, no campaign re-pointing. The shippable sentences
are: (i) the avoidable:doomed split with its CI and its stated coverage,
(ii) the forced-confirmation rate of the avoidable set, (iii) the defect
cluster co-occurrence table, (iv) the time-before-death distribution — each
quoted with its n. Whether the campaign sampler is re-pointed is team-lead's
call, made AFTER these numbers.

---

# AMENDMENT A1 (2026-08-22, BEFORE ANY LABEL ROW) — THE REGISTERED FUTURE DOSE IS INERT IN CLEAN PLAY

TIMING PROOF: at this commit `out/` contains `gate_provenance.json` and a
partial `census/census.jsonl` (population enumeration only — result/pills/
viruses_left/trace per seed). Zero label rows, zero claims, zero forks run.

**THE DEFECT IN §2 AS REGISTERED.** PREREG_LABELS §1 gets its rollout
stochasticity from `dist_seed(seed, ply, sample)`, and that seed reaches the
rollout at exactly ONE place: `oracle_arm._advance`'s garbage injection
(`PR._inject_garbage(board, seed, ...)` / `inject_bursty_garbage(..., seed,
...)`). **Clean solo has no injection.** The capsule stream inside a fork comes
from the deepcopied `PillDraw` cursor, which is a function of the game seed and
the ply — not of `fseed`. So all N=8 samples of a candidate would be
BIT-IDENTICAL, every label would be 0/8 or 8/8, and §4's thresholds (>=5/8,
6-vs-2) could never distinguish a decision from a coin — a vacuous gate of
exactly the kind this project has shipped before (a dose that never fires).
Caught by reading the dose path before running it, not after.

**A1.1 CORRECTED DOSE — RESAMPLE THE UNSEEN FUTURE.** In clean solo the only
thing the agent does not know is the capsule stream beyond `nxt`. So the fork
resamples precisely that:
- deepcopy the env; place the candidate; **keep `cur` and `nxt` unchanged**
  (both are visible to the champion at the decision ply — resampling them would
  change the decision problem, not the future);
- replace the clone's draw with `PillDraw(NesPillSource(seed=fseed & 0xFFFF))`,
  `fseed = dist_seed(seed, ply, sample)`, so every SUBSEQUENT capsule comes
  from an independent NES stream;
- CRN is preserved exactly as registered: `fseed` depends on (seed, ply,
  sample) and never on the candidate, so candidates are compared on the same 8
  futures.
This is the same question the registered dist mode asks — "would a TYPICAL
future rescue this?" — with the randomness moved to the only channel that
carries any in this regime. Thresholds in §4 are unchanged and now meaningful.

**A1.2 A NINTH, CLAIRVOYANT FORK — reported separately, never pooled.** One
extra fork per candidate continues on the TRUE stream (no swap). It answers a
different and stronger question: on this exact stream, did a one-ply deviation
exist that survives/clears where the champion's pick does not? Reported as its
own column because the two verdicts differ in kind:
- AVOIDABLE-under-clairvoyance is WEAK evidence of a defect (the candidate may
  be collecting luck the agent could not have foreseen) — it is an upper bound
  on what any policy could have done;
- **DOOMED-under-clairvoyance is the STRONG absence verdict**: not even a
  future-reading one-ply deviation saves the game.
The headline AVOIDABLE:DOOMED split is the DIST one (A1.1). The clairvoyant
column is reported beside it, labeled, and the two are never averaged.

**A1.3 NEW REQUIRED GATE — G-DOSE, with its own killed mutant.**
- G-DOSE-LIVE: over the first 20 labeled states, at least one candidate must
  show SPREAD across the 8 dist samples (not all 0, not all N). A dose that
  cannot vary cannot be tested.
- **M-INERT (the defect as a mutant, per test-the-defect-not-the-fix)**: run
  the same 20 states with the stream swap REMOVED — i.e. §2 exactly as
  originally registered. It MUST produce ZERO spread on every candidate. If
  M-inert shows spread, my diagnosis is wrong and A1 is withdrawn; if it shows
  none, the vacuity is proven rather than asserted, and the correction is
  justified on the record.
- G-FORK-INDEP: two deepcopies of the same live env draw IDENTICAL capsules
  from their own cursors when unswapped, and DIFFERENT ones when swapped —
  the deepcopy-shares-the-cursor hazard, asserted not assumed.
Void class V5: G-DOSE-LIVE fails => the labels carry no information in this
regime; report that and STOP.

Everything else in PREREG_AUTOPSY §0-§9 stands unchanged.
