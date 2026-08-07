#!/usr/bin/env python3
"""Minimal, fast core comparison -- (a)/(b)/(c)/(d) death rates only, small n,
written to guarantee a real result lands under this session's severe shared-box
contention (measure_fourway.py's fuller n=80 pipeline was killed twice without
finishing an arm; see ADVERSARY_T3.md's resource note). Prints after EACH arm
so partial results are visible even if killed mid-run."""
from __future__ import annotations
import sys, os, json, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from batch_run import evaluate, OPP_ADV, OPP_CHAMP, OPP_NATIVE, OPP_LEARNED, get_pool, shutdown_pool

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=15)
ap.add_argument("--workers", type=int, default=6)
ap.add_argument("--vec", type=int, nargs=5, default=(234, 20, -31, 233, 37))
a = ap.parse_args()

SEEDS = list(range(6000, 6000 + a.n))
get_pool(workers=a.workers)
out = {}

for tag, kind, vec in (("a_selfplay", OPP_CHAMP, None), ("b_native_d1", OPP_NATIVE, None),
                        ("c_evolved_adv", OPP_ADV, tuple(a.vec)), ("d_learned", OPP_LEARNED, None)):
    if kind == OPP_LEARNED and not os.path.exists(
            "/mnt/data/drmario_adversary_t3/checkpoints/adversary_value_model.pkl"):
        print(f"{tag}: SKIPPED (no model)"); continue
    r = evaluate(SEEDS, kind, vec=vec, workers=a.workers)
    out[tag] = r
    print(f"{tag}: death={r['champ_death_rate']:.1%} [{r['death_ci'][0]:.1%},"
          f"{r['death_ci'][1]:.1%}]  dies_ahead={r['dies_ahead_rate']:.1%}  "
          f"win={r['champ_win_rate']:.1%}  outraced={r['outraced_rate']:.1%}  "
          f"stall={r['stall_rate']:.1%}  n={r['n_seeds']}", flush=True)
    with open(os.path.join(HERE, "quick_fiveway_result.json"), "w") as fh:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != "seed_rows"}
                   for k, v in out.items()}, fh, indent=2, default=str)

shutdown_pool()
print("DONE")
