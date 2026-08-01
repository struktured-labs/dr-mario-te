#!/usr/bin/env python3
"""Adversarial board set for the tuck enumerator + the Python reference expectation.

Board is row-major, 16 rows x 8 cols, index = r*8+c, row 0 = TOP.  0xFF = empty.
"""
import sys, json
sys.path.insert(0, "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro")
from tuck_scan import ref_tuck_scan, ROWS, COLS, EMPTY

VIRUS = 0xD0


def blank():
    return [EMPTY] * (ROWS * COLS)


def occ(b, r, c, v=VIRUS):
    b[r * COLS + c] = v


BOARDS = []


def add(name, b, note=""):
    BOARDS.append((name, b, note))


# 1 empty
add("empty", blank(), "no columns occupied at all")

# 2 top row full -> every column first_occ == 0 -> every column skipped
b = blank()
for c in range(COLS):
    occ(b, 0, c)
add("toprow_full", b, "all columns blocked at row 0")

# 3 fully full board
b = [VIRUS] * (ROWS * COLS)
add("board_full", b, "every cell occupied")

# 4 column 0 full top-to-bottom, rest empty
b = blank()
for r in range(ROWS):
    occ(b, r, 0)
add("col0_full", b, "col 0 occupied rows 0-15")

# 5 columns 0 and 7 full (edges)
b = blank()
for r in range(ROWS):
    occ(b, r, 0)
    occ(b, r, 7)
add("col0_col7_full", b, "both edge columns full")

# 6 everything full except column 3 (deep well, no overhang -> no tuck)
b = [VIRUS] * (ROWS * COLS)
for r in range(ROWS):
    b[r * COLS + 3] = EMPTY
add("well_c3_only", b, "single empty column, all neighbours full")

# 7 overhang over column 0 (LEFT EDGE target, only approach is c+1)
b = blank()
occ(b, 8, 0)
add("overhang_c0", b, "col0 lip at row 8, cavity below; approach must be col 1")

# 8 overhang over column 7 (RIGHT EDGE target, only approach is c-1)
b = blank()
occ(b, 8, 7)
add("overhang_c7", b, "col7 lip at row 8, cavity below; approach must be col 6")

# 9 single-cell pocket at (10,3): col3 blocked 9 and 11, everything below 11 full
b = blank()
occ(b, 9, 3)
occ(b, 11, 3)
for r in range(12, ROWS):
    for c in range(COLS):
        occ(b, r, c)
add("pocket_1cell_c3", b, "exactly one reachable cell (10,3) under a lip")

# 10 target has a deep cavity but BOTH approach columns are blocked at row 0
b = blank()
occ(b, 4, 3)
for r in range(ROWS):
    occ(b, r, 2)
    occ(b, r, 4)
add("approach_blocked_c3", b, "cavity under col3 lip, both neighbours full -> must publish NO tuck")

# 11 approach column is blocked ABOVE the trigger rows (shallow approach)
b = blank()
occ(b, 9, 3)          # lip over col3, cavity rows 10..15
occ(b, 3, 2)          # approach col2 blocked at row 3 -> ra = 2 < fc = 9
for r in range(ROWS):
    occ(b, r, 4)      # right neighbour full
add("approach_shallow_c3", b, "approach col cannot reach the trigger rows -> must publish NO tuck")

# 12 THE MIS-LAND CONSTRUCTION: high lip over col3, approach col2 blocked well below
#    the (top-down) trigger row.  Enumerator publishes (approach=2, trigger=3).
b = blank()
occ(b, 2, 3)          # col3 lip at row 2 -> fc=2, cavity rows 3..15
occ(b, 8, 2)          # col2 blocked at row 8 -> capsule rests at row 7 in col2
add("misland_c3_high_lip", b, "trigger row 3 top-down; approach col2 bottoms out at row 7")

# 12b MIS-LAND, uniquely-first: col0 is scanned first and its candidate reaches the floor,
#     so the tie-break keeps it.  Trigger row 3 (top-down) = pill Y 12.  The approach column
#     bottoms out at row 7 (Y 8), which never reaches a RAW trigger of 3.
b = blank()
occ(b, 2, 0)          # col0 lip at row 2 -> fc=2, cavity rows 3..15
occ(b, 8, 1)          # approach col1 blocked at row 8 -> a capsule in col1 rests at row 7
add("misland_c0_lip2", b, "publishes (approach 1, row 3); col1 bottoms out at row 7 = Y 8")

# 12c INERT: a deep lip -> trigger row 13 (top-down) = pill Y 2.  Read raw, the executor
#     switches to the final column at Y 13 (row 2), i.e. immediately, so the tuck never fires.
b = blank()
occ(b, 13, 0)
add("inert_c0_lip13", b, "publishes row 13; raw-compared that is Y 13 = the second row down")

# 13 tie: two tucks resting on the floor at equal depth
b = blank()
occ(b, 8, 1)
occ(b, 8, 5)
add("tie_two_floor_tucks", b, "two candidates both resting at row 15")

# 14 WORST-CASE LATENCY: alternating single blockers at row 1, neighbours fully empty
b = blank()
for c in (0, 2, 4, 6):
    occ(b, 1, c)
add("latency_alt_row1", b, "maximises r-loop x fall-loop: fc=1, ra=15, cavity to the floor")

# 15 same but blockers on the odd columns
b = blank()
for c in (1, 3, 5, 7):
    occ(b, 1, c)
add("latency_alt_row1_odd", b, "mirror of latency_alt_row1")

# 16 every column has a lip at row 1 with an empty column between -- 3 targets, deep falls
b = blank()
for c in (0, 3, 6):
    occ(b, 1, c)
add("latency_lip3", b, "three deep targets, both approaches empty to the floor")

# 17 dense board with a JAGGED surface -- a tuck needs the approach column open BELOW the
#    target's lip, which a flat-topped stack never gives, so the surface is staggered.
b = blank()
COLMAP = {
    0: [6] + list(range(10, ROWS)),
    1: list(range(12, ROWS)),
    2: [2] + list(range(13, ROWS)),
    3: list(range(8, ROWS)),
    4: [5] + list(range(9, ROWS)),
    5: list(range(11, ROWS)),
    6: [3] + list(range(14, ROWS)),
    7: list(range(7, ROWS)),
}
for c, rs in COLMAP.items():
    for r in rs:
        occ(b, r, c)
add("dense_jagged", b, "dense jagged stack, lips over deep cavities on cols 0/2/4/6")

# 18 staircase (every column a different depth, lips everywhere)
b = blank()
for c in range(COLS):
    occ(b, 2 + c, c)
add("staircase", b, "descending lips, each column open above its lip")

# 19 lip at row 1 over EVERY column (approach always ra=0 -> no candidate)
b = blank()
for c in range(COLS):
    occ(b, 1, c)
add("all_lip_row1", b, "every approach bottoms out at row 0 -> no tuck")

# 20 deep well col 0 reachable only from col 1, col 1 empty
b = blank()
for r in range(ROWS):
    for c in range(1, COLS):
        occ(b, r, c)
for r in range(ROWS):
    b[r * COLS + 0] = EMPTY
b[0 * COLS + 1] = EMPTY
b[1 * COLS + 1] = EMPTY
add("well_c0_edge", b, "col0 open, col1 open only at the top two rows")


def main():
    out = sys.argv[1]
    meta = []
    with open(out, "w") as f:
        f.write("%d\n" % len(BOARDS))
        for name, b, note in BOARDS:
            tc, tr = ref_tuck_scan(b)
            meta.append({"name": name, "note": note, "ref_tuck_col": tc, "ref_tuck_row": tr})
            # capsule colours: keep them constant so the search is comparable
            f.write(" ".join(["0", "1", "2", "0"] + ["%02x" % x for x in b]) + "\n")
    with open(out + ".meta.json", "w") as f:
        json.dump(meta, f, indent=1)
    for m in meta:
        print("%-24s ref=(col %3d, row %3d)  %s" % (m["name"], m["ref_tuck_col"], m["ref_tuck_row"], m["note"]))


if __name__ == "__main__":
    main()
