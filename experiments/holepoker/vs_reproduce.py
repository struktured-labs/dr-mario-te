#!/usr/bin/env python3
"""REPRODUCIBILITY GATE for the VS kills.

House rule: a hole you cannot replay is an anecdote. Each VS kill is stored as
(seed, adversary action path, plies). This replays every one from scratch and
demands the champion die at the SAME ply. Anything that does not reproduce is
struck from the taxonomy.

Also does the FLUKE check: perturb the adversary's line by dropping its first
placement and re-searching with a live adversary. A kill that only exists for
one exact action sequence is a board-specific curiosity; one that survives the
perturbation is structural.
"""
from __future__ import annotations
import sys, os, json, argparse, copy
HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import champion as CH   # noqa: E402
import vs_poker as VP   # noqa: E402
from vs_escape import adversary_research   # noqa: E402


def replay_kill(seed, level, path, K):
    m = VP.new_match(seed, level)
    for i, a in enumerate(path):
        if not m.env[VP.ADV].action_masks()[a]:
            return False, f"adversary action illegal at ply {i}"
        st, _s = VP.ply(m, a)
        if st == "champ_dead":
            return (i + 1 == K), f"champion died at ply {i+1} (stored {K})"
        if st is not None:
            return False, f"line ended '{st}' at ply {i+1}"
    return False, "path exhausted without a kill"


def fluke_check(seed, level, path, width=10, plies=None):
    """Drop the adversary's first placement, then let a LIVE adversary
    re-search. Does a kill still exist?"""
    m = VP.new_match(seed, level)
    legal = VP.adv_legal(m)
    alt = next((a for a in legal if a != path[0]), None)
    if alt is None:
        return None, "no alternative first move"
    st, _s = VP.ply(m, alt)
    if st is not None:
        return None, f"perturbed line ended immediately ({st})"
    killed, d = adversary_research(m, width=width,
                                   max_plies=plies or (len(path) + 8))
    return killed, f"re-search {'killed at +' + str(d) if killed else 'found no kill'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kills", type=str, default="results/vs_poker_all.json")
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--out", type=str, default="results/vs_reproduce.json")
    ap.add_argument("--no-fluke", action="store_true")
    a = ap.parse_args()
    CH.init_champion()
    rows = json.load(open(os.path.join(HERE, a.kills)))
    kills = [r for r in rows if r.get("killed") and r.get("path")]
    print(f"=== VS KILL REPRODUCIBILITY: {len(kills)} kills ===", flush=True)
    out = []
    for r in kills:
        ok, why = replay_kill(r["seed"], a.level, r["path"], r["plies"])
        rec = {"seed": r["seed"], "K": r["plies"], "reproduced": bool(ok),
               "note": why}
        if not a.no_fluke and ok:
            fk, fwhy = fluke_check(r["seed"], a.level, r["path"], width=a.width)
            rec.update(structural=fk, fluke_note=fwhy)
        out.append(rec)
        print(f"  seed={rec['seed']:3d} K={rec['K']:3d} repro={rec['reproduced']} "
              f"structural={rec.get('structural')}  {rec['note']}"
              f"{' | ' + rec.get('fluke_note', '') if rec.get('fluke_note') else ''}",
              flush=True)
        with open(os.path.join(HERE, a.out), "w") as fh:
            json.dump(out, fh, indent=1, default=str)
    n = len(out)
    rep = sum(1 for r in out if r["reproduced"])
    stru = sum(1 for r in out if r.get("structural"))
    known = sum(1 for r in out if r.get("structural") is not None)
    print(f"\nreproduced: {rep}/{n}")
    print(f"structural (kill survives perturbing the adversary's first move): "
          f"{stru}/{known} of those testable")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
