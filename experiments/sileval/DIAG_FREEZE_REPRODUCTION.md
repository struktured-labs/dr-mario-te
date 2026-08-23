# DIAGNOSTIC — the two ship-arm freezes REPRODUCE, deterministically, on the other box

**2026-08-23, old box (10.42.0.225, stock MAC, Main 2024-05-07). 4 cycles,
360 s / 20 s, the registered cycle parameters. Armed for this diagnostic only
and disarmed immediately after.**

**This is NOT population B.** No `out_oldbox/rows/` row exists; everything here
lives in `out_oldbox/diag_freeze/`.

## Result: 4 of 4, including both controls

| cycle | distinct RAM states | distinct frames | state | LFSR | verdict |
|---|---|---|---|---|---|
| **48757 ship** | **1** of 18 | **1** of 18 | 42/38 | `$f123` | **FROZEN** |
| 48757 slice | 18 of 18 | 18 of 18 | 43/36 → 39/28 | `$f123` | played normally |
| **45431 ship** | **1** of 18 | **1** of 18 | 47/39 | `$1973` | **FROZEN** |
| 45431 slice | 18 of 18 | 18 of 18 | 45/36 → … | `$1973` | played normally |

**Both freezes recur at the byte-identical state the NEW box froze at:**
48757 at 42/38 and 45431 at 47/39 — exact matches, not merely "a freeze". The
virus counters, the mode and the RNG state are constant across all 18 samples
of the full 360 s cycle, and all 18 screenshots are one hash.

The LFSR at the frozen state equals the LFSR of the SAME seed's slice cycle
(`$f123`, `$1973`), which independently confirms the paired-seed premise: both
arms are playing the same generated match, and ship stops partway into it.

## What this does and does not establish

**It is a reproduction, and it raises the freeze to a CANDIDATE CART PROPERTY.**
It is deterministic and seed-addressable: seed 48757 + ship cart wedges at
42/38, every time, on two different machines.

**It does NOT satisfy prereg rule 5(a) as written.** Rule 5(a) asks for a
re-run of the same arm; this is a re-run of the same arm **on a different box**,
which is a different population. In one respect that is weaker (not the
registered control) and in another stronger: reproducing across two DIFFERENT
boxes running two DIFFERENT MiSTer Main versions (260707 vs 2024-05-07) rules
out box-specific and firmware-specific causes that a same-box re-run could not.

**Had it NOT reproduced, that would not have cleared ship** — it would only have
meant we did not yet have the mechanism.

## The count, with its caveat attached

Population A: **ship 2/129, slice 0/126 — Fisher exact two-sided p = 0.498, so
the count is uninformative about a RATE.** That caveat travels in the same
sentence as the 2/129, always. What the reproduction changes is not the rate
estimate but the *status of the two events*: they are real, deterministic, cart-
and-seed-addressable, and they are on the arm we would promote.

## Why this is now worth a lot

There is a **deterministic repro**: seed 48757, ship cart `9fefaedb`, θ400 core.
The freeze is reachable in an emulator with the seedjit template, where the NMI
behaviour can be traced directly rather than inferred from silicon sampling.
That is the cheapest path to the mechanism, and it needs no box at all.

Artifacts: `out_oldbox/diag_freeze/` (4 rows, 72 save-states, 72 screenshots).
