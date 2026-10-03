#!/usr/bin/env python3
"""Validate the numba silicon-faithful sim brain (cascade_leaf6fw_braingap_20261003.Leaf6FwDecider) on the couch boards.

Checks, per game (G2/G3/G4, the 10/03 couch match):
  OFF   all switches 0 == Leaf6Decider (the sim brain) on every board                       [selfcheck]
  FW    all switches 1, FIRMWARE mask (py65 R_FLT/ROK) -> == the py65 firmware per-root V1 (every root) and the
        py65 search final; == the Verilator co-sim final on every board where the co-sim did not commit a tuck
  FWpm  all switches 1, the PYTHON mask (what a sim run would use) -> == co-sim final
  EH    eh switches only (hang+ehb1+ehnp), python mask -> == co-sim final        (the minimal sim fix)
  plus the per-switch single flips on top of OFF, for the attribution census.
Usage: validate_fwvariant_braingap_20261003.py OUT.jsonl [G2 G3 G4]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlengine_braingap_20261003 as E  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as F  # noqa: E402
import numpy as np  # noqa: E402

CF = E.H16 + "/experiments/couch_forensics"
LF = "/home/struktured/projects/dr-mario-lateflip-wt/experiments/lateflip"
sys.path.insert(0, CF)
O4_OF_VAR = (2, 3, 0, 1)
OFF = dict(veto=0, hang=0, ehb1=0, ehnp=0, wrap=0, order=0)
FWS = dict(veto=1, hang=1, ehb1=1, ehnp=1, wrap=1, order=1)
EHS = dict(OFF, hang=1, ehb1=1, ehnp=1)


def phys(a, cur):
    if a is None:
        return None
    var, col = a // 8, a % 8
    x, y = cur
    return {0: ("H", col, (x, y)), 1: ("H", col, (y, x)), 2: ("V", col, (x, y)), 3: ("V", col, (y, x))}[var]


def main():
    out = sys.argv[1]
    games = sys.argv[2:] or ["G2", "G3", "G4"]
    import analyze_g2 as A
    import fast_rtl_x as FX
    import cascade_chain_x as C
    import cascade_leaf6_x as L6
    from drmario.faithful_game import Pill
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)
    ref = L6.Leaf6Decider(w, fl, **kw)
    mk = lambda sw, mf=None: F.Leaf6FwDecider(w, fl, sw=sw, mask_fn=mf, **kw)  # noqa: E731
    with open(out, "w") as fh:
        for game in games:
            if game == "G2":
                Q = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))}
            else:
                Q = {q["p"]: q for q in map(json.loads, open(os.path.join(CF, "cases_dist60_20261003.jsonl")))
                     if q.get("game") == game}
            tl = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(LF, f"pubtrace_{game}_fw1488e158.jsonl"))}
            pf = os.path.join(HERE, f"py65_{game}_braingap_20261003.jsonl")
            p65 = {json.loads(l)["p"]: json.loads(l) for l in open(pf)} if os.path.exists(pf) else {}
            for p in sorted(tl):
                q, t = Q[p], tl[p]
                cur, nxt = tuple(q["cur"]), tuple(q["nxt"])
                b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
                P = lambda a: phys(a, cur)  # noqa: E731
                cos = O4_OF_VAR[t["final"][1]] * 8 + t["final"][0]
                tuck = t.get("tuck") not in (None, [255, 255])
                row = dict(game=game, p=p, vc=t["vc"], maxh=max(t["heights"]) if t["heights"] else None, cosim=cos,
                           cosim_tuck=tuck)
                a_ref = ref.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
                d_off = mk(OFF); a_off = d_off.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
                d_eh = mk(EHS); a_eh = d_eh.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
                d_fwp = mk(FWS); a_fwp = d_fwp.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
                row.update(py=a_ref, off=a_off, eh=a_eh, fw_pymask=a_fwp)
                singles = {}
                for s in ("veto", "hang", "ehb1", "ehnp", "wrap", "order"):
                    singles[s] = mk(dict(OFF, **{s: 1})).choose(b.clone(), Pill(*cur), Pill(*nxt), p)
                row["single"] = singles
                r65 = p65.get(p)
                if r65 is not None:
                    fm_o4 = r65["rok"] if r65["rflt"] else [1] * 32
                    fm_var = np.zeros(32, np.int8)
                    for o4 in range(4):
                        for c in range(8):
                            fm_var[O4_OF_VAR[o4] * 8 + c] = fm_o4[o4 * 8 + c]
                    d_fw = mk(FWS, lambda _b, _k, m=fm_var: m)
                    a_fw = d_fw.choose(b.clone(), Pill(*cur), Pill(*nxt), p)
                    vals = d_fw.vals
                    nbad = 0
                    for x in r65["roots"]:
                        a = O4_OF_VAR[x["o"]] * 8 + x["c"]
                        nbad += int(vals[a] != x["v1"])
                    pm = d_off.mask(b, p)
                    row.update(fw=a_fw, roots=len(r65["roots"]), root_v1_mismatch=nbad,
                               py65_search=O4_OF_VAR[max(r65["roots"], key=lambda x: x["v1"])["o"]] * 8
                               + max(r65["roots"], key=lambda x: x["v1"])["c"] if r65["roots"] else None,
                               mask_diff=int(sum(int(pm[i] != fm_var[i]) for i in range(32))))
                eq = {k: P(row[k]) == P(cos) for k in ("py", "off", "eh", "fw_pymask", "fw", "py65_search") if k in row}
                eq.update({"py+" + s: P(a) == P(cos) for s, a in singles.items()})
                row["eq"] = eq
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            rows = [json.loads(l) for l in open(out) if json.loads(l)["game"] == game]
            nt = [r for r in rows if not r["cosim_tuck"]]
            print(f"{game}: boards {len(rows)} (co-sim tuck commits {len(rows) - len(nt)})")
            print(f"   OFF == Leaf6Decider            {sum(r['off'] == r['py'] for r in rows)}/{len(rows)}")
            for k in ("py", "eh", "fw_pymask", "fw", "py65_search"):
                n = [r for r in nt if k in r["eq"]]
                print(f"   {k:12s} == co-sim (no-tuck)  {sum(r['eq'][k] for r in n)}/{len(n)}")
            for s in ("veto", "hang", "ehb1", "ehnp", "wrap", "order"):
                print(f"   py+{s:6s} == co-sim (no-tuck)  {sum(r['eq']['py+' + s] for r in nt)}/{len(nt)}")
            wr = [r for r in rows if "root_v1_mismatch" in r]
            print(f"   per-root V1 (FW, fw mask) == py65: boards {sum(r['root_v1_mismatch'] == 0 for r in wr)}/{len(wr)},"
                  f" roots mismatching {sum(r['root_v1_mismatch'] for r in wr)} of {sum(r['roots'] for r in wr)};"
                  f" mask differs (python vs fw) on {sum(r['mask_diff'] > 0 for r in wr)} boards", flush=True)


if __name__ == "__main__":
    main()
