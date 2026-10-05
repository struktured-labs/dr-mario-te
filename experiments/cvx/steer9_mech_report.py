#!/usr/bin/env python3
"""STEER9 mechanism-check REPORT (reads steer9/mech_cases.jsonl written by steer9_mech.py; recomputes the boards).

SEAL EVENTS on the OBSERVED trajectory: a virus LIVE on board k and SEALED (or still present and sealed) on board k+1
(route predicate = seal_steer9._routes). Attributed to the AI's own placement k iff the silicon move's soft b1 already
seals it (own), else to what happened between (garbage / resolve differences = other). For every OWN seal event:
silicon == base brain? does the base brain's choice seal the SAME virus? does each rule's choice?
Plus per-game rates and the critical-move tables (M5 G2 p4/p13/p14 + col-6 cells to p65; M4 G2; lulu G1 (8,2)).

  NUMBA_CACHE_DIR=<the steer9_mech cache> python steer9_mech_report.py > steer9/mech_check.txt
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import steer9_mech as M  # noqa: E402
import seal_steer9 as S9  # noqa: E402
from cascade_link_x import board_flat  # noqa: E402

V = list(M.VARIANTS)
NC = 128


def sealed_by(col, vir, a, ca, cb):
    """set of virus idx LIVE on the root and SEALED on the soft b1 of root a (None if a is None / illegal)."""
    if a is None:
        return None
    r0 = np.empty(NC, np.int64); r1 = np.empty(NC, np.int64)
    sbc = np.empty(NC, np.int8); sbv = np.empty(NC, np.int8)
    S9._routes(col, vir, r0)
    if S9._soft_b1(col, vir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
        return None
    S9._routes(sbc, sbv, r1)
    return {i for i in range(NC) if r0[i] == 1 and r1[i] == 0}


def rc(i):
    return f"({i // 8},{i % 8})"


def main():
    rows = defaultdict(dict)
    for l in open(os.path.join(HERE, "steer9", "mech_cases.jsonl")):
        r = json.loads(l)
        rows[r["game"]][r["p"]] = r
    games = {"m5g2": M.boards_m5g2(), "m4g2": M.boards_cases(os.path.join(M.CF, "cases_m4g2_fair_20261004.jsonl"), "p"),
             "lulu1": M.boards_cases(os.path.join(M.CF, "cases_lulu_20260927.jsonl"), "k_game", label="9/27 lulu G1")}
    print("STEER9 MECHANISM CHECK on banked couch boards (silicon-faithful brain = Leaf6FwDecider all fw switches on, "
          "DIST60, deployed reach mask)\n")
    print("Variants:", json.dumps(M.VARIANTS))
    for g, B in games.items():
        R = rows[g]
        n = len(R)
        print(f"\n################ {g}: {n} placements ################")
        base_seal = sum(1 for r in R.values() if (r["base_sealV"] or 0) > 0)
        sil_seal = sum(1 for r in R.values() if (r["sil_sealV"] or 0) > 0)
        sil_eq = sum(1 for r in R.values() if r["silicon_is_base"])
        print(f"silicon == base brain {sil_eq}/{n}; base choice newly seals >=1 virus on {base_seal}/{n} "
              f"({100 * base_seal / n:.0f}%); silicon move newly seals on {sil_seal}/{n}; "
              f"root boards with a 0-seal allowed alternative {sum(r['alt0V'] for r in R.values())}/{n}; "
              f"sealed viruses on the root board, median {int(np.median([r['nsealed_root'] for r in R.values()]))} "
              f"of median {int(np.median([r['vc'] for r in R.values()]))}")
        for v in V:
            ch = [r for r in R.values() if r[v] != r["base"]]
            kind = "sealC" if v.startswith("C_") else "sealV"
            ok0 = sum(1 for r in ch if (r[v + "_" + kind] or 0) == 0)
            print(f"  {v:7s}: changes the base choice on {len(ch)}/{n} ({100 * len(ch) / n:.0f}%); new choice seals 0 "
                  f"({kind}) on {ok0}/{len(ch)}; choices that newly seal (V) {sum(1 for r in R.values() if (r[v + '_sealV'] or 0) > 0)}/{n}")
        # ---- seal events on the observed trajectory
        print(f"\n  SEAL EVENTS on the observed {g} trajectory (virus live on board k, sealed on board k+1):")
        own_tot = 0; other_tot = 0; tab = defaultdict(int)
        lines = []
        for i in range(len(B) - 1):
            x, y = B[i], B[i + 1]
            if y["p"] != x["p"] + 1:
                print(f"    (gap p{x['p']} -> p{y['p']}: transition skipped)")
                continue
            col, vir = board_flat(x["b"]); col2, vir2 = board_flat(y["b"])
            r0 = np.empty(NC, np.int64); r1 = np.empty(NC, np.int64)
            S9._routes(col, vir, r0); S9._routes(col2, vir2, r1)
            ev = {j for j in range(NC) if r0[j] == 1 and r1[j] == 0}
            if not ev:
                continue
            r = R[x["p"]]
            ca, cb = x["cur"]
            sil = sealed_by(col, vir, r["silicon"], ca, cb)
            own = ev & sil if sil is not None else set()
            other = ev - own
            own_tot += len(own); other_tot += len(other)
            if not own:
                lines.append(f"    p{x['p']:3d} vc {r['vc']:2d}  {','.join(rc(j) for j in sorted(other))}: NOT the AI's move "
                             f"(garbage / board change between reads)" + ("" if sil is not None else " [silicon move not a straight drop]"))
                continue
            bse = sealed_by(col, vir, r["base"], ca, cb) or set()
            parts = [f"silicon==base {'Y' if r['silicon_is_base'] else 'N'}", f"base seals same {'Y' if own & bse else 'N'}"]
            tab["own_events"] += 1; tab["sil_eq_base"] += int(r["silicon_is_base"]); tab["base_same"] += int(bool(own & bse))
            for v in V:
                sv = sealed_by(col, vir, r[v], ca, cb) or set()
                parts.append(f"{v} {'chg' if r[v] != r['base'] else '-'}/{'SEALS' if own & sv else 'open'}")
                tab[v + "_open"] += int(not (own & sv)); tab[v + "_open_when_base_sealed"] += int(bool(own & bse) and not (own & sv))
            lines.append(f"    p{x['p']:3d} vc {r['vc']:2d}  OWN {','.join(rc(j) for j in sorted(own))}"
                         + (f" (+other {','.join(rc(j) for j in sorted(other))})" if other else "") + ":  " + "  ".join(parts))
        print("\n".join(lines))
        print(f"  totals: {own_tot} viruses sealed by the AI's own move, {other_tot} by something else; own-seal decisions "
              f"{tab['own_events']}: silicon==base {tab['sil_eq_base']}, base would seal the same virus {tab['base_same']}")
        for v in V:
            print(f"    {v:7s}: own-seal decisions where the rule's choice keeps that virus open {tab[v + '_open']}/{tab['own_events']}; "
                  f"of the {tab['base_same']} the BASE brain would also have sealed: {tab[v + '_open_when_base_sealed']}")
        if g == "m5g2":
            print("\n  M5 G2 critical moves (col-6 wall): p4 / p13 / p14")
            for p in (4, 13, 14):
                r = R[p]
                print(f"    p{p}: silicon a={r['silicon']} (col-6 cells {r['sil_crit_cells']}, sealV {r['sil_sealV']}) "
                      f"base a={r['base']} (col-6 cells {r['base_crit_cells']}, sealV {r['base_sealV']}) silicon==base "
                      f"{r['silicon_is_base']}; " + "; ".join(f"{v} a={r[v]} c6={r[v + '_crit_cells']}" for v in V))
            sub = [R[p] for p in sorted(R) if p <= 65]
            print(f"    col-6 cells placed p0..p65: silicon {sum(r['sil_crit_cells'] for r in sub)}, base brain "
                  f"{sum(r['base_crit_cells'] for r in sub)} (per-decision counterfactual on the observed boards), "
                  + ", ".join(f"{v} {sum(r[v + '_crit_cells'] for r in sub)}" for v in V))
            print(f"    silicon moves that put a cell in col 6 (p<=65): "
                  + ", ".join(f"p{r['p']}({'=' if r['silicon_is_base'] else 'x'}base)" for r in sub if r['sil_crit_cells'] > 0))
        if g == "lulu1":
            print("\n  lulu G1 critical column 2 (yellow (8,2) sealed under a mixed own stack):")
            sub = [R[p] for p in sorted(R) if R[p]["sil_crit_cells"] > 0]
            vk = None
            for x in B:
                col, vir = board_flat(x["b"])
                if vir[8 * 8 + 2] and vk is None:
                    vk = x["p"]
            print(f"    silicon moves adding cells to col 2: "
                  + ", ".join(f"p{r['p']}({'=' if r['silicon_is_base'] else 'x'}base)" for r in sub[:40]))
            print(f"    col-2 cells placed over the game: silicon {sum(r['sil_crit_cells'] for r in R.values())}, base "
                  f"{sum(r['base_crit_cells'] for r in R.values())}, " + ", ".join(f"{v} {sum(r[v + '_crit_cells'] for r in R.values())}" for v in V))


if __name__ == "__main__":
    main()
