"""m2_screens.py — M2 offline distillation screens (REGISTRATION_M2_SCREENS.md).

Stage `instruments` (this file's first deliverable): measure the FLOOR and
CEILING that every M2 bar is a fraction of (R38), per stratum, before any fit
exists.

Statistic (confirm-halves only — the screen forks chose the shortlist, so
including them would re-import selection; the vacuous-control and
range-restriction lessons of M1 apply):
  dec-half  = sum(s2[0:3])  per shortlist candidate  (0..3)
  eval-half = sum(s2[3:6])  per shortlist candidate  (0..3)
  A decider D maps a state to a shortlist candidate or STAND (champion pick).
  capture(D) = mean over states of eval_half(D(state)) - eval_half(champ).
  (STAND contributes 0 by construction; capture is in eval-half survival
  points, 0..3 scale.)

CEILING = the tribunal itself decided from the dec-half at the half-scaled
promoted rule (override iff champ_dec <= 1 AND best_dec - champ_dec >= 2,
pick argmax (dec_half, champ value)), scored on the eval-half. This is what
perfect imitation of the teacher's verdict could earn under label noise.
FLOOR = the same decision procedure with dec-half sums permuted across
candidates within state (val tiebreak intact), scored on the true eval-half;
20 draws, mean +/- sd (R38a).

Populations: all non-degenerate states; the danger subset (champ_s2 <= 3)
reported alongside (M2's effective-n rider). Strata never pooled.
"""
import glob
import gzip
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "labels_m1")


def load(stratum, include_smoke=False):
    out = []
    for f in sorted(glob.glob(os.path.join(OUT, stratum, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        assert r.get("schema") == "m1v1", f
        if r["smoke"] and not include_smoke:
            continue
        out.append(r)
    return out


def state_view(adj):
    """(shortlist dec/eval/val arrays, champ index in shortlist) or None."""
    sh = [c for c in adj["cands"] if "s2" in c]
    champ_i = None
    for i, c in enumerate(sh):
        if c["rep_slot"] == adj["champ_rep"]:
            champ_i = i
    if champ_i is None or len(sh) < 2:
        return None
    dec = np.array([sum(c["s2"][0:3]) for c in sh], float)
    ev = np.array([sum(c["s2"][3:6]) for c in sh], float)
    val = np.array([c["val"] for c in sh], float)
    return dec, ev, val, champ_i


def decide(dec, val, champ_i):
    """Half-scaled promoted rule on the dec-half. Returns chosen index."""
    order = sorted(range(len(dec)), key=lambda i: (-dec[i], -val[i]))
    best = order[0]
    if dec[champ_i] <= 1 and dec[best] - dec[champ_i] >= 2 \
            and best != champ_i:
        return best
    return champ_i


def capture(states, permute_rng=None):
    gains = []
    fired = 0
    for dec, ev, val, ci in states:
        d = dec
        if permute_rng is not None:
            idx = permute_rng.sample(range(len(dec)), len(dec))
            d = dec[np.array(idx)]
        pick = decide(d, val, ci)
        if pick != ci:
            fired += 1
        gains.append(ev[pick] - ev[ci])
    return float(np.mean(gains)), fired / max(len(states), 1)


def seed_cluster_ci(recs, fn, b=2000, rng=None):
    """Bootstrap over seeds (games) of a per-state statistic."""
    rng = rng or random.Random(11)
    per_seed = [fn(r) for r in recs]
    per_seed = [p for p in per_seed if p is not None]
    means = []
    for _ in range(b):
        draw = [per_seed[rng.randrange(len(per_seed))] for _ in per_seed]
        num = sum(g for g, n in draw)
        den = sum(n for g, n in draw)
        if den:
            means.append(num / den)
    return (float(np.percentile(means, 2.5)),
            float(np.percentile(means, 97.5)))


def stage_instruments():
    for stratum in ("L20", "L11M"):
        recs = load(stratum)
        views = {}
        for r in recs:
            vs = []
            for a in r["adjudications"]:
                if a["degenerate"]:
                    continue
                v = state_view(a)
                if v is not None:
                    vs.append((v, a["champ_s2"] <= 3))
            views[r["seed"]] = vs
        allv = [v for vs in views.values() for v, _ in vs]
        dangv = [v for vs in views.values() for v, d in vs if d]

        def per_seed_gain(r, danger=False):
            vs = [(v, d) for v, d in views[r["seed"]] if (d or not danger)]
            if not vs:
                return None
            g = 0.0
            for v, _ in vs:
                dec, ev, val, ci = v
                pick = decide(dec, val, ci)
                g += ev[pick] - ev[ci]
            return (g, len(vs))

        ceil_all, dose_all = capture(allv)
        lo, hi = seed_cluster_ci(recs, per_seed_gain)
        ceil_d, dose_d = capture(dangv) if dangv else (float("nan"), 0)
        floors = [capture(allv, permute_rng=random.Random(3000 + i))[0]
                  for i in range(20)]
        floors_d = [capture(dangv, permute_rng=random.Random(3000 + i))[0]
                    for i in range(20)] if dangv else [float("nan")]
        print(f"[m2-instr] {stratum} states={len(allv)} danger={len(dangv)}")
        print(f"[m2-instr] {stratum} CEILING all-states capture="
              f"{ceil_all:.4f} CI[{lo:.4f},{hi:.4f}] dose={dose_all:.4f}")
        print(f"[m2-instr] {stratum} CEILING danger-subset capture="
              f"{ceil_d:.4f} dose={dose_d:.4f}")
        print(f"[m2-instr] {stratum} FLOOR (20 draws) all-states "
              f"mean={np.mean(floors):.4f} sd={np.std(floors):.4f} | "
              f"danger mean={np.mean(floors_d):.4f} "
              f"sd={np.std(floors_d):.4f}")
        hr = ceil_all - np.mean(floors)
        print(f"[m2-instr] {stratum} HEADROOM all-states = {hr:.4f} "
              f"({'usable' if hr > 0.005 else 'NO HEADROOM — M2 cannot '
                 'screen on this stratum'})", flush=True)
    json_path = os.path.join(HERE, "out", "m2_instruments.json")
    print(f"[m2-instr] (numbers above are the R38 anchors; bars get filled "
          f"in REGISTRATION_M2 from these + team-lead sign-off)")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "instruments"
    {"instruments": stage_instruments}[stage]()
