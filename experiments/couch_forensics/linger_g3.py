"""Why did the LAST high spawn-column virus linger in 9/27 match-1 G3? (RESULT_COUCH_HSV addendum)

For every placement while exactly one virus remains in cols 3-5 at rows <= 8:
  * where it is, and what sits above it in its column (colours, virus/pill), i.e. the burial
  * every legal root candidate (straight drop) and whether the tap mask (P=2) allows it
  * which candidates CLEAR that virus immediately (place + faithful resolve)
  * what the HSV brain chose, and whether it was a clearing move
Usage: python linger_g3.py HSV_ANALYSIS.jsonl OUT.jsonl
"""
import json
import os
import sys

import numpy as np

import analyze_g2 as A
from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cvx"))
import reach_fw_tap as RFT  # noqa: E402
import steer_model as SM  # noqa: E402

GL = {1: "R", 2: "Y", 3: "B"}


def main(inp, out):
    T = [json.loads(l) for l in open(inp)]
    rows = []
    for t in T:
        V = np.array([int(c) for c in t["S"]["virus"]]).reshape(16, 8)
        C = np.array([int(c) for c in t["S"]["color"]]).reshape(16, 8)
        hv = [(r, c) for r in range(9) for c in (3, 4, 5) if V[r, c]]
        if len(hv) != 1:
            continue
        vr, vc = hv[0]
        above = "".join((GL[C[r, vc]].lower() if not V[r, vc] else GL[C[r, vc]]) if C[r, vc] else "." for r in range(0, vr))
        b = A.board_from_strings(t["S"]["color"], t["S"]["virus"], t["S"]["link"])
        cur = tuple(t["cur"])
        mask = RFT.reach_mask_fw(b.color.tolist(), SM.table_threshold(t["k_game"]), 2)
        clearing, allowed_clearing = [], []
        for a in range(32):
            o, col, cl = A.decode(a, cur)
            bb = b.clone()
            ok = bb.place_pill(Pill(*cl), ORIENT_H if o == "H" else ORIENT_V, col)
            if not ok:
                continue
            bb.resolve()
            if not bb.is_virus[vr, vc]:
                clearing.append(a)
                if mask[a]:
                    allowed_clearing.append(a)
        hsv_a = next((a for a in range(32) if A.decode(a, cur)[0] == t["hsv"][0] and A.decode(a, cur)[1] == t["hsv"][1]
                      and list(A.decode(a, cur)[2]) == t["hsv"][2]), None) if t["hsv"] else None
        rows.append({"k_game": t["k_game"], "t_spawn": t["t_spawn"], "virus": [vr, vc, GL[C[vr, vc]]],
                     "above_top_to_virus": above, "cur": [GL[x] for x in cur],
                     "n_clearing": len(clearing), "n_clearing_allowed": len(allowed_clearing),
                     "clearing_moves": [A.decode(a, cur)[:2] + (''.join(GL[x] for x in A.decode(a, cur)[2]),) for a in allowed_clearing],
                     "brain_hsv": t["hsv"], "brain_clears": hsv_a in clearing if hsv_a is not None else None,
                     "actual": t["actual"], "heights": t["heights"]})
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    n = len(rows)
    avail = sum(r["n_clearing_allowed"] > 0 for r in rows)
    print(f"{n} placements with exactly one high spawn-col virus; a mask-allowed immediate clear existed on {avail}; "
          f"brain chose it on {sum(bool(r['brain_clears']) for r in rows)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
