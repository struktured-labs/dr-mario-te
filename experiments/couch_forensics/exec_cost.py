"""Execution cost per game: where silicon's landing cleared fewer viruses than the brain's choice would have.

For each placement (classify_tap.py output, brain = HSV): simulate the brain's choice and silicon's actual landing
on the settled board (place + faithful resolve) and count viruses cleared by each. A MISSED CLEAR = brain > actual.
Also flags DRSPAWNEDGE missed-edge candidates: a placement that LOCKS in the top row (horizontal at row 0), and
whether the NEXT pill then went unrotated to that pill's column (the documented missed-edge behaviour).
Usage: python exec_cost.py CLS.jsonl OUT.jsonl
"""
import json
import sys

import analyze_g2 as A
from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V


def vir_cleared(b, pose):
    if pose is None:
        return None
    o, c, cl, row = pose
    bb = b.clone()
    v0 = bb.virus_count()
    if not bb.place_pill(Pill(*cl), ORIENT_H if o == "H" else ORIENT_V, c):
        return None
    bb.resolve()
    return v0 - bb.virus_count()


def main(cls, out):
    R = [json.loads(l) for l in open(cls)]
    rows = []
    for i, r in enumerate(R):
        b = A.board_from_strings(r["S"]["color"], r["S"]["virus"], r["S"]["link"])
        vb = vir_cleared(b, r["hsv"])
        va = vir_cleared(b, r["actual"]) if r["actual_action"] is not None else None
        top_lock = r["actual"][0] == "H" and r["actual"][3] == 0
        nxt = R[i + 1] if i + 1 < len(R) else None
        edge = None
        if top_lock and nxt is not None:
            edge = {"next_k": nxt["k_game"], "next_actual": nxt["actual"], "next_brain": nxt["hsv"],
                    "next_unrotated_to_this_col": nxt["actual"][0] == "H" and nxt["actual"][1] == r["actual"][1]}
        rows.append({"k_game": r["k_game"], "t_spawn": r["t_spawn"], "category": r["category"],
                     "brain_vir": vb, "actual_vir": va, "missed_clear": (vb or 0) > (va or 0) if va is not None else (vb or 0) > 0,
                     "top_row_lock": top_lock, "spawnedge": edge, "hsv": r["hsv"], "actual": r["actual"]})
    with open(out, "w") as fh:
        for q in rows:
            fh.write(json.dumps(q) + "\n")
    mc = [q for q in rows if q["missed_clear"]]
    print(f"{cls}: {len(rows)} placements; brain would clear viruses on {sum((q['brain_vir'] or 0) > 0 for q in rows)}, "
          f"silicon cleared on {sum((q['actual_vir'] or 0) > 0 for q in rows)}; MISSED clears {len(mc)} "
          f"(viruses {sum((q['brain_vir'] or 0) - (q['actual_vir'] or 0) for q in mc)}); by category "
          f"{dict((c, sum(1 for q in mc if q['category'] == c)) for c in set(q['category'] for q in mc))}; "
          f"top-row locks {sum(q['top_row_lock'] for q in rows)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
