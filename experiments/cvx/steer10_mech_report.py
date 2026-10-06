#!/usr/bin/env python3
"""STEER10 mechanism-check report (steer10_mech.py outputs in steer10/mech/ -> steer10/mech_check.txt).

Part 1  DECISIONS on the observed boards (dec_<variant>.jsonl), per game:
  eseal events: a root's soft b1 newly SEALS an EDGE-column virus (LIVE on the board, SEALED on b1; rules_steer10
                _edge_live = cascade_leaf6_x._vdist kdig 0). Counted for silicon's landing (when a straight drop), the
                base brain (DIST60) and the variant. "kept open" = boards where base seals an edge virus and the
                variant's choice seals none.
  dig: on boards with >= 1 SEALED edge column (top virus sealed), the summed edge DIG COST on b1 of the variant's
                choice minus base's (negative = the variant digs more), and the share of such boards where the
                variant's b1 dig cost is lower.
  changed: decisions where the variant's action != base's.
  reach-loss raises: boards where the action's soft b1 lifts an edge SIDE (col 0+1 / 6+7, edge column holding a
                virus) from < 13 to >= 13 (the reach_fw_tap band where col 0 / 7 leaves the mask), for base and the
                variant; "avoided" = base raises and the variant does not.
Part 2  BRAIN-ONLY REPLAYS (rep_<variant>_<game>.jsonl): AI-WIN / AI-LOSS / OPEN per start, vs base, per game; in her
  wins (+ m5g2) the starts escaping the stall; in the AI's wins the starts that newly LOSE (harm).
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rules_steer10 as R  # noqa: E402
import steer10_mech as SM  # noqa: E402
from cascade_link_x import board_flat  # noqa: E402

MECH = SM.MECH
HERWINS = ("m1g2", "m1g4", "m2g3", "m5g2")


def b1_metrics(col, vir, a, ca, cb):
    """(newly sealed edge viruses, edge dig cost over the ROOT-sealed edge columns) of action a's soft b1."""
    sbc = np.empty(col.shape[0], dtype=np.int8); sbv = np.empty(col.shape[0], dtype=np.int8)
    if a is None or R._soft_b1(col, vir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
        return None
    r0 = np.empty(col.shape[0], dtype=np.int64); r1 = np.empty(col.shape[0], dtype=np.int64)
    R._edge_live(col, vir, r0); R._edge_live(sbc, sbv, r1)
    nseal = int(((r0 == 1) & (r1 == 0)).sum())
    dig = 0
    for c in R.EDGE:
        if R._col_sealed_top(col, vir, c) == 1:
            dig += int(R._dig_cost(sbc, sbv, c))
    return nseal, dig


def side_raise(col, vir, a, ca, cb, lim=13):
    """1 if action a's soft b1 lifts a side (col 0+1 / 6+7) whose EDGE column holds a virus from < lim to >= lim
    (the reach-loss height band, reach_fw_tap), else 0; None if no legal b1."""
    sbc = np.empty(col.shape[0], dtype=np.int8); sbv = np.empty(col.shape[0], dtype=np.int8)
    if a is None or R._soft_b1(col, vir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
        return None
    n = 0
    for e, c0, c1 in ((0, 0, 1), (7, 6, 7)):
        if not any(vir[r * 8 + e] for r in range(16)):
            continue
        if R._side_h(col, c0, c1) < lim <= R._side_h(sbc, c0, c1):
            n = 1
    return n


def sealed_edge_cols(col, vir):
    return sum(1 for c in R.EDGE if R._col_sealed_top(col, vir, c) == 1)


def part1(variants, out):
    import analyze_g2 as A
    os.chdir(SM.CF)
    boards = {}
    for g in SM.GAMES:
        for q in SM.cases(g):
            S = q["S"]
            b = A.board_from_strings(S["color"], S["virus"], S["link"])
            col, vir = board_flat(b)
            boards[(g, q["p"])] = (col, vir, q)
    out("PART 1 -- decisions on the observed boards (silicon / base = DIST60 faithful brain / variant)")
    out(f"{'variant':20s} {'game':5s} | {'sil eseal':>9s} {'base eseal':>10s} {'var eseal':>9s} {'kept open':>9s} | "
        f"{'dig boards':>10s} {'var digs more':>13s} {'d dig cost':>10s} | {'changed':>7s} {'fired':>5s} | "
        f"{'reach-loss raises: base':>6s} {'var':>6s} {'avoided':>6s}")
    for v in variants:
        path = os.path.join(MECH, f"dec_{v}.jsonl")
        if not os.path.exists(path):
            continue
        rows = [json.loads(l) for l in open(path)]
        for g in SM.GAMES:
            gr = [r for r in rows if r["game"] == g]
            se = be = ve = kept = 0; nd = more = 0; dd = 0; ch = sum(int(r["a"] != r["a_base"]) for r in gr)
            rb = rv = ravo = 0
            fi = sum(r["fired"] for r in gr)
            for r in gr:
                col, vir, q = boards[(g, r["p"])]
                ca, cb = q["cur"]
                ms = b1_metrics(col, vir, r["a_sil"], ca, cb)
                mb = b1_metrics(col, vir, r["a_base"], ca, cb)
                mv = b1_metrics(col, vir, r["a"], ca, cb)
                if ms and ms[0] > 0:
                    se += 1
                if mb and mb[0] > 0:
                    be += 1
                    if mv and mv[0] == 0:
                        kept += 1
                if mv and mv[0] > 0:
                    ve += 1
                xb = side_raise(col, vir, r["a_base"], ca, cb); xv = side_raise(col, vir, r["a"], ca, cb)
                rb += int(bool(xb)); rv += int(bool(xv)); ravo += int(bool(xb) and xv == 0)
                if sealed_edge_cols(col, vir) and mb and mv:
                    nd += 1; dd += mv[1] - mb[1]; more += int(mv[1] < mb[1])
            out(f"{v:20s} {g:5s} | {se:9d} {be:10d} {ve:9d} {kept:9d} | {nd:10d} {more:13d} {dd:+10d} | {ch:7d} {fi:5d} | "
                f"{rb:6d} {rv:6d} {ravo:6d}")
        out("")


def part2(variants, out):
    out("PART 2 -- brain-only replays (observed capsules + observed garbage, perfect execution), per start")
    base = {}
    for g in SM.GAMES:
        p = os.path.join(MECH, f"rep_base_{g}.jsonl")
        if os.path.exists(p):
            base[g] = {r["p0"]: r for r in map(json.loads, open(p))}
    out(f"{'variant':20s} " + " ".join(f"{g:>16s}" for g in SM.GAMES))
    out(f"{'':20s} " + " ".join(f"{'WIN/LOSS/OPEN':>16s}" for g in SM.GAMES))
    summ = {}
    for v in variants:
        cells = []; tot = Counter()
        for g in SM.GAMES:
            p = os.path.join(MECH, f"rep_{v}_{g}.jsonl")
            if not os.path.exists(p) or g not in base:
                cells.append(f"{'-':>16s}"); continue
            X = {r["p0"]: r for r in map(json.loads, open(p))}
            c = Counter(r["class"] for r in X.values())
            fixed = sum(1 for s in X if s in base[g] and base[g][s]["class"] != "AI-WIN" and X[s]["class"] == "AI-WIN")
            new = sum(1 for s in X if s in base[g] and base[g][s]["class"] == "AI-WIN" and X[s]["class"] != "AI-WIN")
            tot["fixed"] += fixed; tot["new"] += new
            if g in HERWINS:
                tot["herwin_win"] += c["AI-WIN"]; tot["herwin_n"] += len(X)
            else:
                tot["aiwin_loss"] += c["AI-LOSS"]; tot["aiwin_n"] += len(X)
            cells.append(f"{c['AI-WIN']:>4d}/{c['AI-LOSS']:>3d}/{c['OPEN']:>3d} +{fixed}-{new}".rjust(16))
            if g == "m1g4":                       # she was at 3 when silicon topped out: an OPEN start is AHEAD at <= 3
                tot["m1g4_ahead"] += sum(1 for r in X.values() if r["class"] == "OPEN" and r["viruses_end"] <= 3)
                tot["m1g4_vend"] = float(np.median([r["viruses_end"] for r in X.values()]))
        out(f"{v:20s} " + " ".join(cells))
        summ[v] = tot
    out("")
    out("SUMMARY: her wins (m1g2, m1g4, m2g3) + m5g2: starts the brain WINS from; the AI's 6 wins: starts it LOSES from;"
        " fixed/new vs base summed over all games")
    for v, t in summ.items():
        out(f"  {v:20s} her-win games: AI wins from {t['herwin_win']:3d}/{t['herwin_n']:3d}   AI-win games: AI loses from "
            f"{t['aiwin_loss']:3d}/{t['aiwin_n']:3d}   starts fixed {t['fixed']:3d} / new {t['new']:3d}   m1g4 OPEN starts at <= 3 "
            f"viruses (ahead of her 3): {t['m1g4_ahead']:3d}, median viruses at the end {t.get('m1g4_vend', float('nan')):.0f}")


if __name__ == "__main__":
    variants = list(SM.VARIANTS)
    lines = []

    def out(s=""):
        print(s); lines.append(s)
    part2(variants, out)
    out("")
    part1(variants, out)
    open(os.path.join(HERE, "steer10", "mech_check.txt"), "w").write("\n".join(lines) + "\n")
