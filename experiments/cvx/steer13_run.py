"""STEER13 (PREREG_STEER13.md): (A) stall fixes under silicon-like execution, (B) anytime-commit pricing of MIN_THINK.

  python steer13_run.py race ARM LAM SIZES LO CNT STEP OUT     (race clock couch11)
  python steer13_run.py gb   ARM OPPONENT LO CNT STEP OUT       (gate b, pill-keyed opponent)

Every arm = steer10_run.make(RULE) VERBATIM (FAIR driver/timing, rules_steer10.S10Decider) + a Knob13 around FAIR's Steer:
  PART A  kind "miss": with probability q per pill the steering target is a uniformly random OTHER root allowed by the
          shipping reach mask and legal (STEER12 ex_qNN, the same RNG key) -- RULE = s10_base | s10_A16 | s10_R60.
  PART B  kind "anytime" (RULE s10_base): the copro's live-publish schedule on the sim board (anytime13: exact firmware
          publish sequence, flat 1645 clocks/leaf timing fitted on the 1488 co-sim and validated out-of-sample on V11)
          for fw 1488 (Pass-0 order) or V11 (DRROOTORD); the driver commits at the gate GO + MT to the mailbox (waits if
          empty) and adopts later publishes under DRLATEGUARD (steer_model.execute sched); "oracle" = the final answer
          published at GO (no non-final commit). GO = FAIR's sampled answer frame - 6 (FAIR's gate is GO + 6), so
          MT 6 / 4 / 2 move the gate by 0 / -2 / -4 f (steer lat, PROPH-first end and reach-mask T_LAT shifted like
          STEER12's lat arms). Plus misses at the residual dose q (a missed pill ignores the schedule).
          RACE TEMPO (part B): + (this pill's lock frame - the REFERENCE lock frame of the same pill), via a
          state-preserving counterfactual execute. Reference = today's cart (fw 1488 anytime schedule at MT 6 under
          DRLATEGUARD, the same miss draw): couch11 was fitted on that silicon, so B_14886 is tempo-neutral by
          construction and every other arm is charged only its difference from it (ref "fair" = identity gate only).
Identity arms (must equal FAIR's banked rows): A_fair_q00 (miss q 0) and B_orc6_q00_fairref (oracle schedule at MT 6,
q 0, FAIR-direct reference). Consistency: B_14886 must charge tempo 0 on every pill (it IS the reference).
"""
import sys, os, json, hashlib, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer10_run as S10
import steer11_run as S11
import steer8_run as S8

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
_SHA_VR = hashlib.sha256(open(os.path.join(HERE, "vs_race.py"), "rb").read()).hexdigest()[:16]
_SHA_SM = hashlib.sha256(open(os.path.join(HERE, "steer_model.py"), "rb").read()).hexdigest()[:16]
_SHA_AT = hashlib.sha256(open(os.path.join(HERE, "anytime13.py"), "rb").read()).hexdigest()[:16]
P_FIRST, ANS = 11, -6
QB = 0.0                                              # PREREG_STEER13: residual miss dose for part B (steer13/cal/qb.txt: the rule outputs 0)


def _arms():
    A = {}
    for q in (0, 2, 3, 4):
        for r, lab in (("s10_base", "fair"), ("s10_A16", "a16"), ("s10_R60", "r60")):
            A[f"A_{lab}_q{q:02d}"] = dict(part="A", rule=r, q=q / 100)
    for fw in ("1488", "v11", "orc"):
        for mt in (6, 4, 2):
            for q in (0, 2, 3, 4):
                A[f"B_{fw}{mt}_q{q:02d}"] = dict(part="B", rule="s10_base", fw=fw, mt=mt, q=q / 100, ref="1488")
            if QB is not None:
                A[f"B_{fw}{mt}_qb"] = dict(part="B", rule="s10_base", fw=fw, mt=mt, q=QB, ref="1488")
    A["B_orc6_q00_fairref"] = dict(part="B", rule="s10_base", fw="orc", mt=6, q=0.0, ref="fair")   # identity gate only
    return A


ARMS = _arms()


class Knob13:
    def __init__(self, steer, spec, race, base_dec=None):
        import steer_model as SM, reach_fw_tap as RFT, vs_race as V
        self.s, self.spec, self.race, self.SM, self.RFT, self.V = steer, spec, race, SM, RFT, V
        self.x0 = list(SM.latency_samples())
        assert steer.lat == [max(SM.F0, x + ANS) for x in self.x0] and steer.proph_first_end == P_FIRST
        assert RFT.T_LAT == 19 and RFT.G0 == 8
        self.D = spec["mt"] - 6 if spec["part"] == "B" else 0
        if self.D:
            steer.lat = [max(SM.F0, x + ANS + self.D) for x in self.x0]
            steer.proph_first_end = max(SM.F0, P_FIRST + self.D)
            RFT.T_LAT = max(SM.F0 + 1, 19 + self.D)
        self.lat_arm, self.pfe_arm = list(steer.lat), steer.proph_first_end
        self.lat_fair = [max(SM.F0, x + ANS) for x in self.x0]
        self.base0 = V.CLOCK["base"] if (race and V.CLOCK is not None) else None
        self.base_dec = base_dec
        self.pending = None
        self.pending_ref = None
        self.kstats = {}

    @property
    def stats(self):
        return self.s.stats

    def reset(self, seed):
        self.s.reset(seed)
        self.seed = seed
        self.kstats = {"dec": 0, "miss": 0, "nonfinal_commit": 0, "late": 0, "adopt": 0, "refuse": 0, "wait_f": 0,
                       "tempo_f": 0.0, "landed_final": 0, "meta_mismatch": 0}

    def wrap_choose(self, choose):
        """part B: after the brain's choice, the anytime meta on the same board (identity-checked vs the choice)"""
        import anytime13 as AT
        meta = AT.Meta()
        coef = json.load(open(os.path.join(HERE, "steer13", "anytime_coef.json")))

        def ch(env, col, vir, ctx):
            a = choose(env, col, vir, ctx)
            self.pending = None
            if a is None or self.spec["part"] != "B":
                return a
            fw = self.spec["fw"]
            self.pending_ref = None
            if fw == "orc" and self.spec["ref"] != "1488":
                self.pending = [(0.0, a)]
                return a
            am, roots = meta.run(self.base_dec, env.board, env.cur, env.nxt, env.pills_placed)
            if am != a:
                self.kstats["meta_mismatch"] += 1
                raise RuntimeError(f"anytime meta final {am} != brain choice {a} (seed {self.seed}, k {env.pills_placed})")
            self.pending = [(0.0, a)] if fw == "orc" else AT.publishes(roots, fw, coef)
            self.pending_ref = AT.publishes(roots, "1488", coef)
            return a
        return ch

    def _miss(self, color, target_action, k):
        SM = self.SM
        q = self.spec["q"]
        if q <= 0:
            return None
        rng = random.Random(self.seed * 7777771 + k * 104729 + 5)            # == steer12_run.Knob (same draws)
        if rng.random() < q:
            mask = self.RFT.reach_mask_fw(color, SM.table_threshold(k), 2)
            alt = [a for a in range(32) if mask[a] and a != target_action and SM.straight_cells(color, a // 8, a % 8) is not None]
            if alt:
                self.kstats["miss"] += 1
                return alt[rng.randrange(len(alt))]
        return None

    def execute(self, color, target_action, k, t_act=None, phase=None):
        SM, s = self.SM, self.s
        self.kstats["dec"] += 1
        alt = self._miss(color, target_action, k)
        if self.spec["part"] == "A":
            ex = s.execute(color, alt if alt is not None else target_action, k, t_act, phase)
            self.kstats["landed_final"] += int(ex["var"] * 8 + ex["col"] == target_action)
            return ex
        # ---- part B
        n = len(self.x0)
        x = self.x0[random.Random(self.seed * 1000003 + k * 7919 + 17).randrange(n)]   # == Steer._t_act pooled draw
        GO = x + ANS - 6
        mk = lambda pubs: [(int(math.ceil(GO + t - 1e-9)), a) for t, a in pubs]
        # the REFERENCE execution of this pill at FAIR's gate (MT 6), state-preserving:
        #   ref "1488": today's cart = the fw-1488 anytime schedule under DRLATEGUARD (the couch11 clock was fitted on
        #               this silicon, so B_14886's own tempo is 0 by construction); a missed pill misses there too
        #   ref "fair": the final answer executed directly (identity gate only)
        sv = (s.v, s.v_at_lock, dict(s.stats), s.lat, s.proph_first_end)
        s.lat, s.proph_first_end = self.lat_fair, P_FIRST
        if self.spec["ref"] == "1488" and alt is None:
            ref = s.execute(color, target_action, k, sched=mk(self.pending_ref))
        else:
            ref = s.execute(color, alt if (alt is not None and self.spec["ref"] == "1488") else target_action, k)
        s.v, s.v_at_lock, s.stats, s.lat, s.proph_first_end = sv[0], sv[1], sv[2], sv[3], sv[4]
        if alt is not None:
            ex = s.execute(color, alt, k, t_act, phase)
        else:
            pubs = self.pending or [(0.0, target_action)]
            assert pubs[-1][1] == target_action
            ex = s.execute(color, target_action, k, t_act, phase, sched=mk(pubs))
            lg = ex["lg"]
            ks = self.kstats
            ks["nonfinal_commit"] += int(lg["commit_a"] != target_action)
            ks["late"] += lg["late"]; ks["adopt"] += lg["adopt"]; ks["refuse"] += lg["refuse"]
            ks["wait_f"] += max(0, (lg["commit_f"] or 0) - max(SM.F0, x + ANS + self.D)) if not ex["proph"] else 0
        self.kstats["landed_final"] += int(ex["var"] * 8 + ex["col"] == target_action)
        d = (ex["lock_f"] or 0) - (ref["lock_f"] or 0)
        self.kstats["tempo_f"] += d
        if self.base0 is not None:
            self.V.CLOCK["base"] = self.base0 + d
        return ex


if __name__ == "__main__":
    import stuck_probe as SP, refit_opp as RO, vs_race as V
    import rules_steer10 as R10
    mode, arm = sys.argv[1], sys.argv[2]
    spec = ARMS[arm]
    stamp = {"wrapper": "steer13_run.py", "sha": _SHA, "s10_sha": S11._SHA_S10, "rules_sha": S10._SHA_RULES,
             "vs_race_sha": _SHA_VR, "steer_model_sha": _SHA_SM, "anytime_sha": _SHA_AT, "git": S8._git(), "arm": arm,
             "knob": spec, "base": S10.BASE_ARM, "spec": json.loads(json.dumps(S8.ARMS[S10.BASE_ARM]))}
    steer0, choose0, dec = S10.make(spec["rule"])
    zero = lambda: {k: 0 for k in dec.stats}
    probe = (lambda: SP.StuckProbe()) if spec["part"] == "A" else (lambda: None)
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        assert V.CLOCK is None
        knob = Knob13(steer0, spec, race=False, base_dec=R10.base_decider() if spec["part"] == "B" else None)
        choose = knob.wrap_choose(choose0)
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_gb(lo + i * step, choose, knob, opp, probe=probe())
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp, "rule": dict(dec.stats),
                          "knob": dict(knob.kstats)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, sizes = float(sys.argv[3]), sys.argv[4]
        lo, cnt, step, outp = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
        V.SIZES = S10.SIZES[sizes]
        V.CLOCK = S11.load_clock("couch11")
        stamp["sizes"] = sizes; stamp["clock"] = dict(V.CLOCK)
        knob = Knob13(steer0, spec, race=True, base_dec=R10.base_decider() if spec["part"] == "B" else None)
        choose = knob.wrap_choose(choose0)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_race(lo + i * step, spec["rule"], lam, level=11, steer=knob, probe=probe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                r["sizes"] = sizes; r["rule"] = dict(dec.stats); r["knob"] = dict(knob.kstats)
                if knob.base0 is not None:
                    V.CLOCK["base"] = knob.base0
                fh.write(json.dumps(r) + "\n"); fh.flush()
    else:
        sys.exit(f"mode {mode}?")
