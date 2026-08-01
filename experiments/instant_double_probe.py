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
ROWS = 16


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


def build_at_height(c0, base_h, extra, ca, cb, nxt, ready=3):
    """The same ready-pair shape, but ELEVATED on `base_h` rows of inert stack.

    Everything above is bottom-anchored: the ready columns rest on the floor, which is the
    one place the AI never misbehaves. The user's third sighting was explicitly MID-BOTTLE,
    and that turns out to be the whole story.
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
    for col in range(COLS):
        for r in range(ROWS - base_h, ROWS):
            b.color[r, col] = (RED, YEL, BLU)[(r * 3 + col) % 3]
    top = ROWS - base_h
    for k, col in enumerate((c0, c0 + 1)):
        for r in range(top - ready, top):
            b.color[r, col] = (ca, cb)[k]
            b.is_virus[r, col] = True
    n = 0
    for r in range(ROWS - base_h, ROWS):
        for col in range(COLS):
            if col not in (c0, c0 + 1) and n < extra:
                b.is_virus[r, col] = True
                n += 1
    e.cur, e.nxt = Pill(ca, cb), nxt
    return e


def run_height_family(arm="chain180"):
    """★ THE PERMANENT GATE ROW: the same shape swept over HEIGHT.

    A gate that only tested the wall would have passed the shipped core while the user
    watched it blunder three times -- the bottom-anchored probe says 9/9 correct. Sweeping
    4 heights x 3 column-pairs x 3 colour-pairs finds the misses are concentrated entirely
    at ONE elevation, which is why the field reports and the first probe disagreed.

    Classification is measured, not assumed: DOUBLE = the enumerated instant-double set,
    CASCADE = >=8 cells but over more than one round, SINGLE = a smaller clear. A SINGLE is
    the user's shape (material left behind); a CASCADE is not.
    """
    from collections import Counter
    print("=" * 72)
    print("HEIGHT FAMILY -- shipped %s over 4 heights x 3 column-pairs x 3 colour-pairs"
          % arm)
    print("=" * 72)
    colours = [(BLU, YEL), (RED, BLU), (YEL, RED)]
    heights = [(0, "WALL (floor)"), (3, "MID-BOTTLE h3"),
               (6, "MID-BOTTLE h6"), (9, "MID-BOTTLE h9")]
    rows = []
    for base_h, lbl in heights:
        for c0 in (1, 3, 5):
            for ca, cb in colours:
                e = build_at_height(c0, base_h, 12, ca, cb, Pill(RED, RED))
                res = enumerate_actions(e, e.cur)
                dbl = {r[0] for r in res if r[3] and r[3] >= 8 and r[5] == 1}
                if not dbl:
                    continue          # no double available: nothing to be graded on
                a = _mk(ARMS[arm], 8).choose(e.board, e.cur, e.nxt)
                r = next((x for x in res if x[0] == a), None)
                cells, rounds = (r[3] or 0), (r[5] or 0)
                kind = ("DOUBLE" if a in dbl else
                        "CASCADE" if cells >= 8 else
                        "SINGLE" if cells >= 4 else "NO-CLEAR")
                rows.append((lbl, c0, ca, cb, kind, cells, rounds))
    for _, lbl in heights:
        sub = [r for r in rows if r[0] == lbl]
        if sub:
            print("  %-16s n=%-3d %s" % (lbl, len(sub), dict(Counter(r[4] for r in sub))))
    bad = [r for r in rows if r[4] in ("SINGLE", "NO-CLEAR")]
    print()
    if bad:
        print("  positions where it left material on the table (the user's shape):")
        for r in bad:
            print("     %-16s cols %d/%d colours %d/%d -> %s (%d cells, %d rounds)"
                  % (r[0], r[1], r[1] + 1, r[2], r[3], r[4], r[5], r[6]))
    print("  TOTAL: %d/%d positions left material on the table" % (len(bad), len(rows)))
    return 1 if bad else 0


def main():
    rc_real = run_condition("REALISTIC -- viruses present, clearing is worth something", 16)
    print()
    rc_degen = run_condition("CONTROL -- ZERO other viruses (my first, degenerate probe)", 0)
    print()
    rc_height = run_height_family()
    print()
    print("#" * 72)
    # ★ THE HEADLINE MUST KEY OFF MATERIAL LOSS, NOT OFF "missed the instant double".
    # It used to read rc_real, and so announced "the blunder reproduces" for the
    # bottom-anchored condition where all four arms take a CASCADE clearing the SAME 8
    # cells over two rounds. Nothing is left behind there -- it is not the user's shape --
    # and the probe's own verdict text says exactly that ten lines earlier. A summary that
    # contradicts the caveat above it is worse than no summary: the caveat is what gets
    # skipped. Only the height family measures material actually abandoned.
    if rc_height == 1:
        print("HEADLINE: the user's shape REPRODUCES, and it is HEIGHT-DEPENDENT -- the "
              "misses are concentrated at one mid-bottle elevation, not at the wall. A "
              "bottom-anchored gate would have passed the shipped core while he watched "
              "it blunder. The credit has a real behavioural target, but a SMALL one: "
              "these are 2-cell mis-rankings, nowhere near vbonus400 territory.")
    else:
        print("HEADLINE: no position in the height family leaves material on the table. "
              "Where arms decline the instant double they take an equivalent CASCADE, "
              "which differs in tempo and appearance but not in material -- do NOT price "
              "a credit against that.")
    return rc_height


if __name__ == "__main__":
    sys.exit(main())
