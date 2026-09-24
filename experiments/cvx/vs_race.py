"""vs_race — the VS-RACE endpoint: our bot racing a MODELLED HUMAN.

Spec: lulu-147 `experiments/lulu147/VS_RACE_ENDPOINT.md` (2026-08-21), never built until now.
It crosses the two rig families that never met: `pressure_rig` (human-fitted pressure, no
race) and `vs_harness` (a real race, but the opponent is always another bot).

Champion C plays a faithful board with ROM-TRUE attack and receive mechanics, imported from
the sanctioned harness (`attack.probe_placement`, `vs_harness.drop_garbage` incl. counter-
attacks, `rom_attack_rule.attack_size`). The human L is a model, not a board:
  * PACE    — seconds-to-clear T_L0, drawn per seed (lognormal around a pace median).
  * VOLLEYS — Poisson at `lam` per minute, sizes from the Hartford 4fps fit (2:73% 3:17% 4:10%);
              merged between C's placements and released after C's next placement (ROM order).
  * DAMAGE  — every tile C lands on L adds `delta` seconds to L's clock (assumed, not fitted).

C's clock is the CART's pace, not a fall-distance physics: frames/ply = BASE + SOFT*fall_rows +
CLR*cascade_steps (soft drop 2 f/row; supergod lane measured L11 MED plies flat in stack height,
no-clear p50 57 f, mean 86 f). CLR is calibrated so the clean mean lands near 86 f.

Each (seed, arm, lam) game is simulated ONCE to its own end and its timeline banked; win/loss
against any (pace median, spread, delta) is evaluated post-hoc by `evaluate()`: volleys fired
after the race is decided cannot change who won, and C's own play does not depend on L's pace.
Outcomes follow the spec: survive-but-slower and cap are LOSSES.
"""
import sys, os, json, math, random
import numpy as np

CVX = "/home/struktured/projects/dr-mario-h16-wt/experiments/cvx"
VSA = "/home/struktured/projects/dr_mario_rl/tmp/vs_aware"
sys.path.insert(0, CVX)
import import_pin
import_pin.pin()
if VSA not in sys.path:
    sys.path.append(VSA)
from attack import probe_placement            # ROM-true: combo sums over the whole cascade
from vs_harness import drop_garbage, HARNESS_REV as _VSH_REV
from rom_attack_rule import attack_size, ATTACK_SIZE_MIN
import nes_pills as _np_check
assert os.path.realpath(_np_check.__file__) == os.path.realpath(import_pin.PINNED["nes_pills"]), \
    f"vs_harness import rebound nes_pills: {_np_check.__file__}"
from vs_choose import VsPolicy

HARNESS_REV = "vsrace-r1 / " + _VSH_REV
FPS = 60.0988
BASE_F, SOFT_F = 45.0, 2.0
CLR_F = float(os.environ.get("VSRACE_CLR_F", "40"))
SIZES = ((2, 0.73), (3, 0.17), (4, 0.10))
TMAX = 1500.0

ARMS = {
    "holes80": dict(trunk="winholes80", k_clock=0.0),
    "winner":  dict(trunk="winner", k_clock=0.0),
    "kc40":    dict(trunk="winner", k_clock=40.0),
    "h80kc20": dict(trunk="winholes80", k_clock=20.0),
    # Combo Stomper lineage (h2h_vs.py): fixpoint cascade physics + chain-depth reward
    # `imm += w_chain*(chain-1)`. chain0 = the same fixpoint decider with no reward (lnkfix),
    # i.e. the internal baseline that isolates the chain term.
    "chain180":    dict(trunk="winner", chain=180),
    "h80chain180": dict(trunk="winholes80", chain=180),
    "h80chain0":   dict(trunk="winholes80", chain=0),
    # FIRMWARE-FAITHFUL (θ400 recipe f78f1e93: DRCHAIN=180 DRSTRAND=20, shipped in BOTH the
    # Childproof and the TE_HOLES80 cores). Tucks/veto not modelled. Differ ONLY in the leaf's
    # holes weight: fw_winner ≈ Childproof's brain, fw_holes80 ≈ the TE_HOLES80 brain.
    "fw_winner":   dict(trunk="winner", chain=180, strand=20),
    "fw_holes80":  dict(trunk="winholes80", chain=180, strand=20),
    # chain-dose knee on the firmware brain (winner leaf + strand20); fw_winner is the 180 point
    "fw270":       dict(trunk="winner", chain=270, strand=20),
    "fw360":       dict(trunk="winner", chain=360, strand=20),
    "fw540":       dict(trunk="winner", chain=540, strand=20),
}

_CHAIN_READY = False


def _decider(arm):
    """Returns choose(env, col, vir, ctx) -> action for either decider family."""
    global _CHAIN_READY
    spec = ARMS[arm]
    if "chain" in spec:
        import fast_rtl_x as FX
        import cascade_chain_x as C
        if not _CHAIN_READY:
            C.warmup_chain(topk2=8); _CHAIN_READY = True
        w, fl = FX.variant(spec["trunk"])
        if "strand" in spec:
            import cascade_stranded_x as S
            dec = S.StrandedChainD3Decider(w, fl, topk2=8, maxpass=0,
                                           w_chain=int(spec["chain"]), ws=int(spec["strand"]))
        else:
            dec = C.ChainRewardD3Decider(w, fl, topk2=8, maxpass=0, w_chain=int(spec["chain"]))
        return lambda env, col, vir, ctx: dec.choose(env.board, env.cur, env.nxt)
    pol = VsPolicy(**spec)
    return lambda env, col, vir, ctx: pol.decide(col, vir, int(env.cur.a), int(env.cur.b),
                                                 int(env.nxt.a), int(env.nxt.b), ctx)


def _volleys(seed, lam):
    """Ghost volley times + sizes over [0, TMAX]; keyed by (seed, lam) only, so every arm faces
    the identical stream (CRN)."""
    rng = random.Random(seed * 104729 + int(round(lam * 1000)))
    out, t = [], 0.0
    if lam <= 0:
        return out
    while True:
        t += rng.expovariate(lam / 60.0)
        if t > TMAX:
            return out
        x = rng.random(); acc = 0.0; sz = 2
        for s, p in SIZES:
            acc += p
            if x <= acc:
                sz = s; break
        out.append((t, sz, [rng.randint(1, 3) for _ in range(4)]))


def play(seed, arm, lam, level=11, maxpills=600):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS
    choose = _decider(arm)
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=maxpills); env.reset()
    NesPillSource(seed=seed).attach(env); env.cur = env._rand_pill(); env.nxt = env._rand_pill()
    vq = _volleys(seed, lam); vi = 0
    store = 0; colours = [1, 2, 3, 1]
    t = 0.0; frames = []; sent = []; recv = 0; nrel = 0
    how = "cap"
    ctx = {"own_vleft": 48, "opp_vleft": 48, "own_t": 0.0, "opp_t": 0.0, "opp_spawn_h": 0, "own_spawn_h": 0}
    for _ in range(maxpills):
        fb = FB.from_board(env.board); col, vir = RS.board_flat_from_fb(fb)
        ctx["own_vleft"] = env.board.virus_count(); ctx["own_t"] = t
        a = choose(env, col, vir, ctx)
        if a is None:
            how = "nomove"; break
        var, cc = a // 8, a % 8
        hmax = 0
        for tc in ([cc] if var in (2, 3) else [cc, min(cc + 1, 7)]):
            filled = [r for r in range(16) if col[r * 8 + tc] != 0]
            hmax = max(hmax, 16 - min(filled) if filled else 0)
        pp = probe_placement(env, int(a))
        _, _, term, trunc, info = env.step(int(a))
        f = BASE_F + SOFT_F * max(0, 15 - hmax) + CLR_F * len(pp["lines"])
        frames.append(f); t += f / FPS
        if pp["attack"]:
            sent.append((round(t, 2), int(pp["atk_size"])))
        if term:
            how = "clear" if info["won"] else "topout"; break
        if trunc:
            break
        while vi < len(vq) and vq[vi][0] <= t:          # ROM order: receive AFTER our placement
            store += vq[vi][1]; colours = vq[vi][2]; vi += 1
        if store >= ATTACK_SIZE_MIN:
            size = min(4, store); store = 0; nrel += 1; recv += size
            combo = drop_garbage(env.board, size, colours, seed * 7919 + nrel)
            cs = attack_size(combo)
            if cs >= ATTACK_SIZE_MIN:                  # counter-attack from the garbage cascade
                sent.append((round(t, 2), int(cs)))
            if env.board.virus_count() == 0:
                how = "clear"; break
            if env.board.spawn_blocked():
                how = "topout"; break
    return {"seed": seed, "arm": arm, "lam": lam, "how": how, "t_end": round(t, 2),
            "pills": len(frames), "vleft": int(env.board.virus_count()), "sent": sent,
            "tiles_sent": sum(s for _, s in sent), "tiles_recv": recv,
            "mean_f": round(float(np.mean(frames)), 1) if frames else 0.0, "rev": HARNESS_REV}


def _phi_inv(u):
    """Acklam-free inverse normal via bisection on erf (plenty for a per-seed quantile)."""
    lo, hi = -8.0, 8.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < u: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def human_t0(seed, median, sigma):
    u = random.Random(seed * 7727 + 13).random()          # per-seed pace quantile, arm-independent
    return math.exp(math.log(median) + sigma * _phi_inv(min(max(u, 1e-9), 1 - 1e-9)))


def evaluate(row, median, sigma=0.15, delta=2.0):
    """Race outcome for one banked game against a human of the given pace. Returns
    ('win_race'|'loss_race'|'loss_kill'|'loss_cap', T_L_effective)."""
    t0 = human_t0(row["seed"], median, sigma)
    T = t0
    for _ in range(50):                                   # fixed point: our damage extends L's clock
        dmg = sum(s for ts, s in row["sent"] if ts <= T)
        Tn = t0 + delta * dmg
        if abs(Tn - T) < 1e-9: break
        T = Tn
    if row["how"] == "clear":
        return ("win_race" if row["t_end"] < T else "loss_race"), T
    if row["t_end"] >= T:
        return "loss_race", T
    return ("loss_kill" if row["how"] in ("topout", "nomove") else "loss_cap"), T


if __name__ == "__main__":
    arm, lam, lo, cnt, step, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
    with open(out, "w") as fh:
        for i in range(cnt):
            fh.write(json.dumps(play(lo + i * step, arm, lam)) + "\n"); fh.flush()
