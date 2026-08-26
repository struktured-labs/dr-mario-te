#!/usr/bin/env python3
"""IN-SAMPLE TRIAGE: does ANY single shipped feature, used as a tie-decider, reach the CHAMPION?

⚠ THIS LICENSES NOTHING AS A SELECTION. It is a ONE-SIDED UPPER-BOUND argument, and that is the
only inference it supports: in-sample best-of-N is biased UPWARD, so if the in-sample BEST decider
still loses to the champion's own tiebreak, the static-substitute route is dead at the
function-class level REGARDLESS of the multiplicity. If something does beat it, that is a LEAD
requiring its own held-out registration -- never a result.

Feature definitions transcribed from eval47/vocab2/feature_battery.py (pure numpy, no imports).
NOTE: the three DELTA features (a_d_maxh, c_d_das_reach, c_d_nlegal) differ from their level
counterparts by a PER-TIE CONSTANT (the pre-board is shared by all candidates at a tie), so they
rank IDENTICALLY within a tie and are not scored separately.
"""
import argparse, base64, glob, gzip, json, sys
import numpy as np

ALLOW = np.array([15 - abs(c - 3) // 2 for c in range(8)])

def das_reach(H):
    ok = H <= ALLOW[None, :]
    R = np.zeros_like(ok)
    R[:, 3] = ok[:, 3]
    for c in range(2, -1, -1): R[:, c] = R[:, c + 1] & ok[:, c]
    for c in range(4, 8):      R[:, c] = R[:, c - 1] & ok[:, c]
    return R

def nlegal_probe(H):
    horiz = (np.maximum(H[:, :-1], H[:, 1:]) < 16).sum(axis=1)
    vert = (H <= 14).sum(axis=1)
    return 2 * horiz + 2 * vert

def feats(b64s):
    """b64s: list of base64 planes -> dict name -> (n,) array"""
    A = np.stack([np.frombuffer(base64.b64decode(s), np.uint8).reshape(2, 16, 8) for s in b64s])
    occ = A[:, 0] != 0                                    # (n,16,8)
    top = np.where(occ, np.arange(16)[None, :, None], 16).min(1)
    H = 16 - top                                          # (n,8) height per column
    R = das_reach(H)
    f = {}
    f["a_topout_dist"]      = 16 - H.max(1)
    f["b_spawn_prox"]       = occ[:, 0:3, 2:6].sum((1, 2))
    f["b_spawn_prox_strict"]= occ[:, 0:2, 3:5].sum((1, 2))
    f["c_das_reach"]        = R.sum(1)
    f["c_nlegal_probe"]     = nlegal_probe(H)
    f["d_gvuln_mass"]       = np.maximum(0, H - 11).sum(1)
    f["d_crit_cols"]        = (H >= 14).sum(1)
    f["d_spawn_h"]          = np.maximum(H[:, 3], H[:, 4])
    f["e_escape_routes"]    = (H <= 10).sum(1)
    f["e_escape_reach"]     = (R & (H <= 10)).sum(1)
    f["x_hvar"]             = H.astype(float).var(1)
    f["x_jagged"]           = np.abs(np.diff(H.astype(np.int32), 1)).sum(1)
    return f

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", required=True)
    ap.add_argument("--boot", type=int, default=2000); a = ap.parse_args()
    rows = []
    for p in sorted(glob.glob(a.dir + "/*.jsonl.gz")):
        for ln in gzip.open(p, "rt"):
            r = json.loads(ln)
            if "labels" not in r: continue
            prog = [l[1] for l in r["labels"]]
            if max(prog) == min(prog): continue
            cands = [str(c) for c in r["cands"]]
            rows.append((r["seed"], np.array(prog, float), cands, r["planes"],
                         r["cands"].index(r["base_action"]), r["cands"].index(r["trt_action"])))
    print(f"discriminating ties {len(rows)} over {len({x[0] for x in rows})} seeds")
    seed = np.array([x[0] for x in rows]); P = np.array([x[1] for x in rows])
    champ = np.array([x[4] for x in rows]); h12 = np.array([x[5] for x in rows])
    allf = [feats([pl[c] for c in cd]) for _, _, cd, pl, _, _ in rows]
    names = list(allf[0])
    F = {n: np.stack([f[n] for f in allf]) for n in names}     # (nties,4)
    pk = lambda idx: P[np.arange(len(P)), idx]
    vh, vc, vr = pk(h12), pk(champ), P.mean(1)
    den = (vh - vr).sum(); cap = lambda v: (v - vr).sum() / den
    us = np.unique(seed); by = {s: np.where(seed == s)[0] for s in us}
    rng = np.random.default_rng(20260826)
    def ci(v):
        nv = v - vr; out = np.empty(a.boot)
        for b in range(a.boot):
            ii = np.concatenate([by[s] for s in rng.choice(us, len(us), True)])
            out[b] = (nv[ii].sum() - (vc - vr)[ii].sum()) / (vh[ii] - vr[ii]).sum()
        return np.percentile(out, [2.5, 97.5])
    base = cap(vc)
    print(f"\nBASELINE the substitute must beat -- CHAMPION's own tiebreak: {100*base:.1f}%")
    print(f"H12 = 100.0% by construction\n")
    res = []
    for n in names:
        for d, lab in ((1, "argmin"), (-1, "argmax")):
            v = pk(np.argmin(d * F[n], axis=1)); res.append((cap(v), n, lab, v))
    res.sort(reverse=True)
    print("| decider | transfer | vs CHAMPION |")
    print("|---|---|---|")
    for c, n, lab, v in res:
        lo, hi = ci(v)
        mark = " **BEATS CHAMPION**" if lo > 0 else ""
        print(f"| {lab}({n}) | {100*c:.1f}% | {100*(c-base):+.1f} pts [{100*lo:+.1f}, {100*hi:+.1f}]{mark} |")
    best = res[0]
    print(f"\n**IN-SAMPLE BEST OF {len(res)} deciders: {best[2]}({best[1]}) at {100*best[0]:.1f}% "
          f"vs champion {100*base:.1f}%**")
    print("**=> " + ("the in-sample best still LOSES to the champion: the static-substitute route is "
                     "DEAD at the function-class level, and multiplicity cannot rescue it "
                     "(in-sample best-of-N is biased UPWARD)."
                     if best[0] <= base else
                     "at least one decider beats the champion IN SAMPLE. This is a LEAD ONLY and "
                     "needs a held-out registration; best-of-N climbs when the truth is flat.") + "**")

if __name__ == "__main__":
    sys.exit(main())
