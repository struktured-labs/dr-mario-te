"""mutant_shuffle_control.py — killed-mutant adjudication of FIT_CONFIG
condition (b), the shuffle-fit control (team-lead ruling part 2).

On the REAL primary feature matrix (C+Cdeep), synthesize labels under two
known ground truths and push them through the REAL pipeline (same z-scoring,
CV shrinkage path, split, metric):

  (i)  BETWEEN-ONLY: y = (state-mean features)·beta + iid noise — no
       within-state feature signal at all.  A working control should TIE the
       full fit here (nothing within-state to lose).
  (ii) WITHIN-SIGNAL: y = (per-candidate features)·beta * g + iid noise at
       several signal sizes g (targeting realistic held-out within-state
       rho).  A working control MUST LOSE to the full fit here — this is the
       exact case condition (b) exists to catch.

If the shuffle control ties the full fit in BOTH cases, it is defective by
construction (rule 16: the control retains the phenomenon's channel — state
means survive within-state permutation).  Direction chosen: beta = the real
full fit's z-space coefficient direction (unit-normed).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
import fit_garbage as F

MUTANT_SEED = 4146


def main():
    rows = F.load_rows()
    data = [d for d in F.build_matrix(rows) if d[1] in ("C", "Cdeep")]
    X = np.array([d[3] for d in data])
    strata = [d[1] for d in data]
    sids = [d[2] for d in data]
    stats = F.zscore_fit(X, strata)
    Z = F.zscore_apply(X, strata, stats)

    # beta = the real fit's direction (recomputed here, unit-normed, z-space)
    y_real = np.array([d[4] for d in data])
    a = F.cv_alpha(Z, y_real, sids)
    w = F.ridge_fit(Z, y_real, a)
    beta = w[:-1] / np.linalg.norm(w[:-1])
    print(f"[mutant] beta direction (unit) = "
          f"{[round(float(b), 3) for b in beta]}  (alpha={a})")

    # per-state mean of Z (case i's only signal channel)
    sid_arr = np.array(sids)
    zmean = np.empty_like(Z)
    for s in set(sids):
        m = sid_arr == s
        zmean[m] = Z[m].mean(axis=0)

    rng = np.random.default_rng(MUTANT_SEED)
    sig_within = Z @ beta
    sig_between = zmean @ beta
    sd_w = float(np.std(sig_within - sig_between))   # within-state spread

    def run_case(name, y_syn):
        syn = [(d[0], d[1], d[2], d[3], y_syn[j]) for j, d in enumerate(data)]
        r_full, _, _ = F.fit_and_score(syn, [0, 1, 2, 3])
        r_shuf, _, _ = F.fit_and_score(syn, [0, 1, 2, 3], shuffle=True)
        common = sorted(set(r_full) & set(r_shuf))
        rf = float(np.mean([r_full[s] for s in common]))
        rs = float(np.mean([r_shuf[s] for s in common]))
        diff = np.array([r_full[s] - r_shuf[s] for s in common])
        b = np.array([diff[rng.integers(0, len(diff), len(diff))].mean()
                      for _ in range(2000)])
        lo, hi = np.percentile(b, [2.5, 97.5])
        verdict = "DISCRIMINATES" if lo > 0 else "TIES"
        print(f"[mutant] {name}: rho_full={rf:.4f} rho_shuffle={rs:.4f} "
              f"diff={diff.mean():+.4f} CI95[{lo:+.4f},{hi:+.4f}] "
              f"n={len(common)} -> {verdict}")
        return verdict

    # ---- case (i): between-only, noise scaled to match within spread ------
    y_i = sig_between + rng.normal(scale=max(sd_w, 0.05), size=len(Z))
    v_i = run_case("case(i) between-only", y_i)

    # ---- case (ii): genuine within-state signal, three sizes --------------
    verdicts = []
    for g, noise in ((1.0, 2.0), (1.0, 1.0), (1.0, 0.5)):
        y_ii = g * sig_within + rng.normal(scale=noise * max(sd_w, 0.05),
                                           size=len(Z))
        # report the realized within-state signal size for calibration
        syn_rho = []
        for s in list(set(sids))[:200]:
            m = sid_arr == s
            if m.sum() >= 3 and len(set(np.round(y_ii[m], 6))) > 1:
                from scipy.stats import spearmanr
                r = spearmanr(sig_within[m], y_ii[m]).statistic
                if np.isfinite(r):
                    syn_rho.append(r)
        tag = f"case(ii) within g/noise={g}/{noise} " \
              f"(true within-rho~{np.mean(syn_rho):.2f})"
        verdicts.append(run_case(tag, y_ii))

    if all(v == "TIES" for v in verdicts):
        print("MUTANT VERDICT: CONTROL DEFECTIVE — ties the full fit even "
              "with genuine within-state signal at every tested size "
              "(rule 16: the control retains the state-mean channel)")
    elif any(v == "TIES" for v in verdicts):
        print("MUTANT VERDICT: CONTROL PARTIALLY BLIND — discriminates only "
              "at some signal sizes; see per-case lines")
    else:
        print("MUTANT VERDICT: CONTROL VALID — discriminates genuine "
              "within-state signal; the NO PASS is fully binding")


if __name__ == "__main__":
    main()
