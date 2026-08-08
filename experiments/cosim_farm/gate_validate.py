#!/usr/bin/env python3
"""VALIDATION GATE (a/c/d/e). Gate (b), agreement vs the stock co-sim, is gate_agree.py.

Nothing this farm produces should be believed until every check here passes. Each one
targets a specific way the harness could be silently wrong:

  (e) ORIENTATION -- pure, instant. VAR_OF_O4 (recovered empirically from the pinned RTL
      node corpus by experiments/bitexact_gate/gate.py) and RING_OF_O4 (read off
      tuck_v3.py's O4_TABLE) are two INDEPENDENT statements about the same four codes.
      They must agree on horizontal-vs-vertical and on colour order for all four. Getting
      this backwards swaps H for V and every game still "runs".

  (d) PHYSICS -- pure, instant. game.fall_from() is the only physics this lane
      reimplements, and it is used only for tucks. Gate it by requiring that, when
      dropped from the top, it reproduces the faithful sim's own resting_position() on
      every (board, column, orientation) in a large random sample. Validated physics
      rather than a second opinion.

  (a) DETERMINISM -- expensive (runs real games). Two forms, because they fail
      differently:
        a1 same seed, two FRESH co-sim processes  -> identical game
        a2 same seed, run FIRST vs run Nth in one LONG-LIVED process -> identical game
      a2 is the one that matters for the farm: workers reuse a co-sim across many games,
      so any state leaking between games (search RAM at $6100-$61FF, the DONE latch, the
      tuck mailbox) would make results depend on scheduling order -- unreproducible, and
      worse, it would silently break paired-seed A/B comparability. Testing the DEFECT
      (reuse) rather than asserting the guard (reset-on-GO exists in the RTL).

Usage: gate_validate.py --fw <dir> [--fast] [--out result.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
for _p in (HERE, RL + "/.claude/worktrees/faithful-sim/src"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import game as G          # noqa: E402
from cosim import Cosim, VAR_OF_O4  # noqa: E402

BUILD = os.environ.get("COSIM_FARM_BUILD", os.path.join(HERE, "build"))
FARM_BIN = os.path.join(BUILD, "obj_farm", "farm_vsim")


# --------------------------------------------------------------------- (e) orientation
def gate_orientation():
    """VAR_OF_O4 and RING_OF_O4 must describe the same four placements."""
    from drmario.faithful_game import Pill, ORIENT_H, ORIENT_V
    rows = []
    ok = True
    for o4 in range(4):
        variant = VAR_OF_O4[o4]
        ring = G.RING_OF_O4[o4]
        # from the variant side (faithful_env._decode's convention)
        v_is_h = variant in (0, 1)
        v_flip = variant in (1, 3)
        # from the ring side (tuck_enum's convention)
        r_is_h = G.RING_IS_H[ring]
        r_flip = bool(G.RING_FLIP[ring])
        agree = (v_is_h == r_is_h) and (v_flip == r_flip)
        ok = ok and agree
        rows.append({"o4": o4, "variant": variant, "ring": ring,
                     "variant_horizontal": v_is_h, "ring_horizontal": r_is_h,
                     "variant_flipped": v_flip, "ring_flipped": r_flip,
                     "agree": agree})
    del Pill, ORIENT_H, ORIENT_V
    return ok, rows


# ------------------------------------------------------------------------ (d) physics
def gate_physics(n_boards=400, seed0=90001):
    """fall_from(top) must reproduce the faithful sim's resting_position()."""
    import numpy as np
    from drmario.faithful_game import FaithfulBoard, Pill, ORIENT_H, ORIENT_V

    checked = 0
    bad = []
    for i in range(n_boards):
        rng = np.random.default_rng(seed0 + i)
        b = FaithfulBoard(16, 8, rng=rng)
        b.place_viruses(int(rng.integers(1, 21)))
        # rough up the board with random settled halves so overhangs exist
        for _ in range(int(rng.integers(0, 40))):
            c = int(rng.integers(0, 8))
            top = b.top_occupied_row(c)
            if top - 1 >= 0:
                b.color[top - 1, c] = int(rng.integers(1, 4))
        for ring in range(4):
            is_h = G.RING_IS_H[ring]
            orient = ORIENT_H if is_h else ORIENT_V
            for col in range(8):
                ref = b.resting_position(Pill(1, 2), orient, col)
                # fall_from's anchor is the LEFT cell (H) or the BOTTOM cell (V);
                # start from the topmost anchor row the pill could occupy.
                got_r = G.fall_from(b.color, col, ring, 0 if is_h else 1)
                if ref is None:
                    if got_r is not None:
                        bad.append({"board": i, "ring": ring, "col": col,
                                    "ref": None, "got": got_r})
                    continue
                if got_r is None:
                    bad.append({"board": i, "ring": ring, "col": col,
                                "ref": [list(x) for x in ref], "got": None})
                    continue
                got = G.cells_of(ring, col, got_r)
                ref_cells = tuple(tuple(x) for x in ref)
                if tuple(got) != ref_cells:
                    bad.append({"board": i, "ring": ring, "col": col,
                                "ref": [list(x) for x in ref_cells],
                                "got": [list(x) for x in got]})
                checked += 1
    return len(bad) == 0, checked, bad[:20]


# -------------------------------------------------------------------- (a) determinism
def _play(cs, seed, level, max_pills, exec_mode):
    return G.play_game(cs, seed=seed, level=level, max_pills=max_pills,
                       trace=True, exec_mode=exec_mode)


def _key(r):
    """Everything that must be reproducible: the move sequence AND the outcome."""
    return (r["result"], r["pills"], r["viruses_cleared"], r["clocks"],
            tuple(r.get("moves", ())))


def gate_determinism(fw_dir, seeds, level, max_pills, exec_mode):
    """a1: fresh process twice. a2: first-in-process vs Nth-in-process."""
    fresh = {}
    for s in seeds:
        with Cosim(FARM_BIN, fw_dir) as cs:
            fresh[s] = _play(cs, s, level, max_pills, exec_mode)

    fresh2 = {}
    for s in seeds:
        with Cosim(FARM_BIN, fw_dir) as cs:
            fresh2[s] = _play(cs, s, level, max_pills, exec_mode)

    # a2: one long-lived process replays the same seeds, in order, after other games.
    reused = {}
    with Cosim(FARM_BIN, fw_dir) as cs:
        for s in seeds:
            _play(cs, s + 500, level, max_pills, exec_mode)   # intervening game
        for s in seeds:
            reused[s] = _play(cs, s, level, max_pills, exec_mode)

    a1_bad = [s for s in seeds if _key(fresh[s]) != _key(fresh2[s])]
    a2_bad = [s for s in seeds if _key(fresh[s]) != _key(reused[s])]
    return a1_bad, a2_bad, fresh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fw", default="/mnt/data/drmario_cosim/fw/s20b")
    ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2])
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--max-pills", type=int, default=8)
    ap.add_argument("--exec-mode", default="drop", choices=["drop", "tuck"])
    ap.add_argument("--fast", action="store_true",
                    help="pure checks only (e, d); skip the game-running determinism gate")
    ap.add_argument("--out")
    a = ap.parse_args()

    res = {"fw_dir": a.fw, "exec_mode": a.exec_mode}
    failures = []

    ok_o, rows_o = gate_orientation()
    res["gate_e_orientation"] = {"pass": ok_o, "rows": rows_o}
    print(f"(e) orientation        : {'PASS' if ok_o else 'FAIL'}  "
          f"(VAR_OF_O4 vs RING_OF_O4 agree on all 4 codes)")
    for r in rows_o:
        print(f"      o4={r['o4']} -> variant {r['variant']} / ring {r['ring']}  "
              f"horizontal={r['ring_horizontal']} flipped={r['ring_flipped']}  "
              f"{'ok' if r['agree'] else 'MISMATCH'}")
    if not ok_o:
        failures.append("orientation")

    t0 = time.time()
    ok_p, checked, bad_p = gate_physics()
    res["gate_d_physics"] = {"pass": ok_p, "checked": checked, "bad": bad_p}
    print(f"(d) fall_from physics  : {'PASS' if ok_p else 'FAIL'}  "
          f"{checked} (board,col,orient) cases vs resting_position()  "
          f"[{time.time()-t0:.1f}s]")
    if not ok_p:
        failures.append("physics")
        for x in bad_p[:5]:
            print("      ", x)

    if not a.fast:
        t0 = time.time()
        a1, a2, games = gate_determinism(a.fw, a.seeds, a.level, a.max_pills, a.exec_mode)
        res["gate_a_determinism"] = {
            "pass": not a1 and not a2, "seeds": a.seeds,
            "max_pills": a.max_pills,
            "a1_fresh_vs_fresh_mismatched_seeds": a1,
            "a2_fresh_vs_reused_mismatched_seeds": a2,
            "games": {str(s): games[s] for s in games},
        }
        print(f"(a1) fresh vs fresh    : {'PASS' if not a1 else 'FAIL ' + str(a1)}")
        print(f"(a2) fresh vs REUSED   : {'PASS' if not a2 else 'FAIL ' + str(a2)}  "
              f"(state leak between games in one co-sim process)  "
              f"[{time.time()-t0:.1f}s]")
        if a1:
            failures.append("determinism_fresh")
        if a2:
            failures.append("determinism_reuse")

    res["failures"] = failures
    res["pass"] = not failures
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump(res, open(a.out, "w"), indent=1)
        print(f"wrote {a.out}")
    print("\nVALIDATION GATE: " + ("PASS" if not failures else "FAIL " + ",".join(failures)))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
