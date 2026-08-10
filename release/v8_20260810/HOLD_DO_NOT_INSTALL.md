# ⚠ HOLD — DO NOT INSTALL THIS CART YET (2026-08-10)

`v8 REMATCH (hardened).nes` / `087ff959ac510c613bbbd2eb1ac5ecf3` is **on hold**, pending a fix
and a re-gate. It is staged here for provenance, not for play. `install_to_pocket.sh` still
works and will still verify everything it claims to — **just don't run it yet.**

## Why

The `DRRTIVEC` NMI shield committed in `b6e5540` **clobbers the accumulator on every NMI that
reaches it.** Disassembled straight out of this cart at `$CEEC` (identical in PRG idx1 and idx3):

```
AD 2E A0   LDA $A02E    <-- destroys A
C9 40      CMP #$40
D0 01      BNE +1
40         RTI
4C 05 80   JMP $8005    <-- enters the game's NMI handler with A already destroyed
```

The game's handler starts with `PHA` and ends with `PLA`, so it faithfully saves and restores
**the already-corrupted value**. The interrupted main-loop code gets a wrong `A`. Silent.

## Why it matters for THIS cart specifically

Alone, `DRRTIVEC` is harmless: in 32KB PRG mode the CPU fetches vectors from idx1, whose NMI
vector is the untouched `$8005`, so the shield never runs. **But this cart also carries
`DRMMC1RST`, and the MMC1 reset write ORs `5'b0_11_00` into control (`MMC1.sv:110`), forcing PRG
mode 3 — which hard-fixes `$C000-$FFFF` to idx3, whose NMI vector IS the shield.** So after the
driver's first bank switch, NMIs route through the shield until the game's own `selCTRL` rewrites
control.

This is the **second** distinct way these two fixes interact. The first (a BRK loop) was caught by
killed mutant M3 before shipping. This one was caught by the v6d hardening gate — after the cart
had been built and staged, and after this cart had passed an 18,000-frame multi-match gate showing
numbers identical to the unhardened build. **A gate that measures match completion is not
sensitive to a corrupted accumulator**, which is exactly why "it passed" was not enough.

## The fix (v6e), verified to fit

`$CEEC-$CEFC` is a 17-byte free run (base bytes `FF 00×6 FF FF 00×6 FF FF`; code resumes at
`$CEFD`). The corrected shield is 15 bytes and preserves `A` on both paths:

```
$CEEC  48        PHA
$CEED  AD 2E A0  LDA $A02E
$CEF0  C9 40     CMP #$40
$CEF2  D0 03     BNE $CEF7
$CEF4  68        PLA
$CEF5  40        RTI          ; overrun: skip this NMI, A intact
$CEF6  40        RTI          ; IRQ vector target, stack-balanced
$CEF7  68        PLA
$CEF8  4C 05 80  JMP $8005    ; game NMI, A intact
```

Repoint the idx3 IRQ vector to `$CEF6` and update the delta assert. Flags need no saving — NMI
hardware pushes P and `RTI` restores it.

⚠ Do **not** fold the BUSY predicate into the same edit: it needs 20 bytes and will not fit, and
it soft-bricks on a stale BUSY latch because `DRBUSYESC`'s escape runs from the very hook the
shield suppresses.

## Lift this hold when

1. v6e is built with the corrected shield, and
2. it re-clears the mechanism gate (defect must still fire with the fixes off), and
3. it clears a multi-match gate **with a check that is actually sensitive to A corruption** —
   the previous gate was not.
