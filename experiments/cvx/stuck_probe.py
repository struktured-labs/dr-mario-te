"""STEER6 phase 2: the STUCK-VIRUS instrument on the steering-on sim.

For every decision it asks, for each virus still on the board: does ANY legal straight-drop placement clear it
(place + faithful resolve, cascades included)? Three notions of "clearing move exists":
  str   STRUCTURAL: with ANY pill colour pair (all 6 unordered pairs x 32 actions). A virus that is str-stuck needs
        the BOARD to change before any pill can clear it -- the couch "sealed" case.
  act   with the ACTUAL current pill (the coordinator's / linger_cell.py definition).
  mask  with the actual pill AND inside the shipping reach mask (reach_fw_tap, tap 2): what the couch driver can do.
A virus's counter = consecutive decisions without a clearing move. An EPISODE is a maximal run; it ends when a
clearing move exists again, or the virus is gone, or the game ends (censored). Episodes >= 10 decisions are kept.
End attribution (str only):
  cleared_own / cleared_garbage   virus vanished during the AI's placement / during a garbage drop (cascade);
  unlocked_own                    clearable again, and the board right after the AI's placement (before any garbage)
                                  was already structurally clearable -> the AI's own pill changed the board;
  unlocked_garbage                only the garbage drop made it clearable;
  end_<how>                       the game ended with the virus still stuck (censored).
The probe only CLONES boards: trajectories are byte-identical to the uninstrumented runners (identity gate below).

  python stuck_probe.py gb BUILD OPPONENT LO CNT STEP OUT.jsonl        # gate (b), opp_run opponents
  python stuck_probe.py race BUILD LAM LO CNT STEP OUT.jsonl           # vs_race (unified tap 2 steering)
  python stuck_probe.py selfcheck
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V

PAIRS = ((1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3))
KEEP = 10


def _decode(a, pa, pb):
    var, col = a // 8, a % 8
    if var == 0: return ORIENT_H, col, Pill(pa, pb)
    if var == 1: return ORIENT_H, col, Pill(pb, pa)
    if var == 2: return ORIENT_V, col, Pill(pa, pb)
    return ORIENT_V, col, Pill(pb, pa)


def cleared_by(board, pa, pb, allowed=None):
    """set of virus positions cleared by at least one legal placement of pill (pa, pb)."""
    before = set(map(tuple, np.argwhere(board.is_virus).tolist()))
    out = set()
    for a in range(32):
        if allowed is not None and not allowed[a]:
            continue
        o, c, p = _decode(a, pa, pb)
        b = board.clone()
        if not b.place_pill(p, o, c):
            continue
        b.resolve()
        if b.virus_count() < len(before):
            after = set(map(tuple, np.argwhere(b.is_virus).tolist()))
            out |= before - after
    return out


def structural(board):
    s = set()
    for pa, pb in PAIRS:
        s |= cleared_by(board, pa, pb)
    return s


ENDS = ("cleared_own", "cleared_garbage", "unlocked_own", "unlocked_garbage", "unlocked_pill", "end")
KINDS = ("str", "act", "mask")


class StuckProbe:
    """Two levels, each for the three kinds str/act/mask:
      VIRUS episodes  per virus, consecutive decisions without a clearing move for THAT virus. Early in a game almost
                      every virus is 'stuck' this way (one pill adds 2 cells; a lone virus needs 3), so these are
                      reported with vleft at start/end and min, for stratification.
      BOARD stalls    consecutive decisions where NO remaining virus has a clearing move (the couch G1 stall: 2 of
                      102 pills had one). This is 'the AI cannot make progress'.
    Compact rows: virus ep = [kind, r, c, colour, k0, len, vleft0, vleft_end, end, t0, dur_s];
                  board stall = [kind, k0, len, vleft0, vleft_end, end, t0, dur_s].
    End codes (ENDS index): cleared_own / cleared_garbage (virus vanished in the AI's placement / in a garbage drop),
      unlocked_own (the board right after the AI's placement was already structurally clearable for it),
      unlocked_garbage (only the garbage drop made it clearable), unlocked_pill (it was structurally clearable
      before; only the pill colour was wrong), end (censored by the game's end; the row's `how` says how)."""

    def __init__(self):
        self.vcnt = {k: {} for k in KINDS}; self.vst = {k: {} for k in KINDS}
        self.bcnt = {k: 0 for k in KINDS}; self.bst = {k: None for k in KINDS}
        self.vep = []; self.bep = []
        self.prev_str = set(); self.post_str = set(); self.v_post = set()
        self.ndec = 0; self.in_stall = {k: {10: 0, 20: 0} for k in KINDS}

    def _end(self, kind, v, gone):
        if gone:
            return 1 if v in self.v_post else 0
        if kind != "str" and v in self.prev_str:
            return 4
        return 2 if v in self.post_str else 3

    def pre_decision(self, board, cur, k, t, mask_fn):
        V = set(map(tuple, np.argwhere(board.is_virus).tolist())); nv = len(V)
        pa, pb = int(cur.a), int(cur.b)
        S = {"str": structural(board), "act": cleared_by(board, pa, pb)}
        S["mask"] = cleared_by(board, pa, pb, allowed=mask_fn()) if S["act"] else set()
        for kind in KINDS:
            ki = KINDS.index(kind)
            cnt, st = self.vcnt[kind], self.vst[kind]
            for v in list(cnt):
                gone = v not in V
                if gone or v in S[kind]:
                    L = cnt.pop(v); s0 = st.pop(v)
                    if L >= KEEP and kind != "mask":
                        self.vep.append([ki, v[0], v[1], s0[3], s0[0], L, s0[2], nv, self._end(kind, v, gone),
                                         round(s0[1], 1), round(t - s0[1], 1)])
            for v in V:
                if v not in S[kind]:
                    if v not in cnt:
                        cnt[v] = 0; st[v] = (k, t, nv, int(board.color[v[0], v[1]]))
                    cnt[v] += 1
            # board-level stall
            if S[kind]:
                if self.bcnt[kind] >= KEEP:
                    s0 = self.bst[kind]
                    newly = sorted(S[kind])
                    ends = [self._end(kind, v, False) for v in newly]
                    self.bep.append([ki, s0[0], self.bcnt[kind], s0[1], nv, min(ends), round(s0[2], 1), round(t - s0[2], 1)])
                self.bcnt[kind] = 0; self.bst[kind] = None
            else:
                if self.bcnt[kind] == 0:
                    self.bst[kind] = (k, nv, t)
                self.bcnt[kind] += 1
                for n in (10, 20):
                    self.in_stall[kind][n] += int(self.bcnt[kind] >= n)
        self.ndec += 1
        self.prev_str = S["str"]; self.post_str = set(); self.v_post = V

    def post_own(self, board):
        """board after the AI's placement + resolve, before any garbage."""
        self.v_post = set(map(tuple, np.argwhere(board.is_virus).tolist()))
        self.post_str = structural(board)

    def finish(self, how, k, t):
        nv = None
        for kind in KINDS:
            ki = KINDS.index(kind)
            for v, L in self.vcnt[kind].items():
                if L >= KEEP and kind != "mask":
                    s0 = self.vst[kind][v]
                    self.vep.append([ki, v[0], v[1], s0[3], s0[0], L, s0[2], -1, 5, round(s0[1], 1), round(t - s0[1], 1)])
            if self.bcnt[kind] >= KEEP:
                s0 = self.bst[kind]
                self.bep.append([ki, s0[0], self.bcnt[kind], s0[1], -1, 5, round(s0[2], 1), round(t - s0[2], 1)])
        return {"vep": self.vep, "bep": self.bep, "ndec": self.ndec, "in_stall": self.in_stall,
                "open_stall_at_end": {kind: self.bcnt[kind] for kind in KINDS}}


def _mask_fn(board, k):
    import reach_fw_tap as RFT
    import steer_model as SM
    return lambda: RFT.reach_mask_fw(board.color.tolist(), SM.table_threshold(k), 2)


# ------------------------------- gate (b): opp_run.play + probe hooks -------------------------------
def play_gb(seed, choose, steer, opp, level=11, maxpills=600, probe=None):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    import clock_play as CP
    import steer_model as SM
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills); env.reset()
    NesPillSource(seed=seed).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    elapsed = 0.0; garbage = 0; res = "stall"; v_at_topout = None
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0, "opp_spawn_h": 0, "own_spawn_h": 0}
    steer.reset(seed); opp.reset(seed)
    for _ in range(maxpills):
        if env.board.virus_count() == 0: res = "clear"; break
        if probe is not None:
            probe.pre_decision(env.board, env.cur, env.pills_placed, elapsed, _mask_fn(env.board, env.pills_placed))
        fb = FB.from_board(env.board); col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count(); ctx["own_t"] = elapsed
        a = choose(env, col, vir, ctx)
        if a is None: break
        var, cc = a // 8, a % 8
        cols_involved = [cc] if var in (2, 3) else [cc, min(cc + 1, 7)]
        hmax = 0
        for tc in cols_involved:
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            h = 16 - min(filled) if filled else 0
            hmax = max(hmax, h)
        dt = CP.T_LAT + CP.FPR * max(0, 16 - hmax); elapsed += dt
        occ_before = int(np.count_nonzero(env.board.color))
        ex = steer.execute(env.board.color.tolist(), int(a), env.pills_placed)
        (_, _, term, trunc, info), _straight = SM.place_executed(env, ex)
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout": v_at_topout = env.board.virus_count()
            break
        if trunc: break
        if probe is not None:
            probe.post_own(env.board)
        if env.pills_placed >= CP.GARBAGE_MIN_PILLS:
            clear_size = max(0, occ_before + 2 - int(np.count_nonzero(env.board.color)))
            garbage += opp.after_placement(env.board, seed, env.pills_placed, clear_size)
            if env.board.virus_count() == 0: res = "clear"; break
            if env.board.spawn_blocked(): res = "topout"; v_at_topout = env.board.virus_count(); break
    vleft = v_at_topout if v_at_topout is not None else env.board.virus_count()
    out = {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"), "stall": int(res == "stall"),
           "pills": env.pills_placed, "elapsed_s": round(elapsed, 1), "garbage": garbage, "vleft": int(vleft),
           "dies_ahead": int(res == "topout" and v_at_topout is not None and v_at_topout <= 12), "how": res}
    out["steer"] = dict(steer.stats)
    if hasattr(opp, "summary"):
        out["opp"] = opp.summary()
    if probe is not None:
        out["stuck"] = probe.finish(res, env.pills_placed, elapsed)
    return out


# ------------------------------- race: vs_race.play + probe hooks -------------------------------
def play_race(seed, arm, lam, level=11, maxpills=600, steer=None, probe=None):
    import vs_race as V
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    choose = V._decider(arm)
    if steer is not None:
        import steer_model as SM
        steer.reset(seed)
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills); env.reset()
    NesPillSource(seed=seed).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    vq = V._volleys(seed, lam); vi = 0
    store = 0; colours = [1, 2, 3, 1]
    t = 0.0; frames = []; sent = []; recv = 0; nrel = 0
    how = "cap"
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0, "opp_spawn_h": 0, "own_spawn_h": 0}
    for _ in range(maxpills):
        if probe is not None:
            probe.pre_decision(env.board, env.cur, env.pills_placed, t, _mask_fn(env.board, env.pills_placed))
        fb = FB.from_board(env.board); col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count(); ctx["own_t"] = t
        a = choose(env, col, vir, ctx)
        if a is None:
            how = "nomove"; break
        if steer is not None:
            ex = steer.execute(env.board.color.tolist(), int(a), env.pills_placed)
            a_ex = ex["var"] * 8 + ex["col"]
            straight = SM.is_straight(env.board.color, ex)
            a = a_ex
        var, cc = a // 8, a % 8
        hmax = 0
        for tc in ([cc] if var in (2, 3) else [cc, min(cc + 1, 7)]):
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            hmax = max(hmax, 16 - min(filled) if filled else 0)
        if steer is None or straight:
            pp = V.probe_placement(env, int(a))
            _, _, term, trunc, info = env.step(int(a))
        else:
            with SM.forced_landing(env.board, ex["cells"]):
                pp = V.probe_placement(env, int(a))
                _, _, term, trunc, info = env.step(int(a))
        f = V.BASE_F + V.SOFT_F * max(0, 15 - hmax) + V.CLR_F * len(pp["lines"])
        frames.append(f); t += f / V.FPS
        if pp["attack"]:
            sent.append((round(t, 2), int(pp["atk_size"])))
        if term:
            how = "clear" if info["won"] else "topout"; break
        if trunc:
            break
        if probe is not None:
            probe.post_own(env.board)
        while vi < len(vq) and vq[vi][0] <= t:
            store += vq[vi][1]; colours = vq[vi][2]; vi += 1
        if store >= V.ATTACK_SIZE_MIN:
            size = min(4, store); store = 0; nrel += 1; recv += size
            combo = V.drop_garbage(env.board, size, colours, seed * 7919 + nrel)
            cs = V.attack_size(combo)
            if cs >= V.ATTACK_SIZE_MIN:
                sent.append((round(t, 2), int(cs)))
            if env.board.virus_count() == 0:
                how = "clear"; break
            if env.board.spawn_blocked():
                how = "topout"; break
    out = {"seed": seed, "arm": arm, "lam": lam, "how": how, "t_end": round(t, 2),
           "pills": len(frames), "vleft": int(env.board.virus_count()), "sent": sent,
           "tiles_sent": sum(s for _, s in sent), "tiles_recv": recv,
           "mean_f": round(float(np.mean(frames)), 1) if frames else 0.0, "rev": V.HARNESS_REV}
    if steer is not None:
        out["steer"] = dict(steer.stats)
    if probe is not None:
        out["stuck"] = probe.finish(how, len(frames), t)
    return out


def selfcheck():
    """_decode must equal FaithfulDrMarioEnv._decode for every action and pill."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    env = FaithfulDrMarioEnv(level=11, seed=1, max_pills=10); env.reset()
    for pa, pb in PAIRS + ((2, 1), (3, 1), (3, 2)):
        env.cur = Pill(pa, pb)
        for a in range(32):
            assert _decode(a, pa, pb) == env._decode(a), (a, pa, pb)
    print("selfcheck: decode OK")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "selfcheck":
        selfcheck(); sys.exit(0)
    import steer_model as SM
    if mode == "gb":
        import opp_run as OR, steer_run as SR
        build, oppname, lo, cnt, step, outp = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer, choose = SR.make(build); opp = OR.make_opponent(oppname)
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = play_gb(lo + i * step, choose, steer, opp, probe=StuckProbe())
                r.update({"arm": f"{build}@{oppname}", "model": oppname, "trate": 0.0})
                fh.write(json.dumps(r) + "\n"); fh.flush()
    elif mode == "race":
        build, lam, lo, cnt, step, outp = sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
        steer = SM.Steer(proph="throat", pulse=True, tap_period=2, tap_unified=True)
        with open(outp, "w") as fh:
            for i in range(cnt):
                r = play_race(lo + i * step, build, lam, level=11, steer=steer, probe=StuckProbe())
                r["arm"] = build + "~steer"; r["level"] = 11; r["tap"] = 2; r["tap_unified"] = True
                fh.write(json.dumps(r) + "\n"); fh.flush()
