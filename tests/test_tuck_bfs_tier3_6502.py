#!/usr/bin/env python3
"""Bit-exact gate for tuck_bfs_tier3_6502.py (task #17, tier-3 mission, 2026-08-05).

Calls tr_derive_cascade DIRECTLY (not through the full tuck_bfs enumeration --
that's covered by stage_full_chain below) for every tuck-class (target,rest,
orient) tuple on the 200-board real-L11 corpus, and compares
FOUND/(approach,trigger) against the Python reference cascade (translate_ref.
derive_verified for tier 1, translate_ref_tier3.derive_tier3_verified as the
fallback -- the SAME cascade test_translate_tier3.py already validated at
1456/1490, 0 over-accepts).

Then a smaller full-chain stage runs the REAL tuck_bfs enumeration -> CANDLIST
via tr_translate_tier3 (not tr_translate) on a handful of boards, confirming the
integration point (BFS_OUT_* -> CANDLIST through the cascade) matches too.
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from py65_harness import Cpu  # noqa: E402
import tuck_bfs_6502 as TB  # noqa: E402
import tuck_bfs_translate_6502 as TRB  # noqa: E402
import tuck_bfs_tier3_6502 as T3  # noqa: E402
import translate_ref as TR  # noqa: E402
import translate_ref_tier3 as T3R  # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tuck_bfs_corpus_200.json")
EMPTY_NES = 0xFF


def to_nes(col):
    return [EMPTY_NES if int(c) == 0 else int(c) for c in col]


def py_cascade(board, target, rest, orient, visited, mono_L, mono_R):
    got = TR.derive_verified(board, target, rest, orient, visited)
    if got is not None:
        return got
    return T3R.derive_tier3_verified(board, target, rest, orient, visited, mono_L, mono_R)


def stage_direct(n_boards=200, max_candidates_per_board=None):
    """Calls tr_derive_cascade directly for every tuck-class candidate tuck_enum
    reports, comparing against the Python cascade -- exercises tier3's search
    loop and mono_reach construction without depending on tuck_bfs's own
    enumeration output being wired up correctly (that's stage_full_chain)."""
    QA_EXPERIMENTS = "/home/struktured/projects/dr-mario-qa-wt/experiments"
    sys.path.insert(0, QA_EXPERIMENTS)
    import tuck_enum as TE  # noqa: E402

    corpus = json.load(open(CORPUS))["boards"][:n_boards]

    a = T3.build_combined()
    code = a.assemble()
    print(f"[gate] assembled {len(code)} bytes, {len(a.labels)} labels")
    bfs_addr = a.base + a.labels["tuck_bfs"]
    setup_addr = a.base + a.labels["t3_setup_board"]
    cascade_addr = a.base + a.labels["tr_derive_cascade"]
    cpu = Cpu()
    cpu.load(a.base, code)

    n_checked = 0
    n_mismatch = 0
    mismatches = []
    t0 = time.time()
    for b in corpus:
        col = b["col"]
        board = to_nes(col)
        cpu.set_board(board)
        # tier 1's own defensive check (tb_vis_test, inside tr_derive) reads
        # BFS_VIS -- it's only populated by running tuck_bfs's main enumeration
        # first, exactly as production does (tuck_bfs always runs before any
        # translation step touches BFS_VIS). PILL_A/PILL_B don't affect
        # reachability, any value is fine here.
        cpu.set_zp(TB.PILL_A, 1)
        cpu.set_zp(TB.PILL_B, 2)
        cpu.call(bfs_addr, max_steps=6_000_000)
        # t3_setup_board ONCE per board (tr3_derive no longer rebuilds MONO_VIS_L/
        # R itself -- see that routine's docstring for the per-candidate-rebuild
        # regression this fixed).
        cpu.call(setup_addr, max_steps=6_000_000)

        placements = TE.enumerate(col, 1, 1, mode="free")
        tucks = [p for p in placements if p["is_tuck"]]
        if max_candidates_per_board:
            tucks = tucks[:max_candidates_per_board]
        if not tucks:
            continue

        visited = TR.row_bfs_visited(board)
        mono_L = T3R.mono_reach(board, "L")
        mono_R = T3R.mono_reach(board, "R")

        for p in tucks:
            target, rest, orient = p["col"], p["row"], p["orient"]
            is_vert = orient in (1, 3)

            cpu.set_zp(TRB.TR_TARGET, target)
            cpu.set_zp(TRB.TR_REST, rest)
            cpu.set_zp(TRB.TR_ORIENT, orient)
            cpu.set_zp(TRB.TR_ISVERT, 1 if is_vert else 0)
            cpu.call(cascade_addr, max_steps=6_000_000)
            found_6502 = cpu.mem[TRB.TR_FOUND]
            got_6502 = ((cpu.mem[TRB.TR_A], cpu.mem[TRB.TR_R]) if found_6502 else None)

            got_py = py_cascade(board, target, rest, orient, visited, mono_L, mono_R)

            n_checked += 1
            if got_6502 != got_py:
                n_mismatch += 1
                mismatches.append((b["id"], target, rest, orient, got_py, got_6502))

    elapsed = time.time() - t0
    print(f"[gate] direct: {n_checked} candidates checked, {n_mismatch} mismatches, "
          f"{elapsed:.1f}s")
    for m in mismatches[:20]:
        print("  MISMATCH", m)
    return n_mismatch == 0, n_checked


def stage_full_chain(n_boards=15):
    """tuck_bfs -> tr_translate_tier3 -> CANDLIST, full integration, vs the
    Python cascade run through translate_ref's own translate_candidates-style
    loop (rebuilt here since translate_ref.translate_candidates is tier-1-only)."""
    corpus = json.load(open(CORPUS))["boards"][:n_boards]
    a = T3.build_combined()
    code = a.assemble()
    bfs_addr = a.base + a.labels["tuck_bfs"]
    tr3_addr = a.base + a.labels["tr_translate_tier3"]
    cpu = Cpu()
    cpu.load(a.base, code)

    def my_bfs_candidates_priority(grid, ca, cb):
        import tuck_enum as TE
        cands = [p for p in TE.enumerate(grid, ca, cb, mode="free",
                                          union_straight_drops=False) if p["reachable"]]
        cands.sort(key=lambda p: (-p["row"], p["col"] * 4 + p["orient"]))
        return [(p["col"], p["row"], p["orient"]) for p in cands]

    def py_translate_cascade(board, bfs_cands, capacity):
        visited = TR.row_bfs_visited(board)
        mono_L = T3R.mono_reach(board, "L")
        mono_R = T3R.mono_reach(board, "R")
        out, dropped = [], 0
        for (x, y, o) in bfs_cands:
            if len(out) >= capacity:
                dropped += 1
                continue
            got = py_cascade(board, x, y, o, visited, mono_L, mono_R)
            if got is None:
                dropped += 1
                continue
            approach, trigger = got
            out.append((x, approach, trigger, y, o))
        return out, dropped

    bad = 0
    total_n, total_dropped = 0, 0
    for rec in corpus:
        grid = rec["col"]
        ca, cb = rec["ca"], rec["cb"]
        board = to_nes(grid)
        cpu.set_board(board)
        cpu.set_zp(TB.PILL_A, ca)
        cpu.set_zp(TB.PILL_B, cb)
        cpu.call(bfs_addr, max_steps=6_000_000)
        cpu.call(tr3_addr, max_steps=15_000_000)

        n = cpu.mem[TRB.TS_CNT]
        dropped = cpu.mem[TRB.TS_DROP]
        got = [tuple(cpu.mem[TRB.CANDLIST + i * 5 + k] for k in range(5)) for i in range(n)]
        total_n += n
        total_dropped += dropped

        my_cands = my_bfs_candidates_priority(grid, ca, cb)
        exp, exp_dropped = py_translate_cascade(board, my_cands, TRB.CAPACITY)
        if got != exp or n != len(exp):
            bad += 1
            print(f"  FULL-CHAIN MISMATCH board {rec['id']}: got n={n} {got[:3]}..., "
                  f"exp n={len(exp)} {exp[:3]}...")

    print(f"[gate] full-chain: {len(corpus)} boards, {bad} mismatches, "
          f"total CANDLIST entries {total_n}, dropped {total_dropped}")
    return bad == 0


def main():
    ok1, n_checked = stage_direct()
    ok2 = stage_full_chain()
    print("PASS" if (ok1 and ok2) else "FAIL")
    sys.exit(0 if (ok1 and ok2) else 1)


if __name__ == "__main__":
    main()
