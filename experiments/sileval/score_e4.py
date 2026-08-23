#!/usr/bin/env python3
"""score_e4.py -- E4 margin endpoint, exactly as registered in
PREREG_E4_MARGIN_ENDPOINT.md (AMENDMENT 2). Registration commit 5c2870e
precedes this computation.

Unit: one COMPLETE match = a segment bounded by a detected boundary on BOTH
sides. Partial first/last segments excluded by construction.
  E4a (primary)   P1 virus count at the LAST sample of the match
  E4b (secondary) P1 MINIMUM virus count within the match
Pairing: (seed, match ordinal), ordinals present in BOTH arms.
Estimator: mean(slice) - mean(ship); NEGATIVE favours slice (hypothesised).
Uncertainty: bootstrap resampling SEEDS (not matches), 10,000, 95% percentile.
"""
import sys, random, statistics, collections
import scan_winner as S

def complete_matches(samples):
    b = S.boundaries(samples)
    return [samples[b[i]:b[i+1]] for i in range(len(b) - 1)]

def per_seed(rows):
    out = collections.defaultdict(dict)
    for (seed, arm), samples in rows.items():
        segs = complete_matches(samples)
        out[seed][arm] = [(s[-1]["vp1"], min(x["vp1"] for x in s)) for s in segs if s]
    return out

def paired(ps, idx):
    """returns list of (seed, [ship vals], [slice vals]) on shared ordinals"""
    res = []
    for seed, d in ps.items():
        if "ship" not in d or "slice" not in d: continue
        n = min(len(d["ship"]), len(d["slice"]))
        if n == 0: continue
        res.append((seed, [v[idx] for v in d["ship"][:n]], [v[idx] for v in d["slice"][:n]]))
    return res

def stat(data):
    sh = [v for _, a, _ in data for v in a]
    sl = [v for _, _, b in data for v in b]
    return statistics.mean(sl) - statistics.mean(sh), statistics.mean(sh), statistics.mean(sl), len(sh)

def main(cache):
    rows = S.load(cache)
    ps = per_seed(rows)
    for name, idx in (("E4a PRIMARY   P1 virus count at match end", 0),
                      ("E4b SECONDARY P1 minimum virus count", 1)):
        data = paired(ps, idx)
        d, sh, sl, n = stat(data)
        print(f"\n=== {name}")
        print(f"  seeds paired={len(data)}  matches per arm={n}")
        print(f"  ship mean={sh:.3f}   slice mean={sl:.3f}   diff(slice-ship)={d:+.3f} viruses")
        random.seed(139)
        bs = []
        for _ in range(10000):
            samp = [random.choice(data) for _ in data]   # resample SEEDS
            bs.append(stat(samp)[0])
        bs.sort()
        lo, hi = bs[250], bs[9750]
        allsd = statistics.pstdev([v for _, a, _ in data for v in a])
        print(f"  realised per-match SD (ship) = {allsd:.2f}   (planning SD was 5.1)")
        print(f"  seed-clustered bootstrap 95% CI: [{lo:+.3f}, {hi:+.3f}]")
        favour = 100 * sum(1 for x in bs if x < 0) / len(bs)
        print(f"  bootstrap mass favouring slice (negative): {favour:.1f}%")
        verdict = ("POSITIVE (favours slice)" if hi < 0 else
                   "NEGATIVE (favours ship)" if lo > 0 else "NULL — CI spans 0")
        print(f"  => {verdict}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tmp_analysis/popA.pkl")
