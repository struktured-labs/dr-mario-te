#!/usr/bin/env python3
"""G2 — falsify the admissible bound.

`h = ceil((min(top_occ[3],top_occ[4]) - 1) / 2)` is the single load-bearing
assumption behind every NEGATIVE in this report: IDA* starts iterating at h and
prunes any node with h > remaining, so if h ever OVERSTATES the distance to
death, the search silently skips real kills and "no hole within K" is worthless.

Two intended test sources failed to produce test cases:
  * the death corpus — ZERO topouts in 1200 solo games, so no real deaths;
  * the taxonomy — zero killing lines found, so no lines.
Both are themselves findings, but neither tests h.

So we MANUFACTURE deaths: randomised near-death boards, kills found by IDA*,
and then the bound is checked at every state of every killing line against the
placements that actually remained. This tests the DEFECT (does h ever exceed the
truth?) rather than asserting the guard.
"""
from __future__ import annotations
import sys, os, json, argparse, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import champion as CH   # noqa: E402
import poker as PK      # noqa: E402


def near_death_board(rng, level=11, floor=1, holes=6):
    """A board buried to `floor` with a few random gaps punched out, so the
    champion has some freedom and the kill depths vary."""
    b = CH.new_board(level, rng.randrange(10_000))
    for c in range(8):
        for r in range(15, floor - 1, -1):
            if b.color[r, c] == 0:
                b.color[r, c] = 1 + rng.randrange(3)
                b.is_virus[r, c] = False
    for _ in range(holes):
        c = rng.randrange(8)
        r = floor + rng.randrange(3)
        if r < 16:
            b.color[r, c] = 0
            b.is_virus[r, c] = False
    b.resolve()
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", type=int, default=40)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=str, default="results/g2_admissibility.json")
    a = ap.parse_args()
    CH.init_champion()
    rng = random.Random(a.seed)

    lines = checked = viol = 0
    worst = None
    tried = 0
    depths = {}
    for i in range(a.boards):
        # floors 1-2 only: these yield SHORT kills, which is all this test needs.
        # A floor-3 board usually has no kill within the depth cap and then costs
        # a full 6^K search to prove it -- expensive, and it contributes no line
        # to check, so it buys nothing here.
        floor = 1 + (i % 2)
        b0 = near_death_board(rng, floor=floor)
        if b0.spawn_blocked():
            continue
        cur = (1 + rng.randrange(3), 1 + rng.randrange(3))
        tried += 1
        sp = PK.SoloPoker(b0, cur, max_oracle=6000)
        r = sp.search(max_depth=a.max_depth)
        if r["depth"] is None:
            continue
        lines += 1
        depths[r["depth"]] = depths.get(r["depth"], 0) + 1
        # walk the line, checking the bound at every state
        b = b0.clone()
        c = cur
        K = len(r["line"])
        for t, (n, act, st) in enumerate(r["line"]):
            h = PK.h_lower_bound(b)
            rem = K - t
            checked += 1
            if h > rem:
                viol += 1
                if worst is None or h - rem > worst[0]:
                    worst = (h - rem, i, t, h, rem)
            if act is None:
                break
            ok, _cl, _v, _ch = CH.apply_action(b, act, c[0], c[1])
            if not ok:
                break
            c = n
        # and the terminal state must actually be a death
        if not (b.spawn_blocked() or r["line"][-1][2] == "nomove"):
            print(f"  !! line {i} did not end in a death -- line invalid", flush=True)
        print(f"  board {i:3d} floor={floor} K={r['depth']} states={K} "
              f"viol_so_far={viol}", flush=True)

    print(f"=== G2 ADMISSIBILITY ===")
    print(f"  boards tried      : {tried}")
    print(f"  killing lines     : {lines}   depths={dict(sorted(depths.items()))}")
    print(f"  states checked    : {checked}")
    print(f"  VIOLATIONS (h>rem): {viol}")
    if worst:
        print(f"  worst overshoot   : {worst[0]} (board {worst[1]} ply {worst[2]}, "
              f"h={worst[3]}, true remaining={worst[4]})")
    ok = viol == 0 and lines > 0
    print(f"  {'PASS -- the bound never overestimated' if ok else ('FAIL -- INADMISSIBLE, every negative in this report is void' if lines else 'INCONCLUSIVE -- no lines found')}")
    with open(os.path.join(HERE, a.out), "w") as fh:
        json.dump({"pass": ok, "lines": lines, "checked": checked,
                   "violations": viol, "depths": depths, "boards": tried}, fh, indent=1)


if __name__ == "__main__":
    main()
