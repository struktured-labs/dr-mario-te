"""What the FIRMWARE's tie-break jitter does to a double capsule's duplicate pair.

The offline champion has no jitter, so it resolves a duplicate pair by scan
order and always lands on the cheap member.  The CART does not: with
`DRSEED != 0` (the default, and `DRSEED: '1'` in every shipped flag snapshot)
the firmware adds a per-candidate `+0..3` to val1 before the argmax --

    t = seed ^ ((o4 << 3) | col)  ;  j = (t ^ (t >> 3)) & 3

(`tests/nes_d3_golden.py::_jitter`, bit-exact against the 6502 at
`test_search_d3.py:577-582`).  The two members of a duplicate pair share `col`
and differ only in bit 0 of `o4`, which is bit 3 of `t`, so their jitters differ
by exactly XOR 1: one draws an even value, the other that value plus one, and
THE HIGHER ONE WINS.  Whether that is the cheap or the expensive member is
fixed by `bit3(seed) ^ bit0(col)`.

Two consequences this rig measures rather than asserts:

  1. TEMPO -- on a jittered cart the expensive (2-extra-rotation) member wins a
     large, seed-determined share of double plies.  That is the real, unbanked
     benefit of #123, and it does not exist in the offline model at all.
  2. ⚠ THE ZERO-BOARD-EFFECT PROOF DOES NOT SURVIVE THE JITTER.  A duplicated
     placement effectively draws the MAX of two jitter values while a unique
     placement draws one, so it carries a systematic advantage in the near-tie
     lottery.  Removing the duplicate removes that advantage, which can hand
     the ply to a genuinely DIFFERENT placement.  This rig counts how often.
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
GW = os.path.abspath(os.path.join(HERE, "..", "gw_design"))
ORACLE_DIR = os.environ.get(
    "GW_ORACLE_DIR",
    "/home/struktured/projects/dr-mario-te/h13-gate/experiments/eval47/stage2/oracle")

import dblcanon as DC  # noqa: E402


def jitter(seed, o4, col):
    """`nes_d3_golden._jitter`, re-implemented from the SPEC, not copied.

    Written from the 6502 at `test_search_d3.py:577-582` (`LDA D_O1; ASL x3;
    ORA D_C1; EOR D_SEED -> D_JT; LSR x3; EOR D_JT; AND #3`) so that agreeing
    with the golden is evidence rather than tautology.  `cross_check` asserts
    the agreement over the whole 256x4x8 domain.
    """
    if seed == 0:
        return 0
    t = (int(seed) ^ ((int(o4) << 3) | int(col))) & 0xFF
    return (t ^ (t >> 3)) & 3


def cross_check():
    """Independent second implementation vs the golden, exhaustively."""
    sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "tests")))
    import nes_d3_golden as G
    bad = [(s, o, c) for s in range(256) for o in range(4) for c in range(8)
           if jitter(s, o, c) != G._jitter(s, o, c)]
    return bad


def argmax_slot(vals, order, seed, var_of_o4):
    """The firmware's argmax: scan `order`, strictly-greater keeps first.

    `order` is (o4 ascending, col ascending) -- the p0 loop's own order, which
    is also the order the top-K extraction preserves on equal keys.
    """
    best_v, best_s = None, None
    for s in order:
        v = vals[int(s)]
        if not np.isfinite(v):
            continue
        o4, col = DC.slot_to_o4_col(s, var_of_o4)
        vj = float(v) + jitter(seed, o4, col)
        if best_v is None or vj > best_v:
            best_v, best_s = vj, int(s)
    return best_s


def canon_order(order, var_of_o4):
    """`order` with the expensive member of every duplicate pair removed."""
    return [s for s in order
            if DC.is_canonical_o4(DC.slot_to_o4_col(s, var_of_o4)[0])]


def play_one(seed, C, bmodel, seeds_j, rows):
    import fast_rtl_x as FX
    import pressure_rig as PR  # noqa: F401
    from oracle_arm import make_env, _champ_action, CHAMP_ORDER
    from screen_gw import champ_values_of, advance_split
    import copy

    var_of_o4 = FX._VAR_OF_O4
    order = [int(s) for s in CHAMP_ORDER]
    corder = canon_order(order, var_of_o4)
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]
    env = make_env(seed, level)

    for ply in range(300):
        if env.board.virus_count() == 0:
            break
        vals = champ_values_of(env.board, env.cur.a, env.cur.b,
                               env.nxt.a, env.nxt.b, w, fl, wt, ws)
        a = _champ_action(vals, CHAMP_ORDER)
        if a is None:
            break
        if DC.is_double(env.cur):
            for sj in seeds_j:
                a_off = argmax_slot(vals, order, sj, var_of_o4)     # cart today
                a_on = argmax_slot(vals, corder, sj, var_of_o4)     # + #123
                o_off, _c = DC.slot_to_o4_col(a_off, var_of_o4)
                o_on, _c2 = DC.slot_to_o4_col(a_on, var_of_o4)
                same_board = None
                if a_off != a_on:
                    e1, e2 = copy.deepcopy(env), copy.deepcopy(env)
                    e1.step(int(a_off))
                    e2.step(int(a_on))
                    same_board = int(DC.board_key(e1.board)
                                     == DC.board_key(e2.board))
                rows.append(dict(
                    seed=int(seed), ply=int(ply), jseed=int(sj),
                    a_off=int(a_off), a_on=int(a_on),
                    o4_off=int(o_off), o4_on=int(o_on),
                    rot_off=int(DC.ROT_COST_O4[o_off]),
                    rot_on=int(DC.ROT_COST_O4[o_on]),
                    action_changed=int(a_off != a_on),
                    same_board=same_board))
        r, _v, _p = advance_split(env, a, C, seed, bmodel)
        if r is not None:
            break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--jseeds", default="0,165,167,169,171,45,201,99")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "jitter.jsonl"))
    args = ap.parse_args()

    for p in (GW, ORACLE_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)

    bad = cross_check()
    print(f"jitter cross-check vs nes_d3_golden over 256x4x8: "
          f"{'OK' if not bad else f'{len(bad)} MISMATCHES'}")
    if bad:
        sys.exit(2)

    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    seeds_j = [int(x) for x in args.jseeds.split(",")]

    rows = []
    for s in range(args.seeds, args.seeds + args.count):
        play_one(s, C, bmodel, seeds_j, rows)
        print(f"  seed {s}: {len(rows)} rows", flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    print(f"\n{'jseed':>6} {'n':>6} {'expensive%':>11} {'rot saved/ply':>14} "
          f"{'action moved%':>14} {'DIFFERENT board':>16}")
    for sj in seeds_j:
        rs = [r for r in rows if r["jseed"] == sj]
        if not rs:
            continue
        exp = sum(1 for r in rs if r["rot_off"] > r["rot_on"])
        saved = sum(r["rot_off"] - r["rot_on"] for r in rs)
        moved = sum(r["action_changed"] for r in rs)
        diff = sum(1 for r in rs if r["same_board"] == 0)
        print(f"{sj:>6} {len(rs):>6} {100.0*exp/len(rs):>10.2f}% "
              f"{saved/len(rs):>14.3f} {100.0*moved/len(rs):>13.2f}% "
              f"{diff:>16}")


if __name__ == "__main__":
    main()
