#!/usr/bin/env python3
"""Self-tests for run_2x2.py. Each one targets a specific way this rig could be
silently wrong, and each tests the DEFECT rather than the guard.

  1. arm A reproduces the already-characterized base32 arm, game for game.
     This is the load-bearing one: `v1_drop` claims to be today's silicon, and
     today's silicon is base32 with the descriptor ignored. If my game loop
     introduced any difference at all -- garbage timing, spawn-block ordering,
     pill advance -- this catches it, because reach_root_ab.py's base32 arm is
     already committed and characterized.
  2. cached_firmware_tier_of == firmware_tier3_ab.firmware_tier_of. The cache
     hoists three per-board derivations out of a per-candidate loop; the claim
     that this is equivalent has to be checked, not asserted.
  3. choose_with_base's pick == reach_root.choose_reach_tier's pick. My
     wrapper exists only to ALSO return the base action; it must not perturb
     the decision.
  4. t3 drop-mode degradation never lands DEEPER than the tuck it replaces --
     the whole premise of the `drop` arm is that depth is lost.

Usage: selftest_2x2.py [--seeds 24] [--workers 6]
"""
from __future__ import annotations

import argparse
import os
import sys

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
import firmware_tier3_ab as FT3      # noqa: E402

COMPARED_FIELDS = ("won", "topout", "stall", "pills", "garbage_injected",
                   "viruses_left_at_end", "dies_ahead")


def selftest_arm_a_is_base32(seeds, workers, pressure, bm):
    """arm A (`v1_drop`) must be game-for-game identical to reach_root_ab's
    already-committed `base32` arm."""
    mine = R2.run_arm(11, seeds, workers, "v1_drop", pressure, R2.FIRMWARE_THETA,
                      "drop", bm)
    theirs = AB.run_arm(11, seeds, workers, "base32", pressure, bm)
    bad = []
    for s in sorted(set(mine) & set(theirs)):
        diff = [f for f in COMPARED_FIELDS if mine[s].get(f) != theirs[s].get(f)]
        if diff:
            bad.append((s, diff, {f: mine[s].get(f) for f in diff},
                        {f: theirs[s].get(f) for f in diff}))
    print(f"  arm A vs reach_root_ab base32 ({pressure}): {len(mine)} seeds, "
          f"{len(bad)} differing")
    for b in bad[:3]:
        print(f"    seed={b[0]} fields={b[1]} mine={b[2]} theirs={b[3]}")
    return not bad


def _real_l11_decisions(n_games=6, max_decisions=140, seed0=9000):
    """Genuine L11 boards from real games driven by the shipped decider, the
    same way reach_root._selftest_base32_matches_shipped sources its boards
    (synthetic boards do not exercise the tier machinery realistically)."""
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource
    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]
    out = []
    for g in range(n_games):
        env = FaithfulDrMarioEnv(level=11, seed=seed0 + g, max_pills=300)
        env.reset()
        NesPillSource(seed=seed0 + g).attach(env)
        env.cur = env._rand_pill()
        env.nxt = env._rand_pill()
        for _ in range(60):
            if env.board.virus_count() == 0:
                break
            fb = FB.from_board(env.board)
            col, vir = RS.board_flat_from_fb(fb)
            ca, cb = int(env.cur.a), int(env.cur.b)
            na, nb = int(env.nxt.a), int(env.nxt.b)
            out.append((fb, col, vir, ca, cb, na, nb))
            if len(out) >= max_decisions:
                return out
            pick = RR.choose_base32(col, vir, ca, cb, na, nb)
            if pick["action"] is None:
                break
            _, _, term, trunc, _ = env.step(int(pick["action"]))
            if term or trunc:
                break
    return out


def selftest_cached_tier(decisions):
    import tuck_enum as TE
    bad = checked = 0
    for fb, col, _vir, ca, cb, _na, _nb in decisions:
        for p in TE.enumerate(fb, ca, cb, mode="free"):
            if not (p["is_tuck"] and p["reachable"]):
                continue
            checked += 1
            if R2.cached_firmware_tier_of(col, p) != FT3.firmware_tier_of(col, p):
                bad += 1
    print(f"  cached_firmware_tier_of vs firmware_tier_of: {checked} candidates, "
          f"{bad} disagreements")
    return bad == 0


def selftest_choose_matches_reach_root(decisions, theta):
    bad = []
    for fb, col, vir, ca, cb, na, nb in decisions:
        mine, _base = R2.choose_with_base(fb, col, vir, ca, cb, na, nb, "t3", theta)
        ref = RR.choose_reach_tier(fb, col, vir, ca, cb, na, nb, 1, theta=theta,
                                   tier_fn=FT3.firmware_tier_of)
        if mine["kind"] != ref["kind"]:
            bad.append(("kind", mine["kind"], ref["kind"]))
            continue
        if mine["kind"] == "base":
            if mine["action"] != ref["action"]:
                bad.append(("action", mine["action"], ref["action"]))
        elif tuple(mine["placement"]["cells"]) != tuple(ref["placement"]["cells"]):
            bad.append(("cells", mine["placement"]["cells"], ref["placement"]["cells"]))
    print(f"  choose_with_base vs choose_reach_tier: {len(decisions)} decisions, "
          f"{len(bad)} disagreements")
    for b in bad[:3]:
        print(f"    {b}")
    return not bad


def selftest_t3_drop_never_deeper(decisions, theta):
    import fast_sim_x as FS
    bad, tucks = [], 0
    for fb, col, vir, ca, cb, na, nb in decisions:
        pick, _base = R2.choose_with_base(fb, col, vir, ca, cb, na, nb, "t3", theta)
        if pick["kind"] != "tuck":
            continue
        tucks += 1
        p = pick["placement"]
        r0, c0, r1, c1 = p["cells"]
        tuck_anchor = max(r0, r1) if c0 == c1 else r0
        a = EM.tier3_drop_action(p)
        ok, dr0, dc0, dr1, dc1 = FS._resting(col, a // 8, a % 8)
        if not ok:
            continue
        drop_anchor = max(dr0, dr1) if dc0 == dc1 else dr0
        if drop_anchor > tuck_anchor:
            bad.append((p["cells"], drop_anchor, tuck_anchor))
    print(f"  t3 drop-degradation never deeper than the tuck: {tucks} tuck picks, "
          f"{len(bad)} violations")
    for b in bad[:3]:
        print(f"    {b}")
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=24)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--theta", type=float, default=R2.FIRMWARE_THETA)
    ap.add_argument("--skip-arm-a", action="store_true")
    a = ap.parse_args()

    print("=== run_2x2 self-tests ===")
    RR._lazy()
    results = {}

    if not a.skip_arm_a:
        results["arm_A_is_base32_clean"] = selftest_arm_a_is_base32(
            a.seeds, a.workers, "clean", None)

    decisions = _real_l11_decisions()
    print(f"  ({len(decisions)} real L11 decisions sourced)")
    results["cached_tier_matches"] = selftest_cached_tier(decisions)
    results["choose_matches_reach_root"] = selftest_choose_matches_reach_root(
        decisions, a.theta)
    results["t3_drop_never_deeper"] = selftest_t3_drop_never_deeper(decisions, a.theta)

    print()
    ok = True
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
        ok = ok and v
    print("\nALL PASS" if ok else "\nFAILURES PRESENT")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
