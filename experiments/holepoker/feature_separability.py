#!/usr/bin/env python3
"""CAN THE EXISTING 11-FEATURE VOCABULARY TELL A FATAL MOVE FROM A SURVIVING ONE?

This lane owns the only corpus in the project where BOTH are known: for every
death with an escape, we have the move the champion chose (fatal) and a move
that would have survived.

WHY IT IS WORTH ASKING RATHER THAN ASSUMING. The eval-headroom lane found the
best reweighting of these 11 features buys -0.57 pills against an oracle's
+3.70, cross-validated R^2 = -0.304 -- i.e. the vocabulary cannot state what the
oracle knows ON ORDINARY SAMPLED POSITIONS. Deaths are a different distribution.
If the features DO separate fatal from surviving here, a re-weighting that only
has to be right in the pre-death regime is far cheaper than a new value
function. If they don't, that is the vocabulary wall confirmed on the population
that actually matters.

THE FEATURES are the champion's own leaf term vector -- literally what a
reweighting would reweight (`fast_rtl_x._combine_terms`):
    MAXH HOLES TOPRISK SPAWN SETUP MATCHED BURIED RDYEXT VRDY CROSS POLL
computed on the board AFTER the placement, which is what the leaf scores.

THREE METHOD RULES, each from a failure this program already paid for:

 1 MATCHED CONTROL. Any feature separating fatal-from-surviving will probably
   also separate chosen-from-unchosen, because the champion's argmax already
   moves these features by construction. So every comparison is run TWICE:
   chosen-vs-survivor and chosen-vs-RANDOM-legal. **Only the difference between
   those two is evidence.** (The garbage-scheduler lane was bitten by exactly
   this.)
 2 SPLIT BY E, never pool. E=1 is horizon-reachable; E>=4 is eval-only. They may
   have opposite signatures and pooling would hide it.
 3 REPORT THE NULL LOUDLY. "No feature separates them" is the likely outcome and
   the more valuable one.

Analysis only -- no new games. Existing corpora, replayed against the memo.
"""
from __future__ import annotations
import sys, os, json, argparse, random, math
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ROOT = "/home/struktured/projects/dr_mario_rl"
for _p in (HERE, QA, QA + "/eval47", ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
           ROOT + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np              # noqa: E402
import champion as CH           # noqa: E402

NAMES = ["MAXH", "HOLES", "TOPRISK", "SPAWN", "SETUP", "MATCHED", "BURIED",
         "RDYEXT", "VRDY", "CROSS", "POLL"]
NT = len(NAMES)


def features(col, vir):
    """The champion's own 11 leaf terms for a board."""
    import fast_rtl_x as FX
    base = np.zeros(64, dtype=np.int64)
    _w, fl = FX.variant("winner")
    FX._base_scan(col, vir, fl, base)
    return np.array([base[i] for i in range(NT)], dtype=np.float64)


def child_features(board, action, ca, cb):
    """Features of the board AFTER `action` -- what the leaf actually scores."""
    nb = board.clone()
    ok, _c, _v, _ch = CH.apply_action(nb, action, ca, cb)
    if not ok:
        return None
    col, vir = CH.board_to_flat(nb)
    return features(col, vir)


# --------------------------------------------------------------- corpora
def load_escapes(rng):
    """Every death with a known escape, replayed to its escape ply."""
    import pressure_escape as PE
    import bursty_frozen as BF
    out = []
    done = [0]
    drip = {"results/pressure_escape.json": (11, 2, 5, 20),
            "results/pressure_escape_p8.json": (11, 2, 8, 25),
            "results/pressure_escape_L17.json": (17, 2, 5, 20)}
    for f, (lvl, k, per, aft) in drip.items():
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        for r in json.load(open(p)):
            if r["result"] not in ("topout", "nomove") or r.get("E") is None:
                continue
            res, plies, trace, _v0 = PE.play(r["seed"], lvl, k, per, aft, record=True)
            if res != r["result"] or plies != r["plies"]:
                continue
            m = [t for t in trace if t.get("ply") == r["escape_ply"] and "col" in t]
            if not m:
                continue
            out.append({"src": "drip", "seed": r["seed"], "E": r["E"],
                        "t": m[0], "alt": r["alt"]})
            done[0] += 1
            if done[0] % 10 == 0:
                print(f"    replayed {done[0]} deaths...", flush=True)
    p = os.path.join(HERE, "results/bursty_frozen_cal.json")
    if os.path.exists(p):
        for r in json.load(open(p)):
            if r["result"] not in ("topout", "nomove") or r.get("E") is None:
                continue
            res, plies, trace, _v0, fired = BF.play(r["seed"], r["level"], record=True)
            if res != r["result"] or plies != r["plies"]:
                continue
            m = [t for t in trace if t.get("ply") == r["escape_ply"] and "col" in t]
            if not m:
                continue
            out.append({"src": "bursty", "seed": r["seed"], "E": r["E"],
                        "t": m[0], "alt": r["alt"]})
    return out


# ----------------------------------------------------------------- stats
def sign_test(diffs):
    """Two-sided exact sign test on paired differences (ties dropped)."""
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    n = pos + neg
    if n == 0:
        return 1.0, 0, 0
    k = max(pos, neg)
    p = 2 * sum(math.comb(n, i) for i in range(k, n + 1)) / (2 ** n)
    return min(1.0, p), pos, neg


def cohen_dz(diffs):
    if len(diffs) < 2:
        return 0.0
    m = float(np.mean(diffs)); s = float(np.std(diffs, ddof=1))
    return m / s if s > 0 else 0.0


def loo_logistic(X, y):
    """Leave-one-out accuracy of a linear model on the 11-dim difference vector.
    Tiny n, so LOO and a strongly regularised model -- an in-sample fit here
    would separate anything."""
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
    except ImportError:
        return None
    n = len(y)
    if n < 8 or len(set(y)) < 2:
        return None
    ok = 0
    for i in range(n):
        tr = [j for j in range(n) if j != i]
        if len(set(y[j] for j in tr)) < 2:
            continue
        clf = make_pipeline(StandardScaler(),
                            LogisticRegression(C=0.1, max_iter=2000))
        clf.fit(X[tr], [y[j] for j in tr])
        ok += int(clf.predict(X[i:i + 1])[0] == y[i])
    return ok / n


def analyse(rows, label, out):
    if len(rows) < 4:
        print(f"\n--- {label}: n={len(rows)} -- TOO FEW TO TEST, reported as untested")
        out[label] = {"n": len(rows), "verdict": "untested"}
        return
    print(f"\n--- {label}  (n={len(rows)} deaths) ---")
    print(f"  {'feature':<9s} {'chosen-SURVIVOR':>22s} {'chosen-RANDOM':>22s} {'excess':>8s}")
    print(f"  {'':<9s} {'mean    dz    p':>22s} {'mean    dz    p':>22s}")
    surv = np.array([r["f_chosen"] - r["f_surv"] for r in rows])
    rand = np.array([r["f_chosen"] - r["f_rand"] for r in rows])
    res = {}
    flagged = []
    for i, nm in enumerate(NAMES):
        ds, dr = surv[:, i], rand[:, i]
        ps, _a, _b = sign_test(ds)
        pr, _c, _d = sign_test(dr)
        zs, zr = cohen_dz(ds), cohen_dz(dr)
        excess = abs(zs) - abs(zr)
        res[nm] = {"surv_mean": float(np.mean(ds)), "surv_dz": zs, "surv_p": ps,
                   "rand_mean": float(np.mean(dr)), "rand_dz": zr, "rand_p": pr,
                   "excess_dz": excess}
        star = ""
        if ps < 0.05 and excess > 0.2:
            star = "  <== separates MORE than the control"
            flagged.append(nm)
        print(f"  {nm:<9s} {np.mean(ds):>8.2f} {zs:>6.2f} {ps:>6.3f} "
              f"{np.mean(dr):>8.2f} {zr:>6.2f} {pr:>6.3f} {excess:>8.2f}{star}")
    # simple combination, honestly cross-validated
    X = np.vstack([surv, rand])
    y = [1] * len(surv) + [0] * len(rand)
    acc = loo_logistic(X, y)
    print(f"\n  simple linear combination (LOO-CV, survivor-diff vs random-diff): "
          f"{'%.1f%%' % (acc*100) if acc is not None else 'n/a'}  "
          f"(50% = the vocabulary cannot tell them apart)")
    out[label] = {"n": len(rows), "features": res, "loo_acc": acc,
                  "flagged": flagged}
    return flagged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default="results/feature_separability.json")
    a = ap.parse_args()
    CH.init_champion()
    # attach the persistent store -- this replays ~90 full games and a champion
    # reply is 56 ms cold; without it the analysis is compute-bound on work the
    # project has already done and saved
    import memo_db
    db = memo_db.ChampionMemo(max_local=400_000, flush_every=20_000)
    CH.attach_db(db)
    rng = random.Random(20260807)
    esc = load_escapes(rng)
    db.flush()
    print(f"    memo: {db.info()['entries']} entries, "
          f"hit rate {db.info()['hit_rate']:.1%}", flush=True)
    print(f"=== FEATURE SEPARABILITY: {len(esc)} deaths with a known escape ===")

    rows = []
    for e in esc:
        t = e["t"]
        b = CH.board_from_flat(t["col"], t["vir"])
        ca, cb = t["cur"]
        legal = CH.legal_actions(b, ca, cb)
        alts = [x for x in legal if x != t["act"] and x != e["alt"]]
        if not alts:
            continue
        f_ch = child_features(b, t["act"], ca, cb)
        f_sv = child_features(b, e["alt"], ca, cb)
        f_rd = child_features(b, rng.choice(alts), ca, cb)
        if f_ch is None or f_sv is None or f_rd is None:
            continue
        rows.append({"src": e["src"], "seed": e["seed"], "E": e["E"],
                     "f_chosen": f_ch, "f_surv": f_sv, "f_rand": f_rd})
    print(f"    usable (chosen, survivor and a random control all legal): {len(rows)}")

    out = {}
    analyse(rows, "ALL", out)
    analyse([r for r in rows if r["E"] == 1], "E=1  (horizon-reachable)", out)
    analyse([r for r in rows if r["E"] is not None and 2 <= r["E"] <= 3],
            "E=2-3", out)
    analyse([r for r in rows if r["E"] is not None and r["E"] >= 4],
            "E>=4  (eval-only)", out)

    with open(os.path.join(HERE, a.out), "w") as fh:
        json.dump({k: {kk: (vv if not isinstance(vv, np.ndarray) else vv.tolist())
                       for kk, vv in v.items()} for k, v in out.items()},
                  fh, indent=1, default=str)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
