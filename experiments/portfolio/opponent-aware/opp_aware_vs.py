#!/usr/bin/env python3
"""Task #15: opponent-aware VS eval A/B.

HYPOTHESIS (falsifiable): the champion -- the shipped strand20 decide path,
fast_rtl_x.variant("winner") leaf + eval47/terms47.g_stranded applied
ROOT-ONLY at ws=20, exactly ab47.py::_choose_base(wt=0, ws=20) -- is entirely
SELF-REGARDING: it never reads the opponent's board when scoring a move. A
single opponent-aware root term should let a candidate beat the blind
champion in VS. If no weight of that term beats k=0, the hypothesis is DEAD.

THE ONE TERM CHOSEN (and why, over the alternatives named in the task brief):
  val += k * opp_danger * cells
    opp_danger = min(1, max(col_height[3], col_height[4]) / 16)  -- how close
      the OPPONENT's spawn lane is to topping out (0 = empty spawn cols,
      1 = one placement from spawn-block), read off opp_board at decision
      time. Fixed for the whole decision (our own candidates don't change
      the opponent's board).
    cells = the CANDIDATE's own round-1 matched-cell count, already computed
      by fast_sim_x._expand_core for every one of the 32 base candidates.
      This is the ROM-true driver of the attack channel: comboCounter/
      attackSize scale with matched cells, and "cells>=7" is the documented
      ROM-true single-round attack proxy (memory dr-mario-rom-attack-rule,
      99.9% precision / 100% recall over 6078 clears). Weighting it by the
      opponent's spawn-lane fullness is the most literal, cheapest,
      single-weight reading of the task's own phrasing -- "time aggression
      to their vulnerability" -- because it reaches for exactly the
      candidate-scoring number that already produces damage (cells), gated
      by exactly the board fact that predicts a kill (spawn-lane height).
    REJECTED alternatives (more code, same one-weight budget spent worse):
      - reward virus-clear count (nv) instead of cells: nv is already
        VBONUS-boosted and less tightly ROM-linked to the attack channel
        than cells is.
      - "value survival more when opponent is safe": requires a NEGATIVE
        term on risk-taking, i.e. a second free parameter (what counts as
        risk) on top of k -- not a one-weight test.
    k=0 must be algebraically AND bit-exactly identical to the champion
    (additive zero) -- asserted by selfcheck() before any match is played.

OPPONENT IN EVERY MATCH: the champion decider itself (bit-exact reproduction
of ab47.py::_choose_base(wt=0, ws=20) / reach_root.choose_base32), never a
depth-1 strawman -- per the task's explicit instruction.

SIMULATOR: the ROM-true Python VS harness, vs_harness.play_match
(dr_mario_rl/tmp/vs_aware/vs_harness.py, "THE consolidated VS harness" --
five mechanics fixes landed 2026-07-31, HARNESS_REV stamped in every result).
This is an OFFLINE python/py65-adjacent simulator, not Verilator RTL co-sim --
per house doctrine (CANDIDATE_TIER3.md sec 10) any move-choice claim from
this harness is provisional until it clears the Verilator farm being built
by cosim-farm. This thread's claim is scoped to "does the python VS harness
show a signal at all" -- the cheapest gate before spending RTL time.

STATS: h2h_vs.py's own paired-seed, side-swapped, seed-level bootstrap CI
machinery is reused (imported), not reinvented -- avoids re-deriving the
sender/receiver attack-index convention trap documented there.
"""
from __future__ import annotations

import sys
import os
import json
import time
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src",
           QA, QA + "/tuck_v3", QA + "/eval47", ROOT + "/tmp/vs_aware"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# h2h_vs.py's bootstrap/attack-index helpers, reused not reinvented.
sys.path.insert(0, QA)
from h2h_vs import boot_ci, attacks_sent  # noqa: E402

WS = 20          # shipped strand20 dose
TOPK2 = 8

_L = {}


def _lazy():
    """Import + numba-warm the champion decide path exactly once per process."""
    if _L:
        return _L
    import numpy as np
    import fast_rtl_x as FX
    import fast_sim_x as FS
    import root_search as RS
    from fb import FB
    from terms47 import g_stranded
    import vs_harness as H

    FX.warmup_ship_eh(topk2=TOPK2)
    w, fl = FX.variant("winner")
    z = np.zeros(FS.NCELL, dtype=np.int8)
    g_stranded(z, z)   # jit warmup so the first real decision never pays compile time
    _L.update(FX=FX, FS=FS, RS=RS, FB=FB, g_stranded=g_stranded, w=w, fl=fl, H=H, np=np)
    return _L


def _choose(col, vir, ca, cb, na, nb, k=0.0, opp_danger=0.0):
    """base32 root search with the #47 g_stranded ws=20 tax, PLUS the
    opponent-aware term k*opp_danger*cells. At k=0 this is EXACTLY
    ab47.py::_choose_base(wt=0, ws=20) -- the term is an additive zero."""
    L = _lazy()
    FX, FS, RS, g_stranded = L["FX"], L["FS"], L["RS"], L["g_stranded"]
    w, fl, np = L["w"], L["fl"], L["np"]
    c1 = np.empty(FS.NCELL, dtype=np.int8)
    v1 = np.empty(FS.NCELL, dtype=np.int8)
    best_val, best_a = None, None
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = FS._expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, TOPK2,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            val -= WS * g_stranded(c1, v1)
            if k:
                val += k * opp_danger * cells
            if best_val is None or val > best_val:
                best_val, best_a = val, var * 8 + cc
    return best_a


def _opp_danger(opp_board):
    h = opp_board.column_heights()
    return min(1.0, float(max(h[3], h[4])) / 16.0)


def champion_dec(board, cur, nxt, opp_board):
    """The champion, bit-exact, wrapped in the 4-arg opp-aware signature but
    NOT reading opp_board -- the blind baseline / VS opponent."""
    L = _lazy()
    FB, RS = L["FB"], L["RS"]
    fb = FB.from_board(board)
    col, vir = RS.board_flat_from_fb(fb)
    return _choose(col, vir, int(cur.a), int(cur.b), int(nxt.a), int(nxt.b), k=0.0)


def make_oppaware_dec(k):
    def dec(board, cur, nxt, opp_board):
        L = _lazy()
        FB, RS = L["FB"], L["RS"]
        fb = FB.from_board(board)
        col, vir = RS.board_flat_from_fb(fb)
        od = _opp_danger(opp_board)
        return _choose(col, vir, int(cur.a), int(cur.b), int(nxt.a), int(nxt.b),
                       k=k, opp_danger=od)
    return dec


# ------------------------------------------------------------------ selfcheck
def selfcheck(n=200, seed=7):
    """(a) k=0 must reproduce reach_root.choose_base32 bit-for-bit (the term
    is a true additive zero, not just 'usually the same action').
    (b) k=40 must move >= 1 decision in the corpus (the term is actually
    wired to the search, not dead code)."""
    _lazy()
    import numpy as np
    import reach_root as RR
    RR._lazy()
    rng = np.random.default_rng(seed)
    moved = 0
    mism0 = 0
    for t in range(n):
        col = np.zeros(128, dtype=np.int8)
        vir = np.zeros(128, dtype=np.int8)
        for i in range(128):
            r = i // 8
            if r >= 8 and rng.random() < 0.35:
                col[i] = rng.integers(1, 4)
                if rng.random() < 0.5:
                    vir[i] = 1
        ca, cb, na, nb = (int(rng.integers(1, 4)) for _ in range(4))
        ref = RR.choose_base32(col, vir, ca, cb, na, nb, ws=WS, topk2=TOPK2)["action"]
        mine0 = _choose(col, vir, ca, cb, na, nb, k=0.0)
        if mine0 != ref:
            mism0 += 1
        mine_k = _choose(col, vir, ca, cb, na, nb, k=40.0, opp_danger=1.0)
        if mine_k != mine0:
            moved += 1
    ok = (mism0 == 0) and (moved > 0)
    print(f"[selfcheck] k=0 vs reach_root.choose_base32: {n - mism0}/{n} bit-identical "
          f"({'PASS' if mism0 == 0 else 'FAIL'})")
    print(f"[selfcheck] k=40,opp_danger=1 moved {moved}/{n} decisions "
          f"({'PASS' if moved > 0 else 'FAIL -- term is dead code'})")
    return ok


# ------------------------------------------------------------------- VS runner
_CFG = {}


def _init(cfg):
    global _CFG
    _lazy()
    _CFG = cfg


def _one(job):
    seed, swap = job
    L = _lazy()
    H = L["H"]
    k = _CFG["k"]
    cand = make_oppaware_dec(k)
    ref = champion_dec
    a, b = (cand, ref) if not swap else (ref, cand)
    r = H.play_match(seed, a, b, level=_CFG["level"], max_pills=_CFG["max_pills"],
                     nes_pills=_CFG["nes_pills"], garbage=_CFG["garbage"])
    side = 0 if not swap else 1
    win = 1.0 if r["winner"] == side else (0.0 if r["winner"] >= 0 else 0.5)
    margin = r["margin"] if side == 0 else -r["margin"]
    return {"seed": seed, "swap": swap, "win": win, "margin": margin,
            "reason": r["reason"], "draw": r["winner"] < 0,
            "atk_cand": attacks_sent(r, side), "atk_ref": attacks_sent(r, 1 - side),
            "pills_cand": r["pills"][side]}


def run(k, seeds, workers=4, level=11, max_pills=300, nes_pills=True, garbage=True):
    cfg = {"k": k, "level": level, "max_pills": max_pills, "nes_pills": nes_pills,
           "garbage": garbage}
    jobs = [(s, sw) for s in seeds for sw in (0, 1)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(cfg,)) as ex:
        rows = list(ex.map(_one, jobs, chunksize=1))
    dt = time.time() - t0

    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["seed"], []).append(r)
    wr_seed, mg_seed = [], []
    for s, rs in by_seed.items():
        wr_seed.append(sum(x["win"] for x in rs) / len(rs))
        mg_seed.append(sum(x["margin"] for x in rs) / len(rs))

    lo, hi = boot_ci(wr_seed)
    mlo, mhi = boot_ci(mg_seed)
    dec = [w for w in wr_seed if w != 0.5]
    decisive = len(dec) / len(wr_seed) if wr_seed else float("nan")
    wr_dec = (sum(dec) / len(dec)) if dec else float("nan")

    return {
        "k": k, "n_seeds": len(by_seed), "n_matches": len(rows),
        "winrate": sum(wr_seed) / len(wr_seed), "wr_lo": lo, "wr_hi": hi,
        "margin": st.mean(mg_seed), "mg_lo": mlo, "mg_hi": mhi,
        "draws": sum(1 for r in rows if r["draw"]),
        "atk_cand": sum(r["atk_cand"] for r in rows) / len(rows),
        "atk_ref": sum(r["atk_ref"] for r in rows) / len(rows),
        "pills_cand": st.mean([r["pills_cand"] for r in rows]),
        "sec_per_match": dt / len(rows) * workers, "wall_s": dt,
        "decisive": decisive, "wr_decisive": wr_dec,
        "wr_seed": wr_seed, "mg_seed": mg_seed,
        "rows": rows,
    }


def fmt(r):
    return (f"k={r['k']:<8g} winrate {r['winrate']:6.1%}  95% CI [{r['wr_lo']:.1%}, {r['wr_hi']:.1%}]"
            f"   margin {r['margin']:+6.2f} [{r['mg_lo']:+.2f}, {r['mg_hi']:+.2f}]"
            f"   n={r['n_seeds']} seeds / {r['n_matches']} matches"
            f"   draws {r['draws']}  atk {r['atk_cand']:.2f}v{r['atk_ref']:.2f}"
            f"   moved {r['decisive']:.0%}, won {r['wr_decisive']:.1%} of those")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--ks", type=float, nargs="+", default=[0.0, 2.0, 5.0, 10.0, 20.0, 40.0])
    ap.add_argument("--seed0", type=int, default=700)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--no-garbage", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    if a.selfcheck:
        ok = selfcheck()
        sys.exit(0 if ok else 1)

    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    print(f"L{a.level}  real NES capsules  garbage={'OFF' if a.no_garbage else 'ON'}"
          f"  seeds {a.seed0}..{a.seed0 + a.seeds - 1}  ks={a.ks}")
    results = []
    for k in a.ks:
        r = run(k, seeds, workers=a.workers, level=a.level, max_pills=a.max_pills,
                garbage=not a.no_garbage)
        print(fmt(r))
        results.append({kk: vv for kk, vv in r.items() if kk not in ("rows",)})
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
