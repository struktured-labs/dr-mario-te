# PARKED: why does DRHOLDBOARD=1 cause the mid-match abort?

Owner ruled 2026-08-09: *"ship v8 without holdboard we will come back to it."* This note exists
so the next person starts from where I stopped rather than from the symptom.

Board-hold is a feature the owner **asked for** (task #48: keep end-of-game boards visible past
the W / GAME OVER screens). v8 shipping without it is a real regression he will notice. A genuine
root cause is the path back to giving it to him.

## What is settled

The **fault** is understood and confirmed on ship bytes: MMC1 shift-register interleave. The base
game writes a 5-write CHR serial sequence to `$DFFF` from the main loop every frame; the driver's
`_sel` writes the PRG register at `$FFF0`. There is **one shared 5-bit shift register**. When the
hook runs long enough that the main loop's CHR sequence slips into the hook's bank switching, the
sequence is cut mid-load and the 5th shift completes with mixed CHR+PRG bits **into the PRG
register** → garbage bank → bank 0 → `$8036` → full RAM wipe → title.

Correlation, same frame, on the exact ship bytes (`tools/gate/probe2.lua`):

| arm | non-boot straddles | non-boot `$8036` entries | RAM wipe |
|---|---|---|---|
| v6c ship (HB=1) | 1 (f681) | 1 (f681) | f681 |
| v6b (HB=1) | 1 (f2458) | 1 (f2458) | f2458 |
| cen6c_both (HB=0) | **0** | **0** | none (its wipes are normal round clears) |

Both failing arms show the identical signature `$DFFF run=4 then $FFF0`. The `f=1` straddle
(`$FF00 run=2 then $9FFF`) is the power-on boot sequence and appears in all three — a built-in
negative control.

## What is NOT settled — the actual open question

**Why does compiling DRHOLDBOARD in lengthen the hook enough to cause the slip, when the board
restore loop only runs while `HOLD_ACTIVE != 0` — and `HOLD_ACTIVE` is never written at all on
the v6c ship cart?** (Measured: zero writes to `$6195` across the whole failing run. The hold
never arms; the match dies first.) So the cost is *not* the 256-iteration restore loop. Something
about merely having the block compiled in — code layout, the extra `LDA/BEQ` on every hook ahead
of the mode split, the extra `MATCH_ACTIVE` store site — shifts the timing.

That "merely compiled in" part is what makes the blast radius unknown, and it is why
`DRHOLDBOARD=0` is a mitigation and not an understanding.

## What I would try next, in order

1. **Measure the hook cycle cost directly, per frame class**, HB=1 vs HB=0, on otherwise
   identical carts. Mesen can count cycles between hook entry and exit. If HB=1 is only a few
   dozen cycles fatter, the slip is a threshold effect and the real story is that the hook is
   already at the frame boundary — in which case *any* flag can trigger it and the MMC1 fix is
   mandatory, not optional. That is the single highest-value measurement.
2. **Instrument the main loop's CHR sequence timing**: log the frame offset at which the `$DFFF`
   run starts, HB=1 vs HB=0. The prediction is a distribution shifted later, with the tail
   crossing into the hook's `$FFF0` window. This turns a 1-event anecdote into a rate.
3. **Test the mitigation directly**: add `$8000` bit-7 reset-before-sequence to `_sel` and re-run
   the gate with `DRHOLDBOARD=1`. If board-hold then survives 10+ matches, the owner gets his
   feature back and the fix is proven by the defect it removes. This is the fastest path to
   shipping board-hold again, and it can be done independently of understanding item 1.
4. Only then, if still unexplained, disassemble the emitted hook prologue for both builds and
   diff instruction counts on the path taken when `HOLD_ACTIVE == 0`.

Do **not** re-litigate these — each was closed with evidence:
- the `$61B0` / S2P_TTL scratch collision (static reach analysis + zero runtime writes near the
  crash),
- a branch-range overflow (the assembler asserts `-128 <= rel <= 127`, so an emitting build has
  in-range branches),
- the title blue bars as a v6c regression (v6b/v6c pixel-identical at boot; the bars are on the
  cold-boot draw path only).

## Related, and worth flagging separately

The shipped **v7b prestart cart** (`RECIPE_v7b_prestart_fixfl.json`, md5 `6f6224f2`) carries
`DRHOLDBOARD=1`. If that cart is on the Pocket SD it has the same soft-brick exposure as v6c and
should be treated as suspect until gated.
