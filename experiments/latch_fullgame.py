#!/usr/bin/env python3
"""Full-game cost of the pair latch, calibrated to the MEASURED RTL disagreement rates.

My first attempt (`latch_ab.py`) modelled the cart's early orient as the depth-1 argmax.
That produced ~30% disagreement (the spec's P=1 row) and collapsed both partial arms to
~0% clear -- far too pessimistic, and I said so at the time.

The RTL has since been measured directly (`sim_orient_trace.cpp`, 69 real L11 positions):

    opening vc>32 : 12.5%      mid vc 9-32 : 16.7%      endgame vc<=8 : 39.1%
    overall 23.2%

So this arm corrupts the orientation at exactly those REGIME-SPECIFIC rates: with
probability p(virus_count) the placement keeps the depth-3 COLUMN but takes the depth-1
ORIENT -- which is precisely the cross-product the cart executes. Everything else is the
shipped brain.

This is still a model (it assumes the 5-frame argmax behaves like depth-1 WHEN it differs),
but the RATE is now measured rather than assumed, which was the dominant error before.
Paired seeds; arm A is the untouched brain.
"""
from __future__ import annotations
import sys, os, json, argparse, random, statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = "/home/struktured/projects/dr_mario_rl"
for p in (ROOT + "/tmp/endgame", ROOT + "/tmp/combo_term",
          ROOT + "/.claude/worktrees/faithful-sim/src"):
    if p not in sys.path:
        sys.path.insert(0, p)

from fb import FB, COLS
import destroy as D

# measured on the real RTL, 69 real L11 positions
P_OPEN, P_MID, P_END = 0.125, 0.167, 0.391
_C = {}


def _init(corrupt, level):
    D._init("winner", level, 300, 4, 600, 28, 8, 6)
    _C.update(corrupt=corrupt, level=level)


def p_for(vc):
    if vc > 32:
        return P_OPEN
    if vc > 8:
        return P_MID
    return P_END


def d1_variant(fb, pa, pb):
    best, bv = None, None
    for var in range(4):
        for c in range(COLS):
            nb, imm = D.child(fb, var, c, pa, pb)
            if nb is None:
                continue
            s = D.proxy_score(nb, imm)
            if best is None or s > best:
                best, bv = s, var
    return bv


def play(args):
    seed, corrupt = args
    from drmario.faithful_env import FaithfulDrMarioEnv
    dec = D._G["dec"]
    rng = random.Random(seed * 7919 + 13)
    env = FaithfulDrMarioEnv(level=_C["level"], seed=seed, max_pills=300)
    env.reset()
    n_corrupt = 0
    # conversion trajectory: pills spent while in each regime, and viruses cleared there.
    # "builds an edge then burns it" = a cheap opening/mid and an expensive endgame.
    seg = {"open": [0, 0], "mid": [0, 0], "end": [0, 0]}   # [pills, viruses_cleared]
    res = "stall"
    while True:
        a = dec.choose(env.board, env.cur, env.nxt)
        if a is None:
            res = "topout"; break
        if corrupt:
            vc = env.board.virus_count()
            if rng.random() < p_for(vc):
                fb = FB.from_board(env.board)
                v1 = d1_variant(fb, env.cur.a, env.cur.b)
                if v1 is not None and v1 != int(a) // COLS:
                    cand = v1 * COLS + (int(a) % COLS)
                    if D.child(fb, v1, int(a) % COLS, env.cur.a, env.cur.b)[0] is not None:
                        a = cand; n_corrupt += 1
        vc_before = env.board.virus_count()
        key = "open" if vc_before > 32 else ("mid" if vc_before > 8 else "end")
        _, _, term, trunc, info = env.step(int(a))
        seg[key][0] += 1
        seg[key][1] += vc_before - env.board.virus_count()
        if term:
            res = "clear" if info["won"] else "topout"; break
        if trunc:
            res = "stall"; break
    return {"seed": seed, "corrupt": corrupt, "res": res,
            "won": int(res == "clear"), "pills": env.pills_placed,
            "n_corrupt": n_corrupt, "seg": seg}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--out", default="latch_fullgame")
    a = ap.parse_args()
    seeds = list(range(a.seeds))
    res = {}
    for corrupt in (0, 1):
        rows = []
        with ProcessPoolExecutor(max_workers=a.workers, initializer=_init,
                                 initargs=(corrupt, a.level)) as ex:
            for f in as_completed([ex.submit(play, (s, corrupt)) for s in seeds]):
                rows.append(f.result())
        res[corrupt] = sorted(rows, key=lambda r: r["seed"])
        print(f"corrupt={corrupt}: clear {sum(r['won'] for r in rows)/len(rows):6.1%}  "
              f"med pills {st.median([r['pills'] for r in rows]):6.1f}  "
              f"topout {sum(1 for r in rows if r['res']=='topout')/len(rows):5.1%}  "
              f"stale-orient moves/game {st.mean([r['n_corrupt'] for r in rows]):.1f}")

    A, B = res[0], res[1]
    d = [b["pills"] - x["pills"] for x, b in zip(A, B)]
    lost = sum(1 for x, b in zip(A, B) if x["won"] and not b["won"])
    print(f"\n=== PAIR-LATCH FULL-GAME COST (L{a.level}, n={a.seeds}, measured rates) ===")
    print(f"  clear rate   {sum(r['won'] for r in A)/len(A):.1%} -> {sum(r['won'] for r in B)/len(B):.1%}")
    print(f"  paired pills (latched - clean): median {st.median(d):+.1f}  mean {st.mean(d):+.1f}")
    print(f"  games where the latch COST a clear: {lost}/{len(A)}")
    print("\n=== CONVERSION COST: pills spent per virus cleared, by regime ===")
    print(f"  {'regime':>8} {'clean':>10} {'latched':>10} {'penalty':>10}")
    for k, lbl in (("open", "open >32"), ("mid", "mid 9-32"), ("end", "END <=8")):
        def ppv(rows):
            pil = sum(r["seg"][k][0] for r in rows); vir = sum(r["seg"][k][1] for r in rows)
            return pil / vir if vir else float("nan")
        a_, b_ = ppv(A), ppv(B)
        print(f"  {lbl:>8} {a_:10.2f} {b_:10.2f} {(b_-a_)/a_*100:9.0f}%")
    print("  (a disproportionate END penalty IS the 'built a big edge then gave it back' shape)")
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     a.out + ".json"), "w"), indent=1)


if __name__ == "__main__":
    main()
