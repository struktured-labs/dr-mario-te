"""eval_h15c.py — ROUND-3 STAGE A: game-screened dose selection
(PREREG ROUND-3 REGISTRATION; EXPLORATORY — no inferential claims).

Grid frozen in the registration.  Arm A is dose-independent and played once
per seed; each lambda plays only its B games.  CRN: same seeds across the
whole grid.  Segments identity-keyed and resumable.
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
import eval_h15 as E
import refit_candidate as RC

GRID = [0.0389, 0.0585, 0.0880, 0.1325, 0.1994, 0.3]
CLEAN_SEEDS = list(range(38000, 38040, 2))     # 20
L20_SEEDS = list(range(40000, 40080, 2))       # 40
OUT = os.path.join(HERE, "out", "h15c")


def _task(t):
    kind, seed, lam = t
    t0 = time.time()
    if kind == "A_clean":
        r = E.play_l11_clean(seed, "A")
    elif kind == "A_l20":
        r = E.play_l20(seed, "A")
    elif kind == "B_clean":
        r = E.play_l11_clean(seed, "B", wc=lam * RC.W_GCENTER,
                             wa=lam * RC.W_GATTACK)
    else:
        r = E.play_l20(seed, "B", wc=lam * RC.W_GCENTER,
                       wa=lam * RC.W_GATTACK)
    r.pop("trace", None)
    r["cpu_s"] = round(time.time() - t0, 1)
    r["lam"] = lam
    return kind, seed, lam, r


def seg(kind, seed, lam):
    tag = f"{kind}_{seed}" if lam is None else f"{kind}_{lam:g}_{seed}"
    return os.path.join(OUT, tag + ".json")


def run(workers):
    os.makedirs(OUT, exist_ok=True)
    tasks = [("A_clean", s, None) for s in CLEAN_SEEDS] + \
            [("A_l20", s, None) for s in L20_SEEDS]
    for lam in GRID:
        tasks += [("B_clean", s, lam) for s in CLEAN_SEEDS]
        tasks += [("B_l20", s, lam) for s in L20_SEEDS]
    todo = [t for t in tasks if not os.path.exists(seg(*t))]
    print(f"[h15c:A] tasks={len(tasks)} todo={len(todo)} workers={workers}",
          flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_task, t) for t in todo]
        for i, f in enumerate(as_completed(futs), 1):
            kind, seed, lam, r = f.result()
            tmp = seg(kind, seed, lam) + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(r, fh)
            os.replace(tmp, seg(kind, seed, lam))
            print(f"[h15c:A] {i}/{len(todo)} {kind} lam={lam} seed={seed} "
                  f"res={r['res']} wall={time.time()-t0:.0f}s", flush=True)
    done = sum(os.path.exists(seg(*t)) for t in tasks)
    print(f"[h15c:A] ledger {done}/{len(tasks)}", flush=True)
    print("STAGEA_OK" if done == len(tasks) else "STAGEA_INCOMPLETE",
          flush=True)


def analyze():
    def load(kind, seeds, lam=None):
        out = {}
        for s in seeds:
            p = seg(kind, s, lam)
            if os.path.exists(p):
                out[s] = json.load(open(p))
        return out
    a_clean = load("A_clean", CLEAN_SEEDS)
    a_l20 = load("A_l20", L20_SEEDS)
    print(f"arm A: clean clears {sum(not r['fail'] for r in a_clean.values())}"
          f"/20, L20 fail rate "
          f"{np.mean([r['fail'] for r in a_l20.values()]):.3f}")
    best = None
    for lam in GRID:
        b_clean = load("B_clean", CLEAN_SEEDS, lam)
        b_l20 = load("B_l20", L20_SEEDS, lam)
        clears = sum(not r["fail"] for r in b_clean.values())
        alive = clears >= 18
        d = float(np.mean([b_l20[s]["fail"] for s in L20_SEEDS])
                  - np.mean([a_l20[s]["fail"] for s in L20_SEEDS]))
        print(f"lam={lam:g}: clean B clears {clears}/20 "
              f"{'ALIVE' if alive else 'DEAD'}  pressured d={d:+.3f}")
        if alive and (best is None or d < best[1]):
            best = (lam, d)
    if best and best[1] < 0:
        print(f"STAGEA_SELECT lam={best[0]:g} pressured_d={best[1]:+.3f}")
    else:
        print("STAGEA_NO_QUALIFIER — program rule: the linear-refit door "
              "CLOSES (no lambda passes clean screen with pressured d<0)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("run", "analyze", "bprimary",
                                      "bguard", "analyze_b"))
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()
    if args.stage == "run":
        run(args.workers)
    elif args.stage == "analyze":
        analyze()
    elif args.stage in ("bprimary", "bguard"):
        run_b(args.stage, args.workers)
    else:
        analyze_b()


if __name__ == "__main__":
    main()


# ----------------------------------------------------------------- STAGE B
# (form registered with reserved seeds; LAM_B fills in post-screen — the one
# permitted edit. Runner-level futility: in-process checks at 200/400 on
# ascending-seed prefixes; a STOP halts this run and stops the guard unit.)
LAM_B = None                      # <- filled from STAGEA_SELECT, nothing else
B_PRIMARY_SEEDS = list(range(42000, 43200, 2))   # 600, reserved
B_GUARD_SEEDS = list(range(44000, 46000, 2))     # 1000, reserved
FUTILITY_NS = (200, 400)


def _bpair_l20(seed):
    t0 = time.time()
    a = E.play_l20(seed, "A")
    b = E.play_l20(seed, "B", wc=LAM_B * RC.W_GCENTER,
                   wa=LAM_B * RC.W_GATTACK)
    for r in (a, b):
        r.pop("trace", None)
    return {"seed": seed, "A": a, "B": b, "cpu_s": round(time.time() - t0, 1)}


def _bpair_guard(seed):
    t0 = time.time()
    a = E.play_l11_clean(seed, "A")
    b = E.play_l11_clean(seed, "B", wc=LAM_B * RC.W_GCENTER,
                         wa=LAM_B * RC.W_GATTACK)
    return {"seed": seed, "A": a, "B": b, "cpu_s": round(time.time() - t0, 1)}


def _bseg(prefix, seed):
    return os.path.join(OUT, f"{prefix}_{seed}.json")


def _prefix_pairs(prefix, seeds, n):
    out = []
    for s in seeds:
        p = _bseg(prefix, s)
        if os.path.exists(p):
            out.append(json.load(open(p)))
        else:
            break                      # ascending-seed PREFIX only
        if len(out) == n:
            break
    return out


def run_b(stage, workers):
    assert LAM_B is not None, "fill LAM_B from STAGEA_SELECT first"
    os.makedirs(OUT, exist_ok=True)
    seeds = B_PRIMARY_SEEDS if stage == "bprimary" else B_GUARD_SEEDS
    fn = _bpair_l20 if stage == "bprimary" else _bpair_guard
    prefix = "bpair" if stage == "bprimary" else "bguard"
    todo = [s for s in seeds if not os.path.exists(_bseg(prefix, s))]
    print(f"[h15c:{stage}] lam={LAM_B} pairs={len(seeds)} todo={len(todo)} "
          f"workers={workers}", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0, checked = time.time(), set()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, s): s for s in todo}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            tmp = _bseg(prefix, r["seed"]) + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(r, fh)
            os.replace(tmp, _bseg(prefix, r["seed"]))
            print(f"[h15c:{stage}] {i}/{len(todo)} seed={r['seed']} "
                  f"A={r['A']['res']} B={r['B']['res']} "
                  f"wall={time.time()-t0:.0f}s", flush=True)
            if stage == "bprimary":
                for th in FUTILITY_NS:
                    if th in checked:
                        continue
                    pre = _prefix_pairs(prefix, seeds, th)
                    if len(pre) < th:
                        continue
                    checked.add(th)
                    sc = E.score_pairs(pre)
                    stop = sc["ci"][0] > -0.01
                    print(f"[h15c:INTERIM] n={th} d={sc['d']:+.4f} "
                          f"CI[{sc['ci'][0]:+.4f},{sc['ci'][1]:+.4f}] "
                          f"futility={'STOP' if stop else 'CONTINUE'}",
                          flush=True)
                    if stop:
                        print("FUTILITY_STOP — halting primary and guard",
                              flush=True)
                        os.system("systemctl --user stop drm-h15c-bguard")
                        for f2 in futs:
                            f2.cancel()
                        ex.shutdown(wait=False, cancel_futures=True)
                        return
    done = sum(os.path.exists(_bseg(prefix, s)) for s in seeds)
    print(f"[h15c:{stage}] ledger {done}/{len(seeds)}", flush=True)
    print(f"{stage.upper()}_OK" if done == len(seeds)
          else f"{stage.upper()}_INCOMPLETE", flush=True)


def analyze_b():
    pairs = _prefix_pairs("bpair", B_PRIMARY_SEEDS, 600)
    if len(pairs) < 600:
        print(f"[h15c:analyze_b] {len(pairs)}/600 — either FUTILITY_STOP "
              f"(see log) or incomplete; no efficacy readout", flush=True)
    else:
        sc = E.score_pairs(pairs)
        go = sc["mcnemar_p_onesided"] < 0.05 and sc["d"] < 0
        print(f"BPRIMARY n=600: failA={sc['failA']:.4f} "
              f"failB={sc['failB']:.4f} d={sc['d']:+.4f} "
              f"CI[{sc['ci'][0]:+.4f},{sc['ci'][1]:+.4f}] "
              f"good={sc['b_good']} bad={sc['b_bad']} "
              f"p={sc['mcnemar_p_onesided']:.4g} -> "
              f"{'GO' if go else 'NO_GO'}", flush=True)
    g = [json.load(open(_bseg("bguard", s))) for s in B_GUARD_SEEDS
         if os.path.exists(_bseg("bguard", s))]
    if len(g) == len(B_GUARD_SEEDS):
        gs = E.score_pairs(g)
        se = np.std([p["B"]["fail"] - p["A"]["fail"] for p in g]) / \
            np.sqrt(len(g))
        lb1 = gs["d"] - 1.645 * se
        trip = gs["d"] > 0.010 or lb1 > 0
        print(f"BGUARD n={gs['n']}: failA={gs['failA']:.4f} "
              f"failB={gs['failB']:.4f} d={gs['d']:+.4f} "
              f"onesided95LB={lb1:+.4f} -> "
              f"{'TRIP (NO-PROMOTION)' if trip else 'PASS'}", flush=True)
    else:
        print(f"BGUARD: {len(g)}/{len(B_GUARD_SEEDS)} banked", flush=True)
