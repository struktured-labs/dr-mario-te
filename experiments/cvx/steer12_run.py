"""STEER12 (PREREG_STEER12.md): TEMPO LEVERS for FAIR on the couch11 race clock.

  python steer12_run.py race ARM LAM SIZES LO CNT STEP OUT      (race clock = couch11, always)
  python steer12_run.py gb   ARM OPPONENT LO CNT STEP OUT        (gate b; its garbage is pill-keyed: clock-free)

BASE = FAIR = steer10_run.make("s10_base") VERBATIM (STEER8b fD_bdepD: silicon-faithful brain, DIST60, fair driver:
G0 7|8 - 5, answer -6, tempo -6, DRPROPHFIRST end f11, DEPLOYED fw mask T_LAT 19 / G0 8). An ARM wraps FAIR's Steer
object (class Knob) and touches nothing else:
  LATENCY  lat_m2 / lat_m4 / lat_m6 (D = -2/-4/-6 f) and lat_ceil -- STEER7 semantics on FAIR, G0 FIXED at FAIR's:
             steer answer frame   max(F0, x - 6 + D)  (x = the silicon first-lateral sample, steer_model pooled mode)
             PROPH-first end      max(F0, 11 + D)     (fix D's commit window moves with the gate)
             reach mask T_LAT     max(F0 + 1, 19 + D) (the firmware's matched constant, as STEER7)
             race tempo           couch11 per-pill base + (this pill's REALISED answer frame - FAIR's realised answer
                                  frame on the same pill), i.e. 1:1 on the clamped shift (STEER7 used the unclamped D)
           lat_ceil: answer F0 on every pill (incl. armed), mask T_LAT F0, tempo shift F0 - FAIR's realised answer.
  EXECUTION  ex_perfect: the brain's chosen action is placed straight (no steering model, no misses) = 0 overhead.
           ex_q05 / ex_q10 / ex_q15: FAIR's steering model PLUS injected misses: with probability q per pill the target
             handed to the steering model is a uniformly random OTHER action allowed by the shipping reach mask
             (reach_fw_tap, the brain's own mask) and legal on the board. (Couch 10/05: 18% of AI pills were not the
             brain's choice and most of those were a different root, only 29/231 an adjacent column: random-root.)
  lat0 / q00 = FAIR exactly (identity arms: must reproduce the steer11 pilot FAIR rows byte-identically).
Rows carry this file's sha, steer10_run / rules / vs_race shas, git HEAD, the arm spec, the clock and `knob` counters.
"""
import sys, os, json, hashlib, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer10_run as S10
import steer11_run as S11
import steer8_run as S8

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
_SHA_VR = hashlib.sha256(open(os.path.join(HERE, "vs_race.py"), "rb").read()).hexdigest()[:16]
P_FIRST = 11                                    # FAIR's DRPROPHFIRST end (steer8_run SETTLE3 fD_bdepD p_first)
ANS = -6                                        # FAIR's answer shift (steer8_run fD_bdepD ans)
ARMS = {
    "lat0": dict(kind="lat", D=0),              # identity
    "lat_m2": dict(kind="lat", D=-2),
    "lat_m4": dict(kind="lat", D=-4),
    "lat_m6": dict(kind="lat", D=-6),
    "lat_ceil": dict(kind="ceil"),
    "q00": dict(kind="miss", q=0.0),            # identity
    "ex_perfect": dict(kind="perfect"),
    "ex_q05": dict(kind="miss", q=0.05),
    "ex_q10": dict(kind="miss", q=0.10),
    "ex_q15": dict(kind="miss", q=0.15),
}
for _q in (1, 2, 3, 4, 6, 8):                     # dose-calibration grid (steer12_qcal: pill overhead only)
    ARMS.setdefault(f"ex_q{_q:02d}", dict(kind="miss", q=_q / 100))


class Knob:
    """Wraps FAIR's steer_model.Steer: same interface (reset / execute / stats) for stuck_probe.play_race / play_gb."""

    def __init__(self, steer, spec, race):
        import steer_model as SM, reach_fw_tap as RFT, vs_race as V
        self.s, self.spec, self.race = steer, spec, race
        self.SM, self.RFT, self.V = SM, RFT, V
        self.x0 = list(SM.latency_samples())               # the silicon samples BEFORE FAIR's answer shift
        assert steer.lat == [max(SM.F0, x + ANS) for x in self.x0] and steer.proph_first_end == P_FIRST
        assert RFT.T_LAT == 19 and RFT.G0 == 8
        k = spec["kind"]
        if k == "lat":
            D = spec["D"]
            steer.lat = [max(SM.F0, x + ANS + D) for x in self.x0]
            steer.proph_first_end = max(SM.F0, P_FIRST + D)
            RFT.T_LAT = max(SM.F0 + 1, 19 + D)
        elif k == "ceil":
            steer.lat = [SM.F0] * len(self.x0)
            steer.proph_first_end = SM.F0
            RFT.T_LAT = SM.F0
        self.base0 = V.CLOCK["base"] if (race and V.CLOCK is not None) else None
        self.kstats = {}

    @property
    def stats(self):
        return self.s.stats

    def reset(self, seed):
        self.s.reset(seed)
        self.seed = seed
        self.kstats = {"dec": 0, "tempo_f": 0.0, "clamp": 0, "armed": 0, "miss": 0, "perfect_fallback": 0}

    def _fair_answer(self, k, armed):
        if armed:
            return P_FIRST
        n = len(self.x0)
        idx = random.Random(self.seed * 1000003 + k * 7919 + 17).randrange(n)   # == Steer._t_act pooled draw
        return max(self.SM.F0, self.x0[idx] + ANS)

    def execute(self, color, target_action, k, t_act=None, phase=None):
        SM, kind = self.SM, self.spec["kind"]
        self.kstats["dec"] += 1
        if kind == "perfect":
            var, col = target_action // 8, target_action % 8
            cs = SM.straight_cells(color, var, col)
            if cs is not None:
                st = self.s.stats; st["pills"] += 1; st["exact"] += 1
                return {"var": var, "col": col, "cells": cs, "lock_f": None, "t_act": None, "proph": None,
                        "armed": None, "clamped": False, "exact": True, "trace": None}
            self.kstats["perfect_fallback"] += 1
        if kind == "miss" and self.spec["q"] > 0:
            rng = random.Random(self.seed * 7777771 + k * 104729 + 5)
            if rng.random() < self.spec["q"]:
                mask = self.RFT.reach_mask_fw(color, SM.table_threshold(k), 2)
                alt = [a for a in range(32) if mask[a] and a != target_action
                       and SM.straight_cells(color, a // 8, a % 8) is not None]
                if alt:
                    target_action = alt[rng.randrange(len(alt))]
                    self.kstats["miss"] += 1
        ex = self.s.execute(color, target_action, k, t_act, phase)
        if kind in ("lat", "ceil"):
            armed = ex["proph"] is not None and self.s.proph_first_end is not None
            ans = self.s.proph_first_end if armed else ex["t_act"]
            d = ans - self._fair_answer(k, armed)
            self.kstats["armed"] += int(armed)
            if kind == "lat" and not armed:
                n = len(self.x0)
                idx = random.Random(self.seed * 1000003 + k * 7919 + 17).randrange(n)
                self.kstats["clamp"] += int(self.x0[idx] + ANS + self.spec["D"] < SM.F0)
            self.kstats["tempo_f"] += d
            if self.base0 is not None:
                self.V.CLOCK["base"] = self.base0 + d          # pill_frames reads it for THIS pill (called next)
        return ex


if __name__ == "__main__":
    import stuck_probe as SP, refit_opp as RO, vs_race as V
    mode, arm = sys.argv[1], sys.argv[2]
    spec = ARMS[arm]
    stamp = {"wrapper": "steer12_run.py", "sha": _SHA, "s10_sha": S11._SHA_S10, "rules_sha": S10._SHA_RULES,
             "vs_race_sha": _SHA_VR, "git": S8._git(), "arm": arm, "knob": spec, "base": S10.BASE_ARM,
             "spec": json.loads(json.dumps(S8.ARMS[S10.BASE_ARM]))}
    steer0, choose, dec = S10.make("s10_base")
    zero = lambda: {k: 0 for k in dec.stats}
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        assert V.CLOCK is None
        knob = Knob(steer0, spec, race=False)
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_gb(lo + i * step, choose, knob, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp, "rule": dict(dec.stats),
                          "knob": dict(knob.kstats)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, sizes = float(sys.argv[3]), sys.argv[4]
        lo, cnt, step, outp = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
        V.SIZES = S10.SIZES[sizes]
        V.CLOCK = S11.load_clock("couch11")
        stamp["sizes"] = sizes; stamp["clock"] = dict(V.CLOCK)
        knob = Knob(steer0, spec, race=True)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_race(lo + i * step, "s10_base", lam, level=11, steer=knob, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                r["sizes"] = sizes; r["rule"] = dict(dec.stats); r["knob"] = dict(knob.kstats)
                if knob.base0 is not None:
                    V.CLOCK["base"] = knob.base0
                fh.write(json.dumps(r) + "\n"); fh.flush()
    else:
        sys.exit(f"mode {mode}?")
