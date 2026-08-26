#!/usr/bin/env python
"""evalweird.py — eval-weirdness control for the census.

For MATCHED (class-e) pills from a board-logging census session
(census_run_board.lua), compare the COMMITTED placement against the
flag-matched python golden (shipped strand20 config: fast_rtl_x
variant('winner') leaf weights + ws=20 eval47 g_stranded root-only —
the exact recipe of film_review_20260804/recon/proxy_test.py, which
predicted the chip's committed placement 3/3; NOT the weekend-era
default, per memory dr-mario-golden-is-weekend-era).

Separates "driver executed faithfully but the choice looks weird"
(genuine eval choice) from execution faults. CAVEAT (disclosed in
report): this census's committed placements come from the harness's
d1-greedy stand-in brain, not the shipped depth-3 silicon, so the
disagreement rate here characterizes the STAND-IN's weirdness ceiling;
the golden side is the shipped-config reference.

Also self-gates the board column: re-runs a python port of the Lua d1
brain on every logged board and requires it to reproduce the committed
(ccol,co4) exactly (any miss = board logging or port bug -> abort).

Next-pill (nA,nB) for the golden's depth-3 ply-2 comes from the NEXT
census row in the same round (the following spawn IS the preview).
Last pill of each round is skipped (no next known).
"""
import csv, math, sys, json
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT+"/tmp/combo_term", ROOT+"/tmp/endgame", ROOT+"/tmp/tuck", ROOT+"/tmp/pillrng",
           ROOT+"/.claude/worktrees/faithful-sim/src", QA, QA+"/tuck_v3", QA+"/eval47",
           QA+"/depth4/snap", QA+"/bitexact_gate"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np
import fast_rtl_x as FX
import root_search as RS
from fast_sim_x import NCELL, ROWS, COLS, _expand_core, _resting
from terms47 import g_stranded

WS = 20
TOPK2 = 8
W_EXCAV = int(FX._W_EXCAV_SHIP)
W_HANG = int(FX._W_HANG_SHIP)

# ---------------- python port of the Lua d1 greedy brain (census_run.lua) ----------
def _occ(bd, r, c):
    if r < 0 or r > 15 or c < 0 or c > 7: return True
    v = bd[r*8+c]; return v != 0xFF and v != 0x00

def _toprow(bd, c):
    for r in range(16):
        if _occ(bd, r, c): return r
    return 16

def _cellinfo(bd, r, c, vcells):
    if r < 0 or r > 15 or c < 0 or c > 7: return None, False
    for (vr, vc, vcol) in vcells:
        if vr == r and vc == c: return vcol, False
    v = bd[r*8+c]
    if v == 0xFF or v == 0x00: return None, False
    return v % 16, (v // 16) == 0x0D

def _runlen(bd, r, c, dr, dc, col, vcells):
    n = nv = 0
    rr, cc = r+dr, c+dc
    while True:
        ccol, isv = _cellinfo(bd, rr, cc, vcells)
        if ccol != col: break
        n += 1
        if isv: nv += 1
        rr += dr; cc += dc
    return n, nv

def _score_place(bd, cells):
    sc = 0
    for (r, c, col) in cells:
        hl, hlv = _runlen(bd, r, c, 0, -1, col, cells)
        hr, hrv = _runlen(bd, r, c, 0, 1, col, cells)
        vu, vuv = _runlen(bd, r, c, -1, 0, col, cells)
        vd, vdv = _runlen(bd, r, c, 1, 0, col, cells)
        hrun, hvir = 1+hl+hr, hlv+hrv
        vrun, vvir = 1+vu+vd, vuv+vdv
        if hrun >= 4: sc += 800 + 400*hvir
        if vrun >= 4: sc += 800 + 400*vvir
        sc += 12*max(hrun, vrun) + 6*r
        bcol, bvir = _cellinfo(bd, r+1, c, cells)
        if bvir:
            sc += 60 if bcol == col else -40
    return sc

def d1_brain(bd, cA, cB):
    bestc, besto, bestsc = 3, 0, -1e9
    for o4 in range(4):
        maxc = 6 if o4 >= 2 else 7
        for c in range(maxc+1):
            cells = None
            if o4 < 2:
                t = _toprow(bd, c)
                if t >= 2:
                    top = cA if o4 == 0 else cB
                    bot = cB if o4 == 0 else cA
                    cells = [(t-2, c, top), (t-1, c, bot)]
            else:
                t = min(_toprow(bd, c), _toprow(bd, c+1))
                if t >= 1:
                    l = cA if o4 == 2 else cB
                    r = cB if o4 == 2 else cA
                    cells = [(t-1, c, l), (t-1, c+1, r)]
            if cells:
                sc = _score_place(bd, cells)
                if sc > bestsc: bestsc, bestc, besto = sc, c, o4
    return bestc, besto

# ---------------- golden (shipped strand20, proxy_test.py recipe) -------------------
def board_arrays(bd):
    col = np.zeros(NCELL, dtype=np.int8)
    vir = np.zeros(NCELL, dtype=np.int8)
    for i in range(NCELL):
        v = bd[i]
        if v == 0xFF or v == 0x00: continue
        col[i] = (v & 0xF) + 1
        vir[i] = 1 if (v >> 4) == 0xD else 0
    return col, vir

def golden_candidates(col, vir, pA1, pB1, nA1, nB1, w, fl, ws):
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    out = []
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(COLS):
            ok, nv, cells = _expand_core(col, vir, var, cc, pA1, pB1, c1, v1)
            if ok == 0: continue
            val = RS._root_value(c1, v1, nv, cells, nA1, nB1, TOPK2, W_EXCAV, W_HANG, w, fl)
            if ws: val = val - ws * int(g_stranded(c1, v1))
            rok, r0, c0, r1, c1_ = _resting(col, var, cc)
            out.append({"o4": o4, "col": cc, "val": float(val),
                        "cells": sorted([(int(r0), int(c0)), (int(r1), int(c1_))])})
    out.sort(key=lambda d: -d["val"])
    for i, d in enumerate(out): d["rank"] = i+1
    return out

def placement_cells(bd, cA, cB, colx, o4):
    """resting cells+colors of (col,o4) on board bd, d1-brain geometry."""
    if o4 < 2:
        t = _toprow(bd, colx)
        if t < 2: return None
        top = cA if o4 == 0 else cB
        bot = cB if o4 == 0 else cA
        return sorted([(t-2, colx, top), (t-1, colx, bot)])
    t = min(_toprow(bd, colx), _toprow(bd, colx+1))
    if t < 1: return None
    l = cA if o4 == 2 else cB
    r = cB if o4 == 2 else cA
    return sorted([(t-1, colx, l), (t-1, colx+1, r)])

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k/n; den = 1+z*z/n; ctr = p+z*z/(2*n)
    adj = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((ctr-adj)/den, (ctr+adj)/den)

def main():
    csvs = sys.argv[1:]
    rows = []
    for path in csvs:
        with open(path) as f:
            for r in csv.DictReader(f):
                rows.append(r)
    ok = [r for r in rows if r["flag"] in ("ok", "latecatch") and r.get("board128")
          and int(r["ccol"]) >= 0]
    # 1) GATE: python d1 port must reproduce every committed placement from the board
    bad = 0
    for r in ok:
        bd = [int(r["board128"][i*2:i*2+2], 16) for i in range(128)]
        pc, po = d1_brain(bd, int(r["cA"]), int(r["cB"]))
        if (pc, po) != (int(r["ccol"]), int(r["co4"])):
            bad += 1
            print(f"GATE-MISS seq={r['seq']} rnd={r['round']} committed=({r['ccol']},{r['co4']}) port=({pc},{po})")
    print(f"[gate] d1-port reproduces committed: {len(ok)-bad}/{len(ok)}")
    if bad:
        print("ABORT: board column or port unfaithful"); sys.exit(1)

    FX.warmup_ship_eh(topk2=TOPK2)
    w_win, fl_win = FX.variant("winner")

    # 2) eval-weirdness on consecutive-pair samples (next pill = next row's cA,cB)
    n = agree_cells = agree_exact = agree_col = 0
    ranks = []; gaps = []
    disagreements = []
    byidx = {}
    for r in ok:
        byidx[(r["round"], int(r["seq"]))] = r
    for r in ok:
        nxt = byidx.get((r["round"], int(r["seq"])+1))
        if nxt is None or nxt["round"] != r["round"]: continue
        bd = [int(r["board128"][i*2:i*2+2], 16) for i in range(128)]
        cA, cB = int(r["cA"]), int(r["cB"])
        nA, nB = int(nxt["cA"]), int(nxt["cB"])
        col, vir = board_arrays(bd)
        cands = golden_candidates(col, vir, cA+1, cB+1, nA+1, nB+1, w_win, fl_win, WS)
        if not cands: continue
        top = cands[0]
        ccol, co4 = int(r["ccol"]), int(r["co4"])
        com_cells = placement_cells(bd, cA, cB, ccol, co4)
        top_cells = placement_cells(bd, cA, cB, top["col"], top["o4"])
        n += 1
        same_cells = (com_cells is not None and com_cells == top_cells)
        if same_cells: agree_cells += 1
        if (ccol, co4) == (top["col"], top["o4"]): agree_exact += 1
        if ccol == top["col"]: agree_col += 1
        # rank of the committed placement in the golden ordering (cell-equivalent)
        crank = None; cval = None
        for d in cands:
            dc = placement_cells(bd, cA, cB, d["col"], d["o4"])
            if dc == com_cells:
                crank = d["rank"]; cval = d["val"]; break
        ranks.append(crank if crank else len(cands)+1)
        if cval is not None: gaps.append(top["val"] - cval)
        if not same_cells:
            disagreements.append(dict(seq=r["seq"], round=r["round"], cA=cA, cB=cB,
                                      committed=(ccol, co4), golden=(top["col"], top["o4"]),
                                      committed_rank=crank, gap=(top["val"]-cval) if cval is not None else None,
                                      h=r["h_go"], vc=r["vc_go"]))
    dis = n - agree_cells
    lo, hi = wilson(dis, n)
    print(f"\n[evalweird] samples={n} (matched pills with known next)")
    print(f"  committed == golden argmax (cell-equivalent): {agree_cells}/{n} "
          f"({100*agree_cells/n:.1f}%)   disagreement {dis}/{n} = {100*dis/n:.2f}% "
          f"CI95 [{100*lo:.2f}, {100*hi:.2f}]")
    print(f"  exact (col,o4) agreement: {agree_exact}/{n}; column-only agreement: {agree_col}/{n}")
    import collections
    rc = collections.Counter(ranks)
    print(f"  committed rank in golden ordering: {dict(sorted(rc.items()))}")
    if gaps:
        gaps.sort()
        print(f"  golden-top minus committed value gap (0 when agreeing): median={gaps[len(gaps)//2]:.1f} "
              f"p90={gaps[int(len(gaps)*0.9)]:.1f} max={gaps[-1]:.1f}")
    with open(csvs[0].rsplit('/',1)[0] + "/evalweird_disagreements.json", "w") as f:
        json.dump(disagreements, f, indent=1)
    print(f"  wrote {len(disagreements)} disagreement records")

if __name__ == "__main__":
    main()
