#!/usr/bin/env python3
"""YIELD PROBE — flips per seed, with spread, and the stall-at-cap fraction.

WHY: the experiment's unit is the FLIP, not the seed, and the two are not proportional.
A seed that runs to `max_pills` and stalls consumes full compute and yields ZERO flips.
Costing the run per SEED therefore understates it. This measures flips/seed, its spread,
and how much compute buys nothing.

Instrumented arm ONLY — G-IDENTITY has already done its job, so ref/mutant are not re-run.
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "1"
os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/drm-numba-cache")
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
_R = {}


def _one(a):
    seed, level, max_pills, model = a
    import oracle_arm as OA
    from h12_boards import H12ArmWithBoards
    if "C" not in _R:
        _R["C"], _R["b"] = OA.init_rig(model=model, level=level)
    t0 = time.time()
    arm = H12ArmWithBoards(provenance=True)
    r = OA.play_one(seed, arm, _R["C"], _R["b"], max_pills)
    return dict(seed=seed, res=r["res"], plies=r["n_plies"], pills=r["pills"],
                flips=len(arm.flip_log),
                planes=sum(1 for f in arm.flip_log if f.get("planes")),
                tie_plies=arm.stats.get("tie_plies", 0),
                gated=arm.stats.get("gated_plies", 0),
                at_cap=int(r["n_plies"] >= max_pills), secs=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed-lo", type=int, default=71000)
    ap.add_argument("--level", type=int, default=20)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default=os.path.join(HERE, "yield_probe.json"))
    a = ap.parse_args()
    seeds = [a.seed_lo + 2 * i for i in range(a.seeds)]
    print(f"yield probe: {len(seeds)} seeds, instrumented arm only, {a.workers} workers, "
          f"L{a.level}, max_pills={a.max_pills}", flush=True)
    t0 = time.time(); rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(_one, (s, a.level, a.max_pills, a.model)) for s in seeds]
        for f in as_completed(futs):
            r = f.result(); rows.append(r)
            print(f"  seed {r['seed']}: {r['res']:7s} plies={r['plies']:3d} "
                  f"flips={r['flips']:2d} tie={r['tie_plies']:3d} at_cap={r['at_cap']} "
                  f"{r['secs']:6.1f}s", flush=True)
    wall = time.time() - t0
    rows.sort(key=lambda r: r["seed"])
    import statistics as st
    fl = [r["flips"] for r in rows]
    tot_f, n = sum(fl), len(rows)
    zero = sum(1 for x in fl if x == 0)
    cap = sum(r["at_cap"] for r in rows)
    core_s = sum(r["secs"] for r in rows)
    print(f"\n=== YIELD (n={n} seeds) ===")
    print(f"  flips/seed: mean {tot_f/n:.2f}  median {st.median(fl):.1f}  "
          f"sd {st.pstdev(fl):.2f}  min {min(fl)}  max {max(fl)}")
    print(f"  ZERO-YIELD seeds: {zero}/{n} = {zero/n*100:.0f}%  (compute that buys nothing)")
    print(f"  STALL-AT-CAP:     {cap}/{n} = {cap/n*100:.0f}%  (censored, not a natural end)")
    print(f"  res mix: " + ", ".join(f"{k}={sum(1 for r in rows if r['res']==k)}"
                                     for k in ("clear", "topout", "stall")))
    print(f"  planes on {sum(r['planes'] for r in rows)}/{tot_f} flips")
    if tot_f:
        per_flip = core_s / tot_f
        print(f"\n=== COST IN THE RIGHT UNIT ===")
        print(f"  {core_s:.0f} core-s for {tot_f} flips = {per_flip:.0f} core-s/flip")
        print(f"  1,000 flips => {per_flip*1000/3600:.1f} core-h   "
              f"(§9 quoted ~20 core-h => ratio {per_flip*1000/3600/20:.2f}x)")
    print(f"\n  throughput {n/(wall/3600):.1f} seeds/h wall at {a.workers} workers "
          f"({wall/60:.1f} min)")
    json.dump(dict(rows=rows, n=n, flips_total=tot_f, zero_yield=zero, at_cap=cap,
                   core_secs=core_s, wall_secs=wall, workers=a.workers,
                   core_s_per_flip=(core_s/tot_f if tot_f else None)),
              open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
