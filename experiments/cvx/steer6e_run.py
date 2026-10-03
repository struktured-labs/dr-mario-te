"""STEER6e (PREREG_STEER6e.md): the 2026-10-03 couch "comboing instead of clearing" fix screen.

ANTIBODY_DIST (s6_dist_target60) + ROOT-GATED switches at root viruses <= 4 (firmware-side state, like DIST's own gate):
  s6e_chain0  w_chain 540 -> 0                    (the owner's hypothesis: CHAIN540 outbids finishing)
  s6e_fin     w_chain -> 0 AND w_excav, w_hang -> 0  (the measured mechanism: CHAIN + the root EXCAV term, which pays
              +96 for leaving a same-colour 2-stack on a virus instead of finishing it)
  s6_dist_target60  identity arm (must reproduce the banked STEER6 screen rows exactly)

  python steer6e_run.py gb ARM LO CNT STEP OUT.jsonl        # gate (b) OWNER-0804, unified tap steering, stuck probe
  python steer6e_run.py race ARM LO CNT STEP OUT.jsonl      # vs_race lam 6, unified tap steering, stuck probe
  python steer6e_run.py guard ARM                           # stale-JIT / wiring guard on banked couch endgame boards
Rows match stuck_probe.py's (same play_gb / play_race), labelled ARM@owner0804 / ARM~steer.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()

GATES = {
    "s6_dist_target60": dict(chain=False, exh=False),
    "s6e_chain0": dict(chain=True, exh=False),
    "s6e_fin": dict(chain=True, exh=True),
}
VK = 4


def make_decider(arm):
    import fast_rtl_x as FX
    import cascade_chain_x as C
    import cascade_leaf6_x as L6
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    g = GATES[arm]

    class Gated(L6.Leaf6Decider):
        def choose(self, board, cur, nxt, k=0):
            nv = int(board.virus_count())
            on = nv <= VK
            sv = (self.w_chain, self.w_excav, self.w_hang)
            if on and g["chain"]:
                self.w_chain = 0
            if on and g["exh"]:
                self.w_excav = 0; self.w_hang = 0
            try:
                return super().choose(board, cur, nxt, k)
            finally:
                self.w_chain, self.w_excav, self.w_hang = sv

    return Gated(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)


def _guard(arm):
    """The variant must differ from DIST60 on banked couch endgame boards (else the wiring/JIT is stale), and the
    baseline must reproduce the banked DIST60 choices."""
    import numpy as np
    from drmario.faithful_game import FaithfulBoard, Pill
    cases = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "couch_forensics",
                         "cases_dist60_20261003.jsonl")
    R = [json.loads(l) for l in open(cases)]
    R = [q for q in R if q["virus_count"] <= VK]
    base = make_decider("s6_dist_target60"); var = make_decider(arm)
    n = diff = 0
    for q in R:
        b = FaithfulBoard(16, 8)
        b.color = np.array([int(c) for c in q["S"]["color"]], np.int8).reshape(16, 8)
        b.is_virus = np.array([c == "1" for c in q["S"]["virus"]], bool).reshape(16, 8)
        b.link = np.array([int(c) for c in q["S"]["link"]], np.int8).reshape(16, 8)
        a0 = base.choose(b.clone(), Pill(*q["cur"]), Pill(*q["nxt"]), q["p"])
        a1 = var.choose(b.clone(), Pill(*q["cur"]), Pill(*q["nxt"]), q["p"])
        n += 1; diff += int(a0 != a1)
        assert a0 == q["dist_action"], "baseline decider != banked DIST60 choice"
    print(f"guard {arm}: differs from DIST60 on {diff}/{n} banked couch endgame boards")
    if arm == "s6_dist_target60":
        assert diff == 0
    else:
        assert diff > 0, "variant identical to baseline on every endgame board: stale JIT or broken gate"


class EndgameTracker:
    """Wraps choose(): per game, the first decision with root viruses <= 4 (k4, t4) and == 1 (k1, t1), and at every
    <= 4 decision whether a root move FINISHES the firmware target / reduces its D, and whether the brain's choice does.
    Observation only (clones the board); the action returned is the decider's, unchanged."""

    def __init__(self, dec):
        self.dec = dec; self.reset()

    def reset(self):
        self.s = {"k4": None, "t4": None, "k1": None, "t1": None, "dec4": 0, "fin_avail": 0, "fin_taken": 0,
                  "dred_avail": 0, "dred_taken": 0}

    def __call__(self, env, col, vir, ctx):
        import numpy as np
        from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
        import cascade_leaf6_x as L6
        if env.pills_placed == 0:
            self.reset()
        b = env.board; nv = int(b.virus_count())
        a = self.dec.choose(b, env.cur, env.nxt, k=env.pills_placed)
        if 1 <= nv <= VK and a is not None:
            s = self.s
            if s["k4"] is None:
                s["k4"], s["t4"] = env.pills_placed, round(float(ctx["own_t"]), 2)
            if nv == 1 and s["k1"] is None:
                s["k1"], s["t1"] = env.pills_placed, round(float(ctx["own_t"]), 2)
            s["dec4"] += 1
            c8 = np.ascontiguousarray(b.color, dtype=np.int8).reshape(-1)
            v8 = np.ascontiguousarray(b.is_virus, dtype=np.int8).reshape(-1)
            d = np.empty(128, np.int64); L6._root_dists(c8, v8, 16, d, 0)
            t = -1
            for i in range(128):
                if d[i] >= 0 and (t < 0 or d[i] < d[t]):
                    t = i
            tr, tc, d0 = t // 8, t % 8, int(d[t])
            fin = dred = False; fin_c = dred_c = False
            for act in range(32):
                var, c = act // 8, act % 8
                pa, pb = int(env.cur.a), int(env.cur.b)
                o = ORIENT_H if var < 2 else ORIENT_V
                p = Pill(pa, pb) if var in (0, 2) else Pill(pb, pa)
                bb = b.clone()
                if not bb.place_pill(p, o, c):
                    continue
                bb.resolve()
                gone = not bb.is_virus[tr, tc]
                if gone:
                    red = True
                else:
                    c2 = np.ascontiguousarray(bb.color, dtype=np.int8).reshape(-1)
                    v2 = np.ascontiguousarray(bb.is_virus, dtype=np.int8).reshape(-1)
                    d2 = np.empty(128, np.int64); L6._root_dists(c2, v2, 16, d2, 0)
                    red = int(d2[t]) < d0
                fin |= gone; dred |= red
                if act == a:
                    fin_c, dred_c = gone, red
            s["fin_avail"] += int(fin); s["fin_taken"] += int(fin and fin_c)
            s["dred_avail"] += int(dred); s["dred_taken"] += int(dred and dred_c)
        return a


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "guard":
        _guard(sys.argv[2]); sys.exit(0)
    import steer_model as SM
    import stuck_probe as SP
    arm, lo, cnt, step, outp = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    _guard(arm)
    dec = make_decider(arm)
    choose = EndgameTracker(dec)
    steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
    with open(outp, "w") as fh:
        if mode == "gb":
            import opp_run as OR
            opp = OR.make_opponent("owner0804")
            for i in range(cnt):
                r = SP.play_gb(lo + i * step, choose, steer, opp, probe=SP.StuckProbe())
                r.update({"arm": f"{arm}@owner0804", "model": "owner0804", "trate": 0.0, "eg": dict(choose.s)})
                fh.write(json.dumps(r) + "\n"); fh.flush()
        elif mode == "race":
            for i in range(cnt):
                r = SP.play_race(lo + i * step, arm, 6.0, level=11, steer=steer, probe=SP.StuckProbe(), choose=choose)
                r["arm"] = arm + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True
                r["eg"] = dict(choose.s)
                fh.write(json.dumps(r) + "\n"); fh.flush()
