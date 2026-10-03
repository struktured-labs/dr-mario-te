"""STEER7 (PREREG_STEER7.md): price answer latency in the FASTER direction.

Brain: s6_dist_target60 (ANTIBODY + dist_target60, the couch build) under the STEER6d measured endgame latency
distribution ("full": one delta per ACTIVE decision, root viruses <= 4, from steer6/endgame_latency_deltas.json,
stochastically rounded -- byte-identical code path to steer6_dlat_dist.py), PLUS a constant shift S frames on EVERY
decision:

  S integer (+1, 0, -1, -2, -4):  D = S + d_active  (d_active = 0 on inactive decisions)
      steer answer frame   max(F0, x + D)            x = the sampled silicon latency (steer_model.latency_samples)
      reach mask T_LAT     max(F0 + 1, 19 + D)       (the firmware's matched constant; STEER6d clamp kept)
      vs_race BASE_F       45 + D                    (tempo, no overlap credit; UNCLAMPED, as STEER6c/6d)
      gate-(b) clock       CP.T_LAT 0.6 + D/60.0988 s
  S = "ceil" (zero-latency ceiling, the answer is available at spawn on EVERY decision, no measured delta):
      steer answer frame   F0 = 3 (the first frame the ROM processes input)
      reach mask T_LAT     F0 = 3 (validated vs the frame simulator: steer7_mask_validate.py)
      tempo / clock        shifted by F0 - mean(x) = -16.25 f on every decision (the mean realised answer gain)

S = 0 is steer6_dlat_dist.py "full" exactly (identity check: the rows must equal the banked steer6/d6 rows).

Activity counters (rule 26: a treatment with zero activity is UNRUN, not neutral), per game:
  lat_dec        decisions; lat_ans_sum / lat_nom_sum: realised vs nominal steer answer frames (sum)
  lat_clamp      decisions where x + D < F0 (the steer clamp binds); lat_overcredit_f: tempo frames credited
                 beyond the clamp (the unclamped tempo channel's overstatement)
  lat_mask_calls / lat_mask_tlat_sum: reach-mask calls made INSIDE the decider and the T_LAT they saw
  lat_tempo_sum: sum of the tempo shift (frames) applied
Every row is stamped with the wrapper's sha256 and the git HEAD (rule 26: stamp the executed code path).

  python steer7_dlat.py gb   ARM OPPONENT LO CNT STEP OUT SHIFT
  python steer7_dlat.py race ARM LAM      LO CNT STEP OUT SHIFT
"""
import sys, os, json, hashlib, random, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()

HERE = os.path.dirname(os.path.abspath(__file__))
F0 = 3
_SRC_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]


def _git_head():
    try:
        return subprocess.run(["git", "-C", HERE, "rev-parse", "--short=8", "HEAD"], capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except Exception:
        return "?"


def deltas():
    d = json.load(open(os.path.join(HERE, "steer6", "endgame_latency_deltas.json")))
    return [r["delta_f"] for r in d["rows"]]


def wrap(choose0, steer, xs, shift, vk=4):
    import reach_fw_tap as RFT, vs_race as V, clock_play as CP
    lat0 = list(steer.lat); n = len(lat0); mean_lat = sum(lat0) / n
    ceil = shift == "ceil"
    cache = {}
    stats = {}

    def reset():
        stats.update(active=0, extra_frames=0, dec=0, ans_sum=0, nom_sum=0, clamp=0, overcredit=0.0,
                     mask_calls=0, mask_tlat_sum=0, tempo_sum=0.0)
    reset()

    def lat_for(d):
        if d not in cache:
            cache[d] = [max(F0, x + d) for x in lat0]
        return cache[d]

    # pass-through instrument on the reach mask: counts calls made inside the decider and the T_LAT they read
    mask_orig = RFT.reach_mask_fw
    state = {"in_choose": False}

    def mask_counted(*a, **kw):
        if state["in_choose"]:
            stats["mask_calls"] += 1; stats["mask_tlat_sum"] += RFT.T_LAT
        return mask_orig(*a, **kw)
    RFT.reach_mask_fw = mask_counted

    def choose(env, col, vir, ctx):
        k = int(env.pills_placed)
        # the steer model's own sample for this pill (steer_model.Steer._t_act, pooled mode): same seed, same k
        x = lat0[random.Random(steer.seed * 1000003 + k * 7919 + 17).randrange(n)]
        stats["dec"] += 1; stats["nom_sum"] += x
        if ceil:
            dT = F0 - mean_lat
            RFT.T_LAT = F0; V.BASE_F = 45.0 + dT; CP.T_LAT = 0.6 + dT / 60.0988
            steer.lat = lat_for(-10 ** 6)                     # every sample clamps to F0
            stats["ans_sum"] += F0; stats["tempo_sum"] += dT
            stats["clamp"] += 1
        else:
            d = 0
            if int(env.board.virus_count()) <= vk:              # == steer6_dlat_dist.wrap (STEER6d "full")
                h = hashlib.md5(env.board.color.tobytes() + env.board.is_virus.tobytes()
                                + int(env.pills_placed).to_bytes(2, "little")).hexdigest()
                rng = random.Random(int(h[:12], 16))
                xd = xs[rng.randrange(len(xs))]
                fl = math.floor(xd)
                d = int(fl) + (1 if rng.random() < xd - fl else 0)
                stats["active"] += 1; stats["extra_frames"] += d
            D = shift + d
            RFT.T_LAT = max(F0 + 1, 19 + D); V.BASE_F = 45.0 + D; CP.T_LAT = 0.6 + D / 60.0988
            steer.lat = lat_for(D)
            stats["ans_sum"] += max(F0, x + D); stats["tempo_sum"] += D
            if x + D < F0:
                stats["clamp"] += 1; stats["overcredit"] += F0 - (x + D)
        state["in_choose"] = True
        try:
            return choose0(env, col, vir, ctx)
        finally:
            state["in_choose"] = False
    return choose, stats, reset


def _row_extra(shift, st):
    return {"lat_variant": "full" if shift != "ceil" else "ceil", "lat_active": st["active"],
            "lat_extra_f": st["extra_frames"], "shift": shift, "lat_dec": st["dec"], "lat_ans_sum": st["ans_sum"],
            "lat_nom_sum": st["nom_sum"], "lat_clamp": st["clamp"], "lat_overcredit_f": round(st["overcredit"], 3),
            "lat_mask_calls": st["mask_calls"], "lat_mask_tlat_sum": st["mask_tlat_sum"],
            "lat_tempo_sum": round(st["tempo_sum"], 3),
            "rig": {"wrapper": "steer7_dlat.py", "sha": _SRC_SHA, "git": _GIT}}


if __name__ == "__main__":
    import stuck_probe as SP, steer_model as SM, steer_run as SR, reach_fw_tap as RFT, vs_race as V
    assert RFT.T_LAT == 19 and V.BASE_F == 45.0
    _GIT = _git_head()
    mode, sh = sys.argv[1], sys.argv[-1]
    shift = "ceil" if sh == "ceil" else int(sh)
    xs = deltas()
    if mode == "gb":
        import opp_run as OR
        arm, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose0 = SR.make(arm); opp = OR.make_opponent(oppname)
        choose, st, reset = wrap(choose0, steer, xs, shift)
        with open(outp, "w") as fh:
            for i in range(cnt):
                reset()
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0})
                r.update(_row_extra(shift, st))
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        arm, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        choose, st, reset = wrap(SR.make(arm)[1], steer, xs, shift)
        with open(outp, "w") as fh:
            for i in range(cnt):
                reset()
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True
                r.update(_row_extra(shift, st))
                fh.write(json.dumps(r) + "\n"); fh.flush()
