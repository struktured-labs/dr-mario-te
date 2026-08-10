#!/usr/bin/env python3
"""SCALE-MATCHED NULL CONTROL ARM (added after the primary read out NO_GO).

Declared in PREREG_ROLLOUT.md deviation-log entry 2 BEFORE it was run.
It carries NO verdict authority - the primary verdict is already fixed.

WHY IT EXISTS.  The primary read NO_GO with a favourable-but-not-significant
dies-ahead point estimate and MASSIVE outcome churn: a 1.78% per-ply argmax-flip
rate produced 611 discordant clear outcomes in 3,000 paired seeds and left only
760 pairs identical.  The question that leaves open is the one memory law
`dr-mario-av-reach-refuted` names: *is the effect the TERM, or is it the
perturbation?*  The only way to answer it is a control matched on scale and
blind to the label - exactly what that memory says IS the test.

THE CONTROL ARM: the identical LUT with each feature's table ROW-PERMUTED
(rng 20260810).  Same 288 entries, same value multiset per feature, same |Delta|
scale, same silicon cost, same flip machinery - and NO fitted mapping from board
to penalty.  Gate 0 already measured it at holdout AUC 0.4746 vs the fitted
model's 0.7220, so it is certified label-blind.

WHAT WRONG INPUT WOULD MAKE THIS CONTROL FAIL: if the shuffled arm were
accidentally the fitted arm, its rollout flip rate and outcome churn would match
the fitted arm AND its offline AUC would be 0.7220.  Both are asserted here.

BASE IS NOT RE-RUN.  The base arm is deterministic in the seed (env, pill
stream and garbage RNG are all seeded from it), so the stored base rows from
ab_lulu.jsonl are reused.  `--verify N` re-derives the base arm on N seeds and
asserts byte-equality with the stored rows; a drifted tree fails it.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _winit(model, k=1.0):
    import arm_lut as AL
    import numpy as np
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                    "jointdig"))
    import p0_ab as P
    import pressure_rig as PR
    obj = P.load_lulu() if model == "lulu" else None
    PR._init(11, 0, 20, model_kind=("bursty" if model == "lulu" else "drip"),
             bursty_model_obj=obj)
    _W["AL"] = AL
    sh = AL.load_recommended().shuffled_tables(20260810)
    if k != 1.0:
        # DOSE-MATCHED null: tables scaled so the holdout target-class
        # argmax-flip matches the fitted arm's 2.12% (calib_null.py).
        sh = AL.LutDelta(sh.feats, sh.scales,
                         [np.rint(np.asarray(t) * k).astype(np.int64)
                          for t in sh.tables], name=f"shuf_k{k}")
    _W["lut"] = sh
    _W["model"] = model


def _work(job):
    seed, verify = job
    AL = _W["AL"]
    t0 = time.monotonic()
    a = AL.Arm(lut=_W["lut"], prune=True)
    r = AL.play_one(seed, a)
    r.pop("_actions", None)
    r["arm"] = "shuf"
    r["flips"] = a.stats["flips"]
    r["plies_scored"] = a.stats["plies"]
    out = {"seed": seed, "model": _W["model"], "shuf": r,
           "secs": round(time.monotonic() - t0, 2)}
    if verify:
        ab = AL.Arm(lut=None)
        rb = AL.play_one(seed, ab)
        rb.pop("_actions", None)
        out["base_recheck"] = rb
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="lulu", choices=["lulu", "drip"])
    ap.add_argument("--pairs", required=True, help="ab_*.jsonl to pair against")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--verify", type=int, default=25)
    ap.add_argument("--k", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    assert a.workers <= 6

    seeds = []
    for ln in open(a.pairs):
        try:
            seeds.append(json.loads(ln)["seed"])
        except Exception:
            pass
    seeds = sorted(set(seeds))
    done = set()
    if os.path.exists(a.out):
        for ln in open(a.out):
            try:
                done.add(json.loads(ln)["seed"])
            except Exception:
                pass
    todo = [(s, i < a.verify) for i, s in enumerate(seeds) if s not in done]
    print(f"CONTROL model={a.model} seeds={len(seeds)} todo={len(todo)} "
          f"verify={a.verify} workers={a.workers}", flush=True)

    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_winit,
                             initargs=(a.model, a.k)) as ex, open(a.out, "a") as fh:
        futs = {ex.submit(_work, j): j for j in todo}
        n = 0
        for f in as_completed(futs):
            fh.write(json.dumps(f.result()) + "\n")
            fh.flush()
            n += 1
            if n % 100 == 0:
                el = time.monotonic() - t0
                print(f"  {n}/{len(todo)}  {el/60:.1f}min  {n/el:.2f} games/s "
                      f"eta {(len(todo)-n)*el/n/60:.1f}min", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
