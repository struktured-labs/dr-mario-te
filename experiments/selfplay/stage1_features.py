#!/usr/bin/env python3
"""STAGE 1b -- SPLIT THE HEADROOM: reweighting vs new features.

WHY THIS EXISTS
---------------
Stage 1 measures how much a PERFECT leaf evaluator would buy. That number alone
does not say what to build, because it lumps together two very different causes:

  H_linear   -- headroom reachable by REWEIGHTING the features the eval already
                has. If this is most of it, the answer is another coef-opt pass,
                not a neural network.
  H_features -- headroom that no reweighting can reach, i.e. the existing feature
                set cannot express the distinction that matters. This is the ONLY
                case that argues for NNUE, and it is the case worth knowing about.

The split is computable for free from the Stage-1 labels, because the shipped leaf
eval is already a LINEAR model:

    leaf = BIAS - MAXH*t0 - HOLES*t1 - TOPRISK*t2 - SPAWN*t3 + SETUP*t4
           + MATCHED*t5 - BURIED*t6 + RDYEXT*t7 + VRDY*t8 + CROSS*t9 - POLL*t10
    (then wrapped to signed 16-bit)

-- eleven hand-designed integer board features with hand-tuned coefficients. In
NNUE terms the shipped eval IS the degenerate case: hand features, one linear
layer, no hidden layer. So "fit the best possible linear model over these same
features against the rollout labels, and see how much of the oracle's advantage it
recovers" is a well-posed and cheap upper bound on H_linear.

HONEST FITTING (the part that is easy to get wrong)
---------------------------------------------------
  * Targets are CENTRED WITHIN POSITION. What a leaf eval must get right is the
    ranking among one position's successors; a model fitted on raw values would
    spend all its capacity predicting "how many viruses are left", score a
    magnificent R^2, and be useless for choosing moves.
  * Evaluation is CROSS-VALIDATED BY POSITION, never by row. Rows from the same
    position share a board, a pill, and a rollout stream; splitting by row lets the
    model see its own test positions and reports memorisation as generalisation.
  * The fitted policy is scored by the SAME split-sample machinery as the oracle,
    so H_linear and H_total are measured on one ruler.

A self-check gates the whole thing: the extracted term vector, recombined with the
shipped weights, must reproduce the leaf value recorded during labelling EXACTLY.
That asserts the artefact (the numbers) rather than that the extraction merely ran.

Usage:
  stage1_features.py extract --labels out/labels_main.jsonl --corpus out/corpus.npz \
                             --out out/feats.npz
  stage1_features.py fit     --feats out/feats.npz --labels out/labels_main.jsonl
"""
from __future__ import annotations

import os
import sys
import json
import math
import random
import argparse
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

TERM_NAMES = ["maxh", "holes", "toprisk", "spawn", "setup", "matched",
              "buried", "rdy", "vrdy", "cross", "poll", "nvir"]
# signs as _combine_terms applies them (BIAS excluded); nvir is not in the combine
COMBINE_SIGN = np.array([-1, -1, -1, -1, +1, +1, -1, +1, +1, +1, -1, 0], dtype=np.float64)
WEIGHT_IDX = ["R_MAXH", "R_HOLES", "R_TOPRISK", "R_SPAWN", "R_SETUP", "R_MATCHED",
              "R_BURIED", "R_RDYEXT", "R_VRDY", "R_CROSS", "R_POLL", None]


def cmd_extract(args):
    import sp_engine as E
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core

    champ = E.Champion()
    w, fl = champ.w, champ.fl
    d = np.load(args.corpus)
    col_a, vir_a, link_a, pills_a = d["col"], d["vir"], d["link"], d["pills"]

    recs = [json.loads(l) for l in open(args.labels)]
    print(f"records: {len(recs)}")

    env = E.new_env(level=E.LEVEL, seed=0, cap=200)
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    base = np.empty(FX.NBASE, dtype=np.int64)

    rows_pos, rows_act, rows_ts, rows_tr, rows_win = [], [], [], [], []
    checked = mismatch = 0
    for r in recs:
        i = r["idx"]
        col = col_a[i].astype(np.int8)
        vir = vir_a[i].astype(np.int8)
        link = link_a[i].astype(np.int8)
        ca, cb, na, nb = (int(pills_a[i][0]), int(pills_a[i][1]),
                          int(pills_a[i][2]), int(pills_a[i][3]))
        for a in r["acts"]:
            var, cc = a // 8, a % 8
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            # terms of the board THE SEARCH believes it reaches
            FX._base_scan(c1, v1, fl, base)
            ts = base[:FX.NT].astype(np.int64).copy()
            # TERMINAL WINS ARE NOT LINEAR-EVAL BOARDS. _leafv_ship short-circuits
            # to _WIN_SHIP when the placement clears the last virus, so those rows
            # carry a sentinel, not a score the eval's weights produced. Folding
            # them into the regression would fit 11 board features to the constant
            # 30000 and quietly corrupt every coefficient. They are flagged here
            # and dropped from the fit; the depth-3 policy still handles them
            # correctly, because champ_root goes through _leafv_ship too.
            # (Found by this self-check, not by inspection.)
            win = int(FX._virus_count(v1) == 0)
            checked += 1
            if win:
                if int(r["leaf_search"][str(a)]) != int(FX._WIN_SHIP):
                    mismatch += 1
                    if mismatch <= 3:
                        print(f"  WIN SENTINEL MISMATCH idx={i} a={a} "
                              f"recorded={r['leaf_search'][str(a)]}")
            else:
                # SELF-CHECK: recombining must reproduce the leaf value recorded at
                # labelling time. Asserts the numbers, not that the call returned.
                recomb = int(FX._combine_terms(ts, w))
                rec_leaf = int(r["leaf_search"][str(a)])
                if recomb != rec_leaf:
                    mismatch += 1
                    if mismatch <= 3:
                        print(f"  TERM MISMATCH idx={i} a={a} "
                              f"recombined={recomb} recorded={rec_leaf}")
            # terms of the board the REAL sim reaches (full cascade)
            E.attach_stream(env, 1)
            E.set_board(env.board, col, vir, link)
            E.set_pills(env, ca, cb, na, nb)
            env.pills_placed = 0
            env._start_viruses = int(env.board.virus_count())
            env.step(int(a))
            rc, rv, _rl = E.board_planes(env.board)
            FX._base_scan(np.ascontiguousarray(rc), np.ascontiguousarray(rv), fl, base)
            tr = base[:FX.NT].astype(np.int64).copy()

            rows_pos.append(i)
            rows_act.append(a)
            rows_ts.append(ts)
            rows_tr.append(tr)
            rows_win.append(win)

    print(f"self-check: {checked} boards, {mismatch} term mismatches "
          f"-> {'PASS' if mismatch == 0 else 'FAIL'}")
    if mismatch:
        return 1
    np.savez_compressed(args.out,
                        pos=np.array(rows_pos, dtype=np.int64),
                        act=np.array(rows_act, dtype=np.int64),
                        terms_search=np.stack(rows_ts),
                        terms_real=np.stack(rows_tr),
                        win=np.array(rows_win, dtype=np.int64))
    print(f"wrote {args.out}  ({len(rows_pos)} labelled boards)")
    return 0


# --------------------------------------------------------------------- fitting
def _spearman(x, y):
    n = len(x)
    if n < 3:
        return float("nan")

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(x), rank(y)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx > 0 and dy > 0 else float("nan")


def boot_ci(xs, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(st.mean([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def _weights_from_beta(beta, T, args):
    """Turn fitted per-term coefficients into a shipped-layout weight vector.

    _combine_terms applies FIXED signs (it subtracts maxh/holes/..., adds
    setup/matched/...), so realising a coefficient c_i needs w[R_i] = c_i * sign_i.
    The result is then RESCALED so the refit leaf spans the same dynamic range as
    the shipped one: _combine_terms wraps to signed 16 bits, and an unscaled fit in
    'pills' units would wrap around and score garbage -- a silent failure that would
    look like 'the refit is bad' rather than 'the refit overflowed'.
    """
    import fast_rtl_x as FX
    w, fl = FX.variant("winner")
    idx = [FX.R_MAXH, FX.R_HOLES, FX.R_TOPRISK, FX.R_SPAWN, FX.R_SETUP,
           FX.R_MATCHED, FX.R_BURIED, FX.R_RDYEXT, FX.R_VRDY, FX.R_CROSS, FX.R_POLL]
    shipped = np.array([COMBINE_SIGN[i] * w[idx[i]] for i in range(11)])
    c = np.array(beta[:11], dtype=np.float64)
    Ts = T[:, :11]
    sd_ship = float(np.std(Ts @ shipped))
    sd_fit = float(np.std(Ts @ c))
    if sd_fit > 0 and sd_ship > 0:
        c = c * (sd_ship / sd_fit)
    wf = w.copy()
    for i in range(11):
        wf[idx[i]] = COMBINE_SIGN[i] * c[i]
    return wf


_D3_CACHE = {}


def _d3_values(posi, wfit, corpus, champ):
    """Root values of all 32 actions from the FULL depth-3 search with a given leaf."""
    import sp_engine as E
    key = (posi, wfit.tobytes())
    if key in _D3_CACHE:
        return _D3_CACHE[key]
    col = corpus["col"][posi].astype(np.int8)
    vir = corpus["vir"][posi].astype(np.int8)
    p = corpus["pills"][posi]
    val = np.zeros(32, dtype=np.float64)
    ok = np.zeros(32, dtype=np.int8)
    E.champ_root(col, vir, int(p[0]), int(p[1]), int(p[2]), int(p[3]),
                 champ.topk2, E.W_EXCAV, E.W_HANG, wfit, champ.fl, champ.ws,
                 val, ok)
    _D3_CACHE[key] = val
    return val


def cmd_fit(args):
    import sp_engine as E
    import fast_rtl_x as FX

    champ = E.Champion()
    corpus = np.load(args.corpus)
    f = np.load(args.feats)
    pos, act = f["pos"], f["act"]
    T = f["terms_real" if args.real else "terms_search"].astype(np.float64)
    WIN = f["win"] if "win" in f else np.zeros(len(pos), dtype=np.int64)

    recs = {r["idx"]: r for r in (json.loads(l) for l in open(args.labels))}
    CENSOR = 200.0

    # value per (position, action), and the champion's own pick per position
    key = {}
    for k in range(len(pos)):
        r = recs[int(pos[k])]
        a = str(int(act[k]))
        vals = [(-float(p) if o == "clear" else -CENSOR)
                for p, o in zip(r["pills"][a], r["outcome"][a])]
        key[(int(pos[k]), int(act[k]))] = (k, vals)

    positions = sorted({int(p) for p in pos})
    print(f"positions {len(positions)}  labelled boards {len(pos)}")

    # ---- build per-position blocks -------------------------------------------
    blocks = []
    for i in positions:
        r = recs[i]
        ks = [key[(i, a)] for a in r["acts"] if (i, a) in key]
        if len(ks) < 3:
            continue
        idxs = [k for k, _ in ks]
        M = len(ks[0][1])
        half = M // 2
        blocks.append(dict(pos=i, rows=np.array(idxs),
                           acts=[a for a in r["acts"] if (i, a) in key],
                           vals=[v for _, v in ks], M=M, half=half,
                           hand=r["hand_act"]))
    print(f"usable positions {len(blocks)}")

    # ---- cross-validated linear fit ------------------------------------------
    import stage1 as _S1
    rng = random.Random(args.seed)
    split_rng = random.Random(args.seed + 1)
    order = list(range(len(blocks)))
    rng.shuffle(order)
    folds = [order[i::args.folds] for i in range(args.folds)]

    reg_hand, reg_fit, reg_oracle = [], [], []
    rho_hand, rho_fit = [], []
    coefs = []

    for fi in range(args.folds):
        test = set(folds[fi])
        train = [b for j, b in enumerate(blocks) if j not in test]
        # design matrix: within-position centred features -> within-position
        # centred target. Centring is what makes this a RANKING fit rather than a
        # "guess the virus count" fit.
        X, y = [], []
        for b in train:
            ft = T[b["rows"]]
            tv = np.array([st.mean(v) for v in b["vals"]])
            keep = WIN[b["rows"]] == 0        # terminal wins carry a sentinel leaf
            if keep.sum() < 3:
                continue
            ft = ft[keep]
            tv = tv[keep]
            X.append(ft - ft.mean(axis=0))
            y.append(tv - tv.mean())
        X = np.vstack(X)
        y = np.concatenate(y)
        sd = X.std(axis=0)
        sd[sd == 0] = 1.0
        Xs = X / sd
        lam = args.ridge
        beta = np.linalg.solve(Xs.T @ Xs + lam * np.eye(Xs.shape[1]), Xs.T @ y)
        coefs.append(beta / sd)

        # Realise the fitted coefficients as ACTUAL EVAL WEIGHTS and put them back
        # inside the SAME depth-3 search. Scoring the fit as a depth-1 linear policy
        # instead would confound two changes at once (depth AND eval) and would
        # answer a question nobody asked. Only the 11 terms _combine_terms actually
        # multiplies are refittable; T_NVIR has no weight slot in the shipped eval
        # (virus count reaches the search through the immediate reward and the win
        # bonus, not the leaf), so it is excluded rather than silently invented.
        bfull = beta / sd
        wfit = _weights_from_beta(bfull, T, args)

        for j in folds[fi]:
            b = blocks[j]
            acts = b["acts"]
            M, half = b["M"], b["half"]
            vA = [st.mean(v[:half]) for v in b["vals"]]
            vB = [st.mean(v[half:]) for v in b["vals"]]
            vAll = [st.mean(v) for v in b["vals"]]
            if b["hand"] not in acts:
                continue
            ih = acts.index(b["hand"])

            # Split-sample oracle on the SAME ruler stage1.py now uses: averaged
            # over many random selection/evaluation partitions rather than one
            # fixed half/half, which on this data moved the estimate by >2 pills
            # purely through split luck. H_linear and H_total must be measured the
            # same way or their difference is meaningless.
            vd = {a: b["vals"][k] for k, a in enumerate(acts)}
            reg_oracle.append(_S1._split_regret(vd, acts, b["hand"],
                                                 split_rng, args.splits))

            # depth-3 search with the REFIT leaf. Its argmax is restricted to the
            # LABELLED actions -- only those have a value to score against, and the
            # champion's own pick is always among them, so the comparison is fair
            # rather than merely convenient.
            rv = _d3_values(b["pos"], wfit, corpus, champ)
            imodel = max(range(len(acts)), key=lambda k: rv[acts[k]])
            reg_fit.append(vAll[imodel] - vAll[ih])
            reg_hand.append(0.0)

            hv = [recs[b["pos"]]["hand_val"][str(a)] for a in acts]
            rho_hand.append(_spearman(hv, vAll))
            rho_fit.append(_spearman([rv[a] for a in acts], vAll))

    def line(tag, xs, unit="pills"):
        if not xs:
            print(f"{tag:40s} (no data)")
            return
        lo, hi = boot_ci(xs)
        print(f"{tag:40s} {st.mean(xs):+8.3f}  [{lo:+.3f},{hi:+.3f}]  n={len(xs)} {unit}")

    print()
    print("=" * 78)
    print("HEADROOM SPLIT: reweighting existing features vs needing new ones")
    print("=" * 78)
    line("  oracle gain over champion (split)", reg_oracle)
    line("  BEST-LINEAR-REFIT gain over champion", reg_fit)
    print("    ^ refit is cross-validated BY POSITION: it never saw the rollouts of")
    print("      the position it is scored on. It is the ceiling of 'just reweight")
    print("      the existing 11 terms'.")
    print()
    line("  within-pos rho: champion eval", [x for x in rho_hand if x == x], "rho")
    line("  within-pos rho: refit linear", [x for x in rho_fit if x == x], "rho")

    C = np.mean(np.stack(coefs), axis=0)
    Cs = np.std(np.stack(coefs), axis=0)
    print()
    print("  fitted coefficients (mean +- sd over folds), and the shipped weight")
    print("  with its combine sign, for comparison:")
    wship = champ_weights()
    for i, nm in enumerate(TERM_NAMES):
        shipped = ("%+8.1f" % (COMBINE_SIGN[i] * wship[i])) if WEIGHT_IDX[i] else "     n/a"
        print(f"    {nm:9s} fit {C[i]:+10.4f} +- {Cs[i]:7.4f}   shipped {shipped}")
    print("    ^ sign FLIPS between fit and shipped are the interesting rows: a term")
    print("      the eval prices backwards relative to measured value.")
    return 0


def champ_weights():
    import fast_rtl_x as FX
    w, fl = FX.variant("winner")
    idx = [FX.R_MAXH, FX.R_HOLES, FX.R_TOPRISK, FX.R_SPAWN, FX.R_SETUP,
           FX.R_MATCHED, FX.R_BURIED, FX.R_RDYEXT, FX.R_VRDY, FX.R_CROSS,
           FX.R_POLL]
    return [float(w[i]) for i in idx] + [0.0]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract")
    e.add_argument("--labels", default="out/labels_main.jsonl")
    e.add_argument("--corpus", default="out/corpus.npz")
    e.add_argument("--out", default="out/feats.npz")
    e.set_defaults(fn=cmd_extract)

    g = sub.add_parser("fit")
    g.add_argument("--feats", default="out/feats.npz")
    g.add_argument("--labels", default="out/labels_main.jsonl")
    g.add_argument("--folds", type=int, default=5)
    g.add_argument("--ridge", type=float, default=1.0)
    g.add_argument("--seed", type=int, default=11)
    g.add_argument("--corpus", default="out/corpus.npz")
    g.add_argument("--splits", type=int, default=100,
                   help="random selection/evaluation partitions averaged per position")
    g.add_argument("--real", action="store_true",
                   help="use terms of the REAL post-cascade board instead of the "
                        "board the search believes it reaches")
    g.set_defaults(fn=cmd_fit)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
