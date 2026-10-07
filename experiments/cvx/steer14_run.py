"""STEER14 (PREREG_STEER14.md): the combined candidate under a CART-FAITHFUL descent model.
STEER13's anytime-commit model started the soft drop the moment the capsule was aligned after the commit. The cart does
not: its DRSLAM gate (patch_cartridge_copro.py dn_p2, FAIR / FAIR2PLUS flags KOPEN 32, KEND 255, KCROSS 8, LOWY 8,
VCEND 10, MATURE 2) holds DOWN until the search is DONE or the published answer has been stable for K hooks
(steer_model.execute(slam=...); validated on the a16-mt-build lane's chained Mesen replays, steer14_slamcal.py).
So MIN_THINK is dropped and the factor is the slam gate's KOPEN:
  2x2 = {DIST gate vk 4 (today), 16 (A16)} x {KOPEN 32 (today), KOPEN cut}, fw V11, MIN_THINK 6 f, + a q 2 % sensitivity
  pair for the combined contrast, a KOPEN dose-response (DIST4), and STEER13's V11-vs-1488 re-derived (C13_* arms).

  python steer14_run.py race ARM LAM SIZES LO CNT STEP OUT     (race clock couch11)
  python steer14_run.py gb   ARM OPPONENT LO CNT STEP OUT       (gate b, pill-keyed opponent)
  python steer14_run.py guard                                   (the stale-JIT worker guard alone)

Every arm = steer13_run's part-B machinery (steer10_run.make(RULE) brain + FAIR driver; anytime13 publish schedule;
commit at GO + MT, later publishes under DRLATEGUARD; race tempo = this pill's lock frame - the lock frame of the same
pill under TODAY's cart; misses at dose q) with Knob14 adding the CART'S SLAM GATE to the arm and to the reference:
  - DONE: done_f = BETA x leaves(fw) + eps (steer14_donecal.py, steer14/done_model.json; eps drawn from the 1488 co-sim
    residuals of the pill's vcount band, keyed by (seed, pill): common to the arm and the reference); never before the
    final publish. The gate opens at frame ceil(GO + done_f).
  - SLAM_ARM (DRSLAM_MATURE + DRABORTSTALE): 0 on a match's first pill; 0 on a pill whose PREVIOUS pill locked while its
    search was still running at this pill's edge, i.e. GO + done_f > lock + gap, gap = max(12, 24 - ROM Y of the
    landing) + 20.2 f/clear step + 15.9 f/cascade fall row (+ the garbage-drop frames before this pill, race only);
    otherwise 1 (steer14_slamcal: 585/585 traced pills).
  - the reference (today's cart) = fw 1488, MIN_THINK 6 f, KOPEN 32, with its own SLAM_ARM chain.
  - a missed pill (q > 0) steers to its random root on the gate's terms: published at the arm's first publish frame.
  - RULE s10_A16: the anytime META decider is rules_steer10.make(vk=16) (it must reproduce the brain's choice).
  - stuck_probe.StuckProbe runs on every LULU-race row (stall metrics).
Identity: arm S14_id_v116 (slam OFF) must equal STEER13's B_v116_qb rows on every key but stamps and the probe.
WORKER GUARD (numba stale-cache): every process plays jit_guard() before its first game (decider answers on 150 fixed
boards; sha == GUARD_SHA, recorded on two fresh caches; killed-mutant checked by steer14_guard_mutants.py); exit 5 on
failure before any row. The guard result is stamped into every row (rig.guard).
"""
import sys, os, json, hashlib, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import steer10_run as S10
import steer11_run as S11
import steer8_run as S8
import steer13_run as S13

HERE = os.path.dirname(os.path.abspath(__file__))
_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()[:16]
_SHA_SM = hashlib.sha256(open(os.path.join(HERE, "steer_model.py"), "rb").read()).hexdigest()[:16]
GUARD_SHA = "064752972d064a89"   # PREREG_STEER14 sec. 2: two independent FRESH-cache guard runs (nb_desk_guard1/2)
GUARD_LEVELS = (0, 1, 2, 3, 5)   # 4 / 8 / 12 / 16 / 24 viruses
GUARD_SEEDS = tuple(range(9000, 9060, 2))      # boards only (no game is played or scored on them)
KOPEN_TODAY, KEND, KCROSS, LOWY, VCEND = 32, 255, 8, 8, 10     # FAIR / FAIR2PLUS cart flags (cart build logs)
GAP_BASE, GAP_FLOOR = 24, 12                                    # lock -> next edge, no clear: max(12, 24 - ROM Y)
KOPENS = (32, 24, 16, 8, 4)


def _arms():
    A = {"S14_id_v116": dict(part="B", rule="s10_base", fw="v11", mt=6, q=0.0, ref="1488", slam=False, kopen=None)}
    for d, rule in ((4, "s10_base"), (16, "s10_A16")):
        for k in KOPENS:
            for q in (0, 2):
                A[f"S14_d{d}_k{k}" + ("" if q == 0 else f"_q{q:02d}")] = dict(
                    part="B", rule=rule, fw="v11", mt=6, q=q / 100, ref="1488", slam=True, kopen=k)
    A["CAL_d4_k32_mt2"] = dict(part="B", rule="s10_base", fw="v11", mt=2, q=0.0, ref="1488", slam=True, kopen=32)
    #   ^ calibration only (steer14_cal_read.py): the model's MIN_THINK 2 f lock-frame change must be ~0, as on the cart
    for fw in ("1488", "v11"):                                  # STEER13's V11-vs-1488 under the slam gate
        A[f"C13_{'14886' if fw == '1488' else 'v116'}"] = dict(part="B", rule="s10_base", fw=fw, mt=6, q=0.0, ref="1488",
                                                               slam=True, kopen=KOPEN_TODAY)
    return A


ARMS = _arms()


def _meta_decider(rule):
    import rules_steer10 as R10
    return R10.base_decider() if rule == "s10_base" else R10.make(dict(S10.RULE_ARMS[rule]))


def jit_guard(verbose=False):
    """Returns the guard summary dict; raises SystemExit(5) on any failed check."""
    import rules_steer10 as R10, anytime13 as AT
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    b4, b16 = R10.make(dict()), R10.make(dict(vk=16))
    m4, m16 = _meta_decider("s10_base"), _meta_decider("s10_A16")
    meta = AT.Meta()
    ans = []; bad = []; mid_diff = 0; mid_n = 0; out_diff = 0
    for lev in GUARD_LEVELS:
        for s in GUARD_SEEDS:
            env = FaithfulDrMarioEnv(level=lev, seed=s, max_pills=10); env.reset()
            NesPillSource(seed=s).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
            nv = int(env.board.virus_count())
            a4 = b4.choose(env.board, env.cur, env.nxt, k=0); a16 = b16.choose(env.board, env.cur, env.nxt, k=0)
            f4 = meta.run(m4, env.board, env.cur, env.nxt, 0)[0]; f16 = meta.run(m16, env.board, env.cur, env.nxt, 0)[0]
            ans.append((lev, s, nv, a4, a16, f4, f16))
            if f4 != a4 or f16 != a16:
                bad.append(("meta", lev, s, a4, f4, a16, f16))
            if 5 <= nv <= 16:
                mid_n += 1; mid_diff += int(a4 != a16)
            elif a4 != a16:
                out_diff += 1; bad.append(("gate", lev, s, nv, a4, a16))
    sha = hashlib.sha256(json.dumps(ans).encode()).hexdigest()[:16]
    g = {"boards": len(ans), "mid_n": mid_n, "mid_diff": mid_diff, "out_diff": out_diff, "meta_bad": len(bad),
         "sha": sha, "expect": GUARD_SHA}
    ok = not bad and mid_diff > 0 and (GUARD_SHA is None or sha == GUARD_SHA)
    if verbose:
        print(json.dumps(g))
    if not ok:
        sys.stderr.write(f"STEER14 JIT GUARD FAIL {g} {bad[:3]}\n")
        raise SystemExit(5)
    return g


class Knob14(S13.Knob13):
    """Knob13 + the cart's slam gate (arm and reference) + the DONE model + the SLAM_ARM chains (module doc)."""

    def __init__(self, steer, spec, race, base_dec):
        super().__init__(steer, spec, race, base_dec=base_dec)
        self.slam_on = bool(spec.get("slam"))
        dm = json.load(open(os.path.join(HERE, "steer14", "done_model.json")))
        self.beta, self.bands, self.pools = dm["beta"], [tuple(b) for b in dm["bands"]], dm["pools"]
        self.clk = json.load(open(os.path.join(HERE, "steer11", "clock_couch11.json")))
        self.garb_f = 0.0
        if race:                                       # garbage-drop frames between pills (the gap before the next edge)
            V = self.V
            if not getattr(V, "_steer14_wrapped", False):
                orig = V.garbage_drop_timed

                def wrapped(board, size, colours, phase, _orig=orig):
                    combo, fr = _orig(board, size, colours, phase)
                    k = Knob14._live
                    if k is not None and k.slam_on:
                        k.garb_f += fr; k.kstats["garb_events"] += 1
                    return combo, fr
                V.garbage_drop_timed = wrapped
                V._steer14_wrapped = True
        Knob14._live = self

    _live = None

    def reset(self, seed):
        super().reset(seed)
        if self.slam_on:
            self.kstats.update({"disarmed": 0, "ref_disarmed": 0, "down_done": 0, "down_stab": 0, "no_down": 0,
                                "garb_events": 0})
        self.prev = None          # (arm: done_m, lock_m, Y) of the previous pill
        self.prev_ref = None
        self.prev_land = None     # (board clone before the previous pill, cells, var, colours) for its clear count
        self.garb_f = 0.0
        self.cur = None

    def wrap_choose(self, choose):
        import anytime13 as AT
        import steer14_donecal as DC
        meta = AT.Meta()
        coef = json.load(open(os.path.join(HERE, "steer13", "anytime_coef.json")))

        def ch(env, col, vir, ctx):
            a = choose(env, col, vir, ctx)
            self.pending = None
            if a is None:
                return a
            fw = self.spec["fw"]
            am, roots = meta.run(self.base_dec, env.board, env.cur, env.nxt, env.pills_placed)
            if am != a:
                self.kstats["meta_mismatch"] += 1
                raise RuntimeError(f"anytime meta final {am} != brain choice {a} (seed {self.seed}, k {env.pills_placed})")
            self.pending = AT.publishes(roots, fw, coef)
            self.pending_ref = AT.publishes(roots, "1488", coef)
            if self.slam_on:
                vc = int(env.board.virus_count())
                bi = next(i for i, (lo, hi) in enumerate(self.bands) if lo <= vc <= hi)
                pool = self.pools[str(bi)]
                eps = pool[random.Random(self.seed * 1000033 + int(env.pills_placed) * 7907 + 91).randrange(len(pool))]
                d_arm = max(self.beta * DC.leaves(roots, fw) + eps, self.pending[-1][0] + 0.1)
                d_ref = max(self.beta * DC.leaves(roots, "1488") + eps, self.pending_ref[-1][0] + 0.1)
                self.cur = {"vc": vc, "done": d_arm, "done_ref": d_ref, "board": env.board.clone(),
                            "pill": (int(env.cur.a), int(env.cur.b))}
            return a
        return ch

    # ------------------------------------------------------------------------------------------------ helpers
    def _gap_prev(self):
        """frames from the previous pill's lock to this pill's edge (module doc) for the arm's landing"""
        import vs_race as V
        from drmario.faithful_game import LINK_UP, LINK_DOWN, LINK_LEFT, LINK_RIGHT
        B, cells, var, (pa, pb) = self.prev_land
        B = B.clone()
        first, second = (pa, pb) if var in (0, 2) else (pb, pa)
        for (r, c), colr, ln in ((cells[0], first, LINK_RIGHT if var < 2 else LINK_DOWN),
                                 (cells[1], second, LINK_LEFT if var < 2 else LINK_UP)):
            if r >= 0:
                B.color[r, c] = colr; B.link[r, c] = ln; B.is_virus[r, c] = False
        falls = V._cascade_falls(B)
        return self.clk["step"] * len(falls) + self.clk["cfall"] * sum(falls) + self.garb_f

    def _armed(self, prev, k, clr):
        if k == 0 or prev is None:
            return False                                   # a match's first pill starts disarmed
        done_m, lock_m, Y = prev
        return not (done_m > lock_m + max(GAP_FLOOR, GAP_BASE - Y) + clr)

    def _slam(self, done_frame, armed, vc, kopen):
        return {"done": done_frame, "armed": armed, "vc": vc, "kopen": kopen, "kend": KEND, "kcross": KCROSS,
                "lowy": LOWY, "vcend": VCEND}

    @staticmethod
    def _Y(ex):
        return 15 - max(ex["cells"][0][0], ex["cells"][1][0])

    def execute(self, color, target_action, k, t_act=None, phase=None):
        if not self.slam_on:
            return super().execute(color, target_action, k, t_act, phase)
        SM, s = self.SM, self.s
        ks = self.kstats
        ks["dec"] += 1
        alt = self._miss(color, target_action, k)
        n = len(self.x0)
        x = self.x0[random.Random(self.seed * 1000003 + k * 7919 + 17).randrange(n)]   # == Steer._t_act pooled draw
        GO = x + S13.ANS - 6
        mk = lambda pubs: [(int(math.ceil(GO + t - 1e-9)), a) for t, a in pubs]
        cur = self.cur
        clr = self._gap_prev() if self.prev_land is not None else 0.0
        armed = self._armed(self.prev, k, clr)
        armed_ref = self._armed(self.prev_ref, k, clr)
        ks["disarmed"] += int(not armed); ks["ref_disarmed"] += int(not armed_ref)
        dn = int(math.ceil(GO + cur["done"] - 1e-9)); dn_ref = int(math.ceil(GO + cur["done_ref"] - 1e-9))
        pubs = self.pending or [(0.0, target_action)]
        assert pubs[-1][1] == target_action
        sched = mk(pubs) if alt is None else [(mk(pubs)[0][0], alt)]
        sched_ref = mk(self.pending_ref) if alt is None else [(mk(self.pending_ref)[0][0], alt)]
        # the REFERENCE execution of this pill = today's cart (fw 1488, MIN_THINK 6 f, KOPEN 32), state-preserving
        sv = (s.v, s.v_at_lock, dict(s.stats), s.lat, s.proph_first_end)
        s.lat, s.proph_first_end = self.lat_fair, S13.P_FIRST
        ref = s.execute(color, target_action if alt is None else alt, k, sched=sched_ref,
                        slam=self._slam(dn_ref, armed_ref, cur["vc"], KOPEN_TODAY))
        s.v, s.v_at_lock, s.stats, s.lat, s.proph_first_end = sv[0], sv[1], sv[2], sv[3], sv[4]
        ex = s.execute(color, target_action if alt is None else alt, k, t_act, phase, sched=sched,
                       slam=self._slam(dn, armed, cur["vc"], self.spec["kopen"]))
        lg = ex["lg"]
        if alt is None:
            ks["nonfinal_commit"] += int(lg["commit_a"] != target_action)
            ks["late"] += lg["late"]; ks["adopt"] += lg["adopt"]; ks["refuse"] += lg["refuse"]
            ks["wait_f"] += max(0, (lg["commit_f"] or 0) - max(SM.F0, x + S13.ANS + self.D)) if not ex["proph"] else 0
        df = ex["slam"]["down_f"]
        if df is None:
            ks["no_down"] += 1
        else:
            ks["down_done"] += int(df >= dn); ks["down_stab"] += int(df < dn)
        ks["landed_final"] += int(ex["var"] * 8 + ex["col"] == target_action)
        d = (ex["lock_f"] or 0) - (ref["lock_f"] or 0)
        ks["tempo_f"] += d
        if self.base0 is not None:
            self.V.CLOCK["base"] = self.base0 + d
        self.prev = (GO + cur["done"], ex["lock_f"] or 0, self._Y(ex))
        self.prev_ref = (GO + cur["done_ref"], ref["lock_f"] or 0, self._Y(ref))
        self.prev_land = (cur["board"], ex["cells"], ex["var"], cur["pill"])
        self.garb_f = 0.0
        return ex


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "guard":
        jit_guard(verbose=True)
        sys.exit(0)
    import stuck_probe as SP, refit_opp as RO, vs_race as V
    import reach_fw_tap as RFT
    arm = sys.argv[2]
    spec = ARMS[arm]
    guard = jit_guard()
    stamp = {"wrapper": "steer14_run.py", "sha": _SHA, "s13_sha": S13._SHA, "s10_sha": S11._SHA_S10,
             "rules_sha": S10._SHA_RULES, "vs_race_sha": S13._SHA_VR, "steer_model_sha": _SHA_SM,
             "anytime_sha": S13._SHA_AT, "git": S8._git(), "arm": arm, "knob": spec, "base": S10.BASE_ARM,
             "spec": json.loads(json.dumps(S8.ARMS[S10.BASE_ARM])), "guard": guard,
             "numba_cache": os.environ.get("NUMBA_CACHE_DIR")}
    steer0, choose0, dec = S10.make(spec["rule"])
    zero = lambda: {k: 0 for k in dec.stats}
    if mode == "gb":
        oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        assert V.CLOCK is None
        knob = Knob14(steer0, spec, race=False, base_dec=_meta_decider(spec["rule"]))
        assert RFT.T_LAT == 19 + (spec["mt"] - 6)
        choose = knob.wrap_choose(choose0)
        opp = RO.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_gb(lo + i * step, choose, knob, opp, probe=None)
                r.update({"arm": f"{arm}@{oppname}", "model": oppname, "trate": 0.0, "rig": stamp, "rule": dict(dec.stats),
                          "knob": dict(knob.kstats)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        lam, sizes = float(sys.argv[3]), sys.argv[4]
        lo, cnt, step, outp = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
        V.SIZES = S10.SIZES[sizes]
        V.CLOCK = S11.load_clock("couch11")
        stamp["sizes"] = sizes; stamp["clock"] = dict(V.CLOCK)
        knob = Knob14(steer0, spec, race=True, base_dec=_meta_decider(spec["rule"]))
        assert RFT.T_LAT == 19 + (spec["mt"] - 6)
        choose = knob.wrap_choose(choose0)
        use_probe = sizes == "lulu202610b" and arm != "S14_id_v116"
        stamp["probe"] = use_probe
        with open(outp, "w") as fh:
            for i in range(cnt):
                dec.stats = zero()
                r = SP.play_race(lo + i * step, spec["rule"], lam, level=11, steer=knob,
                                 probe=SP.StuckProbe() if use_probe else None, choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
                r["sizes"] = sizes; r["rule"] = dict(dec.stats); r["knob"] = dict(knob.kstats)
                if knob.base0 is not None:
                    V.CLOCK["base"] = knob.base0
                fh.write(json.dumps(r) + "\n"); fh.flush()
    else:
        sys.exit(f"mode {mode}?")
