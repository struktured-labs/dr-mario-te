# What is the tuck executor worth? An independent fast-sim answer

Corroboration by a different method for the co-sim farm's RTL 2×2. Same four arms, different
simulator, different failure modes, n=400 paired seeds per arm instead of tens.

**Status:** complete. 6,000 fast-sim games across the 2×2, the v1-hazard bracket, the A′
control arms, the θ sweep and the divergence rigs.

---

## The answer, in one paragraph

**Nobody has yet validly measured what a working tuck executor is worth — including me.**

On the fast sim the executor looks worth having: the full program beats the shipped champion by
**−6.50 points of bad-end rate [−11.25, −1.75], p=0.0088** over 400 paired seeds, clears 26
pills faster, and gets better as it fires more. That effect briefly appeared to be confined to
seeds 120–399, which would have made it far less trustworthy — but five checks on the games
already played established the split as a
[coincidence](#the-block-split-was-a-coincidence-and-here-is-how-that-was-established), so the
n=400 estimate stands as written. It is still a single modest p-value on one simulator.

The RTL's own answer, which contradicted mine outright, has since been withdrawn: its tuck leaf
scored *every* candidate a win because the board upload destroyed itself, and a separate
pill-colour bug voided its descriptor tables. So there is currently **no valid silicon
measurement of tucks at all**, and my own result is suggestive rather than established.

**Do not commit hands to a cart rebuild.** Two safety findings survive, though with different
strengths than this document claimed an hour ago:

- **Never ship tier-3 firmware to a cart without the executor.** Confirmed on both rigs *as a
  mechanism*, but **not yet as a magnitude**: the co-sim's arm B turned out to be contaminated
  too (`tre_commit` writes `TP_TARGET → D_BC`, so drop mode ignores the *descriptor* but not
  the *placement* — spurious wins moved its published column as well). Its 0/58 is the
  mechanism running at a defect-inflated rate, not an independent check of my 80.8%. My own
  number is the better current estimate, and it is now the more credible one for a reason that
  emerged later: post-fix the RTL publishes on 13% of decisions against my 11.5%, so this rig
  and the fixed firmware fire at nearly the same rate.
- **Never enable the executor on v1 firmware.** This one is genuinely clean on both sides — v1
  has no value gate, no tuck scoring, and never touches `LeafEval`, so neither defect can reach
  it. Harmful under the conservative convention and catastrophic under the driver-implied one,
  with the whole bracket negative.

Those are the night's real output — two reliable ways to destroy the champion, now documented
so nobody does either by accident.

---

## The number, at this rig's dose

**Rebuilding the cart with the executor enabled AND tier-3 firmware takes the shipped
champion's bad-end rate under bursty human pressure from 19.2% to 14.0% — a paired difference
of −5.25 points, 95% CI [−10.0, −0.75], McNemar rescued=57 harmed=36, p=0.0375, n=400 —
and clears the level 26.0 pills faster, CI [−32.7, −19.3].**

That is the D − A comparison: the full program versus what is on the cart today.

**⚠ That average hides real heterogeneity, and the part it hides is the part the co-sim can
see.** Split at the co-sim's own seed boundary — seeds 0–119 are exactly the block its RTL arms
run — the effect is not uniform:

| seed block | n | A → D bad ends | paired Δ [95% CI] | McNemar |
|---|---|---|---|---|
| **0–119** (the co-sim's block) | 120 | 16.7% → **20.0%** | **+0.033 [−0.050, +0.117]** | 12 vs 16, p=0.57 — **wash, wrong sign** |
| 120–399 | 280 | 20.4% → 11.4% | −0.089 [−0.146, −0.032] | 45 vs 20, p=0.0026 |
| 0–399 (headline) | 400 | 19.2% → 14.0% | −0.053 [−0.100, −0.008] | 57 vs 36, p=0.038 |

A permutation test on the block labels puts a split this extreme at **p=0.023**, on a boundary
specified externally before I looked. That looked like real regime structure, and I rewrote this
document around it.

**It is not. `block_forensics.py` ran five checks on the 400 games already played, and the
split is a coincidence — the headline recovers.** The verdict and its evidence are in
[the block split](#the-block-split-was-a-coincidence-and-here-is-how-that-was-established);
the short form is that the effect drifts smoothly across seed ranges rather than stepping at
119, and the one genuine structural boundary in the seed space shows nothing at all.

**So −5.25 points at p=0.038 over n=400 is the estimate.** It is a single modest p-value and
should be treated as such, but it is not undermined by the block split, and **the project does
not need to stratify its seed ranges.**

**The survival half of that is entirely stalls, not topouts** (28 → 12, p=0.014; topouts
49 → 44, p=0.65 — a wash), which is the signature of digging buried viruses out rather than of
finishing before the garbage arrives. See the decomposition below; it is the strongest single
piece of evidence here that the executor does what a tuck is *for*.

**De-confounded, the number gets slightly better, not worse.** Arms B and D take their base
candidates from a reachability-filtered pool that arm A does not have, so a control arm A′ was
run — the tier-3 decision path with θ set so no tuck can pass the gate (verified: 0 fires, 0
tuck wins in 400 games). The filter on its own is a wash (A′ − A: 19.2% → 20.5%, McNemar 8 vs
13, p=0.38; pills +0.54 [−0.62, +1.69]), and it was very slightly *hurting*, so isolating the
tuck program **strengthens** the result: **D − A′ = 20.5% → 14.0%, −6.50 points
[−11.25, −1.75], McNemar rescued=59 harmed=33, p=0.0088**, with the same stalls-only signature
(stalls 26 → 12, p=0.034; topouts 56 → 44, p=0.22).

The question as literally posed — *what is executing tucks worth with tier-3 firmware* — is
D − B, the executor's own value with the firmware held fixed, and it is enormous: bad-end rate
80.8% → 14.0%, a paired difference of **−66.8 points, CI [−71.8, −61.8]**, McNemar
rescued=275 harmed=8, p=1.2×10⁻⁷⁰. But B is a configuration nobody should ever ship (see
below), so that number measures how broken the baseline is at least as much as how good the
executor is. **D − A is the number to act on; D − B is the answer to the question asked.**

### And the finding that costs nothing to act on

**Never ship tier-3 firmware to a cart without the executor.** Arm B — today's `DRTUCK=0`
cart running s20t3 — collapses from 19.2% to **80.8%** bad ends under pressure (McNemar
rescued=13 harmed=259, p=1.5×10⁻⁶⁰), and from 99.8% to 34.0% clear even on a *clean* stream
where the champion essentially never fails. Tier-3 without the executor is not a small
regression; it is a broken build. The mechanism is exact and predicted by
`tuck_scan.py`'s own docstring: a winning tier-3 tuck overwrites `D_BC`/`D_BO`
(`tuck_v3.py:644-645`), the pill is steered to the tuck's column and then plain-dropped,
landing a median of **5 rows** shallower than the search scored, about **14 times per game**.

---

## The 2×2

Arms are `firmware vocabulary × cart executor`, all four on the same 400 seeds, every delta
within-seed paired.

|  | `drop` (today's cart) | `tuck` (a `DRTUCK=1` cart) |
|---|---|---|
| **v1** `e970e9ab` | **A** the shipped champion | **C** executor on, v1 firmware |
| **t3** `5d010f62` | **B** ship tier-3 today | **D** the full program |

### Bursty v1.1 pressure — survival (L11, n=400, θ=150)

| arm | clear | bad ends | dies-ahead | mean pills | executor fires/game |
|---|---|---|---|---|---|
| **A** v1 × drop (SHIPPED) | 80.8% | 77/400 (19.2%) | 44/400 (11.0%) | 157.3 | 0 |
| **B** t3 × drop | 19.2% | 323/400 (80.8%) | 52/400 (13.0%) | 121.2 | 0 |
| **C** v1 × tuck | 73.8% | 105/400 (26.2%) | 54/400 (13.5%) | 171.5 | 4.16 |
| **D** t3 × tuck | 86.0% | 56/400 (14.0%) | 43/400 (10.8%) | 126.4 | 7.24 |

| comparison | bad-end rate | paired Δ [95% CI] | McNemar | pills-to-clear |
|---|---|---|---|---|
| **D − A** full program | 19.2% → 14.0% | **−0.0525 [−0.100, −0.008]** | 57 vs 36, p=0.038 | **−25.99 [−32.7, −19.3]** (n=287) |
| **D − B** executor, fw fixed | 80.8% → 14.0% | −0.668 [−0.718, −0.618] | 275 vs 8, p=1.2e−70 | −51.6 [−65.1, −37.5] (n=69) |
| **C − A** v1 executor | 19.2% → 26.2% | **+0.070 [+0.018, +0.123]** | 46 vs 74, p=0.013 | **+12.70 [+5.3, +20.0]** (n=249) |
| **B − A** tier-3 today | 19.2% → 80.8% | +0.615 [+0.560, +0.670] | 13 vs 259, p=1.5e−60 | +28.25 [+11.3, +44.8] (n=64) |

**Dies-ahead moved on no arm at θ=150.** Every dies-ahead CI in the table above includes zero
(D − A: −0.003 [−0.048, +0.040]). At this dose the executor changes whether games are lost, not
the signature of how they are lost. The one exception anywhere in this study is arm D at θ=0,
where the dose is 2.8× higher and dies-ahead does move (11.0% → 6.5%, −4.5 points
[−8.25, −0.75]) — see the θ sweep below.

### Clean stream — speed (L11, n=400, θ=150)

| arm | clear | bad ends | vs A, pills-to-clear [95% CI] |
|---|---|---|---|
| **A** v1 × drop | 99.8% | 1/400 | — |
| **B** t3 × drop | 34.0% | 264/400 | +38.35 [+30.9, +46.1] |
| **C** v1 × tuck | 99.5% | 2/400 | **+7.83 [+4.7, +11.0]** |
| **D** t3 × tuck | 99.8% | 1/400 | **−15.58 [−18.3, −13.0]** |

Arm A's 1 failure in 400 clean games independently reproduces the 1,474-game census finding
that the champion essentially never fails on a clean stream — which is why the clean axis can
only measure speed. On that axis the full program is **15.6 pills faster to clear** at an
identical clear rate, and the v1 executor is **7.8 pills slower**.

> **Read arms B, C and D against the co-sim before acting on them.** Arm B is confirmed by the
> RTL and harsher there. Arm D is *contradicted* by the RTL, which has the same configuration
> at 0 of 17 games cleared. The tables above are this rig's numbers; the contradiction and what
> is known about it are in
> [the disagreement](#the-disagreement-that-matters-and-what-it-costs).

---

## v1's executor is not neutral — it is harmful

This is the cleanest executor test in the whole program, and it is the one the project has
never run. v1 calls its enumerator *after* the search (`build_copro_d3.py:93`) and never
writes `D_BC`/`D_BO`, so **the decision is pure base32 in both modes**: identical brain,
identical chosen column and orientation, and the only thing the executor can change is the
landing row. Under that isolation it makes the champion measurably worse — bad ends
19.2% → 26.2% (p=0.013), 12.7 pills slower to clear under pressure, 7.8 pills slower on a
clean stream.

The reason is visible in the on-policy descriptor audit, which is also the strongest
reconciliation point with the co-sim farm:

| arm | descriptors published | coherent | lands deeper than the drop |
|---|---|---|---|
| **C** v1 × tuck | 43,669 | 12,605 (28.9%) | **1,663 (3.8%)** |
| **D** t3 × tuck | 2,896 | 2,896 (100%) | 2,896 (100%) |

The co-sim's corresponding figures were **withdrawn** on 2026-08-07 — a 1-based/0-based pill
colour bug at its copro mailbox, and then a tuck-leaf defect that scored every candidate a win,
voided its descriptor tables and every tier-3 tuck number it had produced. **This document no
longer cites them, and the earlier agreement it claimed against them should be disregarded**
rather than treated as weakened. The rate above is this rig's own, unchecked by a second
method until the co-sim re-runs.

So v1 fires ~4 times a game, and when it fires it drops the pill into a deep pocket the search
never scored — burying material the search had deliberately left reachable. `tuck_scan.py`'s
own docstring predicted exactly this: *"publishing a tuck the executor cannot perform … is
strictly worse than no tuck."* The measurement is that it is worse even when it *can* perform
it, because v1 chooses its target column independently of `best_col`.

### Both ends of the bracket say the same thing

The numbers above use the **conservative** convention: a descriptor the executor cannot
perform degrades to a plain drop. That is what the co-sim farm assumes, so the two rigs are
comparable, but it is *not* what the driver source implies —
`patch_cartridge_copro.py:1920-1926` steers to the approach column while the capsule is above
the trigger row and to `best_col` at or below it, with no check anywhere that the switch is
possible. If the traverse is blocked the capsule simply lands where it is. Running that
convention instead:

| convention | clear | bad ends | fires/game | vs A |
|---|---|---|---|---|
| conservative (`drop`) | 73.8% | 105/400 (26.2%) | 4.16 | rescued=46 harmed=74, **p=0.013** |
| driver-implied (`approach`) | **6.8%** | **373/400 (93.3%)** | 36.01 | rescued=2 harmed=298, **p=4.4e−86** |

Under the driver-implied convention the executor fires 36 times a game — nearly all of them
blocked descriptors dumping the capsule in the approach column — and only 1.38 of those land
deeper. Bad ends decompose into stalls 28 → 121 and topouts 49 → 252, both catastrophic.

**The truth lies between the two rows, and the whole interval is negative.** No convention
this rig can construct makes enabling the executor on v1 firmware anything other than a
regression, which is the point of bracketing rather than picking one.

---

## The survival win is digging, not racing

The obvious worry about D − A is that it is an artifact of tempo: the bursty model injects
garbage in response to the AI's own clears, so an arm that finishes sooner absorbs less total
garbage (D takes 39.96 garbage cells per game against A's 52.84), and "survives more" could
just be "was exposed less". Decomposing the bad ends settles it, and the answer is the
opposite of the worry:

| failure mode | A → D | McNemar | |
|---|---|---|---|
| **stalls** (300-pill cap: viruses still buried, out of pills) | **28 → 12** | rescued=27 harmed=11 | **p=0.014** |
| **topouts** (board reached the spawn row) | 49 → 44 | rescued=42 harmed=37 | p=0.653 — wash |

**The entire survival benefit is in stalls. Topouts do not move at all.** That is the wrong
signature for a tempo artifact — absorbing less garbage would relieve *topouts*, the failure
mode garbage causes. It is exactly the right signature for a tuck executor: a stall is a board
the AI cannot finish because viruses are buried under material it cannot reach, and reaching
under overhangs is the one thing a tuck does that a straight drop cannot.

The mechanism is visible in the failure statistics too. Arm B's topouts leave a median of **25
viruses** on the board — mid-game collapse from systematically shallow placements — where
A's, C's and D's leave 2–3, the near-the-doorstep signature the project already knows.

So the speed result and the survival result are *not* the same effect seen twice, and the
earlier draft of this document was wrong to suggest they might be. They are two distinct
effects: the executor clears faster (26 pills under pressure, 15.6 clean) *and* it separately
rescues boards that would otherwise be unfinishable.

For completeness, the v1 executor decomposes the same way and harms on both axes without
either reaching significance alone (stalls 28 → 40, p=0.14; topouts 49 → 65, p=0.10), while
the combined bad-end test does (p=0.013).

---

## Which question these arms answer

**These arms use this rig's own enumerator and scorer. They price an idealised tuck
vocabulary, not the descriptors `5d010f62` publishes.** That distinction is not pedantry: the
tuck descriptor is an *RTL output*, so "honour the descriptor this firmware published" and
"pick the best tuck available" are different experiments with different answers, and the gap
between them prices how much of the ideal vocabulary today's firmware actually finds.

A full descriptor-**consuming** arm is not buildable here, and the reason is structural rather
than a matter of effort: the descriptor is computed from the live board, so it exists only for
positions the RTL itself visited. From the first ply where the two rigs diverge, no published
descriptor exists for the board this rig is looking at. Consuming a descriptor stream requires
the RTL in the loop — which is the co-sim, by definition.

The tractable substitute is shipped: `export_decisions.py` runs this decider over the co-sim's
own `hostdata_l11_20` and `hostdata_l11_hz30` corpora and emits `(col, o4)` per board, which is
exactly the ply-1 slice of the arm that cannot be built. Diffing it against the RTL's choices
separates "different tuck chosen" from "same tuck, different outcome". Output:
`results/decisions_for_cosim.json` — this rig picks a tuck on 2/20 and 5/30 of those boards,
with a tuck candidate available on 7/20 and 19/30.

---

## The block split was a coincidence, and here is how that was established

I weakened my own headline on a p=0.023 seed-block split and rewrote this document around it.
That was premature. Five checks on the games already played — no new CPU — say it is noise.
Reported here at length rather than quietly reversed, because "I gave up a real result to a
coincidence" is exactly as much a finding as the split would have been.

**1. The blocks barely differ on their inputs.** Every feature a seed fixes before a pill is
placed:

| feature | 0–119 | 120–399 | perm p |
|---|---|---|---|
| viruses, virus rows, column spread, colour balance | identical to 3 d.p. | | 0.22–1.00 |
| `pill_doubles_frac` | 0.346 | 0.332 | 0.051 |
| `pill_distinct` | 8.92 | 8.99 | 0.107 |
| **`pill_switch_rate`** | **0.833** | **0.867** | **0.0000** |

One of ten features differs (chance expectation at ten tests: 0.5). **But that feature does not
predict the effect** (r = −0.059, p = 0.23, check 5), and block membership can only matter
through something the block determines.

**Where that difference actually comes from — and I attributed it wrongly at first.** I wrote
that it was an `s0 = (seed>>8)&0xFF` property, since s0 is 0 for every seed below 256. Splitting
three ways refutes that:

| `pill_switch_rate` | 0–119 (s0=0, low s1) | 120–255 (s0=0, high s1) | 256–399 (s0=1) |
|---|---|---|---|
| mean | **0.8326** | 0.8690 | 0.8648 |

| contrast | Δ | perm p |
|---|---|---|
| 0–119 vs 120–255 — **same s0**, differing s1 | −0.0364 | **0.0000** |
| 120–255 vs 256–399 — **s0 changes** | +0.0042 | 0.44 |

The anomaly is **low seeds**, not the LFSR high byte: it appears entirely *within* s0=0 and
crossing the s0 boundary does nothing. Seeds below roughly 120 produce slightly more repeated
consecutive capsules; seed 256 is not a meaningful boundary for the capsule stream. This
matters for anyone designing a seed block — the boundary worth straddling is at the bottom of
the range, not at 256 — and it does not change the fluke verdict, since the feature predicts
nothing either way.

**2. The shape is a gradient, not a cliff — and the wobble inside the "effect" block is bigger
than the gap that defined it.**

| block | n | mean effect |
|---|---|---|
| 0–119 | 120 | **+0.033** |
| 120–212 | 93 | −0.172 |
| 213–306 | 94 | −0.075 |
| 307–399 | 93 | −0.022 |

Spread across the three thirds of the supposedly-uniform block: **0.151**. Gap from 0–119 to
its nearest third: **0.055**. The effect wanders, decaying back toward 0–119's value by the
last third. "0–119 is a different regime" is not a description this data supports; "the
per-seed effect is noisy at n≈100" is.

**3. A scan finds bigger splits elsewhere.** The largest split anywhere is |0.166| at k=94,
against |0.123| at the pre-specified k=119, and under the null the maximum over all split
points exceeds the k=119 value **39% of the time**. The p=0.023 remains honest *for a
pre-specified boundary* — but the data is full of apparent block structure, which is what a
binary outcome at this n looks like.

**4. The one structural boundary in the seed space shows nothing.** `NesPillSource` maps
`s0 = (seed>>8)&0xFF`, so seeds below 256 and seeds 256+ occupy different LFSR state regions —
the only discontinuity here that exists independently of anything I chose. Effect −0.055 below
256 versus −0.049 at or above, **p=0.92**. It is flat on the *outcome* side, and per the
three-way split above it is flat on the *input* side too (p=0.44 on switch rate). Seed 256 is
not a regime boundary in either sense.

**5. Nothing predicts the per-seed effect.** One of ten features reaches p<0.05
(`virus_colour_imbalance`, r = −0.104, p = 0.042) against a chance expectation of 0.5 — and at
ten tests, at least one hit at p<0.05 happens about 40% of the time by luck. No mechanism.

**Verdict: fluke, and the practical consequence is that nobody needs to stratify.** Contiguous
seed ranges are interchangeable in this substrate as far as this data can tell, which is the
answer that costs the project the least. Two caveats I would keep: extending seed coverage is
still good practice for reasons that have nothing to do with this (the co-sim's 135–234
extension remains worth running as a genuine out-of-sample check, on a different rig and
different firmware, and I would rather it ran than not); and this is one substrate at one
level, so it is evidence about L11 bursty seeds, not a general licence.

---

## The two gates that self-consistency cannot provide

Added after the co-sim found a pill-colour bug that was invisible to **every** structural gate
it had — its agreement gate fed two binaries the same wrong input, and its corpus generator
shared an encoder with its game loop, so a systematic input error cancelled out of both sides.
The ten gates in the next section all prove *internal* consistency. These two ask whether this
rig agrees with the world outside it. Both pass; `gates.py` re-runs them.

**Colour convention, checked empirically at every boundary** (not by reading the code):

| boundary | observed values |
|---|---|
| `NesPillSource` capsule colours | 1, 2, 3 |
| board colour plane (0 = EMPTY) | 0, 1, 2, 3 |
| `tuck_enum` placement colours | 1, 2, 3 |
| colours written by the tuck path | 1, 2, 3 |

**This rig was never exposed to the co-sim's failure mode, for a structural reason worth
stating.** Its arms never talk to a copro mailbox — pill colours go faithful sim → `tuck_enum`
→ fast-sim eval and back, entirely in the sim's native 1..3 space — so there is no 0-based
boundary for them to cross. The only place the project's 0-based encoding is read at all is
`calibrate_theta.py` / `export_decisions.py`, reading the co-sim's hostdata; that decode is
checked by producing **48/48 viruses on every L11 board**, which is the level's true starting
count and would not survive an off-by-one.

And the failure would be **loud here, not silent**. The co-sim's bug hid because 1..3 written
into a 2-bit 0..2 field still looks like a valid colour. The reverse cannot hide: 0 is EMPTY in
the faithful sim's plane, so a 0-based board loses every cell of its first colour. Measured on
a real board: **16 of 48 occupied cells vanish (33%)**. Demonstrated rather than asserted, in
`gates._selftest_zero_based_board_is_loud`.

**Outcome plausibility, anchored to a known real rate.** The shipped champion has 0 failures in
1,474 clean L11 games, so this rig's clean champion arm must clear essentially everything or
nothing computed from it means anything. Measured: **99.8% (399/400), floor 97% — PASS.** The
gate is deliberately set on the arm that is supposed to be *normal*; putting a floor on arms
B/C/D would be putting a floor on the finding rather than on the rig.

---

## Validation

Every gate below targets a specific way this rig could be silently wrong.

| gate | result |
|---|---|
| **arm A is game-for-game identical to the committed `base32` arm** | 24/24 seeds, 0 differing |
| **`_place_cells` (tuck mode) ≡ `env.step` (drop mode)** — else arm D plays a different game | 1,992 placements / 25 full games, 0 mismatches |
| resting model vs `fast_sim_x._resting`, the engine that places the pills | 10,766 placements, 0 mismatches |
| tuck_enum `(variant, col)` addresses the same 32-action slot `_expand_core` does | 1,072 straight drops, 0 mismatches |
| tier-3 drop-degradation never lands deeper than the tuck it replaces | 17 tuck picks, 0 violations |
| colour order survives the drop-degradation (so arms differ only in depth) | 304 placements, 0 mismatches |
| a coherent v1 execution never lands shallower than the drop it replaces | 2,394 executions, 0 violations |
| cached `firmware_tier_of` ≡ uncached | 672 candidates, 0 disagreements |
| `choose_with_base` pick ≡ `reach_root.choose_reach_tier` pick | 140 real L11 decisions, 0 disagreements |
| divergence-rig fork lockstep / fork independence | 40 steps bit-identical; per-fork capsule cursors |

The `_place_cells ≡ env.step` gate failed 21/480 on its first run. All 21 were terminal
placements, where `env.step` legitimately stops without advancing the capsule while
`_place_cells` draws unconditionally — a bug in the test, not the rig, since `play()` breaks
out of the game on exactly those conditions. Recorded because "the gate failed and I decided
it didn't count" is the kind of claim that deserves its reasoning in writing.

### Cross-rig validation against real RTL, at zero RTL cost

Replaying the co-sim farm's own `decide_compare_l11_20.json` (fw `e970e9ab`, 20 real L11
boards): this rig's v1 descriptor `(TUCK_COL, TUCK_ROW)` matches what the verilated firmware
actually published on **20 of 20 boards**, 7/20 published on both sides. The v1 arm is driving
the real descriptors, not a lookalike.

Geometry agrees independently too: the co-sim's divergent tier-3 picks are 8/9 and 14/16
horizontal; this rig's winning tucks are 401/492 (81%) horizontal.

---

## Firmware findings, independent of any run

1. **The tier-3 tuck gate is θ=150, not 250.** `fpga/copro/tuck_v3.py:79` is
   `THETA = int(os.environ.get("DRCOPRO_TUCKV3_THETA", "150"))` and `build_copro_d3.py:101`
   calls the v3 path the "theta=150 gate". `reach_root.THETA_FULL = 250` carries a comment
   claiming 250 is "the tuck_v3 ship config's theta", and **every offline tier sweep to date**
   (`run_tier_sweep.py`, `firmware_tier3_ab.py`) inherited that 250 — a *tighter* gate than the
   silicon's. This rig runs 150.

2. **The same numeric θ is not the same gate on both sides.** `tuck_v3.py:70-72` records 4.38
   fires/game in firmware against 2.80 offline at the same θ=150. On the shared 20-board corpus
   this rig has a winning tuck on only 20% of decisions even at θ=0 — take any tuck that beats
   the best base at all — against an RTL descriptor-publish rate of 45%. A θ constant copied
   between the two eval chains does not copy the behaviour.

3. **The co-sim farm's 2×2 is running bursty v1, the pool-contaminated fit**
   (`run_farm.py:74`), where 33 of 61 volleys were the AI copro's own sending events. This rig
   runs v1.1. Flagged to that agent. Paired deltas within a rig stay valid either way, but the
   two rigs' absolute bad-end and dies-ahead rates are not comparable.

---

## What this rig cannot settle

Every number here is a **fast-sim** number. `fast_rtl_x.decide_ship_d3` agrees with the real
RTL on 38% of full (col, orient) base-search moves (py65 manages 13.3%). For an A-vs-B ranking
under one simulator most of that error cancels, which is the whole argument for having a fast
tier — but it is not a licence to quote arm B's 19.2% as a silicon prediction. The co-sim farm
is the instrument that can.

**One structural confound, found while writing this up, and now controlled — CLOSED.**
Arms B and D take their base candidates from `reach_root.choose_reach_tier`'s
*reachability-filtered* pool, while arm A is pure `base32` — and the shipped firmware's own
search is not reachability-filtered. So D − A nominally confounded "the tuck program" with
"the reach32 fix". Two independent checks closed it: on 2,873 real L11 decisions the filter
changes the chosen action **0 times (0.00%)**, and the A′ control arm (400 games, 0 tuck
fires) prices the filter at a **wash** — bad ends 19.2% → 20.5%, McNemar 8 vs 13, p=0.38.
Isolating the tuck program raises its effect from −5.25 to −6.50 points and its significance
from p=0.038 to p=0.0088. The confound existed; it was working slightly *against* the reported
result, not for it.

Three further modelling choices are mine, not measurements, and the co-sim can adjudicate all
three:

- **v1 traverse model.** The capsule is treated as switching columns instantaneously at the
  trigger row. Real DAS takes ~12 hooks per column edge while gravity keeps pulling, so a real
  capsule traverses at progressively deeper rows and is blocked more often — that direction
  makes v1 look *better* here than it is, which strengthens the negative v1 result. The model
  is simultaneously *stricter* than the co-sim's on one axis: it requires a clear traverse path
  at the trigger row, where `descriptor_audit.py` requires only that the pill can enter
  `best_col` there. On the shared 20 boards that is 4/7 coherent here against 6/7 there — a
  definition difference, not a measurement disagreement.
- **The blocked-descriptor convention.** Bracketed rather than chosen — both ends are reported
  above and both are negative for v1. Which end the silicon sits at is a question only the
  co-sim can answer.
- **Vertical trigger-row half.** `legal()` treats the anchor as the bottom cell of a vertical
  capsule; whether `$0386` tracks that half is unresolved. Deliberately the same convention
  `descriptor_audit.py` uses.

---

## The disagreement that mattered — RESOLVED: an RTL firmware defect

**Resolution, landed 2026-08-07 while this was being written (task #85, arm `554a16a5`, knob
`DRCOPRO_TUCKV3_FIXSLOT=1`, commit `67eb37c`).** The co-sim's arm D was not measuring tucks. The
firmware's tuck path uploaded the candidate board to `bcell` with `LEV_WSLOT=0` — which
`LeafEval.sv:47` documents as CUR, *not* a slot — and then issued `LEV_CMD=2` to copy CUR from
dpram region 0, **destroying the board it had just written**. The leaf then scanned
uninitialised memory, `anyvir` stayed 0, and `win <= !anyvir` scored **every candidate a win**.
The base search was immune because it uploads to slot 1 and copies from slot 1.

The fix is deleting one command. With it: candidate maxima fall from 30000/30040/30400 to
1233–5768, "still ≥ WIN" goes 16/16 → 0/16, and publication goes 16/30 → **4/30**.

**Consequences for this document.** Every tier-3 tuck number ever taken on the RTL is void,
including arm D's 0-of-17 collapse. The disagreement below is therefore resolved *in favour of
neither rig* — it was an instrument fault, and the 2×2 must be re-run on the fixed arm before
anything is concluded about tucks on silicon. This rig's numbers are unaffected: its tuck
scoring is `root_search._root_value` in the fast-sim eval, which never touches `LeafEval.sv`.

**The fire-rate gap this section documents was the symptom, and it now has a mechanism.** A leaf
that scores every candidate a win passes every θ gate, which is exactly why the RTL published on
36–38% of decisions where this rig published on 5.7–11.5%. With the defect fixed the RTL
publishes on 13% — in line with this rig. And θ=150 was never the wrong threshold: post-fix,
publication matches the gate's own arithmetic on 16/16 boards. The gate worked as soon as it was
handed real values.

Two things below are worth keeping rather than deleting. First, the **v1-agrees / tier-3-disagrees
control** is what showed the fault was confined to the θ-gated path rather than to boards,
enumeration or counting — that shape is reusable. Second, my own **dose explanation was wrong
and I retracted it before the root cause landed**; the θ sweep that refuted it is recorded below
because a refuted hypothesis with the data that killed it is worth more than a quietly deleted
one.

A **separate, still-open** firmware defect is recorded in the same place: base candidates receive
the EH bonus and tucks do not (+237 mean over 10,800 candidates), making the effective gate ~387
against a nominal 150 — a bias *against* tucks, to be fixed after the slot defect.

### The original disagreement, as measured

The co-sim farm's RTL 2×2 began producing games while this was being written, and on arm D it
**flatly contradicts** this rig. That disagreement turned out to be the most valuable output of
running two methods, so it gets the space it deserves rather than a footnote.

| arm | co-sim (real RTL) | this rig (fast sim) |
|---|---|---|
| **A** s20b × drop | 11/12 clear | 323/400 clear (80.8%) |
| **B** s20t3 × drop | **0/48 clear**, dies at median 45 pills with 38 of 48 viruses left | 77/400 clear (19.2%), dies at median 25 viruses left |
| **D** s20t3 × tuck | **0/17 clear** | 344/400 clear (86.0%) |

Arm B agrees emphatically — both rigs say tier-3 without the executor is a broken build, and
the RTL says it more strongly than this rig did. Arm D is the opposite of agreement.

### It is the θ gate, and the v1 arm proves it

One number explains both rows, and the v1 arm is the control that pins it down. Measured as
**descriptors published per decision**:

| firmware | gated? | co-sim (RTL) | this rig | ratio |
|---|---|---|---|---|
| v1 (`s20b`) | **no** — `tuck_scan.py` publishes the deepest rest unconditionally | 60.5% | 66.8% | 1.1× |
| tier-3 (`s20t3`) | **yes** — θ=150 margin gate | **36–38%** | **5.7–11.5%** | **3–6×** |

The **ungated** rate agrees between the two rigs to within 10%. That is the control: it shows
the two rigs see the same boards, enumerate the same candidates and count the same events. The
**gated** rate differs by 3–6×. The discrepancy is therefore isolated to one thing — how tight
θ=150 is in each rig's eval units — and it is not board distribution, not the enumerator, and
not a counting bug.

This is precisely the hazard `tuck_v3.py:70-72` documents in its own build knob: *"theta=150 is
a LOOSER gate in shipped-eval units than in the offline coef-opt units"* (4.38 fires/game in
firmware against 2.80 offline). The firmware's warning was right, and larger than it knew.

Firmware archaeology confirms the events are the same event, so the rates really are
comparable: in `tuck_v3.py`, `TUCK_COL`/`TUCK_ROW` are written at `tre_pub` only when
`TK2_BKIND` was set, and `TK2_BKIND` is set only inside `tre_commit`, which is reached only
after the θ compare falls through to `tre_gok` (lines 629-661). A published tier-3 descriptor
**is** a tuck that won the gate, and `D_BC`/`D_BO` are overwritten in the same branch. So the
co-sim's 38% is the rate at which the real firmware wins its own gate, and this rig's 5.7% is
the rate at which it wins mine.

### The obvious explanation — dose — is REFUTED by this rig's own θ sweep

The natural reading of the fire-rate gap is a dose-response: tucks help in small doses and are
fatal in large ones, so the RTL's 38% poisons a build that this rig's 5.7% improves. **I
published that explanation, and then tested it, and it is wrong.**

The θ sweep varies this rig's own dose. Arm D against the shipped champion, bursty v1.1, n=400
paired:

| θ | fires / decision | fires / game | clear | bad ends | **D − A** bad-end rate | McNemar |
|---|---|---|---|---|---|---|
| 250 | 3.0% | 3.98 | 86.2% | 55/400 (13.8%) | −5.50 pts [−10.5, −0.5] | 64 vs 42, p=0.041 |
| 150 | 5.7% | 7.24 | 86.0% | 56/400 (14.0%) | −5.25 pts [−10.0, −0.8] | 57 vs 36, p=0.038 |
| **0** | **16.2%** | **20.52** | **89.5%** | **42/400 (10.5%)** | **−8.75 pts [−13.5, −4.3]** | **63 vs 28, p=0.0003** |

Two things follow. First, **the executor's value is θ-robust**: positive and significant at
every dose across a 5.4× range, so the headline does not depend on a lucky constant — that is
the sensitivity check passing. Second, and fatally for the dose hypothesis, **more tucks is
better, not worse.** At 16.2% the program improves on every axis at once — bad ends, stalls
(28 → 14, p=0.038), topouts (49 → 28, p=0.013), and dies-ahead (11.0% → 6.5%, −4.5 points
[−8.25, −0.75], the *only* arm anywhere in this study where dies-ahead moves at all). The curve
is flat-then-rising with no turning point in sight. Nothing in it predicts a collapse at 38%.

So the dose hypothesis does not survive contact with the data, and the disagreement with the
co-sim on arm D **remains open**. What is left:

- the RTL may be *selecting* materially worse tucks than this rig does, rather than more of
  them — a quality difference, not a quantity one;
- the co-sim's tuck-execution path may have a defect that its `n_illegal` / `n_incoherent`
  counters do not catch;
- or this rig's tuck execution is too generous in a way its own gates did not catch, though
  `_place_cells ≡ env.step` (1,992 placements, 0 mismatches) rules out the most likely form of
  that.

**The discriminating experiment is cheap and belongs on the co-sim**, and its rationale is now
the opposite of what I first suggested: build one arm with `DRCOPRO_TUCKV3_THETA` raised so the
RTL fires on ~6–16% of decisions and run it in tuck mode. If arm D recovers, dose matters in
their rig even though it does not in mine, and the gate is the answer after all. **If arm D
fails at every dose, it is not dose at all** — it is selection quality or a defect, and the
next step is a direct comparison of *which* placement each rig picks on identical boards, which
their `decide_compare` harness can already produce.

What survives from this section unchanged: **arm B agrees across both rigs and both are
catastrophic**, and the fire-rate gap itself is real and worth fixing regardless of what it
does or does not explain.

---

## Reconciliation with the co-sim farm

**Most of what this section used to contain has been withdrawn by the co-sim, and I have
removed it rather than downgraded it.** Two defects landed on 2026-08-07: a 1-based/0-based
pill-colour bug at the copro mailbox, and a tuck-leaf defect that scored every candidate a WIN.
Between them they void that rig's v1 and tier-3 descriptor tables, its placement-divergence
rate, and every tier-3 tuck measurement it had produced. Treat their **direction as unknown**,
not merely imprecise — which is why no number of theirs is quoted as corroboration below.

What survives, because no simulation is involved in it:

| still solid | source |
|---|---|
| `DRTUCK` never enabled on any of 67 cart manifests; the deployed cart has no tuck executor | manifests |
| `tuck_v3.py:644-645` overwrites `best_col`/`best_orient` when a tuck wins | driver source |
| v1 has **no value gate at all** — it publishes the deepest rest unconditionally and never writes `D_BC`/`D_BO` | `tuck_scan.py`, grepped |
| tier-3 θ is 150, applied as `TK2_BBV + THETA` against a reference captured once before any candidate | `tuck_v3.py:79, 629-630` |
| the champion's 0 failures in 1,474 clean games | prior census |
| bursty v1.1 is the honest pressure model | `BURSTY_V1_RESULTS.md` §5 |

And one measurement of mine that survives the colour bug **by construction**: the
board-for-board match of my v1 descriptors against the RTL's published `(TUCK_COL, TUCK_ROW)`,
20/20. `tuck_scan` is purely geometric — it reads occupancy (`!= 0xFF`) and never touches pill
colour — so a pill-colour bug cannot move it. What that bug *does* invalidate is my v1
*coherence* figure computed against the RTL's chosen `(col, o4)`, since the RTL's choice does
depend on pill colours. **That 4/7 is withdrawn**, along with the co-sim's 6/7 it was compared
against.

**Arm B: the mechanism is confirmed on both rigs, the magnitude is not.** I predicted the RTL
would see bad ends go from 19% to 81% and that n=20 would suffice; it reported 0/48 clear at
n=12 paired, McNemar p=0.0010. I first read that as a clean cross-method confirmation and
**that was wrong** — the co-sim subsequently established that arm B is contaminated by the same
tuck-leaf defect. Drop mode ignores the *descriptor*, but `tre_commit` writes
`TP_TARGET → D_BC` regardless, so spuriously-won tucks moved arm B's published column too. Its
arm B is the degradation mechanism running at a defect-inflated fire rate (53% of decisions
against the post-fix 13%), which is why it reads even more catastrophic than mine.

So the correct statement is: **both rigs agree the mechanism destroys the champion; only this
rig has a magnitude for it.**

**That magnitude is now testable, and here is the prediction, recorded before the run that
checks it.** Post-fix the RTL publishes on **13%** of decisions and this rig fires on **11.5%**
— within two points, where before the fix it was 53% against 11.5% and no transfer could be
expected. Matched dose is the condition under which a magnitude should carry across two
simulators, so:

> **Prediction.** A post-fix RTL arm B, on seeds this rig also covers, should land near
> **80% bad ends** (this rig: 80.8%) — emphatically not near its pre-fix 100%, and emphatically
> not near arm A's ~17%. If it comes back at ~100%, the dose match is not sufficient and
> something else in arm B differs between the rigs. If it comes back near arm A, my arm B is
> wrong and the entire drop-degradation model with it.

Stating it this way is the point: "the rigs now agree on dose" is a hope, and "80% ± the width
of a 12-seed interval, or the model is wrong" is a test. The same applies to arm D, whose
prediction is recorded in [what is left](#what-is-left).

---

## Divergence horizon: does a fired tuck matter, or wash out?

The measurement neither the co-sim nor the offline mirror rig has. At the first pill where drop
and tuck modes would execute differently, the game forks from one identical board into a
reference branch, a branch that executes the tuck, and a **matched control** that takes the
second-best base drop instead. The control is the point: without it, "the boards were still
different 40 pills later" is uninterpretable, because any perturbation might persist that long.

### The clean answer: one tuck is worth about +7.7 points of clear rate

From `divergence_single.py`, where **all three branches continue in drop mode** after the fork,
so the continuation policy cancels and each delta is exactly one placement. Clean stream,
n=300, 298 forked:

| branch | clear rate | vs reference |
|---|---|---|
| **R** no perturbation | 37.2% | — |
| **T1** one tuck executed | **45.0%** | **+7.7 pts [+0.3, +15.1]**, 74 vs 51, p=0.049 |
| **C** one second-best base drop | 39.3% | +2.0 pts [−5.0, +9.1], 59 vs 53, p=0.64 — wash |

A single executed tuck is worth about eight points of clear rate — real but marginal
(p=0.049) — where a matched perturbation of comparable size is worth nothing. The direct
tuck-vs-control contrast, **+5.7 pts [−1.7, +13.4], p=0.16**, does *not* reach significance at
this n, and that should be stated rather than glossed: the evidence that a tuck beats an
arbitrary perturbation is suggestive, not established.

### A defect in the first version of this measurement, and what it cost

**The first divergence run reported T − R = +23.5 points and C − R = −20.5 points. Both were
artifacts and both are withdrawn.** `divergence.py`'s branch loop stopped as soon as the
*reference* branch finished, leaving the other branches mid-game with no result — which the
scorer then counted as "did not clear". Measured on that run: 117 of 298 tuck branches and 136
of 298 control branches were truncated, and every tuck branch that *did* get a result had
cleared (181 clear, 0 topout, 0 stall) — because the only way to get a result at all was to
finish before the reference. That is enough selection bias to manufacture the entire effect,
and it did.

It was caught by disagreement between two rigs that should have agreed: `divergence_single.py`
runs the identical fork protocol with the identical R and C branches, and measured C − R at
+2.0 where the truncated run said −20.5. Same seeds, same branches, same continuation — so one
of them had to be wrong. The loop is fixed (every branch now runs to its own end, and
reconvergence is only scored while both games are live), the superseded outputs are kept under
`results/superseded/` rather than deleted, and the re-run is in progress. The lesson is the
generic one: **a paired rig that silently scores an unfinished game as a loss will invent
whatever effect makes its reference finish first.**

### Nothing ever washes out — for anything

Re-measured with the loop fixed (0 unfinished branches of 298, against 253 before), clean
stream, n=300:

| branch | never reconverges, clean | never reconverges, bursty |
|---|---|---|
| **T** tuck executed | **292/298 (98.0%)** | **293/299 (98.0%)** |
| **C** second-best base drop | 275/298 (92.3%) | 277/299 (92.6%) |

When reconvergence does happen it takes a median of 1–2 pills — the rare case where the
perturbed placement was cleared away immediately. Every figure is **identical to the pre-fix
run and identical across the two pressure regimes**, which is the expected result on both
counts: reconvergence was scored only while both games were live, so it was the one statistic
truncation could not reach, and it is a property of the game rather than of the pressure model.
Exact board equality is essentially never restored after *any* perturbation.

**This inverts the premise of the question.** The worry was that a maneuver might improve the
board for three pills and then wash out, making per-placement statistics overstate its worth.
In this game nothing washes out — placements are permanent — so that particular discount does
not apply. The corollary is the one to carry forward: because *nothing* washes out, persistence
is not evidence of value either, and any "the effect was still visible N pills later" claim
measures the game's chaos rather than the maneuver.

The fixed run also cross-validates the two rigs. Both now put the reference branch at **37.2%**
and the control at **39.3%** — identical to three significant figures, on the same seeds
through independently written game loops.

### It does not decay — it compounds

Board equality is a blunt instrument, so the gap is also tracked continuously. Mean signed
difference from the reference, by pills elapsed since the divergence (clean stream, negative =
better than the reference):

| pills since divergence | viruses, tuck | viruses, control | max height, tuck | max height, control | observations |
|---|---|---|---|---|---|
| 0–2 | −1.41 | −0.43 | −0.69 | −0.47 | 1,740 |
| 3–5 | −2.50 | −0.65 | −1.00 | −0.47 | 1,678 |
| 6–10 | −3.74 | −0.73 | −1.24 | −0.39 | 2,697 |
| 11–20 | −5.80 | −0.54 | −1.73 | −0.16 | 5,046 |
| 21–60 | **−9.74** | −1.21 | **−3.44** | −0.23 | 14,973 |

The control's advantage stays flat near half a virus for the whole game — one perturbation, one
bounded consequence. The tuck branch's advantage grows monotonically to nearly ten viruses and
three and a half rows. **Read with the caveat that the tuck branch keeps firing tucks** (it
continues in tuck mode, where the control does not), so this is the compounding of a policy
rather than the decay of a single maneuver — which is precisely why the single-maneuver number
above, +7.7 points from one tuck, is the one to quote for one tuck.

---

## Still running

- **θ sweep — now the key experiment.** It was queued as a robustness check; the disagreement
  with the co-sim promoted it to a direct test of the dose-response hypothesis *within this
  rig*. θ=0 / 150 / 250 fire on roughly 20% / 10% / 5% of decisions, so the arms bracket this
  rig's own dose by 4×. If tucks help *less* at θ=0 than at θ=250, the "helps at low dose,
  fatal at high dose" story is supported from a second direction; if they help *more*, the
  story is wrong and the disagreement with the co-sim needs a different explanation. Either
  answer is decisive, which is why it is running ahead of the item below.
- **Divergence-horizon re-run** with the truncation defect fixed, clean and bursty, n=300 each.
  Only the reconvergence statistic is still outstanding; the directional question it was meant
  to answer has already been answered correctly by `divergence_single.py`.

Completed since the first revision: the v1 hazard bracket (both ends negative), the
failure-mode decomposition (which corrected this document's interpretation of *why* D − A
works), the A′ control arms (which closed the reachability-filter confound and slightly
strengthened the headline), the full θ dose-response curve (which refuted my own explanation of
the co-sim disagreement), and the single-maneuver isolation (which caught a truncation defect
in the first divergence rig and withdrew two of its numbers).

## Reproducing

    python selftest_2x2.py                 # every gate in the validation table
    python validate_v1_vs_rtl.py           # descriptor match against the co-sim's RTL output
    python calibrate_theta.py              # publish-rate calibration
    bash   run_all.sh                      # the 2x2 runs (N=400 W=6 by default)
    python divergence.py --seeds 300 --workers 6 --pressure clean
    python divergence_single.py --seeds 300 --workers 6 --pressure clean
    python report.py                       # every table above, from results/*.json
