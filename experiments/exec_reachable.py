#!/usr/bin/env python3
"""How many real tucks can the DRIVER'S EXECUTOR actually perform?

The -8.51 pills at L11 (tuck-validated-20260731) was measured with tuck_enum.enumerate(),
which returns the FULL gravity-legal tuck space -- any motion the physics allows. The
shipped executor is far more restricted. From patch_cartridge_copro.py:

    TUCK_C2 = approach column    TUCK_R2 = trigger row
    while $0386 (pill Y, counts UP from the floor) > TUCK_R2 : steer to TUCK_C2
    once $0386 <= TUCK_R2                                    : steer to best_col

i.e. exactly ONE horizontal switch, at one row, with no re-rotation. So the executor can
express a tuck iff:

    the capsule falls in approach column `a` to some row r,
    slides horizontally to final column `c` at row r,
    and then falls straight down in `c` to a rest deeper than a straight drop into `c`.

If the executor covers only part of the measured tuck space, the firmware must publish
ONLY the covered part -- and the honest expected win is the win restricted to that part,
not the headline number. Publishing a tuck the executor cannot perform is worse than
publishing none: the capsule would steer to an approach column and then fail to reach the
target, landing somewhere the search never scored.

Emits: coverage over the 778 real L11 boards, split by whether the tuck kills more viruses
than any straight drop (the STRICT criterion the A/B actually fired on).
"""
import sys, os
ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/tuck", ROOT + "/tmp/endgame", ROOT + "/tmp/combo_term",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)
import tuck_enum as TE
# ★ import EMPTY from fb -- do NOT hardcode. Assuming 0xFF (the value seen in the
# real_boards.txt dump) made every cell read as occupied, every column read as
# blocked, and the script report a clean 0.0%% coverage that looked like a finding.
from fb import FB, ROWS, COLS, EMPTY


def occupied(fb, r, c):
    return fb.col[r * COLS + c] != EMPTY


def rest_row(fb, c, from_r):
    """Fall straight down column c starting at row from_r; return the resting row."""
    r = from_r
    while r + 1 < ROWS and not occupied(fb, r + 1, c):
        r += 1
    return r


def top_empty_run(fb, c):
    """Deepest row reachable by dropping into column c from the top (straight drop)."""
    if occupied(fb, 0, c):
        return None
    return rest_row(fb, c, 0)


def executor_tucks(fb):
    """Cells reachable under the executor's one-switch model.

    Returns {(r, c)} of single-cell rest positions a tuck can reach that a straight drop
    into that same column cannot. Single-cell is the right granularity here: the executor
    steers the capsule as a unit, and we only need to know whether the DESTINATION column's
    rest row is deeper than its straight-drop rest row.
    """
    out = set()
    for c in range(COLS):
        sd = top_empty_run(fb, c)          # None => column blocked at the top
        sd_depth = -1 if sd is None else sd
        for a in (c - 1, c + 1):
            if not (0 <= a < COLS):
                continue
            ra = top_empty_run(fb, a)      # how deep the capsule can get in the approach col
            if ra is None:
                continue
            # slide into c at row ra, then fall
            if occupied(fb, ra, c):
                continue
            rf = rest_row(fb, c, ra)
            if rf > sd_depth:              # genuinely deeper than a straight drop
                out.add((rf, c))
    return out


def full_tuck_cells(fb, pa, pb, fpr=12):
    """Cells the FULL enumerator says a tuck can reach (the space the A/B measured)."""
    # NO bare except here. An earlier version swallowed the exception and reported
    # "0 tucks on every board", which reads as a real finding instead of a broken loader.
    cands = TE.enumerate(fb, pa, pb, mode="gravity", frames_per_row=fpr)
    cells = set()
    tucks = []
    for p in cands:
        if not p.get("is_tuck"):
            continue
        r0, c0, r1, c1 = p["cells"]
        cells.add((r0, c0))
        cells.add((r1, c1))
        tucks.append(p)
    return cells, tucks


def main():
    # Use the PROVEN generator (replays the shipped winner brain) rather than parsing
    # real_boards.txt: that dump is 134 fields/line with an undocumented 6-field header,
    # nothing else on disk reads it back, and a mis-parse here fails SILENTLY as "0 tucks
    # on every board" -- which is exactly how the first version of this script lied to me.
    import argparse
    from yield_real import gen_real_boards
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--every", type=int, default=4)
    a = ap.parse_args()

    pos = list(gen_real_boards(a.games, a.every))
    print(f"positions: {len(pos)} (from {a.games} replayed L11 games)")
    assert pos, "generator produced nothing -- do not interpret zeros below"

    n_board_with_tuck = 0
    n_board_exec_covers = 0
    tot_full = 0
    tot_covered = 0
    for item in pos:
        # gen_real_boards yields dicts: fb, a, b, na, nb, seed, k, virus, occ
        fb, pa, pb = item["fb"], item["a"], item["b"]
        full_cells, tucks = full_tuck_cells(fb, pa, pb)
        if not full_cells:
            continue
        n_board_with_tuck += 1
        ex = executor_tucks(fb)
        covered = full_cells & ex
        tot_full += len(full_cells)
        tot_covered += len(covered)
        if covered:
            n_board_exec_covers += 1

    print(f"\nboards with any gravity-legal tuck : {n_board_with_tuck}")
    print(f"boards where the executor reaches   : {n_board_exec_covers} "
          f"({100.0*n_board_exec_covers/max(1,n_board_with_tuck):.1f}%)")
    print(f"\ntuck-reachable CELLS, full enumerator : {tot_full}")
    print(f"tuck-reachable CELLS, executor model  : {tot_covered} "
          f"({100.0*tot_covered/max(1,tot_full):.1f}%)")
    print("\nInterpretation: the firmware may publish ONLY the executor-covered subset.")
    print("The -8.51 pills headline was measured over the FULL space, so the shippable")
    print("win scales with this coverage -- it is NOT the headline number unless coverage")
    print("is ~100%.")


if __name__ == "__main__":
    main()
