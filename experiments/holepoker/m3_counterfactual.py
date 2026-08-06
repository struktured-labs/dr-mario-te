#!/usr/bin/env python3
"""COUNTERFACTUAL ANALYSIS OF THE REAL m3 SILICON DEATH.

Input: the six consecutive capsule commits reconstructed from the m3 video
(dr_mario_rl/tmp/film_review_20260804/recon/boards.json) -- board, the capsule,
the next capsule, and the placement the TAPE actually shows, ending in a topout.

The prior verdict (recon/VERDICT.md) adjudicated MECHANISM: H1, a commit-path /
pair-latch defect, because the eval's own ranking put the tape's column dead
last in 4 of 6 commits. What it did NOT establish is CONSEQUENCE. This does:

  Q1 CONTINUITY  -- does applying the tape placement to board i reproduce board
                    i+1?  If yes, our world model matches silicon on this tape
                    and everything below is anchored to reality (it also
                    identifies the tape's action exactly, without relying on the
                    ambiguous orientation reading).
  Q2 MYOPIA?     -- roll forward from board i under the KNOWN pill stream with
                    the champion deciding every ply.  Does the champion's own
                    choice survive where the tape's died?  If yes the eval was
                    RIGHT and the hardware threw the game -- an execution bug,
                    not myopia.
  Q3 ALREADY LOST? -- exhaustive (deduped BFS) search over the CHAMPION'S OWN
                    action space against the fixed pill stream: does ANY line
                    survive from board i?  This needs no oracle at all -- it is
                    pure mechanics -- so it can be exact.  The earliest i where
                    survival becomes impossible is the moment the trap closed.

Q3 is the question the project actually cares about: were these deaths myopia
(fixable by depth or eval) or already-lost positions (fixable only earlier)?
"""
from __future__ import annotations
import sys, os, json, argparse
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                      # noqa: E402
import champion as CH                   # noqa: E402
import poker as PK                      # noqa: E402

RECON = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/boards.json"
COLOR = {".": 0, "R": 1, "Y": 2, "B": 3}


def parse_board(entry):
    col = np.zeros(128, dtype=np.int8)
    vir = np.zeros(128, dtype=np.int8)
    for r, row in enumerate(entry["board_colors"]):
        for c, ch in enumerate(row):
            col[r * 8 + c] = COLOR[ch]
    for r, row in enumerate(entry["board_isvirus"]):
        for c, ch in enumerate(row):
            vir[r * 8 + c] = 1 if ch == "1" else 0
    return col, vir


def pill_of(s):
    return (COLOR[s[0]], COLOR[s[1]])


def identify_action(b_before, pill, col_after):
    """Which of the 32 actions turns b_before into the observed next board?
    Returns list of matching actions (colour-plane match; links are invisible on
    video so we compare colours only)."""
    hits = []
    for a in PK_ALL_ACTIONS:
        nb = b_before.clone()
        ok, _c, _v, _ch = CH.apply_action(nb, a, pill[0], pill[1])
        if not ok:
            continue
        if np.array_equal(nb.color.reshape(-1).astype(np.int8), col_after):
            hits.append(a)
    return hits


PK_ALL_ACTIONS = [v * 8 + c for v in range(4) for c in range(8)]


def act_str(a):
    v, c = a // 8, a % 8
    return f"{'H' if v < 2 else 'V'}{'ab' if v % 2 == 0 else 'ba'}@c{c}"


# ------------------------------------------------------------- Q3: survival
def survivable(board, stream, plies, cap=300_000):
    """Can the CHAMPION survive `plies` more placements against this fixed pill
    stream, under ANY choice of its own actions?  Deduped BFS over board states
    -- no oracle needed, this is pure mechanics.  Returns (bool, exhaustive)."""
    if PK.h_lower_bound(board) > plies:
        return True, True                       # survival certificate, free
    frontier = {CH.board_key(board): board}
    exhaustive = True
    for d in range(plies):
        if d >= len(stream):
            break
        ca, cb = stream[d]
        nxt = {}
        for b in frontier.values():
            for a in PK_ALL_ACTIONS:
                nb = b.clone()
                ok, _c, _v, _ch = CH.apply_action(nb, a, ca, cb)
                if not ok:
                    continue
                if nb.virus_count() == 0:
                    return True, exhaustive     # cleared = survived
                if nb.spawn_blocked():
                    continue                    # this line dies
                nxt[CH.board_key(nb)] = nb
                if len(nxt) > cap:
                    exhaustive = False
                    break
            if len(nxt) > cap:
                break
        if not nxt:
            return False, exhaustive            # every line dies
        frontier = nxt
    return True, exhaustive


def champion_rollout(board, stream, max_plies):
    """Champion plays itself forward under a fixed stream. Returns
    (result, plies, boards)."""
    b = board.clone()
    boards = []
    for i in range(max_plies):
        if i + 1 >= len(stream):
            return "stream_end", i, boards
        ca, cb = stream[i]
        na, nb_ = stream[i + 1]
        col, vir = CH.board_to_flat(b)
        a = CH.champion_move(col, vir, ca, cb, na, nb_)
        if a is None:
            return "nomove", i, boards
        ok, _c, _v, _ch = CH.apply_action(b, a, ca, cb)
        if not ok:
            return "nomove", i, boards
        boards.append((a, b.clone()))
        if b.virus_count() == 0:
            return "clear", i + 1, boards
        if b.spawn_blocked():
            return "topout", i + 1, boards
    return "alive", max_plies, boards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extend", type=int, default=8,
                    help="plies to roll past the last known commit (needs a "
                         "pill stream assumption -- reported separately)")
    a = ap.parse_args()
    CH.init_champion()
    d = json.load(open(RECON))
    commits = [e for e in d["boards"] if e.get("pill")]
    print(f"=== m3 COUNTERFACTUAL: {len(commits)} capsule commits ===\n")

    boards, pills = [], []
    for e in commits:
        col, vir = parse_board(e)
        boards.append(CH.board_from_flat(col, vir))
        pills.append(pill_of(e["pill"]))
    # the stream: each commit's pill, then the last commit's 'next'
    stream = list(pills) + [pill_of(commits[-1]["next"])]

    # ---------------------------------------------------------------- Q1
    print("--- Q1 CONTINUITY: does the tape placement reproduce the next board? ---")
    tape_acts = []
    for i in range(len(commits) - 1):
        col_after, _ = parse_board(commits[i + 1])
        hits = identify_action(boards[i], pills[i], col_after)
        tape_acts.append(hits)
        cells = commits[i]["tape_placement"]["cells"]
        print(f"  c{i+1} pill={commits[i]['pill']} tape cells={cells} "
              f"-> matches {[act_str(x) for x in hits] if hits else 'NOTHING'}")
    n_ok = sum(1 for h in tape_acts if h)
    print(f"  continuity: {n_ok}/{len(tape_acts)} commits reproduce the next board "
          f"exactly.")
    if n_ok < len(tape_acts):
        print("  ** gaps mean garbage arrived between commits, or the vision "
              "reconstruction differs -- forward claims across a gap are weaker.")

    # ---------------------------------------------------------------- Q2
    print("\n--- Q2 MYOPIA? champion's OWN choice vs the tape, same stream ---")
    q2 = []
    for i in range(len(commits)):
        b = boards[i]
        ca, cb = pills[i]
        na, nb_ = stream[i + 1]
        col, vir = CH.board_to_flat(b)
        want = CH.champion_move(col, vir, ca, cb, na, nb_)
        tape = tape_acts[i][0] if i < len(tape_acts) and tape_acts[i] else None
        agree = (tape is not None and want is not None and
                 (want % 8) == (tape % 8))
        # roll the champion forward from HERE under the real stream
        res, plies, _ = champion_rollout(b, stream[i:], len(stream) - i - 1)
        q2.append({"i": i, "want": want, "tape": tape, "same_col": agree,
                   "rollout": res, "rollout_plies": plies,
                   "spawn_top": PK.spawn_top(b)})
        print(f"  c{i+1}: spawn_top={PK.spawn_top(b):2d}  eval wants "
              f"{act_str(want) if want is not None else 'NONE':>10s}  tape "
              f"{act_str(tape) if tape is not None else '?':>10s}  "
              f"{'SAME col' if agree else 'DIFFERENT col'}  |  champion rollout "
              f"from here: {res} after {plies} plies")

    # ---------------------------------------------------------------- Q3
    print("\n--- Q3 ALREADY LOST? exhaustive survival over the champion's own moves ---")
    q3 = []
    for i in range(len(commits)):
        rem = len(stream) - i - 1
        alive, exh = survivable(boards[i], stream[i:], rem)
        q3.append({"i": i, "plies": rem, "survivable": alive, "exhaustive": exh})
        print(f"  c{i+1}: over the remaining {rem} known pills -- "
              f"{'SURVIVABLE' if alive else 'LOST (every line tops out)'}"
              f"{'' if exh else '  [capped, not exhaustive]'}")

    out = {"continuity": [[int(x) for x in h] for h in tape_acts],
           "q2": q2, "q3": q3,
           "stream": stream}
    with open(os.path.join(HERE, "results/m3_counterfactual.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\nwrote results/m3_counterfactual.json")


if __name__ == "__main__":
    main()
