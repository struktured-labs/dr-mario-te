# DRTUCKGUARD — gate results (owner priority: tap-out reduction + efficient clears)

Candidate: **`7a22474f643d9a150d18f1390b2892f0`** (`DRTUCKGUARD=1` on the Childproof flag set).
Baseline: **`30c921837fdaa8e915175cdcf8709a24`** = Childproof, the standing champion.

## GATE 1 — byte identity ✅

| build | md5 | expected |
|---|---|---|
| `DRTUCKGUARD=0` | `30c921837fdaa8e915175cdcf8709a24` | **= Childproof exactly** |
| `DRTUCKGUARD=1` | `7a22474f643d9a150d18f1390b2892f0` | **= the team lead's build, reproduced independently** |

The flag is byte-inert when off, and the two mutants below are inert with it.

## GATE 2 — MUTANTS, chosen for THIS mechanism and failing in OPPOSITE directions

A recycled mutant would pass trivially here and prove nothing (R96). Both target the guard's own
logic — *"is the fall budget measured in the right column, with the right margin"*:

* **`approachcol`** (`7fc752e0…`) — counts free rows in the **APPROACH** column instead of the
  **FINAL** one. The entire insight is that the budget must be measured where the capsule must
  FALL after moving laterally. Below the trigger the approach column is occupied — that is *why*
  the capsule rests there — so this **OVER-VETOES** and tucks should collapse toward zero.
* **`nomargin`** (`e2d01e2a…`) — drops the `+2` margin that every one of the 23 completions had.
  This **UNDER-VETOES**: marginal descriptors are admitted and stranding should return.

⇒ **The gate is therefore TWO-SIDED and must fail both**: tucks must still HAPPEN (kills
`approachcol`) **and** stranding must stay low (kills `nomargin`). A one-sided gate would pass
one of them. *Status: pending the Mesen measurement.*

## GATE 3 — #126 frame census ✅ (+1002 cycles)

| build | worst admissible ordered pair | margin |
|---|---|---|
| `DRTUCKGUARD=0` | 25,464 / 29,780 | +4,316 |
| `DRTUCKGUARD=1` | **26,466 / 29,780** | **+3,314** |

⚠ **The census REFUSED the first run**: *"UNDECLARED LOOPS — head $8421 label='tg_lp'"*. That is
the guard behaving correctly — it will not score a loop whose bound is not declared. Bound added
with its proof: `TG_OFF` starts at `(15−TUCK_R2)*8 + final_col` and advances by exactly 8,
exiting at ≥128; a board index is 0..127, so with step 8 the loop runs **at most 16 times**
regardless of start row.

⚠⚠ **AND MY CENSUS HARNESS WAS WRONG FOR THIS CART, which the numbers caught.** My `h5_cvc.py`
was written for the NON-pipelined CvC config and pairs scenarios by full cross product. Childproof
is **pipelined** (`DRPRESPIPE=1`), where `steady_play`/`spawn_edge_p2` are not usable as the other
half of a pair — pairing one with a phase double-counts the pipeline. The wrong harness reported
`DRTUCKGUARD=0` as **30,816 / OVER by 1,036**, i.e. it would have condemned the *unmodified
champion*. Using the human-cart pair construction, `DRTUCKGUARD=0` reproduces the banked
**25,464 / +4,316** exactly — an independent check that the corrected harness is right.
**Same class as every other failure this run: a tool calibrated in one regime applied to another.**

## GATE 4 — PRG-RAM ✅

`--check` green, no collisions, every indexed writer bounded, with a new `tuckguard-human`
deriver config so `TG_NEED $61B9` and `TG_OFF $61BA` show their writers.

## Standing note

⚠ A veto reverts to pre-tuck behaviour, so it **can never be worse than not tucking** — but that
is an argument from the code, **not evidence**. The A/B still has to show it HELPS.
**Safe-by-construction must not slide into assumed-beneficial.**
