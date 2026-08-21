#!/usr/bin/env python3
"""Failure-regime map: analysis + registered stage-2 allocator (regime-141).

Reads the farm JSONL, verifies every row against the registered cell table
(arm names, seed blocks, pressure label, level — the POPULATION gate), and
emits the map: cell x failure rate x exact CI x n.

Modes
-----
  --summarize           : the map table (default), JSON + text.
  --allocate --budget N : stage-2 allocation per the REGISTERED rule in
                          PREREG_REGIME_MAP.md sec 6. Deterministic function of
                          the stage-1 rows; emits {arm: extra_seed_count}.

Each game is one independent unit (one seed, solo, even-stride so no aliased
duplicates); "game-clustered" CIs are therefore plain exact binomial
(Clopper-Pearson) per cell.
"""
from __future__ import annotations

import argparse
import json
import sys

from scipy.stats import beta

# ---- REGISTERED CELL TABLE (must match PREREG_REGIME_MAP.md sec 4) ----------
# arm -> (variant, level, max_pills, seed_start, max_n)   seeds even, stride 2
CELLS = {
    "c1_L11_bursty": ("bursty",     11, 300, 30000, 250),
    "c2_L11_x2":     ("bursty_x2",  11, 300, 30500, 250),
    "c3_L11_aim":    ("bursty_aim", 11, 300, 31000, 250),
    "c4_L20_clean":  ("clean",      20, 400, 31500, 250),
    "c5_L20_bursty": ("bursty",     20, 400, 32000, 250),
    "c6_L20_aim":    ("bursty_aim", 20, 400, 32500, 250),
}
STAGE1_N = 50
FW_MD5 = "e970e9ab0208cdbce1d39ed33e2f51ee"   # champion s20b

FAIL_RESULTS = ("topout", "stall")


def cp_ci(k, n, alpha=0.05):
    """Clopper-Pearson exact two-sided CI."""
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def load_rows(path):
    rows, errors, bad = [], [], []
    with open(path) as fh:
        for i, ln in enumerate(fh):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                bad.append(i)
                continue
            if r.get("result") == "ERROR":
                errors.append(r)
                continue
            rows.append(r)
    return rows, errors, bad


def validate(rows):
    """POPULATION gate: every row must belong to its registered cell."""
    problems = []
    seen = {}
    for r in rows:
        arm = r.get("arm")
        if arm not in CELLS:
            problems.append(f"row seed={r.get('seed')} has UNREGISTERED arm {arm!r}")
            continue
        variant, level, max_pills, seed_start, max_n = CELLS[arm]
        s = int(r["seed"])
        lo, hi = seed_start, seed_start + 2 * (max_n - 1)
        if s % 2 or not (lo <= s <= hi):
            problems.append(f"{arm}: seed {s} outside registered even block "
                            f"[{lo},{hi}]")
        if r.get("level") != level:
            problems.append(f"{arm}: seed {s} level={r.get('level')} != {level}")
        if r.get("pressure_model") != variant:
            problems.append(f"{arm}: seed {s} pressure_model="
                            f"{r.get('pressure_model')!r} != {variant!r}")
        if r.get("fw_md5") != FW_MD5:
            problems.append(f"{arm}: seed {s} fw_md5={r.get('fw_md5')} != champion")
        key = (arm, s)
        if key in seen:
            problems.append(f"{arm}: DUPLICATE row for seed {s}")
        seen[key] = 1
        # variant-binding audits, end-to-end from the row's own volley capture
        if variant == "bursty_aim":
            for gp, added, n_cells, cols in r.get("volleys", []):
                want = [3, 4][:len(cols)]
                if cols[:len(want)] != want:
                    problems.append(f"{arm}: seed {s} volley gp={gp} cols={cols} "
                                    f"NOT aimed at spawn columns")
        if variant == "clean" and r.get("garbage", 0) != 0:
            problems.append(f"{arm}: seed {s} clean row has garbage={r['garbage']}")
    return problems


def summarize(rows):
    out = {}
    for arm, (variant, level, max_pills, seed_start, max_n) in CELLS.items():
        rs = [r for r in rows if r.get("arm") == arm]
        n = len(rs)
        k = sum(1 for r in rs if r["result"] in FAIL_RESULTS)
        topout = sum(1 for r in rs if r["result"] == "topout")
        stall = sum(1 for r in rs if r["result"] == "stall")
        da = sum(1 for r in rs if r.get("dies_ahead"))
        lo, hi = cp_ci(k, n)
        clears = [r["pills"] for r in rs if r["result"] == "clear"]
        out[arm] = {
            "variant": variant, "level": level, "n": n,
            "failures": k, "topout": topout, "stall": stall,
            "dies_ahead": da,
            "rate": (k / n if n else None),
            "ci95": [round(lo, 4), round(hi, 4)],
            "garbage_per_game_mean": (round(sum(r.get("garbage", 0) for r in rs) / n, 2)
                                      if n else None),
            "pills_clear_median": (sorted(clears)[len(clears) // 2] if clears else None),
            "wall_secs_median": (sorted(r.get("wall_secs", 0) for r in rs)[n // 2]
                                 if n else None),
        }
    return out


def allocate(summary, budget):
    """REGISTERED stage-2 rule (PREREG sec 6). Deterministic.

    1. Eligible = cells with >=2 failures at stage 1. Top up eligible cells to
       max_n, priority |rate - 0.10| ascending (ties: cell name ascending);
       partial top-up allowed for the last when the budget runs out.
    2. If fewer than 2 eligible: top up the two highest-failure-count cells
       (ties: cell name ascending) to max_n under the same budget.
    3. If ALL cells have 0 failures: top up c5_L20_bursty and c6_L20_aim to
       n=150 each; every cell is then reported at its exact CP bound.
    """
    counts = {a: (summary[a]["failures"], summary[a]["n"]) for a in CELLS}
    alloc = {}

    def top_up(order, target_of):
        nonlocal alloc
        left = budget - sum(alloc.values())
        for a in order:
            need = max(0, target_of(a) - counts[a][1])
            take = min(need, left)
            if take > 0:
                alloc[a] = take
                left -= take

    eligible = [a for a in CELLS if counts[a][0] >= 2]
    if len(eligible) >= 2:
        order = sorted(eligible,
                       key=lambda a: (abs(counts[a][0] / max(1, counts[a][1]) - 0.10), a))
        top_up(order, lambda a: CELLS[a][4])
    elif any(counts[a][0] > 0 for a in CELLS):
        order = sorted(CELLS, key=lambda a: (-counts[a][0], a))[:2]
        top_up(order, lambda a: CELLS[a][4])
    else:
        top_up(["c5_L20_bursty", "c6_L20_aim"], lambda a: 150)
    return alloc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--allocate", action="store_true")
    ap.add_argument("--budget", type=int, default=600)
    ap.add_argument("--out")
    a = ap.parse_args()

    rows, errors, bad = load_rows(a.rows)
    problems = validate(rows)
    n_total = len(rows) + len(errors)
    err_rate = len(errors) / n_total if n_total else 0.0
    if problems:
        for p in problems[:20]:
            print("POPULATION-GATE FAIL:", p, file=sys.stderr)
        print(f"ANALYZE_REGIME_FAIL ({len(problems)} problems)", flush=True)
        sys.exit(1)
    if err_rate > 0.02:
        print(f"ANALYZE_REGIME_FAIL (ERROR rows {len(errors)}/{n_total} > 2%)",
              flush=True)
        sys.exit(1)

    summary = summarize(rows)
    res = {"rows": len(rows), "error_rows": len(errors), "bad_lines": len(bad),
           "cells": summary}

    if a.allocate:
        res["stage2_alloc"] = allocate(summary, a.budget)

    txt = f"{'cell':<16}{'variant':<12}{'lvl':<5}{'n':<6}{'fail':<6}" \
          f"{'rate':<8}{'ci95':<20}{'top/stall':<11}{'d.a.':<5}\n"
    for arm, c in summary.items():
        rate = f"{c['rate']:.3f}" if c["rate"] is not None else "-"
        txt += (f"{arm:<16}{c['variant']:<12}{c['level']:<5}{c['n']:<6}"
                f"{c['failures']:<6}{rate:<8}"
                f"[{c['ci95'][0]:.3f},{c['ci95'][1]:.3f}]{'':<3}"
                f"{c['topout']}/{c['stall']:<9}{c['dies_ahead']:<5}\n")
    print(txt)
    if a.allocate:
        print("stage2 allocation:", json.dumps(res["stage2_alloc"]))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
        print("wrote", a.out)
    print("ANALYZE_REGIME_OK", flush=True)


if __name__ == "__main__":
    main()
