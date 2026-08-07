#!/usr/bin/env python3
"""Measure d3-delta's per-label SE directly, instead of predicting it.

The screen passed on CLEAR RATE (99.0% vs a 98.21% threshold) but by only ~1.1
sigma, and the threshold itself depends on a calibrated var-vs-clear-rate model
fitted to two points. The decision on where to spend ~10-35 h should rest on a
measured SE, not a modelled one.

Controlled: Stage 1's own positions and action sets, with the SAME split-sample /
CRN-corrected variance decomposition used everywhere else. Only the rollout
continuation policy differs (champion -> d3-delta), so the SE comparison against
Stage 1's 3.31 is like-for-like.
"""
import os, sys, json, time, random, math, statistics as st
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

def _pos_job(t):
    import sp_engine as E, fast_rtl_x as FX
    idx, col, vir, link, ca, cb, na, nb, acts, M, base = t
    env = _W["env"]; w, fl = _W["w"], _W["fl"]
    out = {}
    for a in acts:
        pl, oc = [], []
        for m in range(M):
            E.attach_stream(env, base + m)
            E.set_board(env.board, col, vir, link)
            E.set_pills(env, ca, cb, na, nb)
            env.pills_placed = 0; env._start_viruses = int(env.board.virus_count())
            used = 0; first = a; res = "stall"
            for _ in range(CAP):
                if env.board.virus_count() == 0: res = "clear"; break
                if first is not None: act = first; first = None
                else:
                    c, v, _l = E.board_planes(env.board)
                    act = int(FX._choose_d3_ship_eh_delta(c, v, env.cur.a, env.cur.b,
                            env.nxt.a, env.nxt.b, 8, int(FX._W_EXCAV_SHIP),
                            int(FX._W_HANG_SHIP), w, fl))
                    if act < 0: res = "topout"; break
                _o,_r,term,trunc,info = env.step(int(act)); used += 1
                if term: res = "clear" if info["won"] else "topout"; break
                if trunc: res = "stall"; break
            pl.append(used); oc.append(res)
        out[str(a)] = {"pills": pl, "outcome": oc}
    return {"idx": idx, "acts": acts, "vals": out}

def main():
    npos = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    M = 8
    d = np.load("out/corpus.npz"); C,V,L,P = d["col"],d["vir"],d["link"],d["pills"]
    recs = [json.loads(l) for l in open("out/labels_main.jsonl") if l.strip()]
    rng = random.Random(31337); rng.shuffle(recs)
    jobs = []
    for k, r in enumerate(recs[:npos]):
        i = r["idx"]
        jobs.append((i, C[i].astype(np.int8), V[i].astype(np.int8), L[i].astype(np.int8),
                     int(P[i][0]), int(P[i][1]), int(P[i][2]), int(P[i][3]),
                     r["acts"], M, 7000000 + k*977))
    t0 = time.time(); res = []
    with ProcessPoolExecutor(max_workers=4, initializer=_init) as ex:
        for f in as_completed([ex.submit(_pos_job, j) for j in jobs]):
            res.append(f.result())
    el = time.time() - t0
    nroll = sum(len(r["acts"]) * M for r in res)
    CEN = 200.0
    nclear = sum(1 for r in res for a in r["acts"]
                 for o in r["vals"][str(a)]["outcome"] if o == "clear")
    ses, taus = [], []
    for r in res:
        Vm = np.array([[(-float(p) if o=="clear" else -CEN) for p,o in
                        zip(r["vals"][str(a)]["pills"], r["vals"][str(a)]["outcome"])]
                       for a in r["acts"]], dtype=float)
        if Vm.shape[0] < 2: continue
        dd = Vm - Vm.mean(axis=0, keepdims=True)
        within = dd.var(axis=1, ddof=1).mean(); between = dd.mean(axis=1).var()
        ses.append(math.sqrt(within / M))
        taus.append(math.sqrt(max(0.0, between - within / M)))
    se, tau = st.mean(ses), st.mean(taus)
    print(f"d3-delta labelling slice: {len(res)} positions, {nroll} rollouts, {el:.0f}s")
    print(f"  clear rate                {nclear/nroll:.2%}")
    print(f"  per-label SE (CRN)        {se:.2f}    (champion Stage 1: 3.31)")
    print(f"  true action spread tau    {tau:.2f}    (champion Stage 1: 6.37)")
    print(f"  per-label SNR             {tau/se:.2f}    (champion Stage 1: 1.93)")
    RATIO = 2.16
    adv = math.sqrt(RATIO) * (3.31 / se)
    print(f"\n  signal per unit compute vs champion = sqrt({RATIO}) x (3.31/{se:.2f}) = {adv:.2f}x")
    print(f"  => {'USE d3-delta' if adv > 1.0 else 'USE THE CHAMPION'}")
    for target in (2.0, 3.0):
        R = 11200 * (target * se / 3.31) ** 2
        print(f"  {target:.0f}x Stage-1 signal: {R:,.0f} rollouts "
              f"= {R*1.299/4/3600:.1f} h at 4 workers")

if __name__ == "__main__":
    main()
