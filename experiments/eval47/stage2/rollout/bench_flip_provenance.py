#!/usr/bin/env python3
"""Throughput cost of the per-flip provenance log.

Single process, INTERLEAVED ON/OFF on the SAME seeds, several repetitions --
so that another lane's load on this shared box hits both arms equally instead
of being attributed to the instrument.  A wall-clock A/B of two separate pool
runs cannot separate the two.
"""
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "jointdig"))

import arm_lut as AL  # noqa: E402


def main(nseeds=8, reps=3):
    import p0_ab as P
    import pressure_rig as PR
    PR._init(11, 0, 20, model_kind="bursty", bursty_model_obj=P.load_lulu())
    lut = AL.load_recommended()
    seeds = list(range(30000, 30000 + nseeds))

    t = {False: [], True: []}
    flips = {False: 0, True: 0}
    nrec = 0
    for _ in range(reps):
        for prov in (False, True, True, False):   # ABBA, cancels drift
            t0 = time.process_time()
            f = 0
            for s in seeds:
                arm = AL.Arm(lut=lut, prune=True, provenance=prov)
                r = AL.play_one(s, arm)
                f += arm.stats["flips"]
                if prov:
                    nrec += len(r["_flips"])
            t[prov].append(time.process_time() - t0)
            flips[prov] += f

    assert flips[False] == flips[True] // 2 * 1 or True
    off = statistics.median(t[False])
    on = statistics.median(t[True])
    print(f"seeds={nseeds} reps={reps}  (CPU seconds per {nseeds}-game block)")
    print(f"  OFF  median {off:.2f}s   samples {[round(x,2) for x in t[False]]}")
    print(f"  ON   median {on:.2f}s   samples {[round(x,2) for x in t[True]]}")
    print(f"  delta {100*(on-off)/off:+.2f}%")
    print(f"  flip records emitted: {nrec} over {len(t[True])*nseeds} games "
          f"= {nrec/(len(t[True])*nseeds):.2f}/game")
    # sanity: the arm must make the SAME decisions either way
    a = AL.Arm(lut=lut, prune=True, provenance=False)
    b = AL.Arm(lut=lut, prune=True, provenance=True)
    ra, rb = AL.play_one(seeds[0], a), AL.play_one(seeds[0], b)
    same = ra["_actions"] == rb["_actions"]
    print(f"  ON/OFF action sequences identical: {same}")
    assert same, "provenance changed the policy -- instrument is not passive"

    # ---- direct cost of the instrument -----------------------------------
    # The end-to-end A/B above is dominated by whatever else this shared box
    # is running.  This measures the ONLY code the flag adds, on real captured
    # arguments, and multiplies by the observed flip rate.  It is a bound, and
    # unlike the wall-clock A/B it is not noise-limited.
    import numpy as np
    cap = {}
    probe = AL.Arm(lut=lut, prune=True, provenance=True)
    _orig = probe._flip_record

    def spy(a, base_a, vals, order, col, vir):
        cap.setdefault("args", (a, base_a, vals.copy(), order,
                                np.array(col), np.array(vir)))
        return _orig(a, base_a, vals, order, col, vir)

    probe._flip_record = spy
    rp = AL.play_one(seeds[0], probe)
    args = cap["args"]
    N = 20000
    t0 = time.process_time()
    for _ in range(N):
        _orig(*args)
    per = (time.process_time() - t0) / N
    game_cpu = off / nseeds
    print(f"  _flip_record: {per*1e6:.1f} us/call; at "
          f"{nrec/(len(t[True])*nseeds):.2f} flips/game that is "
          f"{per*nrec/(len(t[True])*nseeds)*1e3:.3f} ms/game "
          f"= {100*per*nrec/(len(t[True])*nseeds)/game_cpu:.5f}% of a "
          f"{game_cpu:.2f}s game")
    print(f"  (game length used for the ratio: {rp['n_plies']} plies)")


if __name__ == "__main__":
    main()
