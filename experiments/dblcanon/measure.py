"""#123 measurement + board-identity gate: play the champion, watch the doubles.

Runs the champion's own game loop (lifted from `screen_gw.play_one_screened`,
minus the observer) and, at EVERY ply, records:

  * whether the capsule is a double,
  * the champion's chosen 32-slot action and its o4,
  * on doubles, the FULL board grouping over all legal slots -- which is how
    the duplicate pairing is derived (never from `_VAR_OF_O4` arithmetic), and
  * whether the champion's pick is already the cheap member of its pair.

That last number is the whole question.  The lane's premise is that the two
members of a duplicate pair cost different numbers of rotations and the search
does not know it; if the argmax's tie-break already lands on the cheap member,
the tempo win is banked already and the change is a no-op worth shipping only
as a guard.  This rig measures it instead of assuming either way.

Usage:  python measure.py --seeds 0 --count 40 --out out/measure.jsonl
"""

import argparse
import copy
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


def _boot():
    for p in (GW, ORACLE_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)


def play_one(seed, C, bmodel, rows, exhaustive=True):
    """The champion's game loop with a double-capsule observer at every ply."""
    import fast_rtl_x as FX
    import pressure_rig as PR  # noqa: F401  (import order matters here)
    from oracle_arm import make_env, _champ_action, CHAMP_ORDER
    from screen_gw import champ_values_of, advance_split

    var_of_o4 = FX._VAR_OF_O4
    level, wt, ws, w, fl = C["level"], C["wt"], C["ws"], C["w"], C["fl"]
    env = make_env(seed, level)
    res = "stall"
    n_ply = n_dbl = 0

    for ply in range(300):
        if env.board.virus_count() == 0:
            res = "clear"
            break

        vals = champ_values_of(env.board, env.cur.a, env.cur.b,
                               env.nxt.a, env.nxt.b, w, fl, wt, ws)
        a = _champ_action(vals, CHAMP_ORDER)
        if a is None:
            break
        n_ply += 1
        dbl = DC.is_double(env.cur)

        if dbl:
            n_dbl += 1
            legal = [int(s) for s in range(32) if np.isfinite(vals[int(s)])]
            o4, col = DC.slot_to_o4_col(a, var_of_o4)
            row = dict(seed=int(seed), ply=int(ply), action=int(a),
                       o4=int(o4), col=int(col),
                       rot_cost=int(DC.ROT_COST_O4[o4]),
                       canonical=int(DC.is_canonical_o4(o4)),
                       rot_saved=int(DC.rotations_saved(o4)),
                       n_legal=len(legal))
            if exhaustive:
                groups = DC.pairing_from_boards(env, legal, var_of_o4)
                bad = DC.assert_pairing(groups, var_of_o4,
                                        ctx=f"seed{seed}/ply{ply}")
                sizes = sorted(len(v) for v in groups.values())
                row.update(n_groups=len(groups),
                           group_sizes=sizes,
                           pairing_violations=bad,
                           # the ship claim: the canonical partner of the
                           # chosen slot must produce the SAME board.
                           partner_same_board=_partner_check(
                               env, a, vals, var_of_o4))
            rows.append(row)

        r, _v, _pre = advance_split(env, a, C, seed, bmodel)
        if r is not None:
            res = r
            break

    return dict(seed=int(seed), res=res, n_ply=n_ply, n_dbl=n_dbl)


def _partner_check(env, a, vals, var_of_o4):
    """Does the chosen slot's canonical partner exist, tie, and match cell-for-cell?

    Returns a dict, never a bare bool -- an absent partner and a mismatching
    partner are different facts and collapsing them is how an inert check
    passes.
    """
    o4, col = DC.slot_to_o4_col(a, var_of_o4)
    p_o4 = DC.PAIR_PARTNER_O4[o4]
    p = DC.o4_col_to_slot(p_o4, col, var_of_o4)
    if not np.isfinite(vals[int(p)]):
        return dict(partner=int(p), legal=0, same_value=None, same_board=None)
    e1, e2 = copy.deepcopy(env), copy.deepcopy(env)
    e1.step(int(a))
    e2.step(int(p))
    return dict(partner=int(p), legal=1,
                same_value=int(float(vals[int(a)]) == float(vals[int(p)])),
                same_board=int(DC.board_key(e1.board) == DC.board_key(e2.board)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=0)
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--model", default="lulu")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "measure.jsonl"))
    ap.add_argument("--fast", action="store_true",
                    help="skip the exhaustive 32-slot board grouping")
    args = ap.parse_args()

    _boot()
    import oracle_arm as O
    C, bmodel = O.init_rig(args.model)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    rows, games = [], []
    for s in range(args.seeds, args.seeds + args.count):
        games.append(play_one(s, C, bmodel, rows, exhaustive=not args.fast))
        print(f"  seed {s}: {games[-1]}", flush=True)

    with open(args.out, "w") as fh:
        for g in games:
            fh.write(json.dumps({"kind": "game", **g}) + "\n")
        for r in rows:
            fh.write(json.dumps({"kind": "dbl", **r}) + "\n")

    n_dbl = len(rows)
    n_ply = sum(g["n_ply"] for g in games)
    noncanon = [r for r in rows if not r["canonical"]]
    viol = [r for r in rows if r.get("pairing_violations")]
    print(f"\nplies {n_ply}  doubles {n_dbl} ({100.0*n_dbl/max(1,n_ply):.1f}%)")
    print(f"non-canonical picks {len(noncanon)} "
          f"({100.0*len(noncanon)/max(1,n_dbl):.2f}% of doubles)")
    print(f"rotations saved total {sum(r['rot_saved'] for r in rows)}")
    print(f"pairing violations {len(viol)}")
    if not args.fast:
        mism = [r for r in rows
                if r["partner_same_board"].get("same_board") == 0]
        print(f"partner-board mismatches {len(mism)}")


if __name__ == "__main__":
    main()
