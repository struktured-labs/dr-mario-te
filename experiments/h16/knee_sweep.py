"""knee_sweep.py — H16 design round 4: the registered operating point,
the (m1, keep, thresholds) knee table, silicon A/B fire rates, per-k catch.
Committed with REGISTRATION_H16.md; bank-only, design-side.
"""
import json
import os

import numpy as np

import trigger_roc3 as T

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def p_var(state, m1, keep, cmax, dmin):
    champ = next(c for c in state["cands"] if c["is_champ"])
    ranked = sorted(state["cands"],
                    key=lambda c: (-T.surv_sum(c, 0, m1), -c["val"]))
    short = ranked[:keep]
    if champ not in short:
        short = short + [champ]
    best = max(short, key=lambda c: (T.surv_sum(c, m1, 8), c["val"]))
    if T.surv_sum(champ, m1, 8) <= cmax and \
       T.surv_sum(best, m1, 8) - T.surv_sum(champ, m1, 8) >= dmin:
        return best, champ
    return None, champ


def main():
    os.makedirs(OUT, exist_ok=True)
    lab = T.load_label_states()
    claims, nonclaim, healthy = [], [], []
    for s in lab:
        got, champ = T.full8(s)
        s["claim"] = got is not None
        s["champ8"] = T.surv_sum(champ, 0, 8)
        (claims if s["claim"] else nonclaim).append(s)
        if s["stratum"] == "C" and s["champ8"] >= 7:
            healthy.append(s)
    W = float(np.median([len(s["cands"]) for s in lab]))
    res = {"n_claims": len(claims), "n_nonclaim": len(nonclaim),
           "n_healthy": len(healthy), "dedup_width_median": W, "sweep": []}

    grid = [(2, 5, 3, 3), (2, 8, 3, 3), (2, 12, 3, 3), (2, 8, 3, 4),
            (3, 5, 3, 2), (3, 8, 3, 2), (3, 5, 3, 3), (3, 8, 3, 3)]
    print(f"{'m1':>3} {'keep':>4} {'cmax':>4} {'dmin':>4} {'rec':>7} "
          f"{'good':>7} {'foNC':>5} {'foH':>4} {'forks':>6}")
    for m1, keep, cmax, dmin in grid:
        rec = qual = 0
        chosen_gain = []
        for s in claims:
            got, _ = p_var(s, m1, keep, cmax, dmin)
            if got is not None:
                rec += 1
                g = T.surv_sum(got, 0, 8) - s["champ8"]
                chosen_gain.append(g)
                if g >= 3:
                    qual += 1
        fo = sum(p_var(s, m1, keep, cmax, dmin)[0] is not None
                 for s in nonclaim)
        foh = sum(p_var(s, m1, keep, cmax, dmin)[0] is not None
                  for s in healthy)
        forks = m1 * W + (8 - m1) * (keep + 1)
        row = {"m1": m1, "keep": keep, "cmax": cmax, "dmin": dmin,
               "recovered": rec, "recovered_frac": round(rec / len(claims), 4),
               "good_choice": qual,
               "good_frac_of_recovered": round(qual / max(rec, 1), 4),
               "false_override_nonclaim": fo,
               "false_override_healthy": foh,
               "forks_per_fire": forks}
        res["sweep"].append(row)
        print(f"{m1:3d} {keep:4d} {cmax:4d} {dmin:4d} "
              f"{rec:3d}/{len(claims):3d} {qual:3d}/{max(rec,1):3d} "
              f"{fo:5d} {foh:4d} {forks:6.0f}")

    # the registered point
    reg = next(r for r in res["sweep"]
               if (r["m1"], r["keep"], r["cmax"], r["dmin"]) == (2, 8, 3, 3))
    res["registered"] = reg
    print(f"\nREGISTERED (m1=2, keep=8, cmax=3, dmin=3): "
          f"recovered {reg['recovered']}/{res['n_claims']} "
          f"= {reg['recovered_frac']:.3f}, good "
          f"{reg['good_frac_of_recovered']:.3f}, "
          f"false-override nonclaim {reg['false_override_nonclaim']}"
          f"/{res['n_nonclaim']}, healthy {reg['false_override_healthy']}"
          f"/{res['n_healthy']}")

    # silicon A/B strata fire rates (scope caveat, REGISTRATION sec 2.4)
    res["ab_fire"] = {}
    for st in ("A", "B"):
        rs = [r for r in lab if r["stratum"] == st]
        for t in (12, 13, 14):
            f = float(np.mean([r["dsh"] >= t for r in rs]))
            res["ab_fire"][f"{st}_dsh{t}"] = round(f, 4)
    print("A/B silicon pre-death fire:",
          {k: v for k, v in res["ab_fire"].items() if "dsh13" in k})

    # per-k catch on C-deep claims
    res["catch_by_k"] = {}
    for k in (8, 12, 16, 20):
        cl = [r for r in claims if r["stratum"] == "Cdeep"
              and r["id"].endswith(f"_k{k}")]
        res["catch_by_k"][k] = round(
            float(np.mean([r["dsh"] >= 13 for r in cl])), 4)
    print("catch by k (dsh>=13):", res["catch_by_k"])

    with open(os.path.join(OUT, "knee_sweep.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote {os.path.join(OUT, 'knee_sweep.json')}")


if __name__ == "__main__":
    main()
