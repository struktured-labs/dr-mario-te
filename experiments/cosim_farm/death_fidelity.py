#!/usr/bin/env python3
"""Champion-decider fidelity vs real RTL, in the NEAR-DEATH regime.

The 100% mid-game result was measured on random-legal playout boards, where the
perturbation gradient (94-98%) shows the chain and #47-stranded terms rarely change the
move. These boards come from the adversary's confirmed kill games: endgame, stack at rows
13-15 of 16, heavy garbage -- the regime those terms specifically target, and the regime
where a mirror divergence would actually cost something.

No extra fast-sim compute: `death_boards.py` recorded the champion's OWN action at each
position while the kill game was being played, so the comparison is against what the fast
sim actually did in that game, not a re-derivation of it.

Reports agreement overall and split by how close to death the position is, because "the
mirror holds until the last few plies" and "the mirror holds throughout" are different
findings.

Usage: death_fidelity.py <decide_compare.json> <death_meta.json>
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

VAR_OF_O4 = (2, 3, 0, 1)                       # cosim.VAR_OF_O4
O4_OF_VAR = tuple(VAR_OF_O4.index(v) for v in range(4))
RING_NAME = ("H", "V", "RH", "RV")
RING_OF_O4 = (3, 1, 0, 2)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    res = json.load(open(sys.argv[1]))
    meta = json.load(open(sys.argv[2]))["meta"]
    rows = res["rows"][res["base"]]
    assert len(rows) == len(meta), f"{len(rows)} RTL rows vs {len(meta)} positions"

    per_seed = {}
    bad = []
    n = ok = ok_col = ok_o4 = 0
    of, orl = Counter(), Counter()
    by_plies_left = {"last 5": [0, 0], "6-15": [0, 0], "16-25": [0, 0]}

    # plies-to-death for each position, within its own game
    last_ply = {}
    for m in meta:
        last_ply[m["seed"]] = max(last_ply.get(m["seed"], -1), m["ply"])

    for r, m in zip(rows, meta):
        fvar, fcol = divmod(int(m["champ_action"]), 8)
        fo4 = O4_OF_VAR[fvar]
        rcol, ro4 = r["col"], r["o4"]
        n += 1
        of[RING_NAME[RING_OF_O4[fo4]]] += 1
        orl[RING_NAME[RING_OF_O4[ro4]]] += 1
        hit = (fcol, fo4) == (rcol, ro4)
        ok += hit
        ok_col += (fcol == rcol)
        ok_o4 += (fo4 == ro4)
        s = per_seed.setdefault(m["seed"], [0, 0])
        s[0] += hit; s[1] += 1
        left = last_ply[m["seed"]] - m["ply"]
        band = "last 5" if left < 5 else ("6-15" if left < 15 else "16-25")
        by_plies_left[band][0] += hit
        by_plies_left[band][1] += 1
        if not hit:
            bad.append({"seed": m["seed"], "ply": m["ply"],
                        "plies_to_death": left,
                        "virus_count": m["virus_count"],
                        "max_height": m["max_height"],
                        "fast": [fcol, fo4], "rtl": [rcol, ro4]})

    print(f"=== champion decider vs real RTL, NEAR-DEATH corpus (n={n}) ===")
    print(f"full (col, orient) : {ok}/{n} = {ok/n:.1%}")
    print(f"column only        : {ok_col}/{n} = {ok_col/n:.1%}")
    print(f"orientation only   : {ok_o4}/{n} = {ok_o4/n:.1%}")
    print("\nper kill game:")
    for s, (h, t) in sorted(per_seed.items()):
        print(f"  seed {s}: {h}/{t} = {h/t:.0%}")
    print("\nby distance to death:")
    for band in ("last 5", "6-15", "16-25"):
        h, t = by_plies_left[band]
        if t:
            print(f"  {band:<7} plies before topout: {h}/{t} = {h/t:.0%}")
    print(f"\norientation mix  fast={dict(of)}  rtl={dict(orl)}")
    if bad:
        print(f"\n{len(bad)} disagreement(s):")
        for b in bad[:12]:
            print(f"  seed {b['seed']} ply {b['ply']} ({b['plies_to_death']} before death) "
                  f"virus={b['virus_count']} height={b['max_height']}  "
                  f"fast={tuple(b['fast'])} rtl={tuple(b['rtl'])}")
    print("\ncontext: same decider on MID-GAME boards = 50/50 = 100%. "
          "This corpus is the regime that number did NOT cover.")

    out = {"n": n, "full": ok, "col": ok_col, "orient": ok_o4,
           "full_frac": ok / n, "per_seed": {str(k): v for k, v in per_seed.items()},
           "by_plies_to_death": by_plies_left, "disagreements": bad,
           "orient_fast": dict(of), "orient_rtl": dict(orl),
           "midgame_reference": {"n": 50, "full": 50, "full_frac": 1.0}}
    dst = "/mnt/data/drmario_cosim/results/death_fidelity.json"
    json.dump(out, open(dst, "w"), indent=1)
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
