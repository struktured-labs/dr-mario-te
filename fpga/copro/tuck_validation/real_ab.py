#!/usr/bin/env python3
"""Executor A/B on the REAL L11 boards, using the RTL's own best_col from the co-sim.

For every board where the firmware published a tuck, run the DRTUCK=1 driver bytes through
the descent under three descriptors and report where the capsule actually lands relative to
the column the search scored.

  raw    -- the trigger row exactly as the firmware publishes it (board row, 0 = top)
  15-r   -- the same row converted into $0386 units (pill Y, 0 = floor)
  none   -- descriptor suppressed

The driver used here has the h2_start invalidation moved after the pend/delay early-outs;
without that fix the descriptor is wiped before mv_p2 reads it and all three arms are
identical (that is defect 2, demonstrated separately).
"""
import sys, csv

SP = "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tuck"
sys.path.insert(0, SP)
sys.path.insert(0, "/home/struktured/projects/dr-mario-canonical-wt/fpga/copro")
import exec_tuck_sim_fixed as E
from tuck_lib import enum_full, straight_rest, first_occ, COLS, ROWS, EMPTY
from tuck_scan import ref_tuck_scan

rows = open(SP + "/real_sub.txt").read().split("\n")
n = int(rows[0])
boards = []
for i in range(1, n + 1):
    t = rows[i].split()
    boards.append(([int(x, 16) for x in t[4:]], int(t[0]), int(t[1])))

got = list(csv.DictReader(open(SP + "/out_tuck_real.csv")))
print("co-sim cases available: %d / %d" % (len(got), n))

mismatch = 0
tucks = 0
tgt_ne_best = 0
ARMS = ("none", "raw", "fix", "fix_bc")
res = {a: [] for a in ARMS}
offtarget = {a: 0 for a in ARMS}
deeper = {a: 0 for a in ARMS}
bc_has_tuck = 0
detail = []


def enum_for_column(board, c):
    """the same enumeration RESTRICTED to a single target column (design fix candidate)"""
    fc = first_occ(board, c)
    if fc == 0:
        return None
    sd = fc - 1
    best = None
    for side in (0, 1):
        a = c - 1 if side == 0 else c + 1
        if not (0 <= a < COLS):
            continue
        fa = first_occ(board, a)
        if fa == 0:
            continue
        ra = fa - 1
        r = fc
        while r <= ra:
            if board[r * COLS + c] == EMPTY:
                rf = r
                while rf + 1 < ROWS and board[(rf + 1) * COLS + c] == EMPTY:
                    rf += 1
                if rf > sd and (best is None or rf > best[0]):
                    best = (rf, a, r)
            r += 1
    return None if best is None else {"rest": best[0], "approach": best[1], "trigger": best[2]}

for k, row in enumerate(got):
    board = boards[k][0]
    rc, rr = int(row["tuck_col"]), int(row["tuck_row"])
    ec, er = ref_tuck_scan(board)
    if (rc, rr) != (ec, er):
        mismatch += 1
        print("REF MISMATCH case %d: rtl=(%d,%d) ref=(%d,%d)" % (k, rc, rr, ec, er))
    if rc == 0xFF:
        continue
    tucks += 1
    e = enum_full(board)
    best_col = int(row["best_col"])
    best_or = int(row["best_orient"])
    if best_or > 3:
        best_or = 0
    if e["target"] != best_col:
        tgt_ne_best += 1
    sd = straight_rest(board, best_col)
    ebc = enum_for_column(board, best_col)
    if ebc:
        bc_has_tuck += 1
        d_bc = (ebc["approach"], 15 - ebc["trigger"])
    else:
        d_bc = (0xFF, 0xFF)
    for arm, d in (("raw", (rc, rr)), ("fix", (rc, 15 - rr)), ("none", (0xFF, 0xFF)),
                   ("fix_bc", d_bc)):
        col, f, why, live, lrow = E.sim(board, best_col, best_or, d[0], d[1])
        res[arm].append((col, lrow))
        if col != best_col:
            offtarget[arm] += 1
    a_raw, a_fix, a_non, a_bc = res["raw"][-1], res["fix"][-1], res["none"][-1], res["fix_bc"][-1]
    for arm, a in (("raw", a_raw), ("fix", a_fix), ("fix_bc", a_bc)):
        if a[0] == a_non[0] and a[1] > a_non[1]:
            deeper[arm] += 1
    detail.append((k, best_col, e["target"], rc, rr, a_non, a_raw, a_fix, a_bc, sd))

print()
print("boards analysed          : %d" % len(got))
print("RTL vs python reference  : %d/%d match" % (len(got) - mismatch, len(got)))
print("boards publishing a tuck : %d (%.1f%%)" % (tucks, 100.0 * tucks / max(1, len(got))))
print("  enumerator target col != search best_col : %d / %d  (%.1f%%)"
      % (tgt_ne_best, tucks, 100.0 * tgt_ne_best / max(1, tucks)))
print()
print("a tuck EXISTS for best_col itself : %d / %d (%.1f%%)"
      % (bc_has_tuck, tucks, 100.0 * bc_has_tuck / max(1, tucks)))
incid = sum(1 for d in detail if d[9] is not None and d[5][0] == d[1] and d[5][1] > d[9])
print("no-tuck driver ALREADY lands deeper than a straight drop (incidental weave-tuck): "
      "%d / %d (%.1f%%)" % (incid, tucks, 100.0 * incid / max(1, tucks)))
print()
print("%-8s %-28s %s" % ("arm", "landed OFF the scored column", "landed DEEPER than no-tuck (same col)"))
for arm in ARMS:
    print("%-8s %-28s %s" % (arm, "%d / %d (%.1f%%)" % (offtarget[arm], tucks, 100.0 * offtarget[arm] / max(1, tucks)),
                             "%d / %d (%.1f%%)" % (deeper[arm], tucks, 100.0 * deeper[arm] / max(1, tucks))))
print()
print("fix_bc suppresses the descriptor on the %d boards with no tuck for best_col, so the"
      % (tucks - bc_has_tuck))
print("meaningful denominator is the %d boards where a best_col tuck EXISTS:" % bc_has_tuck)
print("   converted into a deeper landing : %d / %d ; landed off-column : %d / %d"
      % (deeper["fix_bc"], bc_has_tuck, offtarget["fix_bc"], bc_has_tuck))
print()
print("first 25 boards with a tuck (case, best_col, enum target, published app/row, none/raw/fix/fix_bc):")
for d in detail[:25]:
    print("  case %4d best_col %d enum_tgt %d pub(%d,%2d)  none%s raw%s fix%s bc%s%s%s%s"
          % (d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8],
             "  RAW-OFF" if d[6][0] != d[1] else "",
             "  FIX-OFF" if d[7][0] != d[1] else "",
             "  BC-OFF" if d[8][0] != d[1] else ""))
