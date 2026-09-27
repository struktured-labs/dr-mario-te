#!/usr/bin/env python3
"""Killed-mutant gate suite for run_gw_price.py (PREREG_GW_PRICE §7).

Every gate is shown FAILING on a wrong variant, not just passing on the right
one.  Exit 0 = all green (incl. all mutants killed); exit 1 = red.  Absence is
never a pass: a gate that cannot run raises.

  G1  non-perturbation: interventions OFF + observer ON reproduces the STOCK
      committed game.play_game byte-for-byte on (result, pills, viruses_cleared,
      clocks, (col,o4) move trace, lat) — 3 real seeds, real RTL.
      M1: closure pill source (nes_pills.attach lambda) MUST break the equality.
  G2  population: dedup ON vs OFF on the screen block's own boards — tie events
      must GROW x4-12 with dedup off (predicted ~7.5x), and the unconditional
      never-same-board assert must hold on every surviving tie.
  G3  arm selection on synthetic fixtures.  M3a worst->max caught; M3b rand pool
      including rep0 caught.
  G4  second implementation: dedup_reps_all[:2] == screen_gw.representatives on
      >=200 real post-garbage tie-candidate boards.
  G5  h_hit: the committed test_gw_hhit.py suite, run as-is (its own mutants).
  G8  determinism: one triggered (seed, arm) replayed => identical row.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_gw_price as R  # noqa: E402  (sets up sys.path for everything else)

FARM_BIN = os.path.join(R.FARM, "build", "obj_farm", "farm_vsim")
FW = "/mnt/data/drmario_cosim/fw/s20b"
G1_SEEDS = (52105, 52108, 52111)   # first N1 seeds: real triggers occur

_fail = []

# ---- parallel game helpers (each worker builds its own Cosim + model) ------
def _worker_stock(seed):
    from cosim import Cosim
    m = R.build_farm_model()
    with Cosim(FARM_BIN, FW) as cs:
        r = _stock_game(cs, seed, m)
    return _key_stock(r), r["result"], r["pills"]


def _worker_iv(args):
    seed, arm, interventions, mut = args
    from cosim import Cosim
    m = R.build_farm_model()        # BEFORE oracle imports
    R._boot_oracle()
    import oracle_arm as O
    C, _ = O.init_rig("lulu")
    with Cosim(FARM_BIN, FW) as cs:
        r = R.play_game_iv(cs, seed, arm, C, m, interventions=interventions,
                           mut=mut)
    r.pop("wall_secs", None)
    return r



def check(name, ok, detail=""):
    print(f"  {name:34s} {'PASS' if ok else 'FAIL'}  {detail}")
    if not ok:
        _fail.append(name)


def _stock_game(cosim, seed, model):
    import game as G
    return G.play_game(cosim, seed, level=11, max_pills=300, trace=True,
                       exec_mode="drop", pressure="bursty", model=model)


def _key_stock(r):
    return (r["result"], r["pills"], r["viruses_cleared"], r["clocks"],
            tuple((m[0], m[1]) for m in r["moves"]), tuple(map(tuple, r["lat"])))


def _key_iv(r):
    return (r["result"], r["pills"], r["viruses_cleared"], r["clocks"],
            tuple((m[1], m[2]) for m in r["moves"]), tuple(map(tuple, r["lat"])))


def g1(C, bmodel):
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=8) as ex:
        f_stock = {s: ex.submit(_worker_stock, s) for s in G1_SEEDS}
        f_mine = {s: ex.submit(_worker_iv, (s, "base", False, None))
                  for s in G1_SEEDS}
        f_mut = ex.submit(_worker_iv, (G1_SEEDS[0], "base", False,
                                       {"closure": True}))
        for seed in G1_SEEDS:
            sk, sres, spills = f_stock[seed].result()
            mine = f_mine[seed].result()
            check(f"G1 stock-identity seed {seed}", sk == _key_iv(mine),
                  f"stock={sres}/{spills} mine={mine['result']}/"
                  f"{mine['pills']} ties={mine['n_tie']}")
        sk0, _, _ = f_stock[G1_SEEDS[0]].result()
        mut = f_mut.result()
        killed = sk0 != _key_iv(mut)
        check("G1-M1 closure mutant KILLED", killed,
              f"mutant {'diverged' if killed else 'IDENTICAL'} "
              f"(ties seen: {mut['n_tie']})")


def _tie_boards(n_seeds=40):
    """Real post-garbage boards from the screen block, replayed in the MIRROR
    (cheap, no RTL): returns [(env_clone, vals, legal, seed, ply)] at plies
    where >=2 legal actions exist."""
    import numpy as np
    import screen_gw as SG
    from oracle_arm import CHAMP_ORDER
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    w, fl, wt, ws = C["w"], C["fl"], C["wt"], C["ws"]
    out = []
    for seed in range(52100, 52100 + n_seeds):
        # walk the mirror game capturing envs at post-garbage plies
        env = O.make_env(seed, C["level"])
        pending = None
        for ply in range(300):
            if env.board.virus_count() == 0:
                break
            vals = SG.champ_values_of(env.board, env.cur.a, env.cur.b,
                                      env.nxt.a, env.nxt.b, w, fl, wt, ws)
            a = O._champ_action(vals, CHAMP_ORDER)
            if a is None:
                break
            if pending is not None:
                legal = [int(s) for s in CHAMP_ORDER
                         if np.isfinite(vals[int(s)])]
                if len(legal) >= 2:
                    out.append((copy.deepcopy(env), vals, legal, seed, ply))
                pending = None
            r, v, pending = SG.advance_split(env, a, C, seed, bmodel)
            if r is not None:
                break
    return out, C, bmodel


def g2_g4(boards, C, bmodel):
    import screen_gw as SG
    n_dedup = n_raw = 0
    n_cmp = 0
    mismatch = 0
    for env, vals, legal, seed, ply in boards:
        reps = R.dedup_reps_all(env, legal, vals)
        if len(reps) >= 2 and reps[0][2] == reps[1][2]:
            n_dedup += 1
            assert reps[0][1] != reps[1][1], "same-board tie survived dedup"
        # raw (nodedup) tie predicate on the same board
        from oracle_arm import CHAMP_ORDER
        rank = {int(a): i for i, a in enumerate(CHAMP_ORDER)}
        ranked = sorted(legal, key=lambda c: (-float(vals[c]), rank[int(c)]))
        if len(ranked) >= 2 and float(vals[ranked[0]]) == float(vals[ranked[1]]):
            n_raw += 1
        # G4 cross-implementation on every board (not only ties)
        sg_reps, _dup = SG.representatives(env, legal, vals)
        mine2 = [a for a, k, v in reps[:2]]
        n_cmp += 1
        if [int(x) for x in sg_reps[:2]] != mine2:
            mismatch += 1
    ratio = (n_raw / n_dedup) if n_dedup else float("inf")
    check("G2 population dedup ratio", n_dedup > 0 and 4.0 <= ratio <= 12.0,
          f"raw={n_raw} dedup={n_dedup} ratio={ratio:.2f} (predicted ~7.5)")
    check("G4 second implementation", n_cmp >= 200 and mismatch == 0,
          f"{n_cmp} boards compared, {mismatch} mismatches")


def g3():
    reps = [(10, "k1", 5.0), (18, "k2", 5.0), (3, "k3", 1.0), (26, "k4", -2.0)]
    w = R._pick_worst(reps)
    check("G3 worst = min-value rep", w == 26, f"picked {w}")
    wm = R._pick_worst(reps, mut={"worst_max": True})
    check("G3-M3a worst->max mutant KILLED", wm != 26 and wm in (10, 18),
          f"mutant picked {wm}")
    draws = {R._pick_rand(reps, s, 7) for s in range(400)}
    check("G3 rand excludes rep0",
          10 not in draws and draws <= {18, 3, 26} and len(draws) == 3,
          f"support={sorted(draws)}")
    draws_m = {R._pick_rand(reps, s, 7, mut={"rand_incl_rep0": True})
               for s in range(400)}
    check("G3-M3b rand-incl-rep0 mutant KILLED", 10 in draws_m,
          f"support={sorted(draws_m)}")
    # worst tie-break: equal minima -> LAST in CHAMP_ORDER rank
    from oracle_arm import CHAMP_ORDER
    rank = {int(a): i for i, a in enumerate(CHAMP_ORDER)}
    reps2 = [(10, "k1", 5.0), (4, "k2", 1.0), (27, "k3", 1.0)]
    w2 = R._pick_worst(reps2)
    want = max((4, 27), key=lambda a: rank[a])
    check("G3 worst tie-break last-in-order", w2 == want,
          f"picked {w2} want {want}")


def g5():
    p = subprocess.run([sys.executable,
                        os.path.join(R.FARM, "test_gw_hhit.py")],
                       capture_output=True, text=True)
    check("G5 test_gw_hhit suite", p.returncode == 0,
          (p.stdout + p.stderr).strip().splitlines()[-1] if
          (p.stdout or p.stderr) else "")


def g8(C, bmodel):
    import json as _j
    from concurrent.futures import ProcessPoolExecutor
    seed = G1_SEEDS[0]
    with ProcessPoolExecutor(max_workers=2) as ex:
        rows = [_j.dumps(f.result(), sort_keys=True) for f in
                [ex.submit(_worker_iv, (seed, "deepen", True, None))
                 for _ in range(2)]]
    check("G8 determinism (deepen arm)", rows[0] == rows[1],
          f"n_iv={_j.loads(rows[0])['n_iv']}")


def g6():
    sys.path.insert(0, HERE)
    from analyze_gw_price import route_verdict, MDE_PP

    def T(void="", green=True, lo=0.1, m=1.0, hi=2.0, pp=1.0, pph=2.0):
        return {"void_reason": void, "ordering_green": green,
                "d_vc_ci_lo": lo, "d_vc_mean": m, "d_vc_ci_hi": hi,
                "proj_pp_point": pp, "proj_pp_hi": pph}

    fixtures = [
        ("void", T(void="gate red"), "VOID"),
        ("not-green", T(green=False), "INDETERMINATE"),
        ("harmful", T(lo=-3, m=-1.5, hi=-0.2, pp=-1, pph=-0.1), "NO-GO"),
        ("small-but-significant", T(lo=0.05, m=0.4, hi=0.8, pp=0.2, pph=0.5),
         "NO-GO"),                      # the M-F4 analogue
        ("go", T(lo=0.5, m=2.0, hi=3.5, pp=1.2, pph=2.5), "GO"),
        ("ci-straddles", T(lo=-0.5, m=1.0, hi=2.5, pp=0.9, pph=2.0),
         "INDETERMINATE"),
    ]
    for name, t, want in fixtures:
        got, why = route_verdict(t)
        check(f"G6 router [{name}]", got == want, f"got {got} ({why})")

    def mut_router(t):                  # M6: ignores the MDE clause
        if t["void_reason"]:
            return "VOID"
        if not t["ordering_green"]:
            return "INDETERMINATE"
        return "GO" if t["d_vc_ci_lo"] > 0 else "NO-GO"

    t = dict(fixtures[3][1])
    check("G6-M6 MDE-blind router mutant KILLED",
          mut_router(t) == "GO" and route_verdict(t)[0] == "NO-GO",
          f"mutant={mut_router(t)} real={route_verdict(t)[0]}")


def main():
    print("gate_gw_price:")
    import oracle_arm as O
    R._boot_oracle()
    C, _ = O.init_rig("lulu")
    g1(C, None)
    boards, C2, bm2 = _tie_boards()
    g2_g4(boards, C2, bm2)
    g3()
    g5()
    g6()
    g8(C, None)
    print("RESULT:", "ALL PASS" if not _fail else f"FAIL: {_fail}")
    sys.exit(0 if not _fail else 1)


if __name__ == "__main__":
    main()
