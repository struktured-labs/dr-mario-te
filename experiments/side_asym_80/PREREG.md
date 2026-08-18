# PRE-REGISTRATION — task #80, side asymmetry in the kill channel

Written and committed **before any measurement run existed**. Proof of timing is
recorded in the commit message (`out/` contains only the throwaway smoke files and
the gate log; no arm output, no results JSON).

## 0. What is actually being re-tested, and what could not be recovered

The stored claim is *"6.0% vs 0.67% death rate by side, p=0.02"* in VS games,
attributed to the tier-3 adversary lane (`experiments/adversary_t3`).

⚠ **The original numbers cannot be recomputed from any committed artifact.**
`batch_run.evaluate()` averages a seed's two side-swapped games into one row
(`died` ∈ {0, 0.5, 1}) *before* anything is persisted, so the side label is
destroyed at aggregation and `fourway_result.json` does not contain it. The
producing invocation was not kept. Per [[dr-mario-proof-provenance-rot]] that makes
6.0%/0.67% **an assertion, not a result** — so this re-test treats those figures as
the *effect size the work was funded to detect*, not as a measurement to reproduce.
The re-test's own rows keep the game as the emitted unit precisely so this cannot
recur.

Related prior: `fourway_result.json` shows every death-seed at `died = 0.5` — the
champion never died on both sides of a mirror pair. That is *consistent* with a side
effect and equally consistent with deaths simply being rare and unrepeatable. It is
not evidence for either and is not used as one.

## 1. Hypothesis

**H1 (primary).** In mirror-matched VS games the champion's death rate depends on
which SIDE (physical seat 0 vs seat 1) it occupies.

**H2 (mechanism).** Any such asymmetry is structural — a property of the harness or
the game mechanics — rather than of the deciders. The named candidate mechanism,
identified from the code before running anything:
`vs_harness.play_match` iterates `for who, dec in ((0, dec0), (1, dec1))` and
`break`s on the first terminal result, so **seat 0 moves first in every round** and
seat 1 can be denied its move in the round the match ends. Seat 0 banks garbage
first and wins races it entered level.

## 2. Arms

| arm | pairing | what varies within a seed | seeds |
|---|---|---|---|
| `adv` | champion vs evolved tier-3 adversary (`best_vec = [234, 20, -31, 233, 37]`) | champion's seat (`swap` 0/1) | **56000–57499** (n=1500) |
| `mirror` | champion vs champion | **board orientation** (0/1) | **53000–54499** (n=1500) |

`adv` is the original configuration and carries the primary endpoint. `mirror` is
the structural control.

**Why the mirror arm is not vacuous.** Self-vs-self is 50% by construction *for the
win rate under arm-swapping* ([[dr-mario-vs-harness-defects]] #2), and indeed
swapping the arms in a mirror is information-free — both deciders are the same
object, so `swap=0` and `swap=1` are literally the same call. That is why this arm
swaps the **boards** instead. `VsMatch` draws each seat's virus board from a
different stream (`seed + 1000*k`, `vs_env.py:43`) while both seats share one
capsule stream (`vs_env.py:49`), so the two seats genuinely play different games and
one really does lose. Running each seed in both board orientations makes each seat
see each board exactly once, so **the board draw cancels exactly** and any residual
seat preference is harness/mechanics. Verified, not assumed: gate section C measures
40 seeds and finds virus boards differ on 40/40 and capsule streams identical on
40/40.

## 3. Statistics

**Unit of analysis is the SEED throughout** — the two games of a seed share a
capsule stream and a board pair. Per-game counting is how a four-seed effect once
impersonated p=0.0002 here ([[dr-mario-sample-size-audit]], unit-of-analysis rule).

**Primary endpoint (`adv`), named in advance:** the difference in champion death
rate between the champion's two seats, Δ = rate(seat 0) − rate(seat 1).
- test: **exact McNemar** on the seeds where the champion died in exactly one seat
- interval: seed-clustered bootstrap (10,000 reps) on the per-seed difference

**Secondary (`mirror`), the structural quantity:**
- P(seat 0 wins), pooled over both board orientations, seed-clustered bootstrap CI.
  Under "no positional effect" this is **0.5 exactly**, because the board draw is
  exchanged between the two orientations.
- the decomposition: per seed, does the same **seat** win both orientations
  (positional) or does the same **board** win both (skill/board)?
- death-side split among games that ended in a topout, seed-clustered.

## 4. N, and the minimum detectable effect

From `power.py` (run it; the prereg quotes its output rather than a hand number,
per measurement-rules #25):

```
 N seeds  disc|claim  disc|null   SE(pp)  MDE(pp)  CI95+-(pp)  excl claim
      80         5.3        4.8    2.751    7.703       5.392       False   <- the ORIGINAL n
     150         9.9        9.1    2.009    5.625       3.938        True
    1500        98.8       90.8    0.635    1.779       1.245        True   <- REGISTERED
```

**At the original n=80 the 95% CI half-width (±5.39 pp) is wider than the claimed
effect itself (5.33 pp).** That design could confirm nothing and exclude nothing;
a p=0.02 emerging from it is exactly the regime measurement-rules #23 and #13 warn
about. **N = 1500 seeds per arm** gives MDE 1.78 pp against a 5.33 pp claim — a 3.0x
margin — and a null there can exclude the claimed effect by 4.3x.

Mirror arm at n=1500: worst-case CI half-width 0.0253 on P(seat 0 wins), inside the
0.05 bound a "no bias" verdict requires.

## 5. Decision rule (registered; encoded in `analyze_side_asym.py`, gated by `gate_verdict.py`)

**Primary (`adv`):**
- **CONFIRM** — McNemar p < 0.05 **and** higher/lower death-rate ratio ≥ 2.0
- **REFUTE** — p ≥ 0.05 **and** the 95% CI on Δ excludes ±5.33 pp
- **INDETERMINATE** — p ≥ 0.05 but the CI still contains 5.33 pp (underpowered, not
  negative), **or** p < 0.05 with ratio < 2.0 (real but far smaller than claimed)
- **UNMEASURABLE** — zero champion deaths in either seat. This is *not* a symmetry
  finding: the arm cannot express the quantity (rule 24 #2).

Direction is **not** privileged — a large effect favouring either seat reads as
CONFIRM, and the report must name which seat.

**Mirror:**
- **STRUCTURAL_BIAS** — seed-clustered CI on P(seat 0 wins) excludes 0.5
- **NO_STRUCTURAL_BIAS** — CI contains 0.5 **and** half-width < 0.05
- **INDETERMINATE** — otherwise

## 6. Gates that must pass before any verdict is read

1. **Killed mutant on the side counter** (`--mutant swap_scoring`): relabelling
   sides at scoring time must exchange every by-side count **exactly**. Validated on
   synthetic data including a negative control — an inert counter that ignores the
   side is rejected.
2. **Population mutant** (`--mutant same_board`, gate standard rule 7): both seats
   forced onto one virus board. **Registered prediction: P(seat 0 wins) = 1.000.**
   With identical boards, identical capsule streams and identical policies the two
   seats play the same moves, so the only thing that can separate them is turn
   order — seat 0 moves first and its terminal condition is detected first. If this
   comes back at 1.000 it is a *direct demonstration* of the first-mover asymmetry
   in the exact-tie limit; if it comes back near 0.5 the stated mechanism (H2) is
   wrong and must be withdrawn.
3. **Verdict-script mutants**: 7 synthetic tables straddling every threshold,
   including a significant-but-tiny effect (must not read CONFIRM) and a null at the
   original n=80 (must not read REFUTE). All must route correctly before real data.
4. **Non-degeneracy**: mirror-arm virus boards must differ on every seed.

## 7. Seed-block registration

Registered **53000–58499** (below 65536, so seed == stream key and the registry is
readable by inspection — [[dr-mario-seed-space-is-32767]] corollary). This spans the
two arms' own seeds *and* the `seed + 1000` boards their seat-1 sides consume:

- mirror seeds 53000–54499 → boards 53000–54499 (seat 0) and 54000–55499 (seat 1)
- adv seeds 56000–57499 → boards 56000–57499 (seat 0) and 57000–58499 (seat 1)

Taken from the free range 50100–59999, avoiding 51100–52099 (reserved by the S0-B
lane, task #125). Disjoint from the spent blocks 41100–52099, 60000–62999,
70000–80999, 90000–90499.

⚠ Smoke tests during rig development used 51100–51115 and 51110–51115. Those runs
are throwaway, are not pooled into any arm, and their output is not read.

## 8. Scope — what a result here does NOT cover

Offline fast sim only; level 11; `max_pills` 300; garbage ON; champion-vs-adversary
and champion-vs-champion pairings only. Nothing here is a silicon or RTL claim, and
nothing here transfers to human opponents. A finding in the mirror arm is a
statement about **this harness**, which is the point — but it is then a question
about whether the ROM shares the same turn-order structure, and that is not tested
here.
