# PRE-REGISTRATION — ORACLE-CEILING ARM

**Sealed and committed BEFORE any endpoint game was played.**
Author: oracle-ceiling lane, 2026-08-10.
Subordinate to `../rollout/PREREG_ROLLOUT.md` and `../PREREG_STAGE2.md` §6.3/§6.4.
**Nothing here relaxes either.** The endpoint, the pressure model, the seed
discipline and the verdict rule are reused UNMODIFIED. This file fixes only what
is new: the oracle itself, its gate, its killed mutant, and — because it is the
thing stage 2 got wrong — the **sample size and the arithmetic behind it**.

MANDATORY CAVEAT, attached to every number this lane produces:
> Environment = dr. lulu fitted bursty pressure (`results/dr_lulu_20260808_fit.json`,
> md5 `dfe5938ceeaa0fc1d253ceccb2cd6d46`), base policy = shipped champion,
> `ws=20`, `wt=0`, `variant("winner")`, depth 3, level 11. Base clear rate under
> this model is ~80%, BELOW the 96.9% label-quality screen. This arm does not
> fit anything on labels, so the screen does not gate it — but the regime is the
> pressured one and results do not transfer to clean solo play.

---

## 0. THE QUESTION, AND WHY IT IS ASKED THIS WAY

15,000 games were spent on a learned evaluator **without ever establishing a
calibration point from offline AUC to the dies-ahead endpoint.** The one
measurement that exists (`../rollout/RESULT.md`) is consistent with a **slope of
zero**: the fitted term moved dies-ahead **−0.80 pp [−2.20, +0.60]**, and a
dose-matched **label-blind** term of the same size moved it **−0.53 pp**;
difference-in-differences **−0.27 pp [−1.73, +1.13]**.

This arm asks the prior question — **does *any* root re-ranker move dies-ahead
at all?** — by re-ranking with information no leaf evaluator can ever have: a
15-pill forward rollout of the real policy in the real environment. It is
therefore an **UPPER BOUND on the endpoint movement available to the entire
class of root re-rankers**, expressed in endpoint units.

**Decisive in both directions. That is the point.**

* **Oracle NO_GO** ⇒ root re-ranking is **structurally dead** for dies-ahead.
  No leaf evaluator should be funded for this endpoint again. The lane closes on
  evidence rather than on fatigue.
* **Oracle GO at −2 to −3 pp** ⇒ the AUC gap becomes **priceable for the first
  time**, and stage 2's 0.7220 stops being a proxy nobody can convert.

**This arm is a MEASUREMENT, not a ship candidate.** The oracle is not
implementable in silicon — it costs ~10–17× a game per game. Nothing here
proposes shipping it.

---

## 1. THE ARMS (exactly two for the verdict; declared now)

Both arms run inside `oracle_arm.py`, whose non-decision lines are
`pressure_rig.play`'s. Identical seed ⇒ identical capsule stream, identical
virus board, identical garbage schedule (injection is a pure function of
`(seed, pills_placed)`).

**BASE** — the shipped champion, unchanged. Implemented as
`OracleArm(label_mode="const")`: the gate and the top-k sort still run, every
fork label is identical, so the selection provably cannot move and the champion's
own enumeration (`o4 = 0..3` → `var = _VAR_OF_O4[o4] = [2,3,0,1]`, `cc = 0..7`,
strict `>`) decides. Gate **G1a** asserts this reproduces `pressure_rig.play()`
exactly.

**TRT (the oracle)** — identical everywhere except at gated plies.

* **GATE** — evaluated on the **CURRENT, pre-placement** board:

      d_spawn_h = max(H[3], H[4])            (H = column heights, 0..16)
      viruses   = board.virus_count()
      ORACLE PLY  ⇔  d_spawn_h >= 12  OR  viruses <= 8

  Pre-placement is the honest reading: a real gate must decide *whether* to
  spend the compute from the state it is in. Fixed now; not swept.

* **FORK** — the **TOP-4** candidates by champion value (ties broken by the
  champion's own enumeration order) are each played **15 pills forward**: the
  candidate action, then the **unmodified champion policy**, with the real dr.
  lulu bursty injection running exactly as in the live game.

* **LABEL** — each fork yields `(survived, progress)`:
  `survived = 0` iff the fork topped out or was spawn-blocked inside the horizon;
  `progress = viruses_before_ply − viruses_at_end_of_fork ≥ 0`.
  **Selection = "survivor-with-virus-progress"**: argmax of that pair scanned in
  the champion's rank order with strict `>`, so **a tie keeps the champion's own
  choice** and an uninformative oracle degrades to a NO-OP rather than to noise.

Constants `GATE_DSPAWN_H = 12`, `GATE_VIRUSES = 8`, `TOPK = 4`, `HORIZON = 15`
are fixed by this document. **No sweep over any of them is licensed**, and any
run at other values is reported as a separate, clearly-labelled sensitivity
probe with no verdict authority.

---

## 2. GATES THAT MUST PASS, EACH WITH THE MUTANT THAT MUST BREAK IT

Run by `gate_identity.py`; a failure of any of these **VOIDS** the arm.
A check that has not been shown to fail on a deliberately wrong input is not a
check.

| id | gate | its killed mutant |
|---|---|---|
| **G1a** | `label_mode="const"` reproduces `pressure_rig.play()` on won/topout/stall/pills/dies_ahead, and its per-ply action sequence is deterministic, on ≥12 seeds | — |
| **G1b** | — | **G1a with the enumeration order REVERSED** (tie resolution only). MUST break G1a on ≥11 of 12 seeds |
| **G1c** | two `deepcopy` clones of one LIVE mid-game state draw **identical** capsules, and the parent's cursor does **not** advance | the same clone made through `nes_pills.attach()` — the lambda version that `pressure_rig`'s hard-coded sys.path puts first — **MUST** share the cursor and fail |
| **G1d** | liveness: the true oracle differs from base on ≥11 of 12 seeds and flips >0 plies | — |
| **G1e** | gate coverage: the predicate fires on a strict minority-or-majority but **never 0% and never 100%** of plies | a gate that never fires makes the arm silently inert — the failure mode `dr-mario-tuck-mailbox-vacuous-gate` names |
| **G1f** | the shuffled-label arm produces a **different** action sequence from the true oracle on ≥11 of 12 seeds | otherwise the killed mutant is vacuous |

**G1c is not ceremony.** `pressure_rig.py` hard-codes
`/home/struktured/projects/dr-mario-qa-wt/experiments` onto `sys.path` *ahead of*
`dr_mario_rl/tmp/pillrng`, so `import nes_pills` resolves to a copy whose
`attach()` still installs `env._rand_pill = lambda: ...`. `copy.deepcopy` treats
a function as atomic, so every fork would have drawn from **one shared advancing
capsule cursor** — silently, deterministically, with plausible boards. This arm
forks, so it installs its own `PillDraw` object and **proves** the independence.
Gate seeds are **40000..40011**, reserved for gates and never scored.

---

## 3. THE KILLED MUTANT (mandatory; the arm does not run without it)

**ARM `--label shuffle`.** The **identical four forks** are computed — identical
gate, identical candidate set, identical cost — and their `(survived, progress)`
labels are then **permuted among the candidates** with `random.Random(seed *
100003 + ply)`. The oracle is then re-ranking on a survival label that carries no
information about which candidate produced it.

**PRE-REGISTERED REQUIREMENT: the shuffled arm must NOT read GO.**
If a shuffled survival label clears the same gate the true oracle clears, the
gate is measuring churn and not direction, and **both readings are void**.

**Scale, and its honest bias.** A random permutation moves the argmax more often
than the true label does, so the mutant is expected to be **over-dosed** relative
to the oracle. That biases the difference-in-differences **in favour of the
oracle**, i.e. `DiD = (oracle − mutant)` is an **UPPER bound** on the oracle's
advantage over a same-shaped random perturbation. Both realised flip rates are
reported next to each other so the reader can see the dose gap rather than take
the DiD at face value. This is the identical accounting `../rollout/PREREG_ROLLOUT.md`
deviation-log entry 3 was forced into after the fact; here it is declared first.

A third control, `--label const`, is the exact-identity arm (G1a).

---

## 4. ENDPOINTS AND THE VERDICT RULE

Copied from `PREREG_STAGE2` §6.3/§6.4 and applied by the SAME code
(`analyse_oracle.py` imports `summarise()` and `verdict()` verbatim from
`../rollout/analyse.py`, whose verdict function is itself mutant-tested by
`../rollout/test_verdict.py`). Reusing the instrument is deliberate: the oracle
and the stage-2 arm must be scored identically or their effect sizes are not
comparable, and comparability is the entire purpose of a calibration arm.

**PRIMARY — dies-ahead count** (`res == "topout"` and `viruses_left ≤ 12`).
**GO** requires `DA_trt − DA_base < 0` with a 95% seed-level **paired bootstrap**
CI (B = 2,000, rng 20260810) **excluding 0**, **AND** McNemar exact two-sided
**p < 0.05** on the discordant dies-ahead pairs.

**CO-PRIMARY, GATING — clear-rate non-inferiority.**
**GO** requires the **upper** bound of the 95% CI on `(clear_base − clear_trt)`
to be **< +1.0 pp**. A larger clear-rate loss is **NO_GO regardless of
dies-ahead**.

**NO_GO conditions, evaluated mechanically:**

* **N1** clear-rate loss upper 95% bound ≥ +1.0 pp
* **N2** dies-ahead 95% CI includes 0, **or** McNemar p ≥ 0.05
* **N3** dies-ahead falls but **net bad-ends (topout + stall) do not**
* **N3′ — NEW, and the reason it is new.** Stalls are scored **at parity with
  topouts**. In stage 2, **19 of the 28 topouts avoided reappeared as 300-pill
  stalls** and the stall condition never fired because net bad-ends still fell.
  The topout→stall conversion is therefore **computed and reported as a named
  quantity** (`stall_parity.topouts_converted_to_stalls`), and a dies-ahead win
  accompanied by a bad-ends CI that includes 0 is reported as **N3**.
* **N4** any gate in §2 fails ⇒ **VOID**, not NO_GO.
* **INCONCLUSIVE** if fewer than 1,500 pairs complete.

**STOP/NO_GO is reported with the same prominence as a GO.**

**BREAKAGE ACCOUNTING** is `PREREG_ROLLOUT` §5 unchanged: `b10` (base cleared,
trt did not) and `b01` reported as raw counts with exact-binomial p, plus the net
population effect in **both** units at the census ratio **6.4 clears : 1
dies-ahead**. **A dies-ahead win with meaningful breakage is a LOSS and is
reported as one.**

---

## 5. SAMPLE SIZE — WITH THE ARITHMETIC, BECAUSE STAGE 2 DID NOT DO THIS

For a paired binary endpoint the standard error of the difference is set by the
**discordant** pairs, not by N alone:

    SE(p_trt − p_base) ≈ sqrt(D) / N = sqrt(d / N),   d = D / N

**The formula is validated against stage 2's own published bootstrap CIs before
it is used to size anything:**

| endpoint | D at N=3,000 | d | 1.96·√(d/N) | published CI half-width |
|---|---|---|---|---|
| clear | 611 | 0.2037 | **1.615 pp** | ±1.58 pp |
| dies-ahead | 452 (238+214) | 0.1507 | **1.389 pp** | ±1.40 pp |

Agreement to ~0.03 pp. Inverting it:

    N ≥ d · (1.96 / margin)²

**(a) The clear-rate co-primary is the binding constraint.**
For the +1.0 pp margin to be *reachable at all* — i.e. half-width < 1.0 pp, which
is required before any true effect however good can pass —

    N ≥ 0.2037 · (1.96/0.010)² = 0.2037 · 38,416 = **7,826 paired seeds**

**⚠ N = 4,500 IS NOT ENOUGH.** At stage-2 churn it gives half-width
`1.96·√(0.2037/4500) = 1.319 pp > 1.0 pp`: the gate would again be **unpassable
by construction**, which is precisely the defect
`CHAMPION_ITER_PLAN.md` §"POWER FLOOR" identifies. 4,500 is a floor, not a
sufficient size, and this document says so before the run rather than after it.

**(b) dies-ahead.** To exclude 0 at a true effect of −2.0 pp (the plan's
"interesting" region): `N ≥ d_da · (1.96/0.020)² = d_da · 9,604`. At stage-2
churn (`d_da = 0.1507`) that is **1,448**; if the oracle churns 2× as much
(`d_da ≈ 0.30`), **2,881**. At −1.0 pp it becomes `d_da · 38,416` = **5,791** at
`d_da = 0.1507` and **11,525** at `d_da = 0.30`.

**REGISTERED SIZE — TIER A (primary): N = 9,000 paired seeds, `30000..38999`.**
At stage-2 churn this gives clear half-width **0.932 pp** (decidable) and
dies-ahead half-width **0.801 pp** (detects −1.0 pp). 2 arms × 2 labels
(oracle + killed mutant) = **36,000 games**.

**PRE-REGISTERED FALLBACK — TIER B: N = 5,500 paired seeds, `30000..35499`.**
Registered now, before any data, with its consequence stated: at stage-2 churn
Tier B gives clear half-width **1.192 pp**, so **the clear-rate co-primary is NOT
DECIDABLE** and is reported as `NOT DECIDABLE`, never as a pass. Tier B still
resolves dies-ahead at −1.5 pp (`d_da·(1.96/0.015)² = 2,574` at `d_da = 0.1507`,
**5,122** at `d_da = 0.30`). Tier B is a **dies-ahead-only ceiling verdict** and
is labelled as one everywhere it appears.

**ADEQUACY IS COMPUTED AND PRINTED BEFORE THE VERDICT, ALWAYS**
(`analyse_oracle.power_adequacy`): achieved half-width, the +1.0 pp margin, the
decidable flag, and the N that *would* have been needed at the realised
discordance. **An underpowered gate is reported as underpowered, never as a
pass and never as a NO_GO on the clear-rate axis.**

---

## 6. SEEDS, SEGMENTATION, EARLY STOP

* **PRIMARY REGIME: dr. lulu bursty only.** No secondary regime carries verdict
  authority; none is registered.
* **SEEDS `30000..38999`** (Tier A) — **disjoint from every corpus seed
  (2..12001), from the stage-2 rollout block (20000..29999), and from the gate
  seeds (40000..40011).** `run_oracle.py` asserts `seed_start >= 30000`.
* **MATCHED-INDEX CONTROL**: one work item = one seed = BOTH arms, written
  atomically to one line. A completed item is a complete pair, so a prefix of the
  block is a balanced, uniform sample. Seeds are consumed in ascending order.
* **SEGMENTED**: the block is cut into segments (default 250 pairs); each banks
  its own `seg_XXXXXX.jsonl` and `seg_XXXXXX.summary.json` on completion. A kill
  loses at most one segment's in-flight pairs. Segment size cannot move the
  estimate — it does not change which seed lands in which pair.
* **EARLY STOP**: if the run does not reach the registered N, the analysis uses
  **all completed pairs** and reports achieved N against registered N. **Below
  1,500 pairs the primary reads INCONCLUSIVE**, not GO and not NO_GO.
* **THE PILOT IS A PREFIX, AND IT DECIDES NOTHING.** The pilot runs
  `30000..30249` — the first segment of the registered block — so its games are
  reused by the full run rather than thrown away. **Its numbers are reported as a
  pilot with NO verdict authority, and no stopping, sizing-down, or design
  decision may be taken on them.** Reading a prefix and then continuing is only
  legitimate if nothing is decided on the peek; that is registered here.

---

## 7. PER-PLY FLIP PROVENANCE (mandatory, `CHAMPION_ITER_PLAN.md` P0)

15,000 games produced a NO_GO with **zero mechanism** because `flips` was logged
as a bare integer. Every flipped ply in this arm records: **ply index ·
`t_to_end` · viruses remaining · max height · `d_spawn_h` · the champion's rank
of the chosen action · base action · treatment action · whether the winning label
tied the champion's · all four fork labels.** On by default; `--no-provenance`
exists only for cost probes.

---

## 8. WHAT THIS ARM CANNOT ANSWER (stated before it runs)

* It cannot price a **leaf-level** evaluator. Like stage 2, it re-ranks at the
  **root**. A NO_GO bounds the root-re-ranker class, not every possible use of a
  better evaluator.
* It cannot represent **execution** faults. The fast sim is not the cart; the
  wrong-column rate and the tuck executor gaps live in Mesen and in silicon.
* Its ceiling is **oracle-with-this-gate-and-this-horizon**. A 15-pill horizon
  under bursty pressure is not omniscience; a deeper oracle could in principle do
  better. The number is therefore a **lower bound on the true ceiling** and an
  **upper bound on any implementable root re-ranker**, and it is reported as
  both.
* **The model must be able to represent the fault.** If dies-ahead is dominated
  by states that are already lost when the ply is reached, no re-ranker at any
  quality moves it — and this arm is exactly the instrument that would show that,
  via a NO_GO with a high `frac_flips_in_last_10_plies`.

---

## 9. DEVIATION LOG

*(empty at seal; every subsequent entry is dated and states whether it was
written before or after the corresponding number was seen)*

---

### A1 — 2026-08-10. THE FORK IS CLAIRVOYANT ABOUT THE GARBAGE REALIZATION.

**Status when written: AFTER a 38-pair partial pilot was seen, BEFORE any
completed arm, BEFORE the identity gates landed, and BEFORE any verdict.** The
partial pilot showed an implausibly clean effect (0 topouts, 0 stalls, 0
dies-ahead, −57.8 pills at n=38); this amendment is the result of asking where
an inflated ceiling would come from, and finding a real answer in the code.

**THE FACT, established from the source and demonstrated empirically.**

`bursty_model.BurstyPressureModel.sample()` is:

    def sample(self, seed, pills_placed):
        rng = random.Random(seed * 1000 + pills_placed)
        n_cells = rng.choice(self.volley_sizes)
        n_cols  = max(1, min(NCOLS, round(n_cells / 2)))
        cols    = rng.sample(range(NCOLS), n_cols)

and `inject_bursty_garbage()` draws its fire coin from `random.Random(seed *
1000 + pills_placed)` as well. **The volley's SIZE and TARGET COLUMNS are a pure
function of `(seed, pills_placed)` — they do not depend on the board at all.**
Measured, seed 30000:

    pills_placed=33 -> (3, [0, 6])   called 3x, all identical
    pills_placed=37 -> (2, [1])      called 3x, all identical

**CONSEQUENCE.** A fork that advances to `pills_placed = p` reads *the same
volley, in the same columns, that the live game will deliver at p*. Over a
15-pill horizon the oracle therefore knows, in advance and exactly: whether a
volley fires (given its own clear size), how big it is, and **which columns it
lands in**. It can pre-clear the columns that are about to be attacked.

**WHY THIS MATTERS AND WHY IT IS NOT A BUG.** The rig's `(seed, pills_placed)`
keying is *correct and necessary* — it is what makes the paired A/B a
common-random-numbers design, and it is why base and treatment see the same
pressure. Nothing about the endpoint measurement is wrong. But it means the arm
as sealed measures **an oracle that is clairvoyant about the opponent**, not
"the best any root re-ranker could do":

* Seeing the true future **capsules** is fine and stays. It is the ceiling's
  definition, and a real re-ranker approximates it with expectimax over a known
  generator — the capsule buffer is generated up front and is in principle
  knowable.
* Seeing the true future **attack realization** is **not** recoverable by any
  shippable policy. dr. lulu's volleys are not a function the cart can evaluate.
  **A GO driven by that channel would be unactionable.**

The flip provenance is consistent with this being a live channel rather than a
theoretical worry: only **3.2%** of flips fall in the last 10 plies, i.e. the
oracle is acting ~34 plies from the end, which is where column-level
foreknowledge of an incoming volley would pay.

**THE AMENDMENT.**

1. **The arm as sealed is RENAMED `ORACLE-CLAIR`** and is **DEMOTED from the
   headline.** It is retained and reported, because it is a meaningful quantity —
   an **upper bound on the upper bound** — but it no longer answers the
   programme's question on its own.

2. **A new sub-arm `ORACLE-DIST` is REGISTERED HERE AS THE HEADLINE CEILING.**
   Identical in every respect — same gate, same TOPK=4, same HORIZON=15, same
   selection rule, same seeds, same endpoint, same verdict rule — except that
   **inside a fork the garbage is drawn from the pressure DISTRIBUTION rather
   than from the realization.** Implementation, fixed now: injection inside a
   fork is called with a synthetic key

       seed_eff = seed + 7919 * (ply + 1)

   passed in place of `seed`, so the draw runs through **the identical rig code
   path** (`inject_bursty_garbage` / `_inject_garbage`, no physics is
   re-implemented) but on a stream decorrelated from the true one. `seed_eff`
   depends on the ply but **NOT on the candidate**, so all four candidates at a
   ply are compared against the SAME sampled future — common random numbers
   across candidates, which is what keeps the comparison from being pure noise.

3. **Single sample, and the direction of its bias is stated now.** `ORACLE-DIST`
   evaluates **one** sampled future per ply (K=1), not an expectation. That is
   noisier than a true expectimax oracle and therefore **understates** the
   distributional ceiling. Understating is the conservative direction for the
   headline, so K=1 is registered as primary; `--fork-samples K` exists for a
   sensitivity probe with no verdict authority.

4. **READ-OUT RULE, fixed before the numbers exist.** Report `ORACLE-DIST` and
   `ORACLE-CLAIR` side by side on the same seeds. **The gap between them is the
   part of the ceiling that is pure opponent-clairvoyance and is not available
   to any shippable policy.** The programme's decision — whether to keep funding
   root re-rankers for dies-ahead — is taken on **`ORACLE-DIST` only**.
   * `ORACLE-DIST` NO_GO ⇒ root re-ranking is structurally dead for this
     endpoint, *even given a perfect within-horizon rollout*, and the lane
     closes. `ORACLE-CLAIR` being GO in that case does not re-open it; it would
     only show that the remaining headroom lives in opponent modelling, which is
     a different lane.
   * `ORACLE-DIST` GO ⇒ the AUC-to-endpoint conversion is real and priceable.

5. **The killed mutant applies to BOTH sub-arms.** A shuffled survival label must
   fail `ORACLE-DIST` exactly as it must fail `ORACLE-CLAIR`.

6. **Not yet implemented at the time of writing.** `ORACLE-DIST` is registered
   but the code change is deferred until the in-flight pilots complete, because
   editing `oracle_arm.py` mid-run would let the chained mutant arm spawn workers
   that re-import different code from the arm it is paired against. **Any pilot
   number reported before that change lands is `ORACLE-CLAIR`, and is labelled as
   such.**

---

### A2 — 2026-08-10. BUDGET SPLIT ACROSS THE THREE LABELS.

**Status when written: BEFORE any label runs at Tier A N; BEFORE the gates
landed; BEFORE any verdict.** Approved by the programme lead on the reasoning
recorded below.

Amendment A1 turned a two-label run into a three-label one (`dist`, `clair`,
`shuffle`). At the registered Tier A N = 9,000 paired seeds that is ~507
core-hours instead of ~338. This entry fixes the split **now**, before any of it
is spent.

**REGISTERED SPLIT**

| label | N (paired seeds) | seeds | authority |
|---|---|---|---|
| `ORACLE-DIST` | **9,000** | 30000..38999 | **PRIMARY — the verdict is taken here** |
| `shuffle` (killed mutant, DIST forks) | **9,000** | 30000..38999 | gate: must NOT read GO |
| `ORACLE-CLAIR` | **2,000** | 30000..31999 | sizes the clairvoyance gap only |

**RATIONALE, recorded because it is the kind of choice that gets rewritten
later.** The CLAIR−DIST gap needs **a magnitude and a sign**, not 1 pp
resolution. Spending the ~169 extra core-hours to resolve to 1 pp a channel we
have *already ruled unactionable* is paying for precision we cannot spend. At
N = 2,000 the dies-ahead half-width is `1.96·√(d/2000)` ≈ **1.70 pp** at
stage-2 churn — ample to establish whether the gap is ~0, ~5 pp, or ~25 pp,
which is the only question asked of it.

**TWO CONSTRAINTS THAT SURVIVE INTO THE WRITE-UP, FIXED HERE:**

1. **THE PROGRAMME DECIDES ON `ORACLE-DIST` ALONE.** If `ORACLE-DIST` is NO_GO,
   **the lane closes even if `ORACLE-CLAIR` is GO.** A large CLAIR number **must
   not** be used to soften a DIST null anywhere in the report. A CLAIR GO beside
   a DIST NO_GO means only that the residual headroom is in *opponent
   modelling* — a different lane, which must be funded on its own evidence and
   its own prereg, not on this arm's.

2. **K=1's BIAS DIRECTION IS QUOTED IN THE HEADLINE, NOT A FOOTNOTE.** One
   sampled future per ply understates the distributional ceiling. Therefore:
   * beside a **NO_GO** it is the **CONSERVATIVE** direction — the true ceiling
     is at least this bad, so the NO_GO is if anything understated, and the
     conclusion is safe;
   * beside a **GO** it is the **DANGEROUS** direction — a K=1 GO could be a
     lucky-sample artifact, and a GO therefore requires the `--fork-samples`
     sensitivity probe before it is acted on.
   Every quotation of a K=1 number states which of these two applies.

---

### A3 — 2026-08-10. G1g: FORK LEAKAGE WAS NOT COVERED BY THE SEALED GATE-SET.

**Status when written: BEFORE the 12-seed gate completed, BEFORE any verdict.**
Found while ranking the candidate artifacts behind the 38-pair partial.

**THE HOLE.** The sealed prereg's OFF-identity gate G1a runs
`label_mode="const"`, which short-circuits **before `_fork_label` is ever
called**:

    if self.label_mode == "const":
        labels.append((1, 0))          # no fork is run
    else:
        labels.append(_fork_label(...))

So G1a proves *the selection rule is a no-op when labels tie* and proves
**nothing** about whether running the forks perturbs the live game. G1c proves
the capsule cursors are independent — necessary, but it does not cover the
board or `pills_placed`. **A fork that mutated the parent would have granted the
oracle free practice moves, inflated every headline number, and passed the
entire sealed gate-set.**

**THE ADDED GATE — G1g, `gate_forkleak.py`.** `ForkedConstArm` runs the **real**
forks (same gate, same top-4, same 15-pill rollouts, same cost) and then
**discards the labels** and plays the champion anyway. If forks are side-effect
free this must reproduce the base arm exactly — result, pill count, dies-ahead,
**and the per-ply action sequence**.

**ITS OWN KILLED MUTANT.** `LeakyConstArm` forks on the **live** env instead of a
clone (`copy.deepcopy(env)` → `env`, one line). That is precisely the defect
being screened for and it **MUST** break the gate.

**PROMOTED TO THE MANDATORY SET.** G1g joins §2 with the same standing as
G1a–G1f: **a G1g failure VOIDS the arm.** No claim that any pilot or full-run
number is artifact-free may be made until G1g reads PASS **with its mutant
breaking**, and both directions are reported.

**GENERALISABLE, and the reason it is worth writing down:** the sealed gate-set
tested the *decision rule* and never tested the *machinery that produces the
inputs to the decision rule*. Any future arm that does work in a cloned state
needs a gate that runs that work and then throws its output away.

---

### A4 — 2026-08-10. TEMPO IS REPORTED TWO WAYS, AND IT IS NOT ONLY A CONFOUND.

**Status when written: BEFORE any completed arm.**

The oracle finishes games markedly faster (−57.8 pills at n=38). That shortens
exposure: fewer injection events, fewer chances to die. Part of any dies-ahead
reduction is therefore **reduced exposure** rather than better decisions, and the
raw endpoint alone cannot separate them.

**ADDED, REQUIRED IN EVERY REPORT:** `dies_ahead per 100 pills` (hazard-rate
view) alongside the raw per-game endpoint, for base and each treatment arm, with
paired CIs.

**BUT THE TEMPO GAIN IS NOT NETTED OUT, AND THIS IS DELIBERATE.** The north star
is **beating a human**, and speed is how the champion loses. Finishing 58 pills
sooner is a win condition in this programme, not merely a nuisance variable.
Reporting the hazard rate *instead of* the raw endpoint would silently discard a
real gain; reporting only the raw endpoint would overstate the decision quality.
**Both are reported, and the write-up states explicitly which of the two the
ceiling is made of** — i.e. how much of the dies-ahead movement survives the
per-100-pills normalisation.

---

### A5 — 2026-08-10. IDEAL MEANS IDEAL; NULL, VERDICT, AND DURABILITY REPAIRS.

**Status when written: AFTER the 125-pair `ORACLE-CLAIR` pilot was visible;
BEFORE any Tier-A label completed; BEFORE any dose-matched shuffled arm; BEFORE
any `ORACLE-DIST` endpoint game.** This is an interpretive correction from the
programme lead plus executable repairs found by reconciling the plan, prereg,
handoff, and source. The timing is explicit: the already-visible CLAIR pilot is
not presented as newly blinded evidence.

**OBJECTIVE CLARIFICATION.** The programme wants the strongest ideal headroom
measurement, even when it is deliberately unfair. Therefore `ORACLE-CLAIR` is
restored as the primary **IDEAL-CEILING** arm. Its knowledge of realized future
capsules and garbage is a feature of that question, not a defect. A CLAIR GO
measures available decision headroom; it does not claim the policy is
shippable. `ORACLE-DIST` remains implemented and valuable as a decomposition of
how much headroom survives without realized-garbage knowledge, but it does not
replace the ideal measurement.

The strongest safe NO_GO claim remains exactly what §8 says: top-4 candidates,
the registered gate, and a 15-pill horizon. That is a strong probe, not a proof
over candidates outside top-4 or benefits beyond 15 pills. Broader lane closure
requires K/action/horizon sensitivity in the NO_GO direction. This distinction
is about whether the probe reaches the ideal, not about making the ideal fair.

**PRIMARY RUN, unchanged seed block and endpoint:** `ORACLE-CLAIR` true label
N=9,000 on seeds 30000..38999 plus its CLAIR shuffled-label null on the same
9,000 seeds. The original pilot is the registered prefix and stays visibly
labelled as already seen. `ORACLE-DIST` receives no endpoint authority or N in
this amendment; a future DIST run carries its own dose-matched null and explicit
authority declaration.

**DOSE-MATCHED, LABEL-BLIND NULL.** The raw shuffled arm is over-dosed and can
no longer serve as the required null by disclosure alone. Before endpoint
execution:

1. Run true CLAIR and unthinned shuffled CLAIR on reserved seeds 42000..42059.
2. `calibrate_null.py` reads only seed, `trt.flips`, `trt.raw_flips`, and
   `trt.plies_scored`—never any terminal endpoint—and freezes
   `q = true_flips / raw_shuffle_flips` as an integer fraction over 1,000,000.
3. The endpoint shuffled arm runs identical forks, permutes their labels, then
   accepts a would-be flip iff a stable SplitMix64 hash of `(seed, ply)` falls
   below q. Candidate labels and endpoint outcomes are absent from that test.
4. Amendment A6 records q and calibration counts before the first new endpoint
   mutant game. At full N, accepted shuffled/true flip-rate ratio must lie in
   [0.90, 1.10]. Outside that range the combined comparison is **VOID**.

**DIST RANDOMNESS REPAIR.** A1's `seed + 7919*(ply+1)` collides inside the
registered block: `(seed=30000, ply=1)` and `(37919, 0)` both produce 45838.
The replacement is injective tuple packing:

    seed_eff = (seed << 32) | ((ply + 1) << 16) | sample

It remains candidate-independent (common random numbers). G1h exhaustively
round-trips all 2,700,000 registered `(seed, ply)` keys and demonstrates the old
formula's named collision.

**EXECUTABLE VERDICT REPAIRS.** `analyse_oracle.py` now owns the oracle wrapper
around the unchanged shared paired summaries. It enforces, rather than merely
prints: (a) undecidable clear co-primary forbids GO; (b) N3 fires when the
bad-end CI includes zero; (c) shuffled GO voids true GO; and (d) a dose mismatch
voids the comparison. `test_oracle_verdict.py` proves positive GO, every veto,
both combined-mutant directions, and the named paired topout→stall count.

**PROVENANCE AND RUN DURABILITY.** Shared fields use `t_to_end = n_plies - 1 -
ply`, `tie` for champion-value tie, `tie_score` for oracle-score tie, and
`val_gap` for champion points surrendered. The runner hashes the actually
resolved decision-path modules plus the Lulu fit and refuses to append into an
output directory when frozen settings or code hashes differ. G1g, G1h, G1i,
G1j (real-game provenance plus three schema mutants), and the verdict mutation
test are mandatory pre-run gates alongside G1a–G1f.

---

### A6 — 2026-08-10. SHUFFLED-NULL DOSE FROZEN.

**Status when written: AFTER the reserved 42000..42059 calibration completed;
BEFORE the first dose-matched shuffled endpoint game on 30000..38999.** The
runner's ordinary segment summaries made the reserved seeds' terminal outcomes
visible, but those seeds have no endpoint authority and the calibration code
read only the four fields declared in A5.

Runtime manifest for both calibration arms:
`f15581243f7d298f21eb0e440523dbacbe0e6523225623f2a2b371fd46279037`.

| reserved arm | flips | plies | raw flip rate |
|---|---:|---:|---:|
| true `ORACLE-CLAIR` | 194 | 6,547 | 2.9632% |
| unthinned shuffled CLAIR | 1,719 | 10,479 | 16.4042% |

The fixed endpoint-null acceptance fraction is therefore:

    q = 194 / 1719 = 0.1128563118...
    --null-keep-num 112856 --null-keep-den 1000000

`NULL_DOSE.json` is the machine-readable frozen record. No recalibration on
endpoint seeds is licensed. The full-N accepted flip-rate ratio gate remains
[0.90, 1.10] as registered in A5; falling outside it makes the comparison VOID
rather than triggering an after-the-fact rescale.

---

### A7 — 2026-08-10. A6 FAILED ITS RESERVED-SEED DOSE VALIDATION.

**Status when written: AFTER applying A6's q once on reserved seeds
42000..42059; BEFORE any dose-matched shuffled endpoint game.** A6's fraction
was derived from raw flip counts, but thinning changes the trajectory and hence
the number of later gate/flip opportunities. The required validation exposed
that defect:

| reserved arm | accepted flips | plies | accepted flip rate |
|---|---:|---:|---:|
| true `ORACLE-CLAIR` | 194 | 6,547 | 2.9632% |
| shuffled at q=0.112856 | 141 | 9,345 | 1.5088% |

Accepted dose ratio = **0.5092**, outside [0.90, 1.10]. Therefore A6's q is
**REJECTED before endpoint use** and `run_full.sh` now refuses a dose file that
does not carry `"validated": true`.

The replacement calibration rule is fixed now and may read only accepted flip
rate on the same reserved seeds:

    q_next = round(1e6 * q_current * true_rate / observed_null_rate) / 1e6

Run the next q on all 60 reserved seeds. Freeze the **first** q whose accepted
flip-rate ratio lies in [0.90, 1.10]. If four proportional updates fail, the
null design is blocked and no endpoint run is licensed. Terminal outcomes are
neither an input to the update nor a stopping condition. No adjustment on
30000..38999 is licensed; their full-N ratio remains an independent validity
gate.

---

### A8 — 2026-08-10. FIRST PASSING NULL FRACTION FROZEN.

**Status when written: AFTER A7's reserved-seed updates; BEFORE any
dose-matched shuffled endpoint game.** The proportional sequence was:

| q | accepted flips | plies | null/true flip-rate ratio | result |
|---:|---:|---:|---:|---|
| 0.112856 | 141 | 9,345 | 0.5092 | reject — under-dose |
| 0.221638 | 381 | 9,831 | 1.3079 | reject — over-dose |
| **0.169464** | **266** | **9,683** | **0.9271** | **PASS** |

Per A7, the first passing fraction is frozen:

    --null-keep-num 169464 --null-keep-den 1000000

`NULL_DOSE.json` now carries `"validated": true`; `run_full.sh` refuses any
file without it. No later reserved-seed result and no endpoint result may
change this fraction. The independent full-N [0.90, 1.10] validity gate still
applies.

---

### A9 — 2026-08-10. INTERRUPTED SEGMENTS WERE NOT BALANCED PREFIXES.

**Status when written: BEFORE any dose-matched shuffled endpoint game and
before any new Tier-A launch.** `run_oracle.py` submitted each ascending segment
but banked rows with `as_completed()`. A kill mid-segment therefore retained
the shortest-finishing games, not an ascending seed prefix, contradicting §6
and potentially biasing any early-stop analysis by game length. Resuming also
overwrote the segment summary with only newly completed rows, although the final
analyser correctly loaded the full JSONL.

The runner now uses `Executor.map`: workers still compute concurrently, but
rows are yielded and flushed in registered seed order. A partial segment is an
actual prefix. Segment summaries are rebuilt from the entire de-duplicated,
seed-sorted JSONL after resume. The semantic/code manifest remains fail-closed.

This edit changes only scheduling and banking, not a game, label, hash-thinning
decision, or endpoint. It necessarily changes the runner's manifest hash; A8's
q remains applicable because `oracle_arm.py` and every decision-path dependency
are unchanged.

---

### A10 — 2026-08-10. HISTORICAL PILOT ROWS ARE NOT REUSED ACROSS MANIFESTS.

**Status when written: BEFORE the current Tier-A launch.** §6 registered the
pilot prefix for reuse, but the historical rows were produced before shared
provenance, dose matching, ordered banking, and the fail-closed runtime
manifest. They cannot be proven homogeneous with a current output directory.

Seeds 30000 onward therefore replay under the current sealed manifest. The old
125-pair pilot remains visibly disclosed as already seen and has no verdict
authority; its rows are not copied or mixed. This is a compute-cost deviation,
not a seed, endpoint, arm, or verdict-rule change.
