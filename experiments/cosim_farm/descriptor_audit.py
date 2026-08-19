#!/usr/bin/env python3
"""Is a published tuck descriptor actually EXECUTABLE, and is it worth executing?

Zero RTL cost: replays descriptors the co-sim already published (decide_compare output)
against the boards they were published for. Answers three things that decide whether a
DRTUCK=1 cart is worth building:

  COHERENT   -- can the pill even enter `best_col` at the published trigger row? The
                driver's executor steers to `best_col` after the trigger, so a descriptor
                whose trigger row is blocked in `best_col` cannot be performed at all.
                tuck_scan.py (v1) enumerates over ALL target columns and keeps the
                globally deepest rest, while the driver takes its destination from
                best_col -- so v1's descriptor and v1's best_col need not describe the
                same column. That is a testable prediction, and this tests it.
  DEEPER     -- does executing it land strictly deeper than a plain drop? That is the
                entire point of a tuck; a descriptor that lands at the same row as the
                drop is a no-op.
  ORIENTATION-- team-lead question: are the divergent picks systematically horizontal?

Usage: descriptor_audit.py <decide_compare.json> <hostdata.txt> [more pairs...]
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROWS, COLS, EMPTY = 16, 8, 0xFF
RING_OF_O4 = (3, 1, 0, 2)
RING_IS_H = (True, False, True, False)
RING_NAME = ("H", "V", "RH", "RV")


def occ(board, r, c):
    return board[r * COLS + c] != EMPTY


def legal(board, r, c, is_h):
    """Can the pill's anchor sit at row r, column c? Anchor = left cell (H) / bottom (V)."""
    if r < 0 or r >= ROWS:
        return False
    if is_h:
        if c + 1 >= COLS:
            return False
        return not occ(board, r, c) and not occ(board, r, c + 1)
    if r - 1 < 0:
        return False
    return not occ(board, r, c) and not occ(board, r - 1, c)


def fall_from(board, col, is_h, start_row):
    if not legal(board, start_row, col, is_h):
        return None
    r = start_row
    while legal(board, r + 1, col, is_h):
        r += 1
    return r


def traverse_ok(board, approach, target, row, is_h):
    """Can the pill actually TRAVEL from the approach column to the target at this row?

    The stricter of two coherence definitions, adopted from the independent fast-sim lane.
    `coherent` (below) asks only whether the pill can ENTER `target` at the trigger row --
    i.e. where it lands IF the maneuver happens. This asks whether the maneuver can happen
    at all: the driver's DAS hold walks the pill one column at a time, so EVERY
    intermediate anchor position must be legal at that row, not just the endpoint.

    For "would a DRTUCK=1 cart execute this", this is the right test and `coherent` is too
    permissive. Both are reported; on the 20 shared boards they give 4/7 and 6/7.
    """
    if approach == 0xFF:
        return False
    step = 1 if target >= approach else -1
    x = approach
    while True:
        if not legal(board, row, x, is_h):
            return False
        if x == target:
            return True
        x += step


def straight_drop(board, col, is_h):
    """Deepest anchor row reachable by a plain drop (entering from the top)."""
    return fall_from(board, col, is_h, 1 if not is_h else 0)


def read_hostdata(path):
    toks = open(path).read().split()
    i = 0
    n = int(toks[i]); i += 1
    out = []
    for _ in range(n):
        i += 6
        out.append([int(toks[i + k], 16) for k in range(128)])
        i += 128
    return out


def audit(res_path, host_path):
    r = json.load(open(res_path))
    boards = read_hostdata(host_path)
    assert len(boards) == r["n_boards"], f"{len(boards)} boards vs {r['n_boards']} decisions"
    base = r["base"]
    out = {}
    for arm, rows in r["rows"].items():
        pub = coh = deeper = same = blocked = 0
        trav = 0
        depth_gain = []
        for i, d in enumerate(rows):
            if d["tcol"] == 0xFF:
                continue
            pub += 1
            ring = RING_OF_O4[d["o4"]]
            is_h = RING_IS_H[ring]
            if traverse_ok(boards[i], d["tcol"], d["col"], d["trow"], is_h):
                trav += 1
            rest = fall_from(boards[i], d["col"], is_h, d["trow"])
            if rest is None:
                blocked += 1
                continue
            coh += 1
            sd = straight_drop(boards[i], d["col"], is_h)
            if sd is None:
                continue
            if rest > sd:
                deeper += 1
                depth_gain.append(rest - sd)
            else:
                same += 1
        out[arm] = {
            "published": pub, "coherent": coh, "blocked_at_trigger": blocked,
            "deeper_than_drop": deeper, "same_as_drop": same,
            "traversable": trav,
            "traversable_frac": trav / pub if pub else None,
            "coherent_frac": coh / pub if pub else None,
            "deeper_frac": deeper / pub if pub else None,
            "mean_rows_gained": (sum(depth_gain) / len(depth_gain)) if depth_gain else 0.0,
        }
    # orientation profile, overall and on the boards where the candidate diverges
    orient = {}
    for arm, rows in r["rows"].items():
        orient[arm] = Counter(RING_NAME[RING_OF_O4[d["o4"]]] for d in rows)
    div = {}
    for arm, c in r["comparisons"].items():
        idx = c["boards_differing"]
        div[arm] = {
            "n_divergent": len(idx),
            "candidate_orient": Counter(RING_NAME[RING_OF_O4[r["rows"][arm][i]["o4"]]] for i in idx),
            "control_orient": Counter(RING_NAME[RING_OF_O4[r["rows"][base][i]["o4"]]] for i in idx),
            "candidate_published_tuck_on_divergent":
                sum(1 for i in idx if r["rows"][arm][i]["tcol"] != 0xFF),
        }
    return {"source": res_path, "n_boards": r["n_boards"], "base": base,
            "descriptor": out, "orientation_all": {k: dict(v) for k, v in orient.items()},
            "divergent": {k: {"n_divergent": v["n_divergent"],
                              "candidate_orient": dict(v["candidate_orient"]),
                              "control_orient": dict(v["control_orient"]),
                              "candidate_published_tuck_on_divergent":
                                  v["candidate_published_tuck_on_divergent"]}
                          for k, v in div.items()}}


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2:
        print(__doc__)
        return 1
    all_res = []
    agg = {}
    for k in range(0, len(args), 2):
        a = audit(args[k], args[k + 1])
        all_res.append(a)
        print(f"\n=== {os.path.basename(a['source'])}  ({a['n_boards']} real-L11 boards) ===")
        print(f"{'arm':<12} {'published':>9} {'coherent':>9} {'travers':>8} "
              f"{'blocked':>8} {'deeper':>7} {'same':>5} {'rows gained':>12}")
        for arm, d in a["descriptor"].items():
            print(f"{arm:<12} {d['published']:>9} "
                  f"{d['coherent']:>9} {d['traversable']:>8} "
                  f"{d['blocked_at_trigger']:>8} "
                  f"{d['deeper_than_drop']:>7} {d['same_as_drop']:>5} "
                  f"{d['mean_rows_gained']:>12.2f}")
            s = agg.setdefault(arm, Counter())
            for kk in ("published", "coherent", "traversable", "blocked_at_trigger",
                       "deeper_than_drop", "same_as_drop"):
                s[kk] += d[kk]
        print("  orientation profile (all boards):")
        for arm, o in a["orientation_all"].items():
            print(f"    {arm:<12} {dict(o)}")
        for arm, v in a["divergent"].items():
            print(f"  divergent boards, {arm}: n={v['n_divergent']}  "
                  f"candidate picks {dict(v['candidate_orient'])}  "
                  f"control picks {dict(v['control_orient'])}  "
                  f"candidate published a tuck on "
                  f"{v['candidate_published_tuck_on_divergent']}/{v['n_divergent']}")

    print("\n################ COMBINED ################")
    print(f"{'arm':<12} {'published':>9} {'coherent':>9} {'blocked':>8} {'deeper':>7} {'same':>5}")
    for arm, s in agg.items():
        p = s["published"]
        print(f"{arm:<12} {p:>9} {s['coherent']:>9} ({s['coherent']/p:5.0%}) "
              f"trav {s['traversable']:>3} ({s['traversable']/p:4.0%}) "
              f"{s['blocked_at_trigger']:>6} {s['deeper_than_drop']:>7} "
              f"({s['deeper_than_drop']/p:4.0%}) {s['same_as_drop']:>5}")
    out = {"per_corpus": all_res, "combined": {k: dict(v) for k, v in agg.items()}}
    dst = "/mnt/data/drmario_cosim/results/descriptor_audit.json"
    json.dump(out, open(dst, "w"), indent=1)
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
