#!/usr/bin/env python3
"""M1: is the VS garbage trigger measuring what it claims to?

`vs_env.py` fires an attack when a placement removes >= 7 cells, documented there as a
"near-perfect proxy" for a >=2-simultaneous-line clear (4+4 minus a shared corner).

THE SUSPICION: `FaithfulBoard.resolve()` loops clear -> gravity -> clear until stable and
returns `(total_cells, viruses, chain)`. A single 4-cell line that CASCADES into another
4-cell line is 8 cells with chain=2 -- that is SEQUENTIAL, not simultaneous, and the real
rule keys on simultaneity. The proxy cannot tell those apart because it only sees the total.

Since the garbage rate IS the objective of the self-play tuning, a mis-firing trigger makes
every downstream win-rate number a measurement of the wrong game.

WHAT THIS DOES: wraps `_find_clears` per env INSTANCE (never the shared class) to capture the
board state at every clear step of every resolve, counts maximal runs >= 4 at each step, and
compares the exact first-step line count against the >=7-cell proxy on real self-play games.
"""
from __future__ import annotations
import sys, os, collections

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

EMPTY = 0


def count_lines(color) -> int:
    """Number of MAXIMAL runs of >= 4 same-colour cells (horizontal + vertical).

    Mirrors `FaithfulBoard._find_clears` scan order exactly, but counts RUNS instead of
    painting a mask -- the mask loses the run structure, which is the thing we need.
    A cell in both an H and a V run counts once per run, matching "lines cleared".
    """
    rows, cols = color.shape
    n = 0
    for r in range(rows):
        c = 0
        while c < cols:
            v = color[r, c]
            if v == EMPTY:
                c += 1
                continue
            c2 = c
            while c2 < cols and color[r, c2] == v:
                c2 += 1
            if c2 - c >= 4:
                n += 1
            c = c2
    for c in range(cols):
        r = 0
        while r < rows:
            v = color[r, c]
            if v == EMPTY:
                r += 1
                continue
            r2 = r
            while r2 < rows and color[r2, c] == v:
                r2 += 1
            if r2 - r >= 4:
                n += 1
            r = r2
    return n


class ClearTrace:
    """Per-INSTANCE hook on board._find_clears recording each clear step of each resolve."""

    def __init__(self, board):
        self.board = board
        self.steps = []                 # lines cleared at each clear step of current resolve
        self._orig = board._find_clears
        board._find_clears = self._hook

    def _hook(self):
        lines = count_lines(self.board.color)
        mask = self._orig()
        if mask.any():
            self.steps.append(lines)
        return mask

    def reset(self):
        self.steps = []


def audit(n_seeds=30, level=11, max_pills=300, nes_pills=True):
    import fast_rtl_x as F
    from drmario.faithful_env import FaithfulDrMarioEnv
    F.warmup_delta(topk2=8)
    w, fl = F.variant("winner")
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)

    tally = collections.Counter()
    firststep_lines = collections.Counter()
    chain_hist = collections.Counter()
    clears = 0
    placements = 0

    for seed in range(n_seeds):
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
        env.reset()
        if nes_pills:
            from nes_pills import NesPillSource
            NesPillSource(seed=seed).attach(env)
            env.cur = env._rand_pill(); env.nxt = env._rand_pill()
        tr = ClearTrace(env.board)
        while True:
            a = dec.choose(env.board, env.cur, env.nxt)
            if a is None:
                break
            before = (env.board.color != 0).sum()
            tr.reset()
            _, _, term, trunc, info = env.step(int(a))
            placements += 1
            cells = int(before - (env.board.color != 0).sum())
            if tr.steps:
                clears += 1
                exact = tr.steps[0]                    # SIMULTANEOUS lines, first step only
                proxy = cells >= 7
                truth = exact >= 2
                firststep_lines[exact] += 1
                chain_hist[len(tr.steps)] += 1
                tally[("fire" if proxy else "hold", "attack" if truth else "no-attack")] += 1
            if term or trunc:
                break
    return tally, firststep_lines, chain_hist, clears


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    lvl = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    tally, fs, ch, clears = audit(n_seeds=n, level=lvl)
    tp = tally[("fire", "attack")]; fp = tally[("fire", "no-attack")]
    fn = tally[("hold", "attack")]; tn = tally[("hold", "no-attack")]
    print(f"GARBAGE-TRIGGER AUDIT  (L{lvl}, {n} seeds, REAL NES capsules, {clears} clearing placements)")
    print()
    print("  proxy `cells>=7`   vs   exact `first-step simultaneous lines >= 2`")
    print(f"    true  fire   : {tp:6d}   (proxy right, attack)")
    print(f"    FALSE fire   : {fp:6d}   (proxy attacks, truth says NO -- cascade conflation)")
    print(f"    FALSE hold   : {fn:6d}   (proxy silent, truth says attack)")
    print(f"    true  hold   : {tn:6d}")
    fires = tp + fp
    truth = tp + fn
    if fires:
        print(f"\n    of {fires} proxy attacks, {fp} are WRONG = {fp/fires:.1%} false-fire rate")
    if truth:
        print(f"    of {truth} real attacks, {fn} are MISSED = {fn/truth:.1%} miss rate")
    print(f"    proxy fires {fires} times, truth fires {truth} times"
          f"  => proxy is {'OVER' if fires > truth else 'UNDER'}-firing by "
          f"{abs(fires-truth)/max(truth,1):.1%}")
    print(f"\n  simultaneous lines on first clear step: {dict(sorted(fs.items()))}")
    print(f"  chain depth (clear steps per resolve)  : {dict(sorted(ch.items()))}")
    print(f"\n  ★ 3+ simultaneous lines: {sum(v for k,v in fs.items() if k>=3)}"
          f"  -- relevant because MECHANICS_NES says 'more lines = more garbage',"
          f" while the spec'd rule caps at 2 tiles")
