"""Opponent-aware chain policies in the VS-RACE endpoint (live race, per human pace).

The chain dose (w_chain) is chosen PER PILL from the race state the cart can see: our virus count and
the human's (P1's counter is in NES RAM). Policies are small rules over two/three fixed deciders
(StrandedChainD3Decider, winner leaf, strand 20 = the θ400 recipe at other doses).

Because the bot's play now depends on the human's progress, the race is simulated LIVE for one human
pace (median M, sigma) instead of evaluated post-hoc: L's clock T_eff = T_L0 + delta*tiles_landed, and
L's virus count is modelled as a linear countdown v_L(t) = ceil(48 * (1 - t/T_eff)) (DECLARED: linear).
Mechanics, clock and volleys are identical to vs_race.play.
"""
import sys, os, json, math, random
import numpy as np
CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
sys.path.insert(0, CVX)
import vs_race as V
from attack import probe_placement
from vs_harness import drop_garbage
from rom_attack_rule import attack_size, ATTACK_SIZE_MIN

POLICIES = {
    # name: (doses, rule) ; rule(own_v, opp_v) -> dose
    "fw180":        ((180,),          lambda o, p: 180),                                 # baseline = fw_winner
    "fw360":        ((360,),          lambda o, p: 360),                                 # more chain, blind
    "press":        ((180, 360),      lambda o, p: 360 if (o - p >= 3 or p <= 8) else 180),
    "cruise":       ((90, 180),       lambda o, p: 90 if (p - o >= 5) else 180),
    "press_cruise": ((90, 180, 360),  lambda o, p: 360 if (o - p >= 3 or p <= 8) else (90 if (p - o >= 5) else 180)),
}


def _deciders(doses, trunk="winner", ws=20):
    import fast_rtl_x as FX
    import cascade_chain_x as C
    import cascade_stranded_x as S
    if not getattr(_deciders, "_warm", False):
        C.warmup_chain(topk2=8); _deciders._warm = True
    w, fl = FX.variant(trunk)
    return {d: S.StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=d, ws=ws) for d in doses}


def play_live(seed, pol_name, lam, median, sigma=0.15, delta=2.65, level=11, maxpills=600):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    doses, rule = POLICIES[pol_name]
    decs = _deciders(doses)
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills); env.reset()
    NesPillSource(seed=seed).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    vq = V._volleys(seed, lam); vi = 0
    t0 = V.human_t0(seed, median, sigma)
    store = 0; colours = [1, 2, 3, 1]; t = 0.0; tiles_landed = 0; recv = 0; nrel = 0
    dose_hist = {d: 0 for d in doses}; out = None
    def T_eff(): return t0 + delta * tiles_landed
    for _ in range(maxpills):
        if t >= T_eff():
            out = "loss_race"; break
        own_v = env.board.virus_count()
        opp_v = max(0, math.ceil(48 * (1.0 - t / T_eff())))
        d = rule(own_v, opp_v); dose_hist[d] += 1
        fb = FB.from_board(env.board); col, vir = RS.board_flat_from_fb(fb)
        a = decs[d].choose(env.board, env.cur, env.nxt)
        if a is None:
            out = "loss_kill"; break
        var, cc = a // 8, a % 8
        hmax = 0
        for tc in ([cc] if var in (2, 3) else [cc, min(cc + 1, 7)]):
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            hmax = max(hmax, 16 - min(filled) if filled else 0)
        pp = probe_placement(env, int(a))
        _, _, term, trunc, info = env.step(int(a))
        t += (V.BASE_F + V.SOFT_F * max(0, 15 - hmax) + V.CLR_F * len(pp["lines"])) / V.FPS
        if pp["attack"]:
            tiles_landed += int(pp["atk_size"])
        if term:
            out = ("win_race" if t < T_eff() else "loss_race") if info["won"] else ("loss_kill" if t < T_eff() else "loss_race")
            break
        if trunc:
            out = "loss_cap"; break
        while vi < len(vq) and vq[vi][0] <= t:
            store += vq[vi][1]; colours = vq[vi][2]; vi += 1
        if store >= ATTACK_SIZE_MIN:
            size = min(4, store); store = 0; nrel += 1; recv += size
            cs = attack_size(drop_garbage(env.board, size, colours, seed * 7919 + nrel))
            if cs >= ATTACK_SIZE_MIN:
                tiles_landed += int(cs)
            if env.board.virus_count() == 0:
                out = "win_race" if t < T_eff() else "loss_race"; break
            if env.board.spawn_blocked():
                out = "loss_kill" if t < T_eff() else "loss_race"; break
    if out is None:
        out = "loss_cap"
    return {"seed": seed, "pol": pol_name, "lam": lam, "M": median, "delta": delta, "out": out,
            "t": round(t, 1), "T_eff": round(T_eff(), 1), "sent": tiles_landed, "recv": recv,
            "pills": env.pills_placed, "dose_hist": dose_hist, "rev": V.HARNESS_REV}


if __name__ == "__main__":
    pol, lam, M, lo, cnt, step, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), sys.argv[7]
    with open(out, "w") as fh:
        for i in range(cnt):
            fh.write(json.dumps(play_live(lo + i * step, pol, lam, M)) + "\n"); fh.flush()
