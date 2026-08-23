#!/usr/bin/env python3
"""analyze_onevirus.py — EXPLORATORY decomposition of the one-virus-left games.

PREREG_AUTOPSY §9 licenses four shippable sentences; this script adds NONE of
them.  It answers one descriptive question the owner asked on top of the
registered deliverable: 45 of the 53 clean failures die with exactly ONE virus
left — is that ONE defect or SEVERAL?

Everything here is descriptive and is labeled EXPLORATORY in the output.  No
threshold here gates any verdict.  Every board statistic carries the standing
MATCHED WITHIN-BOARD CONTROL (random occupied cells, same board, same count),
because this corpus has already overturned two confident board findings.

Strata tested for separability:
  * result (stall vs topout) — a stalled one-virus game and a topped-out
    one-virus game are different failures wearing the same virus count;
  * verdict (AVOIDABLE vs DOOMED) from the registered rule;
  * geometry of the surviving virus: column height vs board median, edge
    column, floor rows, and the COVER DEPTH (occupied cells directly above it).

Reads out/AUTOPSY_REPORT.json + out/labels/*.json.gz; writes
out/ONEVIRUS_REPORT.json and prints a table.  ONEVIRUS_OK on success.
"""
from __future__ import annotations

import gzip
import json
import os
import random
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "out")
LABELS = os.environ.get("DRM_AUTOPSY_LABELS", os.path.join(OUT, "labels"))
ROWS, COLS = 16, 8
CONTROL_SEED = 20260822          # same stream discipline as analyze_autopsy


def heights(color):
    b = np.asarray(color) != 0
    first = np.argmax(b, axis=0)
    return np.where(b.any(axis=0), ROWS - first, 0).astype(int)


def cover_depth(color, r, c):
    """Occupied cells directly ABOVE the virus — how buried it is, counted
    rather than asserted (the refuted 'buried' story was never counted)."""
    col = np.asarray(color)[:r, c]
    return int(np.count_nonzero(col))


def load_docs():
    docs = []
    for f in sorted(os.listdir(LABELS)):
        if f.startswith("autopsy_") and f.endswith(".json.gz"):
            with gzip.open(os.path.join(LABELS, f), "rt") as fh:
                docs.append(json.load(fh))
    docs.sort(key=lambda d: d["seed"])
    return docs


def geometry(doc, rng):
    """Terminal geometry of the single surviving virus, with its matched
    within-board control.  None when the game did not end on exactly one."""
    t = doc.get("terminal")
    if not t or doc["viruses_left"] != 1:
        return None
    tc = np.array(t["color"])
    tv = np.array(t["virus"])
    cells = np.argwhere(tv != 0)
    if len(cells) != 1:
        return None
    r, c = int(cells[0][0]), int(cells[0][1])
    H = heights(tc)
    occ_cols = H > 0
    med = float(np.median(H[occ_cols])) if occ_cols.any() else 0.0
    occ = np.argwhere(tc != 0)
    # MATCHED WITHIN-BOARD CONTROL: one random occupied cell, same board.
    ctl = None
    if len(occ):
        pr, pc = (int(x) for x in occ[rng.randrange(len(occ))])
        ctl = {"col_height": int(H[pc]), "delta_median": int(H[pc]) - med,
               "cover_depth": cover_depth(tc, pr, pc),
               "edge_col": bool(pc in (0, COLS - 1)),
               "floor_row": bool(pr >= ROWS - 2)}
    return {
        "row": r, "col": c,
        "col_height": int(H[c]),
        "board_median_height": med,
        "delta_median": int(H[c]) - med,
        "shorter_than_median": bool(H[c] < med),
        "cover_depth": cover_depth(tc, r, c),
        "edge_col": bool(c in (0, COLS - 1)),
        "floor_row": bool(r >= ROWS - 2),
        "total_occupied": int(np.count_nonzero(tc)),
        "control": ctl,
    }


def summarize(rows, key):
    """mean/median of a numeric field over rows, with n."""
    xs = [r[key] for r in rows if r.get(key) is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": round(float(np.mean(xs)), 3),
            "median": float(np.median(xs)),
            "min": float(np.min(xs)), "max": float(np.max(xs))}


def main():
    rep_path = os.path.join(OUT, "AUTOPSY_REPORT.json")
    if not os.path.exists(rep_path):
        sys.exit("no AUTOPSY_REPORT.json — run analyze_autopsy.py first")
    rep = json.load(open(rep_path))
    verdict = {g["seed"]: g["verdict"] for g in rep["games"]}
    clair = {g["seed"]: g["clair_avoidable"] for g in rep["games"]}

    rng = random.Random(CONTROL_SEED)
    rows = []
    for d in load_docs():
        g = geometry(d, rng)
        if g is None:
            continue
        rows.append(dict({"seed": d["seed"], "result": d["result"],
                          "n_moves": d["n_moves"], "anchor": d["anchor"],
                          "verdict": verdict.get(d["seed"]),
                          "clair_avoidable": clair.get(d["seed"])}, **g))

    n = len(rows)
    strata = {}
    for name, sel in (
        ("all", lambda r: True),
        ("stall", lambda r: r["result"] == "stall"),
        ("topout", lambda r: r["result"] == "topout"),
        ("avoidable", lambda r: r["verdict"] == "AVOIDABLE"),
        ("doomed", lambda r: r["verdict"] == "DOOMED"),
    ):
        sub = [r for r in rows if sel(r)]
        if not sub:
            strata[name] = {"n": 0}
            continue
        ctl = [r["control"] for r in sub if r["control"]]
        strata[name] = {
            "n": len(sub),
            "col_height": summarize(sub, "col_height"),
            "delta_median": summarize(sub, "delta_median"),
            "cover_depth": summarize(sub, "cover_depth"),
            "shorter_than_median": sum(1 for r in sub
                                       if r["shorter_than_median"]),
            "edge_col": sum(1 for r in sub if r["edge_col"]),
            "floor_row": sum(1 for r in sub if r["floor_row"]),
            "col_hist": dict(Counter(r["col"] for r in sub)),
            "CONTROL_delta_median": summarize(ctl, "delta_median"),
            "CONTROL_cover_depth": summarize(ctl, "cover_depth"),
            "CONTROL_edge_col": sum(1 for r in ctl if r["edge_col"]),
        }

    # ONE DEFECT OR SEVERAL: cross-tab of the two strata that could split it.
    xtab = Counter((r["result"], r["verdict"]) for r in rows)
    doc = {"EXPLORATORY": True,
           "note": ("descriptive only — PREREG_AUTOPSY §9 licenses no claim "
                    "from this file; every board statistic is quoted beside "
                    "its matched within-board control"),
           "n_one_virus": n, "strata": strata,
           "result_x_verdict": {f"{a}|{b}": v for (a, b), v in xtab.items()},
           "rows": rows}
    with open(os.path.join(OUT, "ONEVIRUS_REPORT.json"), "w") as f:
        json.dump(doc, f, indent=2)

    print(f"one-virus-left games: {n}")
    print("result x verdict:", dict(doc["result_x_verdict"]))
    for name, s in strata.items():
        if not s.get("n"):
            continue
        print(f"  {name:<10} n={s['n']:<3} "
              f"col_h {s['col_height']['mean']:<6} "
              f"delta_med {s['delta_median']['mean']:<7} "
              f"(control {s['CONTROL_delta_median'].get('mean')}) "
              f"cover {s['cover_depth']['mean']:<6} "
              f"(control {s['CONTROL_cover_depth'].get('mean')}) "
              f"edge {s['edge_col']}/{s['n']} (control {s['CONTROL_edge_col']})")
    print("ONEVIRUS_OK")


if __name__ == "__main__":
    main()
