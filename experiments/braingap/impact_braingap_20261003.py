#!/usr/bin/env python3
"""Brain-gap IMPACT on general sim boards: how often does the python sim brain (Leaf6Decider dist_target60) pick a
different move from the silicon-faithful brain (Leaf6FwDecider, every firmware switch on; numba, validated per root
against py65 of the shipped image), and in which phase?

Per board: python action, firmware action, the EH-only fix (hang + soft b1 + no-ply-2 skip), single-switch flips, the
immediate clear (cells / viruses) of the python and firmware picks, virus count, max height, pill index.
Usage: impact_braingap_20261003.py BOARDS.jsonl OUT.jsonl [--report]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlengine_braingap_20261003 as E  # noqa: E402
import cascade_leaf6fw_braingap_20261003 as F  # noqa: E402
import numpy as np  # noqa: E402

OFF = dict(veto=0, hang=0, ehb1=0, ehnp=0, wrap=0, order=0)
FWS = dict(veto=1, hang=1, ehb1=1, ehnp=1, wrap=1, order=1)
EHS = dict(OFF, hang=1, ehb1=1, ehnp=1)
SINGLES = ("veto", "hang", "ehb1", "ehnp", "wrap", "order")


def phys(a, cur):
    if a is None:
        return None
    var, col = a // 8, a % 8
    x, y = cur
    return {0: ("H", col, (x, y)), 1: ("H", col, (y, x)), 2: ("V", col, (x, y)), 3: ("V", col, (y, x))}[var]


def immediate(b, a, cur):
    """cells / viruses cleared and chain of placing action a on b (the search's own ply-1 node)."""
    from fast_sim_x import NCELL
    from cascade_link_x import board_flat
    from cascade_chain_x import _expand_chain
    col, vir = board_flat(b)
    lnk = np.ascontiguousarray(b.link, dtype=np.int8).reshape(-1)
    c = np.empty(NCELL, np.int8); v = np.empty(NCELL, np.int8); l = np.empty(NCELL, np.int8)
    m = np.empty(NCELL, np.int8)
    ok, nv, cells, ch = _expand_chain(col, vir, lnk, a // 8, a % 8, cur[0], cur[1], c, v, l, m, 0)
    return int(cells), int(nv), int(ch)


def run(boards_path, out):
    sys.path.insert(0, E.H16 + "/experiments/couch_forensics")
    import analyze_g2 as A
    import fast_rtl_x as FX
    import cascade_chain_x as C
    from drmario.faithful_game import Pill
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)
    D = {"py": F.Leaf6FwDecider(w, fl, sw=OFF, **kw), "fw": F.Leaf6FwDecider(w, fl, sw=FWS, **kw),
         "eh": F.Leaf6FwDecider(w, fl, sw=EHS, **kw)}
    for s in SINGLES:
        D["py+" + s] = F.Leaf6FwDecider(w, fl, sw=dict(OFF, **{s: 1}), **kw)
        D["fw-" + s] = F.Leaf6FwDecider(w, fl, sw=dict(FWS, **{s: 0}), **kw)
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["i"] for l in open(out)}
    with open(out, "a") as fh:
        for l in open(boards_path):
            q = json.loads(l)
            if q["i"] in done:
                continue
            b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
            cur, nxt, k = tuple(q["cur"]), tuple(q["nxt"]), q["k"]
            acts = {n: d.choose(b.clone(), Pill(*cur), Pill(*nxt), k) for n, d in D.items()}
            P = {n: phys(a, cur) for n, a in acts.items()}
            row = dict(i=q["i"], k=k, nv=q["nv"], maxh=q["maxh"], acts=acts,
                       diff={n: P[n] != P["py"] for n in acts}, eqfw={n: P[n] == P["fw"] for n in acts})
            if acts["py"] is not None and acts["fw"] is not None:
                row["imm_py"] = immediate(b, acts["py"], cur)
                row["imm_fw"] = immediate(b, acts["fw"], cur)
            fh.write(json.dumps(row) + "\n")


def report(out):
    R = [json.loads(l) for l in open(out)]
    print(f"boards {len(R)}")

    def rate(rows, key="fw"):
        n = len(rows)
        d = sum(r["diff"][key] for r in rows)
        return f"{d}/{n} = {100.0 * d / n:.1f}%" if n else "-"
    print(f"python != firmware (all switches):  {rate(R)}")
    print(f"python != EH-only fix:              {rate(R, 'eh')}")
    print(f"EH-only fix == firmware:            {sum(r['eqfw']['eh'] for r in R)}/{len(R)}")
    for s in SINGLES:
        print(f"   python + {s:6s} alone != python: {rate(R, 'py+' + s):>18s}   firmware - {s:6s} == firmware: "
              f"{sum(r['eqfw']['fw-' + s] for r in R)}/{len(R)}")
    print("by max height (python != firmware):")
    for lo, hi in ((0, 8), (8, 10), (10, 12), (12, 14), (14, 17)):
        rr = [r for r in R if lo <= r["maxh"] < hi]
        print(f"   maxh {lo:2d}-{hi - 1:2d}: {rate(rr)}")
    print("by virus count (python != firmware):")
    for lo, hi in ((0, 5), (5, 9), (9, 17), (17, 33), (33, 99)):
        rr = [r for r in R if lo <= r["nv"] < hi]
        print(f"   viruses {lo:2d}-{hi - 1:2d}: {rate(rr)}")
    dd = [r for r in R if r["diff"]["fw"] and "imm_py" in r]
    if dd:
        cp = sum(r["imm_py"][0] > 0 for r in dd); cf = sum(r["imm_fw"][0] > 0 for r in dd)
        vp = sum(r["imm_py"][1] for r in dd); vf = sum(r["imm_fw"][1] for r in dd)
        print(f"on the {len(dd)} divergent boards: python pick clears cells on {cp}, firmware pick on {cf}; "
              f"viruses cleared immediately python {vp} vs firmware {vf}")


if __name__ == "__main__":
    if "--report" in sys.argv:
        report(sys.argv[2])
    else:
        run(sys.argv[1], sys.argv[2])
        report(sys.argv[2])
