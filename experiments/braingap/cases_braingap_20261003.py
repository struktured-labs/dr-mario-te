#!/usr/bin/env python3
"""Bank the per-board brain-gap CASES: every 10/03 couch board (G2/G3/G4) where the python sim brain's pick differs
from the copro's final (Verilator co-sim of RTL 3b164c7 + fw 1488e158) and the co-sim did not commit a tuck.

Per case: board, pills, virus count, max height, late-flip category (G2), python pick / silicon pick, the root values
of both picks under the python brain and under the silicon-faithful brain (Leaf6FwDecider, value-exact vs py65 of
the shipped image), their eh add-ons (python: 24*excav + 40*hang on the link-aware child; firmware: 24*excav + R4 hang
on the soft b1), cells cleared, and the CAUSE BUCKET from the switch tests:
  R4-hang    python + hang alone reproduces silicon, and firmware without hang does not
  soft-b1    python + ehb1 alone reproduces silicon, and firmware without ehb1 does not
  either     either single switch alone reproduces silicon
  joint      neither alone; hang + ehb1 together does
  tie-break  only the root evaluation order (K-descending, first max) reproduces silicon
Usage: cases_braingap_20261003.py OUT.jsonl
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlengine_braingap_20261003 as E  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as F  # noqa: E402
import mirror_braingap_20261003 as M  # noqa: E402
import numpy as np  # noqa: E402

CF = E.H16 + "/experiments/couch_forensics"
LF = "/home/struktured/projects/dr-mario-lateflip-wt/experiments/lateflip"
sys.path.insert(0, CF)
O4_OF_VAR = (2, 3, 0, 1)
OFF = dict(veto=0, hang=0, ehb1=0, ehnp=0, wrap=0, order=0)
FWS = dict(veto=1, hang=1, ehb1=1, ehnp=1, wrap=1, order=1)


def phys(a, cur):
    var, col = a // 8, a % 8
    x, y = cur
    return {0: ("H", col, (x, y)), 1: ("H", col, (y, x)), 2: ("V", col, (x, y)), 3: ("V", col, (y, x))}[var]


def main():
    out = sys.argv[1]
    import analyze_g2 as A
    import fast_rtl_x as FX
    import cascade_chain_x as C
    from drmario.faithful_game import Pill
    from impact_braingap_20261003 import immediate
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)
    mk = lambda sw: F.Leaf6FwDecider(w, fl, sw=sw, **kw)  # noqa: E731
    D = {"py": mk(OFF), "fw": mk(FWS), "py+hang": mk(dict(OFF, hang=1)), "py+ehb1": mk(dict(OFF, ehb1=1)),
         "py+hang+ehb1": mk(dict(OFF, hang=1, ehb1=1)), "fw-hang": mk(dict(FWS, hang=0)),
         "fw-ehb1": mk(dict(FWS, ehb1=0)), "py+order": mk(dict(OFF, order=1))}
    n = 0
    with open(out, "w") as fh:
        for game in ("G2", "G3", "G4"):
            if game == "G2":
                Q = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))}
            else:
                Q = {q["p"]: q for q in map(json.loads, open(os.path.join(CF, "cases_dist60_20261003.jsonl")))
                     if q.get("game") == game}
            for l in open(os.path.join(LF, f"pubtrace_{game}_fw1488e158.jsonl")):
                t = json.loads(l)
                if t.get("tuck") not in (None, [255, 255]):
                    continue
                p = t["p"]; q = Q[p]
                cur, nxt = tuple(q["cur"]), tuple(q["nxt"])
                b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
                sil = O4_OF_VAR[t["final"][1]] * 8 + t["final"][0]
                acts = {k: d.choose(b.clone(), Pill(*cur), Pill(*nxt), p) for k, d in D.items()}
                eq = {k: phys(a, cur) == phys(sil, cur) for k, a in acts.items()}
                if eq["py"]:
                    continue
                vpy = D["py"].vals.copy(); vfw = D["fw"].vals.copy()
                D["py"].choose(b.clone(), Pill(*cur), Pill(*nxt), p); vpy = D["py"].vals.copy()
                D["fw"].choose(b.clone(), Pill(*cur), Pill(*nxt), p); vfw = D["fw"].vals.copy()
                a_py = acts["py"]
                # silicon's pick as a root action of the same physical placement (doubles: either member)
                sil_a = sil if vpy[sil] > -(1 << 39) else next(a for a in range(32) if phys(a, cur) == phys(sil, cur)
                                                                and vpy[a] > -(1 << 39))
                nes, cA, cB, nA, nB = E.parse_upload(t["upload"])
                ca, cb = cA & 3, cB & 3
                root = E.dec(nes)

                def eh(a):
                    o4 = O4_OF_VAR[a // 8]; col = a % 8
                    nd = M._node(root, o4, col, ca, cb, E.w6_of(0), 1)
                    c1 = E.enc(*nd["child"])
                    sb = M.soft_b1(nes, o4, col, ca, cb)
                    return dict(py=24 * M.g_excav_nes(c1) + M.hang_credit_nes(c1, 0),
                                fw=24 * M.g_excav_nes(sb) + M.hang_credit_nes(sb, 1))
                if eq["py+hang"] and eq["py+ehb1"]:
                    bucket = "either"
                elif eq["py+hang"] and not eq["fw-hang"]:
                    bucket = "R4-hang"
                elif eq["py+ehb1"] and not eq["fw-ehb1"]:
                    bucket = "soft-b1"
                elif eq["py+hang+ehb1"]:
                    bucket = "joint"
                elif eq["py+order"]:
                    bucket = "tie-break"
                else:
                    bucket = "other"
                row = dict(game=game, p=p, S=q["S"], cur=cur, nxt=nxt, vc=t["vc"], maxh=max(t["heights"]),
                           category=q.get("category"), upload=t["upload"], python_action=a_py, silicon_action=sil,
                           python_value=dict(python_pick=int(vpy[a_py]), silicon_pick=int(vpy[sil_a])),
                           python_margin=int(vpy[a_py] - vpy[sil_a]),
                           firmware_value=dict(python_pick=int(vfw[a_py]), silicon_pick=int(vfw[sil_a])),
                           firmware_margin=int(vfw[sil_a] - vfw[a_py]),
                           eh=dict(python_pick=eh(a_py), silicon_pick=eh(sil_a)),
                           cleared=dict(python_pick=immediate(b, a_py, cur), silicon_pick=immediate(b, sil_a, cur)),
                           switch_eq=eq, bucket=bucket)
                fh.write(json.dumps(row) + "\n"); n += 1
                print(f"{game} p{p:3d} vc{row['vc']:2d} h{row['maxh']:2d} py a{a_py:2d} sil a{sil:2d} "
                      f"pymargin {row['python_margin']:4d} fwmargin {row['firmware_margin']:4d} eh py {row['eh']['python_pick']} "
                      f"sil {row['eh']['silicon_pick']} cleared py {row['cleared']['python_pick'][0]} sil "
                      f"{row['cleared']['silicon_pick'][0]} -> {bucket}", flush=True)
    print(f"{n} cases -> {out}")


if __name__ == "__main__":
    main()
