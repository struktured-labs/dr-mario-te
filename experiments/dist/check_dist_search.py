#!/usr/bin/env python3
"""WHOLE-SEARCH CHECK for DRDIST: the sim brain STEER6b measured (cascade_leaf6_x.Leaf6Decider mode dist_target, W 60,
vk 4, on ANTIBODY/HSV512; the HSV and D extras added AFTER the base leaf's signed-16 wrap) vs an RTL-EXACT twin (the
same module with every `+ _x5(...) + _x6(...)` wrapped to signed 16 together with the base, i.e. INSIDE the combine,
as LeafEval implements both: HSV in S_COLWALK's matched60, -60*D folded at S_DONE). Textual transform of the four
leaf-value sites; everything else is byte-for-byte the measured module.
Boards: real gate-(b) play boards with 1..4 viruses (the term's regime; fw540 baseline, owner model), the couch
endgame boards incl. the two STEER6 regression cases (9/27 lulu G1 stall, 9/27 match-1 G3), and a sample of >4-virus
boards (term off). Non-vacuity: the term moves the root decision vs mode "off".
Usage: check_dist_search.py [--games N]
"""
import argparse, json, os, re, sys, importlib.util
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(ROOT, "tmp", "nbcache_distcheck"))
sys.path.insert(0, CVX)
import import_pin; import_pin.pin()
import numpy as np

SITES = [
    ("            lv += _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6)\n",
     "            lv = _w16(lv + _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6))\n"),
    ("        return (1, 0, 0, _combine_terms(terms, w) + _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6), 0)\n",
     "        return (1, 0, 0, _w16(_combine_terms(terms, w) + _x5(ccol, cvir, fl, w5) + _x6(ccol, cvir, w6)), 0)\n"),
    ("    val = _combine_terms(terms, w) + _x5(pcol, pvir, fl, w5) + _x6(pcol, pvir, w6)\n",
     "    val = _w16(_combine_terms(terms, w) + _x5(pcol, pvir, fl, w5) + _x6(pcol, pvir, w6))\n"),
    ("        tot += best3 if have3 else (_leafv_ship(b2c, b2v, w, fl) + _x5(b2c, b2v, fl, w5) + _x6(b2c, b2v, w6))\n",
     "        tot += best3 if have3 else _w16(_leafv_ship(b2c, b2v, w, fl) + _x5(b2c, b2v, fl, w5) + _x6(b2c, b2v, w6))\n"),
]
W16 = '''

@njit(cache=True, fastmath=False)
def _w16(x):
    """signed-16 wrap: the RTL combine's single wrap (modular, so wrap(wrap(a) + b) == wrap(a + b))."""
    y = x & 0xFFFF
    if y >= 0x8000:
        y -= 0x10000
    return int64(y)
'''


def make_rtl_module():
    src = open(os.path.join(CVX, "cascade_leaf6_x.py")).read()
    n_all = len(re.findall(r"_x6\(", src))
    for a, b in SITES:
        assert src.count(a) == 1, a
        src = src.replace(a, b, 1)
    # insert _w16 before the first function that uses it (after _x5's definition)
    anchor = "@njit(cache=True, fastmath=False)\ndef _leaf_chain6("
    assert src.count(anchor) == 1
    src = src.replace(anchor, W16.lstrip("\n") + "\n\n" + anchor, 1)
    out = os.path.join(ROOT, "tmp", "cascade_leaf6_rtl_x.py")
    open(out, "w").write(src)
    spec = importlib.util.spec_from_file_location("cascade_leaf6_rtl_x", out)
    m = importlib.util.module_from_spec(spec); sys.modules["cascade_leaf6_rtl_x"] = m; spec.loader.exec_module(m)
    return m, n_all


def board_from_S(S):
    from drmario.faithful_game import FaithfulBoard
    b = FaithfulBoard(16, 8)
    b.color = np.array([int(ch) for ch in S["color"]], np.int8).reshape(16, 8)
    b.is_virus = np.array([ch == "1" for ch in S["virus"]], bool).reshape(16, 8)
    b.link = np.array([int(ch) for ch in S["link"]], np.int8).reshape(16, 8)
    return b


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--games", type=int, default=24); ap.add_argument("--big", type=int, default=60)
    a = ap.parse_args()
    import cascade_leaf6_x as L6
    import gate_b as G, bursty_model as BM, vs_race as V, fast_rtl_x as FX
    from drmario.faithful_game import Pill
    R, n_x6 = make_rtl_module()
    w, fl = FX.variant("winner")
    kw = dict(topk2=8, maxpass=0, w_chain=540, ws=20, tap=2)
    mk = lambda M, mode: M.Leaf6Decider(w, fl, mode=mode, W=60, vk=4, **kw)
    m = BM.fit_struktured_20260804(); boards = []
    base = V._decider("fw540")

    def choose(env, col, vir, ctx):
        boards.append(("game", env.board.clone(), env.pills_placed, Pill(int(env.cur.a), int(env.cur.b)),
                       Pill(int(env.nxt.a), int(env.nxt.b))))
        return base(env, col, vir, ctx)
    for s in range(a.games):
        G.play(40101 + 2 * s, None, m, choose=choose)
    nv = lambda b: int(np.asarray(b.is_virus).sum())
    end = [x for x in boards if 1 <= nv(x[1]) <= 4]
    big = [x for x in boards if nv(x[1]) > 4][:a.big]
    couch = []
    for f, lab in (("cases_lulu_20260927.jsonl", "lulu"), ("cases_hsv_20260927.jsonl", "m1")):
        for l in open(os.path.join(CF, f)):
            r = json.loads(l)
            b = board_from_S(r["S"])
            reg = (lab == "lulu" and r.get("game_label") == "9/27 lulu G1") or (lab == "m1" and r.get("game_label") == "9/27 HSV G3")
            if 1 <= nv(b) <= 4 or reg:
                couch.append(("couch_" + lab + ("_REG" if reg else ""), b, r["k_game"], Pill(*r["cur"]), Pill(*r["nxt"])))
    sets = (("game_end", end), ("couch", couch), ("game_big", big))
    ok = True
    print(f"transform: {len(SITES)} leaf-value sites wrapped (of {n_x6} _x6 references incl. the def/calls)")
    for name, S in sets:
        sim, rtl, off = mk(L6, "dist_target"), mk(R, "dist_target"), mk(L6, "off")
        same = moved = act = 0; bad = []
        for i, (kind, b, k, c, n) in enumerate(S):
            x = sim.choose(b, c, n, k); y = rtl.choose(b, c, n, k)
            same += int(x == y)
            if x != y:
                bad.append((kind, i))
            moved += int(x != off.choose(b, c, n, k))
        act = sim.active
        reg = sum(1 for s in S if s[0].endswith("_REG"))
        print(f"{name:9s}: {len(S)} boards ({reg} regression-case boards), term active on {act}: sim (post-wrap) == "
              f"RTL-exact (in-combine) {same}/{len(S)}; the term moved the root decision vs off on {moved}")
        if bad:
            print("   mismatches", bad[:10])
        ok &= same == len(S)
    ok &= len(end) > 0
    print("CHECK_DIST_SEARCH", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
