# DRSEATLOG — gate results (owner-approved build, 2026-09-01)

Deliverable: **`seat_on_L20.nes` md5 `7f60363c14ef5d5ab25dc92747267575`**
(CvC hardened flag set, L20, `DRSEATLOG=1`).

## GATE 1 — byte identity, WITH THE LINEAGE CONTROL BUILT FIRST ✅

The control was built *before* interpreting anything, because on this program a byte-identity
failure can indicate the **emitter lineage** rather than the flag (the `FC_STAB $61BB→$61C4`
relocation). It landed exactly on the pre-existing baselines, so there is no lineage confound
to disentangle:

| build | md5 | expected baseline |
|---|---|---|
| `DRSEATLOG=0`, L11 | `858990bf37a150d6ee90178140fd0168` | **exact match** |
| `DRSEATLOG=0`, L20 | `6e657dc812842c2cc7edb05be0bfa5cf` | **exact match** |

⇒ the emitter edit is provably inert when the flag is off.

## GATE 2 — MUTANT KILL (the one that matters) ✅

Truth computed in Lua from the **live** boards every frame; the cart never sees it. The cart's
own latch (`$61C7-$61CA`) is read at match end and compared.

| arm | deaths | agree | disagree |
|---|---|---|---|
| **correct** (latch during play) | 10 | **10** | 0 |
| **mutant** (sample at the transition) | 10 | 0 | **10** |

★ **And the mutant fails in exactly the predicted way, which is the point:** it reads
`cart(t1=0,t2=0)` — an EMPTY board — while truth is `t2=1`. That is `RB337_STAGE_CLEAR/TOP_7`
having wiped `$0400`/`$0500` before the sample. **The trap is demonstrated, not asserted**, and
a gate that merely showed "different numbers" would not have proven it.

## GATE 3 — #126 frame census ✅

| build | p1_search (by-design overrun) | worst NON-search pair | margin |
|---|---|---|---|
| `DRSEATLOG=0` | 94,791 | 17,208 / 29,780 | +12,572 |
| `DRSEATLOG=1` | 94,866 | **17,356 / 29,780** | **+12,424** |

**Cost: +148 cycles** on the worst non-search pair, +75 on `p1_search`. Measured, not assumed.

## GATE 4 — PRG-RAM + hazard suite ✅

`derive_prg_ram_map.py --check`: **no collisions, every indexed writer bounded**, with a new
`seatlog-cvc` deriver config so `$61C7-$61CA` show their writers (and so an overlap with
`PROPH_DIR $61C6` would have been caught).

Cart hazard suite **ALL PASS**: `test_rtivec` (4/4 mutants), `test_mmc1rst` (3/3),
`test_rtivec_aclobber`, `test_prg_ram_map`, `test_combo_cart`.

## Why this design was preferred

**The latch runs every hook, so a defect is CONTINUOUS rather than rare — loud, not hidden.**
After a run whose failures were all quiet (a boundary sample that would have logged plausible
garbage, a gate that printed its own inputs, a detector validated in the wrong regime), loud is
the property we want.
