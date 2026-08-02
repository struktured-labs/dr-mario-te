# depth4/ — re-test of the depth-4 NO-GO (2026-07-31)

**RESULT: the standing NO-GO was WRONG. Depth-4 is mildly POSITIVE, not "strictly worse in
expectation". It remains unshippable — but on LATENCY (22.9x), not on quality, and those
have different remedies.**

## What was being re-tested

The 2026-07-24 memo concluded *"depth-4 NO-GO — d4 loses on horizon-effect QUALITY, also
unshippable"* on **n=10 games**. The project's own sample-size audit flagged it as one of two
door-closing negatives decided on n=10, in the same era whose weight-tuning work had already
written down *"10-seed scores swing ±20 pills — always holdout."*

## Headline: the memo's own statistic, sign-flipped, with the baseline reproducing exactly

The memo's summary number was "expected pills including topout cost" = mean-pills-on-clear +
topout_rate·400.

| | 07-12 memo (n=10) | this re-test (n=120, NES stream) |
|---|---|---|
| d3 | **121** | **121** |
| d4 | **160** | **101** |

**d3 reproduces to the digit** across four months, a different search implementation
(`nes_d3_golden.decide_d3_incr` → `fast_rtl_x._choose_d3_ship_eh_delta`) and a different leaf
(W_SETUP 60 → the coef-opt2 `winner`, 32). That is what makes the comparison trustworthy: the
measuring stick did not move, so it is **d4's** number that moved, 160 → 101.

⚠ **State your convention.** The memo ran `max_pills=400` and its non-clears were topouts. This
harness distinguishes a **stall** (pill budget exhausted, never topped out) from a **topout**.
Charging 400 for topouts only — like-for-like — gives 121 / 101. Charging *all* non-clears gives
124 / 105. Both are printed by `analyze.py`; quote the topout-only pair against the memo.
Components: d3 mean-on-clear 107.2 @ 3.3% topout, d4 101.4 @ 0%. The old n=10 saw 10/10 clears,
which at a 3.3% true rate has probability 0.71 — its clean sweep was expected, and the n=10
noise bit on the d4 side.

## Full results, n=120 paired seeds, L11, `winner` leaf

**NES capsule stream (the one that counts):**
- clear **115/120 → 119/120**; discordant **0 / 4** — d4 never lost a clear d3 got. McNemar
  two-sided p=0.125 (one-sided 0.0625). Direction unanimous, **underpowered** at a 96% base rate.
- paired pills on both-cleared (n=115): mean **−6.10**, CI95 **[−12.77, +0.85] — crosses zero.**
- censored pills (non-clear charged 300): **−12.22**, CI95 **[−21.40, −3.54]** — excludes zero.
- pills-per-virus, per-seed paired: open −0.046 [−0.093,−0.002], mid −0.137 [−0.218,−0.056],
  end −0.771 [−1.741,+0.160].

**Uniform stream:** paired pills **−9.46 [−15.50, −4.06]** (excludes zero), censored −7.62
[−14.37, −0.72]. But d3 clears **120/120** here — uniform is at the **ceiling** and structurally
cannot show a clear-rate gain at all. Running only uniform would have hidden the entire
clear-rate story; running only NES would have shown a pills effect that crosses zero.

**Honest bound.** *"d4 is not worse"* is solid — every point estimate on both streams favours
d4, nothing favours d3. *"d4 is better"* is **not** established by NES pills alone; it rests on
the censored composite (excludes zero on both streams) plus 4 unanimous discordants. Mildly
positive, not decisive.

## Mechanism — the memo had it backwards

All four NES discordants are **d3 topping out with 1–3 viruses left**, which d4 finishes:

| seed | d3 | d4 |
|---|---|---|
| 4 | topout, 1 virus left | clear @ 159 pills |
| 9 | topout, 2 left | clear @ 80 |
| 63 | topout, 3 left | clear @ 133 |
| 109 | topout, 1 left | clear @ 63 |

d4 has **fewer** topouts, not more. The memo blamed horizon-effect topouts from over-deep setup
plans — a claim conditional on **W_SETUP=60**, and the shipped winner leaf runs **32**. The
coefficient that caused the horizon effect is no longer in the brain.

This is the user's literal *"can't clear certain messes"* complaint, now located at **search**
level. The pair-latch work found the same failure at **execution** level. Two independent
instruments now point at the same place: **the endgame with a nearly-cleared board.**

## ★ Reconciliation with the clairvoyant beam result (same night, opposite sign)

opening-book measured a **clairvoyant beam:5** — deeper search *with perfect capsule knowledge* —
**losing decisively** to shipped d3 (full-game clear 81.7% vs 95.8%, p=0.0002, +20 pills), while
this depth-4 came out mildly positive. Both are "deeper search". The synthesis that fits both:

- **Deterministic deep BEAMS with this eval are poison.** A narrow beam commits to lines the
  eval flatters, and leaf mispricing compounds along the committed line with nothing averaging
  it away. Perfect information does not rescue it — openbook's beam *had* the true capsules and
  still lost, which is the strongest available evidence that **the eval, not the information, is
  the wall**.
- **Deeper EXPECTIMAX is mildly positive.** Chance nodes average over capsule outcomes at every
  ply, which regularises leaf error instead of compounding it.
- **But only mildly** (censored −12 at 22.9x cost), so the eval's error still dominates what
  extra depth can extract. This *refines* the eval-wall corollary rather than overturning it.

**What this experiment does and does not license.** It does **not** independently test "beams are
poison" — no beam arm was run here; that claim is openbook's. What it does contribute is a sharper
boundary: **a beam is not automatically fatal.** This d4 contains a ply-3 beam (`topk3=6`, keeping
6 of ~32 placements) and did not crater. The difference is structural — this beam sits *inside* an
averaged tree, at one ply, with chance nodes both above and below it, whereas openbook's beam *is*
the whole search. So the operative distinction is not beam-vs-no-beam but **whether chance nodes
survive between the root and the leaf.**

## ★ Phase 3: the oracle verdict — d4's edge is SEQUENTIAL, not per-move

All 1809 disagreements adjudicated deterministically: from each, both actions played forward
on the identical true capsule stream with **d3 steering after the branch** (deliberate — the
oracle exists to mine leaf terms for the shipped brain, so "was d4's move better *for a d3
player*" is the actionable question; a d4-consistent roll-forward answers one we cannot act
on, at 20x). Zero rollout variance: the only difference between branches is the one move.

**Replay gates CLEAN** — 1809/1809 rows reached, zero mismatches on board colors, virus mask,
served capsules, stream cursor, and d3's own recorded action.

| metric | result |
|---|---|
| paired pills, both cleared (n=1654) | **+0.503** CI95 [−2.949, +3.807] — spans zero |
| censored delta | **−3.96** CI95 [−12.45, +3.65] — spans zero |
| win share among decisive | 708/1347 = **52.6%** |
| regime concentration | **none**; endgame is the *most positive* (+0.890) |

### ★★ The apparent surviving signal is a CLUSTERING ARTEFACT

Among rows where exactly one branch cleared, d4 won **61 to 26** (70.1%), and a naive
two-sided binomial returns **p = 0.00022**. That treats 87 rows as 87 independent trials.
They are not: rows cluster by **seed**, and one doomed game emits many disagreement rows that
each avert **the same** topout.

```
d4-only rescues: FOUR seeds      -- 4(18)  9(16)  63(11)  109(16)   = 61
d3-only losses:  FOURTEEN seeds  -- 8(3) 33(2) 45 50 64(2) 72 73 86
                                    89 93 96(2) 104 105 108(8)      = 26
```

**Those four seeds are exactly the A/B's four discordant seeds.** No other seed produced a
rescue. So the 61 are 61 views of the *same four games the A/B already counted* — a re-derivation,
not independent evidence.

Correct analysis, with the **game** as the unit:

| | |
|---|---|
| net rescues per game | **+0.294** CI95 [−0.176, +0.866] — spans zero |
| seeds net>0 / net<0 / net==0 | **4 / 14 / 101** — more seeds favour d3 |
| Wilcoxon signed-rank | **p = 0.389** |

Same error class as the completion-order bias found earlier in this lane: a within-cluster
effect wearing the costume of an independent-sample effect. `rescue_cluster.py` prints the
invalid and valid computations side by side.

### What follows

No single-move value is detectable on **any** metric. Because the A/B's censored −12.22 is an
**independent existence proof** that d4's edge is real, the null cannot mean "no edge" — it
means the edge is not in isolated placements. **It lives in multi-move steering**, so the
mining target moves from "a leaf term capturing single-position judgment" to "what does d4 set
up across moves". Harder quarry, still real.

One genuine positive: within the four rescued games the rescue is **robust** — 18/16/11/16
separate moves each independently avert the topout. Those games differ by persistent judgment,
not one lucky placement. That is a fact about four games (consistent with the A/B's
underpowered McNemar p=0.125), not a per-move effect.

**Pre-registration scorecard** (registered before the data, scored after): mean delta −0.3 to
−1.5 pills — **WRONG** (+0.503, sign opposite); win share 52–58% — **CORRECT** (52.6%, though
inside a zero-spanning CI so the direction is unestablished); endgame strongest — **WRONG**
(endgame is the most positive); measured value is a lower bound on d4's true edge — **HOLDS**,
and it is what makes the null interpretable rather than fatal.

## The blocker is latency, and that is a different problem

Measured in-game as **CPU time** (this box runs an FPGA compile and several agents; wall clock
would measure the neighbours):

| | ms / decision |
|---|---|
| d3 | 27.2 |
| d4 (topk3=6, pills4=4) | 622.9 |
| ratio | **22.9x** |

Unshippable on a copro deadline regardless of the quality verdict. So the deliverable is an
**ORACLE**, not a runtime: mine the positions where d4 and d3 disagree *and* d4's choice proves
better downstream, to characterise what d3's eval is missing — training signal for a leaf term.
This is the dual of the pair-latch finding: there the eval knew answers the *driver* discarded;
here the question is what one more ply reveals that the *eval* never knew.

`disagree.py` produces the rate and the corpus. Phase-3 adjudication rolls forward with **d3**
deliberately (team-lead's call): *"was d4's move better for a d3 player"* is the actionable
question; a d4-consistent roll-forward answers one we cannot act on, at 20x. Adjudication is
**deterministic** — the seed fixes the 128-capsule buffer — so corpus rows carry `seed`, `k` and
`src_i` (opening-book's own cursor convention, `bookab.play`: the clairvoyant k+2 read is
`ids[src.i % 128]`) rather than a sampled rollout. Calibration warning from openbook's null:
**18.4% different moves can carry zero value**, so the corpus is only as good as its adjudication.

## The rig, and why it is a new one

The old rig (`dr-mario-mods/tmp/decide_d4_incr.py`) sits on `nes_d3_golden.decide_d3_incr` — the
weekend-era golden (`dr-mario-golden-is-weekend-era`: it ignores the R47 flags and its defaults
are not the shipped search), with `topk1=32` **sorted and pruned** at ply 1 and a **coarse 2-pill**
ply-4 subset its own docstring flags as biasing the estimate. Re-running it would have re-tested a
brain we no longer ship.

`d4_kernel._choose_d4_ship_eh_delta` is `fast_rtl_x._choose_d3_ship_eh_delta` with **exactly one
structural change**: the ply-3 MAX layer keeps its top-`topk3` placements and expands each into a
ply-4 chance layer + ply-4 MAX → leaf. Ply-4 uses the **same 4-pill stratified subset as ply 3**
(the delta buys the unbiased version the old rig could not afford). Enumeration order, tie-breaks,
the topk2 stable sort, the DISC_SHIFT blend, the eh root add-on and imm are byte identical.

**Gates — these make "exactly one structural change" a fact, not a claim:**

| gate | result |
|---|---|
| delta-vs-full d3 substitution (same action?) | **200/200** |
| d4 degeneracy: ply4=leaf + topk3=∞ == d3 | **300/300** |

Both on real mid-game boards taken off real trajectories, not synthetic fills — a uniform random
board fill over-represents positions the search never visits.

**Both arms run the same kernel.** Comparing a delta arm against a non-delta arm would confound
the kernel with the depth.

## Provenance

`snap/` is a **hash-pinned copy** of the kernel, vendored here so this experiment reproduces from
a `git archive` export alone rather than depending on a gitignored `tmp/`:

```
665a8e0b7a256c6cc348cbf3ad67764e  snap/fast_rtl_x.py
624634bc6cdc272ab8ee3eb72ddf768a  snap/fast_sim_x.py
```

It was taken because the source file was being edited concurrently by another lane; a mid-run
kernel change would have silently invalidated the pairing. **Standard practice now for any A/B
importing from `tmp/`.**

External dependency not vendored: the faithful sim (`drmario.faithful_env`), which lives in the
`dr_mario_rl` worktree — same dependency as the other experiments here.

⚠ **Corpus format note for whoever writes the next one: STORE `link`.** `disagree.py` records
`color` and `is_virus` (what `board_flat` feeds the search) but not `link`. That is sufficient to
*re-decide* a position and insufficient to *resume* one: the search ignores link, but gravity does
not — a linked capsule half falls with its partner until the partner clears. A board restored
without link looks identical to every inspector and has a different FUTURE, which is exactly what
a roll-forward measures. `adjudicate.py` sidesteps it by replaying each seed from move 0, which
costs a replay per seed and buys five verification gates per row. Store link, or accept the replay.

## ★ Method trap found (applies to every ProcessPool A/B in this repo)

Results stream via `as_completed`, which returns **fastest-finishing games first**. A fast game is
a short game, and short games are disproportionately clears — so **any mid-run read of a partial
arm is a seed subset selected in favour of whichever arm is slower.**

Measured cost of ignoring this: the completion-order-biased interim said censored **−20.5**; the
completed run says **−12.2**. A ~70% overstatement, in the direction that would have flattered the
result. **Never analyse an unfinished arm.**

## Files

| file | what |
|---|---|
| `d4_kernel.py` | the d4 search + both correctness gates (`validate`, `validate_delta_vs_full`) + `bench` |
| `d4_ab.py` | paired A/B runner, both streams, per-seed JSONL |
| `analyze.py` | paired pills + bootstrap CI, discordants + McNemar, censored pills, both memo conventions, per-regime ppv, latency |
| `disagree.py` | disagreement rate by regime + orient/column/both split + the oracle corpus |
| `cost_profile.py` | cost by virus count + branching factor + sampled dv_fallback + copro budget arithmetic |
| `adjudicate.py` | phase-3 deterministic adjudication (replay + fork + d3 roll-forward, five gates) |
| `rescue_cluster.py` | the clustering check that killed the 61-26 "signal" — invalid and valid computations side by side |
| `results/d4main_k3-6_p4-4_perseed.jsonl` | **the evidence** — 480 games, one row each |
| `results/disagree_nes_k3-6_corpus.jsonl` | **the oracle corpus** — 1809 anchored disagreements |
| `results/adjudicate_rows.jsonl` | **the adjudication** — one verdict per disagreement |
| `results/*_summary.json`, `cost_profile.json` | derived summaries (assertions; the JSONLs are the evidence) |

Reproduce:

```bash
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python   # only interpreter with numba+py65
$PY d4_kernel.py validate 300      # gates; must print GATE PASS
$PY d4_ab.py --seeds 120 --workers 4 --streams nes,uniform --topk3 6 --pills4 4 --out d4main
$PY analyze.py results/d4main_k3-6_p4-4_perseed.jsonl
$PY disagree.py --seeds 120 --workers 4 --stream nes
$PY cost_profile.py --per-bucket 60 --stream nes
$PY adjudicate.py --workers 4 --out adjudicate     # ~23 min; gates must be 0
$PY rescue_cluster.py results/adjudicate_rows.jsonl
```

Phase 2 (beam-crater vs horizon-effect attribution) was **cancelled, not skipped**: it was an
attribution for a loss, and there is no loss to attribute. The endgame-gated A/B was likewise
cancelled once the cost profile came back at 23.2x — see below.

## Endgame-gated d4: DOES NOT FIT, by ~7x

| bucket | n | mean vc | branch | d3 ms | d4 ms | ratio | dv_fb |
|---|---|---|---|---|---|---|---|
| open | 60 | 40.8 | 30.0 | 31.32 | 652.23 | 20.8x | 6.2% |
| mid | 60 | 20.2 | 30.0 | 23.54 | 531.80 | 22.6x | 7.8% |
| end | 60 | 4.2 | 30.0 | 24.53 | 568.76 | **23.2x** | 7.5% |

The endgame is **not** cheaper — marginally worse than the 22.9x all-game figure. At 24f copro d3
endgame DONE against an 80f budget that projects to **556f, 6.96x over**.

★ **Why, and this generalises past depth-4:** search cost is driven by **legal placement count**,
not virus count — and branching is **~30 in every regime**. The ceiling is 30 rather than 32
because the two horizontal orientations at column 7 have no column 8 (verified on an empty board),
and at L11 the stack is never tall enough to block anything further. **"The endgame is sparse" is
true of VIRUSES and false of PLACEMENTS:** a nearly-cleared board is *low*, so almost nothing gets
pruned. The emptiness that makes the endgame feel cheap is exactly what pins branching at the
ceiling. **Any future "gate the expensive thing to the endgame" proposal — tucks, planner, depth —
meets this fact first.**
