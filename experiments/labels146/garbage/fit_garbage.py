"""fit_garbage.py — the A2 PRIMARY promotion gate: ridge fit of
[champ_value, g_center, g_attack, g_construct] -> surv/8, per FIT_CONFIG
(approved 094a2aa; CI-excluding-0 recorded by team-lead as the binding form).

Verdict first, then rho_full / rho_champval / rho_shufflefit with the
bootstrap CI, then diagnostics (ablations + coefficient signs).
"""
import glob
import gzip
import json
import os
import sys
import zlib
import base64

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np
from scipy.stats import spearmanr

LABELS = os.path.join(HERE, "out", "labels")
SHUFFLE_SEED = 20260823
BOOT_SEED = 146
N_BOOT = 10_000
ALPHAS = [10.0 ** k for k in range(-3, 4)]


# ------------------------------------------------------------- features
def decode_planes(b64):
    raw = base64.b64decode(b64)
    col = np.frombuffer(raw[:128], dtype=np.int8)
    vir = np.frombuffer(raw[128:256], dtype=np.int8)
    return col, vir


def g_center(col, vir):
    tot = 0
    for c in (3, 4):
        occ = [r for r in range(16) if col[r * 8 + c] != 0]
        h = 16 - occ[0] if occ else 0
        vrows = [r for r in range(16) if vir[r * 8 + c] != 0]
        b = 0
        if vrows:
            deep = max(vrows)                     # deepest virus (row-major)
            b = sum(1 for r in range(deep)
                    if col[r * 8 + c] != 0 and vir[r * 8 + c] == 0)
        tot += h + b
    return tot


def g_attack(col, vir):
    lab = np.zeros(128, dtype=np.int32)          # component ids for pill cells
    sizes = {0: 0}
    nid = 0
    for i in range(128):
        if col[i] == 0 or vir[i] != 0 or lab[i]:
            continue
        nid += 1
        k, stack, n = col[i], [i], 0
        lab[i] = nid
        while stack:
            j = stack.pop()
            n += 1
            r, c = divmod(j, 8)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < 16 and 0 <= cc < 8:
                    jj = rr * 8 + cc
                    if col[jj] == k and vir[jj] == 0 and not lab[jj]:
                        lab[jj] = nid
                        stack.append(jj)
        sizes[nid] = n
    tot = 0
    for i in range(128):
        if vir[i] == 0:
            continue
        k, best = col[i], 0
        r, c = divmod(i, 8)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < 16 and 0 <= cc < 8:
                jj = rr * 8 + cc
                if col[jj] == k and vir[jj] == 0:
                    best = max(best, sizes[lab[jj]])
        tot += min(3, best)
    return tot


def g_construct(col, vir):
    n = 0
    for i in range(128):
        if vir[i] == 0:
            continue
        k = col[i]
        r, c = divmod(i, 8)
        best = 0
        for axis in (0, 1):
            for s0 in range(4):                  # window start offset back
                cells = []
                ok = True
                for t in range(4):
                    rr = r if axis else r
                    if axis == 0:                # horizontal window
                        rr, cc = r, c - s0 + t
                    else:                        # vertical window
                        rr, cc = r - s0 + t, c
                    if not (0 <= rr < 16 and 0 <= cc < 8):
                        ok = False
                        break
                    cells.append(rr * 8 + cc)
                if not ok or i not in cells:
                    continue
                score, live = 0, True
                for j in cells:
                    if col[j] == 0:
                        continue
                    if col[j] != k:              # other colour, pill or virus
                        live = False
                        break
                    score += 1
                if live:
                    best = max(best, score)
        if best == 2:                            # staged MULTI-STEP only
            n += 1
    return n


# ------------------------------------------------------------- data prep
def load_rows():
    rows = []
    for p in sorted(glob.glob(os.path.join(LABELS, "*.jsonl.gz"))):
        with gzip.open(p, "rt") as fh:
            rows.append(json.loads(fh.readline()))
    return rows


def build_matrix(rows):
    """Per candidate: (unit, stratum, state_id, feats[4], y).  Excludes
    candidates with no finite champ value (never happens for legal slots)."""
    out = []
    for r in rows:
        vals = r.get("vals") or r.get("champ_vals")
        for e in r["cands"]:
            vs = [vals[s] for s in e["slots"] if vals[s] is not None]
            if not vs:
                continue
            col, vir = decode_planes(e["planes"])
            y = sum(e["surv"]) / len(e["surv"])
            if r["stratum"] in ("C", "Cdeep"):
                unit = ("seed", zlib.crc32(str(r["seed"]).encode()))
            else:
                unit = ("row", zlib.crc32(r["source"]["row"].encode()))
            out.append((unit, r["stratum"], r["id"],
                        [max(vs), g_center(col, vir), g_attack(col, vir),
                         g_construct(col, vir)], y))
    return out


def heldout(unit):
    return unit[1] % 4 == 3


def zscore_fit(X, strata):
    stats = {}
    for st in set(strata):
        m = np.array([s == st for s in strata])
        mu = X[m].mean(axis=0)
        sd = X[m].std(axis=0)
        sd[sd == 0] = 1.0
        stats[st] = (mu, sd)
    return stats


def zscore_apply(X, strata, stats):
    Z = np.empty_like(X)
    for st, (mu, sd) in stats.items():
        m = np.array([s == st for s in strata])
        Z[m] = (X[m] - mu) / sd
    return Z


def ridge_fit(Z, y, alpha):
    A = np.hstack([Z, np.ones((len(Z), 1))])
    n = A.shape[1]
    R = alpha * np.eye(n)
    R[-1, -1] = 0.0                              # never penalize intercept
    return np.linalg.solve(A.T @ A + R, A.T @ y)


def ridge_pred(Z, w):
    return np.hstack([Z, np.ones((len(Z), 1))]) @ w


def cv_alpha(Z, y, states, seed=1):
    rng = np.random.default_rng(seed)
    us = sorted(set(states))
    rng.shuffle(us)
    folds = [set(us[i::5]) for i in range(5)]
    best, best_mse = ALPHAS[0], np.inf
    for a in ALPHAS:
        mse = 0.0
        for f in folds:
            m = np.array([s in f for s in states])
            w = ridge_fit(Z[~m], y[~m], a)
            mse += float(np.mean((ridge_pred(Z[m], w) - y[m]) ** 2))
        if mse < best_mse:
            best, best_mse = a, mse
    return best


def state_rhos(states, pred, y):
    out = {}
    for st in sorted(set(states)):
        m = np.array([s == st for s in states])
        if len(set(y[m])) < 2 or m.sum() < 3:
            continue
        rho = spearmanr(pred[m], y[m]).statistic
        if np.isfinite(rho):
            out[st] = rho
    return out


def fit_and_score(data, cols, shuffle=False, tag=""):
    tr = [d for d in data if not heldout(d[0])]
    te = [d for d in data if heldout(d[0])]
    Xtr = np.array([d[3] for d in tr])[:, cols]
    Xte = np.array([d[3] for d in te])[:, cols]
    ytr = np.array([d[4] for d in tr])
    yte = np.array([d[4] for d in te])
    str_tr = [d[1] for d in tr]
    str_te = [d[1] for d in te]
    sid_tr = [d[2] for d in tr]
    sid_te = [d[2] for d in te]
    if shuffle:                                   # per-state label permutation
        rng = np.random.default_rng(SHUFFLE_SEED)
        ytr = ytr.copy()
        for st in set(sid_tr):
            m = np.array([s == st for s in sid_tr])
            ytr[m] = rng.permutation(ytr[m])
    stats = zscore_fit(Xtr, str_tr)
    Ztr = zscore_apply(Xtr, str_tr, stats)
    Zte = zscore_apply(Xte, str_te, stats)
    a = cv_alpha(Ztr, ytr, sid_tr)
    w = ridge_fit(Ztr, ytr, a)
    rhos = state_rhos(sid_te, ridge_pred(Zte, w), yte)
    return rhos, w, a


def main():
    rows = load_rows()
    data = build_matrix(rows)
    pops = {"C+Cdeep (PRIMARY)": [d for d in data if d[1] in ("C", "Cdeep")],
            "A+B (side)": [d for d in data if d[1] in ("A", "B")]}
    names = ["champ_value", "g_center", "g_attack", "g_construct"]
    verdict = None
    for pname, pdata in pops.items():
        nte = len({d[2] for d in pdata if heldout(d[0])})
        print(f"\n=== population {pname}: {len({d[2] for d in pdata})} states "
              f"({nte} held out), {len(pdata)} candidate rows ===")
        r_full, w_full, a_full = fit_and_score(pdata, [0, 1, 2, 3])
        r_champ, _, _ = fit_and_score(pdata, [0])
        r_shuf, _, _ = fit_and_score(pdata, [0, 1, 2, 3], shuffle=True)
        common = sorted(set(r_full) & set(r_champ))
        d_full = np.array([r_full[s] for s in common])
        d_ch = np.array([r_champ[s] for s in common])
        diff = d_full - d_ch
        rng = np.random.default_rng(BOOT_SEED)
        boots = np.array([diff[rng.integers(0, len(diff), len(diff))].mean()
                          for _ in range(N_BOOT)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rho_full = float(np.mean(list(r_full.values())))
        rho_ch = float(np.mean(list(r_champ.values())))
        rho_sh = float(np.mean(list(r_shuf.values()))) if r_shuf else float("nan")
        if "PRIMARY" in pname:
            ok = lo > 0 and rho_full > rho_sh
            verdict = "PASS" if ok else "NO PASS"
            print(f"VERDICT {verdict}")
        print(f"rho_full={rho_full:.4f}  rho_champval={rho_ch:.4f}  "
              f"rho_shufflefit={rho_sh:.4f}")
        print(f"paired mean diff (full-champ) = {diff.mean():+.4f}  "
              f"bootstrap95 [{lo:+.4f}, {hi:+.4f}]  n_states={len(common)}  "
              f"alpha={a_full}")
        print("coefficients (z-scored):",
              {n: round(float(c), 4) for n, c in zip(names, w_full[:-1])})
        for j, nm in enumerate(names[1:], start=1):
            r_ab, _, _ = fit_and_score(pdata, [0, j])
            ca = sorted(set(r_ab) & set(r_champ))
            dd = np.mean([r_ab[s] - r_champ[s] for s in ca])
            print(f"  ablation +{nm}: delta rho {dd:+.4f} (n={len(ca)})")
    print(f"\nFIT_VERDICT {verdict}")


if __name__ == "__main__":
    main()
