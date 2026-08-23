# FREEZE MECHANISM — it is the #133 unpausable soft-lock, and it is live on the SHIP arm

**2026-08-23. Diagnosed entirely from the banked save-states. No emulator, no
box time.**

## It is NOT a CPU lockup

14 bytes in the copro driver's state block ADVANCE throughout the 360 s
"freeze" — `$6147`, `$615b`, `$6183`, `$6190` each take 17-18 distinct values
across the 18 samples, and `$6176` (BUSY) even toggles. **The 6502 is executing
and NMI is firing the whole time.** So this is not a hang, and it is not the
[[dr-mario-busy-brick]] BUSY latch (`$6176`=`$00`, `BUSYSKP`=`$00`,
NAV_MAGIC warm).

## The GAME main loop is blocked — OAM is never refilled

The 1P main loop is `$8148 JSR $8157` (fill OAM) → `$814B JSR $978E`
(pause-check) → `$814E JSR $B654` (frame-wait, whose tail `$B894` clears the
OAM buffer to `$FF`) → `JMP $8148`. So in normal play the `$0200` buffer is
cleared and refilled every frame, and a sample lands on a filled buffer most of
the time.

| | OAM buffer at `$0200` all-`$FF` |
|---|---|
| **48757 ship (frozen)** | **18 / 18 samples** |
| **45431 ship (frozen)** | **18 / 18 samples** |
| 48757 slice (control) | 0 / 18 |
| 45431 slice (control) | 0 / 18 |
| **population A baseline (255 rows)** | **62 / 4,589 = 1.35%** |

At the 1.35% base rate, 18-for-18 is ~10⁻³⁴. **The buffer is never refilled ⇒
the main loop never reaches `$8157` ⇒ it is parked inside the pause-check.**

## Why it can never leave: `$F5` can never equal `$10`

`$978E` is a self-contained BLOCKING routine: on START it blanks, draws
"PAUSE", then spins `JSR $B654 / JMP` until the exit compare at `$97D6` sees
`$F5 == $10` (pure START).

Measured in the frozen states:

| cycle | `$F5` across all 18 samples | ever `$10`? |
|---|---|---|
| 48757 ship | `$80` (with two `$00`) | **NO** |
| 45431 ship | `$80` (with one `$00`) | **NO** |
| 48757 slice | `$00` throughout | n/a |

`$80` is the **A button** — a member of the P1 executor's vocabulary
`{none,right,left,down,A}`. The executor rewrites `$F5` every hook, before the
stock edge-detect, and **its vocabulary contains no START**, so `$F5 == $10` is
unreachable and the pause loop is permanent.

**This is defect #133 verbatim**, as already written in
`patch_cartridge_copro.py:427`: *"a P1-driven cart is UNPAUSABLE … the pause
loop's exact-compare `$F5==$10` at `$97D6` can never be satisfied: one stray
START (human, script, or nav glitch) soft-locks the cart permanently."*

## The fixes exist and are OFF on the arm under test

From `roms/manifests/hardened-ctrl-ship-20260819.json` (the SHIP arm,
`9fefaedb`): **`DRUNPAUSE = 0`**, **`DRSTARTGUARD = 0`**, `DRVERFIX = 0`.

`DRUNPAUSE` (#133) restores stock START semantics for P1 so the pause can be
exited; `DRSTARTGUARD` (#134) stops the driver's own START injections landing
on a match frame. Both are already implemented and both are enabled on the
hardened cart `70a857cc`. They are simply not in the A/B's ship arm.

## ⚠ What this does NOT show — slice is not immune

**Both arms lack the fix** (the slice manifest does not carry `DRUNPAUSE` /
`DRSTARTGUARD` either, so both default off). Slice did not wedge **on these two
seeds**; nothing here shows it cannot. The arm difference is in whether a stray
START ever *lands*, not in whether the trap exists — and the trap is armed on
both.

**What injects the stray START is still unproven.** DRP1SLICE changes NMI slice
timing, and #131's lesson is that a mode-gated input arm must also exclude the
predecessor mode, so a timing shift plausibly decides whether an injected START
lands on a play frame. Plausible, and consistent with ship-2 / slice-0 — but
not demonstrated, and I am not asserting it.

## Consequence

The ship candidate carries a **known, documented, already-fixed defect** that
deterministically soft-locks the cart on at least two of 240 registered seeds,
reproducibly across two boxes and two firmware versions. The owner is playing
these carts. **The fix is a flag flip that already exists and is already
shipped on the hardened cart.**

⚠ The rate is still not estimated: ship 2/129 vs slice 0/126 is **Fisher exact
two-sided p = 0.498, uninformative about a rate.** What is established is the
mechanism and that it is reachable, not how often it fires.
