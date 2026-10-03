#!/usr/bin/env python3
"""Bank GENERAL SIM BOARDS for the brain-gap impact estimate: the s6_dist_target60 (ANTIBODY_DIST) python brain playing
gate-(b) games vs the owner0804 opponent model -- exactly steer7_anytime.collect (the STEER7 desk corpus generator,
seeds lo, lo+2, ...). Every decision board is written with its pills, pill index k, virus count and max height so the
brain-gap comparison (impact_braingap_20261003.py) can run on it without replaying games.

Usage: simboards_braingap_20261003.py N_SEEDS LO OUT.jsonl [fw]
  fw: the boards come from the SILICON-FAITHFUL brain playing (Leaf6FwDecider, every firmware switch on) instead of
      the python sim brain -- the board distribution silicon's own play produces (same steering, opponent, seeds).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rtlengine_braingap_20261003 as E  # noqa: E402,F401  (pins paths + fresh numba cache)
sys.path.insert(0, E.CVX)


def enc(a):
    import numpy as np
    return "".join(str(int(v)) for v in np.asarray(a).ravel())


def collect_fw(n_seeds, lo):
    """steer7_anytime.collect with the s6_dist_target60 steering/opponent but the Leaf6FwDecider brain."""
    from types import SimpleNamespace
    import stuck_probe as SP, steer_run as SR, opp_run as OR
    import fast_rtl_x as FX
    import cascade_chain_x as C
    import cascade_leaf6fw_braingap_20261003 as F
    C.warmup_chain(topk2=8)
    w, fl = FX.variant("winner")
    out = []
    for i in range(n_seeds):
        steer, _choose = SR.make("s6_dist_target60"); opp = OR.make_opponent("owner0804")
        dec = F.Leaf6FwDecider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, mode="dist_target", W=60, vk=4)

        def ch(env, col, vir, ctx, dec=dec):
            out.append((dec, env.board.clone(), SimpleNamespace(a=int(env.cur.a), b=int(env.cur.b)),
                        SimpleNamespace(a=int(env.nxt.a), b=int(env.nxt.b)), int(env.pills_placed)))
            return dec.choose(env.board, env.cur, env.nxt, k=env.pills_placed)
        SP.play_gb(lo + 2 * i, ch, steer, opp)
    return out


def main():
    n, lo, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    if len(sys.argv) > 4 and sys.argv[4] == "fw":
        boards = collect_fw(n, lo)
    else:
        import steer7_anytime as S7
        boards = S7.collect(n, lo)
    with open(out, "w") as fh:
        for i, (dec, b, cur, nxt, k) in enumerate(boards):
            col = b.color
            h = [next((16 - r for r in range(16) if col[r, c] != 0), 0) for c in range(8)]
            fh.write(json.dumps(dict(i=i, k=k, cur=[cur.a, cur.b], nxt=[nxt.a, nxt.b],
                                     S=dict(color=enc(b.color), virus=enc(b.is_virus.astype(int)), link=enc(b.link)),
                                     nv=int(b.is_virus.sum()), maxh=max(h), heights=h)) + "\n")
    print(f"{len(boards)} boards -> {out}")


if __name__ == "__main__":
    main()
