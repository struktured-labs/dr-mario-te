"""Lingering-virus analysis for ONE target virus cell (generalises linger_g3.py).

Per placement while the target virus is present (between T0 and T1):
  column content above it (top -> target), every legal root candidate that CLEARS it immediately
  (place + faithful resolve), how many of those the tap mask (P=2) allows, the HSV brain's choice,
  the widened-region HSV brain's choice (analyze_tap HSVWIDE=1), whether either clears it, and the garbage
  that landed after the placement (cells of S_{k+1} not explained by pill + resolve).
Usage: python linger_cell.py ANALYSIS.jsonl RAW.jsonl ROW COL T0 T1 OUT.jsonl
"""
import json
import os
import sys

import numpy as np

import analyze_g2 as A
import mech_check as MC
from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cvx"))
import reach_fw_tap as RFT  # noqa: E402
import steer_model as SM  # noqa: E402

GL = {1: "R", 2: "Y", 3: "B"}


def action_of(pose, cur):
    if pose is None:
        return None
    for a in range(32):
        o, c, cl = A.decode(a, cur)
        if o == pose[0] and c == pose[1] and list(cl) == pose[2]:
            return a
    return None


def main(an, raw, vr, vc, t0, t1, out):
    T = [json.loads(l) for l in open(an)]
    Rw = {json.loads(l)["k"]: json.loads(l) for l in open(raw)}
    keys = sorted(Rw)
    rows = []
    for t in T:
        if not (t0 <= t["t_spawn"] <= t1):
            continue
        V = np.array([int(c) for c in t["S"]["virus"]]).reshape(16, 8)
        C = np.array([int(c) for c in t["S"]["color"]]).reshape(16, 8)
        if not V[vr, vc]:
            continue
        above = "".join((GL[C[r, vc]] if V[r, vc] else GL[C[r, vc]].lower()) if C[r, vc] else "." for r in range(vr))
        b = A.board_from_strings(t["S"]["color"], t["S"]["virus"], t["S"]["link"])
        cur = tuple(t["cur"])
        mask = RFT.reach_mask_fw(b.color.tolist(), SM.table_threshold(t["k_game"]), 2)
        clear, clear_ok = [], []
        for a in range(32):
            o, col, cl = A.decode(a, cur)
            bb = b.clone()
            if not bb.place_pill(Pill(*cl), ORIENT_H if o == "H" else ORIENT_V, col):
                continue
            bb.resolve()
            if not bb.is_virus[vr, vc]:
                clear.append(a)
                if mask[a]:
                    clear_ok.append(a)
        ah, aw = action_of(t["hsv"], cur), action_of(t.get("hsv_wide"), cur)
        # garbage after this placement
        i = keys.index(t["k"])
        garb = []
        nxt = next((Rw[k] for k in keys[i + 1:] if Rw[k]["landing"] is not None and 0 not in Rw[k]["cur"]), None)
        if nxt is not None and Rw[t["k"]]["landing"] is not None:
            P = MC.after_pill(Rw[t["k"]])
            N = np.array([int(c) for c in nxt["S"]["color"]]).reshape(16, 8)
            garb = [(int(r), int(c), GL[int(N[r, c])]) for r, c in np.argwhere((N > 0) & (P.color == 0))]
        rows.append({"k_game": t["k_game"], "t_spawn": t["t_spawn"], "above": above, "cur": [GL[x] for x in cur],
                     "n_clear": len(clear), "n_clear_allowed": len(clear_ok),
                     "clear_moves": [list(A.decode(a, cur)[:2]) + ["".join(GL[x] for x in A.decode(a, cur)[2])] for a in clear_ok],
                     "hsv": t["hsv"], "hsv_clears": ah in clear if ah is not None else None,
                     "hsv_wide": t.get("hsv_wide"), "hsv_wide_clears": aw in clear if aw is not None else None,
                     "wide_differs": t.get("hsv_wide") != t["hsv"], "actual": t["actual"],
                     "actual_clears": action_of(t["actual"], cur) in clear if t["actual"] else None,
                     "heights": t["heights"], "garbage_after": garb, "category_hint": None})
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    n = len(rows)
    print(f"{n} placements with the target virus ({vr},{vc}) present in [{t0},{t1}]: immediate clear existed on "
          f"{sum(r['n_clear'] > 0 for r in rows)} (mask-allowed {sum(r['n_clear_allowed'] > 0 for r in rows)}); "
          f"HSV took it {sum(bool(r['hsv_clears']) for r in rows)}; wide-HSV takes it {sum(bool(r['hsv_wide_clears']) for r in rows)}; "
          f"wide-HSV differs from HSV on {sum(r['wide_differs'] for r in rows)}; silicon cleared it {sum(bool(r['actual_clears']) for r in rows)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), sys.argv[7])
