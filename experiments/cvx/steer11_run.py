"""STEER11 (PREREG_STEER11.md): the s10_A16 confirmation on a COUCH-CALIBRATED race clock.

  python steer11_run.py race ARM LAM SIZES CLOCK LO CNT STEP OUT     CLOCK = legacy | couch11 (steer11/clock_couch11.json)
  python steer11_run.py gb   ARM OPPONENT LO CNT STEP OUT             (gate b: its opponent's garbage is keyed on PILLS,
                                                                       not on the race clock -> no CLOCK argument)
REUSE (declared): steer10_run.make(ARM) VERBATIM (FAIR = STEER8b fD_bdepD driver/timing, rules_steer10.S10Decider;
ARM in steer10_run.RULE_ARMS: s10_base = FAIR, s10_A16 = dist_target gate vk 4 -> 16), stuck_probe.play_race /
play_gb, refit_opp opponents, steer10_run.SIZES. The ONLY change vs STEER10 is vs_race.CLOCK:
  legacy   vs_race.CLOCK = None: the STEER10 clock (39 + 2 fall + 40 steps frames, garbage free) -- must reproduce the
           banked steer10 rows byte-identically (identity gate, steer11_identity.py)
  couch11  the couch-calibrated clock fitted by steer11_clockcal.py (per-pill base / drop / clear step / cascade fall
           rows, and per released volley the garbage drop + its cascade). Fitted on FAIR-family silicon, so it is only
           valid for the FAIR timing (tempo -6): asserted below.
Rows carry this file's sha, steer10_run's and rules_steer10's sha, git HEAD, the arm spec and the FULL clock dict.
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer10_run as S10
import steer8_run as S8

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
_SHA_S10 = hashlib.sha256(open(os.path.join(HERE, "steer10_run.py"), "rb").read()).hexdigest()[:16]
_SHA_VR = hashlib.sha256(open(os.path.join(HERE, "vs_race.py"), "rb").read()).hexdigest()[:16]
CLOCKS = {"couch11": os.path.join(HERE, "steer11", "clock_couch11.json")}


def load_clock(name):
    if name == "legacy":
        return None
    c = json.load(open(CLOCKS[name]))
    import vs_race as V
    assert set(V.CLOCK_KEYS) <= set(c), sorted(set(V.CLOCK_KEYS) - set(c))
    assert c["name"] == name, (c["name"], name)
    return {k: c[k] for k in V.CLOCK_KEYS}


if __name__ == "__main__":
    import stuck_probe as SP, refit_opp as RO, vs_race as V
    mode, arm = sys.argv[1], sys.argv[2]
    assert S8.ARMS[S10.BASE_ARM]["t"]["tempo"] == -6            # the couch clock is FAIR silicon's (fair settle tempo)
    stamp = {"wrapper": "steer11_run.py", "sha": _SHA, "s10_sha": _SHA_S10, "rules_sha": S10._SHA_RULES,
             "vs_race_sha": _SHA_VR, "git": S8._git(), "arm": arm, "base": S10.BASE_ARM,
             "spec": json.loads(json.dumps(S8.ARMS[S10.BASE_ARM])), "rule": S10.RULE_ARMS[arm]}
    steer, choose, dec = S10.make(arm)
    zero = lambda: {k: 0 for k in dec.stats}
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        assert V.CLOCK is None
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp, "rule": dict(dec.stats)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, sizes, clock = float(sys.argv[3]), sys.argv[4], sys.argv[5]
        lo, cnt, step, outp = int(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8]), sys.argv[9]
        V.SIZES = S10.SIZES[sizes]
        V.CLOCK = load_clock(clock)
        stamp["sizes"] = sizes; stamp["clock"] = V.CLOCK if V.CLOCK is not None else "legacy"
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_race(lo + i * step, arm, lam, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                r["sizes"] = sizes; r["rule"] = dict(dec.stats)
                fh.write(json.dumps(r) + "\n"); fh.flush()
    else:
        sys.exit(f"mode {mode}?")
