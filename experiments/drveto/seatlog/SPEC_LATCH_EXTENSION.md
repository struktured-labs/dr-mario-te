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

## SOAK BAR THAT UNLOCKS THE BUILD — fixed NOW, before the soak produces it

**Banked freeze rate for this pairing: λ = 3 events / 45.6 bounded hours = 0.066/h**, i.e. an
expected clean stretch of ~15 h. So a few quiet hours mean nothing, and the bar must be stated
against that rate rather than against zero.

> **BAR: 12 continuous clean hours of the DRSEATLOG soak on bluemage, with freeze/reload count
> compared against the banked rate — not against zero.**

Justification, so the number is not negotiated later: 12.2 h gives **80% power against a
DOUBLING** of the freeze rate (`P(0 freezes | 2λ) ≤ 0.20`). ⚠ And the honest converse, stated
now: **P(0 freezes | UNCHANGED rate) over 12 h is 0.45**, so **a clean 12 h is NOT strong
evidence of safety** — it is evidence against a *gross* regression only. Anything subtler needs
~16 h (50% worsening) or the rate simply cannot be resolved at this event frequency.

**If a freeze occurs inside the window, the bar resets and the build waits** — with the caveat
that a single freeze is also consistent with the banked rate, so one event is not by itself
evidence DRSEATLOG caused it. Report the interval and compare.
