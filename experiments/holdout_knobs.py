#!/usr/bin/env python3
"""Fresh-seed HOLDOUT confirmation of the DA re-screen's winners (#86).

Endpoints, thresholds, seed range and n are PRE-REGISTERED in PREREG_KNOBS_HOLDOUT.md,
committed before this was launched. This file only executes that plan; it decides nothing.

Reuses `sweep_knobs.evaluate` UNCHANGED so the holdout is measured by the same instrument
as the screen -- a holdout on a different rig would confound "did it replicate" with "do
the rigs agree".

★ SEEDS ARE STRIDE 2. NesPillSource gives 2k and 2k+1 the identical capsule stream
(measured: 200 consecutive seeds -> 100 distinct streams). Virus layouts still differ, so
consecutive seeds are correlated rather than duplicated -- the screen stands -- but the
correlation is free to remove and this run removes it.

    holdout_knobs.py [--seeds 1000] [--seed0 300000] [--workers 6]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from sweep_knobs import evaluate, _warm                    # noqa: E402
from h2h_vs import WINNER                                   # noqa: E402

ARMS = [
    ("rdyext", 16, "winrate", "primary winrate >=52% AND CI excludes 50"),
    ("maxh",    6, "winrate", "primary winrate >=52% AND CI excludes 50"),
    ("vrdy",   12, "da",      "primary DA: DA_cand < DA_ref (winrate descriptive only)"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=1000)
    ap.add_argument("--seed0", type=int, default=300000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=300)
    ap.add_argument("--topk2", type=int, default=8)
    ap.add_argument("--rule", default="rom")
    ap.add_argument("--out", default="../tmp/selfplay/holdout_knobs_20260809.jsonl")
    a = ap.parse_args()

    assert a.seed0 % 2 == 0, "seed0 must be EVEN so stride 2 lands on distinct capsule streams"
    seeds = list(range(a.seed0, a.seed0 + 2 * a.seeds, 2))
    cfg = dict(level=a.level, max_pills=a.max_pills, nes_pills=True, chain_mode="first",
               topk2=a.topk2, rule=a.rule, garbage=True)
    ref = dict(WINNER)
    out = os.path.abspath(os.path.join(HERE, a.out))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    print("HOLDOUT vs WINNER  L%d  REAL NES capsules  rule=%s" % (a.level, a.rule), flush=True)
    print("seeds %d..%d STRIDE 2 (%d seeds = %d matches/arm), disjoint from the screen's 70000..70319"
          % (seeds[0], seeds[-1], len(seeds), 2 * len(seeds)), flush=True)
    print("reference = WINNER %s" % ref, flush=True)
    print("pre-registration: experiments/PREREG_KNOBS_HOLDOUT.md (committed before launch)", flush=True)
    print(flush=True)

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_warm,
                             initargs=(a.topk2,)) as ex:
        r = evaluate(ex, dict(WINNER), ref, seeds[:20], cfg)
        ok = abs(r["winrate"] - 0.5) < 1e-9 and abs(r["margin"]) < 1e-9
        print("  NULL (winner vs itself)  winrate %6.1f%%  margin %+6.2f   %s"
              % (100 * r["winrate"], r["margin"],
                 "<- exact, as required" if ok else "*** NOT EXACT -- RUN IS VOID"), flush=True)
        if not ok:
            print("VOID: the null control did not return exactly 50.0%/+0.00; no arm is read.",
                  flush=True)
            return 2
        print(flush=True)
        with open(out, "w") as fh:
            for knob, val, primary, note in ARMS:
                cand = dict(ref); cand[knob] = val
                t1 = time.time()
                r = evaluate(ex, cand, ref, seeds, cfg)
                r.update(knob=knob, value=val, base=ref[knob], primary=primary,
                         note=note, seed0=seeds[0], stride=2, n_seeds_req=len(seeds))
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                excl = r["wr_lo"] > 0.5
                if primary == "winrate":
                    verdict = ("CONFIRMED" if (r["winrate"] >= 0.52 and excl)
                               else "NOT CONFIRMED")
                else:
                    verdict = ("CONFIRMED" if r["da_cand"] < r["da_ref"] else "NOT CONFIRMED")
                print("  %s=%-4s winrate %6.1f%% [%.1f%%,%.1f%%]  margin %+6.2f  "
                      "atk %.2fv%.2f  DA %dv%d  -> %s  (%.1f min)"
                      % (knob, val, 100 * r["winrate"], 100 * r["wr_lo"], 100 * r["wr_hi"],
                         r["margin"], r["atk_cand"], r["atk_ref"], r["da_cand"], r["da_ref"],
                         verdict, (time.time() - t1) / 60), flush=True)
    print("\ndone in %.1f min -> %s" % ((time.time() - t0) / 60, out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
