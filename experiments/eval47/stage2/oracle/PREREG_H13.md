# PRE-REGISTRATION ADDENDUM — H13 GATE-V2 (task #110)

**Status: DRAFT, frozen before any H13 outcome data exists.** Addendum to
`PREREG_ORACLE.md`; everything not restated here is inherited from the oracle
prereg and its H12 endpoint addendum unchanged.

Proof of timing, per [[dr-mario-measurement-rules]] #28 (a pre-registration
nobody can date is just an assertion) — recorded in the commit that adds this
file, and verifiable from it:

- no `out/h13_*` directory exists on disk;
- `out/census_70000.jsonl` exists but is a GATE-RATE census only: it contains
  no arm outcome, no flip, and no endpoint quantity. Its columns are board
  geometry and the champion's own tie indicator. It cannot be read as a result
  for either endpoint below.

---

## 0. THE POSTURE — THIS LANE IS PRICING GATE-V2, NOT ADVOCATING IT

The H12 gate is `d_spawn_h >= 12 OR viruses <= 8` with
`d_spawn_h = max(H[3], H[4])` — the spawn-path columns only. Both photographed
died-ahead deaths in the owner's 2026-08-15 soak were EDGE towers (cols 1-2
while ahead 41-15; col 6 while ahead 31-41) with LOW centre columns, so the
gate was closed throughout the fatal build
([[dr-mario-gate-center-blind]]).

**The counter-evidence is registered here, first, on purpose.** The third
exhibit from the same session — the 13:21 col-2 "fatal tower" — was priced by
the forced-move harness against all 15 legal alternatives under solo and two
drip regimes and came back the **uniquely best move on the board**: 0% topout
in every regime where alternatives top out 6.2-75%, most viruses cleared, and
the LOWEST resulting spawn height ([[dr-mario-death1321-col2-vindicated]]).
That is the fourth time a visually alarming champion habit has priced as
neutral-or-good. A wider gate would have been **firing on a good move there**.

Therefore the registered prior for this lane is: **gate-v2 is at least as
likely to add DOSE without adding JUDGMENT.** Every extra trigger costs rollout
compute and puts a good tie-keep at risk of being overturned. **A clean NO-GO
is a fully successful outcome and must be reported in the same tone as a GO.**

## 1. THE CHANGE, AND WHAT IS HELD FIXED

```
gate-v1 (H12, sealed):   d_spawn_h >= 12  OR  viruses <= 8
gate-v2 (H13):           max(H)    >= T   OR  d_spawn_h >= 12  OR  viruses <= 8
```

`T` is the any-column height threshold. **The v1 clauses are RETAINED**, so
gate-v2 is a strict SUPERSET of gate-v1 at every `T`: the dose is monotone
non-increasing in `T`, and no H12 trigger is lost. This is a design choice, not
an accident — a non-superset gate would confound "wider" with "different" and
make the dose ratio uninterpretable.

**Held fixed at H12's sealed values, and not to be touched by this lane:** the
exact top-2 champion-value tie trigger; top-k = 4; horizon = 15; five sampled
futures; `future_mode='dist'` (the on-cart observation set — the arm never sees
the true capsule stream beyond cur+next, per
[[dr-mario-flip-fairness-screen]] rule 3); `theta_margin = 0.5` (accepted only
if the winner's fork progress SUM beats the champion action's by >= 3 of 5);
and the shuffled-null thinning machinery.

**Registered variants:** `T = 13` PRIMARY (one row of headroom above v1's
spawn threshold), `T = 12` SECONDARY (v1's own threshold applied to every
column). No other `T` may be promoted to primary after seeing data; the census
in section 5 sweeps `T = 10..15` for DOSE only, and dose is not an endpoint.

## 2. ENDPOINTS AND THE VERDICT RULE

Inherited from the oracle prereg verbatim:

- **PRIMARY: dies-ahead rate** (topout with `viruses_left <=` the rig's
  dies-ahead threshold), paired, McNemar over discordant seeds.
- **CO-PRIMARY: clear rate**, paired, McNemar.
- Stalls scored at parity with topouts. Tempo (pills) reported both ways,
  never as a verdict quantity.
- Seed-clustered CIs on every reported delta.

**The comparison is H13 vs H12, not H13 vs champion.** H12 is the certified
incumbent as of 2026-08-17 ([[dr-mario-h12-endpoint-verdict]]). An H13-vs-
champion delta would re-measure H12's own established win and is not the
question; it may be reported as a secondary descriptive, clearly labelled.

**GO requires ALL of:** the true arm beats H12 on the primary at the registered
alpha; the dose-matched shuffled mutant returns NO_GO at a dose ratio inside
[0.90, 1.10]; and the co-primary does not move against the arm. Any one of
these failing is a NO-GO. **A dose ratio outside the band is a VOID, not a
NO-GO** — the same outcome that cost the H12 lane a full re-run.

## 3. THE DOSE ANCHOR — THE H12 LESSON, ENCODED

H12 v1 was **VOID by 0.002** because its null dose was anchored on a 60-seed
reserved calibration window (42000-42059) whose sampling noise exceeded the
+-10% gate: keep 0.5806 gave a realized mutant RATE ratio of 0.898.

Two corrections are registered here, both binding:

1. **ANCHOR ON FULL-N REALIZED FLIP RATES, NOT COUNTS, AND NOT ON A
   CALIBRATION WINDOW.** `keep_v2 = keep_v1 * true_rate / mutant_rate`,
   evaluated over the whole phase-1 block. Count-matching is WRONG and was
   measured to be wrong: H12's mutant kept-COUNT ratio was 1.02 while its
   per-ply RATE ratio was 0.898, because mutant games run ~19 pills longer and
   dilute the per-ply rate. The anchor computation reads ONLY whitelisted flip
   counters — never an outcome — so it stays endpoint-blind.
2. **NO SMALL RESERVED CALIBRATION WINDOW IS USED AT ALL.** If phase 1's
   full-N anchor cannot be computed for any reason, the lane VOIDs rather than
   falling back to a windowed estimate.

## 4. SAMPLE SIZE AND SEEDS

**N = 9,000 paired seeds** for the endpoint, per the standing task #106
constraint (floor 7,826; register 9,000). Paired: one work item is one seed and
BOTH arms, so an early stop yields a balanced prefix.

Registered seed blocks for this lane, chosen disjoint from every block in use:

| block | purpose |
|---|---|
| 41000-41099 | H13 pre-launch gates (shared with the H12 gate seeds, deliberately — these are gate seeds, never endpoint seeds) |
| **70000-70399** | gate-rate census (dose only, no outcomes read) |
| **71000-71999** | PILOT (underpowered by construction; see section 6) |
| **72000-80999** | H13 ENDPOINT, 9,000 paired seeds — reserved, NOT YET RUN |

Disjoint from: label corpus 2-12001; stage-2 rollout 20000-29999; oracle
30000-36000; H12 endpoint **41100-50099**; H12 calibration **42000-42059**;
distill lanes **60000-60499 / 61000-61999 / 62000-62999**. Seed 1 (the LFSR
absorbing state, [[dr-mario-degenerate-seed-1]]) is excluded and lies outside
every block above.

**SEED-SPACE NOTE, stated to prevent a known trap rather than to act on it.**
The NES pill-seed space is **32,767** distinct streams: the seed's low bit is
dead, so `2k` and `2k+1` draw the identical capsule stream
([[dr-mario-seed-space-is-32767]]). A contiguous block therefore contains ~50%
aliased PILL streams. **This lane does NOT halve N and does NOT deduplicate.**
The eval47 rig draws viruses from `numpy.default_rng(seed)`, so a twin pair
shares pills but plays a **different board**, and the boards dominate the
variance; the measured twin-pair correlation of paired differences is
r = -0.077 (design effect 0.92, i.e. effective n no worse than nominal).
Halving a numpy-seeded sweep on the strength of the 32,767 result has already
cost this project 40 minutes of a census running at half coverage. The 32,767
figure binds COVERAGE claims ("N% of the seed space"), which this lane makes
none of. H12's own endpoint used a contiguous 9,000 block; this matches it.

## 5. GATES THAT MUST PASS, EACH WITH THE MUTANT THAT MUST BREAK IT

`gate_h13.py`. Project standard: a gate must be shown to FAIL on wrong inputs,
not merely to pass on right ones ([[dr-mario-gate-standard-killed-mutants]]).

- **G0 EXTRACTION NO-OP.** The gate predicate was extracted into a `self._gate`
  hook on `H12Arm` so that v1 and v2 share `choose` verbatim instead of living
  in two transcribed copies (rule 3). G0 requires H12Arm-with-hook to reproduce
  `h12_arm_sealed.py` — a pristine `git show 2b96cd3` copy, loaded as a
  separate module so the reference shares no code with the refactor —
  **action-sequence identically** on 20 seeds.
- **G1 V1 IDENTITY.** `H13Arm(gate_mode='v1')` reproduces sealed H12
  action-for-action on 20 seeds. This is the "gate-v2 off reproduces the sealed
  arm" requirement, at the action-sequence standard the distill lane used.
- **G2 NOT INERT.** Gate-v2 must measurably BIND on real boards: it must open
  on plies gate-v1 leaves closed, at a rate materially above zero. An inert
  widening passes every equality test trivially and would price as free
  ([[dr-mario-measurement-rules]] #26 — a null A/B is uninformative unless the
  treatment is proven active).
- **G3 MUTANT KILL.** Four wrong gates must each DIVERGE from gate-v2 in action
  sequence: inverted; threshold off-by-4 low; off-by-4 high; always-fires. Each
  mutant's PREDICATE is first shown to differ from gate-v2's on real plies, so
  a survivor is a real failure and not an unkillable equivalent mutant.
- **G4 DETERMINISM.** Same seed twice, identical result dict.

**What these gates do NOT cover, stated next to their result** (rule 24 —
partial coverage reads as coverage): they exercise the gate predicate and the
action sequence it produces. They say nothing about whether gate-v2's extra
triggers IMPROVE play — that is the endpoint's job — and nothing about the
shuffled-null thinning, inherited unchanged from H12.

## 6. DOSE, MEASURED CHEAPLY AND BEFORE ANY ENDPOINT SPEND

The fire rate factorises ([[dr-mario-measurement-rules]] #5 corollary):

```
fire rate = gate rate  x  P(exact top-2 tie | gated)  x  P(margin passes | tie)
```

The first two factors are pure functions of the board the CHAMPION reaches and
of the champion's own values, both already computed by a const arm. So they can
be measured with **no forks at all**, at roughly 1/40th the cost of a paired
game, by `run_census.py` over seeds 70000-70399 sweeping `T = 10..15`.

**Registered red flag, before the number exists:** if gate-v2's trigger rate
(gate AND tie) exceeds **2x** gate-v1's at the primary `T = 13`, that is
reported as a red flag with its theta re-anchoring implications, because
theta = 0.5 was calibrated against v1's trigger population and a materially
different population invalidates that calibration rather than merely scaling
it. It does not by itself veto the lane, but it moves the recommendation toward
NO-GO-on-spending and toward re-calibrating theta first.

**SCOPE, carried with the number:** the census plays the CHAMPION's trajectory.
Under a real H13 arm the flips themselves change later boards, so the census
measures the dose at the FIRST divergence, not a whole-game dose. It bounds the
trigger-rate ratio; it does not replace the paired arm. The census arm's action
sequence is compared against `OracleArm(const)` on every seed and the result is
stored per row (`champ_identical`), so "the census plays the champion" is an
assertion in the instrument, not an assumption in the caller.

## 7. THE PILOT IS NOT AN ENDPOINT

Seeds 71000-71999, paired H12 vs H13. **Underpowered by construction** and
labelled PILOT everywhere it is reported. It exists to (a) confirm the arm runs
and banks, (b) give a cost-per-pair for the endpoint quote, and (c) surface a
gross defect early. Registered before the data exists:

- **No verdict language may be attached to it**, in either direction.
- **No endpoint may be promoted or demoted on the basis of which one moves
  first in the pilot.** The first endpoint to cross significance is the one
  most likely to be inflated ([[dr-mario-measurement-rules]] #23).
- A pilot direction that agrees with the center-blind hypothesis is the one to
  withhold hardest (#19: an underpowered statistic that agrees with you is the
  one most likely to travel without its caveat).
- Discordant PAIR COUNTS are reported alongside every delta. Below the ~2-3%
  decisions-changed interpretability floor, the correct report is "not testable
  at this dose", never "null" (#5).

## 8. WHAT THIS LANE CANNOT ANSWER

- It cannot tell whether gate-v2 would have saved the two photographed EDGE
  deaths. Those were VS games against a live opponent; this rig is the lulu
  pressure model. The exhibits remain UNPRICED and this lane does not price
  them.
- It cannot separate "the gate now sees the right plies" from "the gate now
  sees more plies". A wider gate that helps could be helping only through extra
  dose. **The registered discriminator is the `T` contrast**: if `T = 12` and
  `T = 13` help in proportion to their dose, the mechanism is dose, not sight.
- It says nothing about silicon implementability. H12 itself is a RESEARCH
  champion; root rollouts are copro/driver work not shipped by any verdict here.

## 9. AMENDMENT (2026-08-18, after the DOSE census, before any endpoint spend)
### THE ENDPOINT IS THE WRONG NEXT PURCHASE — REGISTER THE FLIP SCREEN FIRST

The fork-free census (400 seeds, 60,686 champion plies) measured two things
that together change what should be bought next. Both are dose quantities, not
endpoint quantities, so registering this amendment stays endpoint-blind.

**(a) The extra dose is small: trigger ratio 1.129 [1.109, 1.151] at T=13.**

**(b) But gate-v1 is overwhelmingly an ENDGAME gate, and the widening is not.**

```
                                   % of plies   % of v1 opens
  gate-v1 open (either clause)        54.61          100.0
    d_spawn_h >= 12 ALONE              5.70           10.4
    viruses <= 8 ALONE                35.61           65.2
    both                              13.29           24.3
  v2-only (T=13, v1 closed)            7.92            —
```

Median context: v1 opens at **3 viruses remaining**; v2-only plies at **15**,
with `max(H)` a median of **7 rows above** the spawn columns.

**So gate-v2 is not a marginal widening. It is a 2.4x expansion of the
HEIGHT-driven sensor** (5.70% -> 13.62% of plies), which reads as a mere +12.9%
on the total only because the endgame clause dwarfs everything else. The extra
triggers are a MID-GAME off-centre-tower population that H12's gate barely
touches — exactly the regime the soak photographs came from.

**⚠ THIS BREAKS THE POWER EXTRAPOLATION IN BOTH DIRECTIONS.** `price_h13.py`
scales H12's published discordance by the extra dose to project ~176
discordant dies-ahead pairs at N=9,000. That projection assumes the extra
flips behave like H12's own. They are drawn from a **different regime**, so it
is not an upper bound and not a lower bound — it is an extrapolation across
exactly the boundary this project has been burned on before
([[dr-mario-measurement-rules]] #20/#24: a mid-game corpus does not certify
near-death behaviour, and the converse holds too). The honest statement is that
**the endpoint's power is unknown, not marginal.**

**REGISTERED CONSEQUENCE — the N=9,000 endpoint is NOT the next purchase.**
Buying it now spends $173-$384 (see section 10) to answer "are the extra flips
good?" through the lossiest possible channel: whole-game outcomes, ~176
discordant pairs. The same question is answerable directly, per flip, for
about two dollars.

**THE FLIP SCREEN (registered here, before it is run):**
1. Run the H13 arm ALONE on ~500 fresh seeds (block 73000-73499, reserved
   here). One arm suffices: at a v2-only trigger H12 does not act, so H12's
   action IS the champion's base action, and both the keep and the flip are
   recoverable from the H13 flip log.
2. Take every accepted flip whose trigger was **v2-only** (`gate_v2 and not
   gate_v1`) — the decisions that distinguish H13 from H12, and the only ones.
3. Screen each with the project-standard **CAPSULE-FAIR refork**
   ([[dr-mario-flip-fairness-screen]]): fork the H12 keep and the H13 flip
   under K=17 UNSEEN capsule streams and compare mean progress. This is
   mandatory project policy for calling any single flip an improvement, and it
   applies a fortiori to the aggregate.
4. Expected volume: 4.07 extra triggers/game x ~10.3% margin-pass = **~0.42
   extra flips/game**, so ~500 seeds yields **~200 screened flips**.

**DECISION RULE, fixed before the data exists:**
- Extra flips price **NEGATIVE** (mean fair gain < 0, CI excluding 0) =>
  gate-v2 is REFUTED. Close #110. Cost of learning this: ~$2.
- Extra flips price **NULL** (CI spans 0, |mean| small) => the widening is
  churn: it adds compute and changes decisions without adding judgment. NO-GO
  on the endpoint. This is the outcome the 13:21 vindication predicts.
- Extra flips price **POSITIVE** => the endpoint spend is unblocked, and only
  then, with the screen's effect size available to size N honestly.

⚠ **WHAT THE SCREEN CANNOT DO, registered so a positive is not over-read:** it
prices per-flip quality, not the compounding of many flips across a game. It is
a **RULE-OUT instrument** ([[dr-mario-label-budget-rules]]: proxies rule out
only). A negative kills the lane cheaply; a positive does NOT certify gate-v2 —
it only licenses paying for the endpoint that can.

Seed block **73000-73499** is reserved for the screen and is disjoint from
every block in section 4.

## 10. THE PRICE, COMPUTED (see `price_h13.py`, `out/PRICE_H13*.json`)

Cost basis is anchored on H12's OWN spend rather than a quoted rate: H12 paid
~$135 for roughly 1,337 core-hours (phase 1 343, phase 2 null ~497, and the
VOID re-run ~497) = **$0.101 per core-hour**.

| basis for s/pair | core-h (both phases) | cost | with a VOID re-run |
|---|---|---|---|
| 279 s (H12's quiet-node calibration x the measured dose) | 1,709 | **$173** | $275 |
| 390 s (measured locally, but under heavy contention — load-inflated) | 2,389 | **$241** | $384 |

Both exceed the $50-100 envelope this lane was asked to check against. The
flip screen in section 9 costs ~21 core-hours (~$2), or nothing at all if run
on blackmage overnight (~3.5 h wall at 6 workers).

---

*Drafted 2026-08-18 by the h13-gate lane, before any H13 arm was run.
Section 9-10 amended the same morning after the DOSE census and before any
endpoint or screen data existed.*
