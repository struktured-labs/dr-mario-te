#!/usr/bin/env python3
"""SCREEN: is d3-delta RELIABLE enough to be worth using for labels?

Pre-registered threshold (team-lead, before this ran). For a ridge fit,
    signal ~ sqrt(R) / SE_single      R = TOTAL rollouts, however split
so averaging k rollouts per position buys nothing that k x more positions would;
the only levers are total rollout budget and single-rollout SE. d3-delta is 3.3x
cheaper than the champion, buying sqrt(3.3) = 1.82x more rollouts per hour, so it
wins iff  SE_d3delta < 1.82 * 3.31 = 6.01.

Calibrating var ~ f(1-f)*C^2 + s0^2 on the two MEASURED points (99.5% clear -> SE
3.31; 64.2% -> 15.44) gives C = 31.8 pills, floor 2.43. That converts the SE
threshold into a CLEAR-RATE threshold:

    d3-delta must clear >= 96.9% to be worth using.

DECISION RULE, fixed before the measurement:
  >= 96.9%      measure SE properly, then cost champion labels against it
  90 - 96.9%    d3-delta is WORSE per unit compute than the champion -> champion
  < 90%         same conclusion, harder

CONTROLLED COMPARISON. Stage 1's 99.5% was champion continuations from champion
corpus positions, each starting with a FORCED first action drawn from that
position's labelled set -- including deliberately poor ones. This screen reuses
those exact positions and those exact forced actions and changes ONLY the
continuation policy. Anything else would confound policy with position difficulty,
which is the mistake that made the depth-2 corpus look worse than it was.
"""
import os, sys, json, random, time, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

CAP = 200
_W = {}

def _init():
    import sp_engine as E, fast_rtl_x as FX
    FX.warmup_delta(topk2=8)
    _W["w"], _W["fl"] = FX.variant("winner")
    _W["env"] = E.new_env(level=E.LEVEL, seed=0, cap=CAP)

def _job(t):
    import sp_engine as E, fast_rtl_x as FX
    col, vir, link, ca, cb, na, nb, act, stream = t
    env = _W["env"]; w, fl = _W["w"], _W["fl"]
    E.attach_stream(env, stream)
    E.set_board(env.board, col, vir, link)
    E.set_pills(env, ca, cb, na, nb)
    env.pills_placed = 0
    env._start_viruses = int(env.board.virus_count())
    used = 0; first = act
    for _ in range(CAP):
        if env.board.virus_count() == 0: return "clear", used
        if first is not None:
            a = first; first = None
        else:
            c, v, _l = E.board_planes(env.board)
            a = int(FX._choose_d3_ship_eh_delta(c, v, env.cur.a, env.cur.b,
                    env.nxt.a, env.nxt.b, 8, int(FX._W_EXCAV_SHIP),
                    int(FX._W_HANG_SHIP), w, fl))
            if a < 0: return "topout", used
        _o,_r,term,trunc,info = env.step(int(a)); used += 1
        if term: return ("clear" if info["won"] else "topout"), used
        if trunc: return "stall", used
    return "stall", used

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    d = np.load("out/corpus.npz")
    C, V, L, P = d["col"], d["vir"], d["link"], d["pills"]
    recs = [json.loads(l) for l in open("out/labels_main.jsonl") if l.strip()]
    rng = random.Random(4242)
    jobs = []
    while len(jobs) < n:
        r = rng.choice(recs); i = r["idx"]; a = rng.choice(r["acts"])
        jobs.append((C[i].astype(np.int8), V[i].astype(np.int8), L[i].astype(np.int8),
                     int(P[i][0]), int(P[i][1]), int(P[i][2]), int(P[i][3]),
                     int(a), 5000000 + len(jobs)))
    t0 = time.time(); out = []
    with ProcessPoolExecutor(max_workers=4, initializer=_init) as ex:
        for f in as_completed([ex.submit(_job, j) for j in jobs]):
            out.append(f.result())
    el = time.time() - t0
    oc = collections.Counter(o for o, _ in out)
    N = len(out); f_clear = oc["clear"] / N
    se_rate = (f_clear * (1 - f_clear) / N) ** 0.5
    C_CAL, S0 = 31.8, 2.43
    pred_se = (f_clear * (1 - f_clear) * C_CAL**2 + S0**2) ** 0.5
    print(f"d3-delta continuations, Stage-1 positions + forced actions")
    print(f"  rollouts {N} in {el:.0f}s ({el/N:.2f}s each, 4 workers)")
    print(f"  outcomes {dict(oc)}")
    print(f"  CLEAR RATE {f_clear:.1%}  (+-{se_rate*100:.1f} pts)")
    print(f"  predicted per-label SE from the calibrated model: {pred_se:.2f}")
    print(f"  threshold: clear >= 96.9%  <=>  SE < 6.01")
    print()
    if f_clear >= 0.969:
        print("  => PASS. d3-delta beats the champion per unit compute. Next: measure")
        print("     SE properly on a labelling slice, then cost champion labels against it.")
    elif f_clear >= 0.90:
        print("  => FAIL (90-96.9% band). d3-delta is WORSE per unit compute than the")
        print("     champion despite costing 3.3x less per rollout. Go to champion labels.")
    else:
        print("  => FAIL (<90%). Same conclusion, more decisively. Champion labels.")
    print(f"\n  reference: champion 99.5% -> SE 3.31 (Stage 1); depth-2 64.2% -> SE 15.44")

if __name__ == "__main__":
    main()
