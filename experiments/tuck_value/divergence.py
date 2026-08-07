#!/usr/bin/env python3
"""DIVERGENCE HORIZON: when a tuck fires, how long does it actually matter?

The measurement neither the co-sim farm nor the offline mirror rig has. Every
tuck result this project has produced is a per-placement statistic -- "lands
+3.3 rows deeper", "fires 6x/game" -- and a maneuver that improves the board
for three pills and then washes out is worth far less than those statistics
imply. Nobody has checked which it is.

METHOD -- fork at the first divergence, with a matched control.

At the FIRST pill index where tuck-mode and drop-mode would execute
differently, the game is forked three ways from one identical board:

  R (reference) plain-drop the tuck's column/orientation, then continue in
                drop mode. This is arm B.
  T (treatment) execute the tuck, then continue in tuck mode. This is arm D.
  C (control)   execute the SECOND-BEST base action, then continue in drop
                mode.

C is the point. Without it, "the boards were still different 40 pills later"
is uninterpretable, because ANY placement difference might persist that long
in a chaotic game -- the same trap the naive best-of-N fell into today (+21.8
pills where the permutation null gave +15.8 of pure noise). C perturbs the
same board at the same pill by a placement of comparable size, so
horizon(T) - horizon(C) isolates what is specific to TUCKS rather than
generic to being perturbed. It is matched by construction on ordinal (same
pill index) and board (same fork point), which is the control discipline the
matched-index memo demands.

Reported per fork:
  pills_to_reconverge   pills until the branch's board is EXACTLY equal to R's
                        again (None = never within the game)
  outcome_changed       branch's terminal result differs from R's
  height/virus gap traces, so washout is visible even without exact
                        reconvergence

FORK CORRECTNESS: `NesPillSource.attach` monkeypatches `env._rand_pill` with a
lambda closing over the source instance, and `copy.deepcopy` treats function
objects as atomic -- so a naive deepcopy leaves BOTH envs drawing from ONE
cursor, silently desynchronising their capsule streams. `fork_env` rebuilds an
independent source at the same index, and `_selftest_fork_lockstep` checks
that two forks fed identical actions stay bit-identical for 40 pills, which is
what catches that defect.

Usage: divergence.py --seeds 300 --workers 6 --pressure clean --out results/div_clean
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS = os.path.dirname(HERE)
EVAL47 = os.path.join(EXPERIMENTS, "eval47")
for _p in (HERE, EXPERIMENTS, EVAL47):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import exec_model as EM              # noqa: E402
import run_2x2 as R2                 # noqa: E402
import reach_root as RR              # noqa: E402
import reach_root_ab as AB           # noqa: E402

MAX_PILLS = 300
_C = {}


# --------------------------------------------------------------------------
def fork_env(env, src):
    """Deep-copy an env AND give the copy its own capsule cursor at the same
    position. See the module docstring for why the second half is not
    optional."""
    from nes_pills import NesPillSource
    e2 = copy.deepcopy(env)
    s2 = NesPillSource(seed=src_seed(src))
    s2.ids = list(src.ids)
    s2.i = src.i
    s2.drawn = src.drawn
    s2.attach(e2)
    return e2, s2


def src_seed(src):
    return getattr(src, "_tv_seed", 1)


def make_source(seed):
    from nes_pills import NesPillSource
    s = NesPillSource(seed=seed)
    s._tv_seed = seed
    return s


def board_key(b):
    return (b.color.tobytes(), b.link.tobytes(), b.is_virus.tobytes())


def height_profile(b):
    import numpy as np
    occ = b.color != 0
    return tuple(int(16 - np.argmax(occ[:, c])) if occ[:, c].any() else 0
                 for c in range(8))


def _new_game(level, seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=MAX_PILLS)
    env.reset()
    src = make_source(seed)
    src.attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    return env, src


# --------------------------------------------------------------------------
def _step_one(env, seed, mode, theta, pressure, bm, force_action=None):
    """Advance one pill under the t3 policy in `mode`. Returns
    (result, diverged_info). `result` is None if the game continues, else one
    of clear/topout/stall. `force_action` overrides the decision entirely
    (used once, to plant the control's second-best base action)."""
    import numpy as np
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    if env.board.virus_count() == 0:
        return "clear", None
    fb = FB.from_board(env.board)
    col, vir = RS.board_flat_from_fb(fb)
    ca, cb = int(env.cur.a), int(env.cur.b)
    na, nb = int(env.nxt.a), int(env.nxt.b)

    occ_before = int(np.count_nonzero(env.board.color)) if pressure == "bursty" else 0
    info = None
    stepped = False

    if force_action is not None:
        action = int(force_action)
    else:
        pick, base_action = R2.choose_with_base(fb, col, vir, ca, cb, na, nb,
                                                "t3", theta)
        if pick["kind"] == "tuck":
            p = pick["placement"]
            a = EM.tier3_drop_action(p)
            import fast_sim_x as FS
            ok = FS._resting(col, a // 8, a % 8)[0]
            drop_action = a if ok else base_action
            info = {"tuck_cells": tuple(p["cells"]),
                    "tuck_colors": (pick["ca"], pick["cb"]),
                    "drop_action": drop_action,
                    "second_best": _second_best_base(fb, col, vir, ca, cb, na, nb,
                                                     drop_action)}
            if mode == "tuck":
                r0, c0, r1, c1 = p["cells"]
                R2._place_cells(env, r0, c0, r1, c1, pick["ca"], pick["cb"])
                stepped = True
            else:
                action = drop_action
        else:
            action = pick["action"]

    if not stepped:
        if action is None:
            return "stall", info
        _, _, term, trunc, gi = env.step(int(action))
        if term:
            return ("clear" if gi["won"] else "topout"), info
        if trunc:
            return "stall", info
    else:
        if env.board.virus_count() == 0:
            return "clear", info
        if env.board.spawn_blocked():
            return "topout", info
        if env.pills_placed >= MAX_PILLS:
            return "stall", info

    if pressure == "bursty" and env.pills_placed >= AB.GARBAGE_MIN_PILLS:
        from bursty_model import inject_bursty_garbage
        occ_after = int(np.count_nonzero(env.board.color))
        clear_size = max(0, occ_before + 2 - occ_after)
        if clear_size > 0:
            inject_bursty_garbage(env.board, bm, seed, env.pills_placed, clear_size)
        if env.board.virus_count() == 0:
            return "clear", info
        if env.board.spawn_blocked():
            return "topout", info
    return None, info


def _second_best_base(fb, col, vir, ca, cb, na, nb, exclude_action):
    """Highest-valued reachable straight drop OTHER than `exclude_action`.
    Deliberately the second-best rather than a random legal action: a random
    action would be a much larger perturbation than a tuck and would inflate
    the control's horizon, flattering the tuck by comparison."""
    cands = RR._scored_base_candidates(fb, col, vir, ca, cb, na, nb, RR.WS, RR.TOPK2)
    pool = [c for c in cands if c["reachable"]] or cands
    pool = [c for c in pool if c["action"] != exclude_action]
    if not pool:
        return None
    return max(pool, key=lambda c: c["val"])["action"]


# --------------------------------------------------------------------------
def play(seed):
    """One seed: run drop mode until the first divergence, fork R/T/C, then
    run all three to completion recording reconvergence."""
    level, theta, pressure = _C["level"], _C["theta"], _C["pressure"]
    bm = _C.get("bm")

    env, src = _new_game(level, seed)
    res = None
    fork_at = None
    fork_info = None

    # ---- run drop mode until the first pill that would diverge -----------
    for _ in range(MAX_PILLS):
        probe_pills = env.pills_placed
        env_r, src_r = fork_env(env, src)          # snapshot BEFORE the step
        res, info = _step_one(env, seed, "drop", theta, pressure, bm)
        if info is not None:
            # a tuck won; does executing it differ from the drop?
            fork_at = probe_pills
            fork_info = info
            env, src = env_r, src_r                 # rewind to the fork point
            break
        if res is not None:
            break
    if fork_at is None:
        return {"seed": seed, "forked": 0, "result_ref": res}

    # ---- three branches from one board ----------------------------------
    env_R, src_R = fork_env(env, src)
    env_T, src_T = fork_env(env, src)
    env_C, src_C = fork_env(env, src)

    import numpy as np
    occ_fork = int(np.count_nonzero(env_R.board.color))
    r0, c0, r1, c1 = fork_info["tuck_cells"]
    col0, col1 = fork_info["tuck_colors"]
    res_R, _ = _step_one(env_R, seed, "drop", theta, pressure, bm)
    R2._place_cells(env_T, r0, c0, r1, c1, col0, col1)
    res_T = _terminal_after_place(env_T, seed, pressure, bm, occ_fork)
    sb = fork_info["second_best"]
    res_C = (_step_one(env_C, seed, "drop", theta, pressure, bm,
                       force_action=sb)[0] if sb is not None else "nocontrol")

    same_T0 = board_key(env_T.board) == board_key(env_R.board)
    same_C0 = board_key(env_C.board) == board_key(env_R.board)

    # ---- run all three out, watching for exact reconvergence with R ------
    trace = {"T": {"recon": None, "gap": []}, "C": {"recon": None, "gap": []}}
    states = {"R": (env_R, res_R, "drop"), "T": (env_T, res_T, "tuck"),
              "C": (env_C, res_C, "drop")}
    step_i = 0
    while step_i < MAX_PILLS:
        if states["R"][1] is not None:
            break
        env_r_, _, _ = states["R"]
        for k in ("T", "C"):
            e, r, m = states[k]
            if r is not None or trace[k]["recon"] is not None:
                continue
            if board_key(e.board) == board_key(env_r_.board):
                trace[k]["recon"] = step_i
            else:
                trace[k]["gap"].append(
                    (step_i,
                     int(e.board.is_virus.sum()) - int(env_r_.board.is_virus.sum()),
                     max(height_profile(e.board)) - max(height_profile(env_r_.board))))
        alive = [k for k in ("R", "T", "C") if states[k][1] is None]
        if not alive:
            break
        for k in alive:
            e, _r, m = states[k]
            nr, _ = _step_one(e, seed, m, theta, pressure, bm)
            states[k] = (e, nr, m)
        step_i += 1

    out = {"seed": seed, "forked": 1, "fork_at_pill": fork_at,
           "result_R": states["R"][1], "result_T": states["T"][1],
           "result_C": states["C"][1],
           "pills_R": states["R"][0].pills_placed,
           "pills_T": states["T"][0].pills_placed,
           "pills_C": states["C"][0].pills_placed,
           "T_identical_at_fork": int(same_T0), "C_identical_at_fork": int(same_C0),
           "horizon_T": trace["T"]["recon"], "horizon_C": trace["C"]["recon"],
           "observed_pills": step_i,
           "gap_T": trace["T"]["gap"][:60], "gap_C": trace["C"]["gap"][:60]}
    out["outcome_changed_T"] = int(_won(out["result_T"]) != _won(out["result_R"]))
    out["outcome_changed_C"] = int(_won(out["result_C"]) != _won(out["result_R"]))
    return out


def _terminal_after_place(env, seed, pressure, bm, occ_before):
    """Terminal check + garbage injection after a manual tuck placement, so
    branch T's fork pill gets exactly the bookkeeping `_step_one` gives R and
    C. `occ_before` is the fork board's occupancy, which all three branches
    share by construction -- without it T would be the only branch that skips
    an injection on its fork pill, and an asymmetry on the very pill being
    measured is the last place to accept one."""
    import numpy as np
    if env.board.virus_count() == 0:
        return "clear"
    if env.board.spawn_blocked():
        return "topout"
    if env.pills_placed >= MAX_PILLS:
        return "stall"
    if pressure == "bursty" and env.pills_placed >= AB.GARBAGE_MIN_PILLS:
        from bursty_model import inject_bursty_garbage
        occ_after = int(np.count_nonzero(env.board.color))
        clear_size = max(0, occ_before + 2 - occ_after)
        if clear_size > 0:
            inject_bursty_garbage(env.board, bm, seed, env.pills_placed, clear_size)
        if env.board.virus_count() == 0:
            return "clear"
        if env.board.spawn_blocked():
            return "topout"
    return None


def _won(r):
    return r == "clear"


def _init(level, theta, pressure, bm=None):
    RR._lazy()
    _C.update(level=level, theta=theta, pressure=pressure, bm=bm)


# --------------------------------------------------------------------------
def _selftest_fork_lockstep(seed=77, n=40):
    """Two forks fed IDENTICAL actions must stay bit-identical. This is the
    test that catches the shared-capsule-cursor defect -- a naive deepcopy
    passes a board-equality check for one step and fails here."""
    RR._lazy()
    env, src = _new_game(11, seed)
    for _ in range(5):
        env.step(3)
    a, sa = fork_env(env, src)
    b, sb = fork_env(env, src)
    for i in range(n):
        act = (i * 7 + 3) % 32
        a.step(act)
        b.step(act)
        if board_key(a.board) != board_key(b.board):
            print(f"  fork lockstep: DIVERGED at step {i}")
            return False
        if (a.cur.a, a.cur.b, a.nxt.a, a.nxt.b) != (b.cur.a, b.cur.b, b.nxt.a, b.nxt.b):
            print(f"  fork lockstep: capsule stream desynced at step {i}")
            return False
    print(f"  fork lockstep: {n} steps bit-identical, capsule streams in sync")
    return True


def _selftest_fork_independent(seed=77):
    """...and each fork must own its capsule cursor: drawing from one must not
    advance the other.

    Asserted on the SOURCE OBJECTS rather than on `env.cur` after a step. An
    earlier version of this test stepped both forks with different actions and
    compared `env.cur`, which fails for an innocent reason -- one action can
    end the episode, so that branch never draws and the two `cur`s legitimately
    differ. Reading the cursors directly tests the shared-cursor defect and
    nothing else."""
    RR._lazy()
    env, src = _new_game(11, seed)
    for _ in range(5):
        env.step(3)
    a, sa = fork_env(env, src)
    b, sb = fork_env(env, src)
    if sa is sb or sa is src:
        print("  fork independence: forks share a source object")
        return False
    i_before = sb.i
    for _ in range(3):
        sa.next_pill()
    if sb.i != i_before:
        print(f"  fork independence: drawing from fork A moved fork B's cursor "
              f"({i_before} -> {sb.i})")
        return False
    if sa.i != i_before + 3:
        print(f"  fork independence: fork A's own cursor did not advance")
        return False
    a.step(0)
    if board_key(a.board) == board_key(b.board):
        print("  fork independence: stepping A also changed B's board")
        return False
    print("  fork independence: cursors and boards are per-fork")
    return True


def run_selftests():
    print("=== divergence self-tests ===")
    ok = _selftest_fork_lockstep() and _selftest_fork_independent()
    print("ALL PASS" if ok else "FAILURES PRESENT")
    return ok


# --------------------------------------------------------------------------
def summarize(rows):
    f = [r for r in rows if r.get("forked")]
    n = len(rows)
    print(f"\nforked {len(f)}/{n} seeds ({len(f) / max(1, n):.1%}) "
          f"-- the rest never had a tuck win at all")
    if not f:
        return {}
    at = [r["fork_at_pill"] for r in f]
    print(f"first divergence at pill: median {st.median(at):.0f} "
          f"mean {st.mean(at):.1f}")

    def horizon_stats(key):
        hs = [r[key] for r in f]
        never = sum(1 for h in hs if h is None)
        fin = [h for h in hs if h is not None]
        return never, fin

    out = {}
    for br, label in (("T", "TUCK"), ("C", "control (2nd-best base)")):
        never, fin = horizon_stats(f"horizon_{br}")
        chg = sum(r[f"outcome_changed_{br}"] for r in f)
        med = st.median(fin) if fin else float("nan")
        print(f"  {label:<24} never reconverges {never}/{len(f)} "
              f"({never / len(f):.1%});  when it does, median {med:.1f} pills "
              f"(n={len(fin)});  outcome changed {chg}/{len(f)} ({chg / len(f):.1%})")
        out[br] = {"never": never, "n": len(f), "median_when_reconverges": med,
                   "n_reconverged": len(fin), "outcome_changed": chg}
    lo, hi = AB.boot_ci([r["outcome_changed_T"] - r["outcome_changed_C"] for r in f])
    d = st.mean([r["outcome_changed_T"] - r["outcome_changed_C"] for r in f])
    print(f"  paired outcome-change difference TUCK - control: "
          f"{d:+.3f} [{lo:+.3f},{hi:+.3f}] "
          f"{'REAL' if (lo > 0 or hi < 0) else 'WASH'}")
    out["tuck_minus_control_outcome_change"] = {"delta": d, "ci": [lo, hi]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=300)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--theta", type=float, default=R2.FIRMWARE_THETA)
    ap.add_argument("--pressure", choices=("clean", "bursty"), default="clean")
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return 0 if run_selftests() else 1

    bm = None
    if a.pressure == "bursty":
        import run_bursty_v1_1_validity as V11
        bm = V11.build_v1_1()
        bm.meta = {k: v for k, v in bm.meta.items() if k != "raw_events"}

    print(f"=== DIVERGENCE HORIZON, L{a.level}, n={a.seeds}, "
          f"pressure={a.pressure}, theta={a.theta:g} ===", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                             initargs=(a.level, a.theta, a.pressure, bm)) as ex:
        futs = [ex.submit(play, s) for s in range(a.seeds)]
        for i, fu in enumerate(as_completed(futs)):
            rows.append(fu.result())
            if (i + 1) % max(1, a.seeds // 5) == 0 or (i + 1) == a.seeds:
                print(f"  {i + 1}/{a.seeds}", flush=True)

    summary = summarize(rows)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(f"{a.out}.json", "w") as fh:
            json.dump({"config": vars(a), "summary": summary, "rows": rows}, fh)
        print(f"wrote {a.out}.json")
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
