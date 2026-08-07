#!/usr/bin/env python3
"""The four-way measurement + overfitting check + transfer test, per the Tier-3 task
spec. All on HELD-OUT seeds distinct from the search's TRAIN_SEEDS (5000-5019) --
this is the overfitting gate: a policy that only beats the champion on its training
seeds is a candidate, not a finding.

Usage:
  measure_fourway.py --vec 165 64 -6 122 6   # best adversary from search_checkpoint.json
  measure_fourway.py                          # reads vec from search_checkpoint.json
"""
from __future__ import annotations

import sys
import os
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from batch_run import (evaluate, OPP_ADV, OPP_CHAMP, OPP_NATIVE, OPP_PRE20, OPP_LEARNED,
                       get_pool, shutdown_pool)

import os as _os
# n reduced from the originally-planned 80/60 -- this box has been running at
# 100-120%+ of nominal CPU capacity most of this session (many concurrent
# sibling-tier jobs), and a single arm at n=80 was observed to take >5 minutes
# without finishing. Smaller n trades CI width for actually completing within
# this session; --full restores the original sizing for a later, less
# contended re-run. Still disjoint from TRAIN_SEEDS (5000-5019).
_N = 30 if not _os.environ.get("FOURWAY_FULL") else 80
HELDOUT_SEEDS = list(range(6000, 6000 + _N))
TRANSFER_SEEDS = list(range(7000, 7000 + (_N - 10 if _N > 10 else _N)))


def fmt(tag, res):
    d = res["champ_death_rate"]; dlo, dhi = res["death_ci"]
    a = res["dies_ahead_rate"]
    ptc = res["champ_pills_to_clear"]
    ptc_s = f"{ptc:.1f}" if ptc is not None else "n/a"
    return (f"{tag:<28} death={d:.1%} [{dlo:.1%},{dhi:.1%}]  dies_ahead={a:.1%}  "
            f"win={res['champ_win_rate']:.1%}  outraced={res['outraced_rate']:.1%}  "
            f"stall={res['stall_rate']:.1%}  pills_to_clear={ptc_s}  n={res['n_seeds']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vec", type=int, nargs=5, default=None,
                    help="w_chain ws w_press w_hold w_bigsq (default: read from checkpoint)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(HERE, "fourway_result.json"))
    a = ap.parse_args()

    if a.vec is None:
        with open(os.path.join(HERE, "search_checkpoint.json")) as fh:
            ck = json.load(fh)
        vec = tuple(ck["best_vec"])
        print(f"using best_vec from search_checkpoint.json (gen {ck['generation']}): {vec}")
    else:
        vec = tuple(a.vec)
        print(f"using --vec: {vec}")

    get_pool(workers=a.workers)
    out = {"vec": vec, "train_seeds": None, "heldout_seeds": [HELDOUT_SEEDS[0], HELDOUT_SEEDS[-1]]}

    print("\n=== FOUR-WAY: champion death rate under different opponents (held-out seeds) ===")
    r_self = evaluate(HELDOUT_SEEDS, OPP_CHAMP, workers=a.workers)
    print(fmt("(a) self-play (champ vs champ)", r_self))
    out["a_selfplay"] = r_self

    r_native = evaluate(HELDOUT_SEEDS, OPP_NATIVE, workers=a.workers)
    print(fmt("(b) champ vs native-d1 (weak)", r_native))
    out["b_native_d1"] = r_native

    r_adv_heldout = evaluate(HELDOUT_SEEDS, OPP_ADV, vec=vec, workers=a.workers)
    print(fmt("(c) champ vs EVOLVED ADVERSARY", r_adv_heldout))
    out["c_evolved_adversary_heldout"] = r_adv_heldout

    import os.path as _osp
    model_path = "/mnt/data/drmario_adversary_t3/checkpoints/adversary_value_model.pkl"
    if _osp.exists(model_path):
        r_learned = evaluate(HELDOUT_SEEDS, OPP_LEARNED, workers=a.workers)
        print(fmt("(d) champ vs LEARNED (distilled) adversary", r_learned))
        out["d_learned_adversary_heldout"] = r_learned
    else:
        print("(d) champ vs LEARNED adversary: SKIPPED -- no trained model yet at "
              f"{model_path}")
        r_learned = None
    print("(e) champ vs HOLE POKER: see hole-poker's own results directory / "
          "coordination reply -- not reproduced here, see ADVERSARY_T3.md")

    print("\n=== OVERFITTING CHECK: adversary on its own TRAINING seeds vs held-out ===")
    from search_adversary import TRAIN_SEEDS
    r_adv_train = evaluate(TRAIN_SEEDS, OPP_ADV, vec=vec, workers=a.workers)
    print(fmt("adversary on TRAIN seeds", r_adv_train))
    print(fmt("adversary on HELDOUT seeds", r_adv_heldout))
    gap = r_adv_train["champ_death_rate"] - r_adv_heldout["champ_death_rate"]
    print(f"  train-vs-heldout death-rate gap: {gap:+.1%} "
          f"({'OVERFIT -- treat as candidate, not finding' if gap > 0.10 else 'no material overfit'})")
    out["overfit_train"] = r_adv_train
    out["overfit_gap"] = gap

    print("\n=== TRANSFER: best adversary vs PRE-STRAND20 champion (chain180, no g_stranded) ===")
    r_transfer = evaluate(TRANSFER_SEEDS, OPP_ADV, vec=vec, champ_kind="pre20", workers=a.workers)
    print(fmt("pre-strand20 champ vs adversary", r_transfer))
    r_transfer_ctrl = evaluate(TRANSFER_SEEDS, OPP_CHAMP, champ_kind="pre20", workers=a.workers)
    print(fmt("pre-strand20 champ self-play ctrl", r_transfer_ctrl))
    out["transfer_pre20_vs_adv"] = r_transfer
    out["transfer_pre20_selfplay_ctrl"] = r_transfer_ctrl

    lift_strand20 = r_adv_heldout["champ_death_rate"] - r_self["champ_death_rate"]
    lift_pre20 = r_transfer["champ_death_rate"] - r_transfer_ctrl["champ_death_rate"]
    print(f"\ndeath-rate LIFT over self-play baseline:")
    print(f"  strand20 champion:    {lift_strand20:+.1%}")
    print(f"  pre-strand20 champion: {lift_pre20:+.1%}")
    if lift_pre20 > 0.05 and lift_strand20 > 0.05:
        verdict = "kills BOTH -- long-standing weakness, not a #47 regression"
    elif lift_pre20 <= 0.02 and lift_strand20 > 0.05:
        verdict = "kills strand20 ONLY -- possible #47-introduced regression, report loudly"
    elif lift_strand20 <= 0.02:
        verdict = "does not materially exceed self-play baseline on EITHER champion"
    else:
        verdict = "mixed / inconclusive at this n -- needs a larger sample before calling it"
    print(f"  VERDICT: {verdict}")
    out["lift_strand20"] = lift_strand20
    out["lift_pre20"] = lift_pre20
    out["verdict"] = verdict

    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\nwrote {a.out}")
    shutdown_pool()


if __name__ == "__main__":
    main()
