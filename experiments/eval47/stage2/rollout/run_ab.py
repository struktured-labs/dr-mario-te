#!/usr/bin/env python3
"""PRIMARY ENDPOINT RUNNER - paired-seed A/B, base vs treatment.

PRE-REGISTERED (PREREG_STAGE2.md sec 6.3 @ b9725fc):
  N = 3,000 seeds from 20000..29999 (disjoint from every corpus seed: the
  corpus is 2..12001), lulu regime, same rig, same injection schedule.
  PRIMARY = dies-ahead; CO-PRIMARY GATING = clear-rate non-inferiority.

MATCHED-INDEX CONTROL: one task = ONE SEED = BOTH ARMS.  The two arms share the
seed, the pill stream, the virus board and the garbage RNG; the only difference
is the Delta term.  A completed task is therefore a COMPLETE PAIR, so a run that
is stopped early yields a balanced, unbiased prefix of the seed range rather
than a lopsided one.  Seeds are consumed in ascending order and every arm-pair
is written atomically to the same jsonl line.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _winit(model, model_name, provenance=False):
    import arm_lut as AL
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                    "jointdig"))
    import p0_ab as P
    import pressure_rig as PR
    obj = P.load_lulu() if model == "lulu" else None
    PR._init(11, 0, 20, model_kind=("bursty" if model == "lulu" else "drip"),
             bursty_model_obj=obj)
    _W["AL"] = AL
    if model_name == "recommended":
        _W["lut"] = AL.load_recommended()
    elif model_name == "off":
        _W["lut"] = AL.load_recommended().zeroed()
    else:
        raise ValueError(model_name)
    _W["model"] = model
    _W["prov"] = bool(provenance)


def _work(seed):
    AL = _W["AL"]
    prov = _W.get("prov", False)
    t0 = time.monotonic()
    ab = AL.Arm(lut=None)
    rb = AL.play_one(seed, ab)
    at = AL.Arm(lut=_W["lut"], prune=True, provenance=prov, tag="trt")
    rt = AL.play_one(seed, at)
    flips = rt.get("_flips", []) if prov else []
    for r in (rb, rt):
        r.pop("_actions", None)
        r.pop("_flips", None)
    rb["arm"], rt["arm"] = "base", "trt"
    rb["flips"], rt["flips"] = 0, at.stats["flips"]
    rt["plies_scored"] = at.stats["plies"]
    rt["delta_evals"] = at.stats["delta_evals"]
    return {"seed": seed, "model": _W["model"], "base": rb, "trt": rt,
            "secs": round(time.monotonic() - t0, 2), "_flips": flips}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["lulu", "drip"], required=True)
    ap.add_argument("--term", default="recommended",
                    choices=["recommended", "off"])
    ap.add_argument("--seed-start", type=int, default=20000)
    ap.add_argument("--seed-count", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", required=True)
    ap.add_argument("--flips", default=None,
                    help="per-flip provenance CSV (default: <out>.flips.csv). "
                         "ALWAYS ON: measured at 0.00055%% of a game's CPU and "
                         "~108 bytes/game.  Append-only, so a resumed run adds "
                         "rows only for the seeds it actually replays -- it "
                         "pairs with --out by seed, not by line.  "
                         "See PROVENANCE.md.")
    ap.add_argument("--no-flips", action="store_true",
                    help="disable the provenance log (not recommended; the "
                         "stage-2 NO_GO was undiagnosable without it)")
    a = ap.parse_args()
    if a.no_flips:
        a.flips = None
    elif not a.flips:
        a.flips = os.path.splitext(a.out)[0] + ".flips.csv"
    assert a.workers <= 6, "local worker cap is 6 (this box has been OOM-killed)"
    assert a.seed_start >= 20000, "rollout seeds must be disjoint from the corpus"

    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    done = set()
    if os.path.exists(a.out):
        for ln in open(a.out):
            try:
                done.add(json.loads(ln)["seed"])
            except Exception:
                pass
    todo = [s for s in seeds if s not in done]
    print(f"model={a.model} term={a.term} seeds={len(seeds)} todo={len(todo)} "
          f"workers={a.workers}", flush=True)

    import arm_lut as AL
    fl = None
    if a.flips:
        fresh = not os.path.exists(a.flips) or os.path.getsize(a.flips) == 0
        fl = open(a.flips, "a")
        if fresh:
            fl.write(AL.flip_csv_header())

    from concurrent.futures import ProcessPoolExecutor, as_completed
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_winit,
                             initargs=(a.model, a.term, bool(a.flips))) as ex, \
            open(a.out, "a") as fh:
        futs = {ex.submit(_work, s): s for s in todo}
        n = 0
        for f in as_completed(futs):
            rec = f.result()
            rows = rec.pop("_flips", [])
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            if fl is not None:
                for r in rows:
                    fl.write(AL.flip_csv_row(r))
                fl.flush()
            n += 1
            if n % 50 == 0:
                el = time.monotonic() - t0
                print(f"  {n}/{len(todo)} pairs  {el/60:.1f}min  "
                      f"{2*n/el:.2f} games/s  eta "
                      f"{(len(todo)-n)*el/n/60:.1f}min", flush=True)
    if fl is not None:
        fl.close()
        print(f"flips -> {a.flips} ({os.path.getsize(a.flips)} bytes)",
              flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
