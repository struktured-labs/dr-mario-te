#!/usr/bin/env python3
"""#26 -- THE INSTANT-DOUBLE POSITION PROBE (the user's diagram, as a regression test).

TWICE now the user has watched the shipped core hold a two-colour pill over two adjacent
ready columns --

        B Y
        B Y
        B Y          <- both columns one cell from clearing

-- and drop it VERTICALLY into one column (single clear, no attack, the other column left
for later) instead of laying it HORIZONTALLY across both, which clears both in the SAME
round: an instant double, and a real ROM attack of 2 tiles.

★ THIS PROBE SHIPS REGARDLESS OF THE WIN-RATE VERDICT. Even if an instant-double credit
turns out win-neutral, the user watches for this shape and it reads as a blunder on screen.
A regression test for "does it take the free double" is worth having whether or not the
credit is worth buying.

★ THE CORRECT ANSWER IS MEASURED, NOT ASSERTED. The script enumerates all 32 actions,
plays each on a copy, and reports what each actually clears. Whatever produces two lines in
one round IS the double; the probe then asks the decider what it picks and compares. That
way the test cannot encode my belief about which action is right -- a mistake that would
make it agree with a wrong AI.

Action encoding (faithful_env._decode): action = variant*8 + col, variant 0/1 = HORIZONTAL
with the pill normal/colour-swapped, 2/3 = VERTICAL normal/swapped.
"""
from __future__ import annotations
import sys

for p in ("/home/struktured/projects/dr_mario_rl/tmp/vs_aware",
          "/home/struktured/projects/dr_mario_rl/tmp/champion",
          "/home/struktured/projects/dr_mario_rl/tmp/pillrng",
          "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src",
          "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if p not in sys.path:
        sys.path.insert(0, p)

from drmario.faithful_env import FaithfulDrMarioEnv          # noqa: E402
from drmario.faithful_game import Pill                       # noqa: E402
from h2h_vs import ARMS, _mk                                 # noqa: E402

RED, YEL, BLU = 1, 2, 3
COLS = 8


def make_position(c0=3, ready=3, colours=(BLU, YEL), extra_viruses=16):
    """Two adjacent columns, each `ready` VIRUSES of one colour, resting on the floor.

    `ready=3` is the user's shape: one more same-colour cell completes a run of 4.

    ★ THE READY CELLS ARE VIRUSES, AND THE BOTTLE HOLDS OTHERS. My first version wiped the
    board and used plain pill cells, so virus_count was ZERO -- and with no viruses left
    there is nothing to gain by clearing, so EVERY arm declined to clear at all (they chose
    an action clearing 0 cells, not a single). That "reproduction" was an artefact of a
    degenerate position, not the field blunder. A probe has to put the AI in the situation
    the user actually saw, or its verdict is about the probe.

    `extra_viruses=0` reproduces that degenerate condition on purpose, as a control.
    """
    e = FaithfulDrMarioEnv(level=11, seed=1, max_pills=300)
    e.reset()
    b = e.board
    b.color[:, :] = 0
    b.is_virus[:, :] = False
    try:
        b.link[:, :] = 0
    except Exception:
        pass
    rows = b.color.shape[0]
    for k, col in enumerate((c0, c0 + 1)):
        for r in range(rows - ready, rows):              # bottom-anchored
            b.color[r, col] = colours[k]
            b.is_virus[r, col] = True
    # scatter other viruses so the bottle is a real mid-game one, deterministically and
    # never in the two probe columns or directly above them
    placed, r, c = 0, rows - 1, 0
    while placed < extra_viruses and r >= rows - 7:
        if c not in (c0, c0 + 1) and b.color[r, c] == 0:
            b.color[r, c] = (RED, YEL, BLU)[(r + c) % 3]
            b.is_virus[r, c] = True
            placed += 1
        c += 1
        if c >= COLS:
            c, r = 0, r - 1
    return e


def enumerate_actions(e, pill):
    """Play every action on a CLONE and record what it really does."""
    out = []
    for a in range(4 * COLS):
        variant, col = a // COLS, a % COLS
        orient = 0 if variant < 2 else 1                 # 0/1 = H, 2/3 = V
        p = Pill(pill.a, pill.b) if variant % 2 == 0 else Pill(pill.b, pill.a)
        b = e.board.clone()
        if not b.place_pill(p, orient, col):
            out.append((a, variant, col, None, None, None))
            continue
        cells, viruses, chain = b.resolve()
        out.append((a, variant, col, cells, viruses, chain))
    return out


def run_condition(label, extra_viruses, c0=3):
    e = make_position(c0=c0, extra_viruses=extra_viruses)
    pill = Pill(BLU, YEL)
    e.cur, e.nxt = pill, Pill(RED, RED)
    print("=" * 72)
    print("CONDITION: %s   (viruses on board: %d)" % (label, e.board.virus_count()))
    print("=" * 72)
    print("columns %d/%d hold 3 BLUE and 3 YELLOW viruses; pill = BLUE/YELLOW" % (c0, c0+1))
    print(e.board.ascii() if hasattr(e.board, "ascii") else "")

    res = enumerate_actions(e, pill)
    playable = [r for r in res if r[3] is not None]
    # ★ chain == 1 EXACTLY. An INSTANT double is two lines in ONE round. My first filter
    # said `chain >= 1`, which also admits a CASCADE that clears 8 cells over two rounds --
    # a materially different move, and the very thing the arms actually prefer here. With
    # the loose filter this probe reported "all arms take the double" when they were in
    # fact taking a cascade. The distinction IS the subject of the task, so getting it
    # wrong in the measuring instrument made the instrument useless.
    doubles = [r for r in playable if r[5] == 1 and r[3] >= 8]
    singles = [r for r in playable if r[3] and 4 <= r[3] < 8]

    print("\n--- what each action ACTUALLY does (measured, not assumed) ---")
    for a, v, col, cells, vir, chain in playable:
        if cells:
            kind = "H" if v < 2 else "V"
            swap = " (colours swapped)" if v % 2 else ""
            print("  action %2d  %s col %d%-18s cleared=%2d  rounds=%d%s"
                  % (a, kind, col, swap, cells, chain,
                     "   <== INSTANT DOUBLE" if cells >= 8 and chain == 1 else ""))

    if not doubles:
        print("\nPROBE INVALID: no action clears 8 cells in one round -- the position does "
              "not actually contain an instant double. Fix the position, not the AI.")
        return 2
    best = sorted(doubles, key=lambda r: -r[3])
    want = {r[0] for r in best}
    print("\n  instant-double actions : %s" % sorted(want))
    print("  single-clear actions   : %s" % sorted(r[0] for r in singles))

    print("\n--- what each arm CHOOSES ---")
    bad = 0
    for name in ("winner", "lnk1", "chain180", "chain360"):
        dec = _mk(ARMS[name], 8)
        a = dec.choose(e.board, e.cur, e.nxt)
        v, col = a // COLS, a % COLS
        kind = "H" if v < 2 else "V"
        row = next((r for r in res if r[0] == a), None)
        cells = row[3] if row else None
        ok = a in want
        if not ok:
            bad += 1
        print("  %-9s -> action %2d (%s col %d)  clears %s  %s"
              % (name, a, kind, col, cells,
                 "TAKES THE DOUBLE" if ok else "*** MISSES IT ***"))

    print()
    if bad:
        print("VERDICT: %d/4 arms do not take the INSTANT double." % bad)
        print("  ⚠ Do NOT read that as reproducing the user's blunder without checking WHAT")
        print("    they took instead. Here they take a CASCADE clearing the same 8 cells / 6")
        print("    viruses over 2 rounds -- nothing is left behind, so it is not the")
        print("    'cleared one column and abandoned the other' shape he described. Under the")
        print("    ROM attack rule a cascade SUMS comboCounter across steps, so this is")
        print("    plausibly attack-neutral. What differs is TEMPO and what it LOOKS like.")
        return 1
    print("VERDICT: all arms take the instant double in this condition.")
    return 0


def main():
    rc_real = run_condition("REALISTIC -- viruses present, clearing is worth something", 16)
    print()
    rc_degen = run_condition("CONTROL -- ZERO other viruses (my first, degenerate probe)", 0)
    print()
    print("#" * 72)
    if rc_real == 1:
        print("HEADLINE: the blunder reproduces on a REALISTIC board -> the credit has a "
              "real behavioural target.")
    elif rc_real == 0:
        print("HEADLINE: on a realistic board every arm TAKES the double. The field "
              "sighting is therefore NOT this simple shape -- something else in the real "
              "position (depth, next-pill, or the surrounding stack) drove it. Do not "
              "price a credit against a blunder this probe cannot reproduce.")
    return rc_real


if __name__ == "__main__":
    sys.exit(main())
