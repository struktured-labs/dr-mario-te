"""analyze_garbage.py — pilot/campaign readout + the two label-level mutants
(PREREG_GARBAGE §6.5-6.6, §7).

M-mimic  : labels = champion's own values  -> MUST yield 0 claims
           (required verdict `MIMIC FAIL_NO_CLAIMS`).
M-shuffle: per-state permutation of the candidate labels (seeded, recorded)
           -> nonempty claim set (dose check); its stratum-C claims go to the
           forced-move validator at campaign stage, report-only at pilot.
Calibration (A/B endpoint ii): forks 0-3 vs 4-7, pooled within-state Spearman
per stratum, must be > 0.

Report-only at pilot n: prints numbers, never promotes anything.
"""
import argparse
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import garbcore as G

OUT = os.path.join(HERE, "out")
LABELS = os.path.join(OUT, "labels")
SHUFFLE_SEED = 20260823        # recorded (PREREG §6.6)


def load_rows():
    rows = []
    for p in sorted(glob.glob(os.path.join(LABELS, "*.jsonl.gz"))):
        with gzip.open(p, "rt") as fh:
            for ln in fh:
                rows.append(json.loads(ln))
    return rows


def mimic_claims(rows):
    """M-mimic: labels := the champion's own values, rank-mapped onto the
    0..8 surv scale, then fed through the REAL claim extractor.  The champion
    entry gets the top pseudo-surv, so the extractor must return 0 claims —
    exercised, not assumed."""
    n = 0
    for r in rows:
        vals = r.get("champ_vals") or r.get("vals")
        ents = r["cands"]
        vs = [max(vals[s] for s in e["slots"] if vals[s] is not None)
              for e in ents]
        order = np.argsort(np.argsort(vs))          # 0..len-1, max = best
        hi = max(1, len(ents) - 1)
        mim = [{"slots": e["slots"], "rep_slot": e["rep_slot"],
                "key": e["key"],
                "surv": [1] * int(round(8 * order[i] / hi))
                        + [0] * (8 - int(round(8 * order[i] / hi))),
                "prog": e["prog"]}
               for i, e in enumerate(ents)]
        if G.claims_from_row({"cands": mim, "champ_slot": r["champ_slot"],
                              "id": r["id"]}):
            n += 1
    return n


def shuffle_claims(rows):
    rng = np.random.default_rng(SHUFFLE_SEED)
    n, examples = 0, []
    for r in rows:
        ents = r["cands"]
        perm = rng.permutation(len(ents))
        sh = [{"slots": e["slots"], "rep_slot": e["rep_slot"], "key": e["key"],
               "surv": ents[j]["surv"], "prog": ents[j]["prog"]}
              for e, j in zip(ents, perm)]
        c = G.claims_from_row({"cands": sh, "champ_slot": r["champ_slot"],
                               "id": r["id"]})
        if c:
            n += 1
            examples.append(r["id"])
    return n, examples[:5]


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="which", default="pilot")
    args = ap.parse_args()

    rows = load_rows()
    voids = {}
    vp = os.path.join(OUT, "voids.jsonl")
    if os.path.exists(vp):
        for ln in open(vp):
            r = json.loads(ln)
            voids[r["id"]] = r

    print(f"=== analyze_garbage ({args.which}) — report-only ===")
    for stratum in "ABC":
        rs = [r for r in rows if r["stratum"] == stratum]
        if not rs:
            print(f"stratum {stratum}: 0 rows")
            continue
        ncands = [len(r["cands"]) for r in rs]
        champ_surv, claims, rhos = [], [], []
        for r in rs:
            c = G.claims_from_row(r)
            ce = next(e for e in r["cands"] if r["champ_slot"] in e["slots"])
            champ_surv.append(sum(ce["surv"]))
            if c:
                claims.append({"id": r["id"], **c})
            surv_a = [sum(e["surv"][:4]) for e in r["cands"]]
            surv_b = [sum(e["surv"][4:]) for e in r["cands"]]
            rho = spearman(np.array(surv_a), np.array(surv_b))
            if rho is not None:
                rhos.append(rho)
        nv = sum(v["stratum"] == stratum for v in voids.values())
        print(f"stratum {stratum}: rows={len(rs)} voids={nv} "
              f"cands/state med={int(np.median(ncands))} "
              f"champ_surv mean={np.mean(champ_surv):.2f} "
              f"claims={len(claims)} "
              f"calib_rho={np.mean(rhos):.3f} (n={len(rhos)})"
              if rhos else
              f"stratum {stratum}: rows={len(rs)} voids={nv} "
              f"claims={len(claims)} calib_rho=NA")
        for c in claims[:8]:
            print(f"    claim {c['id']}: champ={c['champ_surv']}/8 "
                  f"best={c['best_surv']}/8 slot={c['best_slot']}")

    # ---- mutants -----------------------------------------------------------
    bad = mimic_claims(rows)
    if bad == 0:
        print("MIMIC FAIL_NO_CLAIMS")        # required verdict line
    else:
        print(f"MIMIC BROKEN: {bad} value-argmax/champion mismatches")
    ns, ex = shuffle_claims(rows)
    print(f"SHUFFLE claims={ns} (dose check: must be nonempty) e.g. {ex}")
    print("ANALYZE_DONE")


if __name__ == "__main__":
    main()
