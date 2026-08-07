#!/usr/bin/env python3
"""Emit this rig's chosen placement per board, for a direct diff against the RTL's.

The co-sim asked for exactly this: run the arm-D decider over the same hostdata
corpora it decides on, and hand back `(col, o4)` per board. Diffing those
separates **"the two rigs choose a different tuck"** from **"same tuck,
different outcome"** in one pass, with no games and no RTL time — which is the
cheapest remaining way to attack the arm-D disagreement.

WHAT THIS IS AND IS NOT. This runs the fast sim's OWN enumerator and scorer,
so its answer is "what would an idealised tuck vocabulary pick here", not
"what does `5d010f62` publish". Those are different questions and the diff is
informative precisely because they are: a placement both rigs agree on is one
where the firmware found what an unconstrained search would want.

A FULL descriptor-CONSUMING arm — playing whole games while honouring the
descriptors the RTL published at every ply — is NOT buildable here, and it is
worth being explicit about why rather than leaving it as an unexplained gap:
the descriptor is an RTL *output* computed from the live board, so it exists
only for positions the RTL itself visited. After the first ply where the two
rigs diverge, no published descriptor exists for the board this rig is looking
at. Consuming a descriptor stream therefore requires the RTL in the loop,
which is the co-sim by definition. The per-board diff below is the tractable
substitute: it compares the two deciders on identical positions, which is
exactly the ply-1 slice of the arm that cannot be built.

BOARD DECODE is `calibrate_theta.planes()`, gated by `gates.py`
(`_selftest_hostdata_decode`): colours land in 1..3 and virus counts come out
at 48/48 for L11, which is the level's true starting count — an independent
check that the 0-based → 1-based conversion at this boundary is right.

Usage: export_decisions.py [--out decisions_for_cosim.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import calibrate_theta as CT      # noqa: E402
import exec_model as EM           # noqa: E402
import run_2x2 as R2              # noqa: E402
import reach_root as RR           # noqa: E402

CORPORA = ["/mnt/data/drmario_cosim/gate/hostdata_l11_20.txt",
           "/mnt/data/drmario_cosim/gate/hostdata_l11_hz30.txt"]


def decide_corpus(path, theta):
    import fast_rtl_x as FX
    from fb import FB
    # variant -> o4 is the inverse of _VAR_OF_O4, which is its own inverse
    var_to_o4 = {int(v): o for o, v in enumerate(FX._VAR_OF_O4)}
    cases = CT.read_hostdata_full(path)
    out = []
    for i, (cA, cB, nA, nB, board) in enumerate(cases):
        col, vir = CT.planes(board)
        fb = FB.from_lists(col.tolist(), vir.tolist(), [0] * 128)
        pick, base_action = R2.choose_with_base(fb, col, vir, cA, cB, nA, nB,
                                                "t3", theta)
        rec = {"board": i, "pills_1based": [cA, cB, nA, nB],
               "kind": pick["kind"],
               "n_tuck_cands": int(pick.get("n_tuck_cands", 0)),
               "base_col": int(base_action % 8),
               "base_o4": var_to_o4[int(base_action // 8)]}
        if pick["kind"] == "tuck":
            p = pick["placement"]
            a = EM.tier3_drop_action(p)
            rec.update(col=int(p["col"]), o4=var_to_o4[int(p["variant"])],
                       rest_row=int(p["row"]), cells=list(p["cells"]),
                       margin_over_base=float(pick.get("margin", 0.0)),
                       steered_col=int(a % 8), steered_o4=var_to_o4[int(a // 8)])
        else:
            rec.update(col=int(pick["action"] % 8),
                       o4=var_to_o4[int(pick["action"] // 8)])
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theta", type=float, default=R2.FIRMWARE_THETA)
    ap.add_argument("--out", default=os.path.join(HERE, "results",
                                                  "decisions_for_cosim.json"))
    a = ap.parse_args()

    RR._lazy()
    payload = {"produced_by": "experiments/tuck_value/export_decisions.py",
               "decider": "fast_rtl_x variant('winner') + terms47.g_stranded ws=20, "
                          "tier-3 tuck branch via reach_root._tuck_branch_pick "
                          "with firmware_tier3_ab.firmware_tier_of",
               "theta": a.theta,
               "colour_convention": "pill colours and board plane are 1..3 with 0=EMPTY "
                                    "(faithful-sim native); hostdata's 0-based values are "
                                    "converted on read, verified by virus-count 48/48 at L11",
               "o4_convention": "o4 as the RTL reports it; variant = fast_rtl_x._VAR_OF_O4[o4]",
               "caveat": "this rig's OWN enumerator/scorer, i.e. the idealised vocabulary, "
                         "not what 5d010f62 publishes",
               "corpora": {}}
    for path in CORPORA:
        if not os.path.exists(path):
            print(f"  absent, skipped: {path}")
            continue
        rows = decide_corpus(path, a.theta)
        payload["corpora"][os.path.basename(path)] = rows
        ntuck = sum(1 for r in rows if r["kind"] == "tuck")
        print(f"  {os.path.basename(path):<26} {len(rows):3d} boards, "
              f"tuck chosen on {ntuck} ({ntuck / len(rows):.0%}), "
              f"a tuck candidate existed on "
              f"{sum(1 for r in rows if r['n_tuck_cands'] > 0)}")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(payload, fh, indent=1)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
