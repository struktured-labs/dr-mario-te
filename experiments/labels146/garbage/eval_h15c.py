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
    ap.add_argument("stage", choices=("run", "analyze"))
    ap.add_argument("--workers", type=int, default=20)
    args = ap.parse_args()
    if args.stage == "run":
        run(args.workers)
    else:
        analyze()


if __name__ == "__main__":
    main()
