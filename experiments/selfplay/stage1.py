#!/usr/bin/env python3
"""STAGE 1 -- EVAL HEADROOM AT DEPTH 3.  The kill-gate for the whole program.

THE QUESTION
------------
How much better could ANY leaf evaluator make the shipped depth-3 search? If the
hand eval already tracks true value closely enough that a PERFECT leaf would pick
the same move almost always, then the eval is not the lever and no amount of
self-play or NNUE machinery will help. That is a cheap negative worth having.

WHY THIS SHAPE OF MEASUREMENT (and not CFR / regret matching)
------------------------------------------------------------
Dr. Mario VS is a two-player zero-sum STOCHASTIC PERFECT-INFORMATION game: both
bottles are on screen, and the only thing neither player knows is the FUTURE pill
draw. There is no private state, so there are no information sets to abstract and
no counterfactual regret to minimise -- CFR exists to handle hidden information
this game does not have. The right family is AlphaZero-shaped: search + a learned
value, with the pill draw as a CHANCE node. Stage 1 measures the ceiling of the
"learned value" half of that before any of it gets built.

WHAT "PERFECT LEAF" MEANS HERE
------------------------------
If the leaf evaluator were exact, depth-3 search would be pointless -- you would
just take argmax over the 32 root actions of the true value of the resulting
board (the next pill is already known, so a ply-1 board's value is well defined).
So the oracle policy is:

    a* = argmax_a  V(s1(a))

and the headroom is the gap between the champion's move and a*.

V is estimated by MONTE-CARLO ROLLOUT under the champion policy itself, i.e. this
measures V^pi, not V*. That is a deliberate, statable choice:
  * It is UNBIASED with respect to eval error -- unlike labelling with a deeper
    search, which would just inherit the hand eval's own blind spots at ITS leaves
    and could report "the eval agrees with itself".
  * argmax_a V^pi(s1(a)) is exactly ONE step of policy iteration -- the AlphaZero
    improvement operator with a perfect value net. Its measured gain is therefore a
    LOWER bound on the fully-converged gain (a better eval yields a better policy,
    which raises V^pi in turn), and an honest estimate of what the first iteration
    buys. It is not an upper bound on V*, and this file never claims it is.

THE WINNER'S-CURSE TRAP (why there are two splits)
--------------------------------------------------
V-hat over ~30 actions is noisy. Taking argmax of noisy estimates and then reading
off that same estimate reports the noise as if it were headroom -- with M=8
rollouts and a per-action sigma of tens of pills, a pure-noise position would show
a large fake "oracle gain". So each action's rollouts are SPLIT:

    split A (select)   ->  a*_A = argmax_a V-hat_A(a)
    split B (evaluate) ->  gain = V-hat_B(a*_A) - V-hat_B(a_hand)

Selection and evaluation use disjoint rollouts, so `gain` is unbiased for the value
of a NOISY oracle -- which understates a perfect oracle. The same-split quantity
max_a V-hat_B(a) - V-hat_B(a_hand) overstates it. Reporting BOTH brackets the truth
instead of picking whichever number flatters the program. A control arm
(`--shuffle-control`) re-runs the selection on shuffled action labels: whatever
"gain" that produces is pure selection noise and is the floor any real effect must
clear.

COMMON RANDOM NUMBERS: rollout m uses the SAME pill stream for every action at a
position, so between-action differences are paired and most of the variance cancels.

Usage:
  stage1.py corpus  --games 300 --out out/corpus.npz
  stage1.py label   --corpus out/corpus.npz --positions 250 --rollouts 8 \
                    --workers 4 --out out/labels.jsonl
  stage1.py analyze --labels out/labels.jsonl
"""
from __future__ import annotations

import os
import sys
import json
import time
import math
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np

ROLLOUT_CAP = 200          # censoring horizon for a rollout, in pills
VALUE_CENSOR = float(ROLLOUT_CAP)
TOPK_ACTS = 8              # hand-eval contenders labelled per position
RAND_ACTS = 2              # random non-contenders -- the out-of-top-K control


# =============================================================== corpus building
def _corpus_worker(seed):
    """Play one champion game, return every position along its trajectory."""
    import sp_engine as E
    champ = _W["champ"]
    env = E.new_env(level=E.LEVEL, seed=seed, cap=300)
    E.attach_stream(env, seed)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    out = []
    for ply in range(300):
        if env.board.virus_count() == 0:
            break
        col, vir, link = E.board_planes(env.board)
        a = champ.choose(col, vir, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
        if a < 0:
            break
        out.append(dict(seed=seed, ply=ply, col=col.copy(), vir=vir.copy(),
                        link=link.copy(), ca=int(env.cur.a), cb=int(env.cur.b),
                        na=int(env.nxt.a), nb=int(env.nxt.b),
                        nvir=int(env.board.virus_count()), hand_act=int(a)))
        _o, _r, term, trunc, _i = env.step(int(a))
        if term or trunc:
            break
    return out


_W = {}


def _init_worker():
    import sp_engine as E
    _W["champ"] = E.Champion()


def cmd_corpus(args):
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = [ex.submit(_corpus_worker, s) for s in range(args.games)]
        for i, f in enumerate(as_completed(futs)):
            rows.extend(f.result())
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{args.games} games, {len(rows)} positions, "
                      f"{time.time()-t0:.0f}s", flush=True)
    print(f"corpus: {len(rows)} positions from {args.games} games "
          f"in {time.time()-t0:.0f}s", flush=True)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    np.savez_compressed(
        args.out,
        col=np.stack([r["col"] for r in rows]),
        vir=np.stack([r["vir"] for r in rows]),
        link=np.stack([r["link"] for r in rows]),
        pills=np.array([[r["ca"], r["cb"], r["na"], r["nb"]] for r in rows], dtype=np.int8),
        meta=np.array([[r["seed"], r["ply"], r["nvir"], r["hand_act"]] for r in rows],
                      dtype=np.int32))
    print(f"wrote {args.out}", flush=True)


# ==================================================================== labelling
def _label_worker(job):
    """Label one corpus position: every legal root action, M common-stream rollouts."""
    import sp_engine as E
    from fast_sim_x import NCELL, _expand_core, _virus_count
    import fast_rtl_x as FX

    champ = _W["champ"]
    env = _W.setdefault("env", E.new_env(level=E.LEVEL, seed=0, cap=ROLLOUT_CAP))
    idx, pos, M, stream_base = job
    col = np.asarray(pos["col"], dtype=np.int8)
    vir = np.asarray(pos["vir"], dtype=np.int8)
    link = np.asarray(pos["link"], dtype=np.int8)
    ca, cb, na, nb = pos["ca"], pos["cb"], pos["na"], pos["nb"]

    hand_act, val, ok = champ.values(col, vir, ca, cb, na, nb)
    val = val.copy()
    ok = ok.copy()

    # hand LEAF eval on the board the SEARCH believes results from each action
    # (_expand_core's cap-1 targeted resolve), kept separate from the leaf eval of
    # the board the REAL sim produces (full cascade) so the dynamics-approximation
    # cost can be reported apart from the eval's own error.
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    leaf_search = {}
    for a in range(32):
        if ok[a] != 1:
            continue
        var, cc = a // 8, a % 8
        okk, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
        if okk == 0:
            continue
        leaf_search[a] = int(FX._leafv_ship(c1, v1, champ.w, champ.fl))

    # ACTION SUBSET. A full-horizon rollout costs ~13 s, so labelling all ~30 legal
    # actions at every position is not affordable. We label the hand eval's TOP-K
    # (the only actions that could plausibly be the champion's move) plus R actions
    # drawn at random from the rest. The random draw is not padding: it is the
    # control that detects the failure mode this subset could otherwise hide -- an
    # oracle whose best move the hand eval ranks far down. If out-of-top-K actions
    # never win among the sampled ones, restricting to contenders is safe; if they
    # do, the restriction itself is a finding.
    legal = sorted(leaf_search.keys())
    topk = sorted(legal, key=lambda a: -val[a])[:TOPK_ACTS]
    rest = [a for a in legal if a not in set(topk)]
    rng = random.Random(stream_base)
    extra = rng.sample(rest, min(RAND_ACTS, len(rest)))
    acts = sorted(set(topk) | set(extra))
    rec_topk = sorted(topk)
    rec = dict(idx=idx, seed=int(pos["seed"]), ply=int(pos["ply"]),
               nvir=int(pos["nvir"]), hand_act=int(hand_act), acts=acts,
               n_legal=len(legal), topk=rec_topk, extra=sorted(extra),
               hand_val={str(a): float(val[a]) for a in acts},
               leaf_search={str(a): leaf_search[a] for a in acts},
               leaf_real={}, dyn_diff={}, pills={}, outcome={}, trace={})
    p = dict(col=col, vir=vir, link=link, ca=ca, cb=cb, na=na, nb=nb)

    # One isolated step per action to capture the board the REAL sim produces
    # (full cascade resolve) as opposed to _expand_core's cap-1 approximation.
    # Comparing leaf_real against leaf_search separates the eval's own error from
    # the search's dynamics-model error -- two different defects that a single
    # end-to-end correlation would silently blend.
    for a in acts:
        E.attach_stream(env, stream_base)
        E.set_board(env.board, col, vir, link)
        E.set_pills(env, ca, cb, na, nb)
        env.pills_placed = 0
        env._start_viruses = int(env.board.virus_count())
        _o, _r, _t, _tr, sinfo = env.step(int(a))
        if sinfo.get("illegal"):
            # champ_root's legality (_expand_core/_resting) disagreed with the real
            # sim's (board.place_pill). Never observed, but a silent disagreement
            # here would poison every label for this action, so it is recorded
            # rather than swallowed.
            rec.setdefault("illegal", []).append(int(a))
        rc, rv, _rl = E.board_planes(env.board)
        rec["leaf_real"][str(a)] = int(FX._leafv_ship(
            np.ascontiguousarray(rc), np.ascontiguousarray(rv), champ.w, champ.fl))
        var, cc = a // 8, a % 8
        _ok, _nv, _cl = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
        rec["dyn_diff"][str(a)] = int(not (np.array_equal(c1, rc)
                                           and np.array_equal(v1, rv)))

    for a in acts:
        pl, oc, tr = [], [], []
        for m in range(M):
            t = []
            out, used = E.rollout_value(p, a, stream_base + m, champ,
                                        cap=ROLLOUT_CAP, env=env, trace=t)
            pl.append(int(used))
            oc.append(out)
            tr.append(t)
        rec["pills"][str(a)] = pl
        rec["outcome"][str(a)] = oc
        rec["trace"][str(a)] = tr
    return rec


def cmd_label(args):
    d = np.load(args.corpus)
    col, vir, link, pills, meta = d["col"], d["vir"], d["link"], d["pills"], d["meta"]
    n = len(col)
    print(f"corpus: {n} positions", flush=True)

    rng = random.Random(args.sample_seed)
    idxs = list(range(n))
    rng.shuffle(idxs)
    idxs = sorted(idxs[:args.positions])

    jobs = []
    for k, i in enumerate(idxs):
        pos = dict(col=col[i], vir=vir[i], link=link[i],
                   ca=int(pills[i][0]), cb=int(pills[i][1]),
                   na=int(pills[i][2]), nb=int(pills[i][3]),
                   seed=int(meta[i][0]), ply=int(meta[i][1]), nvir=int(meta[i][2]))
        jobs.append((int(i), pos, args.rollouts, 1000000 + k * 977))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    t0 = time.time()
    done = 0
    with open(args.out, "w") as fh, \
         ProcessPoolExecutor(max_workers=args.workers,
                             initializer=_init_worker) as ex:
        futs = [ex.submit(_label_worker, j) for j in jobs]
        for f in as_completed(futs):
            fh.write(json.dumps(f.result()) + "\n")
            fh.flush()
            done += 1
            if done % 5 == 0 or done == len(jobs):
                el = time.time() - t0
                print(f"  {done}/{len(jobs)} positions  {el:.0f}s  "
                      f"eta {el/done*(len(jobs)-done):.0f}s", flush=True)
    print(f"wrote {args.out}", flush=True)


# ===================================================================== analysis
def _value(pills_list, outcomes):
    """Scalar value of a rollout: NEGATIVE pills-to-clear, censored at the cap.

    Higher is better. A rollout that never clears is charged the full horizon --
    the same censoring the project's own 300-pill stall cap applies, so speed and
    reliability collapse into one number without an invented exchange rate."""
    out = []
    for p, o in zip(pills_list, outcomes):
        out.append(-float(p) if o == "clear" else -VALUE_CENSOR)
    return out


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


def _pearson(x, y):
    n = len(x)
    if n < 3:
        return float("nan")
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy) if dx > 0 and dy > 0 else float("nan")


def boot_ci(xs, stat=None, n=10000, seed=12345):
    stat = stat or st.mean
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def _v_full(rec, a):
    """Per-rollout FULL-horizon value: negative pills-to-clear, censored at the cap.

    Higher is better. A rollout that never clears is charged the whole horizon --
    the same censoring the project's own 300-pill stall cap applies, so speed and
    reliability collapse into one number with no invented exchange rate."""
    return [(-float(p) if o == "clear" else -VALUE_CENSOR)
            for p, o in zip(rec["pills"][str(a)], rec["outcome"][str(a)])]


def _v_trunc(rec, a, T):
    """Per-rollout TRUNCATED value: negative viruses remaining after T pills.

    Uses no hand eval and no invented constants -- it is simply the objective
    measured over a shorter horizon. Cheap because a T-pill rollout costs T/|game|
    of a full one; whether it RANKS actions the same way is measured, not assumed
    (see the calibration block in cmd_analyze)."""
    out = []
    for tr in rec["trace"][str(a)]:
        if not tr:
            out.append(-float(rec["nvir"]))
        else:
            out.append(-float(tr[min(T, len(tr)) - 1]))
    return out


def cmd_analyze(args):
    recs = [json.loads(l) for l in open(args.labels)]
    print(f"positions: {len(recs)}")
    rng = random.Random(args.shuffle_seed)

    glob_leaf_s, glob_leaf_r, glob_v = [], [], []
    within_hand, within_leaf = [], []
    agree, agree_split = [], []
    regret_split, regret_same, regret_shuf = [], [], []
    spread, se_per_action, nact, nlegal = [], [], [], []
    out_topk, dyn_diff, illegal_n = [], [], 0
    leaf_sr = []
    phase = {}
    trunc_T = [10, 15, 20, 25, 30, 40, 60]
    trunc_rho = {T: [] for T in trunc_T}

    for r in recs:
        acts = r["acts"]
        illegal_n += len(r.get("illegal", []))
        if len(acts) < 3:
            continue
        vals = {a: _v_full(r, a) for a in acts}
        M = len(next(iter(vals.values())))
        if M < 2:
            continue
        half = M // 2
        vA = {a: st.mean(vals[a][:half]) for a in acts}
        vB = {a: st.mean(vals[a][half:]) for a in acts}
        vAll = {a: st.mean(vals[a]) for a in acts}

        hand = {a: r["hand_val"][str(a)] for a in acts}
        leaf = {a: r["leaf_search"][str(a)] for a in acts}
        a_hand = r["hand_act"]
        if a_hand not in vAll:
            continue

        nact.append(len(acts))
        nlegal.append(r.get("n_legal", len(acts)))
        glob_leaf_s.extend(leaf[a] for a in acts)
        glob_leaf_r.extend(r["leaf_real"][str(a)] for a in acts)
        glob_v.extend(vAll[a] for a in acts)
        dyn_diff.extend(r["dyn_diff"][str(a)] for a in acts)

        within_hand.append(_spearman([hand[a] for a in acts], [vAll[a] for a in acts]))
        within_leaf.append(_spearman([leaf[a] for a in acts], [vAll[a] for a in acts]))
        leaf_sr.append(_spearman([leaf[a] for a in acts],
                                 [r["leaf_real"][str(a)] for a in acts]))

        a_best_all = max(acts, key=lambda a: vAll[a])
        agree.append(1.0 if a_best_all == a_hand else 0.0)
        out_topk.append(1.0 if a_best_all in set(r.get("extra", [])) else 0.0)

        # split-sample: select on A, evaluate on B, and symmetrically B -> A
        a_star_A = max(acts, key=lambda a: vA[a])
        a_star_B = max(acts, key=lambda a: vB[a])
        regret_split.append(((vB[a_star_A] - vB[a_hand])
                             + (vA[a_star_B] - vA[a_hand])) / 2.0)
        agree_split.append(1.0 if a_star_A == a_hand else 0.0)
        regret_same.append(vAll[a_best_all] - vAll[a_hand])

        # SHUFFLE CONTROL: keep the selection machinery, destroy the link between
        # rollouts and the actions that produced them. Any "gain" here is selection
        # noise, and is the floor the split-sample number must clear.
        flat = [x for a in acts for x in vals[a]]
        rng.shuffle(flat)
        sh = {a: flat[i * M:(i + 1) * M] for i, a in enumerate(acts)}
        shA = {a: st.mean(sh[a][:half]) for a in acts}
        shB = {a: st.mean(sh[a][half:]) for a in acts}
        s_star = max(acts, key=lambda a: shA[a])
        regret_shuf.append(shB[s_star] - shB[a_hand])

        spread.append(st.pstdev([vAll[a] for a in acts]))
        sds = [st.pstdev(vals[a]) for a in acts if len(set(vals[a])) > 1]
        if sds:
            se_per_action.append(st.mean(sds) / math.sqrt(M))

        for T in trunc_T:
            vt = {a: st.mean(_v_trunc(r, a, T)) for a in acts}
            rho = _spearman([vt[a] for a in acts], [vAll[a] for a in acts])
            if rho == rho:
                trunc_rho[T].append(rho)

        ph = ("early" if r["nvir"] >= 3 * args.v0 // 4 else
              "mid" if r["nvir"] >= args.v0 // 4 else "late")
        phase.setdefault(ph, []).append(regret_split[-1])

    def line(tag, xs, unit=""):
        if not xs:
            print(f"{tag:36s}  (no data)")
            return None
        lo, hi = boot_ci(xs)
        print(f"{tag:36s}  {st.mean(xs):+8.3f}  [{lo:+.3f},{hi:+.3f}]  n={len(xs)} {unit}")
        return st.mean(xs), lo, hi

    print()
    print("=" * 78)
    print("0. SANITY")
    print("=" * 78)
    print(f"  legality disagreements (want 0)      : {illegal_n}")
    print(f"  mean legal actions / position        : {st.mean(nlegal):.1f}")
    print(f"  mean LABELLED actions / position     : {st.mean(nact):.1f}")
    print(f"  search-vs-real dynamics mismatch     : {st.mean(dyn_diff):.1%} of actions")
    print("    ^ _expand_core's cap-1 targeted resolve vs the sim's full cascade.")
    line("  rho(leaf_search, leaf_real)", [x for x in leaf_sr if x == x], "rho")

    print()
    print("=" * 78)
    print("A. LEAF FIDELITY -- does the hand leaf eval track true value?")
    print("=" * 78)
    print(f"  labelled ply-1 boards                : {len(glob_v)}")
    sp_g = _spearman(glob_leaf_s, glob_v)
    pe_g = _pearson(glob_leaf_s, glob_v)
    print(f"  GLOBAL Spearman(leaf, V)             : {sp_g:+.4f}")
    print(f"  GLOBAL Pearson r / R^2               : {pe_g:+.4f} / {pe_g**2:.4f}")
    print("    ^ flattering by construction: dominated by 'how many viruses are")
    print("      left', which both sides trivially know. NOT what decides moves.")
    wh = [x for x in within_hand if x == x]
    wl = [x for x in within_leaf if x == x]
    r_wh = line("  WITHIN-position rho(root val, V)", wh, "rho")
    r_wl = line("  WITHIN-position rho(leaf, V)", wl, "rho")
    print("    ^ THE number that matters: discrimination among the successors of")
    print("      ONE position is what actually picks the move.")

    print()
    print("=" * 78)
    print("B. DECISION IMPACT -- would a perfect leaf move differently?")
    print("=" * 78)
    line("  P(hand == argmax V) same-split", agree)
    line("  P(hand == argmax V) split-sample", agree_split)
    line("  P(best is OUTSIDE hand top-K)", out_topk)
    print("    ^ control on the contender restriction: if a randomly drawn")
    print("      non-contender wins this often, top-K was hiding real options.")
    print()
    r_lo = line("  REGRET split-sample (LOWER)", regret_split, "pills")
    r_ct = line("  REGRET shuffle CONTROL", regret_shuf, "pills")
    r_hi = line("  REGRET same-sample (UPPER)", regret_same, "pills")
    net = None
    if regret_split and regret_shuf:
        net = [a - b for a, b in zip(regret_split, regret_shuf)]
        r_net = line("  REGRET net of control", net, "pills")
    print("    ^ split-sample is unbiased for a NOISY oracle => understates a")
    print("      perfect one; same-sample is winner's-curse inflated => overstates.")
    print("      The truth is bracketed between them. Net-of-control is the")
    print("      headline: it is what survives after pure selection noise.")
    print()
    line("  spread: sd(V) across actions", spread, "pills")
    line("  MC noise: se per action", se_per_action, "pills")

    print()
    print("=" * 78)
    print("C. BY GAME PHASE (split-sample regret, pills)")
    print("=" * 78)
    for ph in ("early", "mid", "late"):
        if ph in phase:
            line(f"  {ph}", phase[ph], "pills")

    print()
    print("=" * 78)
    print("D. TRUNCATION CALIBRATION -- can a cheap short rollout replace a full one?")
    print("=" * 78)
    print("  within-position rho(V_truncated_at_T, V_full):")
    for T in trunc_T:
        xs = trunc_rho[T]
        if xs:
            lo, hi = boot_ci(xs)
            print(f"    T={T:3d} pills   rho = {st.mean(xs):+.3f}  [{lo:+.3f},{hi:+.3f}]")
    print("    ^ if rho is high at small T, the big run can use short rollouts and")
    print("      cost proportionally less. Measured, not assumed.")

    out = dict(n_positions=len(recs), n_leaf=len(glob_v),
               illegal=illegal_n,
               dyn_mismatch=st.mean(dyn_diff) if dyn_diff else None,
               global_spearman=sp_g, global_pearson=pe_g,
               within_hand=st.mean(wh) if wh else None,
               within_leaf=st.mean(wl) if wl else None,
               agree=st.mean(agree) if agree else None,
               agree_split=st.mean(agree_split) if agree_split else None,
               out_of_topk=st.mean(out_topk) if out_topk else None,
               regret_split=st.mean(regret_split) if regret_split else None,
               regret_shuffle=st.mean(regret_shuf) if regret_shuf else None,
               regret_same=st.mean(regret_same) if regret_same else None,
               regret_net=st.mean(net) if net else None,
               regret_net_ci=boot_ci(net) if net else None,
               spread=st.mean(spread) if spread else None,
               se_per_action=st.mean(se_per_action) if se_per_action else None,
               trunc_rho={T: (st.mean(v) if v else None) for T, v in trunc_rho.items()})
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"\nwrote {args.json_out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("corpus")
    c.add_argument("--games", type=int, default=300)
    c.add_argument("--workers", type=int, default=4)
    c.add_argument("--out", default="out/corpus.npz")
    c.set_defaults(fn=cmd_corpus)

    l = sub.add_parser("label")
    l.add_argument("--corpus", default="out/corpus.npz")
    l.add_argument("--positions", type=int, default=250)
    l.add_argument("--rollouts", type=int, default=8)
    l.add_argument("--workers", type=int, default=4)
    l.add_argument("--sample-seed", type=int, default=20260806)
    l.add_argument("--out", default="out/labels.jsonl")
    l.set_defaults(fn=cmd_label)

    a = sub.add_parser("analyze")
    a.add_argument("--labels", default="out/labels.jsonl")
    # L11 starts at min((11+1)*4, 84) = 48 viruses (faithful_game.place_viruses).
    a.add_argument("--v0", type=int, default=48, help="starting virus count (L11=48)")
    a.add_argument("--shuffle-seed", type=int, default=7)
    a.add_argument("--json-out", default="")
    a.set_defaults(fn=cmd_analyze)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
