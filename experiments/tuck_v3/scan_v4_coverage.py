#!/usr/bin/env python3
"""scan_v4 coverage gate: over the 20-game corpus, v4's candidate set must
cover >= 99% of (RS union scan_v3) physically-normalized candidates, and its
EXCESS over the union (v4-only) is reported (should be modest; corridor rule
admits a few placements TE's motion model rejects — they get priced by the
mirror, not assumed harmful)."""
from __future__ import annotations

import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
QA_TUCK = "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/bitexact_gate", QA_TUCK):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import fast_rtl_x as FX
import root_search as RS
from fast_sim_x import NCELL, _expand_core
from tuck_scan_v3_ref import ref_tuck_scan_v3, candidate_cells, H, V, RH, RV
from common import arrays_to_nes
from scan_v4 import scan_v4

FLIP = {H: 0, V: 1, RH: 1, RV: 0}


def _norm(cells, colors):
    r0, c0, r1, c1 = cells
    a, b = colors
    return tuple(sorted([(r0, c0, int(a)), (r1, c1, int(b))]))


def main(games=20, level=11):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB

    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    union_n = covered = v4_extra = 0
    missed = {}

    for seed in range(games):
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
        env.reset()
        NesPillSource(seed=seed).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        for _ in range(300):
            fb = FB.from_board(env.board)
            if env.board.virus_count() == 0:
                break
            col, vir = RS.board_flat_from_fb(fb)
            ca, cb = int(env.cur.a), int(env.cur.b)
            board = arrays_to_nes(col, vir)

            uni = set()
            for p in RS.tuck_root_candidates(fb, ca, cb, 12, True):
                uni.add(_norm(p["cells"], p["colors"]))
            fw_cands, _ = ref_tuck_scan_v3(board)
            for cnd in fw_cands:
                r0, c0, r1, c1 = candidate_cells(cnd["target"], cnd["rest"], cnd["orient"])
                fp = FLIP[cnd["orient"]]
                col0, col1 = (ca, cb) if fp == 0 else (cb, ca)
                uni.add(_norm((r0, c0, r1, c1), (col0, col1)))
            v4 = {_norm(d["cells"], d["colors"]) for d in scan_v4(board, ca, cb)}
            union_n += len(uni)
            covered += len(uni & v4)
            v4_extra += len(v4 - uni)
            for k in (uni - v4):
                cells = [t[:2] for t in k]
                vert = cells[0][1] == cells[1][1]
                rs_keys = set()
                for p in RS.tuck_root_candidates(fb, ca, cb, 12, True):
                    rs_keys.add(_norm(p["cells"], p["colors"]))
                srcname = "RS" if k in rs_keys else "V3"
                missed[(srcname, "V" if vert else "H")] = missed.get((srcname, "V" if vert else "H"), 0) + 1

            c1b = np.empty(NCELL, dtype=np.int8)
            v1b = np.empty(NCELL, dtype=np.int8)
            best_val, best_a = None, None
            for o4 in range(4):
                var = int(FX._VAR_OF_O4[o4])
                for cc in range(8):
                    ok, nv, cells_ = _expand_core(col, vir, var, cc, ca, cb, c1b, v1b)
                    if ok == 0:
                        continue
                    val = RS._root_value(c1b, v1b, nv, cells_, int(env.nxt.a),
                                         int(env.nxt.b), 8, FX._W_EXCAV_SHIP,
                                         FX._W_HANG_SHIP, w, fl)
                    if best_val is None or val > best_val:
                        best_val, best_a = val, var * 8 + cc
            if best_a is None:
                break
            _, _, term, trunc, _i = env.step(int(best_a))
            if term or trunc:
                break
        print(f"seed {seed}: union {union_n} covered {covered} v4-extra {v4_extra}",
              flush=True)

    print(f"\n=== SCAN_V4 COVERAGE ===")
    print(f"union candidates {union_n}, v4 covers {covered} "
          f"({covered/max(union_n,1):.2%}), v4-only extras {v4_extra} "
          f"({v4_extra/max(union_n,1):.1%} of union size)")
    print(f"missed breakdown (source, geometry): {missed}")
    print("GATE " + ("PASS" if covered / max(union_n, 1) >= 0.99 else "FAIL"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    a = ap.parse_args()
    main(a.games)
