#!/usr/bin/env python3
"""POST-HOC DIAGNOSTIC — not part of the registered verdict, run after the fact to
localise WHY the registered same_board prediction (P(seat 0 wins) = 1.000) failed.

same_board equalises the virus boards, but it does NOT remove the second
symmetry-breaker: garbage column phase is keyed on the GLOBAL volley ordinal
(`seed * 7919 + vol` in vs_harness.play_match), so the two seats receive garbage in
DIFFERENT columns and their boards diverge from the first release onward. Every
same_board game had releases (mean 26.3), so none of them was ever in the exact-tie
limit the prediction was about.

This arm severs the attack channel (`garbage=False`), which is the only condition
under which the two seats genuinely cannot diverge and turn order is the sole
remaining asymmetry.
"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_side_asym as R

def _one(seed):
    H = R._STATE["H"]; champ = R._STATE["champ"]
    prev = R._patch_boards(H, 0, "same_board")
    try:
        a = R._wrap(champ, H); b = R._wrap(champ, H)
        r = H.play_match(seed, a, b, level=11, max_pills=300, garbage=False)
    finally:
        if prev is not None: H.VsMatch = prev
    return {"seed": seed, "winner_side": r["winner"], "reason": r["reason"],
            "releases": r["releases"], "pills": r["pills"], "virus": r["virus"]}

if __name__ == "__main__":
    ex = ProcessPoolExecutor(max_workers=10, initializer=R._init_pool)
    rows = list(ex.map(_one, range(53000, 53100)))
    ex.shutdown(wait=True)
    with open("out/diag_firstmover.jsonl", "w") as fh:
        for r in rows: fh.write(json.dumps(r) + "\n")
    from collections import Counter
    print("n =", len(rows))
    print("winner side :", Counter(r["winner_side"] for r in rows))
    print("reasons     :", Counter(r["reason"] for r in rows))
    print("releases>0  :", sum(1 for r in rows if r["releases"] > 0))
    print("identical pills p0==p1 :", sum(1 for r in rows if r["pills"][0] == r["pills"][1]))
    w0 = sum(1 for r in rows if r["winner_side"] == 0)
    print(f"\nP(seat 0 wins) = {w0/len(rows):.4f}   (registered prediction was 1.000)")
