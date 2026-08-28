"""M3 rider (a): derive the FALSE-VETO ceiling NUMERICALLY on reference data,
BEFORE any guard exists (R62/R28 — the bar must not be calibrated on the fit
it will judge).

A false veto = the guard overrides at a state the TEACHER calls non-danger
(champ_s2 >= 5: the champion's own pick survives >=5 of 6 confirm forks).
H16 has FVR = 0 on this population BY CONSTRUCTION (its rule needs
champ_s2 <= 3), so any FVR is pure distillation error.

The cost of a false veto is measured here WITHOUT reference to any fitted g:
force a veto at each non-danger state (take the best NON-champion candidate by
the champion's own value ordering — the deployed fallback) and read the
realized eval-half survival loss. That is harm-per-false-veto, a property of
the board population, not of the guard."""
import sys, json, glob, gzip, os
import numpy as np
sys.path.insert(0, ".")
import m2_screens as M

for stratum in ("L20", "L11M"):
    rows = M.assemble(stratum) if stratum == "L20" else None
    if rows is None:
        # L11M has no derived features; read labels directly
        rows = []
        for f in sorted(glob.glob(f"out/labels_m1/{stratum}/seed_*.json.gz")):
            r = json.load(gzip.open(f, "rt"))
            if r["smoke"]: continue
            for a in r["adjudications"]:
                if a["degenerate"]: continue
                v = M.state_view(a)
                if v is None: continue
                dec, ev, val, ci = v
                rows.append({"ev": ev, "val": val, "ci": ci,
                             "champ_s2": a["champ_s2"], "seed": r["seed"]})
    else:
        for r in rows:
            r["champ_s2"] = int(r["s2full"][r["ci"]])
    nd = [r for r in rows if r["champ_s2"] >= 5]
    dg = [r for r in rows if r["champ_s2"] <= 3]
    if not nd: continue
    loss, sat = [], 0
    for r in nd:
        ci = r["ci"]
        others = [i for i in range(len(r["ev"])) if i != ci]
        if not others: continue
        alt = max(others, key=lambda i: r["val"][i])   # deployed fallback
        loss.append(r["ev"][alt] - r["ev"][ci])
        if len(set(r["ev"].tolist())) == 1: sat += 1
    loss = np.array(loss)
    print(f"== {stratum}: non-danger (champ_s2>=5) n={len(nd)}  "
          f"danger n={len(dg)}  of {len(rows)} non-degenerate")
    print(f"   harm per FORCED veto (eval-half surv pts, 0-3 scale): "
          f"mean={loss.mean():+.4f} sd={loss.std():.4f} "
          f"median={np.median(loss):+.1f}")
    print(f"   vetoes that cost NOTHING: {(loss>=0).mean():.1%} "
          f"(>0: {(loss>0).mean():.1%})   fully saturated states: "
          f"{sat/len(loss):.1%}")
    print(f"   worst decile loss: {np.percentile(loss,10):+.2f}")
