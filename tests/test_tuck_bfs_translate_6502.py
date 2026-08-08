#!/usr/bin/env python3
"""Validation for the CANDLIST translation step (tuck_bfs_translate_6502.py).

1. tr_derive-level checks: reuses translate_ref.py's python model, already validated
   standalone (0/732 mismatches vs tuck_scan_v3_ref.py's own rule on 400 boards; the
   known scan_v3-over-approximation case correctly excluded -- see that file's docstring).
2. Full chain (tuck_bfs -> tr_translate -> CANDLIST) under py65 vs translate_ref.py's
   translate_candidates(), on real corpus boards.
3. scan_v3 cross-check: every CANDLIST entry the chain produces must also be found by
   tuck_scan_v3_ref.ref_tuck_scan_v3's own (uncapped) rule with the SAME approach/trigger
   -- any mismatch is exactly the "scan_v3-only surprise" class to investigate.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))
from py65_harness import Cpu
import tuck_bfs_translate_6502 as TRB
import tuck_bfs_6502 as TB
import translate_ref as TR

sys.path.insert(0, "/home/struktured/projects/dr_mario_rl/tmp/endgame")
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments")
from fb import ROWS, COLS  # noqa: E402

os.environ.setdefault("DRCANON", "/home/struktured/projects/dr-mario-canonical-wt")
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/fpga/copro/tuck_validation")
import tuck_scan_v3_ref as SV3  # noqa: E402

EMPTY = 0xFF


def fb_to_nes(grid):
    return [EMPTY if c == 0 else c for c in grid]


def my_bfs_candidates_priority(grid, ca, cb):
    """The SAME set + order tuck_bfs_6502's own emit phase produces (already proven
    bit-exact, task #17 stage 4): descending row, ascending col*4+orient."""
    import tuck_enum as TE
    cands = [p for p in TE.enumerate(grid, ca, cb, mode="free", union_straight_drops=False)
             if p["reachable"]]
    cands.sort(key=lambda p: (-p["row"], p["col"] * 4 + p["orient"]))
    return [(p["col"], p["row"], p["orient"], ca, cb) for p in cands]


def read_candlist(cpu):
    n = cpu.mem[TRB.TS_CNT]
    dropped = cpu.mem[TRB.TS_DROP]
    out = []
    for i in range(n):
        base = TRB.CANDLIST + i * 5
        out.append(tuple(cpu.mem[base + k] for k in range(5)))
    return n, dropped, out


def stage_full_chain(corpus_path, n_boards=None):
    with open(corpus_path) as f:
        corpus = json.load(f)["boards"]
    if n_boards:
        corpus = corpus[:n_boards]
    a = TRB.build_combined()
    code = a.assemble()
    bfs_addr = a.base + a.labels["tuck_bfs"]
    tr_addr = a.base + a.labels["tr_translate"]
    cpu = Cpu()
    cpu.load(a.base, code)

    bad = 0
    scanv3_surprises = 0
    total_candlist = 0
    total_dropped = 0
    for rec in corpus:
        grid = rec["col"]
        ca, cb = rec["ca"], rec["cb"]
        board = fb_to_nes(grid)
        cpu.set_board(board)
        cpu.set_zp(TB.PILL_A, ca)
        cpu.set_zp(TB.PILL_B, cb)
        cpu.call(bfs_addr, max_steps=4_000_000)
        cpu.call(tr_addr, max_steps=4_000_000)
        n, dropped, got = read_candlist(cpu)
        total_candlist += n
        total_dropped += dropped

        my_cands = my_bfs_candidates_priority(grid, ca, cb)
        exp, exp_dropped = TR.translate_candidates(board, my_cands, capacity=TRB.CAPACITY)
        if got != exp or n != len(exp):
            bad += 1
            if bad <= 5:
                print(f"  MISMATCH board id={rec.get('id')}: got={got} exp={exp}")

        # scan_v3 cross-check on this board's CANDLIST entries
        sv3_cands, _ = SV3.ref_tuck_scan_v3(board, capacity=10**9)
        sv3_by_key = {}
        for c in sv3_cands:
            key = (c["target"], c["rest"], c["orient"] in (1, 3))
            sv3_by_key.setdefault(key, (c["approach"], c["trigger"]))
        for (target, approach, trigger, rest, orient) in got:
            key = (target, rest, orient in (1, 3))
            if sv3_by_key.get(key) != (approach, trigger):
                scanv3_surprises += 1
                print(f"  SCAN_V3 SURPRISE board id={rec.get('id')}: "
                      f"mine={(target, approach, trigger, rest, orient)} "
                      f"scanv3={sv3_by_key.get(key)}")

    n_total = len(corpus)
    print(f"[full-chain] {n_total - bad}/{n_total} boards match translate_ref exactly")
    print(f"  CANDLIST entries: total={total_candlist} "
          f"mean={total_candlist / n_total:.2f}  dropped: total={total_dropped} "
          f"mean={total_dropped / n_total:.2f}")
    print(f"  scan_v3 cross-check surprises: {scanv3_surprises} (must be 0)")
    return bad == 0 and scanv3_surprises == 0


if __name__ == "__main__":
    corpus = os.path.join(os.path.dirname(__file__), "tuck_bfs_corpus_200.json")
    ok = stage_full_chain(corpus, n_boards=50)
    sys.exit(0 if ok else 1)
