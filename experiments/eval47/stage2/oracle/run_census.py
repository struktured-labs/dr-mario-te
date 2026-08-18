"""Gate-rate census: price gate-v2's DOSE without paying for a single fork.

The H12/H13 fire rate factorises (measurement rule 5 corollary):

    fire rate = gate rate  x  P(exact top-2 tie | gated)  x  P(margin | tie)

The first two factors are pure functions of the board the CHAMPION reaches and
of the champion's own values — both already computed by a const arm — so they
cost ~1 champion game per seed instead of an H12 pair (~232 core-s). Only the
third factor needs rollouts. This instrument measures the first two exactly and
reports the trigger-rate ratio v2/v1, which is what decides whether the wider
gate is affordable at all.

⚠ SCOPE, stated with the number (rule 24): the census plays the CHAMPION's
trajectory. Under a real H13 arm the flips themselves change later boards, so
the census is the dose at the FIRST divergence, not a full-game dose. It bounds
the trigger-rate ratio; it does not replace the paired pilot.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def _winit(model, thresholds):
    import oracle_arm as O
    C, bmodel = O.init_rig(model)
    _W.update(O=O, C=C, bmodel=bmodel, thresholds=thresholds)


def _work(seed):
    """Census one seed, and PROVE the census arm is the champion on that seed.

    GateCensusArm recomputes the champion's values in its own `choose`, so it is
    a second implementation of a path that already exists (measurement rule 3).
    Rather than assert the two "should agree", every row carries the result of
    comparing its full action sequence against OracleArm(const) — the guard
    lives in the instrument, not in a convention the caller has to remember.
    The extra const game is cheap next to the fork-free census itself.
    """
    from h13_arm import GateCensusArm
    O = _W["O"]
    arm = GateCensusArm(thresholds=_W["thresholds"])
    res = O.play_one(seed, arm, _W["C"], _W["bmodel"])
    ref = O.play_one(seed, O.OracleArm(label_mode="const"), _W["C"],
                     _W["bmodel"])
    champ_identical = int(res.pop("_actions", None) == ref.pop("_actions", None))
    return {"seed": seed, "res": res["res"], "n_plies": res["n_plies"],
            "champ_identical": champ_identical, "rows": arm.rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, required=True)
    ap.add_argument("--seed-count", type=int, required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--thresholds", type=int, nargs="+", default=[11, 12, 13, 14])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    seeds = list(range(a.seed_start, a.seed_start + a.seed_count))
    thresholds = tuple(a.thresholds)
    print(f"census seeds={len(seeds)} thresholds={thresholds} "
          f"workers={a.workers}", flush=True)

    from concurrent.futures import ProcessPoolExecutor
    t0 = time.monotonic()
    n = 0
    with open(a.out, "w") as fh, ProcessPoolExecutor(
            max_workers=a.workers, initializer=_winit,
            initargs=("lulu", thresholds)) as ex:
        for r in ex.map(_work, seeds):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            n += 1
            if n % 25 == 0:
                el = time.monotonic() - t0
                print(f"  {n}/{len(seeds)} {el/60:.1f}min "
                      f"{n/el:.2f} games/s", flush=True)
    el = time.monotonic() - t0
    print(f"DONE {n} games in {el/60:.1f} min ({el*a.workers/max(n,1):.1f} "
          f"core-s/game) -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
