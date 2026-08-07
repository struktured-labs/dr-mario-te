# Task #15 — Opponent-aware VS evaluation: A/B report

**Thread:** opponent-aware · **Verdict: DEAD** · 2026-08-06

## Hypothesis (falsifiable)

The champion's eval is entirely **self-regarding**: it never reads the
opponent's board when scoring a move. Adding **one** opponent-aware term to
the root value — with a single weight `k` — should let a candidate beat the
blind champion in VS. **If no `k` beats `k=0`, the hypothesis is DEAD.**

## Champion definition used (and a discrepancy worth flagging)

Per this thread's brief and `experiments/adversary/adversary_harness.py`'s own
docstring (identical wording): the champion is `fast_rtl_x.variant("winner")`
leaf + `eval47/terms47.g_stranded` applied **root-only** at `ws=20`, exactly
`eval47/ab47.py::_choose_base(wt=0, ws=20)` — a **plain, non-chain-reward**
root search (`root_search._root_value`, no cascade `w_chain` term). I
reproduced this bit-exactly (see Selfcheck) and used it as both arms' shared
base and as the fixed VS **opponent** in every match, per this thread's
explicit instruction not to use a depth-1 strawman.

**Flag:** memory `dr-mario-eval47-stranded-win.md` records that the config
actually **shipped to silicon** on 2026-08-04 is `strand180_20` =
`cascade_stranded_x.StrandedChainD3Decider(w_chain=180, ws=20)` — the chain
reward *plus* g_stranded, not the plain root search this brief names. The two
are different deciders. I used the brief's literal, explicitly-cited
definition (`ab47.py::_choose_base`) because that is what I was told is
canonical for this comparison; a reader who wants "beats the thing actually
on the MiSTer today" should re-run against `strand180_20`, not this report.

## The one term (and why)

```
val = root_search._root_value(...) - 20 * g_stranded(c1, v1)   # unchanged champion
    + k * opp_danger * cells                                   # NEW, k=0 by default
```

- `opp_danger = min(1, max(opp_col_height[3], opp_col_height[4]) / 16)` — how
  close the **opponent's spawn lane** is to topping out, read from the
  opponent's board at decision time (fixed across our own 32 candidates for
  that decision — our move doesn't change their board).
- `cells` = the **candidate's own** round-1 matched-cell count, already
  computed by `fast_sim_x._expand_core` for all 32 base candidates — the
  ROM-true driver of the attack channel (`comboCounter`/`attackSize` scale
  with matched cells; `cells>=7` is the documented ROM-true single-round
  attack proxy, memory `dr-mario-rom-attack-rule`, 99.9% precision / 100%
  recall over 6078 clears).

Chosen over the brief's other named readings ("value survival more when
opponent is safe") because it is the cheapest one-weight, mechanism-grounded
form: it reaches for the number that already produces damage (`cells`),
gated by the board fact that predicts a kill (spawn-lane height). A
survival-weighting term needs a second free parameter (what counts as
"risk"); this doesn't. At `k=0` the extra term is an **additive zero** — see
selfcheck.

## Selfcheck (before any match was played)

```
[selfcheck] k=0 vs reach_root.choose_base32: 200/200 bit-identical (PASS)
[selfcheck] k=40,opp_danger=1 moved 11/200 decisions (PASS)
```

`k=0` is bit-exact to the champion's own reference implementation
(`reach_root.choose_base32`) over 200 random boards — the null arm is a true
null, not "usually the same." The term is also confirmed **not dead code**:
at extreme dose it does move decisions.

## Simulator

`vs_harness.play_match` (`dr_mario_rl/tmp/vs_aware/vs_harness.py`, "THE
consolidated VS harness," ROM-true attack rule, five mechanics fixes from
2026-07-31). This is the sanctioned **offline Python** VS rig, not Verilator
RTL co-sim — per house doctrine, any move-choice claim from it is provisional
until it clears the co-sim farm. Since the result below is a clean negative,
no RTL spend is warranted (see Next step).

## Stage 1 — cheapest kill test: coarse dose sweep, n=20 seeds/arm (paired, side-swapped)

Seeds 700–719, L11, real NES capsule stream, garbage ON, 4 workers, ~26–32
s/match. `k=0` is the exact-null control (winrate 50.0% CI [50,50] by
construction — sanity check per `h2h_vs.py`'s own doctrine).

| k  | winrate | 95% CI (seed bootstrap) | margin | 95% CI | moved | won-of-moved | atk cand v ref |
|----|---------|--------------------------|--------|--------|-------|---------------|-----------------|
| 0  | 50.0%   | [50.0%, 50.0%]           | +0.00  | [+0.00,+0.00] | 0%  | —     | 7.80 v 7.80 |
| 3  | 52.5%   | [40.0%, 65.0%]           | +0.40  | [-0.90,+1.73] | 35% | 57.1% | 7.83 v 8.15 |
| 7  | 47.5%   | [32.5%, 62.5%]           | -0.95  | [-2.25,+0.28] | 45% | 44.4% | 7.50 v 8.00 |
| 15 | 37.5%   | [22.5%, 52.5%]           | -1.73  | [-3.73,+0.38] | 55% | 27.3% | 6.58 v 7.60 |
| 30 | 45.0%   | [32.5%, 60.0%]           | -0.20  | [-1.80,+1.43] | 40% | 37.5% | 6.50 v 7.22 |
| 60 | 36.2%   | [22.5%, 51.2%]           | -0.82  | [-2.42,+0.90] | 55% | 25.0% | 5.88 v 7.95 (1 draw) |

**No k beats 50%; every CI includes 50%.** The only candidate with a positive
point estimate (`k=3`, 52.5%) has a CI four times wider than the effect and
is the smallest nonzero dose tried — the classic small-n noise signature, not
a gradient (contrast `k=7`→47.5%, immediately below 50%). From `k=7` on, the
trend is **consistently negative and gets worse with dose**: at `k=60` the
candidate's own attack output (5.88) drops *below* the reference's (7.95) —
juicing this term doesn't just fail to help, it makes the search chase the
rare high-`opp_danger` states at the expense of matched-cell output in the
common (opponent-safe) states, the same "overdose sprays junk" failure shape
already documented for `g_tower` in this codebase (memory
`dr-mario-eval47-stranded-win.md`'s dose curve).

## Stage 2 — confirmatory run on the only surviving candidate, n=64 (fresh seeds)

`k=3` was the sole arm with any positive signal at n=20, so it is the one
candidate worth a real-compute confirmation (not the full n≥60 grid — the
other five arms are already unambiguous or negative at n=20, and running
them out further would spend compute on a foregone conclusion). Fresh seeds
800–863 (disjoint from stage 1, guarding against the seed-block artifacts
memory `dr-mario-selfplay-vs-negative.md` warns about — "every apparent win
died on a fresh block").

```
k=3   winrate 50.8%  95% CI [44.5%, 57.8%]   margin +0.48 [-0.16, +1.10]
      n=64 seeds / 128 matches   draws 0   atk 7.45 v 7.63
      moved 30% of seeds, won 52.6% of those
```

The stage-1 52.5% collapses to 50.8% with a CI tightly straddling 50% (and
now including the null on the margin axis too). **Confirmed noise, not a
gradient.**

## Verdict: DEAD

No weight of the opponent-aware term (`k*opp_danger*cells`, swept 3–60
against the `k=0` null, n=20 coarse + n=64 confirmatory on the one candidate
that needed it) beats the opponent-blind champion in VS. Positive doses trend
**negative** past a small threshold, both on win rate and on the candidate's
own attack output — the opposite of "time aggression to their
vulnerability." Total spend: 368 matches, ~40 wall-minutes on 4 cores.

This is consistent with, and adds a second confirmation of, the project's
existing prior: `dr-mario-selfplay-vs-negative.md` found **40+ eval-constant
candidates, zero confirmed VS improvements**, and specifically that **"speed
beats aggression"** — the champion already wins VS by racing (clearing
faster), and garbage/aggression levers compress rather than widen the skill
gap. An opponent-vulnerability-gated aggression term is exactly the kind of
lever that prior predicts should fail, and it did.

## Caveats

- **Offline Python simulator only.** `vs_harness.play_match` is the
  sanctioned rig for this class of question but is not Verilator RTL —
  per house doctrine any move-choice claim is provisional until co-sim
  confirms it. Not pursued here because the result is a clean negative (a
  negative doesn't need RTL confirmation to be actionable — there is no
  candidate to ship).
- **One term, one shape.** Only `k*opp_danger*cells` (a linear multiplicative
  gate on the attack-channel driver) was tested. A different opponent-aware
  reading — e.g. discouraging risky vertical stacking specifically when the
  opponent is *safe* (the brief's other named variant) — was not built,
  because it needs a second free parameter (what counts as "risk") and so
  isn't a one-weight test; per "speed beats aggression" and this result, I'd
  expect it to fail for the same underlying reason, but that is a
  hypothesis, not a measurement.
- **Champion identity discrepancy** noted above (plain root search per brief
  vs. the actually-shipped `strand180_20` chain+stranded decider) — this
  result speaks to the brief's definition, not necessarily to whatever is
  live on the MiSTer today.
- n=20/64 by seed (40/128 matches) is enough to kill a hypothesis this size
  cheaply but not to detect a small (~2-3 point) real effect with tight
  bounds; that was not needed here since the trend is unambiguous and
  negative, not merely "consistent with zero."

## Artifacts

- `experiments/portfolio/opponent-aware/opp_aware_vs.py` — decider + selfcheck + VS runner
- `experiments/portfolio/opponent-aware/tmp/stage1_n20.{log,json}` — coarse sweep
- `experiments/portfolio/opponent-aware/tmp/stage2_k3_n64.{log,json}` — confirmatory run

## Next step

None warranted on this term — task #15 is answered (DEAD) for the
mechanism-grounded, cheapest reading of "opponent-aware." If the portfolio
wants a second shot at task #15, the two live options are (a) the
survival-when-safe variant (two free parameters, real design work) or (b)
re-run this exact term against the actually-shipped `strand180_20` champion
instead of the brief's plain-root-search definition, in case the chain
reward changes the picture. Neither is cheap enough to be a "kill test" —
they'd be genuine new spends, not part of this thread's mandate.
