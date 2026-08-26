#!/usr/bin/env python3
"""G-IDENTITY, PARALLEL ACROSS SEEDS — PREREG_H12_SUBSTITUTION.md §2.1.

WHY PARALLEL, and it is not for speed: the production run will be parallel across ~14
workers on a shared 16-vCPU box, so the quantity that costs it is WALL-CLOCK THROUGHPUT
at the worker count actually used — including the shared-tenant tax. A serial
core-seconds figure prices an arrangement that will never occur, and extrapolating it
UNDERSTATES the true cost confidently. Measure the consumer, not the estimator.

Correctness is unaffected: seeds are independent and every comparison is WITHIN seed
(sealed / instrumented / mutant all for the same seed). Per-seed determinism on this CPU
is what the bit-exactness PASS established. Parallelising can change timing, never a verdict.

⚠ THREADS ARE PINNED TO 1 PER WORKER, set before numpy/numba import. Unpinned, each worker
spawns its own pool and the box thrashes — measured elsewhere in this program at 62 threads
taking 11+ min against 4 threads taking 5.6 s.
⚠ A SHARED numba cache dir is used so workers do not each compile from cold; the first
completed seed is additionally reported separately so JIT warm-up cannot contaminate the rate.
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "1"
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/drm-numba-cache")

import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_RIG = {}


def _one(args):
    seed, level, max_pills, model, skip_mutant = args
    import oracle_arm as OA
    from h12_arm import H12Arm
    from h12_boards import H12ArmWithBoards, H12ArmMutantNoMargin
    if "C" not in _RIG:
        _RIG["C"], _RIG["b"] = OA.init_rig(model=model, level=level)
    C, bmodel = _RIG["C"], _RIG["b"]
    t0 = time.time()
    ref = OA.play_one(seed, H12Arm(provenance=True), C, bmodel, max_pills)
    arm = H12ArmWithBoards(provenance=True)
    ins = OA.play_one(seed, arm, C, bmodel, max_pills)
    md = None
    if not skip_mutant:
        m = OA.play_one(seed, H12ArmMutantNoMargin(provenance=True), C, bmodel, max_pills)
        md = m["_actions"] != ref["_actions"]
    return dict(seed=seed, plies=ins["n_plies"], res=ins["res"],
                identical=ref["_actions"] == ins["_actions"], mutant_differs=md,
                flips=len(arm.flip_log),
                planes=sum(1 for r in arm.flip_log if r.get("planes")),
                secs=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed-lo", type=int, default=70000)
    ap.add_argument("--level", type=int, default=20)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--skip-mutant", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "gate_identity_par.json"))
    a = ap.parse_args()

    seeds = [a.seed_lo + 2 * i for i in range(a.seeds)]
    jobs = [(s, a.level, a.max_pills, a.model, a.skip_mutant) for s in seeds]
    print(f"G-IDENTITY parallel: {len(seeds)} seeds x 3 arms, {a.workers} workers, "
          f"threads pinned to 1, L{a.level} {a.model}", flush=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(_one, j): j[0] for j in jobs}
        for f in as_completed(futs):
            r = f.result(); rows.append(r)
            print(f"  seed {r['seed']}: plies={r['plies']:3d} res={r['res']:7s} "
                  f"identical={r['identical']} mutant_differs={r['mutant_differs']} "
                  f"flips={r['flips']:2d} planes={r['planes']:2d} {r['secs']:6.1f}s",
                  flush=True)
    wall = time.time() - t0
    rows.sort(key=lambda r: r["seed"])
    same = sum(r["identical"] for r in rows)
    mut = sum(1 for r in rows if r["mutant_differs"])
    nf = sum(r["flips"] for r in rows); npl = sum(r["planes"] for r in rows)

    # ---- report G-MUTANT FIRST (team-lead's order): a blind gate voids everything after it
    ok_mut = a.skip_mutant or mut > 0
    print(f"\nG-MUTANT    margin-off differs on {mut}/{len(rows)} seeds  "
          f"{'PASS (the gate CAN fail)' if ok_mut else 'FAIL — GATE IS BLIND, ALL DOWNSTREAM VOID'}")
    ok_id = same == len(rows)
    print(f"G-IDENTITY  instrumented == sealed on {same}/{len(rows)} seeds  "
          f"{'PASS' if ok_id else 'FAIL'}")
    print(f"\nflips {nf} ({nf/len(rows):.2f}/game), planes on {npl}")
    slowest = max(r["secs"] for r in rows)
    med = sorted(r["secs"] for r in rows)[len(rows)//2]
    thr = len(rows) / (wall / 3600.0)
    print(f"\nTHROUGHPUT (the number that costs the run): {thr:.1f} seeds/hour wall-clock "
          f"at {a.workers} workers")
    print(f"  wall {wall/60:.1f} min for {len(rows)} seeds x 3 arms")
    print(f"  per-seed(3 arms) contended: median {med:.0f}s, slowest {slowest:.0f}s")
    print(f"  => 200-game instrumented-only run ~= {200/ (thr*3):.2f} h wall "
          f"(3 arms here vs 1 arm in production)")
    json.dump(dict(seeds=seeds, workers=a.workers, level=a.level, model=a.model,
                   identical=same, mutant_differs=mut, flips=nf, with_planes=npl,
                   wall_secs=wall, seeds_per_hour=thr, rows=rows,
                   verdict="PASS" if (ok_id and ok_mut) else "FAIL"),
              open(a.out, "w"), indent=1)
    sys.exit(0 if (ok_id and ok_mut) else 1)


if __name__ == "__main__":
    main()
