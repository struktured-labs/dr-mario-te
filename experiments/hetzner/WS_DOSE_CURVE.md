# The g_stranded dose curve, priced on FAILURE RATE

**Result: the shipped `ws=20` is failure-optimal. Reported as a finding, not as
an absence of one — it closes the question rather than leaving it open.**

n=300 seeds per arm, paired by seed, bursty **v1.1** pressure (the human-only
fit), L11, `StrandedChain`-free base decider driven through
`eval47/pressure_rig.run_arm` — the same code path that produced
`BURSTY_V1_RESULTS.md` §5, so the ws=0 and ws=20 arms double as a replication
of the published anchors at 2.5x their sample size.

| ws | bad-ends | dies-ahead | rescued | broken | net | McNemar p |
|----|----------|------------|---------|--------|-----|-----------|
| 0  | 116/300 **38.7%** | 92 (30.7%) | 29 | 85 | **−56** | **<0.0001** |
| 10 | 66/300 22.0% | 42 (14.0%) | 34 | 40 | −6 | 0.56 |
| **20** | **60/300 20.0%** | **30 (10.0%)** | — | — | — | — (shipped) |
| 40 | 65/300 21.7% | 34 (11.3%) | 39 | 44 | −5 | 0.66 |
| 80 | 102/300 **34.0%** | 68 (22.7%) | 37 | 79 | **−42** | **0.0001** |

`rescued`/`broken` are vs the shipped arm on identical seeds.

## The shape is a U with hard walls, and the minimum is where we already are

Both directions away from 20 eventually hurt, decisively: turning the term off
(`ws=0`) costs **+18.7 points** of bad-ends, and quadrupling it (`ws=80`) costs
**+14.0**, both at p≤1e-4. The immediate neighbours (10, 40) are statistically
indistinguishable from 20 (p=0.56, p=0.66), so 20 sits in a **flat basin with
steep sides** — the constant is not finely tuned, but it is in the right place
and there is no better place nearby.

## THIS NULL IS A REAL NULL, and the distinction matters

The arms are **not inert**. ws=10 and ws=40 each produce ~75-85 discordant
pairs — they change the outcome on roughly a quarter of seeds — they simply
**trade wins for losses symmetrically**. That is the opposite of the selfseal
lane's flat null, where the term changed 0.63% of decisions and the experiment
could not distinguish "wrong idea" from "never fired". Here the experiment had
ample power and the answer is that the dose is already optimal.

## What it means for the risk-neutrality hypothesis

**It weakens the hypothesis for THIS knob, and only this knob.** `ws=20` was
selected on mirror margin and VS win rate — SPEED and ATTACK — and it lands
exactly on the survival optimum too. For `g_stranded`, the speed-tuned and
survival-tuned settings coincide; there is no trade being missed.

Note `dies-ahead` tracks the same U (30.7 → 14.0 → **10.0** → 11.3 → 22.7), so
the dies-ahead signature is not separately purchasable by re-dosing this term
either.

**⇒ The lever is not a coefficient inside the existing feature set.** Three
lanes now agree independently: this curve, the portfolio failure-objective
sweep (all CIs straddle 0), and the eval-headroom lane (best linear refit of
the existing 11 terms buys **−0.57** pills/decision while an oracle buys
+3.70). Coefficient space is exhausted; the missing thing is a term that is not
in the feature set.

That is what makes `spawn_lane_gate_probe.py`'s result the natural next step:
a NEW gated spawn-lane term flips 4.28% of decisions at k=6/dose=640 — well
above the ~2% testability floor — so it is worth running where a re-dose is not.

Rig: `ws_dose_bursty.py` · model: `fit_bursty_v11.py` (28 volleys / 89 clears)
Raw: `results/wsbursty/{arm_ws*.json, summary.json}`
