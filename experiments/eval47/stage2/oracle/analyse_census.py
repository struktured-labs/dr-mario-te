"""Read the fork-free gate census and report the gate-v2 DOSE decomposition.

Reports, per threshold T, the two factors of the fire rate that need no forks:

    gate rate            = P(gate open)
    trigger rate         = P(gate open AND exact top-2 champion-value tie)

and the ratios v2/v1. The trigger rate is the one that matters: H12 only acts
on an exact tie, so a gate that opens far more often but on plies with no tie
costs nothing and buys nothing.

⚠ SCOPE, printed with the numbers (rule 24): this is the CHAMPION's trajectory.
Under a real H13 arm the flips change later boards, so this is the dose at the
FIRST divergence and it bounds the ratio rather than reproducing a whole-game
dose. It also cannot see P(margin passes | tie), which needs rollouts.

Seed-clustered bootstrap on the ratio, because plies within a seed are not
independent.
"""
import argparse
import json

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True)
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    per_seed = []
    bad = 0
    thresholds = None
    for line in open(a.census):
        d = json.loads(line)
        if not d.get("champ_identical", 0):
            bad += 1
        rows = d["rows"]
        if not rows:
            continue
        if thresholds is None:
            thresholds = sorted(int(k.split("_t")[1]) for k in rows[0]
                                if k.startswith("gate_v2_t"))
        rec = {"seed": d["seed"], "res": d["res"], "plies": len(rows),
               "tie": sum(r["exact_tie"] for r in rows),
               "v1": sum(r["gate_v1"] for r in rows),
               "v1_tie": sum(r["gate_v1"] and r["exact_tie"] for r in rows)}
        for T in thresholds:
            k = f"gate_v2_t{T}"
            rec[f"v2_{T}"] = sum(r[k] for r in rows)
            rec[f"v2_tie_{T}"] = sum(r[k] and r["exact_tie"] for r in rows)
        per_seed.append(rec)

    n_seeds = len(per_seed)
    assert n_seeds, "empty census"
    print(f"CENSUS {a.census}: {n_seeds} seeds, "
          f"{sum(r['plies'] for r in per_seed)} plies")
    if bad:
        print(f"  *** {bad} seeds FAILED the champ_identical guard — the "
              f"census arm did not reproduce OracleArm(const). STOP. ***")
    else:
        print(f"  champ_identical guard: {n_seeds}/{n_seeds} PASS "
              f"(the census arm IS the champion on every seed)")

    plies = np.array([r["plies"] for r in per_seed], float)
    tie = np.array([r["tie"] for r in per_seed], float)
    v1 = np.array([r["v1"] for r in per_seed], float)
    v1t = np.array([r["v1_tie"] for r in per_seed], float)
    rng = np.random.default_rng(20260818)

    def boot_ratio(num, den):
        """Seed-clustered bootstrap CI of sum(num)/sum(den)."""
        idx = rng.integers(0, n_seeds, size=(a.boot, n_seeds))
        rs = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1e-9)
        return float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5))

    print(f"\n  overall exact-tie rate {tie.sum()/plies.sum():7.4f} of plies")
    print(f"  gate-v1  open {v1.sum()/plies.sum():7.4f} of plies | "
          f"TRIGGER (gate AND tie) {v1t.sum()/plies.sum():7.4f}")

    out = {"census": a.census, "n_seeds": n_seeds,
           "plies": int(plies.sum()), "champ_identical_failures": bad,
           "tie_rate": float(tie.sum()/plies.sum()),
           "v1_gate_rate": float(v1.sum()/plies.sum()),
           "v1_trigger_rate": float(v1t.sum()/plies.sum()),
           "by_threshold": {}}

    print(f"\n{'T':>3} {'gate rate':>10} {'gate x/v1':>10} "
          f"{'TRIGGER':>10} {'TRIG x/v1':>10} {'95% CI on TRIG ratio':>24}")
    for T in thresholds:
        g = np.array([r[f"v2_{T}"] for r in per_seed], float)
        gt = np.array([r[f"v2_tie_{T}"] for r in per_seed], float)
        gr = g.sum()/plies.sum()
        tr = gt.sum()/plies.sum()
        gx = g.sum()/max(v1.sum(), 1e-9)
        tx = gt.sum()/max(v1t.sum(), 1e-9)
        lo, hi = boot_ratio(gt, v1t)
        flag = "  <-- RED FLAG (>2x)" if tx > 2.0 else ""
        print(f"{T:>3} {gr:>10.4f} {gx:>10.3f} {tr:>10.4f} {tx:>10.3f} "
              f"      [{lo:.3f}, {hi:.3f}]{flag}")
        out["by_threshold"][T] = {
            "gate_rate": float(gr), "gate_ratio_vs_v1": float(gx),
            "trigger_rate": float(tr), "trigger_ratio_vs_v1": float(tx),
            "trigger_ratio_ci95": [lo, hi],
            "red_flag_over_2x": bool(tx > 2.0)}

    print("\nSCOPE (travels with the numbers): champion trajectory, so this is "
          "the dose at the FIRST divergence, not a whole-game dose. It does "
          "NOT include P(margin passes | tie), which needs rollouts. The "
          "trigger column, not the gate column, is what H12/H13 act on.")
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
        print(f"-> {a.out}")


if __name__ == "__main__":
    main()
