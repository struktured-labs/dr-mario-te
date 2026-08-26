# PRE-REGISTRATION — RECON C: anatomy of the dr. lulu dies-ahead corpus

Written 2026-08-09 BEFORE any statistic beyond the raw census marginals
(clear/topout/stall/dies-ahead counts, which were supplied in the task brief)
was computed. Committed before `recon_c_replay.py` is run for data.

Corpus: `experiments/eval47/jointdig/results_hetzner/lulu_census.jsonl`,
champion base arm (ws=20, wt=0, L11), dr. lulu bursty fit
(`results/dr_lulu_20260808_fit.json`), max_pills=300, GARBAGE_MIN_PILLS=25,
DIES_AHEAD_VIRUS_THRESHOLD=12. Snapshot taken while the Hetzner job was still
running; N is reported, not assumed.

## Q0 — what "dies-ahead" is in this rig

`dies_ahead = (res == "topout") and (viruses_remaining <= 12)`. There is no
opponent board; the "lead" is the champion's own remaining virus count out of
48 at L11. Any statement about a "virus lead" is a statement about
viruses_remaining, and will be worded that way.

## Q1 — PRIMARY PARTITION (mechanism, not fitted)

Every non-clear game is assigned exactly one TERMINATION MECHANISM, read off
the rig's own control flow in `p0_ab.play_one` (this is structural, so it
cannot be tuned post hoc):

| tag | condition |
|---|---|
| `T_PLACE`   | `env.step` returned `term` and `info["won"]` false |
| `T_GARB`    | `board.spawn_blocked()` true immediately after a garbage injection |
| `T_GARBCLR` | virus_count hit 0 as a result of the injection (a clear) |
| `T_NOMOVE`  | `_choose_base` returned `None` (no legal action) — the rig records this as `res="stall"` |
| `T_TRUNC`   | env truncation |
| `T_BUDGET`  | the 300-pill loop ran out with viruses remaining |

**DO-NOT-POOL, declared in advance:** `T_PLACE` vs `T_GARB` are different
phenomena (self-inflicted block vs volley-inflicted block) and are never
summed into one "topout" number without also being reported apart.
`T_NOMOVE` vs `T_BUDGET` are different phenomena and are never summed into one
"stall" number. This mirrors the project's clean-failure split (stalls vs
topouts, different geometry) whose pooling is known to hide the signal.

Each cell is cross-tabulated with `dies_ahead` and reported with
viruses_remaining, pills, garbage received, garbage rate in the last 25 pills,
terminal max height, terminal spawn-lane height `max(H[3],H[4])`, holes.
Clears and stalls are the comparison classes.

## Q2 — SUB-STRUCTURE WITHIN DIES-AHEAD

Exploratory and labelled as such: k-means (k chosen by silhouette over k=2..6,
fixed rng=20260810) over z-scored terminal geometry
{spawn_h, maxh, holes, viruses_remaining, jaggedness, pills, garbage_last25}.
The verdict-bearing partition is Q1's mechanism partition; Q2 may only
*describe*. Any Q2 cluster quoted must also be reported as its mechanism mix,
so a reader can see whether it is just Q1 re-discovered.

## Q3 — EVAL vs HORIZON vs MODEL (method inherited from Stage 1f)

Stage 1f (`dr-mario-eval-headroom-stage1`) defined:
HORIZON = what extra DEPTH buys with the current leaf; EVAL = what a PERFECT
leaf buys on top of that; MODEL = the search simulating a different world than
the one it is played in. Stage 1f's ruler was pills-of-regret on a clean
corpus (99.52% cleared) and is silent about the death regime, so the same
three-way question is re-asked with a DEATH ruler:

For each analysed failure, walk BACKWARD from the terminal ply over a window
of W = 12 plies. At ply t, for every legal action a (all 32 expanded, illegal
skipped):

* fork: apply `a` to a CLONE of the real pre-decision board, then continue
  with the REAL champion policy and the REAL lulu injection schedule for
  S = 30 further pills;
* `survives(t, a)` = the fork neither tops out nor runs out of legal moves
  within S pills (clearing all viruses counts as surviving).

Definitions (each failure gets exactly one):

* **EVAL-ADDRESSABLE**: ∃ t in the window and ∃ a with `survives(t,a)` while
  the champion's own action at t does not. A perfect leaf at the SAME depth
  would have ranked `a` above the champion's move, so no extra depth is
  required — this is exactly Stage 1f's EVAL arm (V(oracle) − V(dₙ)) with a
  0/1 survival value. Recorded: earliest rescuing ply (`t_deep`), latest
  (`t_cheap`), rescue count, and the rescuer's rank in the champion's own
  value order.
* **MODEL**: the terminal event is `T_GARB` AND the same board survives S
  pills when the volley is suppressed. The depth-3 search contains no garbage
  model at all, so a leaf evaluated on the post-move board is being asked
  about a world it was never shown. Reported separately as
  MODEL∩EVAL-ADDRESSABLE (a lower spawn lane would have absorbed the SAME
  volley — an evaluator CAN price it) and MODEL-ONLY (nothing in the window
  survives the volley).
* **BEYOND-W / FORCED**: no `a` at any t in the window survives. The position
  was already lost more than W plies before the end, or is genuinely forced.
  This is charged AGAINST the evaluator's reachable prize; it is the
  horizon-like residue at this window.

Sensitivity, pre-declared: W ∈ {6, 12} and S ∈ {15, 30} are both reported;
the headline uses W=12, S=30. Larger W can only INCREASE the addressable
count, so the headline is a LOWER bound on eval-addressability and an UPPER
bound on BEYOND-W.

## Q4 — TARGET

Target class = the Q1 mechanism cell with the largest ABSOLUTE
EVAL-ADDRESSABLE count. Reported as: games in the sampled census, % of all
rows, % of the 12.44% dies-ahead, with a seed-level bootstrap 95% CI
(B=2000, rng=20260811) on every addressable fraction. Also reported, because
of the STRUCTURAL LAW on breakage: the addressable prize expressed as games
per 9,044 census rows, alongside the clear-game population that any always-on
change would have to leave untouched.

## GATES — a check that cannot fail is not a check

* **G1 CENSUS FIDELITY.** The instrumented replayer must reproduce the census
  row (`res`, `pills`, `garbage`, `dies_ahead`) for EVERY replayed seed. Any
  mismatch aborts the analysis.
* **G2 G1 CAN FAIL (killed mutant).** A mutant replayer with ws=19 instead of
  ws=20 must produce a row that DISAGREES with the census on ≥1 gate seed.
  Without this, G1 is vacuous.
* **G3 FORK SOUNDNESS (the deepcopy pill-cursor trap,
  `dr-mario-deepcopy-pill-closure`).** A fork that re-applies the champion's
  OWN recorded action and then continues must reproduce the real game's
  remaining trajectory EXACTLY (result, pills, garbage). MUTANT: a fork whose
  pill source is NOT fast-forwarded to `2 + pills_placed` draws must FAIL that
  identity check. Both required; the identity check alone is not a check.
* **G4 NON-VACUITY.** At least one alternative action on at least one seed
  must change the outcome. A probe that never flips anything is measuring
  nothing.
* **G5 LABEL QUALITY.** The corpus is the champion's own census; clear rate is
  reported (it is ~79.8%, far below the >96.9% rollout-screening bar) and this
  report therefore makes NO claim of the form "the champion's decisions here
  are good labels". The corpus is used to describe FAILURES, not to fit a
  policy. Stated so a later lane cannot mistake it for training data.

## What would make this report WRONG

* If EVAL-ADDRESSABLE is high because S is too short (a fork "survives" 30
  pills and then dies anyway): reported by re-running the winners at S=60 on a
  subsample.
* If the fork's garbage schedule diverges from reality merely because the
  action changed: this is intended (garbage is triggered by the AI's own
  clears) but means an "escape" may be escaping the volley by not clearing.
  The fraction of rescues that clear LESS than the champion's move is
  reported as `rescue_by_not_clearing`.
