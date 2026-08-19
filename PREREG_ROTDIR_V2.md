# PREREG_ROTDIR v2 — amendment, registered after v1 returned NO-VERDICT

v1 (`PREREG_ROTDIR.md`) ran and **hit its own stop rule**: it capped dropped cells at 2 of 12
and 4 dropped, so v1's registered verdict is **NO-VERDICT**, not a pass and not a failure. That
stands; this file does not reinterpret v1's data, it registers a corrected design.

## What v1 established anyway (recorded here, not re-litigated)

**The three control orients are EXACTLY equal between arms — 0.00, not "within tolerance".**

| copro | game | delta | OFF f/pill (s271 / s2001 / s3001) | ON f/pill |
|---|---|---|---|---|
| 2 | 0 | 0 | 78.79 / 219.33* / 78.56 | 78.79 / 219.33* / 78.56 |
| 0 | 3 | 3 | 78.48 / 78.18 / 75.77 | 78.48 / 78.18 / 75.77 |
| 3 | 2 | 2 | 80.48 / 100.97* / 80.79 | (same, cell-for-cell) |

`*` = a cell containing a #131 wedge. Pills, pressA, pressB and f/pill agree to the last digit
in every control cell, wedged ones included. Two things follow:

1. **P2 is satisfied in the strongest possible form.** For delta 0/2/3 the emitter produces the
   *same bytes* with the flag on and off, so the runs are replicas. There is nothing for a
   wedge to bias.
2. **The rig is deterministic given (cart, seed)** — a wedged cell reproduces its wedge exactly.
   That is *why* the drop rule has to be rewritten: a wedge is not noise to be averaged out, it
   is a deterministic property of the cell.

## The actual problem v1 hit

Only at the WIN orient (copro 1, delta 1) do the arms emit different bytes, so only there can a
wedge land on one arm and not the other. It did: at seeds 2001 and 3001 the OFF arm wedged
(24 and 87 pills) while the ON arm did not (118 and 116). That leaves **one** clean paired cell
(s271) for the one comparison that matters.

## v2 design — registered before any v2 run exists

**Scope.** The WIN orient only (copro 1). The controls are settled by exact equality above and
are not re-run.

**Seeds.** 16 fresh seeds: 4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 4009, 4010, 4011,
4012, 4013, 4014, 4015, 4016. None has been used in this lane.

**Inclusion, decided per cell before looking at f/pill:** a cell is scored iff **both** arms
report `wedges == 0`. A wedge in either arm drops the pair. This is the v1 rule with the cap
re-derived for the real wedge rate rather than a guessed one.

**Power bar.** Score only if **≥ 8 of 16** pairs survive. Below that: NO-VERDICT again, report
the wedge rate, and escalate to #131 rather than adding seeds until something passes.

**P1 (registered).** Mean ON f/pill minus mean OFF f/pill over surviving pairs is
**≤ −1.5 f/pill**, with a paired 95% CI (t, n−1 df) whose upper bound is **< 0**.
Point prediction −2.2, from 2 fewer presses at the 1.09 f/press measured in v1.

**P3 (registered, unchanged).** On every surviving pair: OFF `pressB == 0` and `pressA > 0`;
ON `pressB > 0.5 × pills` and `pressA == 0`.

**Secondary, EXPLORATORY — explicitly not a claim.** v1 showed OFF wedging at this orient in
2/3 seeds and ON in 0/3. v2 records the per-arm wedge counts over all 16 seeds. Any difference
is reported as an observation for #131 with the n stated, and is **not** offered as a benefit of
DRROTDIR: the flag changes match length, match length sets the restart phase, and phase is what
#132 already showed drives the wedge. A tempo change that shifts wedge exposure is a confound to
flag, not a win to bank.

**Mutants.** The v1 mutant carts (`rotdir_m1..m4`) are re-scored on the same surviving seed set
by the same predicates. A mutant that passes P1 is a surviving mutant and voids the verdict.

## Verdict routing (unchanged from v1 in spirit)

- P1 and P3 pass, ≥8 pairs, all 4 mutants killed, preflight green, romgen reproducible at
  `DRBUILDID=0`, `DRROTDIR=0` still md5 `9fefaedb` => **GO**.
- P1's CI includes 0 => under-powered or null; report the interval and close, do not ship.
- P3 fails => the flag is not doing what it claims; NO-GO.
- < 8 surviving pairs => NO-VERDICT; the blocker is #131, not this fix.
