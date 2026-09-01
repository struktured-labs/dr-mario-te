# SPEC (decision document, NOT a change): extend the DRSEATLOG latch to carry death GEOMETRY

**Do not build until the soak bar below is met. Reason: DRSEATLOG is a driver change that is
hours old and CERTIFIED FOR CORRECTNESS, NOT STABILITY. Stacking a second driver change onto
an uncertified first is the [[dr-mario-combo-pairing-hazard]] failure — COMBINED FLAGS NEED A
COMBINED CERT — and if a freeze appears with both in, it cannot be attributed and the soak's
evidence is spent for nothing.**

## Why an extension is needed at all

The shipped latch answers *"which seat died"*. It does **not** answer *"what did the death
board look like"*, which is what Stage 2 of the Mesen calibration needs. Verified against the
emitted helper: of the five matching features it carries **one** (viruses-left). `SEAT_T1/T2`
are **booleans** — `fo==0` — so a ledge at row 1 or 2 reads `throat=0` and the boolean
discards precisely the distinction the matching needs.

## What to add (3 bytes, into the free run `$61C7-$61FF`, 57 B — ample)

| byte | content |
|---|---|
| `SEAT_FO` `$61CB` | `fo3` low nibble, `fo4` high nibble (both 0-15; 16 clamps to 15) |
| `SEAT_TOP` `$61CC` | count of occupied cells in P2 rows 0-2 (0-24) |
| `SEAT_GATE` `$61CD` | bit0 = c2 rows 0-1 free, bit1 = c5 rows 0-1 free |

Same site and discipline as the shipped latch: **written every hook while mode==4**, never at
the boundary, because `RB337_STAGE_CLEAR/TOP_7` wipe the boards synchronously at match end.

## ⚠ COST — materially more than the shipped latch, and this is the reason to gate it

The shipped latch is **constant-time** (two cell reads per seat) and measured **+148 cycles**.
`fo3`/`fo4` require a **COLUMN SCAN** — up to 16 rows each — so this is a different load class
on a budget that already overruns by design on `p1_search`.

**Cost precedent, bounded and already registered:** `proph_trigger` performs exactly these
scans, and its `pf_s3`/`pf_s4` loop bounds (16 head passes each, `CPX #128` exit) are recorded
in `tools/nmi126/census.py` `LOOP_BOUNDS`. So the #126 census **measures** this rather than
guessing — reuse those bounds; do not invent new ones.

## GATES — same set as DRSEATLOG, with ONE DELIBERATELY DIFFERENT MUTANT

1. `DRSEATLOG_GEO=0` rebuilds **byte-identical**, with the **emitter-lineage control built
   first**.
2. **⚠ THE MUTANT MUST TARGET THE NEW FAILURE MODE, NOT THE OLD ONE.** "Samples at the
   transition" is already covered by the shipped gate and would pass here trivially — **a
   mutant that cannot fail for the new reason is not a control (R96).** The new failure mode is
   a **WRONG SCAN BOUND**, so the mutant is: **`fo` scan terminated at 8 rows instead of 16**.
   It must produce `fo=8` (the clamp) on any board whose column is empty above row 8, while
   truth says 16 — detectable exactly where it matters, on the sparse boards that dominate this
   death population. A second candidate worth building: **`fo` scan that treats `$FF` as
   occupied**, violating the dual-encoding rule and returning `fo=0` everywhere.
3. #126 frame census, **reusing `pf_s3`/`pf_s4` bounds**; worst non-search pair must stay inside
   29,780 cycles and the delta from the shipped latch must be reported.
4. PRG-RAM `--check` with the deriver config extended to `$61CB-$61CD`.
5. Full cart hazard suite.
6. **Ground-truth agreement in Mesen** as the shipped latch had: cart-latched geometry must
   equal Lua-computed geometry from the live boards, on >= 10 deaths.

## SOAK BAR THAT UNLOCKS THE BUILD — ACCUMULATED EXPOSURE, fixed before the hours accrue

⚠ **CORRECTION to my first draft, which was self-contradictory.** I wrote both *"a freeze
resets the bar"* and *"one event is consistent with the banked rate"*. **Both cannot hold.**
At 0.79 expected events per 12 h the modal outcome is 0 or 1, so discarding all accumulated
exposure because one occurred throws away good evidence for an event the null predicts — and
with P(clean 12 h)=0.45 it would take ~2.2 attempts of up to 12 h each, stalling the build for
days on a rate that never changed.

⇒ **The rule is ACCUMULATED EXPOSURE + a rate comparison. A freeze CONTRIBUTES data rather
than erasing it.** Total soak hours `H`, total freeze/reload events `k`, compared against the
banked λ = 3/45.6 = **0.0658/h**.

### ⚠ WHAT THIS EVENT RATE CAN AND CANNOT RESOLVE — computed, not asserted

Scanning `H` and `k_max` for P(pass | baseline) ≥ 0.75 **and** power ≥ 0.70:

| target | smallest workable window |
|---|---|
| detect a **DOUBLING** | **H = 38 h**, fail if k > 3 (pass 0.76, power 0.73) |
| detect a **TRIPLING** | **H = 14 h**, fail if k > 1 (pass 0.76, power 0.76) |

**No (H, k) pair under 72 h achieves both a low false-alarm rate and 80% power against a
doubling.** That is a property of the event frequency, not of the design.

### THE RULE (choose the practical window, state its limit)

> **PASS when `H ≥ 24` accumulated soak hours with `k ≤ 2` freeze/reload events.**
> P(pass | unchanged rate) = **0.79**; power vs a doubling = **0.61**; power vs a tripling =
> **0.85**.

**A pass is therefore evidence against a TRIPLING, and only weak evidence against a doubling.
It is NOT a safety claim.** If a doubling must be excluded, the window is 38 h with k ≤ 3 —
available by extending the same soak, since exposure accumulates rather than resetting.

`k` counts `RELOADED` lines in `freeze_watch.log` within the window, the same structural source
Amendment 3 of the A/B prereg uses. Report `H`, `k`, the expected `λH`, and which of the two
windows was reached.

## SOAK BAR THAT UNLOCKS THE BUILD — fixed NOW, before the soak produces it


