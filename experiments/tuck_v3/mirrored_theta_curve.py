#!/usr/bin/env python3
"""FINAL diagnostic (task #17 stage 3): the pure-python theta curve under the
RTL-faithful leaf mirror (mirrored_leaf.py -- leaf_r47.leaf_vrdy12, matching the real
shipped W_VRDY=12, imm1/eh/DISC untouched). Team-lead directive: "re-run the theta
curve: L11 n=120, theta in {0,150,250,400} on-arms vs a fresh off-arm under the SAME
mirrored eval."

Mirrors ab_root_firmware.py's / ab_root.py's statistics machinery (paired pills-to-
clear, clear rate, sign test, bootstrap CI, real NES capsule stream only) so this
output is directly comparable to the firmware A/B's own report format -- only the
decision-maker differs (mirrored_leaf.choose_root_with_tucks_mirrored instead of
firmware_decider.FirmwareDecider, and instead of real/firmware bytes this is a PURE
PYTHON offline re-proof).

Workers=8 by default (2.3s/decision measured single-threaded; parallelized across
worker PROCESSES, one per seed-batch, matching the house style of every other A/B
runner in this directory -- RSS logged, nohup+disown at launch time, never a bare
foreground run for the full n=120 x 5-arm sweep).
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
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_C = {}


def _init(level, theta, off_arm=False):
    """Runs once per worker process: warm up the numba eval once, stash the (theta,
    off_arm) config for `play()`."""
    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")
    _C.update(level=level, theta=theta, off_arm=off_arm, w=w, fl=fl)


def play(seed):
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource
    from fb import FB
    import mirrored_leaf as ML

    level, theta, off_arm, w = _C["level"], _C["theta"], _C["off_arm"], _C["w"]
    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    fired = 0
    res = "stall"
    for _ in range(300):
        fb = FB.from_board(env.board)
        vc = env.board.virus_count()
        if vc == 0:
            res = "clear"
            break
        tuck_cands = [] if off_arm else None   # [] forces the base-only arm-off control
                                                 # (root_search.py's own documented
                                                 # convention, unchanged here)
        best = ML.choose_root_with_tucks_mirrored(fb, env.cur, env.nxt, w, topk2=8,
                                                    tuck_cands=tuck_cands, theta=theta)
        if best["kind"] == "tuck":
            p = best["placement"]
            r0, c0, r1, c1 = p["cells"]
            col0, col1 = p["colors"]
            b = env.board
            b.color[r0, c0] = col0
            b.color[r1, c1] = col1
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT; b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN; b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            fired += 1
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                break
            if env.pills_placed >= 300:
                break
            continue

        a = best["action"]
        _, _, term, trunc, info = env.step(int(a))
        if term:
            res = "clear" if info["won"] else "topout"
            break
        if trunc:
            break

    return {"seed": seed, "won": int(res == "clear"), "pills": env.pills_placed, "fired": fired}


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


def _log_rss(tag):
    import subprocess
    try:
        out = subprocess.run(
            ["bash", "-c", "ps -o rss= -C python 2>/dev/null | awk '{s+=$1} END {print s+0}'"],
            capture_output=True, text=True, timeout=10)
        rss_kb = int(out.stdout.strip() or "0")
        print(f"  [RSS] {tag}: {rss_kb/1024:.0f} MB across all python processes", flush=True)
    except Exception as e:
        print(f"  [RSS] {tag}: measurement failed ({e})", flush=True)


def run_arm(level, seeds, workers, theta, off_arm=False):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                              initargs=(level, theta, off_arm)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 10) == 0 or (i + 1) == seeds:
                _log_rss(f"L{level} theta={theta} off_arm={off_arm} after {i + 1}/{seeds} games")
    tag = "OFF" if off_arm else f"theta={theta}"
    print(f"  L{level} MIRRORED arm {tag} done ({len(rows)} games)", flush=True)
    return {r["seed"]: r for r in rows}


def compare(off, on, tag):
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
    verdict = "REAL" if (hi < 0 or lo > 0) else "WASH"
    print(f"{tag}: paired pills {st.mean(d) if d else float('nan'):+.2f} "
          f"[{lo:+.2f},{hi:+.2f}] {verdict}  clear {c_off:.1%}->{c_on:.1%}  "
          f"(better {better} worse {worse} tie {len(d)-better-worse}, "
          f"discordant {len(disc)}, tuck-only-wins {won_only_on} tuck-only-losses "
          f"{won_only_off}, sign-p={p_clear:.4f})  fires/g {st.mean(fires) if fires else 0:.2f}",
          flush=True)
    return {"tag": tag, "n": len(all_seeds), "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
            "paired_pills_ci": [lo, hi], "verdict": verdict, "clear_off": c_off, "clear_on": c_on,
            "fires_per_game": st.mean(fires) if fires else 0.0, "sign_test_p": p_clear}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--thetas", type=float, nargs="+", default=[0, 150, 250, 400])
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    print(f"=== MIRRORED-LEAF THETA CURVE, L{a.level}, n={a.seeds}, thetas={a.thetas} ===", flush=True)
    off = run_arm(a.level, a.seeds, a.workers, theta=0, off_arm=True)

    results = {}
    for theta in a.thetas:
        on = run_arm(a.level, a.seeds, a.workers, theta=theta, off_arm=False)
        out = compare(off, on, f"theta={theta}")
        results[theta] = out
        if a.out:
            with open(f"{a.out}_theta{theta}.json", "w") as fh:
                json.dump({"summary": out, "off": [off[s] for s in sorted(off)],
                           "on": [on[s] for s in sorted(on)]}, fh)

    print("\n=== SUMMARY ===")
    for theta, out in results.items():
        print(f"  theta={theta:>6}  delta {out['paired_pills_delta_mean']:+7.2f} "
              f"[{out['paired_pills_ci'][0]:+7.2f},{out['paired_pills_ci'][1]:+7.2f}]  "
              f"{out['verdict']}  clear {out['clear_off']:.1%}->{out['clear_on']:.1%}  "
              f"fires/g {out['fires_per_game']:.2f}")
    any_real = [t for t, o in results.items() if o["verdict"] == "REAL"]
    if any_real:
        print(f"\n{len(any_real)} theta(s) REAL under the mirrored leaf: {any_real}. "
              f"Recalibrate around these -- the design transfers once the ruler matches.")
    else:
        print("\nEVERYTHING WASHES under the RTL-faithful leaf too. Per standing terms, "
              "task #17's firmware phase closes as a validated negative: root-action "
              "tucks work mechanically (base-action agreement, imm1/eh match), but under "
              "the shipped evaluation the positions they reach aren't worth reaching.")
    print("\nDONE")


if __name__ == "__main__":
    main()
