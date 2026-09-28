"""STEER6d (PREREG_STEER6d.md): dist_target60 with its MEASURED whole-decision latency delta.

reachbuild's co-sim (`steer6/endgame_latency_deltas.json`): DRDIST fw vs ANTIBODY fw on 437 real endgame boards,
delta frames mean -0.07, median +0.005, p95 +2.73, max +12.8, min -7.4. The engine adds 0 cycles; the delta is the
search doing different work (tuck extension, top-k) because the term changes leaf values.

On every ACTIVE decision (root viruses <= 4) one delta x is drawn from the 437 per-board values (deterministic per
board). It becomes whole frames by stochastic rounding: floor(x) + Bernoulli(x - floor(x)). The delta then moves:
  - the steer answer frame (clamped at F0 = 3),
  - the reach-mask T_LAT constant,
  - vs_race BASE_F,
  - the gate-(b) clock.
Inactive decisions run at nominal latency. With CLIP = the p95, draws above the p95 are replaced by the p95
("tail clipped"). The difference between the full run and the clipped run is the tail's contribution.

  python steer6_dlat_dist.py gb   ARM OPPONENT LO CNT STEP OUT {full|clip}
  python steer6_dlat_dist.py race ARM LAM      LO CNT STEP OUT {full|clip}
"""
import sys, os, json, hashlib, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()

HERE = os.path.dirname(os.path.abspath(__file__))


def deltas(variant):
    d = json.load(open(os.path.join(HERE, "steer6", "endgame_latency_deltas.json")))
    xs = [r["delta_f"] for r in d["rows"]]
    if variant == "clip":
        xs = [min(x, d["p95"]) for x in xs]
    return xs


def wrap(choose0, steer, xs, vk=4):
    import reach_fw_tap as RFT, vs_race as V, clock_play as CP
    F0 = 3
    lat0 = list(steer.lat); cache = {}
    stats = {"active": 0, "extra_frames": 0}

    def lat_for(d):
        if d not in cache:
            cache[d] = [max(F0, x + d) for x in lat0]
        return cache[d]

    def choose(env, col, vir, ctx):
        d = 0
        if int(env.board.virus_count()) <= vk:
            h = hashlib.md5(env.board.color.tobytes() + env.board.is_virus.tobytes()
                            + int(env.pills_placed).to_bytes(2, "little")).hexdigest()
            rng = random.Random(int(h[:12], 16))
            x = xs[rng.randrange(len(xs))]
            fl = math.floor(x)
            d = int(fl) + (1 if rng.random() < x - fl else 0)
            stats["active"] += 1; stats["extra_frames"] += d
        RFT.T_LAT = max(F0 + 1, 19 + d); V.BASE_F = 45.0 + d; CP.T_LAT = 0.6 + d / 60.0988
        steer.lat = lat_for(d)
        return choose0(env, col, vir, ctx)
    return choose, stats


if __name__ == "__main__":
    import stuck_probe as SP, steer_model as SM, steer_run as SR, reach_fw_tap as RFT, vs_race as V
    assert RFT.T_LAT == 19 and V.BASE_F == 45.0
    mode, variant = sys.argv[1], sys.argv[-1]
    assert variant in ("full", "clip")
    xs = deltas(variant)
    if mode == "gb":
        import opp_run as OR
        arm, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose0 = SR.make(arm); opp = OR.make_opponent(oppname)
        choose, st = wrap(choose0, steer, xs)
        with open(outp, "w") as fh:
            for i in range(cnt):
                st["active"] = st["extra_frames"] = 0
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "lat_variant": variant,
                          "lat_active": st["active"], "lat_extra_f": st["extra_frames"]})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        arm, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        choose, st = wrap(SR.make(arm)[1], steer, xs)
        with open(outp, "w") as fh:
            for i in range(cnt):
                st["active"] = st["extra_frames"] = 0
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True
                r.update({"lat_variant": variant, "lat_active": st["active"], "lat_extra_f": st["extra_frames"]})
                fh.write(json.dumps(r) + "\n"); fh.flush()
