#!/usr/bin/env python3
"""Task #96 step 2: how OFTEN is the owner's two-pill joint dig available, and how often
does the champion take it?

Plays the shipped champion (fast_rtl_x winner variant, depth-3 + EH + delta, topk2=8) and
at every decision asks the detector: on the current danger column, does a two-pill line
exist that digs when neither pill alone would? Then compares against what the champion
actually played.

TWO TRAPS THIS FILE IS BUILT AROUND
  * deepcopy pill-cursor. The detector never copies the env -- it reads the raw
    (color, is_virus, link) planes and drives `cascade_chain_x._expand_chain` on them, so
    the capsule cursor is never touched. That is argued, not trusted: `--replay` plays each
    seed twice, once with the scanner attached and once without, and requires the games to
    be IDENTICAL (pills, result, viruses, and the full move list).
  * placement mapping. The champion's action is decoded through the env, then the SAME
    placement is rebuilt through `_expand_chain`, and the two resulting COLOUR planes are
    compared cell-for-cell against an independent `FaithfulBoard.place_pill + resolve` on a
    clone. A mapping error (or a kernel/sim disagreement) would otherwise silently
    misattribute what the champion "chose". Mismatches are counted and reported, never
    swallowed. `--verify-frac` controls how many decisions get the (slow, pure-Python)
    cross-check; it is 1.0 by default because correctness here is the whole point.

    corpus_pass.py [n_games] [--replay] [--level 11]
"""
from __future__ import annotations

import sys

import numpy as np

HERE = "/home/struktured/projects/dr-mario-prestart-wt/experiments/jointdig"
for _p in (HERE, "/home/struktured/projects/dr_mario_rl/tmp/combo_term",
           "/home/struktured/projects/dr_mario_rl/tmp/endgame",
           "/home/struktured/projects/dr_mario_rl/tmp/pillrng",
           "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import jointdig as J                                     # noqa: E402
import fast_rtl_x as F                                   # noqa: E402
import cascade_link_x as L                                # noqa: E402
from drmario.faithful_env import FaithfulDrMarioEnv       # noqa: E402
from drmario.faithful_game import ORIENT_H                # noqa: E402
from nes_pills import NesPillSource                       # noqa: E402

COLS, ROWS = J.COLS, J.ROWS


def planes(board):
    return (np.ascontiguousarray(board.color, dtype=np.int8).reshape(-1).copy(),
            board.is_virus.reshape(-1).astype(np.int8).copy(),
            np.ascontiguousarray(board.link, dtype=np.int8).reshape(-1).copy())


def action_to_variant(env, action):
    """env action -> (cascade variant, column, pa, pb). Verified per-decision by
    board comparison in run_game(), never assumed."""
    orient, col, pill = env._decode(int(action))
    variant = 0 if orient == ORIENT_H else 2
    return variant, col, pill.a, pill.b


def build_decider():
    F.warmup_ship_eh()
    F.warmup_delta()
    L.warmup_linked()
    J.warmup()
    w, fl = F.variant("winner")
    return F.FastShipD3DeciderEHDelta(w, fl, topk2=8)


def run_game(dec, seed, level, scan=True, h_min=J.H_MIN_DEFAULT, S=None, verify=True):
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()
    rec = []
    moves = []
    map_bad = 0
    pending = {}      # mode -> (danger column, viruses in it right after the setup half)
    while True:
        a = dec.choose(env.board, env.cur, env.nxt)
        if a is None:
            break
        moves.append(int(a))
        if scan:
            col, vir, lnk = planes(env.board)
            variant, c, pa, pb = action_to_variant(env, a)
            # --- rebuild the champion's own placement through the kernel, into the RESERVED
            #     buffer b3 (scan() clobbers b1/b2 on every candidate).
            ok, _, _, _ = S.place(col, vir, lnk, variant, c, pa, pb, S.b3)
            chose_col, chose_vir = S.b3[0].copy(), S.b3[1].copy()
            if ok and verify:
                ref = env.board.clone()
                orient, rcol, rpill = env._decode(int(a))
                if ref.place_pill(rpill, orient, rcol):
                    ref.resolve()
                    if not np.array_equal(
                            np.ascontiguousarray(ref.color, dtype=np.int8).reshape(-1),
                            chose_col):
                        map_bad += 1
                else:
                    map_bad += 1
            # --- COMPLETION: did a setup parked last decision actually cash this decision?
            for mode, pend in list(pending.items()):
                pd, pv = pend
                if ok:
                    now = J.col_viruses(chose_col, chose_vir, pd)
                    for rr in reversed(rec):
                        if rr["mode"] == mode and rr.get("chose_setup"):
                            rr["completed"] = bool(now < pv)
                            break
                del pending[mode]
            dgs = J.danger_columns(col, vir, h_min=h_min)
            n_legal = len(S.legal(col, vir, lnk, env.cur.a, env.cur.b))
            for mode in ("tall", "buried"):
                for d in dgs[mode][:1]:                       # most-dangerous column only
                    r = S.scan(col, vir, lnk, (env.cur.a, env.cur.b), (env.nxt.a, env.nxt.b), d)
                    chose_setup = ok and ((variant, c) in r["setups_v"])
                    chose_single = ok and (
                        r["v0"] - J.col_viruses(chose_col, chose_vir, d)) > 0
                    rec.append(dict(seed=seed, mode=mode, pill=len(moves), d=d,
                                    v0=r["v0"], o0=r["o0"],
                                    single=r["single_vdig"], joint=r["joint_vdig"],
                                    joint_only=r["joint_v_only"],
                                    n_setups=len(r["setups_v"]), n_legal=n_legal,
                                    chose_setup=chose_setup, chose_single=chose_single,
                                    completed=None))
                    if chose_setup and r["joint_v_only"]:
                        pending[mode] = (d, J.col_viruses(chose_col, chose_vir, d))
            if not ok:
                map_bad += 1
        _, _, term, trunc, _ = env.step(int(a))
        if term or trunc:
            break
    return dict(seed=seed, pills=env.pills_placed, viruses_left=env.board.virus_count(),
                moves=moves, rec=rec, map_bad=map_bad)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0]) if args else 12
    level = 11
    if "--level" in sys.argv:
        level = int(sys.argv[sys.argv.index("--level") + 1])
    dec = build_decider()
    S = J.Scanner()
    verify = True
    if "--verify-frac" in sys.argv:
        verify = float(sys.argv[sys.argv.index("--verify-frac") + 1]) > 0

    if "--replay" in sys.argv:
        print("REPLAY GATE: same seed with and without the scanner must be IDENTICAL")
        bad = 0
        for s in range(2000, 2000 + min(n, 6)):
            g1 = run_game(dec, s, level, scan=True, S=S, verify=True)
            g0 = run_game(dec, s, level, scan=False)
            same = (g1["moves"] == g0["moves"] and g1["pills"] == g0["pills"]
                    and g1["viruses_left"] == g0["viruses_left"])
            bad += (not same)
            print("  seed %d: pills %d/%d  vleft %d/%d  moves %d/%d  %s"
                  % (s, g1["pills"], g0["pills"], g1["viruses_left"], g0["viruses_left"],
                     len(g1["moves"]), len(g0["moves"]),
                     "IDENTICAL" if same else "*** DIVERGED"))
        print("REPLAY:", "PASS" if bad == 0 else "FAIL (%d)" % bad)
        if bad:
            return 1
        print()

    allrec, map_bad, pills_tot = [], 0, 0
    for s in range(2000, 2000 + n):
        g = run_game(dec, s, level, scan=True, S=S, verify=verify)
        allrec += g["rec"]
        map_bad += g["map_bad"]
        pills_tot += g["pills"]
    print("=" * 84)
    print("JOINT-DIG AVAILABILITY + TAKE-RATE -- champion, %d games, %d pills, L%d"
          % (n, pills_tot, level))
    print("=" * 84)
    print("placement-mapping / kernel-vs-sim mismatches: %d (must be 0)" % map_bad)
    for mode in ("tall", "buried"):
        R = [r for r in allrec if r["mode"] == mode]
        if not R:
            print("\n%-7s no decisions had such a column" % mode)
            continue
        avail_j = [r for r in R if r["joint"] > 0]
        only_j = [r for r in R if r["joint_only"]]
        avail_s = [r for r in R if r["single"] > 0]
        took_setup = [r for r in only_j if r["chose_setup"]]
        took_single = [r for r in avail_s if r["chose_single"]]
        print()
        print("%s danger column -- %d decisions with one" % (mode.upper(), len(R)))
        print("  single-pill dig available : %5d (%5.1f%%)" % (len(avail_s), 100*len(avail_s)/len(R)))
        print("  JOINT dig available       : %5d (%5.1f%%)" % (len(avail_j), 100*len(avail_j)/len(R)))
        print("  JOINT-ONLY (no single)    : %5d (%5.1f%%)  <- the owner's case"
              % (len(only_j), 100*len(only_j)/len(R)))
        if avail_s:
            print("  take-rate | single avail : %5d/%-5d (%5.1f%%)"
                  % (len(took_single), len(avail_s), 100*len(took_single)/len(avail_s)))
        if only_j:
            # CHANCE BASELINE: what fraction of legal placements happen to BE a setup half?
            # Without this, a "51% setup rate" is not evidence of intent -- it may be below
            # what a coin flip over the legal moves would give.
            chance = sum(r["n_setups"] / max(1, r["n_legal"]) for r in only_j) / len(only_j)
            obs = len(took_setup) / len(only_j)
            print("  SETUP-rate | joint-only   : %5d/%-5d (%5.1f%%)" % (len(took_setup), len(only_j), 100*obs))
            print("    chance baseline (mean |setups|/|legal|) : %5.1f%%   -> lift %+.1f pts %s"
                  % (100*chance, 100*(obs-chance),
                     "(ABOVE chance)" if obs > chance else "(AT OR BELOW chance -- no evidence of intent)"))
            comp = [r for r in took_setup if r["completed"] is not None]
            done = [r for r in comp if r["completed"]]
            if comp:
                print("    COMPLETED next pill      : %5d/%-5d (%5.1f%%)  <- did the dig actually cash?"
                      % (len(done), len(comp), 100*len(done)/len(comp)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
