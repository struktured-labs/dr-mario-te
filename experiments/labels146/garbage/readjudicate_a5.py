"""readjudicate_a5.py — the ONE A5 re-adjudication (PREREG A5; no third bite).

Reports BOTH verdicts side by side: the original A2 NO PASS (on the record)
and the A5 result under the replacement nulls (b-i) across-state permutation
and (b-ii) matched-noise features.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import fit_garbage as F

NOISE_SEEDS = list(range(5000, 5020))
BOOT_SEED = 146
N_BOOT = 10_000


def fit_with_matrix(data, X_override=None, y_override=None):
    """F.fit_and_score but with optional replaced feature matrix / labels."""
    d2 = []
    for j, d in enumerate(data):
        f = list(X_override[j]) if X_override is not None else d[3]
        y = y_override[j] if y_override is not None else d[4]
        d2.append((d[0], d[1], d[2], f, y))
    return F.fit_and_score(d2, [0, 1, 2, 3])


def main():
    rows = F.load_rows()
    data = [d for d in F.build_matrix(rows) if d[1] in ("C", "Cdeep")]
    X = np.array([d[3] for d in data])
    y = np.array([d[4] for d in data])

    r_full, w_full, a_full = F.fit_and_score(data, [0, 1, 2, 3])
    r_champ, _, _ = F.fit_and_score(data, [0])

    # (b-i) ACROSS-state permutation null (training labels only)
    rng = np.random.default_rng(20260824)
    tr_mask = np.array([not F.heldout(d[0]) for d in data])
    y_bi = y.copy()
    y_bi[tr_mask] = rng.permutation(y_bi[tr_mask])
    r_bi, _, _ = fit_with_matrix(data, y_override=y_bi)

    # (b-ii) matched-noise features: 20 seeded global column permutations
    noise_rhos = []
    for sd in NOISE_SEEDS:
        rgn = np.random.default_rng(sd)
        Xn = X.copy()
        for c in (1, 2, 3):
            Xn[:, c] = rgn.permutation(Xn[:, c])
        r_n, _, _ = fit_with_matrix(data, X_override=Xn)
        noise_rhos.append(r_n)

    common = sorted(set(r_full) & set(r_champ)
                    & set.intersection(*[set(r) for r in noise_rhos]))
    rf = np.array([r_full[s] for s in common])
    rn = np.array([np.mean([r[s] for r in noise_rhos]) for s in common])
    diff = rf - rn
    rb = np.random.default_rng(BOOT_SEED)
    boots = np.array([diff[rb.integers(0, len(diff), len(diff))].mean()
                      for _ in range(N_BOOT)])
    lo, hi = np.percentile(boots, [2.5, 97.5])

    rho_full = float(np.mean(list(r_full.values())))
    rho_champ = float(np.mean(list(r_champ.values())))
    rho_bi = float(np.mean(list(r_bi.values())))
    rho_noise = float(rn.mean())

    bi_ok = abs(rho_bi) < 0.05
    bii_ok = lo > 0
    a5 = "PASS" if (bi_ok and bii_ok) else "NO PASS"
    print(f"A2-as-registered verdict (on the record): NO PASS")
    print(f"A5 verdict: {a5}")
    print(f"  rho_full={rho_full:.4f}  rho_champval={rho_champ:.4f}")
    print(f"  (b-i) across-state null rho={rho_bi:.4f} "
          f"({'collapses' if bi_ok else 'DOES NOT collapse — pipeline manufactures signal'})")
    print(f"  (b-ii) matched-noise rho={rho_noise:.4f}  paired diff "
          f"(real−noise)={diff.mean():+.4f}  CI95[{lo:+.4f},{hi:+.4f}]  "
          f"n_states={len(common)}  draws={len(NOISE_SEEDS)}")
    print(f"  condition (a) carry-over: diff vs champ-only +0.0568 "
          f"CI[+0.0353,+0.0779] PASS (unchanged fit)")
    print(f"A5_FINAL {a5}")


if __name__ == "__main__":
    main()
