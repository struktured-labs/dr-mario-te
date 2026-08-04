#!/usr/bin/env python3
"""#17 convergence step 1a: which cheap, 6502-amenable CORRIDOR rule covers the
RS-only candidate class?

scan_v3's horizontal geometry admits only ADJACENT approach (one lateral step).
The RS-only class (19% of candidates, 88% horizontal, deep rows) comes from
TE.enumerate's full gravity-timed motion model. Before specing a 6502
extension, measure coverage of candidate corridor rules on the same 20-game
corpus:

  RULE(K): a horizontal candidate resting at rows (rf) on anchor c is covered
  if there exists an entry column-pair (s, s+1) with open sky down to some
  trigger row r (first_occ2(s,s+1) > r >= entry), a clear corridor at row r
  between (s,s+1) and (c,c+1), corridor width d = |s - c|, and lateral budget
  d <= K * (rf - r + 1)   [K columns of travel per row of remaining descent].

Reports, per K in {1,2,3, inf}: fraction of RS-only horizontal candidates
covered. K=inf isolates pure corridor-geometry coverage from budget effects.
Also reports vertical-class coverage by the analogous single-column rule.
"""
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
from tuck_scan_v3_ref import ref_tuck_scan_v3, candidate_cells, occ, first_occ, \
    first_occ2, ROWS, COLS, H, V, RH, RV
from common import arrays_to_nes

FLIP = {H: 0, V: 1, RH: 1, RV: 0}


def _norm(cells, colors):
    r0, c0, r1, c1 = cells
    a, b = colors
    return tuple(sorted([(r0, c0, int(a)), (r1, c1, int(b))]))


def covered_h(board, c, rf, K):
    """Horizontal candidate anchored at c (cells (rf,c),(rf,c+1)): exists entry
    pair (s,s+1) + trigger row r with open sky to r, clear corridor at r, and
    budget |s-c| <= K*(rf-r+1)."""
    for s in range(COLS - 1):
        if s == c:
            continue
        fs = first_occ2(board, s, s + 1)
        if fs == 0:
            continue
        step = 1 if c > s else -1
        for r in range(0, fs):          # any trigger row with open sky in (s,s+1)
            if r > rf:
                break
            # corridor: every intermediate anchor position open at row r
            x = s
            ok = True
            while x != c:
                x += step
                if occ(board, r, x) or occ(board, r, x + 1):
                    ok = False
                    break
            if not ok:
                continue
            d = abs(s - c)
            if K is None or d <= K * (rf - r + 1):
                return True
    return False


def covered_v(board, c, rf, K):
    for s in range(COLS):
        if s == c:
            continue
        fs = first_occ(board, s)
        if fs == 0:
            continue
        step = 1 if c > s else -1
        for r in range(1, fs):          # top cell needs r-1 open too (approx)
            if r > rf:
                break
            x = s
            ok = True
            while x != c:
                x += step
                if occ(board, r, x) or occ(board, r - 1, x):
                    ok = False
                    break
            if not ok:
                continue
            d = abs(s - c)
            if K is None or d <= K * (rf - r + 1):
                return True
    return False


def main(games=20, level=11):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB

    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    Ks = [1, 2, 3, None]
    cov_h = {k: 0 for k in Ks}
    cov_v = {k: 0 for k in Ks}
    tot_h = tot_v = 0

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
            fw_keys = set()
            fw_cands, _ = ref_tuck_scan_v3(board)
            for cnd in fw_cands:
                r0, c0, r1, c1 = candidate_cells(cnd["target"], cnd["rest"], cnd["orient"])
                fp = FLIP[cnd["orient"]]
                col0, col1 = (ca, cb) if fp == 0 else (cb, ca)
                fw_keys.add(_norm((r0, c0, r1, c1), (col0, col1)))
            for p in RS.tuck_root_candidates(fb, ca, cb, 12, True):
                k = _norm(p["cells"], p["colors"])
                if k in fw_keys:
                    continue
                cells = [t[:2] for t in k]
                vert = cells[0][1] == cells[1][1]
                rf = max(t[0] for t in cells)
                anchor = min(t[1] for t in cells)
                if vert:
                    tot_v += 1
                    for kk in Ks:
                        if covered_v(board, anchor, rf, kk):
                            cov_v[kk] += 1
                else:
                    tot_h += 1
                    for kk in Ks:
                        if covered_h(board, anchor, rf, kk):
                            cov_h[kk] += 1

            # advance with base decider
            import numpy as _np
            c1b = _np.empty(NCELL, dtype=_np.int8)
            v1b = _np.empty(NCELL, dtype=_np.int8)
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
        print(f"seed {seed}: cum RS-only H={tot_h} V={tot_v}", flush=True)

    print(f"\n=== CORRIDOR COVERAGE of RS-only class ({games} games) ===")
    print(f"horizontal RS-only n={tot_h}:")
    for kk in Ks:
        name = "inf" if kk is None else str(kk)
        print(f"  K={name}: {cov_h[kk]} ({cov_h[kk]/max(tot_h,1):.1%})")
    print(f"vertical RS-only n={tot_v}:")
    for kk in Ks:
        name = "inf" if kk is None else str(kk)
        print(f"  K={name}: {cov_v[kk]} ({cov_v[kk]/max(tot_v,1):.1%})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20)
    a = ap.parse_args()
    main(a.games)
