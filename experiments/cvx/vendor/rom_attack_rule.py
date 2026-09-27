#!/usr/bin/env python3
"""THE ROM-TRUE VS ATTACK RULE, cited to the disassembly. This is the frozen trigger.

Source tree: `dr-mario-mods-wt/driver-nav/tmp/refs/dr-mario-disassembly`
(the labelled disassembly; `build_config.asm` has ver_revA=1 -- none of the listed revA
deltas touch attack logic. Line numbers below are that tree's .asm files; the `optimize`
switch changes only step NUMBERING, never the control flow described here.)

★ THE MODEL WE HAD WAS WRONG IN THREE INDEPENDENT WAYS. All three are corrections, not
confirmations:

  (1) CASCADES DO ATTACK.  Our model: ">=2 distinct lines in the SAME clear step".
      ROM: `currentP_comboCounter` is incremented ONCE PER MATCHED RUN
      (game_logic.asm:1176 horizontal, :1623 vertical) and is NOT reset anywhere inside
      the cascade. The cascade loop is driven by `updateField`, which at
      @finishedUpdatingField (game_logic.asm:1474-1485) re-enters `checkDrop` whenever
      `currentP_matchFlag` is set, and `resetMatchFlag` (:1495) clears only the MATCH
      FLAG, never the combo counter. `resetCombo` (:37, pillPlacedStep 0) resets
      `scoreMultiplier`, NOT `comboCounter`, and is reached only once the cascade has
      ALREADY ended (via `resetPillPlacedStep`, :197).
      The counter is read and cleared exactly once, in `checkComboCounterForAttack`
      ($9C03, :2874-2888), AFTER the whole cascade finishes.
      ⇒ lines cleared in DIFFERENT cascade steps SUM. A cascade of two singles gives
        comboCounter=2 >= attackSize_min and SENDS GARBAGE.
      ⇒ `chain_mode="all"` is ROM-true; `chain_mode="first"` (the current default) is wrong.

  (2) MORE LINES = MORE TILES, 2/3/4 -- not a flat 2.
      `checkComboCounterForAttack`: attackSize += comboCounter (it ACCUMULATES; it is
      cleared only on release, :2984-2988). `checkReleaseAttack` ($9C1B, :2895-2993)
      branches on the size: ==2 -> 2 tiles, ==3 -> 3 tiles, anything else >=4 -> 4 tiles
      (the `cmp #$03 / bne @attackSize_4` fallthrough means 5,6,... all deliver 4).

  (3) ★ COLUMNS 0 AND 4 ARE NOT IMMUNE.  Our model: pairs {1,5}/{2,6}/{3,7} only.
      ROM, size 2: `lda frameCounter / and #attackSize_2_pos` with attackSize_2_pos=$03
      ⇒ start in {0,1,2,3}; then `rept attackSize_2_gap+1` inys with gap=$03 ⇒ +4.
      ⇒ pairs {0,4}, {1,5}, {2,6}, {3,7}. **{0,4} is one of the four.**
      size 3: start = frameCounter & $03, step +2 (gap=$01) ⇒ {s, s+2, s+4}.
      size 4: start = frameCounter & $01, step +2          ⇒ {s, s+2, s+4, s+6}.
      Constants: drmario_constants.asm:17-24. frameCounter = $43 (ram_zp.asm:42).

OTHER ROM FACTS THE HARNESSES SHOULD CARRY:
  * Garbage is written to ROW 0 (`sta (currentP_fieldPointer),Y` after the low byte of
    the field pointer is zeroed at :2897; Y is the column 0..7), as tiles
    `attackColors[i] | singleHalfPill` ($80, constants.asm:215) -- unlinked singles.
  * The write is UNCONDITIONAL: nothing checks the target cell is empty, so garbage
    OVERWRITES an occupied top row.
  * Colours: `updateAttackColor` ($945B, :1546-1557) stores the matched run's starting
    colour at attackColors[comboCounter-1], and only while comboCounter <= 4
    (`cmp #attackSize_max+1 / bcs exit`). attackColors is never cleared, so an attack
    whose size accumulated across placements can ship STALE colours in the high slots.
  * TIMING: the attack lands on the RECEIVER's own `action_checkAttack`
    (nextAction=$02, jump table :2818-2826) -- i.e. after the receiver's next placement,
    not instantly. `checkReleaseAttack` then sets nextAction=pillPlaced so the garbage
    settles through the normal cascade -- meaning RECEIVED GARBAGE CAN ITSELF CLEAR LINES
    AND COUNTER-ATTACK.
  * A run longer than 4 counts ONCE: after a match the scan resumes at `fieldPos_last`
    (:1234-1240), so a 5-in-a-row is one increment. An L/T shape counts TWICE, because
    `checkHorMatch` and `checkVerMatch` are separate pillPlacedStep entries (:27-28).
  * `attackSize_min = $02` is the only threshold; a single line never attacks.

WHY THE EARLIER EMPIRICAL NULL DID NOT CATCH (1): selfplay-opt measured chain_mode
first|all making zero difference at L11 (16/16 attacks identical). That is consistent with
this correction -- it says multi-step cascades are RARE at L11, not that the rule is
"first". Rarity is not confirmation.

★★ RECONCILIATION -- THE ORIGINAL `cells >= 7` PROXY WAS RIGHT ALL ALONG.
Scored against the ROM rule as ground truth (rule_delta.py, 120 L11 games, 6078 clearing
placements):
    cells >= 7  (as DOCUMENTED)     TP 918  FP  1  FN   0   precision 99.9%  recall 100.0%
    cells >= 9  (as IMPLEMENTED)    TP 216  FP  0  FN 702   precision 100%   recall  23.5%
    simultaneous-only (line-exact)  137 of 918                              recall  14.9%
Not a coincidence: one run is >=4 cells, so `cells >= 7` is an algebraic near-equivalent of
`sum(runs) >= 2`, and BOTH sum over the whole cascade. Its only failure mode is a SINGLE
run of >=7 cells (comboCounter 1, no attack) -- which is exactly the single FP above.
So this lane went three steps in the WRONG direction: the documented proxy was ROM-true;
an off-by-2 made the SHIPPED test `cells >= 9`, silently dropping 76% of real attacks; and
the "line-accurate" replacement fixed the off-by-2 but adopted the simultaneous-only model,
landing at 14.9% recall -- worse than the bug it replaced. Each step was validated against
the previous wrong model instead of against the ROM.

★★ CONFIRMED ON THE REAL ROM IN MESEN (mesen/attack_probe.lua; logs in mesen/out/).
Boards injected into P1 with the cascade forced via p1_pillPlacedStep=0 / p1_nextAction=1,
so the exact code path under test runs with no pill physics involved:

  A  cascade of two SINGLE lines     comboCounter 1 -> 2 (37 frames apart, ACROSS the two
                                     clear steps, never reset), attackSize 2, and GARBAGE
                                     DELIVERED to P2 at columns {3,7}.
                                     => simultaneous-only is REFUTED on the ROM itself.
  B  true simultaneous double        comboCounter 2, attackSize 2, garbage {3,7}. Control.
  C  one run then TWO after gravity   comboCounter 1 -> 3 (per-RUN increments), attackSize
                                     3, THREE tiles at {1,3,5} = size-3 {s, s+2, s+4}.

★ ALL FOUR size-2 phases observed on the ROM: {0,4}, {1,5}, {2,6}, {3,7}. **{0,4} -- the
pair the old model called IMMUNE -- was produced deterministically twice** by pinning
frameCounter ($43) during the watch phase (AP_PINFC): pin 3 -> ROM reads 4 -> 4&3=0 ->
{0,4}; pin 7 -> reads 8 -> 8&3=0 -> {0,4}. Pins 0 and 4 both read 1 and both gave {1,5}.
That also pins the formula exactly: s = frameCounter & 3, sampled at RELEASE time (the
ROM increments $43 once more within the frame after the pin), NOT when the clear happened.

★ MESEN GOTCHA (cost one silent run): `emu.write` takes THREE args (addr, value, type).
A 4-arg call -- the natural copy of the 4-arg `emu.read` -- raises "too many parameters"
INSIDE the callback and silently kills it for the rest of the run. It presents as "the
script did nothing at all".
"""
from __future__ import annotations

# ★ HARNESS_REV: stamp this into every results file produced by a harness that uses this
# rule. It is how a number is traced to a trigger revision. If a result carries no rev, or
# an older one, it predates the ROM-true trigger and its attack rate is NOT comparable:
#   (no stamp / pre-2026-08-01) -- either the simultaneous-only rule (~14.9% of real
#   attacks seen) or the shipped `cells >= 9` off-by-2 (~23.5%). See the module docstring.
HARNESS_REV = "rom-attack-2026-08-01"

# The mechanics that must accompany the trigger for a harness to be FULLY ROM-true. A
# harness that has the trigger but not these should stamp the rev and list what it lacks,
# so a half-upgraded harness cannot silently pass as complete.
REQUIRED_MECHANICS = (
    "tile_table_234",        # 2/3/4 tiles by attackSize, not flat 2
    "column_phases_incl_04",  # {0,4} is reachable; columns 0 and 4 are NOT immune
    "row0_unconditional",    # garbage overwrites an occupied top row
    # ★ gravity_settle was MISSING FROM THIS VOCABULARY and that is exactly how the
    # floating-garbage bug hid: a harness could list every other mechanic, stamp itself
    # honestly, and still hang garbage at row 0. `resolve()` is clear-driven and returns
    # before _apply_gravity when nothing clears, so delivery MUST settle explicitly.
    # A gap that is not in the vocabulary cannot appear in a MISSING list.
    "gravity_settle",        # delivered garbage falls; never left floating at row 0
    "receiver_timing",       # lands on the RECEIVER's next checkAttack, not instantly
    "counter_attack",        # received garbage can itself clear and counter-attack
)


def stamp(mechanics=()):
    """Return the provenance string for a results file. `mechanics` is what the caller
    actually implements; anything missing from REQUIRED_MECHANICS is named explicitly."""
    missing = [m for m in REQUIRED_MECHANICS if m not in mechanics]
    if not missing:
        return HARNESS_REV + " (complete)"
    return HARNESS_REV + " (trigger only; MISSING: " + ",".join(missing) + ")"


# --- constants, verbatim from defines/drmario_constants.asm:15-24, 215 -----------------
MATCH_LENGTH      = 4      # match_length      = $04
ATTACK_SIZE_MIN   = 2      # attackSize_min    = $02
ATTACK_SIZE_MAX   = 4      # attackSize_max    = $04
ATTACK_2_POS      = 0x03   # attackSize_2_pos  = $03  -> frameCounter & 3
ATTACK_3_POS      = 0x03   # attackSize_3_pos  = $03
ATTACK_4_POS      = 0x01   # attackSize_4_pos  = $01  -> frameCounter & 1
ATTACK_2_GAP      = 0x03   # attackSize_2_gap  = $03  -> stride gap+1 = 4
ATTACK_3_GAP      = 0x01   # attackSize_3_gap  = $01  -> stride 2
ATTACK_4_GAP      = 0x01   # attackSize_4_gap  = $01  -> stride 2
SINGLE_HALF_PILL  = 0x80   # singleHalfPill    = $80
ROW_SIZE          = 8      # rowSize           = $08


def combo_from_cascade(lines_per_step) -> int:
    """ROM `comboCounter` after a placement: the SUM over every cascade step.

    game_logic.asm:1176/:1623 increment per matched run; nothing in the cascade loop
    resets it (:1474-1485 re-enters checkDrop, :1495 clears only matchFlag), and
    checkComboCounterForAttack (:2874) consumes it once the cascade has ended."""
    return int(sum(lines_per_step))


def attack_size(combo: int, pending: int = 0) -> int:
    """checkComboCounterForAttack (:2874-2888): below the minimum the counter is dropped;
    otherwise it ACCUMULATES onto whatever is already pending for the opponent."""
    if combo < ATTACK_SIZE_MIN:
        return pending
    return pending + combo


def garbage_columns(size: int, frame_counter: int) -> list:
    """checkReleaseAttack (:2895-2993). Returns the row-0 columns that receive a tile.

    ★ size 2 can select {0,4} -- columns 0 and 4 are NOT immune."""
    if size < ATTACK_SIZE_MIN:
        return []
    if size == 2:
        s = frame_counter & ATTACK_2_POS
        return [s, s + ATTACK_2_GAP + 1]
    if size == 3:
        s = frame_counter & ATTACK_3_POS
        st = ATTACK_3_GAP + 1
        return [s, s + st, s + 2 * st]
    s = frame_counter & ATTACK_4_POS          # size >= 4 all land here (cmp #$03 / bne)
    st = ATTACK_4_GAP + 1
    return [s, s + st, s + 2 * st, s + 3 * st]


def garbage_tiles(size: int, frame_counter: int, attack_colors) -> list:
    """[(column, tile_byte)] for row 0. tile = colour | singleHalfPill, unlinked."""
    cols = garbage_columns(size, frame_counter)
    return [(c, (attack_colors[i] | SINGLE_HALF_PILL)) for i, c in enumerate(cols)]


# ------------------------------------------------------------------------ selftest
def selftest() -> bool:
    ok = True

    # (1) a two-step cascade of SINGLES attacks -- the correction that changes behaviour
    ok &= combo_from_cascade([1, 1]) == 2
    ok &= attack_size(combo_from_cascade([1, 1])) == 2
    ok &= attack_size(combo_from_cascade([1])) == 0          # a lone single never attacks
    print(f"  cascade [1,1] -> combo {combo_from_cascade([1,1])}, "
          f"attackSize {attack_size(combo_from_cascade([1,1]))}  (old model: NO attack)")

    # (2) tile count tracks line count, and >=4 saturates at 4
    sizes = {n: len(garbage_columns(n, 0)) for n in (2, 3, 4, 5, 6)}
    ok &= sizes == {2: 2, 3: 3, 4: 4, 5: 4, 6: 4}
    print(f"  tiles by attackSize: {sizes}  (old model: flat 2)")

    # (3) columns 0 and 4 are reachable
    pairs = sorted(tuple(garbage_columns(2, f)) for f in range(4))
    ok &= (0, 4) in pairs and pairs == [(0, 4), (1, 5), (2, 6), (3, 7)]
    print(f"  size-2 column pairs over frameCounter&3: {pairs}")
    print(f"  size-3: {[garbage_columns(3, f) for f in range(4)]}")
    print(f"  size-4: {[garbage_columns(4, f) for f in range(2)]}")

    # every generated column must be inside the bottle
    for n in (2, 3, 4, 5):
        for f in range(4):
            ok &= all(0 <= c < ROW_SIZE for c in garbage_columns(n, f))

    print(f"\n  SELFTEST {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if selftest() else 1)
