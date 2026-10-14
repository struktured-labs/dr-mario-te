"""TAPOUT study (PREREG_TAPOUT.md): STEER14's harness verbatim (steer14_run.Knob14, stuck_probe.play_race, couch11 clock,
dr. lulu at measured pace) + (1) a per-pill TRACE for characterising tap-outs and (2) DANGER root penalties as knobs.

  python tapout_run.py race ARM LAM SIZES LO CNT STEP OUT [TRACE_OUT]
  python tapout_run.py seeds ARM LAM SIZES SEEDFILE OUT TRACE_OUT      (replay listed seeds with the trace)
  python tapout_run.py gb    ARM OPPONENT LO CNT STEP OUT            (gate b guard, == steer14_run gb mode)

DANGER penalties (root-side = firmware-only, like STEER10's ereach; subtracted after DRVETO via seal_steer9's pen):
  kind "spawn": pen[a] = P * max(0, Hs(b1(a)) - h0), Hs = max column height over cols c0..c1 (default 2..5, the spawn
               throat: the pill spawns at row 0, cols 3/4) on the soft b1 of root a.
  kind "spawnq": P * max(0, Hs - h0)^2.
  gate: only when the ROOT board's Hs >= trig (0 = always).
Arms with a danger rule cannot use the anytime META check verbatim (META has no pen): the META roots' values are
penalised by the same pen[act] before the publish timeline is built; a residual mismatch (final publish != brain choice)
is COUNTED (knob.meta_pen_mismatch) and the brain's choice is appended as the final publish 0.1 f after the last one.
"""
import sys, os, json, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
from numba import njit, int8, int64
import steer14_run as S14
import steer10_run as S10
import rules_steer10 as R10
from fast_sim_x import ROWS, COLS, NCELL
from cascade_leaf6fw_braingap_20261003 import _soft_b1

# ---------------------------------------------------------------------------------------------------- danger rule
@njit(cache=True, fastmath=False)
def _hs(col, c0, c1):
    h = 0
    for c in range(c0, c1 + 1):
        for r in range(ROWS):
            if col[r * COLS + c] != 0:
                if ROWS - r > h:
                    h = ROWS - r
                break
    return h


@njit(cache=True, fastmath=False)
def _danger_pen(pcol, pvir, ca, cb, allowed, P, h0, quad, c0, c1, pen, nfire):
    sbc = np.empty(NCELL, dtype=int8); sbv = np.empty(NCELL, dtype=int8)
    for a in range(32):
        pen[a] = 0; nfire[a] = -1
        if allowed[a] == 0:
            continue
        if _soft_b1(pcol, pvir, a // 8, a % 8, ca, cb, sbc, sbv) == 0:
            continue
        h = _hs(sbc, c0, c1)
        n = h - h0 if h > h0 else 0
        if quad:
            n = n * n
        nfire[a] = n
        pen[a] = int64(P) * n


_orig_choose = R10.S10Decider.choose


def _choose(self, board, cur, nxt, k=0):
    r = self.rule
    if r.get("kind") not in ("spawn", "spawnq"):
        return _orig_choose(self, board, cur, nxt, k)
    import seal_steer9 as S9
    from cascade_link_x import board_flat
    col, vir = board_flat(board)
    lnk = np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1)
    allowed = self.mask(board, k) if self.mask_fn is None else self.mask_fn(board, k)
    w6 = self.w6_for(col, vir, cur, allowed, k)
    s = self.sw
    c0, c1 = int(r.get("c0", 2)), int(r.get("c1", 5))
    on = _hs(col, c0, c1) >= int(r.get("trig", 0))
    if on and int(r["P"]) != 0:
        _danger_pen(col, vir, cur.a, cur.b, allowed, int(r["P"]), int(r["h0"]), int(r["kind"] == "spawnq"), c0, c1,
                    self.pen, self.nfire)
    else:
        self.pen[:] = 0; self.nfire[:] = -1
    a = S9._choose_fw_seal(col, vir, lnk, cur.a, cur.b, nxt.a, nxt.b, self.topk2, self.w_excav, self.w_hang,
                           self.w, self.fl, self.maxpass, self.w_chain, self.ws, allowed, self.w5, w6,
                           int(s["veto"]), int(s["hang"]), int(s["ehb1"]), int(s["ehnp"]), int(s["wrap"]),
                           int(s["order"]), self.vals, self.pen, 0, self.act0)
    self.stats["dec"] += 1
    fired = bool((self.pen > 0).any()) and int(self.pen.max()) != int(self.pen[self.nfire >= 0].min())
    self.stats["fired"] += int(fired)
    self.stats["changed"] += int(a >= 0 and int(self.act0[0]) != a)
    self.last_pen = self.pen.copy(); self.last_a = int(a)
    return None if a < 0 else int(a)


R10.S10Decider.choose = _choose

# --------------------------------------------------------------------------------------------- arms (pre-registered)
DANGER = {   # PREREG_TAPOUT.md sec. 3 (vk 16 = A16)
    "D1": (16, dict(kind="spawn", P=60, h0=11)),
    "D2": (16, dict(kind="spawn", P=200, h0=11)),
    "D3": (16, dict(kind="spawn", P=200, h0=13)),
    "D4": (16, dict(kind="spawnq", P=40, h0=10)),
    "D5": (16, dict(kind="spawn", P=500, h0=12, trig=11)),
}
for name, (vk, rule) in DANGER.items():
    S10.RULE_ARMS[name] = dict(rule, vk=vk)
    for g in ("k32", "u8"):
        ko, ke, ve = S14.GATES[g]
        S14.ARMS[f"T_{name}_{g}"] = dict(part="B", rule=name, fw="v11", mt=6, q=0.0, ref="1488", slam=True,
                                          kopen=ko, kend=ke, vcend=ve)
# baselines under this wrapper (must reproduce the banked STEER14 rows: identity gate)
S14.ARMS["T_base_k32"] = dict(S14.ARMS["S14_d4_k32"]); S14.ARMS["T_a16_u8"] = dict(S14.ARMS["S14_d16_u8"])


# ------------------------------------------------------------------------------------------------- knob + trace
class KnobT(S14.Knob14):
    trace = None

    def reset(self, seed):
        super().reset(seed)
        self.tr = []; self.garb = []
        self.kstats["meta_pen_mismatch"] = 0

    def wrap_choose(self, choose):
        inner = super().wrap_choose(self._pen_choose(choose))
        return inner

    def _pen_choose(self, choose):
        # brain choice; META is patched (below) to see the same penalty
        def ch(env, col, vir, ctx):
            a = choose(env, col, vir, ctx)
            self._last_board = env.board
            return a
        return ch

    def execute(self, color, target_action, k, t_act=None, phase=None):
        ks = self.kstats
        before = dict(ks)
        ex = super().execute(color, target_action, k, t_act, phase)
        if self.trace is not None:
            c = np.array(color)
            hts = [int(16 - np.nonzero(c[:, j])[0].min()) if c[:, j].any() else 0 for j in range(8)]
            d = lambda key: ks.get(key, 0) - before.get(key, 0)
            cur = self.cur or {}
            self.tr.append({"k": k, "vc": cur.get("vc"), "pill": cur.get("pill"), "h": hts, "act": int(target_action),
                            "ex": ex["var"] * 8 + ex["col"], "lock_f": ex["lock_f"], "disarmed": d("disarmed"),
                            "stab": d("down_stab"), "done": d("down_done"), "nodown": d("no_down"),
                            "final": d("landed_final"), "garb_ev": d("garb_events"),
                            "board": [[int(x) for x in row] for row in c] if True else None})
            if len(self.tr) > 12:
                self.tr[-13]["board"] = None
        return ex


def _patch_meta():
    """META sees the danger penalty: roots' values minus pen[act] (pen from the brain's own decision)."""
    import anytime13 as AT
    orig = AT.Meta.run

    def run(self, dec, board, cur, nxt, k, allowed=None):
        am, roots = orig(self, dec, board, cur, nxt, k, allowed)
        b = KnobT._brain
        if b is None or b.rule.get("kind") not in ("spawn", "spawnq") or getattr(b, "last_pen", None) is None:
            return am, roots
        pen = b.last_pen
        roots = [(r[0], r[1] - int(pen[r[0]]), *r[2:]) for r in roots]
        best = None; am2 = None
        for r in roots:
            if best is None or r[1] > best:
                best = r[1]; am2 = r[0]
        if am2 != b.last_a and any(r[0] == b.last_a for r in roots):
            KnobT._live_knob.kstats["meta_pen_mismatch"] += 1
            roots = [(r[0], (best + 1) if r[0] == b.last_a else r[1], *r[2:]) for r in roots]
            am2 = b.last_a
        return am2, roots
    AT.Meta.run = run


KnobT._brain = None


def main():
    import stuck_probe as SP, vs_race as V, steer11_run as S11, steer8_run as S8, reach_fw_tap as RFT
    mode, arm = sys.argv[1], sys.argv[2]
    spec = S14.ARMS[arm]
    guard = S14.jit_guard()
    if mode == "gb":
        return main_gb(arm, spec, guard)
    lam, sizes = float(sys.argv[3]), sys.argv[4]
    if mode == "race":
        lo, cnt, step, outp = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
        seeds = [lo + i * step for i in range(cnt)]; trp = sys.argv[9] if len(sys.argv) > 9 else None
    else:
        seeds = [int(x) for x in open(sys.argv[5]).read().split()]; outp, trp = sys.argv[6], sys.argv[7]
    stamp = {"wrapper": "tapout_run.py", "s14_sha": S14._SHA, "git": S8._git(), "arm": arm, "knob": spec, "guard": guard,
             "danger": S10.RULE_ARMS.get(spec["rule"]), "numba_cache": os.environ.get("NUMBA_CACHE_DIR")}
    steer0, choose0, dec = S10.make(spec["rule"])
    KnobT._brain = dec
    _patch_meta()
    zero = lambda: {k: 0 for k in dec.stats}
    V.SIZES = S10.SIZES[sizes]; V.CLOCK = S11.load_clock("couch11")
    base = S14._meta_decider(spec["rule"])
    knob = KnobT(steer0, spec, race=True, base_dec=base)
    KnobT._live_knob = knob
    if trp:
        knob.trace = True
        # garbage sizes per pill
        og = V.garbage_drop_timed

        def gw(board, size, colours, phase, _o=og):
            knob.garb.append((len(knob.tr), int(size)))
            return _o(board, size, colours, phase)
        V.garbage_drop_timed = gw
    assert RFT.T_LAT == 19 + (spec["mt"] - 6)
    choose = knob.wrap_choose(choose0)
    use_probe = sizes == "lulu202610b"
    tf = open(trp, "w") if trp else None
    with open(outp, "w") as fh:
        for sd in seeds:
            dec.stats = zero()
            r = SP.play_race(sd, spec["rule"], lam, level=11, steer=knob,
                             probe=SP.StuckProbe() if use_probe else None, choose=choose)
            r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True; r["rig"] = stamp
            r["sizes"] = sizes; r["rule"] = dict(dec.stats); r["knob"] = dict(knob.kstats)
            if knob.base0 is not None:
                V.CLOCK["base"] = knob.base0
            fh.write(json.dumps(r) + "\n"); fh.flush()
            if tf:
                tf.write(json.dumps({"seed": sd, "arm": arm, "how": r["how"], "t_end": r["t_end"], "trace": knob.tr,
                                     "garb": knob.garb}) + "\n"); tf.flush()


def main_gb(arm, spec, guard):
    """gate b vs a pill-keyed opponent: steer14_run.py's gb branch verbatim, with this wrapper's knob/decider."""
    import stuck_probe as SP, vs_race as V, steer8_run as S8, reach_fw_tap as RFT, refit_opp as RO
    oppname, lo, cnt, step, outp = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
    assert V.CLOCK is None
    stamp = {"wrapper": "tapout_run.py", "s14_sha": S14._SHA, "git": S8._git(), "arm": arm, "knob": spec, "guard": guard,
             "danger": S10.RULE_ARMS.get(spec["rule"]), "numba_cache": os.environ.get("NUMBA_CACHE_DIR")}
    steer0, choose0, dec = S10.make(spec["rule"])
    KnobT._brain = dec
    _patch_meta()
    zero = lambda: {k: 0 for k in dec.stats}
    knob = KnobT(steer0, spec, race=False, base_dec=S14._meta_decider(spec["rule"]))
    KnobT._live_knob = knob
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


if __name__ == "__main__":
    main()
