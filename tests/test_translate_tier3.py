#!/usr/bin/env python3
"""Validation for translate_ref_tier3.py (task #17, tier-3 mission, 2026-08-05).

Two stages:
  1. Self-contained soundness checks (no cross-repo dependency): mono_reach's
     planes must be SUBSETS of the full row_bfs_visited plane (a monotonic path
     is a restriction of an unconstrained one -- if this ever fails, mono_reach
     has a bug, since it should only ever find LESS than the full BFS, never more).
  2. Coverage validation against translatable.py's tier_of() ladder (cross-repo:
     dr-mario-qa-wt/experiments/eval47 -- the SAME cross-repo pattern this branch
     already uses in trajectory_fire_proof.py) on the 200-board real-L11 corpus:
     the cascade (tier1 unchanged, tier3 as fallback) must recover the
     tier_of()<=3 population with ZERO over-accepts (nothing tier_of()>3 ever gets
     a descriptor -- the safety-critical direction) and reports the achieved
     coverage. See translate_ref_tier3.py's own module docstring for the measured
     97.7% figure and the one documented, safety-motivated root cause of the gap.
"""
import sys
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translate_ref as TR  # noqa: E402
import translate_ref_tier3 as T3  # noqa: E402

CORPUS = os.path.join(HERE, "tuck_bfs_corpus_200.json")
EMPTY_NES = 0xFF


def to_nes(col):
    return [EMPTY_NES if int(c) == 0 else int(c) for c in col]


def stage_soundness(n_boards=40):
    """mono_L/mono_R planes must be subsets of the full visited plane, for every
    board, row, and state -- checked directly, not sampled."""
    corpus = json.load(open(CORPUS))
    bad = 0
    checked = 0
    for b in corpus["boards"][:n_boards]:
        board = to_nes(b["col"])
        visited = TR.row_bfs_visited(board)
        mono_L = T3.mono_reach(board, "L")
        mono_R = T3.mono_reach(board, "R")
        for y in range(TR.ROWS):
            for s in range(32):
                checked += 1
                if mono_L[y][s] and not visited[y][s]:
                    bad += 1
                    print(f"  SUBSET VIOLATION (L): board {b['id']} y={y} s={s}")
                if mono_R[y][s] and not visited[y][s]:
                    bad += 1
                    print(f"  SUBSET VIOLATION (R): board {b['id']} y={y} s={s}")
    print(f"[soundness] {n_boards} boards, {checked} (y,s) cells checked, "
          f"{bad} subset violations")
    return bad == 0


def _translate_cascade(board, target, rest, orient, visited, mono_L, mono_R):
    got = TR.derive_verified(board, target, rest, orient, visited)
    if got is not None:
        return got, 1
    got = T3.derive_tier3_verified(board, target, rest, orient, visited, mono_L, mono_R)
    if got is not None:
        return got, 3
    return None, None


def stage_coverage():
    QA_EVAL47 = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
    QA_EXPERIMENTS = "/home/struktured/projects/dr-mario-qa-wt/experiments"
    sys.path.insert(0, QA_EVAL47)
    sys.path.insert(0, QA_EXPERIMENTS)
    import translatable as TL  # noqa: E402 (cross-repo, see module docstring)
    import tuck_enum as TE  # noqa: E402

    corpus = json.load(open(CORPUS))
    n_le3, n_found, n_over = 0, 0, 0
    found_by_tier = {1: 0, 3: 0}
    missed = []
    over_accepts = []
    for b in corpus["boards"]:
        col = b["col"]
        board = to_nes(col)
        placements = TE.enumerate(col, 1, 1, mode="free")
        tucks = [p for p in placements if p["is_tuck"]]
        if not tucks:
            continue
        mono_L = T3.mono_reach(board, "L")
        mono_R = T3.mono_reach(board, "R")
        visited = TR.row_bfs_visited(board)
        for p in tucks:
            tier = TL.tier_of(col, p)
            target, rest, orient = p["col"], p["row"], p["orient"]
            got, found_at = _translate_cascade(board, target, rest, orient,
                                                visited, mono_L, mono_R)
            if tier <= 3:
                n_le3 += 1
                if got is not None:
                    n_found += 1
                    found_by_tier[found_at] += 1
                else:
                    missed.append((b["id"], target, rest, orient, tier))
            else:
                if got is not None:
                    n_over += 1
                    over_accepts.append((b["id"], target, rest, orient, tier, got))

    pct = 100.0 * n_found / n_le3 if n_le3 else 0.0
    print(f"[coverage] tier<=3 population: {n_le3}, found: {n_found} ({pct:.1f}%)")
    print(f"[coverage] found via tier1: {found_by_tier[1]}, "
          f"via tier3 fallback: {found_by_tier[3]}")
    print(f"[coverage] over-accepts (tier>3 claimed): {n_over}")
    if over_accepts:
        for oa in over_accepts[:20]:
            print("  OVER-ACCEPT", oa)
    print(f"[coverage] misses: {len(missed)} (see translate_ref_tier3.py's module "
          f"docstring for the documented root cause)")
    return n_over == 0, n_found, n_le3


def main():
    ok_sound = stage_soundness()
    ok_safe, n_found, n_le3 = stage_coverage()
    print("PASS" if (ok_sound and ok_safe) else "FAIL")
    sys.exit(0 if (ok_sound and ok_safe) else 1)


if __name__ == "__main__":
    main()
