"""eval_h15.py — the H15 registered evaluation (REGISTRATION v2, approved).

Stages:
  sheet    — killed mutants: m-ident (A-vs-A zero discordance), m-dose0
             (H15@wc=wa=0 vs A byte-identical traces), m-swap (scorer
             negation), pressure-live counters.
  primary  — L20 lulu home-regime paired A/B, even seeds 34000..35198
             (600 pairs), resumable per-pair segments.
  guard    — L11 clean non-inferiority, even seeds 36000..37998 (1000 pairs).
  analyze  — interim/final readout: paired d, CI, McNemar; futility at
             200/400; guard trip rule.  NEVER prints efficacy before n=600.

Arms: A = certified H12 (sealed values); B = H15 (refit_candidate, config
47aa04e722ef).  CRN paired seeds; injection keyed (seed, pills_placed).
"""
import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np

PRIMARY_SEEDS = list(range(34000, 35200, 2))      # 600
GUARD_SEEDS = list(range(36000, 38000, 2))        # 1000
OUT = os.path.join(HERE, "out", "h15")
FUTILITY_NS = (200, 400)
FINAL_N = 600


# ------------------------------------------------------------- game loops
def play_l20(seed, arm, wc=None, wa=None):
    """One full L20 lulu game.  arm in {'A','B'}.  Returns dict."""
    import labelcore as LC
    import oracle_arm as OA
    import refit_candidate as RC
    C, bmodel = LC.init_rig()                     # level 20 lulu
    env = OA.make_env(seed, 20, max_pills=400)
    trace = []
    res = "stall"
    ninj = {"n": 0}
    import bursty_model as BM
    real = BM.inject_bursty_garbage

    def counting(board, model, s, pills, cs):
        ninj["n"] += 1
        return real(board, model, s, pills, cs)

    BM.inject_bursty_garbage = counting
    try:
        for _ply in range(400):
            if env.board.virus_count() == 0:
                res = "clear"
                break
            vals = LC.compute_vals(env, C["w"], C["fl"], C["wt"], C["ws"])
            if arm == "B":
                import root_search as RS
                from fb import FB
                fb = FB.from_board(env.board)
                col, vir = RS.board_flat_from_fb(fb)
                kw = {}
                if wc is not None:
                    kw = {"wc": wc, "wa": wa}
                vals = RC.champ_values_refit(
                    col, vir, int(env.cur.a), int(env.cur.b),
                    int(env.nxt.a), int(env.nxt.b),
                    C["w"], C["fl"], C["wt"], C["ws"], **kw)
            a = OA._champ_action(vals, OA.CHAMP_ORDER)
            if a is None:
                res = "topout"
                break
            trace.append(int(a))
            r, _v = OA._advance(env, a, C, seed, bmodel)
            if r is not None:
                res = r
                break
    finally:
        BM.inject_bursty_garbage = real
    return {"seed": seed, "arm": arm, "res": res, "fail": res != "clear",
            "pills": int(env.pills_placed), "vir": int(env.board.virus_count()),
            "inj": ninj["n"], "trace": trace}


def play_l11_clean(seed, arm, wc=None, wa=None):
    """One clean L11 game, no injection (guard / stage-A screen)."""
    import oracle_arm as OA
    import refit_candidate as RC
    import labelcore as LC
    C, _bm = OA.init_rig(model="lulu", level=11, wt=0, ws=20)
    C = dict(C)
    env = OA.make_env(seed, 11, max_pills=300)
    res = "stall"
    for _ply in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break
        vals = LC.compute_vals(env, C["w"], C["fl"], C["wt"], C["ws"])
        if arm == "B":
            import root_search as RS
            from fb import FB
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            kw = {} if wc is None else {"wc": wc, "wa": wa}
            vals = RC.champ_values_refit(
                col, vir, int(env.cur.a), int(env.cur.b),
                int(env.nxt.a), int(env.nxt.b),
                C["w"], C["fl"], C["wt"], C["ws"], **kw)
        a = OA._champ_action(vals, OA.CHAMP_ORDER)
        if a is None:
            res = "topout"
            break
        _obs, _r, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            res = "stall"
            break
    return {"seed": seed, "arm": arm, "res": res, "fail": res != "clear",
            "pills": int(env.pills_placed)}


# ------------------------------------------------------------- workers
def _b0(seed):
    return play_l20(seed, "B", wc=0, wa=0)


def _a20(seed):
    return play_l20(seed, "A")


def _pair_l20(seed):
    t0 = time.time()
    a = play_l20(seed, "A")
    b = play_l20(seed, "B")
    return {"seed": seed, "A": a, "B": b,
            "cpu_s": round(time.time() - t0, 1)}


def _pair_guard(seed):
    t0 = time.time()
    a = play_l11_clean(seed, "A")
    b = play_l11_clean(seed, "B")
    return {"seed": seed, "A": a, "B": b,
            "cpu_s": round(time.time() - t0, 1)}


def run_stage(stage, seeds, worker_fn, prefix, workers):
    os.makedirs(OUT, exist_ok=True)
    todo = [s for s in seeds
            if not os.path.exists(os.path.join(OUT, f"{prefix}_{s}.json"))]
    print(f"[h15:{stage}] pairs={len(seeds)} todo={len(todo)} "
          f"workers={workers}", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(worker_fn, s): s for s in todo}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            tmp = os.path.join(OUT, f".{prefix}_{r['seed']}.tmp")
            with open(tmp, "w") as fh:
                json.dump(r, fh)
            os.replace(tmp, os.path.join(OUT, f"{prefix}_{r['seed']}.json"))
            print(f"[h15:{stage}] {i}/{len(todo)} seed={r['seed']} "
                  f"A={r['A']['res']} B={r['B']['res']} "
                  f"cpu_s={r['cpu_s']} wall={time.time()-t0:.0f}s", flush=True)
    done = sum(os.path.exists(os.path.join(OUT, f"{prefix}_{s}.json"))
               for s in seeds)
    print(f"[h15:{stage}] ledger {done}/{len(seeds)}", flush=True)
    print(f"{stage.upper()}_OK" if done == len(seeds)
          else f"{stage.upper()}_INCOMPLETE", flush=True)


# ------------------------------------------------------------- mutant sheet
def sheet(workers):
    os.makedirs(OUT, exist_ok=True)
    ok = True
    seeds = PRIMARY_SEEDS[:20]
    from concurrent.futures import ProcessPoolExecutor

    # m-ident: A vs A — zero discordance, and pressure fired
    with ProcessPoolExecutor(max_workers=workers) as ex:
        r1 = list(ex.map(_a20, seeds))
        r2 = list(ex.map(_a20, seeds))
    disc = sum(x["fail"] != y["fail"] for x, y in zip(r1, r2))
    tr_eq = all(x["trace"] == y["trace"] for x, y in zip(r1, r2))
    inj = sum(x["inj"] for x in r1)
    ok &= disc == 0 and tr_eq
    print(f"[sheet] m-ident: discordance={disc}/20 traces_equal={tr_eq} "
          f"{'PASS' if disc == 0 and tr_eq else 'FAIL'}", flush=True)
    ok &= inj > 0
    print(f"[sheet] pressure-live: injections={inj} "
          f"{'PASS' if inj > 0 else 'FAIL'}", flush=True)

    # m-dose0: B at zero dose vs A — byte-identical traces
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rb = list(ex.map(_b0, seeds))
    same = all(x["trace"] == y["trace"] and x["res"] == y["res"]
               for x, y in zip(r1, rb))
    ok &= same
    print(f"[sheet] m-dose0: byte-identical traces 20/20: "
          f"{'PASS' if same else 'FAIL'}", flush=True)

    # m-swap: scorer negation on a synthetic ledger
    fake = [{"A": {"fail": True}, "B": {"fail": False}} for _ in range(7)] + \
           [{"A": {"fail": False}, "B": {"fail": True}} for _ in range(3)] + \
           [{"A": {"fail": False}, "B": {"fail": False}} for _ in range(10)]
    d1 = score_pairs(fake)["d"]
    sw = [{"A": p["B"], "B": p["A"]} for p in fake]
    d2 = score_pairs(sw)["d"]
    ok &= abs(d1 + d2) < 1e-12 and d1 != 0
    print(f"[sheet] m-swap: d={d1:+.4f} swapped={d2:+.4f} "
          f"{'PASS' if abs(d1 + d2) < 1e-12 and d1 != 0 else 'FAIL'}",
          flush=True)
    print("SHEET_OK" if ok else "SHEET_FAIL", flush=True)
    return ok


# ------------------------------------------------------------- scoring
def score_pairs(pairs):
    n = len(pairs)
    fa = np.array([p["A"]["fail"] for p in pairs])
    fb = np.array([p["B"]["fail"] for p in pairs])
    d = float(fb.mean() - fa.mean())
    b01 = int(((~fa) & fb).sum())      # B fails where A cleared (bad)
    b10 = int((fa & (~fb)).sum())      # B clears where A failed (good)
    diffs = fb.astype(int) - fa.astype(int)
    rng = np.random.default_rng(146)
    boots = np.array([diffs[rng.integers(0, n, n)].mean()
                      for _ in range(10000)]) if n else np.array([0.0])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    from scipy.stats import binomtest
    p = (binomtest(b10, b01 + b10, 0.5, alternative="greater").pvalue
         if (b01 + b10) else 1.0)
    return {"n": n, "d": d, "ci": (float(lo), float(hi)),
            "b_good": b10, "b_bad": b01, "mcnemar_p_onesided": float(p),
            "failA": float(fa.mean()), "failB": float(fb.mean())}


def load_pairs(prefix, seeds):
    out = []
    for s in seeds:
        p = os.path.join(OUT, f"{prefix}_{s}.json")
        if os.path.exists(p):
            out.append(json.load(open(p)))
    return out


def analyze(interim=None):
    pairs = load_pairs("pair", PRIMARY_SEEDS)
    pairs.sort(key=lambda p: p["seed"])
    if interim:
        if len(pairs) < interim:
            print(f"[analyze] only {len(pairs)} pairs, interim {interim} "
                  f"not reached", flush=True)
            return
        sc = score_pairs(pairs[:interim])
        fut = sc["ci"][0] > -0.01
        print(f"INTERIM n={interim}: d={sc['d']:+.4f} "
              f"CI[{sc['ci'][0]:+.4f},{sc['ci'][1]:+.4f}] "
              f"good={sc['b_good']} bad={sc['b_bad']} "
              f"futility={'STOP' if fut else 'CONTINUE'}", flush=True)
        return
    if len(pairs) < FINAL_N:
        print(f"[analyze] {len(pairs)}/{FINAL_N} — no efficacy readout "
              f"before the registered n", flush=True)
        return
    sc = score_pairs(pairs[:FINAL_N])
    go = sc["mcnemar_p_onesided"] < 0.05 and sc["d"] < 0
    print(f"PRIMARY n={sc['n']}: failA={sc['failA']:.4f} "
          f"failB={sc['failB']:.4f} d={sc['d']:+.4f} "
          f"CI[{sc['ci'][0]:+.4f},{sc['ci'][1]:+.4f}] "
          f"good={sc['b_good']} bad={sc['b_bad']} "
          f"p={sc['mcnemar_p_onesided']:.4g} -> "
          f"{'GO' if go else 'NO_GO'}", flush=True)
    g = load_pairs("guard", GUARD_SEEDS)
    if len(g) == len(GUARD_SEEDS):
        gs = score_pairs(g)
        from scipy.stats import norm
        se = np.std([p["B"]["fail"] - p["A"]["fail"] for p in g]) / \
            np.sqrt(len(g))
        lb1 = gs["d"] - 1.645 * se
        trip = gs["d"] > 0.010 or lb1 > 0
        print(f"GUARD n={gs['n']}: failA={gs['failA']:.4f} "
              f"failB={gs['failB']:.4f} d={gs['d']:+.4f} "
              f"onesided95LB={lb1:+.4f} -> "
              f"{'TRIP (NO-PROMOTION)' if trip else 'PASS'}", flush=True)
    else:
        print(f"GUARD incomplete: {len(g)}/{len(GUARD_SEEDS)}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("sheet", "primary", "guard", "analyze"))
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--interim", type=int, default=None)
    args = ap.parse_args()
    if args.stage == "sheet":
        sys.exit(0 if sheet(args.workers) else 1)
    if args.stage == "primary":
        run_stage("primary", PRIMARY_SEEDS, _pair_l20, "pair", args.workers)
    elif args.stage == "guard":
        run_stage("guard", GUARD_SEEDS, _pair_guard, "guard", args.workers)
    else:
        analyze(args.interim)


if __name__ == "__main__":
    main()
