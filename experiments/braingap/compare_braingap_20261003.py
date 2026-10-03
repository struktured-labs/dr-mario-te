#!/usr/bin/env python3
"""Per-board brain-gap attribution on the 10/03 couch boards.

For each board: the co-sim final (Verilator, real RTL + fw 1488e158 = GROUND TRUTH), the py65 firmware search with
the RTL-faithful engine (py65run_braingap_20261003 rows: search final + per-root V1), the python sim brain
(Leaf6Decider dist_target60, as g2_tapout_dist60_20261003 ran it), the RTL-exact twin (check_dist_search's
in-combine wrap), and the switchable mirror (mirror_braingap_20261003) at:
  PY      every switch at the python value, python mask           (must == the sim brain)
  FW      every switch at the firmware value, firmware mask       (must == py65 per root)
  PY+x    python with ONE switch moved to the firmware value      (which single feature flips the board?)
  FW-x    firmware with ONE switch moved back to python           (which feature is NECESSARY?)
Masks: python = Leaf6Decider.mask(board, p) (reach_fw_tap, SM.table_threshold(p), tap 2); firmware = the ROK/R_FLT the
py65 run left in RAM (R_FLT 0 -> all allowed).
Placement identity: doubles compare as physical placements (o4 0==1, 2==3), like DBLCANON.

Usage: compare_braingap_20261003.py GAME OUT.jsonl [p ...]   (GAME G2 | G3 | G4)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_braingap_20261003 as M  # noqa: E402
import rtlengine_braingap_20261003 as E  # noqa: E402
import numpy as np  # noqa: E402

H16 = E.H16
CF = H16 + "/experiments/couch_forensics"
LF = "/home/struktured/projects/dr-mario-lateflip-wt/experiments/lateflip"
sys.path.insert(0, CF)
O4_OF_VAR = (2, 3, 0, 1)
SWITCHES = ("veto", "hang", "ehb1", "ehnp", "wrap", "order", "mask", "eh", "hang+ehb1")
GROUPS = {"eh": ("hang", "ehb1", "ehnp"), "hang+ehb1": ("hang", "ehb1")}


def phys(a, cur):
    """action (var*8+col) -> physical placement key (axis, col, colours in board order)."""
    if a is None:
        return None
    var, col = a // 8, a % 8
    x, y = cur
    return {0: ("H", col, (x, y)), 1: ("H", col, (y, x)), 2: ("V", col, (x, y)), 3: ("V", col, (y, x))}[var]


def act_of_final(c, o4):
    return O4_OF_VAR[o4] * 8 + c


def load_cases(game):
    if game == "G2":
        Q = [json.loads(l) for l in open(os.path.join(CF, "cases_g2_dist60_20261003.jsonl"))]
    else:
        Q = [json.loads(l) for l in open(os.path.join(CF, "cases_dist60_20261003.jsonl"))]
        Q = [q for q in Q if q.get("game") == game]
    return {q["p"]: q for q in Q}


_DEC = {}


def deciders():
    if not _DEC:
        import fast_rtl_x as FX
        import cascade_chain_x as C
        import cascade_leaf6_x as L6
        sys.path.insert(0, "/home/struktured/projects/dr-mario-dist-wt/experiments/dist")
        C.warmup_chain(topk2=8)
        w, fl = FX.variant("winner")
        kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
        _DEC["py"] = L6.Leaf6Decider(w, fl, mode="dist_target", W=60, vk=4, **kw)
        _DEC["twin"] = twin_module().Leaf6Decider(w, fl, mode="dist_target", W=60, vk=4, **kw)
    return _DEC


def twin_module():
    """check_dist_search.make_rtl_module, written to h16 tmp (not the dist worktree's tmp)."""
    import importlib.util
    import re
    spec = importlib.util.spec_from_file_location(
        "cds", "/home/struktured/projects/dr-mario-dist-wt/experiments/dist/check_dist_search.py")
    cds = importlib.util.module_from_spec(spec)
    src = open(spec.origin).read()
    # reuse its SITES / W16 text transform without executing its module-level path setup twice
    ns = {}
    exec(compile(re.search(r"SITES = \[.*?\n\]\n", src, re.S).group(0), "sites", "exec"), ns)
    exec(compile(re.search(r"W16 = '''.*?'''\n", src, re.S).group(0), "w16", "exec"), ns)
    s = open(os.path.join(E.CVX, "cascade_leaf6_x.py")).read()
    for a, b in ns["SITES"]:
        assert s.count(a) == 1, a
        s = s.replace(a, b, 1)
    anchor = "@njit(cache=True, fastmath=False)\ndef _leaf_chain6("
    s = s.replace(anchor, ns["W16"].lstrip("\n") + "\n\n" + anchor, 1)
    out = os.path.join(H16, "tmp", "braingap", "cascade_leaf6_rtl_x.py")
    open(out, "w").write(s)
    spec = importlib.util.spec_from_file_location("cascade_leaf6_rtl_x", out)
    m = importlib.util.module_from_spec(spec); sys.modules["cascade_leaf6_rtl_x"] = m; spec.loader.exec_module(m)
    return m


def py_mask_o4(dec, board, p):
    m = dec.mask(board, p)                       # var space
    return [int(m[O4_OF_VAR[o4] * 8 + c]) for o4 in range(4) for c in range(8)]


def search_final_from_roots(roots):
    best = None; bv = None
    for r in roots:
        if bv is None or r["v1"] > bv:
            bv = r["v1"]; best = (r["c"], r["o"])
    return best


def main():
    game, out = sys.argv[1], sys.argv[2]
    want = set(int(x) for x in sys.argv[3:])
    import analyze_g2 as A
    from drmario.faithful_game import Pill
    cases = load_cases(game)
    tl = {json.loads(l)["p"]: json.loads(l) for l in open(os.path.join(LF, f"pubtrace_{game}_fw1488e158.jsonl"))}
    p65 = {}
    pf = os.path.join(HERE, f"py65_{game}_braingap_20261003.jsonl")
    if os.path.exists(pf):
        p65 = {json.loads(l)["p"]: json.loads(l) for l in open(pf)}
    D = deciders()
    done = set()
    if os.path.exists(out):
        done = {json.loads(l)["p"] for l in open(out)}
    with open(out, "a") as fh:
        for p in sorted(tl):
            if (want and p not in want) or p in done or p not in cases:
                continue
            q, t = cases[p], tl[p]
            cur, nxt = tuple(q["cur"]), tuple(q["nxt"])
            b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
            nes, cA, cB, nA, nB = E.parse_upload(t["upload"])
            ca, cb, na, nb = cA & 3, cB & 3, nA & 3, nB & 3
            assert (ca + 1, cb + 1, na + 1, nb + 1) == cur + nxt, (p, cur, nxt, cA, cB, nA, nB)
            a_py = D["py"].choose(b.clone(), Pill(*cur), Pill(*nxt), p)
            a_tw = D["twin"].choose(b.clone(), Pill(*cur), Pill(*nxt), p)
            pm = py_mask_o4(D["py"], b, p)
            row = dict(game=game, p=p, cur=cur, nxt=nxt, vc=t["vc"], maxh=max(t["heights"]),
                       cosim=act_of_final(*t["final"][:2]), cosim_tuck=t.get("tuck"), banked_sim=t.get("sim_action"),
                       py=a_py, twin=a_tw, py_mask=pm)
            r65 = p65.get(p)
            if r65 is not None:
                sf = search_final_from_roots(r65["roots"])
                row["py65_search"] = act_of_final(sf[0], sf[1]) if sf else None
                row["py65_final"] = act_of_final(*r65["py65"])
                fm = r65["rok"] if r65["rflt"] else [1] * 32
                row["fw_mask"] = fm
                row["tgt"] = r65["tgt"]
            else:
                fm = None
            tgt = row.get("tgt", 0)
            res = {}
            res["PY"], roots_py = M.choose(nes, ca, cb, na, nb, pm, M.PY, tgt)
            if fm is not None:
                res["FW"], roots_fw = M.choose(nes, ca, cb, na, nb, fm, M.FW, tgt)
                row["fw_roots"] = [{k: r[k] for k in ("o4", "col", "v1", "imm1", "leaf1", "best2", "ad", "strand",
                                                       "veto")} for r in roots_fw]
                for s in SWITCHES:
                    swp = dict(M.PY); mk = pm
                    swf = dict(M.FW); mkf = fm
                    if s == "mask":
                        mk = fm; mkf = pm
                    else:
                        for x in GROUPS.get(s, (s,)):
                            swp[x] = 1; swf[x] = 0
                    res["PY+" + s], _ = M.choose(nes, ca, cb, na, nb, mk, swp, tgt)
                    res["FW-" + s], _ = M.choose(nes, ca, cb, na, nb, mkf, swf, tgt)
            row["py_roots"] = [{k: r[k] for k in ("o4", "col", "v1", "imm1", "leaf1", "best2", "ad", "strand")}
                               for r in roots_py]
            row["mirror"] = res
            P = lambda a: phys(a, cur)  # noqa: E731
            row["eq"] = {k: P(v) == P(row["cosim"]) for k, v in list(res.items()) +
                         [("py", a_py), ("twin", a_tw), ("py65_search", row.get("py65_search"))]}
            fh.write(json.dumps(row) + "\n"); fh.flush()
            print(f"{game} p{p:3d} vc{row['vc']:2d} h{row['maxh']:2d} cosim a{row['cosim']:2d} py a{a_py} "
                  f"twin a{a_tw} py65s a{row.get('py65_search')} | PY a{res['PY']} FW a{res.get('FW')} | "
                  + " ".join(f"{k}:{int(v)}" for k, v in row["eq"].items() if k.startswith(("PY+", "FW-"))),
                  flush=True)


if __name__ == "__main__":
    main()
