#!/usr/bin/env python3
"""GATED FIRE RATE: how many real tuck opportunities survive an eval gate?

The v2 design scores the tuck placement against the straight placement into best_col and
publishes only on strict improvement.  "Deepest wins" alone executes a rest position the
eval never scored -- deeper can bury the capsule or seal the shaft -- so the availability
figure (44/160 boards where a best_col tuck EXISTS) is a CEILING, not a value.  This
prices the gate.

Both sides are scored with the SAME quantity the search uses for a node:

    value = 180*viruses_cleared + 10*cells_cleared + leaf(resulting board)

`leaf_r47` is the python mirror of the shipped RTL leaf (LeafEval.sv S_DONE2), validated
536/536 cell-exact against the pinned Verilator corpus -- so this is leaf-vs-leaf at the
same depth with the same evaluator, never leaf-vs-the-search's-depth-3-value.

TWO-CELL LEGALITY.  The enumerator that produced the 44 is single-cell.  A real capsule is
two cells; placed vertically in best_col it occupies (r-1, c) and (r, c) on entry.  When
the trigger row is fc+1 the cell above it IS the lip, so a vertical capsule cannot enter
there at all.  This script reports the single-cell set (what the co-sim measured) and the
two-cell-legal subset (what a real capsule can do) separately, because the difference is
exactly where this rig and a two-cell rig will disagree.
"""
import os, sys, csv

HERE = os.path.dirname(os.path.abspath(__file__))
CANON = os.environ.get("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(CANON, "fpga", "copro"))
sys.path.insert(0, os.path.join(CANON, "tests"))
from leaf_r47 import leaf_r47                                    # noqa: E402
from nes_d2_golden import _place, _landing                       # noqa: E402
from nes_d3_golden import _cap1_targeted                         # noqa: E402
from tuck_lib import ROWS, COLS, EMPTY, first_occ, rest_row      # noqa: E402

WIN_VALUE = 30000


def value_of(board, offa, offb, ta, tb):
    """node value the search would assign to this placement (imm + leaf)"""
    nb = _place(board, offa, offb, ta, tb)
    cells, vir = _cap1_targeted(nb, offa, offb)
    sco, win = leaf_r47(nb)
    if win:
        return WIN_VALUE + 180 * vir + 10 * cells, True
    return 180 * vir + 10 * cells + sco, False


def scored_placement(board, best_col, o4, ca, cb):
    """The placement the SEARCH actually chose and scored -- the only honest baseline.

    Using a straight VERTICAL drop as the baseline is wrong whenever the search picked a
    horizontal placement (and on 21 of the 44 boards a vertical straight drop into best_col
    is not even legal, because the column is blocked at row 0 or 1).  Orientation and the
    colour swap follow the shipped CMD-4 path: orient = 0 if o4 < 2 else 1,
    (ta, tb) = (cb, ca) if o4 & 1 else (ca, cb).
    """
    orient = 0 if o4 < 2 else 1
    land = _landing(board, orient, best_col)
    if land is None:
        return None
    ta, tb = (cb, ca) if (o4 & 1) else (ca, cb)
    return {"offa": land[0], "offb": land[1], "ta": ta, "tb": tb, "orient": orient}


def tuck_vertical(board, c, two_cell):
    """deepest one-switch tuck into column c; two_cell also requires the UPPER cell to fit"""
    fc = first_occ(board, c)
    if fc == 0:
        return None
    best = None
    for side in (0, 1):
        a = c - 1 if side == 0 else c + 1
        if not (0 <= a < COLS):
            continue
        fa = first_occ(board, a)
        if fa == 0:
            continue
        for r in range(fc, fa):                      # r <= fa-1
            if board[r * COLS + c] != EMPTY:
                continue
            if two_cell and (r - 1 < 0 or board[(r - 1) * COLS + c] != EMPTY):
                continue                             # upper cell cannot enter here
            rf = rest_row(board, c, r)
            if rf > fc - 1 and (best is None or rf > best[0]):
                best = (rf, a, r)
    if best is None:
        return None
    rf = best[0]
    offb = rf * COLS + c
    if two_cell and (offb - COLS < 0 or board[offb - COLS] != EMPTY):
        # no room for the UPPER cell at rest.  This bites exactly when rf == r -- a pocket
        # one cell deep, where the cell above the rest position is the lip itself.  Such
        # pockets are reachable by the single-cell model and NOT by a real vertical capsule.
        return None
    return {"offa": offb - COLS, "offb": offb, "rest": rf,
            "approach": best[1], "trigger": best[2]}


def main():
    rows = open(os.path.join(HERE, "data", "real_sub.txt")).read().split("\n")
    n = int(rows[0])
    boards, cols = [], []
    for i in range(1, n + 1):
        t = rows[i].split()
        cols.append((int(t[0]), int(t[1])))
        boards.append([int(x, 16) for x in t[4:]])
    got = list(csv.DictReader(open(os.path.join(HERE, "results", "out_tuck_real.csv"))))

    for label, two_cell in (("SINGLE-CELL tuck geometry (what the co-sim measured)", False),
                            ("TWO-CELL VERTICAL tuck geometry (what a real capsule can do)", True)):
        avail = horiz = no_geom = fired = suppressed = wins = 0
        gains = []
        for k, row in enumerate(got):
            board = boards[k]
            ca, cb = cols[k]
            bc, o4 = int(row["best_col"]), int(row["best_orient"])
            if o4 > 3:
                o4 = 0
            base = scored_placement(board, bc, o4, ca, cb)
            if base is None:
                continue
            tk = tuck_vertical(board, bc, two_cell)
            if tk is None:
                continue
            avail += 1
            if base["orient"] != 0:
                horiz += 1          # v2 is vertical-only: cannot publish for this capsule
                continue
            sv, swin = value_of(board, base["offa"], base["offb"], base["ta"], base["tb"])
            tv, twin = value_of(board, tk["offa"], tk["offb"], ca, cb)
            if tv > sv:
                fired += 1
                gains.append(tv - sv)
                if twin and not swin:
                    wins += 1
            else:
                suppressed += 1
        gains.sort()
        gated = avail - horiz
        print("%s" % label)
        print("  boards with a best_col tuck        : %d" % avail)
        print("  search chose HORIZONTAL -> vertical-only v2 cannot publish : %d (%.1f%%)"
              % (horiz, 100.0 * horiz / max(1, avail)))
        print("  eligible (vertical scored placement): %d" % gated)
        if gated:
            print("    SURVIVES the strict eval gate    : %d  (%.1f%% of eligible, %.1f%% of available)"
                  % (fired, 100.0 * fired / gated, 100.0 * fired / max(1, avail)))
            print("    suppressed (tuck <= scored)      : %d  (%.1f%% of eligible)"
                  % (suppressed, 100.0 * suppressed / gated))
        if gains:
            print("    gain when it fires               : min %d  median %d  max %d"
                  % (gains[0], gains[len(gains) // 2], gains[-1]))
            print("    of which turn a non-win into a WIN: %d" % wins)
        print()


def sensitivity():
    """Is the survivor count an artifact of WHICH leaf weights we score with?"""
    import leaf_r47 as L
    rows = open(os.path.join(HERE, "data", "real_sub.txt")).read().split("\n")
    n = int(rows[0])
    boards = [[int(x, 16) for x in rows[i].split()[4:]] for i in range(1, n + 1)]
    cols = [(int(rows[i].split()[0]), int(rows[i].split()[1])) for i in range(1, n + 1)]
    got = list(csv.DictReader(open(os.path.join(HERE, "results", "out_tuck_real.csv"))))

    def val(board, offa, offb, ta, tb, leaf):
        nb = _place(board, offa, offb, ta, tb)
        cells, vir = _cap1_targeted(nb, offa, offb)
        sco, win = leaf(nb)
        return (WIN_VALUE if win else sco) + 180 * vir + 10 * cells

    print("LEAF-VARIANT SENSITIVITY (two-cell vertical, eval-gated)")
    for name, leaf in (("R47 shipped (vrdy=24)", L.leaf_r47),
                       ("vrdy=12 variant", L.leaf_vrdy12),
                       ("weekend burial variant", L.leaf_weekend_burial)):
        fired, elig, deltas = 0, 0, []
        for k, row in enumerate(got):
            b = boards[k]; ca, cb = cols[k]
            bc, o4 = int(row["best_col"]), int(row["best_orient"])
            if o4 > 3:
                o4 = 0
            base = scored_placement(b, bc, o4, ca, cb)
            tk = tuck_vertical(b, bc, True)
            if base is None or tk is None or base["orient"] != 0:
                continue
            elig += 1
            sv = val(b, base["offa"], base["offb"], base["ta"], base["tb"], leaf)
            tv = val(b, tk["offa"], tk["offb"], ca, cb, leaf)
            if tv > sv:
                fired += 1
                deltas.append(tv - sv)
        print("  %-24s eligible %2d  fires %d  deltas %s"
              % (name, elig, fired, sorted(deltas)))


if __name__ == "__main__":
    main()
    sensitivity()
