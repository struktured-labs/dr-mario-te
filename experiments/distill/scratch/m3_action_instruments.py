"""m3_action_instruments.py — M3 §4.R2 (team-lead ruling 2026-08-28).

⚠ THIS FILE FIXES THE METHOD, NOT THE NUMBER. The bar is a FRACTION OF
MEASURED HEADROOM, and the headroom must be re-measured on the bank the M3 fit
will actually use (base + PHASE 1 census + reserve census). Freezing today's
number and carrying it forward would import a bar calibrated for a smaller,
differently-composed population — the exact R62 error this ruling exists to
avoid. Measured floors differ materially by split already (L20 train 0.2115 vs
held 0.1274), which is the evidence that the LEVEL does not transfer even when
the HEADROOM does (0.1555 vs 0.1629).

M3 §4.R2: derive g's ACTION bar on independent reference data, BEFORE any
guard exists (R62 + R38 discipline, same shape as the M2 capture instruments).

STATISTIC (the one M3 will actually compute):
  recall = P(decider fires | the TEACHER fires), on held-out danger states.

Fork-half split so predictor and target never share a fork (the M2 instruments'
own device):
  target    "teacher fires" = half-scaled promoted rule on the EVAL half s2[3:6]
  predictor                 = the same rule on the DEC half s2[0:3]
CEILING = the tribunal predicting ITSELF across independent fork halves — what
          perfect imitation can reach under this label noise.
FLOOR   = the same predictor with dec-half sums permuted across candidates
          within state (20 draws) — a dose-matched random decider.
Also reported: PRECISION and the dose, because a recall bar alone is gameable
by an always-fire decider (R53: a one-sided gate is blind to the other side).
"""
import glob, gzip, json, os, random, sys
import numpy as np
sys.path.insert(0, ".")
import m2_screens as M

def rule(h, val, ci):
    """Half-scaled promoted rule on a 0..3 half: fire iff champ<=1 and
    best-champ>=2 and best is not the champion."""
    order = sorted(range(len(h)), key=lambda i: (-h[i], -val[i]))
    b = order[0]
    return int(h[ci] <= 1 and h[b] - h[ci] >= 2 and b != ci)

def collect(stratum, split="train"):
    """split='train' is the R62-correct reference: the bar must come from data
    the verdict is NOT computed on. Held-out states are scored, never used to
    set the bar they will be judged against."""
    out = []
    for f in sorted(glob.glob(os.path.join(M.OUT, stratum, "seed_*.json.gz"))):
        r = json.load(gzip.open(f, "rt"))
        if r["smoke"]:
            continue
        if split == "train" and M.held(r["seed"]):
            continue
        if split == "held" and not M.held(r["seed"]):
            continue
        for a in r["adjudications"]:
            if a["degenerate"] or a["champ_s2"] > 3:
                continue                      # danger states only
            v = M.state_view(a)
            if v is None:
                continue
            dec, ev, val, ci = v
            out.append((dec, ev, val, ci, r["seed"]))
    return out

# PRE-COMMITTED SPLIT (team-lead ruling 2026-08-28): the bar is DERIVED ON
# TRAIN and the guard is JUDGED ON HELD-OUT. The held row below is printed as a
# transparency check ONLY and must never be used to set the bar — choosing the
# split after seeing the bank is the degree of freedom this pinning removes.
for stratum, split in (("L20","train"), ("L20","held"), ("L11M","train")):
    S = collect(stratum, split)
    stratum = f"{stratum}/{split}"
    if len(S) < 20:
        print(f"== {stratum}: n={len(S)} — too thin to derive a bar"); continue
    tgt = np.array([rule(ev, val, ci) for _, ev, val, ci in
                    [(d, e, v, c) for d, e, v, c, _ in S]])
    pred = np.array([rule(d, val, ci) for d, _, val, ci in
                     [(d, e, v, c) for d, e, v, c, _ in S]])
    npos = int(tgt.sum())
    def stats(p):
        tp = int((p & tgt).sum()); fp = int((p & (1 - tgt)).sum())
        rec = tp / npos if npos else float("nan")
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        return rec, prec, p.mean()
    c_rec, c_prec, c_dose = stats(pred)
    fl = []
    for i in range(20):
        rng = random.Random(4000 + i)
        pp = []
        for d, ev, val, ci, _ in S:
            idx = rng.sample(range(len(d)), len(d))
            pp.append(rule(d[np.array(idx)], val, ci))
        fl.append(stats(np.array(pp))[0])
    f_rec, f_sd = float(np.mean(fl)), float(np.std(fl))
    hr = c_rec - f_rec
    print(f"== {stratum}: danger states n={len(S)}  teacher fires on "
          f"{npos} ({npos/len(S):.3f})")
    print(f"   CEILING (tribunal self-transfer, dec->eval): recall={c_rec:.4f} "
          f"precision={c_prec:.4f} dose={c_dose:.4f}")
    print(f"   FLOOR   (dose-matched shuffle, 20 draws):    recall={f_rec:.4f} "
          f"+/-{f_sd:.4f}")
    print(f"   HEADROOM = {hr:+.4f}")
    if hr > 2 * f_sd:
        for frac, lab in ((0.30, "0.30 of headroom (matches the M2 GO bar's construction)"),
                          (0.50, "0.50 of headroom")):
            print(f"   -> BAR (TRAIN-DERIVED ONLY) at {lab}: recall >= {f_rec + frac*hr:.4f}")
    else:
        print(f"   -> NO USABLE HEADROOM: cannot set a recall bar on this "
              f"stratum (headroom inside 2sd of the floor)")
