#!/usr/bin/env python3
"""THE DECISIVE GATE: paired A/B where BOTH arms are driven by the REAL assembled
EMIT_TUCK_V3 firmware (py65-executed 6502 bytes from fpga/copro/tuck_v3.py +
build_copro_d3.py), not root_search.py's python approximation. Arm off = DRCOPRO_TUCKV3=0,
arm on = DRCOPRO_TUCKV3=1 -- both built from the exact same search code otherwise, so this
is a WITHIN-FIRMWARE comparison that never depends on matching root_search.py/fast_rtl_x.py's
absolute eval scale (which is a documented approximation of the real RTL-faithful firmware,
NOT meant to be bit-exact -- see fast_rtl_x.py's own "BOUNDARY / HONESTY" docstring and its
g_hang comment; confirmed via firmware_decider.py's diagnostic differential, not guessed).

Mirrors ab_root.py's game-stepping and statistics machinery as closely as possible
(FaithfulDrMarioEnv, boot_ci, sign_test_p, the same paired-pills/clear-rate/sign-test
report) so the two scripts' OUTPUT is directly comparable -- only the decision-maker
differs. Each worker process sets DRCOPRO_TUCKV3 via its OWN os.environ (ProcessPoolExecutor
initializer) BEFORE ever importing build_copro_d3/test_search_d3, avoiding the module-
import-time env-var caching hazard (build_copro_d3.EMIT_TUCK_V3 is a module-level constant
read ONCE at import; switching it within one process after import has no effect without a
force-reload, so each arm gets its OWN worker process instead).

Usage: ab_root_firmware.py --seeds 12 --level 11 --workers 4
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/bitexact_gate"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_C = {}


def _init(level, tuck, drchain=180, drfix=1, arm=1):
    """Runs once per WORKER PROCESS. Sets the env vars BEFORE any firmware module is
    imported in this process, then does the one-time (expensive) module load + assembly
    setup, stashed in _C for `play()` to reuse across all decisions in this worker."""
    os.environ["DRCOPRO_TUCKV3"] = "1" if tuck else "0"
    os.environ["DRCOPRO_ARM"] = "1" if arm else "0"
    os.environ["DRFIX"] = "1" if drfix else "0"
    os.environ["DRCHAIN"] = str(drchain)
    from firmware_decider import FirmwareDecider
    fd = FirmwareDecider(drchain=drchain, drfix=drfix, arm=arm)
    _C.update(level=level, tuck=tuck, fd=fd)


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    import root_search as RS

    fd = _C["fd"]
    env = FaithfulDrMarioEnv(level=_C["level"], seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    seg = {"open": [0, 0], "mid": [0, 0], "end": [0, 0]}
    fired = 0
    res = "stall"
    steps_total = 0

    while True:
        from fb import FB
        fb = FB.from_board(env.board)
        vc = env.board.virus_count()
        col, vir = RS.board_flat_from_fb(fb)

        pick = fd.decide(col, vir, env.cur.a, env.cur.b, env.nxt.a, env.nxt.b)
        if pick is None:
            res = "stall"
            break
        steps_total += pick.get("steps", 0)

        k = "open" if vc > 32 else ("mid" if vc > 8 else "end")

        if pick["kind"] == "tuck":
            r0, c0, r1, c1 = pick["placement"]["cells"]
            b = env.board
            b.color[r0, c0] = pick["ca"]
            b.color[r1, c1] = pick["cb"]
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT
                b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN
                b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            fired += 1
            seg[k][0] += 1
            seg[k][1] += vc - b.virus_count()
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                break
            if env.pills_placed >= 300:
                break
            continue

        a = pick["action"]
        _, _, term, trunc, info = env.step(int(a))
        seg[k][0] += 1
        seg[k][1] += vc - env.board.virus_count()
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {"seed": seed, "won": int(res == "clear"), "pills": env.pills_placed,
            "fired": fired, "seg": seg, "steps_total": steps_total}


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = [stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n)]
    reps.sort()
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def sign_test_p(better, worse):
    from math import comb
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    p = sum(comb(n, i) for i in range(0, k + 1)) * (0.5 ** n) * 2
    return min(1.0, p)


def run_level(level, seeds, workers):
    R = {}
    for tuck in (0, 1):
        rows = []
        with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                                 initargs=(level, tuck)) as ex:
            for f in as_completed([ex.submit(play, s) for s in range(seeds)]):
                rows.append(f.result())
        R[tuck] = {r["seed"]: r for r in rows}
        print(f"  L{level} FIRMWARE arm tuck={tuck} done ({len(rows)} games)", flush=True)

    off, on = R[0], R[1]
    all_seeds = sorted(set(off) & set(on))

    both = [s for s in all_seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)

    c_off = sum(off[s]["won"] for s in all_seeds) / len(all_seeds)
    c_on = sum(on[s]["won"] for s in all_seeds) / len(all_seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in all_seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    won_only_off = len(disc) - won_only_on
    p_clear = sign_test_p(won_only_on, won_only_off)

    fires = [on[s]["fired"] for s in all_seeds]

    out = {
        "level": level, "seeds": len(all_seeds),
        "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
        "paired_pills_ci": [lo, hi],
        "paired_n": len(both), "better": better, "worse": worse, "tie": len(d) - better - worse,
        "clear_off": c_off, "clear_on": c_on,
        "discordant": len(disc), "tuck_only_wins": won_only_on, "tuck_only_losses": won_only_off,
        "sign_test_p": p_clear,
        "fires_per_game": st.mean(fires) if fires else 0.0,
    }

    verdict = "REAL (CI excludes 0)" if (hi < 0 or lo > 0) else "WASH (CI spans 0)"
    print(f"\n=== FIRMWARE-BACKED ROOT-ACTION TUCKS v3, L{level}, n={len(all_seeds)} paired seeds ===")
    print(f"1. PAIRED PILLS (both cleared, n={len(both)}/{len(all_seeds)})")
    print(f"   mean delta {out['paired_pills_delta_mean']:+.2f}   95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"   better {better} / worse {worse} / tie {out['tie']}   => {verdict}")
    print(f"2. CLEAR RATE  off {c_off:.1%} -> on {c_on:.1%}   discordant {len(disc)} "
          f"(tuck-only wins {won_only_on}, tuck-only losses {won_only_off}, "
          f"sign-test p={p_clear:.4f})")
    print(f"3. FIRES/GAME  {out['fires_per_game']:.2f}")

    return out, R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--levels", type=int, nargs="+", default=[11])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    results = {}
    for level in a.levels:
        out, R = run_level(level, a.seeds, a.workers)
        results[level] = out
        if a.out:
            fn = f"{a.out}_L{level}.json"
            with open(fn, "w") as fh:
                json.dump({"summary": out,
                          "off": [R[0][s] for s in sorted(R[0])],
                          "on": [R[1][s] for s in sorted(R[1])]}, fh)
            print(f"wrote {fn}")

    print("\n=== SUMMARY ===")
    for level, out in results.items():
        lo, hi = out["paired_pills_ci"]
        verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
        print(f"L{level}: paired pills {out['paired_pills_delta_mean']:+.2f} "
              f"[{lo:+.2f},{hi:+.2f}] {verdict}   clear {out['clear_off']:.1%}->"
              f"{out['clear_on']:.1%}   fires/g {out['fires_per_game']:.2f}")


if __name__ == "__main__":
    main()
