# Tier 3: Adversarial Opponent AI — champion death-rate exploit search

## The target

Champion = `fast_rtl_x.variant("winner")` + `cascade_stranded_x.StrandedChainD3Decider`
(`w_chain=180, ws=20`) -- h2h_vs.py's `"strand180_20"` pattern, matching the
silicon build `NES_stomper180s20_20260804.rbf`. `eval47/ab47.py::_choose_base`
tests the same `ws=20` term in isolation (base-only, no chain) as a cheaper
mirror proof; the deployed VS decider is the chain180+stranded combination
reproduced here (see `adversary_search.py`'s module docstring for the full
reconciliation).

Objective is NOT adversary win rate. In priority order: (1) champion DEATH
rate (loses via topout / no-move -- board destruction, not merely outraced by
a clear), (2) champion DIES-AHEAD rate (topped out while still having fewer
remaining viruses than the opponent -- proof of a pure pressure kill, not
incompetence), (3) champion's own pills-to-clear on games it still wins.

## Program structure (mid-course correction from the team lead)

Originally scoped as evolutionary search only. Restructured mid-flight to
SEARCH-GENERATES -> POLICY-DISTILLS: the evolutionary search remained the
BASELINE arm, and a second arm is an off-policy LEARNED adversary trained on a
mix of the evolutionary search's own rollouts, broadly-sampled random
adversary-parameter rollouts (explicit exploration/diversity), and self-play /
native-d1 rollouts (negative-heavy calibration data). Cost was explicitly NOT
a constraint on the learned adversary (a later correction from the owner) --
it is an offline oracle, never shipped, never a "ship gate".

**hole-poker's killing-line demonstrations were NOT available to train on** --
see the coordination section. Its independent numbers were used as a
cross-check instead (see below), which turned out to be the most valuable use
of that coordination.

## Policy encodings

**Evolved (arm c):** 5 free integers on top of the champion's own depth-3
search machinery: `(w_chain, ws, w_press, w_hold, w_bigsq)`. Full mechanism
descriptions in `adversary_search.py`'s docstring:
- `w_press`: scales a clearing placement's value by `opp_maxh * cells` --
  price a shallow clear against a short opponent low, a big clear against a
  tall opponent high.
- `w_hold`: bonus on NON-clearing candidates while the opponent is still
  short (< a fixed threshold H0=8) -- makes patient building relatively more
  attractive than cashing in a small clear too early.
- `w_bigsq`: pure preference for bigger single clears (`cells^2`), independent
  of opponent state.

Column TARGETING is deliberately excluded -- the ROM's garbage columns are
`frameCounter & 3`-keyed, not player-chosen; giving the adversary that knob
would model a capability the disassembly doesn't support (the exact
ROM-TRUE-ATTACK-RULE mistake this project has paid for before).

`selfcheck()` (adversary_search.py) proves: (a) at
`ws=w_press=w_hold=w_bigsq=0` the kernel is bit-identical to
`cascade_chain_x._choose_d3_chain`; (b) at the champion's own values it is
bit-identical to `StrandedChainD3Decider`; (c) each of the three new knobs
moves >=1 decision on a 200-board random corpus when turned on alone. All
three passed before any search ran.

**Learned (arm d):** depth-1 candidate enumeration (`_leaf_chain`, the same
primitive the champion's own root loop uses per candidate) scored by a
trained value model -- P(champion dies within 15 pills | features). 15
hand-built features (own/opp column heights average/max/spawn-lane, holes,
virus counts, this-move cells-cleared/chain-depth, running attack-sent/
received counters, ply fraction) -- see `adversary_features.py`. Model:
sklearn `HistGradientBoostingClassifier` -- chosen over a deep net because
the feature space is 15-D and hand-built (exactly the tabular regime where
tree ensembles are the sample-efficient default), it is directly inspectable
via permutation importance (the deliverable IS "what did it learn"), and it
trains in under a second, letting iteration stay cheap.

An important disanalogy, stated explicitly: this project previously REFUTED
compressing the champion's OWN planner into a learned model (memory
`dr-mario-imitation-fails` -- port the planner, don't compress it). That
finding does not transfer here. The champion's compressed copy had to be
CORRECT to be useful -- a wrong copy plays worse than the real search, full
stop, with nothing to catch the error. The adversary side only has to be
SUGGESTIVE: every game the learned adversary plays is replayed and scored by
the real `vs_harness` ROM-true match loop before any number counts, so a
noisy prediction costs a wasted rollout, never a silently-worse deployed
decider. Different risk profile, not a reversal of the earlier finding.

## Exploration / exploitation

- Rollout data generation (`gen_rollout_data.py`) deliberately mixed
  behaviour policies (40% evolved-family perturbations, 30% broad random
  vectors, 15% self-play, 15% native-d1) rather than sampling only from the
  evolved adversary's own narrow style.
- The baseline evolutionary search (`search_adversary.py`) uses a single
  random-vector injection per generation plus a self-adapting step size.
  `search_adversary_v2.py` adds explicit periodic RESTARTS (global-best
  tracked separately so a restart never loses the best-found candidate) and a
  NOVELTY bonus (L2 distance in bounds-normalised parameter space from every
  previously-accepted parent) -- built and selfcheck-validated, but NOT
  separately executed this session: the shared box's contention (below) made
  a second concurrent search an irresponsible use of already-scarce cycles.
  It is ready to run; see its docstring for the design.
- The learned adversary's `epsilon` parameter supports softmax sampling over
  predicted kill-probability for iterative data regeneration; the arm
  reported below uses `epsilon=0` (pure argmax).

## THE KEY FINDING, stated first: the champion is very hard to kill

**Zero of three independently-run search methods found a champion death rate
materially above the self-play baseline, on the samples this session could
afford.** Every method agrees, to within the (wide, small-n) noise:

| Method | Champion death rate | n | Source |
|---|---|---|---|
| Self-play baseline | 0.0% [0%, 0%] | 15 seeds | this tier, quick_fiveway.py |
| Native-d1 (weak strawman) | 0.0% [0%, 0%] | 15 seeds | this tier |
| Evolved adversary (best found) | 0.0% on this sample; 5.0% [0%, 12.5%] on its own training seeds | 15 held-out / 20 train | this tier |
| hole-poker beam search (independent, oracle-based single-agent planning) | 7.1% (1/14) | 14 seeds | hole-poker's `vs_poker.json`, read directly |
| hole-poker control (no search) | 0% champion topouts (0/14; outcomes were champ_clear x6, adv_clear x4, adv_dead x4) | 14 seeds | hole-poker's `vs_poker.json` |

Two independently-built approaches (this tier's two-sided evolutionary/VS-
harness search, and hole-poker's single-agent oracle-planning beam search)
land on the SAME order of magnitude: low single digits to ~7% at best, and
often 0% on modest samples. That agreement, arrived at independently, is the
strongest evidence in this report. **This is a genuine negative finding: at
this policy class (garbage-timing / attack-shaping adversaries with unbounded
think time), the champion has no large, easily-exploitable strategic
weakness.** It is not proof of NO weakness -- see the overfitting and n
caveats below -- but three separate hunts converged on "hard to kill," not
"here is the exploit."

## The DMUU reframing, and what it changes about how to read a kill

Mid-session the owner reframed this program as decision-making under
uncertainty, which sharpens what a "kill" should even mean here. The champion
maximises EXPECTED CLEARING PROGRESS (its coefficients were tuned on clear
rate / pills-to-clear). The actual goal is P(WIN), and death is an ABSORBING
state -- those objectives coincide almost everywhere but can diverge sharply
near the ruin boundary: with a rising stack, an expected-progress-maximizing
agent keeps taking the highest-value placement; a win-probability-maximizing
agent would sometimes trade value for survival margin once the downside is
catastrophic and irreversible. "Dies while ahead" (already a tracked metric
in this tier's harness, see `vs_run.py::_outcome`'s `dies_ahead`) is close to
a definition of risk-neutral behaviour near ruin. So: when an adversary
finds a kill, the diagnostic question isn't just "did it die" but "at the
decisions leading up to death, did the champion's OWN evaluation have a
materially safer option and rank it below a riskier, higher-value one?" If
yes, that's evidence of OBJECTIVE mis-specification (fixable by a
risk-sensitive objective -- survival-weighted value, a CVaR-style downside
penalty, or optimizing P(win) directly) rather than an eval-coefficient gap
(fixable, if at all, by retuning existing hand terms).

**Coordination note**: `experiments/portfolio/failure-objective/REPORT.md`
(a parallel lane, already landed) ran exactly the "retune existing hand
terms toward survival" experiment -- a 6-point coordinate scan around the
champion's own coefficients (`ws` at 0.5x/2x, `R_BURIED` at 0.5x/2x,
`R_SETUP` at 0.5x/2x) scored on bad-end rate under human-cadence bursty
pressure. **Every arm was a WASH against the shipped point** (n=40,
paired-bootstrap CIs all straddling 0) -- no local retuning of the existing
terms beats the champion's own survival rate. That result and this tier's
"no adversary found a large exploit" both point the same direction, and
BOTH are consistent with (not proof of) the DMUU hypothesis: if the gap is
in the OBJECTIVE rather than the coefficients, no amount of nudging the
existing hand terms should find it -- which is exactly what both lanes
observed. Neither lane, on its own, distinguishes "no gap exists" from "the
gap needs an objective change, not a coefficient change" -- the kill
classification below is the first piece of direct evidence that tries to.

### Kill classification: outplayed vs. risk-neutral choice

Built `instrumented_champion.py` (a mechanical copy of the champion's own
root loop that returns EVERY legal candidate's value and resulting
spawn-lane headroom, not just the argmax -- `selfcheck()` proves its #1
candidate always equals `StrandedChainD3Decider.choose()`, so it sees
exactly what the champion saw, nothing more) and `classify_kills.py`, which
replays each known death game and asks, at every champion decision in a
window before the topout: among the FULL candidate set, did a materially
SAFER placement (lower spawn-lane height -- `spawn_blocked()`'s own row0-
cols{3,4} trigger, so this is the direct topout-proximity metric) exist?
Three-way classification per decision:

- `no_escape` -- no legal placement (of ~28-30 available) had lower
  spawn-lane height than the one chosen. Physically boxed in.
- `cheap_risk_neutral` -- a safer placement existed WITHIN the champion's
  own near-optimal band (its own top-8, the same cutoff its ply-2 pruning
  uses) -- declined a nearly-as-good, safer move for a slightly better one.
- `expensive_risk_neutral` -- a safer placement existed somewhere in the
  full candidate set but scored far enough below the top-8 that a pure
  expected-value argmax would never reach it regardless of the safety gain.
  This is the sharpest evidence for the DMUU framing: the champion isn't
  choosing between two similar options, it's choosing between "safe at a
  real, priced cost" and "best score, unsafe" -- exactly the choice a hard
  survival floor would override and a pure risk-neutral maximizer never will.

**Replayed all 4 concrete champion-death games this session's compute
produced** (2 from the off-policy rollout corpus, 2 from the evolutionary
search's own training seeds 5005/5012 -- both of the latter also independently
flagged `dies_ahead=1`, i.e. the champion had FEWER remaining viruses than
its killer at the moment it died). Classified the last 40 champion decisions
before each topout (widened from an initial 3, then 15, after both showed
spawn-lane height already stuck at 12-15 for the entire window -- the
"still had real options" period turned out to extend much further back than
expected):

```
no_escape:              156
cheap_risk_neutral:        2
expensive_risk_neutral:    2
                     (n=160 decisions across 4 games)
```

**Reading it plainly**: the dominant pattern (97.5% of decisions examined)
is `no_escape` -- once the champion's spawn-lane height reaches roughly
12-13, EVERY one of its ~30 legal placements keeps or raises that height for
many consecutive plies in a row (one game shows 30+ consecutive `no_escape`
decisions). At that point the champion genuinely has no good option; this is
NOT a risk-neutrality failure, it's a structural inevitability once the
stack reaches that state (the more interesting question this raises -- when
and why did the stack get there, likely much earlier in the game, is outside
what this small sample can answer).

**But 4 of 160 decisions (2.5%) DID show a real, priced escape the champion
declined**, and both instances sit right at the edge of the no-escape
region -- the last moment before the situation became fully locked-in, not
buried in the middle of it:
- Game `evosearch_death_5012`, plies 74-75: a candidate existed with 3 more
  rows of spawn-lane headroom (`spawnh` 9 vs the chosen 12), ranked 8th-13th
  by the champion's own value (i.e. `expensive_risk_neutral` -- well outside
  its near-optimal band), at a real cost (15-24% of that decision's full
  value range).
- Game `rollout_death_2` (seed 42357), the LAST champion decision before its
  topout: a candidate existed with 2 more rows of headroom (`spawnh` 14 vs
  the chosen 16 -- 16 is essentially the top row), ranked 2nd by the
  champion's own value (`cheap_risk_neutral` -- barely outside the argmax),
  at a val cost of 147 (15.6% of that decision's value range).

**Honest read, n=4 games / 4 flagged decisions**: this is an illustration of
a method that works and finds real instances of the DMUU signature, not a
statistically powered claim about how OFTEN it happens. What it does show:
the risk-neutral-choice pattern is real and detectable in this data, it
clusters at the transition INTO the locked-in state rather than throughout
it, and in the one case with a big headroom gain available (3 rows, game
5012) the champion still took the higher-value option across two consecutive
decisions. Whoever runs a larger death-game corpus next (the highest-value
use of more compute for this specific question) should run this same
classification and expect the SHAPE of the finding -- rare-but-real risky
choices concentrated near the transition into "no_escape" -- to matter more
than the raw count. Full per-decision data: `kill_classification_result.json`.

## Four-way comparison (held-out seeds 6000-6014, n=15 -- see resource note)

```
a_selfplay:     death=0.0%  [0.0%,0.0%]   win=50.0%  outraced=50.0%  n=15
b_native_d1:    death=0.0%  [0.0%,0.0%]   win=100.0% outraced=0.0%   n=15
c_evolved_adv:  death=0.0%  [0.0%,0.0%]   win=96.7%  outraced=3.3%   n=15
d_learned:      death=0.0%  [0.0%,0.0%]   win=100.0% outraced=0.0%   n=15
```

Arm (d) completed after ~13 minutes (Python-level per-candidate sklearn
inference under contention, vs the numba-jitted arms' ~2.5 minutes each --
see resource note). At n=15 it lands exactly on the native-d1 and self-play
baselines: no deaths, champion wins every game by clearing. Consistent with
the overall finding, though worth flagging its own limitation: the model was
trained on only 2 death-games total, so it may not have learned much of a
genuinely threatening policy yet, distinct from "the champion is unkillable
against this specific learned policy."

Arm (c) is the evolved adversary at its best-found vector
`(w_chain=234, ws=20, w_press=-31, w_hold=233, w_bigsq=37)`, found at
generation 3 of the evolutionary search and never beaten through generation 7
(where the search was stopped to free capacity for measurement -- see below).
On its OWN 20 training seeds it scored 5.0% death rate [0%, 12.5%] (1 death in
20 paired seeds); on this DIFFERENT n=15 held-out block it scored 0/15. Both
are consistent with a true rate in the low single digits and this small n --
not evidence of overfitting by itself, but also not a confirmed effect (see
below).

## Search trajectory (search_adversary.py, run 1, gens 0-7)

```
gen 0  init                                        death=0.0%
gen 1  (234,...)->(191,22,-76,194,50)  ACCEPTED     death=0.0%
gen 2  ->(125,9,-50,192,50)            ACCEPTED     death=0.0%
gen 3  ->(234,20,-31,233,37)           ACCEPTED     death=5.0%   <- best found
gen 4  rejected, kept parent                        death=0.0%
gen 5  rejected, kept parent                        death=0.0%
gen 6  rejected, kept parent                        death=0.0%
gen 7  rejected, kept parent                        death=0.0%
```

Stopped at generation 7 of a planned 18 to free CPU for measurement, an
anytime-safe interruption per the design (checkpointed every generation). The
search plateaued after gen 3 -- four consecutive generations found nothing
better, consistent with the "hard to kill" finding above rather than a search
that needed more budget to find a large effect. `search_checkpoint.json` and
`search_log.jsonl` hold the full record; `search_adversary_v2.py`
(restarts + novelty) is built and ready if a future pass wants to rule out a
local-optimum explanation more thoroughly.

## Learned model quality (offline validation, NOT the same as the VS-match arm above)

Trained on `/mnt/data/drmario_adversary_t3/replay_buffer/` (43,085 examples
from 472 rollout games mixing the four behaviour policies).

**The central data-sparsity finding**: only **2 of 472 games** (0.4%) had the
champion die at all. This is the same "hard to kill" finding from a different
angle -- it directly limited what supervised training could learn. A first
naive seed-level train/held-out split put BOTH positive-bearing games on the
held-out side purely by chance (0 positives in training, an unusable model,
and a scorer crash) -- fixed by stratifying the split so positive-bearing and
negative-only seeds are each divided across train/held-out separately
(`train_adversary_model.py::seed_split`, now guarantees >=1 positive seed per
side whenever >=2 exist). After the fix: 1 positive-bearing game in training
(16 rows, `LABEL_HORIZON=15`), 1 in held-out (16 rows).

- TRAIN: AUC=1.00, AP=1.00 (expected -- trivial to memorize the single
  training death's trajectory).
- **HELD-OUT** (a DIFFERENT death game the model never saw): AUC=0.878,
  AP=0.055 against a 0.18% base rate -- a genuine ~30x lift in average
  precision, i.e. the model generalises SOME real signal beyond memorizing
  one game, even from a single training example of the target class. Treat
  this as directional, not a robust trained model -- n=1 training positive
  game is about as thin as supervised learning gets.
- Permutation importance (held-out, n=4000 subsample, n_repeats=2): by far
  the strongest feature is `own_virus` (drop in AP: -0.081) -- the
  adversary's OWN remaining virus count is the most informative signal for
  predicting whether the champion is about to die. `atk_sent_running` is
  second (-0.005). `opp_avgh`, `opp_spawnh`, `own_spawnh` show small positive
  importance. Most others are ~0 -- unsurprising given how few positive
  examples exist to inform which features generalise. Full table in
  `logs/train3.log`.

## Overfitting check

- **Evolved adversary**: 5.0% on its own 20 training seeds vs 0.0% on the
  n=15 held-out block above. The GAP (5 points) is within noise at these
  sample sizes for a rate this low (a single seed flips the observed rate by
  5-6.7 points either way) -- not evidence of overfitting, but not evidence
  of a robust effect either. A larger held-out run (the originally-planned
  n=80, blocked by shared-box contention this session -- see resource note)
  is needed to separate "no effect" from "true rate ~5% and this sample was
  unlucky."
- **Learned model**: held-out AUC/AP computed on a GAME the model's training
  never touched (seed-level split, not row-level) -- the 30x AP lift is
  therefore a genuine held-out result, not leakage, but it rests on one
  training positive and one held-out positive, the thinnest possible n.

## Transfer test: NOT RUN this session

Planned (best evolved adversary vs the pre-strand20 `ChainRewardD3Decider`
lineage, seeds 7000-7059, against that lineage's own self-play control) but
cut for time given the resource constraints below and the fact that arm (c)
itself showed no held-out effect to transfer. `vs_run.py::pre_strand20_champion`
and `batch_run.py`'s `champ_kind="pre20"` plumbing are built, selfcheck-
verified (mirror match confirmed exact 50/50 self-play split), and ready:
`measure_fourway.py` still contains the transfer-test code path (currently
using reduced `n` via `FOURWAY_FULL=1` env var to restore full sizing) for
whoever continues this with more compute headroom.

## Coordination with hole-poker

Messaged directly early in the session asking: (1) the schema for real
killing-line demonstrations once available; (2) whether a persistent
champion-move memo database existed on `/mnt/data`; (3) whether hole-poker's
"kill" claims get replayed through the real `vs_harness` match loop before
being called equivalent to this tier's "champion death". No reply received by
report time. Read hole-poker's `results/` directly instead (their `deaths.jsonl`
and `vs_poker.json`), which turned out to be the more useful thing regardless
-- see the key finding above. `results/deaths.jsonl` had 5 entries at last
check, all `result="stall"` (hit the 300-pill cap, long streaks of one
repeated action -- reads as oscillation, not a garbage-induced kill), i.e. no
usable killing-line demonstrations were ever produced for training data. Their
`vs_poker.json` (single-agent beam search + a "control" mode) IS a live-look
at genuine kills and controls, and is what the key-finding table above uses.
NOTE the methodology difference: hole-poker's search gives the champion a
constructed/injected board and plans against it as an oracle (no live
opponent); it is not confirmed (by either agent, this session) that its
"killed":true games would also be two-sided VS wins under the real garbage
channel. Flagged as an open question in the coordination message; treat the
7.1% figure as corroborating evidence of DIFFICULTY, not a confirmed
silicon-equivalent kill count.

## Resource note (why several planned pieces are smaller or missing)

This box ran at 100-130% of nominal 24-core capacity for nearly this entire
session -- Tier 1/2's census and garbage-scheduler jobs, hole-poker's beam
search and taxonomy jobs, and several other concurrent tiers (`stage1.py`,
`opp_aware_vs.py`, `sample_boards.py`) were all running simultaneously most
of the time. Concrete consequences, in the order they were hit:
1. The evolutionary search (6 workers) took ~5x longer per generation than
   its own uncontended smoke test predicted; stopped at generation 7/18.
2. `train_adversary_model.py`'s FIRST run hung for >5 minutes on a ~35K-row
   dataset that should train in seconds -- root cause was sklearn's own
   internal thread pool (permutation_importance, n_jobs=2) thrashing against
   everything else on the box, not genuine work. Fixed by capping
   OMP_NUM_THREADS/OPENBLAS_NUM_THREADS/MKL_NUM_THREADS=2 and reducing
   permutation_importance's n_repeats/sample size -- second attempt: 7
   seconds.
3. `measure_fourway.py`'s originally-planned n=80 four-way comparison was
   killed twice without a single arm completing (>5 min each attempt).
   Replaced with `quick_fiveway.py` at n=15, which completed arms (a)-(c) in
   ~2.5 minutes each; arm (d) (the learned adversary, which does per-
   candidate Python-level sklearn inference rather than a pure-numba kernel)
   took ~13 minutes under the same contention before completing (result now
   in the four-way table above). The box's load dropped substantially partway
   through this session (other tiers' jobs apparently wrapping up) -- the
   kill-classification work later in this report ran in a fraction of the
   time the earlier measurements needed, for the same reason.
4. Own multiprocessing worker counts were kept at 4-8 throughout rather than
   the authorised-up-to-20, specifically to avoid making the shared
   contention worse for the live silicon A/B and sibling tiers -- a
   deliberate trade of this tier's own throughput for the program's overall
   throughput, worth revisiting if the box frees up.

**Practical consequence for anyone continuing this**: every n reported here
is smaller than originally planned, and every CI is correspondingly wide.
The honest read is "no large effect found by any of three methods, on samples
too small to rule out a moderate one" -- re-running `measure_fourway.py` with
`FOURWAY_FULL=1` (restores n=80/60) once the box is less contended is the
highest-value next step, not a new search or a new feature set.

## What was reused vs newly built

See `README.md` for the full inventory. Headline: the entire VS match loop
(`vs_harness.play_match`) was reused unmodified; the champion's own depth-3
numba kernels were mechanically copied and extended (not rewritten) for the
evolved adversary AND for the kill-classifier's candidate-inspection kernel
(`instrumented_champion.py`), following this project's own established
discipline; the off-policy pipeline (`adversary_features.py`,
`gen_rollout_data.py`, `train_adversary_model.py`, `learned_adversary.py`)
and the kill classifier (`instrumented_champion.py`, `classify_kills.py`)
are new, built to the team lead's two mid-session design updates.

## Note on the concurrent census finding (clean stream unbreakable)

The team lead reported the pooled clean-stream census (Hetzner + local,
1,474 games) found ZERO failures -- rule-of-three puts the true clean
failure rate below 0.20% at 95% confidence. That is independent evidence for
the same shape this tier's results already show: seed variation ALONE,
without an active attacker, essentially never kills the champion. It
directly supports why this tier's adversary design deliberately does NOT
include a "target column" or seed-manipulation knob (see the module
docstrings) and instead spends its whole parameter budget on GARBAGE TIMING
(`w_press`, `w_hold`, `w_bigsq`) -- per this finding, that channel is where
whatever leverage exists actually is, and this tier's design already bet on
that before the census result confirmed it.

## Fixtures

- `fixtures/best_adversary_vector.json` -- the evolved adversary's best
  vector + provenance (generation found, train-seed death rate + CI).
- `/mnt/data/drmario_adversary_t3/checkpoints/adversary_value_model.pkl` +
  `.meta.json` -- the trained learned-adversary model + its offline metrics.
- `/mnt/data/drmario_adversary_t3/replay_buffer/*.jsonl` -- the full labelled
  rollout corpus (kept on disk per the owner's instruction), 43,085 rows,
  472 games, 4 behaviour policies.
- `search_checkpoint.json` / `search_log.jsonl` -- full evolutionary search
  record, anytime-resumable.
- `quick_fiveway_result.json` -- the completed four-way comparison result.
- `kill_classification_result.json` -- full per-decision data behind the
  outplayed-vs-risk-neutral-choice classification above, all 4 death games.

## Honesty notes (consolidated)

- This entire program runs in the offline Python simulator, which disagrees
  with real RTL on ~87% of base-search moves (verified against the primary
  source: `CANDIDATE_TIER3.md` §10 -- real-L11 boards, 4/30 = 13.3% full
  column+orientation agreement between the offline base-search and RTL, i.e.
  86.7% disagreement). Any exploit found here needs co-sim replay before
  being called a silicon failure -- these are offline-sim findings, and
  given the key finding above, there is not yet an exploit to replay.
- `native-d1` here is `fast_sim_x.FastDecider(depth=1)`, the offline POLICY
  CLASS equivalent of the CvC cart's `DRP1NATIVE`, not the literal 6502 code.
- "Garbage in flight" (an originally-requested feature) is not observable by
  any decider in `vs_harness.play_match` by construction -- approximated by
  running attack-sent/received counters the decider maintains itself, per
  `adversary_features.py`'s docstring.
- All rates above report `n` explicitly, and every n in this report is small
  (15-20 per arm) because of the resource contention documented above --
  read every percentage with that in mind, especially the 0.0% entries: at
  n=15, a true rate as high as ~18% would still show 0/15 about 6% of the
  time, so "0%" here means "not detected at this n", not "impossible."
