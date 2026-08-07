# What is the tuck executor worth? An independent fast-sim answer

Corroboration by a different method for the co-sim farm's RTL 2×2. Same four arms, different
simulator, different failure modes, n=400 paired seeds per arm instead of tens.

**Status:** the two primary runs (bursty pressure, clean stream) are complete. The v1-hazard
bracket, the divergence-horizon measurement and the θ sensitivity sweep are still running and
are marked below; this document will be updated in place as they land.

---

## The number

**Rebuilding the cart with the executor enabled AND tier-3 firmware takes the shipped
champion's bad-end rate under bursty human pressure from 19.2% to 14.0% — a paired difference
of −5.25 points, 95% CI [−10.0, −0.75], McNemar rescued=57 harmed=36, p=0.0375, n=400 —
and clears the level 26.0 pills faster, CI [−32.7, −19.3].**

That is the D − A comparison: the full program versus what is on the cart today. It is the
number a rebuild decision turns on, so it leads.

**The survival half of that is entirely stalls, not topouts** (28 → 12, p=0.014; topouts
49 → 44, p=0.65 — a wash), which is the signature of digging buried viruses out rather than of
finishing before the garbage arrives. See the decomposition below; it is the strongest single
piece of evidence here that the executor does what a tuck is *for*.

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

**Dies-ahead moved on no arm.** Every dies-ahead CI includes zero (D − A: −0.003
[−0.048, +0.040]). The executor changes whether games are lost, not the signature of how they
are lost. Anyone citing this work for a dies-ahead claim is citing it wrongly.

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

The co-sim farm's `descriptor_audit.py`, running the real RTL over a 50-board corpus, found
**1 of 26 (4%)** v1 descriptors land deeper. This rig, on 43,669 descriptors from whole games
in a different simulator, finds **3.8%**. Two rigs, two methods, three orders of magnitude
apart in sample size, same answer.

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

**One structural confound, found while writing this up, measured, and being controlled for.**
Arms B and D take their base candidates from `reach_root.choose_reach_tier`'s
*reachability-filtered* pool, while arm A is pure `base32` — and the shipped firmware's own
search is not reachability-filtered. So D − A nominally confounds "the tuck program" with "the
reach32 fix". Measured directly: on 2,873 real L11 decisions the filter changes the chosen
action **0 times (0.00%)**, so on the board distribution the champion actually visits the
confound is empty. That is not a proof for arm B, which dies on tall congested boards where a
column walled to row 0 is far more likely, and where `REACH_ROOT_VERDICT`'s M3CASE analysis
found the filter *does* bite. A control arm — the tier-3 decision path with θ set so high no
tuck can pass the gate, i.e. reach-filtered base32 with no tucks — is running to settle
D − A' (the tuck program alone) and A' − A (the filter alone).

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

## Reconciliation with the co-sim farm

Their RTL 2×2 had not accumulated meaningful n when this was written (their throughput is
~8.5 s per decision against ~110 decisions per game), so the 2×2-to-2×2 comparison is still
open. Where the two rigs *can* already be compared, they agree:

| statistic | co-sim (real RTL) | this rig (fast sim) |
|---|---|---|
| v1 descriptors published, 20-board corpus | 7/20 | 7/20, and identical board-for-board |
| v1 descriptors landing deeper | 1/26 (4%) | 1,663/43,669 (3.8%) |
| tier-3 descriptor coherence | 100% (25/25, 9/9, 16/16) | 100% (2,896/2,896) |
| tier-3 divergent picks horizontal | 8/9, 14/16 | 401/492 (81%) |
| tier-3 depth gained | mean 3.4–3.5 rows | median 5 rows (winning tucks only) |

The depth-gain difference is a denominator difference, not a disagreement: they average over
all *published* descriptors, this rig counts only the ones the search actually *picks*, and the
search picks the deeper ones.

**A cheap falsification test has been handed to that agent:** if arm B really drives bad ends
from 19% to 81%, their RTL will see it at n=20 per arm — a 4× effect needs no large sample.
Confirming it settles the single most actionable finding here; failing to see it means this
rig's drop-degradation model is wrong, and that would be the most important result of the day.

---

## Still running

- **Divergence horizon** (`divergence.py`) — at the first pill where drop and tuck modes
  diverge, the game forks three ways from one board: reference, tuck executed, and a matched
  control that takes the second-best base drop instead. Measures how many pills until the
  boards reconverge, how often the eventual outcome changes, and whether either exceeds the
  control. A 12-seed smoke run had tucks never reconverging (11/11) against the control's 73%,
  with outcomes changing 36% vs 18% — too small to call, hence n=300.
- **Control arms A′** — the tier-3 decision path with θ so high no tuck can pass, isolating
  D − A′ (the tuck program alone) from A′ − A (the reachability filter alone).
- **θ sensitivity** — 0 / 150 / 250 on the headline pair.

Completed since the first revision: the v1 hazard bracket (both ends negative, above) and the
failure-mode decomposition (which corrected this document's interpretation of *why* D − A
works).

## Reproducing

    python selftest_2x2.py                 # every gate in the validation table
    python validate_v1_vs_rtl.py           # descriptor match against the co-sim's RTL output
    python calibrate_theta.py              # publish-rate calibration
    bash   run_all.sh                      # the 2x2 runs (N=400 W=6 by default)
    python divergence.py --seeds 300 --workers 6 --pressure clean
    python report.py                       # every table above, from results/*.json
