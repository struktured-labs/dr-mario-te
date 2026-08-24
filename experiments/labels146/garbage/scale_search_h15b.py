"""scale_search_h15b.py — round-2 dose scale search (ran 2026-08-24; the
heredoc original is preserved here verbatim as the committed record).

RESULT (out/h15b_scale_search.log): train rho MONOTONE 0.2553->0.3062 across
the whole log grid, no interior maximum; lambda*=1 — the round-1 dose that
measured +49.2pp WORSE on games.  The label-ranking criterion cannot price
off-policy compounding.  Reported to team-lead instead of registering.
"""
import numpy as np
from scipy.stats import spearmanr
import zlib
import fit_garbage as F

WC, WA = -252.611, 18.361
GRID = [0.0] + [10.0 ** k for k in np.arange(-4, 0.5, 0.5)]


def main():
    rows = F.load_rows()
    prim = [r for r in rows if r["stratum"] in ("C", "Cdeep")]
    states = []
    for r in prim:
        vals = r.get("vals")
        ents = []
        for e in r["cands"]:
            vs = [vals[s] for s in e["slots"] if vals[s] is not None]
            if not vs:
                continue
            col, vir = F.decode_planes(e["planes"])
            ents.append((max(vs),
                         WC * F.g_center(col, vir) + WA * F.g_attack(col, vir),
                         sum(e["surv"]) / len(e["surv"])))
        if len(ents) < 3:
            continue
        y = np.array([t[2] for t in ents])
        if len(set(np.round(y, 6))) < 2:
            continue
        held = zlib.crc32(str(r["seed"]).encode()) % 4 == 3
        states.append((held, np.array([t[0] for t in ents]),
                       np.array([t[1] for t in ents]), y))

    def rho_at(lam, subset):
        out = []
        for held, v, d, y in states:
            if held != subset:
                continue
            rho = spearmanr(v + lam * d, y).statistic
            if np.isfinite(rho):
                out.append(rho)
        return np.array(out)

    best_lam, best = None, -np.inf
    for lam in GRID:
        tr = rho_at(lam, False).mean()
        print(f"lambda={lam:.6g}: train_rho={tr:.4f}")
        if tr > best:
            best, best_lam = tr, lam
    print(f"SELECTED lambda* = {best_lam:.6g} (train rho {best:.4f})")
    h_star, h_0 = rho_at(best_lam, True), rho_at(0.0, True)
    diff = h_star - h_0
    rng = np.random.default_rng(146)
    boots = np.array([diff[rng.integers(0, len(diff), len(diff))].mean()
                      for _ in range(10000)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"HELD-OUT: rho(lambda*)={h_star.mean():.4f} rho(0)={h_0.mean():.4f} "
          f"gain={diff.mean():+.4f} CI95[{lo:+.4f},{hi:+.4f}] n={len(diff)}")


if __name__ == "__main__":
    main()
