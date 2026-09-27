# PREREG — #114 DRROTDIR: shortest-direction rotation

**Registered before any DRROTDIR=1 measurement existed.** Proof of timing: at commit time
`tmp/rotwedge/` contains only `rw_o{0..3}_12000_s{114,271,999}` — twelve *reference-cart*
(`9fefaedb`) arms, produced before `DRROTDIR` existed as a flag — and there is no
`rw_on_*` or `rw_off_*` directory on disk. `roms/rotdir_on.nes` has been built but never
executed.

## The change

`patch_cartridge_copro.py`, `act_p2` rotation pre-phase. The executor has only ever pressed
**A**, and A is `DEC $A5` in the stock handler at `$8E2B`, so the orientation ring is walked
one way. From spawn (game orient 0) that costs 1 rotation to reach game orient 3, 2 to reach
2, and **3 to reach 1**. **B** is `INC $A5` in the same handler. DRROTDIR picks whichever is
shorter:

```
delta = (TGT_O2 - $03A5) & 3        ; delta != 0 here (the CMP above peeled that off)
delta == 1 -> B ($40, CW,  1 press)
delta == 3 -> A ($80, CCW, 1 press)
delta == 2 -> A  (2 presses either way; keeping A leaves the 180 path bit-for-bit unchanged)
```

## Baseline (already measured, reference cart 9fefaedb, 3 seeds x 4 orients)

Constant-orient arms, frames of mode 4 per pill:

| copro orient | game orient | CCW presses (OFF) | f/pill |
|---|---|---|---|
| 2 | 0 | 0 | 77.79 |
| 0 | 3 | 1 | 78.99 |
| 3 | 2 | 2 | 80.48 |
| 1 | 1 | 3 | 81.07 |

≈ **1.09 frames per rotation.**

## Registered predictions

Paired: same seeds, same probe, same publisher; only the cart differs
(`rotdir_off.nes` = md5 `9fefaedb…`, byte-identical to the reference cart, vs
`rotdir_on.nes` = md5 `d1db55ba…`).

**P1 — the win.** The delta-1 arm (copro 1 / game 1) drops from 3 presses to 1:
f/pill **81.07 -> 78.9 ± 0.6**, i.e. −2.2 ± 0.6.

**P2 — the three controls MUST NOT MOVE.** copro 2 / 0 / 3 (deltas 0, 3, 2) each stay within
**±0.6 f/pill** of their OFF value in the same run. This is the half of the prereg that can
fail, and it is why a constant-orient ladder was chosen over a mixed-orient tempo average:
a change that speeds everything up equally is *not* this fix and must be caught.

**P3 — not inert, and inert-by-construction when off.** `pressB` (frames with `$F6 == $40`)
must be **> 0.5 x pills** on the ON delta-1 arm and **exactly 0** on every OFF arm and on
every ON arm with delta != 1.

**P4 — byte-identity.** `DRROTDIR=0` rebuilds md5 `9fefaedba9a27ba10f058ac239eeb77d`.
*Already verified* — this one is recorded, not predicted.

**Seeds.** 271, 2001, 3001. Seed 271 is known clean at all four orients on the reference
cart. 2001/3001 are unused. **Declared in advance:** any (orient, seed) cell whose OFF arm
wedges (#131; detector = `wedges > 0`) is dropped from **both** arms of that cell and
reported as dropped — the wedge freezes the whole game and its f/pill is not a tempo
measurement. If more than 2 of 12 cells drop, the ladder is under-powered and the verdict is
NO-VERDICT, not a pass.

## Mutants that MUST fail the above

| # | mutation | must fail |
|---|---|---|
| M1 | direction inverted: B on delta 3 instead of delta 1 | P1 (delta-1 arm stays ~81) **and** P2 (delta-3 arm slows to ~81) |
| M2 | delta computed as `($03A5 - TGT_O2) & 3` | P1 (delta-1 arm stays ~81) and P2 (delta-3 arm slows) |
| M3 | B path omits `STA $F8` (no press edge) | P1 — with no edge the rotation never re-fires and the delta-1 arm gets *slower*, not faster |
| M4 | **population**: `CMP #$05` so the B branch is unreachable | P3 — `pressB == 0` on the delta-1 ON arm, proving the arm's population really does contain delta-1 plies rather than the tempo change coming from somewhere else |

M4 is the population mutant required by gate-standard rule 7: without it, a green P1/P2 would
not establish that the delta-1 case is what the delta-1 arm actually exercises.

## Verdict routing

- P1 **and** P2 **and** P3 all pass, all four mutants killed, `test_rtivec` preflight green,
  romgen reproducible at `DRBUILDID=0` => **GO**, propose a named cart to main.
- P1 fails but P2/P3 pass => the win is smaller than the instrument resolves. Report the
  measured interval and **close as under-powered**; do not ship a tempo change that cannot be
  measured.
- P2 fails => the change is doing something other than what it claims. **NO-GO**, and the
  fact is the finding.
- Any mutant survives => the cases are vacuous; fix the cases before reading any number.
