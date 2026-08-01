#!/usr/bin/env python3
"""Confirm WHY the >=7-cell proxy misses 82% of real double-line clears.

HYPOTHESIS: `vs_env.py` computes `cells = nonzero(before_step) - nonzero(after_step)`, but
`env.step` PLACES THE PILL (+2 cells) before resolving. So that delta is
`cleared_cells - 2`, and the >=7 test really demands 9 raw cleared cells. A genuine
2-line clear is 7 cells (H4 x V4 sharing one cell) or 8 (disjoint) -> delta 5 or 6 -> SILENT.

This prints raw `resolve()` cells against the delta the proxy actually sees.
"""
from __future__ import annotations
import sys, collections

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/combo_term", ROOT + "/tmp/pillrng",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from garbage_trigger_audit import ClearTrace


def main(n_seeds=12, level=11):
    import fast_rtl_x as F
    from drmario.faithful_env import FaithfulDrMarioEnv
    F.warmup_delta(topk2=8)
    w, fl = F.variant("winner")
    dec = F.FastShipD3DeciderEHDelta(w, fl, topk2=8)

    rows = []
    for seed in range(n_seeds):
        env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
        env.reset()
        from nes_pills import NesPillSource
        NesPillSource(seed=seed).attach(env)
        env.cur = env._rand_pill(); env.nxt = env._rand_pill()

        raw = {}
        orig_resolve = env.board.resolve
        def resolve_hook(_o=orig_resolve, _d=raw):
            r = _o()
            _d["cells"] = r[0]; _d["chain"] = r[2]
            return r
        env.board.resolve = resolve_hook
        tr = ClearTrace(env.board)

        while True:
            a = dec.choose(env.board, env.cur, env.nxt)
            if a is None:
                break
            before = int((env.board.color != 0).sum())
            tr.reset(); raw.clear()
            _, _, term, trunc, _i = env.step(int(a))
            delta = before - int((env.board.color != 0).sum())
            if tr.steps:
                rows.append((tr.steps[0], raw.get("cells", 0), delta, raw.get("chain", 0)))
            if term or trunc:
                break

    print(f"raw resolve() cells vs the delta vs_env.py measures   ({len(rows)} clearing placements)")
    print()
    off = collections.Counter(r[1] - r[2] for r in rows)
    print(f"  raw_cells - delta  distribution: {dict(sorted(off.items()))}"
          f"   <- if this is a constant 2, the placed pill is the whole story")
    print()
    print("  first-step simultaneous lines == 2 (a REAL attack):")
    dbl = [r for r in rows if r[0] >= 2]
    print(f"    n={len(dbl)}   raw cells {sorted(set(r[1] for r in dbl))}"
          f"   delta seen by proxy {sorted(set(r[2] for r in dbl))}")
    print(f"    proxy (delta>=7) fires on {sum(1 for r in dbl if r[2] >= 7)} of {len(dbl)}")
    print(f"    a CORRECTED raw>=7 test would fire on {sum(1 for r in dbl if r[1] >= 7)} of {len(dbl)}")
    print()
    sing = [r for r in rows if r[0] == 1]
    print("  first-step simultaneous lines == 1 (NOT an attack):")
    print(f"    n={len(sing)}   proxy (delta>=7) FALSELY fires on {sum(1 for r in sing if r[2] >= 7)}")
    print(f"    a CORRECTED raw>=7 test would falsely fire on {sum(1 for r in sing if r[1] >= 7)}"
          f"   <- residual = pure CASCADE conflation, unfixable by threshold")
    ch = collections.Counter(r[3] for r in sing if r[1] >= 7)
    print(f"    chain depth of those raw>=7 single-line clears: {dict(sorted(ch.items()))}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
