#!/usr/bin/env python3
"""analyze_autopsy.py — PREREG_AUTOPSY §4/§7: verdicts, defect clusters, and
the time-before-death distribution.  Mechanical; no discretion.

Every board property reported about these fatal boards carries a MATCHED
WITHIN-BOARD CONTROL (random occupied cells, same board, same count) — the
standing rule for this corpus, which has already overturned two confident
findings.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OUT = os.path.join(HERE, "out")
LABELS = os.path.join(OUT, "labels")
ROWS, COLS, NCELL = 16, 8, 128
CONTROL_SEED = 20260822


def planes(b64):
    raw = base64.b64decode(b64)
    c = np.frombuffer(raw[:NCELL], dtype=np.int8).reshape(ROWS, COLS)
    v = np.frombuffer(raw[NCELL:], dtype=np.int8).reshape(ROWS, COLS)
    return c, v


def heights(color):
    b = np.asarray(color) != 0
    first = np.argmax(b, axis=0)
    return np.where(b.any(axis=0), ROWS - first, 0).astype(int)


def dsh(color):
    """Spawn-lane height: the champion's own d_spawn_h (cols 3-4)."""
    H = heights(color)
    return int(max(H[3], H[4]))


def clopper_pearson(k, n, alpha=0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def load_docs():
    docs = []
    for f in sorted(os.listdir(LABELS)):
        if f.startswith("autopsy_") and f.endswith(".json.gz"):
            with gzip.open(os.path.join(LABELS, f), "rt") as fh:
                docs.append(json.load(fh))
    docs.sort(key=lambda d: d["seed"])
    return docs


def classify(doc, st, claim):
    """§7 defect clusters for ONE firing ply.  Clusters OVERLAP by design."""
    ents = {e["key"]: e for e in st["cands"]}
    ch, be = ents[claim["champ_key"]], ents[claim["best_key"]]
    vals = st["vals"]
    vch = vals[ch["rep_slot"]]
    vbe = vals[be["rep_slot"]]
    tags = []

    # (a) tie-at-the-cliff
    if vch is not None and vbe is not None and abs(vch - vbe) < 1e-6:
        tags.append("tie_at_cliff")
    # (b) deferred-clearing failure — the better move leaves MORE viruses NOW
    if be["vir_after"] > ch["vir_after"]:
        tags.append("deferred_clearing")
    # (c) spawn-lane self-block
    ch_c, _ = planes(ch["planes"])
    be_c, _ = planes(be["planes"])
    d_ch, d_be = dsh(ch_c), dsh(be_c)
    if d_ch >= d_be + 2:
        tags.append("spawn_lane_selfblock")
    # (d) last-virus notch — the controlled statistic, NOT "buried"
    notch = None
    if doc["viruses_left"] == 1 and doc.get("terminal"):
        tc = np.array(doc["terminal"]["color"])
        tv = np.array(doc["terminal"]["virus"])
        cells = np.argwhere(tv != 0)
        if len(cells) == 1:
            r, c = int(cells[0][0]), int(cells[0][1])
            H = heights(tc)
            occ = H > 0
            med = float(np.median(H[occ])) if occ.any() else 0.0
            notch = {"row": r, "col": c, "col_height": int(H[c]),
                     "board_median_height": med,
                     "shorter_than_median": bool(H[c] < med),
                     "floor_row": bool(r >= ROWS - 2),
                     "edge_col": bool(c in (0, COLS - 1))}
            if H[c] < med:
                tags.append("last_virus_notch")
    if not tags:
        tags.append("unclassified")
    return {"tags": tags, "v_champ": vch, "v_best": vbe,
            "dv": (None if (vch is None or vbe is None) else round(vch - vbe, 6)),
            "vir_after_champ": ch["vir_after"], "vir_after_best": be["vir_after"],
            "dsh_champ": d_ch, "dsh_best": d_be, "notch": notch,
            "clair_champ": ch.get("clair_surv"), "clair_best": be.get("clair_surv"),
            "clair_clear_champ": ch.get("clair_clear"),
            "clair_clear_best": be.get("clair_clear")}


def clair_verdict(doc):
    """A1.2: is ANY candidate a clairvoyant rescue at ANY scanned ply?"""
    stall = doc["result"] == "stall"
    key = "clair_clear" if stall else "clair_surv"
    for st in doc["states"]:
        ch = next(e for e in st["cands"] if st["a_champ"] in e["slots"])
        best = max(e[key] for e in st["cands"])
        if best > ch[key]:
            return True, st["k"]
    return False, None


def notch_control(doc, rng):
    """MATCHED WITHIN-BOARD CONTROL for the notch statistic: is the virus's
    column shorter than the median by more than a RANDOM OCCUPIED CELL's is?"""
    t = doc.get("terminal")
    if not t or doc["viruses_left"] != 1:
        return None
    tc = np.array(t["color"])
    tv = np.array(t["virus"])
    cells = np.argwhere(tv != 0)
    if len(cells) != 1:
        return None
    H = heights(tc)
    occ = np.argwhere(tc != 0)
    if len(occ) < 2:
        return None
    med = float(np.median(H[H > 0]))
    r, c = int(cells[0][0]), int(cells[0][1])
    pick = occ[rng.randrange(len(occ))]
    return {"virus_delta": int(H[c]) - med,
            "control_delta": int(H[int(pick[1])]) - med}


def main():
    docs = load_docs()
    assert docs, "no label files"
    rng = random.Random(CONTROL_SEED)
    sys.path.insert(0, HERE)
    import validate_autopsy as V

    games, cluster_rows = [], []
    for d in docs:
        cls = V.claims_of(d)
        deepest = max(cls, key=lambda c: c["k"]) if cls else None
        cv, ck = clair_verdict(d)
        g = {"seed": d["seed"], "result": d["result"],
             "viruses_left": d["viruses_left"], "n_moves": d["n_moves"],
             "anchor": d["anchor"], "H": d["H"],
             "plies_scanned": len(d["states"]),
             "plies_available": d["plies_available"],
             "verdict": "AVOIDABLE" if cls else "DOOMED",
             "n_firing": len(cls), "firing_k": [c["k"] for c in cls],
             "deepest_k": (deepest["k"] if deepest else None),
             "deepest_ply": (deepest["ply"] if deepest else None),
             "clair_avoidable": cv, "clair_deepest_k": ck,
             "notch_control": notch_control(d, rng)}
        games.append(g)
        for c in cls:
            st = next(s for s in d["states"] if s["ply"] == c["ply"])
            cluster_rows.append(dict(
                {"seed": d["seed"], "result": d["result"], "ply": c["ply"],
                 "k": c["k"], "d": c["d"]}, **classify(d, st, c)))

    n = len(games)
    n_av = sum(1 for g in games if g["verdict"] == "AVOIDABLE")
    lo, hi = clopper_pearson(n_av, n) if n else (0, 0)
    n_cav = sum(1 for g in games if g["clair_avoidable"])
    clo, chi = clopper_pearson(n_cav, n) if n else (0, 0)

    tags = {}
    for r in cluster_rows:
        for t in r["tags"]:
            tags[t] = tags.get(t, 0) + 1
    co = {}
    keys = sorted(tags)
    for a in keys:
        for b in keys:
            co[f"{a}|{b}"] = sum(1 for r in cluster_rows
                                 if a in r["tags"] and b in r["tags"])

    rep = {
        "n_games": n,
        "by_result": {k: sum(1 for g in games if g["result"] == k)
                      for k in ("topout", "stall")},
        "one_virus_left": sum(1 for g in games if g["viruses_left"] == 1),
        "avoidable": n_av, "doomed": n - n_av,
        "avoidable_rate": (n_av / n if n else None),
        "avoidable_ci95": [lo, hi],
        "clair_avoidable": n_cav, "clair_ci95": [clo, chi],
        "deepest_k": [g["deepest_k"] for g in games if g["deepest_k"] is not None],
        "firing_k_all": sorted(k for g in games for k in g["firing_k"]),
        "cluster_marginals": tags,
        "cluster_cooccurrence": co,
        "n_firing_plies": len(cluster_rows),
        "games": games, "clusters": cluster_rows,
    }
    with open(os.path.join(OUT, "AUTOPSY_REPORT.json"), "w") as f:
        json.dump(rep, f, indent=2)

    print(f"games={n}  topout={rep['by_result']['topout']} "
          f"stall={rep['by_result']['stall']}  1-virus={rep['one_virus_left']}")
    print(f"AVOIDABLE {n_av}/{n} = {n_av / n:.1%}  95% CI "
          f"[{lo:.1%}, {hi:.1%}]   DOOMED {n - n_av}")
    print(f"clairvoyant-avoidable {n_cav}/{n}  95% CI [{clo:.1%}, {chi:.1%}]")
    print("clusters:", json.dumps(tags))
    print("ANALYZE_OK")


if __name__ == "__main__":
    main()
