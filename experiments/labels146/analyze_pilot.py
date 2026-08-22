"""analyze_pilot.py — mechanical pilot report (PREREG_LABELS §4/§5/§7).

Reads out/labels + out/validate_*.json + out/harvest.log and emits
out/PILOT_REPORT.json plus a printed summary.  Applies the pre-stated
HORIZON RULE and WINDOW RULE mechanically; the campaign values go to
team-lead review, they do not self-execute.

--selftest drives the rule functions with synthetic tables straddling every
threshold (gate-standard: analysis code that has only seen one real table has
never been shown to discriminate).
"""
import argparse
import glob
import gzip
import json
import os
import re
import sys
from itertools import combinations

import numpy as np

import labelcore as LC
from validate_labels import extract_claims, CLAIM_H

KS = [1, 3, 6, 10, 15, 20]


def kendall_tau(x, y):
    n = len(x)
    if n < 2:
        return None
    conc = disc = 0
    for i, j in combinations(range(n), 2):
        a = (x[i] - x[j]) * (y[i] - y[j])
        if a > 0:
            conc += 1
        elif a < 0:
            disc += 1
    tot = conc + disc
    return None if tot == 0 else (conc - disc) / tot


def horizon_rule(rows):
    """Smallest H in {15,25} with mean tau(H,40)>=0.85 AND claim Jaccard>=0.75
    vs H=40, else 40.  Only dual-labeled states participate."""
    by_state = {}
    for r in rows:
        by_state.setdefault((r["seed"], r["ply"]), {})[r["H"]] = r
    dual = {k: v for k, v in by_state.items() if set(v) == {15, 25, 40}}
    out = {"n_dual_states": len(dual)}
    verdict = 40
    for H in (25, 15):   # evaluated independently; pick smallest passing
        taus = []
        for v in dual.values():
            s_h = [sum(e["surv"]) for e in v[H]["cands"]]
            s_40 = [sum(e["surv"]) for e in v[40]["cands"]]
            assert len(s_h) == len(s_40), "candidate sets differ across H"
            t = kendall_tau(s_h, s_40)
            if t is not None:
                taus.append(t)
        dual_rows_h = [v[H] for v in dual.values()]
        dual_rows_40 = [v[40] for v in dual.values()]
        c_h = {(c["seed"], c["ply"]) for c in _claims_at(dual_rows_h, H)}
        c_40 = {(c["seed"], c["ply"]) for c in _claims_at(dual_rows_40, 40)}
        uni = c_h | c_40
        jac = (len(c_h & c_40) / len(uni)) if uni else 1.0
        mtau = float(np.mean(taus)) if taus else None
        out[f"H{H}"] = {"mean_tau_vs_40": mtau, "n_tau_states": len(taus),
                        "claims": len(c_h), "claims_40": len(c_40),
                        "jaccard_vs_40": round(jac, 3)}
        if mtau is not None and mtau >= 0.85 and jac >= 0.75:
            verdict = H
    out["campaign_H"] = verdict
    return out


def _claims_at(rows, H):
    """extract_claims but at an arbitrary horizon (rule evaluation only)."""
    import validate_labels as V
    old = V.CLAIM_H
    try:
        V.CLAIM_H = H
        return V.extract_claims(rows, "true")
    finally:
        V.CLAIM_H = old


def window_rule(yield_by_k, bar=0.10, extend=5):
    """Contiguous k-range containing every k with claim yield >= bar,
    extended by `extend` on the deep end.  None if no k qualifies (V2)."""
    hot = [k for k, y in yield_by_k.items() if y >= bar]
    if not hot:
        return None
    return {"k_min": min(hot), "k_max": max(hot) + extend}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    import validate_labels as V
    rows = V.load_labels(os.path.join(LC.HERE, "out", "labels"))
    h25 = [r for r in rows if r["H"] == CLAIM_H]
    claims = extract_claims(rows, "true")
    cl_states = {(c["seed"], c["ply"]) for c in claims}

    # dsurv-vs-k profile + claim yield per k (S-death, H=25)
    prof = {}
    for k in KS:
        sub = [r for r in h25 if r["stratum"] == "death" and r["k"] == k]
        ds, ny = [], 0
        for r in sub:
            surv = [sum(e["surv"]) for e in r["cands"]]
            ci = next(i for i, e in enumerate(r["cands"])
                      if r["a"] in e["slots"])
            ds.append(max(surv) - surv[ci])
            ny += (r["seed"], r["ply"]) in cl_states
        prof[k] = {"n": len(sub),
                   "mean_dsurv": round(float(np.mean(ds)), 3) if ds else None,
                   "max_dsurv": int(max(ds)) if ds else None,
                   "claim_yield": round(ny / len(sub), 3) if sub else None}
    win = window_rule({k: v["claim_yield"] or 0.0 for k, v in prof.items()})

    hor = horizon_rule(rows)

    # measured cost
    cost = {}
    logp = os.path.join(LC.HERE, "out", "harvest.log")
    if os.path.exists(logp):
        with open(logp, errors="replace") as fh:
            txt = fh.read()
        cpu = [float(m) for m in re.findall(r"cpu_s=([0-9.]+)", txt)]
        nrows = [int(m) for m in re.findall(r"rows=(\d+)", txt)]
        forks = [int(m) for m in re.findall(r"forks=(\d+)", txt)]
        if cpu:
            cost = {"seeds": len(cpu), "cpu_s_total": round(sum(cpu), 1),
                    "label_rows": sum(nrows), "forks": sum(forks),
                    "cpu_s_per_label_row": round(sum(cpu) / sum(nrows), 1),
                    "cpu_s_per_fork": round(sum(cpu) / sum(forks), 3)}

    vres = {}
    for tag in ("true", "shuffle", "mimic"):
        p = os.path.join(LC.HERE, "out", f"validate_{tag}.json")
        if os.path.exists(p):
            with open(p) as fh:
                d = json.load(fh)
            d.pop("per_claim", None)
            vres[tag] = d

    voids = []
    if not claims:
        voids.append("V2_zero_true_claims")
    if cost and cost["cpu_s_per_fork"] > 4 * 1.07 * (CLAIM_H / 15):
        voids.append("V4_cost_overrun")
    if (vres.get("shuffle", {}).get("realized_rescue_minus_break_rate") or 0) \
            > (vres.get("true", {}).get("realized_rescue_minus_break_rate")
               or 0):
        voids.append("V3_shuffle_outperforms_true")

    rep = {"n_label_rows": len(rows), "n_states_h25": len(h25),
           "n_true_claims": len(claims), "profile_by_k": prof,
           "window_rule": win, "horizon_rule": hor, "cost": cost,
           "validation": vres, "voids": voids}
    with open(os.path.join(LC.HERE, "out", "PILOT_REPORT.json"), "w") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps(rep, indent=1))
    print("ANALYZE_PILOT_OK", flush=True)


def _mkrow(seed, ply, H, survs, champ_idx=0, stratum="death", k=6):
    cands = []
    for i, s in enumerate(survs):
        cands.append({"slots": [i], "rep_slot": i, "key": f"k{i}",
                      "surv": [1] * s + [0] * (8 - s), "prog": [0] * 8})
    return {"seed": seed, "ply": ply, "stratum": stratum, "k": k, "H": H,
            "N": 8, "a": champ_idx, "vals": [0.0] * 32, "game_res": "topout",
            "game_n_plies": 50, "vir": 5, "dsh": 12, "maxh": 12, "gate": 1,
            "cands": cands}


def selftest():
    # window rule straddles the 10% bar and the no-hot-k void
    assert window_rule({1: 0.0, 3: 0.09, 6: 0.10, 10: 0.5, 15: 0.0,
                        20: 0.0}) == {"k_min": 6, "k_max": 15}
    assert window_rule({1: 0.09, 3: 0.0}) is None
    # claim rule: 3/8 with champ<=5 claims; 2/8 or champ=6 must not
    r_yes = _mkrow(2, 1, 25, [2, 5])         # dsurv 3, champ 2 -> claim
    r_no1 = _mkrow(2, 2, 25, [3, 5])         # dsurv 2 -> no
    r_no2 = _mkrow(2, 3, 25, [6, 8])         # champ 6 -> no (champ>5 rule)
    cl = extract_claims([r_yes, r_no1, r_no2], "true")
    assert [(c["seed"], c["ply"]) for c in cl] == [(2, 1)], cl
    # mimic: zero claims even where true labels scream
    assert extract_claims([r_yes], "mimic") == []
    # horizon rule: perfect agreement -> picks 15; anti-correlated -> 40
    good = []
    for i in range(3):
        for H in (15, 25, 40):
            good.append(_mkrow(10 + i, 5, H, [1, 6, 3]))
    hr = horizon_rule(good)
    assert hr["campaign_H"] == 15, hr
    bad = []
    for i in range(3):
        for H in (15, 25, 40):
            surv = [1, 6, 3] if H == 40 else [6, 1, 3]
            bad.append(_mkrow(20 + i, 5, H, surv))
    hr = horizon_rule(bad)
    assert hr["campaign_H"] == 40, hr
    # kendall sanity
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == 1.0
    assert kendall_tau([1, 2, 3], [3, 2, 1]) == -1.0
    print("ANALYZE_SELFTEST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
