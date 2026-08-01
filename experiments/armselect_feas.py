#!/usr/bin/env python3
"""#34 -- CAN BOOT-TIME INFORMATION PICK THE ARM?

#32 found chain180 and lnk1 lose largely DIFFERENT seeds: an oracle that picks the right
arm per match scores 84.6% against chain180-alone's 70.9%. That is an ORACLE bound. This
asks the only question that matters for shipping it: does anything knowable AT BOOT --
the opening virus layout and the head of the capsule stream, both recoverable on the cart
(dr-mario-seed-replay-proven / dr-mario-seed-is-deterministic-on-cart) -- carry enough
signal to capture part of that gap?

★ THE METRIC IS THE DECISIVE SET, NOT RAW ACCURACY. On most matches both arms win or both
lose, and the selector cannot change those. Only matches where EXACTLY ONE arm wins are
steerable. On that set:
    always-chain180 (the shipping default) already scores 195/304 = 64.1%
    a coin flip scores ~50% -- WORSE than shipping
    the oracle scores 100%
So "beats 50%" is not a result; the bar is 64.1%, and captured share of the +13.7 pts is
(acc - 0.641) / (1 - 0.641). Reporting plain accuracy here would flatter a useless model.

★ EVALUATION IS SEED-CLUSTERED. The two swaps of a seed share a virus layout and the whole
capsule stream, so a random split leaks a near-duplicate of every test row into training.
GroupKFold on seed. Every number below is out-of-fold.

★ SIDE-LEAKAGE IS ASSERTED, NOT ASSUMED. #32 measured the lnk1 rescue rate as 50.0% on
swap 0 and 44.1% on swap 1 -- close, but "close" is not a control. A swap-only model is
fitted and reported alongside; if the feature model cannot beat it, the features are doing
nothing and the apparent skill is side.
"""
from __future__ import annotations
import json, os, sys, random
import numpy as np

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/vs_aware", ROOT + "/tmp/champion", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src",
          "/home/struktured/projects/dr-mario-qa-wt/experiments"):
    if p not in sys.path:
        sys.path.insert(0, p)

SP = "/home/struktured/projects/dr-mario-qa-wt/tmp/selfplay"


def load(fn):
    return {(r["seed"], r["swap"]): r
            for r in (json.loads(l) for l in open(os.path.join(SP, fn)) if l.strip())}


def boards_and_stream(seed, level, n_pills=24):
    """Exactly how VsMatch builds a match: P0 board from `seed`, P1 from `seed+1000`,
    and ONE capsule stream from `seed` shared by both (vs_env.py:38-51)."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    out = []
    for k in range(2):
        e = FaithfulDrMarioEnv(level=level, seed=seed + 1000 * k, max_pills=300)
        e.reset()
        NesPillSource(seed=seed).attach(e)
        e.cur = e._rand_pill(); e.nxt = e._rand_pill()
        out.append(e.board.color.copy())
    e = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    e.reset(); NesPillSource(seed=seed).attach(e)
    stream = [e._rand_pill() for _ in range(n_pills)]
    return out[0], out[1], stream


def board_feats(c, tag):
    """Opening layout only: rows, columns, colours. No play information."""
    occ = (c != 0)
    rows = occ.sum(axis=1).astype(float)
    cols = occ.sum(axis=0).astype(float)
    f = {}
    f[tag + "_n"] = float(occ.sum())
    f[tag + "_toprow"] = float(np.argmax(occ.any(axis=1))) if occ.any() else 16.0
    f[tag + "_rowspan"] = float(occ.any(axis=1).sum())
    f[tag + "_colmax"] = float(cols.max())
    f[tag + "_colmin"] = float(cols.min())
    f[tag + "_colstd"] = float(cols.std())
    f[tag + "_rowstd"] = float(rows.std())
    for col in range(1, 4):                       # colour balance
        f[f"{tag}_c{col}"] = float((c == col).sum())
    f[tag + "_colimb"] = float(max((c == k).sum() for k in (1, 2, 3))
                               - min((c == k).sum() for k in (1, 2, 3)))
    for r in range(0, 16, 4):                     # coarse row histogram
        f[f"{tag}_rb{r}"] = float(rows[r:r + 4].sum())
    return f


def stream_feats(stream):
    """`stream` is a list of drmario.faithful_game.Pill(a, b) -- named fields, not a tuple."""
    pr = [(p.a, p.b) for p in stream]
    f = {}
    f["st_double"] = sum(1 for a, b in pr if a == b) / len(pr)
    runs, cur = 1, pr[0]
    for q in pr[1:]:
        if q == cur:
            runs += 1
        cur = q
    f["st_repeat"] = runs / len(pr)
    for col in range(1, 4):
        f["st_c%d" % col] = sum((a == col) + (b == col) for a, b in pr) / (2.0 * len(pr))
    for i in range(6):                             # first six capsules, explicitly
        f["st_p%d_a" % i] = float(pr[i][0])
        f["st_p%d_b" % i] = float(pr[i][1])
    return f


def build(level, ch_file, lk_file, n_pills=24):
    ch, lk = load(ch_file), load(lk_file)
    keys = sorted(set(ch) & set(lk))
    seeds = sorted(set(k[0] for k in keys))
    cache = {}
    rows = []
    for (s, sw) in keys:
        if s not in cache:
            cache[s] = boards_and_stream(s, level, n_pills)
        b0, b1, stream = cache[s]
        cand, opp = (b0, b1) if sw == 0 else (b1, b0)
        f = {}
        f.update(board_feats(cand, "me"))
        f.update(board_feats(opp, "op"))
        f.update(stream_feats(stream))
        for k in list(f):                          # differences carry the matchup
            if k.startswith("me_"):
                f["d_" + k[3:]] = f[k] - f.get("op_" + k[3:], 0.0)
        f["swap"] = float(sw)
        rows.append({"seed": s, "swap": sw, "f": f,
                     "ch": ch[(s, sw)]["win"], "lk": lk[(s, sw)]["win"]})
    return rows, seeds


def decisive(rows):
    """Matches where exactly one arm wins -- the only ones a selector can move."""
    return [r for r in rows if (r["ch"] == 1.0) != (r["lk"] == 1.0)]


def _fit_logistic(X, y, l2=1.0, iters=400, lr=0.5):
    """Ridge-penalised logistic regression, plain numpy -- no sklearn in this venv, and a
    50-feature / ~300-row fit does not justify adding a dependency. Full-batch gradient
    descent on standardised inputs converges well inside `iters` at this size."""
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(Z @ w, -30, 30)))
        gr = Z.T @ (p - y) / len(y)
        gr[:-1] += l2 * w[:-1] / len(y)          # no penalty on the intercept
        w -= lr * gr
    return (mu, sd, w)


def _predict(model, X):
    mu, sd, w = model
    Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    return (Z @ w > 0).astype(int)


def evaluate(rows, seeds, feat_keys, name, folds=5, seed=3):
    D = decisive(rows)
    y = np.array([1 if r["ch"] == 1.0 else 0 for r in D])       # 1 = pick chain180
    X = np.array([[r["f"][k] for k in feat_keys] for r in D], dtype=float)
    g = np.array([r["seed"] for r in D])
    rng = random.Random(seed)
    order = seeds[:]; rng.shuffle(order)
    fold_of = {s: i % folds for i, s in enumerate(order)}
    pred = np.zeros(len(D), dtype=int)
    tr_hit = tr_tot = 0
    for k in range(folds):
        te = np.array([fold_of[s] == k for s in g])
        if te.sum() == 0 or (~te).sum() == 0:
            continue
        m = _fit_logistic(X[~te], y[~te])
        pred[te] = _predict(m, X[te])
        tr_hit += int((_predict(m, X[~te]) == y[~te]).sum()); tr_tot += int((~te).sum())
    acc = float((pred == y).mean())
    base = float((y == 1).mean())          # always-chain180
    return dict(name=name, n=len(D), acc=acc, base=base,
                train=tr_hit / tr_tot if tr_tot else float("nan"),
                captured=(acc - base) / (1 - base) if base < 1 else 0.0,
                pred=pred, y=y, g=g)


def boot_ci(res, seeds, B=3000, seed=5):
    rng = random.Random(seed)
    by = {}
    for p, t, s in zip(res["pred"], res["y"], res["g"]):
        by.setdefault(s, []).append((p, t))
    ss = list(by)
    out = []
    for _ in range(B):
        samp = [ss[rng.randrange(len(ss))] for _ in ss]
        pairs = [pt for s in samp for pt in by[s]]
        a = sum(1 for p, t in pairs if p == t) / len(pairs)
        b = sum(1 for _p, t in pairs if t == 1) / len(pairs)
        out.append((a - b) / (1 - b) if b < 1 else 0.0)
    out.sort()
    return out[int(.025 * B)], out[int(.975 * B)]


def main():
    level = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    ch_f = sys.argv[2] if len(sys.argv) > 2 else "chain180_permatch.jsonl"
    lk_f = sys.argv[3] if len(sys.argv) > 3 else "lnk1_permatch.jsonl"
    print(f"=== ARM-SELECT FEASIBILITY  L{level}   {ch_f}  vs  {lk_f}")
    rows, seeds = build(level, ch_f, lk_f)
    D = decisive(rows)
    n = len(rows)
    ch_wr = sum(r["ch"] for r in rows) / n
    lk_wr = sum(r["lk"] for r in rows) / n
    orac = sum(1 for r in rows if r["ch"] == 1.0 or r["lk"] == 1.0) / n
    print(f"  matches {n}  seeds {len(seeds)}   chain180 {100*ch_wr:.1f}%  "
          f"lnk1 {100*lk_wr:.1f}%  ORACLE {100*orac:.1f}%  (+{100*(orac-ch_wr):.1f} pts)")
    print(f"  DECISIVE (exactly one arm wins): {len(D)}  "
          f"({100*len(D)/n:.1f}% of matches) -- the steerable set")
    allk = sorted(rows[0]["f"])
    sets = {
        "swap only (side-leak control)": ["swap"],
        "capsule stream head":           [k for k in allk if k.startswith("st_")],
        "opening layouts":               [k for k in allk if k[:3] in ("me_", "op_", "d_v")
                                          or k.startswith("d_")],
        "everything":                    [k for k in allk if k != "PLANT"],
    }
    # ★ POSITIVE CONTROL. A null result is only worth reading if the instrument can
    # detect a signal that IS there. Plant a feature that agrees with the label 80% of
    # the time and require the pipeline to recover most of it. If this row fails, every
    # negative below is uninformative -- a broken fitter also returns "no signal".
    rngp = random.Random(99)
    for r in rows:
        r["f"]["PLANT"] = float(r["ch"] == 1.0) if rngp.random() < 0.80 else float(r["ch"] != 1.0)
    print()
    print("  %-32s %5s %8s %8s %8s %8s   %s" % ("feature set", "n", "base", "train",
                                                "acc", "captured", "95% CI on captured"))
    pc = evaluate(rows, seeds, ["PLANT"], "POSITIVE CONTROL (planted 80%)")
    lo, hi = boot_ci(pc, seeds)
    print("  %-32s %5d %7.1f%% %7.1f%% %7.1f%% %7.1f%%   [%+.1f%%, %+.1f%%]" % (
        pc["name"], pc["n"], 100*pc["base"], 100*pc["train"], 100*pc["acc"],
        100*pc["captured"], 100*lo, 100*hi))
    assert pc["captured"] > 0.30, (
        "POSITIVE CONTROL FAILED (captured %.1f%%): the pipeline cannot recover a planted "
        "80%% signal, so the negatives below mean nothing." % (100*pc["captured"]))
    print("    ^ instrument verified: it recovers a signal that is genuinely present.")
    for nm, ks in sets.items():
        ks = [k for k in ks if k in rows[0]["f"]]
        if not ks:
            continue
        r = evaluate(rows, seeds, ks, nm)
        lo, hi = boot_ci(r, seeds)
        print("  %-32s %5d %7.1f%% %7.1f%% %7.1f%% %7.1f%%   [%+.1f%%, %+.1f%%]" % (
            nm, r["n"], 100*r["base"], 100*r["train"], 100*r["acc"],
            100*r["captured"], 100*lo, 100*hi))
    print()
    print("  base = always-chain180 (the shipping default). captured = share of the")
    print("  oracle gap that the selector actually recovers, out-of-fold, seed-clustered.")
    print("  A captured CI containing 0 means: no better than shipping chain180 always.")


if __name__ == "__main__":
    main()
