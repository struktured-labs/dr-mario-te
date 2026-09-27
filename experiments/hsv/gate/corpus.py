"""Adversarial + real board corpus for the bit-exactness gate.

Classes (tag -> intent):
  empty            the all-empty board (win path)
  full_*           every cell occupied (mono virus / mixed / pills / mixed both)
  single_virus     one virus, corners/edges/center/spawn-window boundaries
  virus_on_stack   virus atop pill columns (matched / buried-exempt boundaries)
  buried_suite     systematic cover-run x color x depth x >2-per-column (nearest2)
  matched_suite    cover directly-on-top cases incl. virus-above-virus
  exact4           formed 4-runs, 3-runs w/ open span, runs BLOCKED at span 3
  cross_suite      viruses completable on both axes (cross gating boundaries)
  near_win         1-2 viruses, one placement from a full clear
  no_clear         dense checkerboards, no 2-run anywhere
  cascade          stacked chains + hanging (unsettled) structures
  spawn_toprisk    single cells on the r<3 / r<4 / c in {3,4} boundaries
  wrap_stress      |prewrap| >> 32767 at ships weights: mono virus columns etc.
  rand_settled     column-packed randoms, density x virus-fraction sweep
  rand_scatter     fully random incl. floating cells
  real_*           boards lifted from the pinned RTL corpora (real distribution)

Determinism: fixed seed; the corpus file is written once and then PINNED --
gate runs always read the file, never regenerate silently.
"""
from __future__ import annotations
import random

from common import ROWS, COLS, NCELL, QA_COPRO

E = 0xFF
def V(c): return 0xD0 | c
def P(c): return 0x40 | c


class Build:
    def __init__(self):
        self.boards = []
        self.classes = []

    def add(self, cls, grid):
        assert len(grid) == NCELL
        self.boards.append(list(grid))
        self.classes.append(cls)

    def grid(self):
        return [E] * NCELL


def _put(g, r, c, v):
    g[r * COLS + c] = v


def build_corpus(seed=20260730):
    rng = random.Random(seed)
    B = Build()

    # ---- empty ----
    B.add("empty", B.grid())

    # ---- full boards ----
    for c in range(3):
        B.add("full_virus_mono", [V(c)] * NCELL)
    B.add("full_virus_mix", [V((r + c) % 3) for r in range(ROWS) for c in range(COLS)])
    B.add("full_virus_mix", [V((r * 3 + c * 5 + 1) % 3) for r in range(ROWS) for c in range(COLS)])
    B.add("full_pill_mix", [P((r + c) % 3) for r in range(ROWS) for c in range(COLS)])
    B.add("full_pill_mix", [P(rng.randrange(3)) for _ in range(NCELL)])
    B.add("full_mixed", [(V if (r + c) % 2 else P)((r * 2 + c) % 3)
                         for r in range(ROWS) for c in range(COLS)])
    B.add("full_mixed", [(V if rng.random() < 0.5 else P)(rng.randrange(3))
                         for _ in range(NCELL)])

    # ---- single virus at boundary positions ----
    POS = [(0, 0), (0, 7), (15, 0), (15, 7), (0, 3), (0, 4), (2, 3), (3, 3),
           (3, 4), (4, 4), (2, 2), (3, 5), (8, 4), (15, 4), (12, 7)]
    for c in range(3):
        for (r, cc) in POS:
            g = B.grid(); _put(g, r, cc, V(c))
            B.add("single_virus", g)

    # ---- virus on pill stacks: matched + color-aware exemption boundaries ----
    for vc in range(3):
        for cover in ([], [0], [1], [vc], [vc, vc], [vc, (vc + 1) % 3],
                      [(vc + 1) % 3, vc], [vc, vc, vc], [(vc + 1) % 3] * 3):
            g = B.grid()
            col = 2
            r = ROWS - 1 - len(cover)
            _put(g, r, col, V(vc))
            for k, pc in enumerate(cover):
                _put(g, r + 1 + k, col, P(pc))
            B.add("virus_on_stack", g)

    # ---- buried suite: fill above virus, cover-run lengths, nearest2 cap ----
    for vc in range(3):
        for depth in (1, 2, 3, 5):
            for runlen in (0, 1, 2, 3):
                g = B.grid()
                col = 4
                vr = ROWS - 1
                _put(g, vr, col, V(vc))
                r = vr - 1
                for k in range(depth):          # diff-color junk directly above
                    _put(g, r, col, P((vc + 1 + k % 2) % 3)); r -= 1
                for k in range(runlen):         # same-color run ENDING just above the junk
                    _put(g, r, col, P(vc)); r -= 1
                B.add("buried_suite", g)
    for nvir in (2, 3, 4, 6):                   # >2 viruses per column: nearest2 cap
        for vc in range(3):
            g = B.grid()
            col = 1
            r = ROWS - 1
            for k in range(nvir):
                _put(g, r, col, V(vc)); r -= 1
                _put(g, r, col, P((vc + 1) % 3)); r -= 1
            B.add("buried_suite", g)

    # ---- matched suite ----
    for vc in range(3):
        g = B.grid(); _put(g, 15, 3, V(vc)); _put(g, 14, 3, P(vc))
        B.add("matched_suite", g)
        g = B.grid(); _put(g, 15, 3, V(vc)); _put(g, 14, 3, P((vc + 1) % 3))
        B.add("matched_suite", g)
        g = B.grid(); _put(g, 15, 3, V(vc)); _put(g, 14, 3, V(vc))   # virus cover: NOT matched
        B.add("matched_suite", g)
        g = B.grid(); _put(g, 0, 3, V(vc))                            # top row: no cover possible
        B.add("matched_suite", g)
        g = B.grid()                                                  # interleaved P V P V
        for k, r in enumerate(range(15, 11, -1)):
            _put(g, r, 5, V(vc) if k % 2 == 0 else P(vc))
        B.add("matched_suite", g)

    # ---- exact-4 runs / spans ----
    for c in range(3):
        for row in (15, 8, 0):
            g = B.grid()                                    # formed H 4-run of pills + virus
            _put(g, row, 2, V(c))
            for k in range(3):
                _put(g, row, 3 + k, P(c))
            B.add("exact4", g)
        g = B.grid()                                        # V 4-run
        _put(g, 15, 6, V(c))
        for k in range(3):
            _put(g, 12 + k, 6, P(c))
        B.add("exact4", g)
        g = B.grid()                                        # 3-run, open span (rdy fires)
        _put(g, 15, 0, V(c)); _put(g, 15, 1, P(c)); _put(g, 15, 2, P(c))
        B.add("exact4", g)
        g = B.grid()                                        # 3-run BLOCKED: span exactly 3
        _put(g, 15, 0, V(c)); _put(g, 15, 1, P(c)); _put(g, 15, 2, P(c))
        _put(g, 15, 3, P((c + 1) % 3))
        B.add("exact4", g)
        g = B.grid()                                        # span exactly 4 boundary
        _put(g, 15, 1, V(c)); _put(g, 15, 2, P(c)); _put(g, 15, 3, P(c))
        _put(g, 15, 0, P((c + 2) % 3)); _put(g, 15, 4, E); _put(g, 15, 5, P((c + 1) % 3))
        B.add("exact4", g)
        g = B.grid()                                        # vertical span-blocked at 3
        _put(g, 15, 4, V(c)); _put(g, 14, 4, P(c)); _put(g, 13, 4, P((c + 1) % 3))
        B.add("exact4", g)

    # ---- cross suite: both-axis completable viruses ----
    for c in range(3):
        g = B.grid()                                        # run_h=2, run_v=2, both spans open
        _put(g, 12, 3, V(c)); _put(g, 12, 4, P(c)); _put(g, 13, 3, P(c))
        B.add("cross_suite", g)
        g = B.grid()                                        # run_h=2, run_v=1 (gate must NOT fire)
        _put(g, 12, 3, V(c)); _put(g, 12, 4, P(c))
        B.add("cross_suite", g)
        g = B.grid()                                        # run_v=2, run_h=1 (gate must NOT fire)
        _put(g, 12, 3, V(c)); _put(g, 13, 3, P(c))
        B.add("cross_suite", g)
        g = B.grid()                                        # both runs 3: hq=vq=9
        _put(g, 10, 3, V(c)); _put(g, 10, 4, P(c)); _put(g, 10, 5, P(c))
        _put(g, 11, 3, P(c)); _put(g, 12, 3, P(c))
        B.add("cross_suite", g)

    # ---- near-win ----
    for c in range(3):
        g = B.grid()
        _put(g, 15, 2, V(c)); _put(g, 15, 3, P(c)); _put(g, 15, 4, P(c))
        _put(g, 14, 6, P((c + 1) % 3)); _put(g, 15, 6, P((c + 1) % 3))
        B.add("near_win", g)
        g = B.grid()
        _put(g, 15, 0, V(c)); _put(g, 14, 0, P(c)); _put(g, 13, 0, P(c))
        _put(g, 15, 7, V((c + 1) % 3))
        B.add("near_win", g)

    # ---- no-clear dense checkerboards ----
    heights = [(16,) * 8, (3, 7, 12, 16, 16, 12, 7, 3), (1, 2, 3, 4, 5, 6, 7, 8)]
    for hi, hs in enumerate(heights):
        for phase in (0, 1):
            g = B.grid()
            for c in range(COLS):
                for k in range(hs[c]):
                    r = ROWS - 1 - k
                    cell = (r + c + phase) % 2
                    color = (r + 2 * c + phase) % 3
                    g[r * COLS + c] = V(color) if cell else P(color)
            B.add("no_clear", g)

    # ---- cascade / hanging (unsettled) ----
    for c in range(3):
        g = B.grid()                    # clearing bottom row would form a second 4-run
        for k in range(4):
            _put(g, 15, 2 + k, P(c))
            _put(g, 14, 2 + k, P((c + 1) % 3))
            _put(g, 13, 2 + k, P((c + 1) % 3))
            _put(g, 12, 2 + k, P((c + 1) % 3))
        _put(g, 11, 2, P((c + 1) % 3))  # 4th of the follow-up run, hanging high
        B.add("cascade", g)
        g = B.grid()                    # floating pills over a gap (unsettled input)
        _put(g, 5, 3, P(c)); _put(g, 5, 4, P(c))
        _put(g, 15, 3, V((c + 1) % 3))
        B.add("cascade", g)
        g = B.grid()                    # tower: alternating pairs ready to chain
        for r in range(15, 3, -1):
            _put(g, r, 6, P(c if r % 4 < 2 else (c + 1) % 3))
        _put(g, 15, 5, V(c))
        B.add("cascade", g)

    # ---- spawn/toprisk boundary singles (pills so no virus terms interfere) ----
    for (r, c) in [(0, 3), (2, 3), (3, 3), (4, 3), (0, 4), (2, 4), (3, 4),
                   (4, 4), (3, 2), (3, 5), (2, 2), (2, 5), (0, 0), (2, 7)]:
        g = B.grid(); _put(g, r, c, P(1))
        # ground the column below so the cell is "settled" for delta-style candidates
        for rr in range(r + 1, ROWS):
            _put(g, rr, c, P((rr + 1) % 2 * 2))
        B.add("spawn_toprisk", g)

    # ---- wrap stress: huge vrdy/rdy_ext via mono-color virus columns ----
    for ncols in range(1, 9):
        g = B.grid()
        for c in range(ncols):
            for r in range(ROWS):
                _put(g, r, c, V(0))
        B.add("wrap_stress", g)
    for ncols in (3, 5, 7):              # 12-high versions (different multiples)
        g = B.grid()
        for c in range(ncols):
            for r in range(4, ROWS):
                _put(g, r, c, V(1))
        B.add("wrap_stress", g)
    g = [V(2)] * NCELL                   # all-virus minus a few cells
    for i in (0, 37, 90):
        g[i] = E
    B.add("wrap_stress", g)
    g = [V(0)] * NCELL
    g[5] = P(1)
    B.add("wrap_stress", g)
    for nrows in (2, 4, 6):              # mono virus ROWS: giant run_h + rdy_ext
        g = B.grid()
        for r in range(ROWS - nrows, ROWS):
            for c in range(COLS):
                _put(g, r, c, V(0))
        B.add("wrap_stress", g)

    # ---- randoms ----
    for dens in (0.15, 0.3, 0.5, 0.7, 0.85):
        for vfrac in (0.2, 0.5, 0.9):
            for _ in range(8):
                g = B.grid()
                for c in range(COLS):
                    h = 0
                    for r in range(ROWS):
                        if rng.random() < dens:
                            h += 1
                    for k in range(h):
                        r = ROWS - 1 - k
                        color = rng.randrange(3)
                        g[r * COLS + c] = V(color) if rng.random() < vfrac else P(color)
                B.add("rand_settled", g)
    for dens in (0.1, 0.3, 0.6):
        for _ in range(20):
            g = B.grid()
            for i in range(NCELL):
                if rng.random() < dens:
                    color = rng.randrange(3)
                    g[i] = V(color) if rng.random() < 0.4 else P(color)
            B.add("rand_scatter", g)

    # ---- real boards from the pinned RTL corpora ----
    def _add_real(path, cls, stride):
        try:
            toks = open(path).read().split()
        except FileNotFoundError:
            return
        n = int(toks[0]); toks = toks[1:]
        for k in range(n):
            row = toks[k * stride:(k + 1) * stride]
            if cls == "real_hostdata":       # cA cB nA nB ec eo + 128 cells
                cells = [int(x, 16) for x in row[6:134]]
            else:                            # leafeval: 128 cells + sco + win
                cells = [int(x, 16) for x in row[:128]]
            B.add(cls, cells)

    _add_real(QA_COPRO + "/leafeval_cases.txt", "real_leafcases", 130)
    _add_real(QA_COPRO + "/hostdata_real.txt", "real_hostdata", 134)
    # node-case parent boards (first 128 tokens of each 266-token record)
    try:
        toks = open(QA_COPRO + "/leafeval_node_cases.txt").read().split()
        n = int(toks[0]); toks = toks[1:]
        for k in range(n):
            rec = toks[k * 266:(k + 1) * 266]
            B.add("real_nodeparents", [int(x, 16) for x in rec[:128]])
    except FileNotFoundError:
        pass

    return B.boards, B.classes


if __name__ == "__main__":
    import collections
    boards, classes = build_corpus()
    print(len(boards), "boards")
    for k, v in collections.Counter(classes).items():
        print("  %-18s %d" % (k, v))
