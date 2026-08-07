#!/usr/bin/env python3
"""tuck_setdiff_value.py -- are the firmware scanner's tuck picks WORSE, or
merely DIFFERENT, than the Python enumerator's?

`characterize_setdiff.py` already established WHAT each side enumerates over
2,433 decisions: shared 28%, RS-only 19%, **FW-only 53%**, with FW-only heavily
horizontal (RH 1917 + H 1242 of 4219 = 75%) and concentrated in mid-board rows
8-12 while RS-only sits low (13-15). What nobody measured is whether that
difference COSTS anything.

THE COMPARISON, and why it is controlled. For each decision on an identical
board, score three candidate sets through the SAME scorer at the SAME theta --
`mirrored_leaf.choose_root_with_tucks_mirrored`, the mirror ruler the tuck
program already uses -- varying ONLY the candidate set:

    base   tuck_cands = []                      (no tucks at all)
    PY     tuck_cands = RS.tuck_root_candidates (the proof's enumerator)
    FW     tuck_cands = ref_tuck_scan_v3        (the firmware scanner)

Every number is therefore a paired within-decision difference on one board with
one pill pair; nothing differs but the vocabulary. The firmware scanner returns
candidates WITHOUT scores (`tuck_scan_v3_ref.ref_tuck_scan_v3` -> a bare list),
so "the firmware's selected candidate" is necessarily argmax-under-the-eval over
its set -- best-in-set is the faithful reading, not an approximation of one.

WHAT THIS DOES AND DOES NOT ISOLATE. It isolates the VOCABULARY: given the same
eval, does the firmware's candidate set contain as good a best move? It does NOT
test the firmware's own scoring/selection rule, nor its execution. If FW's
best-in-set matches PY's, the vocabulary is fine and the loss is downstream
(selection, execution, or the root-placement overwrite).

THETA: the ship value is 150 (`fpga/copro/tuck_v3.py`) against reach_root's
offline 250. Both are reported, because if the FW-only picks live in the
marginal band that 150 admits and 250 rejects, tightening theta is the fix.

No new games in the sense that matters: boards come from replaying the BASE
decider, so every arm sees an identical trajectory.

Usage: tuck_setdiff_value.py --seeds 8 --out results/tuck_setdiff_value.json
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import statistics as st
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
for _p in (QA + "/tuck_v3", QA + "/eval47", QA, QA + "/bitexact_gate", QA_TUCK,
           ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                        # noqa: E402
import fast_rtl_x as FX                                   # noqa: E402
import root_search as RS                                  # noqa: E402
import mirrored_leaf as ML                                # noqa: E402
import reach_root as RR                                   # noqa: E402

RR_WS = 20            # shipped strand20 dose, as reach_root.choose_base32 uses
from tuck_scan_v3_ref import (ref_tuck_scan_v3, candidate_cells,  # noqa: E402
                              H, V, RH, RV)
from common import arrays_to_nes                          # noqa: E402

FLIP = {H: 0, V: 1, RH: 1, RV: 0}
ONAME = {H: "H", V: "V", RH: "RH", RV: "RV"}


def fw_candidates(fb, ca, cb):
    """tuck_scan_v3's set, converted to the {cells, colors} shape the mirror
    scorer takes. Same conversion union_mirror.py:union_cands uses."""
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    cands, _dropped = ref_tuck_scan_v3(arrays_to_nes(col, vir))
    out = []
    for c in cands:
        r0, c0, r1, c1 = candidate_cells(c["target"], c["rest"], c["orient"])
        col0, col1 = (ca, cb) if FLIP[c["orient"]] == 0 else (cb, ca)
        out.append({"cells": (r0, c0, r1, c1), "colors": (col0, col1),
                    "src": "fw", "orient": ONAME[c["orient"]]})
    return out


def orient_of(cells):
    r0, c0, r1, c1 = cells
    return "H" if r0 == r1 else "V"


# ---------------------------------------------------------------- fast scorer
# `mirrored_leaf.choose_root_with_tucks_mirrored` is the RTL-faithful ruler but
# it evaluates each candidate in PYTHON: measured 3.3 s of CPU per decision,
# which makes a few hundred decisions unaffordable. What this comparison
# actually requires is that BOTH sides be scored by the SAME ruler -- not that
# the ruler be the RTL mirror. So use the njit shipped eval, which is the exact
# arithmetic `reach_root.choose_base32` uses:
#     val = RS._root_value(...) - ws * g_stranded(c1, v1)
# `--gate` checks the njit scorer agrees with the RTL mirror on the SIGN of
# (fw_margin - py_margin) on real decisions -- the quantity every conclusion
# here rests on -- so the substitution is verified rather than assumed.
def score_sets(fb, ca, cb, na, nb, py, fw, w, fl, ws, topk2=8):
    """-> (base_val, best_py_margin|None, best_fw_margin|None, py_or, fw_or)."""
    from terms47 import g_stranded
    col = np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8)
    vir = np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8)
    import fast_sim_x as FS
    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)

    base_val = None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            if base_val is None or val > base_val:
                base_val = val

    def best_of(cands):
        bv, bo = None, None
        for p in cands:
            r0, c0, r1, cc1 = p["cells"]
            col0, col1 = p["colors"]
            nv, cells = RS._expand_core_at(col, vir, r0, c0, r1, cc1,
                                           col0, col1, c1, v1)
            val = RS._root_value(c1, v1, nv, cells, na, nb, topk2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= ws * g_stranded(c1, v1)
            if bv is None or val > bv:
                bv, bo = val, orient_of(p["cells"])
        return bv, bo

    py_v, py_o = best_of(py)
    fw_v, fw_o = best_of(fw)
    return (float(base_val),
            (float(py_v) - base_val) if py_v is not None else None,
            (float(fw_v) - base_val) if fw_v is not None else None,
            py_o, fw_o)


def gate(w, fl, seed=4242, n=10):
    """Prove the njit scorer RANKS the two sets the same way the RTL-mirror
    scorer does. The substitution is only legitimate if it does not change
    which set looks better -- so compare the SIGN of (fw_margin - py_margin)
    on real decisions, which is the quantity every conclusion rests on."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB

    env = FaithfulDrMarioEnv(level=11, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    agree = checked = 0
    for _ in range(n):
        if env.board.virus_count() == 0:
            break
        fb = FB.from_board(env.board)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        py = RS.tuck_root_candidates(fb, ca, cb, 12, True)
        fw = fw_candidates(fb, ca, cb)

        _b, pm, fm, _po, _fo = score_sets(fb, ca, cb, na, nb, py, fw, w, fl, RR_WS)
        mp = ML.choose_root_with_tucks_mirrored(fb, env.cur, env.nxt, w, topk2=8,
                                                tuck_cands=py, theta=0.0)
        mf = ML.choose_root_with_tucks_mirrored(fb, env.cur, env.nxt, w, topk2=8,
                                                tuck_cands=fw, theta=0.0)
        m_pm = (float(mp["val"]) - float(mp["best_base_val"])) if mp["kind"] == "tuck" else None
        m_fm = (float(mf["val"]) - float(mf["best_base_val"])) if mf["kind"] == "tuck" else None
        s_fast = (0 if pm is None else pm) - (0 if fm is None else fm)
        s_mirr = (0 if m_pm is None else m_pm) - (0 if m_fm is None else m_fm)
        checked += 1
        agree += (s_fast > 0) == (s_mirr > 0) and (s_fast < 0) == (s_mirr < 0)

        a = RR.choose_base32(np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8),
                             np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8),
                             ca, cb, na, nb)["action"]
        if a is None:
            break
        _, _, term, trunc, _ = env.step(int(a))
        if term or trunc:
            break
    print(f"[gate] njit vs RTL-mirror agree on sign(FW-PY): {agree}/{checked}")
    return agree == checked


def probe_seed(seed, w, fl, thetas, level=11, max_pills=300):
    """Replay one game with the BASE decider; at every decision score the three
    candidate sets through the same scorer at each theta."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    rows = []
    for _ in range(max_pills):
        if env.board.virus_count() == 0:
            break
        fb = FB.from_board(env.board)
        ca, cb = int(env.cur.a), int(env.cur.b)

        py = RS.tuck_root_candidates(fb, ca, cb, 12, True)
        fw = fw_candidates(fb, ca, cb)

        # ONE scoring pass covers EVERY theta. The gate is exactly
        # `val < best_base_val + theta -> skip` (mirrored_leaf.py:171), so a
        # tuck fires at theta iff its MARGIN over base is >= theta. Recording
        # the margin once makes every theta a post-hoc filter.
        na, nb = int(env.nxt.a), int(env.nxt.b)
        base_val, py_m, fw_m, py_o, fw_o = score_sets(fb, ca, cb, na, nb, py, fw,
                                                      w, fl, RR_WS)
        rows.append({"seed": seed, "n_py": len(py), "n_fw": len(fw),
                     "base": base_val, "py_margin": py_m, "fw_margin": fw_m,
                     "py_or": py_o, "fw_or": fw_o})

        # advance with the BASE choice so every arm shares one trajectory
        a = RR.choose_base32(np.frombuffer(bytes(fb.col), dtype=np.uint8).astype(np.int8),
                             np.frombuffer(bytes(fb.vir), dtype=np.uint8).astype(np.int8),
                             ca, cb, na, nb)["action"]
        if a is None:
            break
        _, _, term, trunc, _ = env.step(int(a))
        if term or trunc:
            break
    return rows


def summarise(rows, th):
    """A tuck fires at theta iff its margin over base is >= theta, so every
    theta is recoverable from the single theta=0 measurement."""
    n = len(rows)

    def fires(m):
        return m is not None and m >= th

    py_fire = sum(1 for r in rows if fires(r["py_margin"]))
    fw_fire = sum(1 for r in rows if fires(r["fw_margin"]))
    # Paired value difference on decisions where EITHER set would fire. A set
    # that declines contributes its base value (0 margin) -- declining IS its
    # choice, so scoring it as 0 is the honest comparison.
    either = [r for r in rows if fires(r["py_margin"]) or fires(r["fw_margin"])]
    delta = [(r["fw_margin"] if fires(r["fw_margin"]) else 0.0)
             - (r["py_margin"] if fires(r["py_margin"]) else 0.0) for r in either]
    fw_or = Counter(r["fw_or"] for r in rows if fires(r["fw_margin"]))
    py_or = Counter(r["py_or"] for r in rows if fires(r["py_margin"]))
    return {
        "theta": th, "n_decisions": n,
        "py_fire": py_fire, "fw_fire": fw_fire,
        "py_fire_pct": 100.0 * py_fire / n if n else 0.0,
        "fw_fire_pct": 100.0 * fw_fire / n if n else 0.0,
        "n_either": len(either),
        "mean_fw_minus_py": st.mean(delta) if delta else 0.0,
        "median_fw_minus_py": st.median(delta) if delta else 0.0,
        "fw_better": sum(1 for x in delta if x > 0),
        "py_better": sum(1 for x in delta if x < 0),
        "tie": sum(1 for x in delta if x == 0),
        "fw_orient": dict(fw_or), "py_orient": dict(py_or),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=7000)
    ap.add_argument("--thetas", type=int, nargs="+", default=[150, 250])
    ap.add_argument("--out", required=True)
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()

    FX.warmup_ship_eh(topk2=8)
    RR._lazy()
    w, fl = FX.variant("winner")

    if a.gate and not gate(w, fl):
        sys.exit("gate FAILED -- njit scorer disagrees with the RTL mirror on sign(FW-PY)")

    rows = []
    for i in range(a.seeds):
        s = a.seed0 + i
        r = probe_seed(s, w, fl, a.thetas)
        rows.extend(r)
        print(f"  seed {s}: {len(r)} decisions (cum {len(rows)})", flush=True)

    print(f"\n{len(rows)} decisions, paired within-decision, same scorer, "
          f"only the candidate SET differs\n")
    out = []
    for th in a.thetas:
        s = summarise(rows, th)
        out.append(s)
        print(f"theta={th}")
        print(f"  fire rate   PY {s['py_fire_pct']:5.1f}%   FW {s['fw_fire_pct']:5.1f}%"
              f"   (FW/PY = {s['fw_fire'] / max(1, s['py_fire']):.2f}x)")
        print(f"  on {s['n_either']} decisions where either would tuck:")
        print(f"    mean(FW - PY) value = {s['mean_fw_minus_py']:+.2f}   "
              f"median {s['median_fw_minus_py']:+.2f}")
        print(f"    FW strictly better {s['fw_better']}   PY strictly better "
              f"{s['py_better']}   tie {s['tie']}")
        print(f"    winner orientation  FW {s['fw_orient']}   PY {s['py_orient']}")
        print()

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump({"n_decisions": len(rows), "summaries": out}, f, indent=2)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
