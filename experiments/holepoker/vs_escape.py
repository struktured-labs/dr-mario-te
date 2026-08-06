#!/usr/bin/env python3
"""ESCAPE DEPTH FOR THE VS KILLS -- the depth-vs-eval question, asked where the
champion actually dies.

The solo poker found the champion essentially unkillable by a pill stream, and
the death corpus found ZERO solo topouts in 1200 games. The deaths are all in
the VS/garbage channel. So this is where "would more search depth have saved
it?" has to be answered.

For each VS kill the poker found, replay the match against the SAME adversary
line and, at each of the champion's last plies, ask whether ONE different
champion move survives past the fatal ply. The latest such ply gives E, the
number of plies ahead the champion needed to see:

    E <= 1   the alternative is already inside depth-3's horizon -- an EVAL
             mistake, not a depth mistake
    E = 2-3  a depth-4/5 search would dodge it -- depth is the lever
    E > 5    no feasible search reaches it -- the eval must encode the pattern

REPLAY FIDELITY: the adversary's action list is fixed, but a different champion
move changes the garbage the champion sends back, which can make a stored
adversary action illegal. When that happens we fall back to the champion's own
decider for the adversary seat and flag the line, rather than silently skipping
the ply.
"""
from __future__ import annotations
import sys, os, json, argparse, copy, time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import champion as CH   # noqa: E402
import poker as PK      # noqa: E402
import vs_poker as VP   # noqa: E402

ALL_ACTIONS = [v * 8 + c for v in range(4) for c in range(8)]


def adv_act(m, stored):
    """Use the stored adversary action if still legal, else its own decider."""
    e = m.env[VP.ADV]
    if stored is not None and e.action_masks()[stored]:
        return stored, False
    col, vir = CH.board_to_flat(e.board)
    a = CH.champion_move(col, vir, int(e.cur.a), int(e.cur.b),
                         int(e.nxt.a), int(e.nxt.b))
    return a, True


def replay_to(seed, level, path, upto):
    """Replay the match `upto` full plies; return the match state."""
    m = VP.new_match(seed, level)
    for i in range(upto):
        a, _sub = adv_act(m, path[i] if i < len(path) else None)
        if a is None:
            return None
        st, _s = VP.ply(m, a)
        if st is not None:
            return None
    return m


def continue_with(m, path, start, K, champ_override=None):
    """Continue the match from ply `start`. On the first ply the champion plays
    `champ_override` instead of its own choice. Returns True if the champion is
    still alive after ply K-1."""
    subbed = False
    for i in range(start, K + 2):
        a, sub = adv_act(m, path[i] if i < len(path) else None)
        subbed = subbed or sub
        if a is None:
            return True, subbed              # adversary stuck: champion lives
        # --- adversary half-ply
        m.deliver(VP.ADV)
        if m.env[VP.ADV].board.spawn_blocked():
            return True, subbed
        done, res = m.step(VP.ADV, a)
        if done:
            return True, subbed              # adversary died/cleared: champ alive
        # --- champion half-ply
        m.deliver(VP.CHAMP)
        if m.env[VP.CHAMP].board.spawn_blocked():
            return False, subbed
        if i == start and champ_override is not None:
            ca = champ_override
            if not m.env[VP.CHAMP].action_masks()[ca]:
                return None, subbed          # illegal alternative
        else:
            ca = VP.champ_decide(m)
        if ca is None:
            return False, subbed
        done, res = m.step(VP.CHAMP, ca)
        if done:
            return (res == "clear"), subbed
        if i >= K:
            return True, subbed
    return True, subbed


def escape_for_kill(seed, level, path, K, max_E=8):
    """Latest champion ply with a one-move escape. Returns dict."""
    for j in range(K - 1, max(-1, K - 1 - max_E), -1):
        base = replay_to(seed, level, path, j)
        if base is None:
            continue
        for alt in ALL_ACTIONS:
            m = copy.deepcopy(base)
            alive, subbed = continue_with(m, path, j, K, champ_override=alt)
            if alive is None:
                continue
            if alive:
                # confirm it is a REAL deviation (champion would not have chosen it)
                m2 = copy.deepcopy(base)
                a2, _ = adv_act(m2, path[j] if j < len(path) else None)
                if a2 is None:
                    continue
                m2.deliver(VP.ADV)
                if not m2.env[VP.ADV].board.spawn_blocked():
                    m2.step(VP.ADV, a2)
                    m2.deliver(VP.CHAMP)
                    own = VP.champ_decide(m2)
                    if own == alt:
                        continue            # not a deviation at all
                return {"E": K - j, "ply": j, "alt": alt, "avoidable": True,
                        "adv_substituted": bool(subbed)}
    return {"E": None, "ply": None, "alt": None, "avoidable": False,
            "adv_substituted": None}


def _init():
    CH.init_champion()


def _job(spec):
    CH.init_champion()
    t0 = time.time()
    r = escape_for_kill(spec["seed"], spec["level"], spec["path"], spec["plies"])
    r.update(seed=spec["seed"], K=spec["plies"], secs=round(time.time() - t0, 1))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kills", type=str, default="results/vs_poker_v2.json")
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--out", type=str, default="results/vs_escape.json")
    a = ap.parse_args()
    rows_in = json.load(open(os.path.join(HERE, a.kills)))
    kills = [r for r in rows_in if r.get("killed") and r.get("path")]
    print(f"=== VS ESCAPE DEPTH: {len(kills)} kills ===", flush=True)
    specs = [{"seed": r["seed"], "level": a.level, "path": r["path"],
              "plies": r["plies"]} for r in kills]
    out = []
    with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
        futs = [ex.submit(_job, s) for s in specs]
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            out.append(r)
            print(f"  [{i+1}/{len(specs)}] seed={r['seed']:3d} K={r['K']:3d} "
                  f"E={r['E']} avoidable={r['avoidable']} "
                  f"adv_subbed={r['adv_substituted']} {r['secs']}s", flush=True)
            with open(os.path.join(HERE, a.out), "w") as fh:
                json.dump(out, fh, indent=1, default=str)
    es = [r["E"] for r in out if r["E"] is not None]
    print(f"\navoidable by ONE different champion move: {len(es)}/{len(out)}")
    if es:
        from collections import Counter
        for k, v in sorted(Counter(es).items()):
            print(f"  E={k}: {v}   (a depth-{3+k} search would have dodged it)")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
