# Next champion iteration — plan of record

**Written 2026-08-10, after the v8 ship and the stage-2 rollout NO_GO.**
North star unchanged: **beat dr. lulu.** Everything below is ranked by that, not by tractability.

---

## Where we actually are

Three things landed today. Two of them are good news and one of them reframes the program.

| | verdict |
|---|---|
| **v8 REMATCH cart** | shipped, gated, pushed. `c0082cb34259007854120d3d4ab9fa27` |
| **seed-30011 freeze** | **not ours** — reproduces on the unhardened cart at identical frames |
| **stage-2 learned evaluator** | **rollout NO_GO** — the +0.0575 AUC edge did not transfer |

**The uncomfortable sentence: v8 plays exactly as well as the build dr. lulu has already been
beating.** Everything shipped is crash-hardening and execution fidelity. No strength was added
today, and the one bet that was supposed to add strength came back null.

### What the NO_GO actually proved

- dies-ahead 12.13% → 11.33%, **−0.80pp [−2.20, +0.60]**, McNemar p=0.2793 over 3,000 paired seeds.
- A **dose-matched, label-blind null** — the same LUT with rows permuted, holdout AUC 0.4746,
  scaled so it flipped the same fraction of plies — did **just as well**. DiD **−0.27pp**.
  ⇒ the effect present is **indistinguishable from a random perturbation of the same size**.
  Not underpowered. **Undirected.**
- **Churn is the story**: perturbing **1.8% of plies reshuffles ~20% of game outcomes.** Only
  760 of 3,000 pairs identical. The champion cleared **301 games** the new arm does not.
- **15,000 games were spent without ever establishing that *any* evaluator improvement moves
  dies-ahead.** The single measurement is consistent with a **slope of zero.**

That last line is why the plan below leads with a calibration arm and not with another model.

---

## P0 — ORACLE-CEILING ARM

**Question:** does *any* root re-ranker move dies-ahead at all?

**Design.** Under the unmodified stage-2 prereg. At plies where `d_spawn_h >= 12 OR viruses <= 8`,
fork the **top-4 champion candidates 15 pills forward** with the real policy and real lulu
injection; pick the survivor-with-virus-progress. Play the champion everywhere else. This measures
the **maximum dies-ahead reduction reachable by any root re-ranker**, in endpoint units.

**Decisive in both directions — this is the point:**

- **Oracle NO_GO** ⇒ root re-ranking is **structurally dead** for dies-ahead. No leaf evaluator
  should be funded for this endpoint again. **We close the lane on evidence rather than fatigue**,
  and the search moves to mechanism (garbage-reactive policy, tempo, attack channel).
- **Oracle GO at −2 to −3pp** ⇒ the AUC gap becomes **priceable for the first time**, and stage-2's
  0.7220 stops being a proxy number nobody can convert.

**Required before it runs:** pre-registered gate-set **and a killed mutant** — an oracle fed a
*shuffled* survival label must **fail**. Without that the arm can only confirm itself.

**Cost:** ~18,000 game-equivalents, ~8.6 h Hetzner behind the running jobs.

---

## P0 — PER-PLY FLIP PROVENANCE

15,000 games produced a NO_GO with **zero mechanism**. `flips` is logged as a bare integer: no ply
index, no `t_to_end`, no tie-vs-decided tag, no first-divergence marker. **The 301 broken clears
are undiagnosable.**

Log per flip: ply index · `t_to_end` · viruses remaining · max height · tie-vs-strict flag ·
champion rank of the chosen action · base action · treatment action.

**Mandatory for every future arm.** This is cheap, blocks nothing, and is the difference between
a null result and a null result you can learn from.

---

## P0 — POWER FLOOR: N ≳ 4,500 PAIRED SEEDS

With 611 discordant clears the paired CI half-width on clear rate is **±1.58pp**. The
pre-registered **+1.0pp non-inferiority margin was unreachable at N=3,000 by construction** —
the arm could not have passed its own gate even if the model were perfect.

**Rule: any arm at this flip rate is sized ≥4,500 paired seeds, or it is not run.**

⚠ Related: **19 of the 28 topouts avoided reappeared as 300-pill stalls (68%).** Net bad-ends fell
so the stall condition did not fire — but that is exactly the mechanism the condition exists to
catch. Future gates must score stalls at parity with topouts.

---

## P1 — θ400 POCKET CORE (#101)

**The only route to tucks on the platform he actually plays.** θ is a **coprocessor firmware
constant** (`DRCOPRO_TUCKV3_THETA`, default 150), not one of the 57 cart flags. θ400 exists today
**only** as `NES_theta400_20260809.rbf` for MiSTer. The Pocket core is tuck **v1** — no θ mechanism
at any dose. A tuck cart on that core is inert or worse.

- Firmware-only by design: **zero RTL change**, <1 KB inside a 16 KB `$readmemh` ROM.
- But it needs a **full clean refit at 98.8% ALM occupancy**, its own **bijection proof**, and its
  own **value A/B**.
- ⚠ **The −11.0 pill headline does not transfer.** Cart-level measured value is **−4.16**.
  Re-price before funding the fit.

---

## P1 — TUCK FALL-BUDGET GUARD REWRITE (#102)

Current guard **fails its own prereg**: the predicate keys on the **final** column when the hazard
is on the **approach** column. Rewrite with a fresh prereg. The
*veto-degrades-to-no-tuck* property must survive the change. Value can only be priced in the
**Mesen rig**, not the fast sim — the fast sim cannot represent the fault.

---

## P1 — `d_spawn_h` AS A RESOLUTION FIX

The SPAWN term is a **clipped sensor**: it saturates at 8, exactly where games are decided.
Unclipped it scores **AUC 0.929 vs 0.900**. It survived into the stage-2 LUT feature set — but the
LUT as a whole did not transfer, so the term has never been tested **alone** as a resolution
change rather than as part of a learned re-weighting.

This is the cheapest remaining shot at the **vocabulary wall**: the wall is that a fatal move
scores *better* on all 11 features. Widening a saturated sensor is a vocabulary change, not a
weight change — a different class of intervention from the one that just failed.

---

## P2 — FREEZE ROOT CAUSE (#42 / #99)

Now known **pre-existing** and **deterministically reproducible**: seed 30011, match #44, mode 4
holds 22,529 frames. Reproduces on the unhardened `c16271c6` at the identical frames.

`srchGapMax=1199` **does not discriminate a pause from a wedge** — a new discriminator is needed
before any fix can be gated. Honest per-evening freeze risk today: **~2.5% (95% upper 11.3%)**.

---

## Sequencing

1. **Now** — land per-ply flip provenance (cheap, unblocks everything downstream).
2. **Behind the running Hetzner jobs** — oracle-ceiling arm with its killed mutant.
3. **Branch on the oracle.**
   - GO ⇒ re-open the evaluator lane, now with a conversion factor, sized at N≥4,500.
   - NO_GO ⇒ **stop funding leaf evaluators for dies-ahead.** Move to mechanism work and to
     `d_spawn_h` as a vocabulary change.
4. **In parallel, independent of the branch** — θ400 Pocket refit and the tuck guard rewrite.
   These are execution-fidelity levers and do not compete with the evaluator question.
5. **Opportunistic** — freeze discriminator, using the deterministic reproducer.

---

## Design laws this iteration must obey

- **Every arm carries a dose-matched, label-blind null.** Stage-2 only knows what it knows because
  it built one. An arm without a null cannot distinguish direction from churn.
- **Every check must be shown to FAIL on a deliberately wrong input,** in both directions.
- **Pre-register verdict rules, feature sets and quantisation before any data.**
- **Ask whether the model can represent the fault** before sweeping thresholds. A tight CI around
  the wrong quantity is worse than showing nothing.
- **Churn is not free.** A 4x-overdosed random term *raises* dies-ahead 1.13pp and costs 2.00pp of
  clear rate. Any always-on change that perturbs clean-game behaviour loses at population scale
  unless breakage is essentially zero.
