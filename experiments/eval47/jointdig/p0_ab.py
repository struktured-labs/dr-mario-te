#!/usr/bin/env python3
"""Forced-policy A/B for the P0 joint-dig tactic (task #96).

PRE-REGISTERED (2026-08-09, before any full-run data was seen):
  ARMS        base (champion unchanged) vs forced (P0 policy below)
  CONDITIONS  drip (rig default) and lulu (bursty, dr_lulu_20260808 fit)
  SEEDS       2..241 paired (seed 1 excluded: degenerate stream; note that
              2k/2k+1 share pill streams -> ~120 distinct streams)
  PRIMARY     dies-ahead and bad-ends (topout+stall), paired discordant
              counts, McNemar exact (two-sided binomial)
  SECONDARY   clear rate, pills among both-clear pairs

POLICY (the owner's tactic, atomic form):
  TAKE: if an instant-4 P0 exists (mono X-X, column top is X over X) take it
        (tallest column first); else if a danger P0 exists (top is X, height
        >= 6, next pill contains X, >=2 free rows) take the tallest.
        Action = vertical mono on that column; legality re-verified via
        _expand_core, champion fallback (counted) if illegal.
  COMPLETE: on the decision after a non-instant take on (c, x): if column c's
        top is still x and cur contains x, play the best CHAMPION-VALUED
        action among those that add an x cell to column c (empirically
        enumerated); champion fallback (counted) if none.
GATES (run in --selftest, required before any A/B run):
  1. OFF-identity: forced=False reproduces pressure_rig.play() exactly, incl.
     the bursty path (3 seeds each model).
  2. Fire-time predicate recheck on every override (always on; any violation
     raises).
  3. KILLED MUTANT: a mutant policy that verts on a non-qualifying column
     must be caught by gate 2.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
QA = os.path.dirname(EV)
for p in (EV, QA, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

import pressure_rig as PR  # noqa: E402
from p0_corpus import p0_columns, col_top, DANGER_H  # noqa: E402

LULU_FIT = os.path.join(EV, "results", "dr_lulu_20260808_fit.json")


def load_lulu():
    from bursty_model import BurstyPressureModel
    j = json.load(open(LULU_FIT))
    return BurstyPressureModel(
        volley_sizes=j["volley_sizes"], gap_samples=j["gap_samples"],
        p_within_k=j["p_within_k"], k_seconds=j["k_seconds"],
        n_volleys=j["n_volleys"], n_clears=j["n_clears"],
        n_matches=j["n_matches"], opponent_of=j["opponent_of"], meta=j["meta"])


def completing_actions(col, vir, c, x, ca, cb, w, fl):
    """All legal actions that add an x-coloured cell to column c, with their
    champion values. Empirical: expand every (var, cc) and diff column c."""
    import root_search as RS
    import fast_rtl_x as FX
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_stranded
    out = []
    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    for var in range(4):
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            adds_x = any(c1[r * 8 + c] == x and col[r * 8 + c] != x
                         for r in range(16))
            if not adds_x:
                continue
            val = RS._root_value(c1, v1, nv, cells, ca, cb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            ws = PR._C["ws"]
            if ws:
                val -= ws * g_stranded(c1, v1)
            out.append((val, var * 8 + cc))
    return out


class Policy:
    """P0 forced policy. mutant=True deliberately picks a NON-qualifying
    column (must be killed by the fire-time recheck). instant_only=True is
    the PRE-REGISTERED FOLLOW-UP arm (2026-08-09, after the full policy was
    refuted p~0 both models): force ONLY instant-4 takes (deterministic
    immediate clears), no danger-column parking, no completion machinery."""

    def __init__(self, mutant=False, instant_only=False):
        self.mutant = mutant
        self.instant_only = instant_only
        self.pending = None       # (col, x) awaiting completion
        self.stats = {"takes": 0, "instant_takes": 0, "completes": 0,
                      "complete_fallback": 0, "take_fallback": 0}

    def choose(self, col, vir, ca, cb, na, nb, w, fl, champ_a):
        from fast_sim_x import NCELL, _expand_core
        c1 = np.empty(NCELL, dtype=np.int8)
        v1 = np.empty(NCELL, dtype=np.int8)
        # completion step first
        if self.pending is not None:
            pc, px = self.pending
            self.pending = None
            r, topc = col_top(col, pc)
            if topc == px and (ca == px or cb == px):
                acts = completing_actions(col, vir, pc, px, ca, cb, w, fl)
                if acts:
                    self.stats["completes"] += 1
                    return max(acts)[1]
                self.stats["complete_fallback"] += 1
            else:
                self.stats["complete_fallback"] += 1
        x, hits = p0_columns(col, ca, cb, na, nb)
        if not hits:
            return champ_a
        inst = sorted((h[1], h[0]) for h in hits if h[2])
        dang = sorted((h[1], h[0]) for h in hits if h[3])
        pick = None
        if inst:
            pick, instant = inst[-1][1], True
        elif dang and not self.instant_only:
            pick, instant = dang[-1][1], False
        if pick is None:
            return champ_a
        if self.mutant:   # deliberately wrong column (first NON-qualifying)
            bad = [c for c in range(8) if c not in [h[0] for h in hits]]
            pick, instant = (bad[0] if bad else pick), False
        # fire-time predicate recheck (GATE 2 — also what kills the mutant)
        rr, topc = col_top(col, pick)
        if not (ca == cb and topc == ca and rr is not None and rr >= 2):
            if self.mutant:
                raise AssertionError("MUTANT KILLED: non-qualifying column")
            self.stats["take_fallback"] += 1
            return champ_a
        ok, _, _ = _expand_core(col, vir, 2, pick, ca, cb, c1, v1)
        if ok == 0:
            self.stats["take_fallback"] += 1
            return champ_a
        self.stats["takes"] += 1
        if instant:
            self.stats["instant_takes"] += 1
        else:
            self.pending = (pick, x)
        return 2 * 8 + pick


def play_one(seed, forced, mutant=False, instant_only=False):
    """pressure_rig.play() replica (drip AND bursty paths) with the policy."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    from fb import FB
    import root_search as RS

    C = PR._C
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]
    model_kind = C.get("model_kind", "drip")
    bmodel = C.get("bursty_model_obj")
    drip_period = C.get("drip_period") or PR.GARBAGE_PERIOD
    drip_k = C.get("drip_k") or PR.GARBAGE_K
    if model_kind == "bursty":
        from bursty_model import inject_bursty_garbage

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    pol = Policy(mutant=mutant, instant_only=instant_only) if forced else None
    res, garbage_injected, v_at_topout = "stall", 0, None
    col = vir = None
    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb = int(env.cur.a), int(env.cur.b)
        na, nb = int(env.nxt.a), int(env.nxt.b)
        a, _c1b = PR._choose_base(col, vir, ca, cb, na, nb, w, fl, wt, ws)
        if a is None:
            break
        if pol is not None:
            a = pol.choose(col, vir, ca, cb, na, nb, w, fl, int(a))
        occ_before = int(np.count_nonzero(env.board.color)) if model_kind == "bursty" else 0
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            if res == "topout":
                v_at_topout = env.board.virus_count()
            break
        if trunc:
            break
        if env.pills_placed >= PR.GARBAGE_MIN_PILLS:
            landed = 0
            if model_kind == "drip":
                if env.pills_placed % drip_period == 0:
                    landed = PR._inject_garbage(env.board, seed, env.pills_placed, k=drip_k)
            else:
                occ_after = int(np.count_nonzero(env.board.color))
                clear_size = max(0, occ_before + 2 - occ_after)
                if clear_size > 0:
                    landed = inject_bursty_garbage(env.board, bmodel, seed,
                                                   env.pills_placed, clear_size)
            garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break
    dies_ahead = int(res == "topout" and v_at_topout is not None
                     and v_at_topout <= PR.DIES_AHEAD_VIRUS_THRESHOLD)
    row = {"seed": seed, "res": res, "won": int(res == "clear"),
           "topout": int(res == "topout"), "pills": env.pills_placed,
           "garbage": garbage_injected, "dies_ahead": dies_ahead}
    if pol is not None:
        row.update({f"pol_{k}": v for k, v in pol.stats.items()})
    return row


_W = {}


def _winit(model, forced, instant_only=False):
    obj = load_lulu() if model == "lulu" else None
    PR._init(11, 0, 20, model_kind=("bursty" if model == "lulu" else "drip"),
             bursty_model_obj=obj)
    _W["forced"] = forced
    _W["instant_only"] = instant_only


def _wplay(seed):
    return play_one(seed, _W["forced"], instant_only=_W.get("instant_only", False))


def selftest():
    # GATE 1: OFF-identity vs pressure_rig.play, both models
    for model in ("drip", "lulu"):
        obj = load_lulu() if model == "lulu" else None
        PR._init(11, 0, 20, model_kind=("bursty" if model == "lulu" else "drip"),
                 bursty_model_obj=obj)
        for s in (2, 3, 4):
            ref, mine = PR.play(s), play_one(s, forced=False)
            for k in ("seed", "won", "topout", "pills"):
                assert ref[k] == mine[k], (model, s, k, ref[k], mine[k])
        print(f"GATE 1 OFF-identity [{model}]: PASS (3 seeds)")
    # GATE 3: mutant killed
    PR._init(11, 0, 20, model_kind="drip")
    killed = 0
    for s in (2, 3, 4, 5, 6, 7):
        try:
            play_one(s, forced=True, mutant=True)
        except AssertionError as e:
            assert "MUTANT KILLED" in str(e)
            killed += 1
    assert killed >= 1, "mutant never fired -> cannot certify gate 2"
    print(f"GATE 3 mutant: KILLED on {killed}/6 seeds (fire-time recheck works)")
    # liveness: forced policy actually fires
    r = play_one(2, forced=True)
    assert r.get("pol_takes", 0) > 0, "policy never fired on seed 2"
    print(f"liveness: seed 2 forced takes={r['pol_takes']} completes={r['pol_completes']}")
    print("SELFTEST: PASS")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--arm", choices=["base", "forced"])
    ap.add_argument("--policy", choices=["full", "instant"], default="full")
    ap.add_argument("--model", choices=["drip", "lulu"])
    ap.add_argument("--seed-start", type=int, default=2)
    ap.add_argument("--seed-count", type=int, default=240)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str)
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    from concurrent.futures import ProcessPoolExecutor, as_completed
    seeds = [s for s in range(args.seed_start, args.seed_start + args.seed_count + 1)
             if s != 1][:args.seed_count]
    done = set()
    if os.path.exists(args.out):
        for ln in open(args.out):
            try:
                r = json.loads(ln)
                done.add((r.get("arm"), r.get("model"), r["seed"]))
            except Exception:
                pass
    todo = [s for s in seeds if (args.arm, args.model, s) not in done]
    print(f"arm={args.arm} model={args.model} seeds={len(seeds)} todo={len(todo)} workers={args.workers}")
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_winit,
                             initargs=(args.model, args.arm == "forced",
                                       args.policy == "instant")) as ex, \
            open(args.out, "a") as fh:
        futs = {ex.submit(_wplay, s): s for s in todo}
        n = 0
        for f in as_completed(futs):
            row = f.result()
            row["arm"], row["model"] = args.arm, args.model
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            n += 1
            if n % 24 == 0:
                print(f"  {n}/{len(todo)}")
    print("DONE")


if __name__ == "__main__":
    main()
