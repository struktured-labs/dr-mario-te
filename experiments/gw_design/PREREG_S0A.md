# PREREG — S0-A: argmax-flip screen for the 2-candidate deepening

> # ⚠⚠ VOID — SUPERSEDED BY `PREREG_S0A_v2.md`
>
> **Voided 2026-08-18, before the registered run produced a single row.** The gate found
> that **87.1% of "exact top-2 ties" are the same physical placement** — a double capsule is
> symmetric under 180°, so orientations 0/2 and 1/3 are identical placements with exactly
> equal value. §3's arm would have spent the screen comparing a board with itself and
> returned a spurious CLOSE.
>
> This document is kept unedited as the registered-then-voided record. It is **not** amended
> in place; §10's own rule says a wrong prereg is voided and re-registered. Nothing below
> was used to produce a result.

**Registered 2026-08-18, BEFORE any screen data exists.** Task #117 step 1, pre-approved by
the team lead. Companion: `GARBAGE_WINDOW_DESIGN.md` §4.2 on branch `gw-design`.

This document fixes the population, the arm, the readout, the decision rule, the void
conditions and the mutant set. Nothing below may be changed once the first screen row is
written. If something here turns out to be wrong, the run is reported as void and re-registered
— it is not silently amended.

---

## 1. What this screens, and what it cannot do

**Question:** at a post-garbage ply where the champion's top-2 candidate values are exactly
tied, does deepening those two candidates by one ply **change the chosen move**?

This is a **rule-out instrument** and nothing more. A flip rate below the floor kills the
garbage-window lane for the cost of an afternoon. A flip rate above the floor **does not**
say the flips are good — it only licenses paying for the farm A/B that can price them
(§4.3 of the design doc, ~$4). Proxies rule out; they do not rule in.

**It carries a second, independent job** (task #121): re-deriving the **50.5% pre-vs-post-
garbage argmax flip**, which currently has *no reproducible artifact in any of the 30
worktrees* and was measured entirely below 45% board fill. That number is what makes the
post-garbage re-search mandatory and motivates the whole lane, so the lane must stop resting
on it. Marginal cost is ~zero: the screen already stands at post-garbage plies holding both
boards.

---

## 2. Population

Plies drawn from real champion games under the standard bursty (dr. lulu) pressure model,
level 11, P2 side, at seeds **110000-110999** (registered; disjoint from H12 endpoint
41100-50099, the perpetual gate block 61000-61999, extension 62000+, census 70000, and the
h13 screen 90000-90499).

- **Primary population `T`:** plies that are (a) post-garbage decisions — the board has just
  received and settled a volley — AND (b) the top-2 champion values are **exactly** tied.
- **Secondary population `P`:** all post-garbage plies, tie or not (for §6, the re-derivation).

Both counted and reported. The tie predicate matches `h12_arm.py` exactly: `fv[0] == fv[1]`
on the sorted finite candidate values, candidates ordered by `CHAMP_ORDER`.

---

## 3. The arm under test — the 2-candidate deepening

At a ply in `T`, with `cands = [c1, c2]` the top-2 by champion value (`c1` = the champion's
own pick, asserted):

For each candidate `c`:
1. clone the environment, apply `c`, settle → successor board;
2. the successor's **current** capsule is the **known** `nxt`;
3. the successor's **preview** capsule is **one sampled draw**, from a stream seeded by
   `(play_seed, ply)` — **the same draw for both candidates**;
4. score(`c`) = the champion's own root value of that successor position, i.e.
   `max` over legal moves of `_champ_values(successor, cur=nxt, nxt=sampled)`.

Pick `argmax` of score. **On a tie in score, keep the champion's pick** (conservative, and it
mirrors the "degrade to the certified champion's move" pre-emption rule).
**FLIP** := deepened pick ≠ `c1`.

### 3.1 Declared observation set (ceiling-arm rule)

The arm **sees**: the settled post-garbage board, `cur`, `nxt`. All three are in cart RAM at
the release frame, so the arm is on-cart-legal.
The arm **does not see**: the true next-next capsule (sampled, k=1), any future garbage
volley, the opponent's board, or any outcome label.

⚠ **The sampled next-next is the one thing the cart must synthesize, and it is priced.** The
budget table assumes **k = 1**: cost = 2 candidates × 1 search = 2 × C. **k > 1 multiplies the
cost by k** (2k × C), and at k = 5 — H12's `fork_samples` — nothing fits at any board height.
**k = 1 is not a convenience, it is the only affordable choice**, and it is registered here so
that a later "just add samples" cannot quietly break the budget.

### 3.2 Why common random numbers

Both candidates must face the identical sampled future or the comparison rewards draw luck
rather than position quality. This is the same pairing discipline as the capsule-fair refork
screen. Mutant **M-D2** exists to prove the pairing is load-bearing.

---

## 4. Stratification — registered, because pooling is the failure mode here

**Fill** := occupied cells / 128 on the settled post-garbage board.

Strata: **<30% · 30-45% · 45-60% · ≥60%**, and separately by `h_hit`.

Every readout in §5 and §6 is reported **per stratum first, pooled second**. The lane targets
the high-fill regime; a result that exists only below 45% fill does not license it. This is
the specific defect being repaired — the original 50.5% pooled a corpus that never left low
fill.

---

## 5. Primary readout and decision rule — FIXED BEFORE DATA

**Readout:** flip rate = flips / |T|, with **Wilson 95% CI**, overall and per stratum.

Let `U` = CI upper bound, `L` = CI lower bound. The **≥45% fill** group is the union of the
45-60% and ≥60% strata.

| verdict | condition |
|---|---|
| **CLOSE THE LANE** | `U(overall) < 2%` **OR** `U(≥45% fill) < 2%` |
| **PROCEED** to the ~$4 farm A/B | `L(≥45% fill) > 2%` |
| **INDETERMINATE** | otherwise — report as such, do **not** proceed, and state the n that would resolve it |

The 2% floor is the project's standing argmax-flip gate: below it an arm is untestable and a
null means nothing.

**Note the asymmetry, and it is deliberate.** Closing may be triggered by *either* the pooled
or the high-fill result; proceeding requires the **high-fill** result specifically. A lane
aimed at the near-death regime does not get to be licensed by mid-board flips.

---

## 6. Secondary readout — re-deriving the 50.5% (task #121)

Over population `P`: `argmax(champion | PRE-garbage board)` vs
`argmax(champion | settled POST-garbage board)`. Same board, same capsules; the only
difference is whether the volley has been applied. Wilson CIs, per stratum.

**No pass/fail rule is attached** — this is a measurement, not a gate. But one reporting rule
is registered: **if the ≥45%-fill flip rate is materially below the low-fill rate, that is
reported as a HEADLINE, not a footnote**, because the entire justification for the mandatory
post-garbage re-search rests on this number holding at high fill.

Committed rig, committed output, so the number is reproducible from this day forward.

---

## 7. VOID conditions — a run that hits one is void, not null

1. **Coverage.** Fewer than **100** plies in `T` land at ≥45% fill ⇒ the high-fill readout is
   **VOID**, the lane verdict is INDETERMINATE, and the corpus must be re-scoped. *A corpus
   that never reaches the regime under test is not a conservative bound, it is a different
   experiment* — the prestart lane published a 69% fire rate that was exactly this mistake.
2. **Non-vacuity.** `|T| == 0`, or zero rows logged, ⇒ void. A logger that never fired proves
   nothing.
3. **Mutant survival.** Any mutant in §8 surviving ⇒ void until the gate is repaired.
4. **Determinism.** Re-running one seed must reproduce its rows exactly. Any mismatch ⇒ void.

---

## 8. Killed-mutant set — registered before the gate is written

A check that cannot fail is not a check. Each mutant is paired with the observable that can
see it; an unkillable-by-that-observable mutant is a design error in the gate, not a pass.

**Verdict router:**

| id | mutation | must be caught by |
|---|---|---|
| M-R1 | always returns PROCEED | synthetic 0%-flip input ⇒ must return CLOSE |
| M-R2 | comparison inverted (`<` for `>`) | synthetic high-flip input ⇒ wrong verdict |
| M-R3 | uses the point estimate, ignores the CI | low-n input, point 3% but `L` < 2% ⇒ must be INDETERMINATE, not PROCEED |
| M-R4 | collapses strata to pooled | synthetic case: pooled 5%, ≥45% stratum 0% ⇒ must CLOSE, not PROCEED |
| M-R5 | ignores the coverage void | synthetic case with 3 high-fill plies ⇒ must be VOID, not a verdict |

**Instrument:**

| id | mutation | must be caught by |
|---|---|---|
| M-D1 | deepening returns the champion's pick unconditionally | flip rate must be **exactly 0**; any flip means the screen invents them |
| M-D2 | unpaired futures (independent sample per candidate) | flip rate must move materially; proves CRN pairing is load-bearing |

M-D1 is the two-sided control: M-D2 shows the screen *can* see a change, M-D1 shows it does
not manufacture one.

---

## 9. Logging — per-flip provenance is mandatory

Stage 2 spent 15,000 games reaching a NO_GO with **zero mechanism**, because `flips` was
logged as a bare integer. Every row logs: `seed, ply, fill, h_hit, viruses, max_h, d_spawn_h,
champ_pick, deep_pick, score_c1, score_c2, sampled_capsule, tie_margin, t_to_end, result`,
plus the arm tag and the code hash.

---

## 10. Cost and stopping

Fork-free; ~2 extra root evaluations per tie ply. Estimated well under an hour on 14 cores,
$0 (local, blackmage). **Runs only after the h13-gate screen releases the cores** (~13:10
EDT, coordinated directly).

No interim peeking at the primary readout. The run completes, the gate runs, then the verdict
is read once.
