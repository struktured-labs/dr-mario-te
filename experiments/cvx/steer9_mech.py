#!/usr/bin/env python3
"""STEER9 step 2: MECHANISM CHECK of the seal rules on the BANKED couch cases (before any sim game).

Boards (observed, hidden-spawn tracker + repair, as banked by the couch-forensics lane):
  m5g2  10/04 M5 G2 (FAIR; col 6 walled by p65, col 7's 6 viruses unreachable 119 pills): stall_fair_20261004.load()
  m4g2  10/04 M4 G2 (FAIR2's tap-out; tall board, reach mask 30 -> 1): cases_m4g2_fair_20261004.jsonl
  lulu1 9/27 dr. lulu G1 (yellow (8,2) sealed under a mixed own-pill stack, ~99 pills): cases_lulu_20260927.jsonl

Per placement: the silicon-faithful brain (Leaf6FwDecider, every fw switch on, DIST60, deployed reach mask at the
pill index) = `base`; every rule variant's choice on the SAME board; for base / silicon / each variant the number of
NEWLY SEALED viruses (kind 0) and newly closed virus columns (kind 1) on the firmware soft b1, and the cells it adds
to the critical column. Output: steer9/mech_cases.jsonl + the printed tables (steer9/mech_check.txt).

  NUMBA_CACHE_DIR=<fresh> python steer9_mech.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.abspath(os.path.join(HERE, "..", "couch_forensics"))
sys.path.insert(0, HERE)
import seal_steer9 as S9  # noqa: E402  (pins import paths)
sys.path.insert(0, CF)
from drmario.faithful_game import Pill  # noqa: E402

VARIANTS = {
    "V_P60": dict(kind=0, mode=0, P=60), "V_P150": dict(kind=0, mode=0, P=150), "V_P400": dict(kind=0, mode=0, P=400),
    "V_VETO": dict(kind=0, mode=1, P=20000),
    "C_P150": dict(kind=1, mode=0, P=150), "C_P400": dict(kind=1, mode=0, P=400), "C_VETO": dict(kind=1, mode=1, P=20000),
    "L_W30": dict(wleaf=30), "L_W60": dict(wleaf=60),
}


def decider(seal):
    import fast_rtl_x as FX
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    return S9.SealFwDecider(w, fl, sw=None, seal=seal, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2,
                            mode="dist_target", W=60, vk=4)


def boards_m5g2():
    os.environ["GAME"] = "m5g2"
    cwd = os.getcwd()
    import stall_fair_20261004 as ST
    L, _fixes, _w = ST.load()
    os.chdir(cwd)
    import analyze_g2 as A
    out = []
    for r in L:
        S = r["S"]
        b = A.board_from_strings(S["color"], S["virus"], S["link"])
        o, orow, ocol, ocl = r["landing"]
        out.append(dict(p=r["p"], k=r["p"], b=b, cur=tuple(r["cur"]), nxt=tuple(r["nxt"]), actual=[o, ocol, list(ocl), orow]))
    return out


def boards_cases(path, kkey, label=None):
    """label: keep only rows whose game_label == label (cases_lulu_20260927.jsonl holds G1 AND G2, both game=1)."""
    import analyze_g2 as A
    out = []
    for l in open(path):
        r = json.loads(l)
        if label is not None and r.get("game_label") != label:
            continue
        S = r["S"]
        b = A.board_from_strings(S["color"], S["virus"], S["link"])
        out.append(dict(p=r.get("p", r.get("k_game")), k=r[kkey], b=b, cur=tuple(r["cur"]), nxt=tuple(r["nxt"]),
                        actual=r["actual"]))
    return out


def action_of(pose, cur, b):
    from endgame_dist60_20261003 import pose_of
    if pose is None:
        return None
    for a in range(32):
        if pose_of(a, cur, b) == list(pose):
            return a
    return None


def cells_in_col(a, cur, b, col):
    """cells the straight-drop root a adds to column col (0..2) and their rows."""
    from endgame_dist60_20261003 import pose_of
    if a is None:
        return 0
    o, c, cl, row = pose_of(a, cur, b)
    if row is None:
        return 0
    if o == "H":
        return int(c == col) + int(c + 1 == col)
    return 2 * int(c == col)


def main():
    from cascade_link_x import board_flat
    base = decider(dict(P=0))
    var = {k: decider(v) for k, v in VARIANTS.items()}
    pen = np.zeros(32, dtype=np.int64)
    nn0 = np.full(32, -1, dtype=np.int64); nn1 = np.full(32, -1, dtype=np.int64)
    games = {"m5g2": (boards_m5g2(), 6), "m4g2": (boards_cases(os.path.join(CF, "cases_m4g2_fair_20261004.jsonl"), "p"), None),
             "lulu1": (boards_cases(os.path.join(CF, "cases_lulu_20260927.jsonl"), "k_game", label="9/27 lulu G1"), 2)}
    os.makedirs(os.path.join(HERE, "steer9"), exist_ok=True)
    fh = open(os.path.join(HERE, "steer9", "mech_cases.jsonl"), "w")
    for g, (B, crit) in games.items():
        for x in B:
            b, cur, nxt, k = x["b"], Pill(*x["cur"]), Pill(*x["nxt"]), x["k"]
            col, vir = board_flat(b)
            allowed = base.mask(b, k)
            S9._seal_pen(col, vir, cur.a, cur.b, allowed, 0, 0, 1, pen, nn0)
            S9._seal_pen(col, vir, cur.a, cur.b, allowed, 1, 0, 1, pen, nn1)
            a0 = base.choose(b.clone(), cur, nxt, k)
            act = action_of(x["actual"], x["cur"], b)
            row = {"game": g, "p": x["p"], "k": k, "vc": int(vir.sum()), "n_allowed": int(np.sum(allowed)),
                   "base": a0, "silicon": act, "silicon_is_base": act == a0,
                   "nnewV": nn0.tolist(), "nnewC": nn1.tolist(),
                   "base_sealV": int(nn0[a0]) if a0 is not None else None,
                   "base_sealC": int(nn1[a0]) if a0 is not None else None,
                   "sil_sealV": (int(nn0[act]) if act is not None and allowed[act] else None),
                   "sil_sealC": (int(nn1[act]) if act is not None and allowed[act] else None),
                   "alt0V": bool((nn0 == 0).any()), "alt0C": bool((nn1 == 0).any()),
                   "nsealed_root": int(S9._n_sealed(col, vir))}
            if crit is not None:
                row["crit_col"] = crit
                row["base_crit_cells"] = cells_in_col(a0, x["cur"], b, crit)
                row["sil_crit_cells"] = cells_in_col(act, x["cur"], b, crit)
            for name, d in var.items():
                a = d.choose(b.clone(), cur, nxt, k)
                row[name] = a
                row[name + "_sealV"] = int(nn0[a]) if a is not None else None
                row[name + "_sealC"] = int(nn1[a]) if a is not None else None
                if crit is not None:
                    row[name + "_crit_cells"] = cells_in_col(a, x["cur"], b, crit)
            fh.write(json.dumps(row) + "\n"); fh.flush()
    fh.close()


if __name__ == "__main__":
    main()
