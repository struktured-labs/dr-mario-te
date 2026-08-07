#!/usr/bin/env python3
"""STAGE B under PRESSURE: the seal/no-open-window term vs the champion under
bursty-v1.1 garbage, where the failures actually live (BURSTY_V1_RESULTS.md §5:
control 39.2% bad-ends, shipped ws=20 16.7%, dies-ahead 7.5%).

NO COPY of the pressure loop.  eval47/pressure_rig.py's play() resolves
`_choose_base` from its own module globals at CALL time, so this module swaps
in a seal-aware chooser per worker process and otherwise runs pressure_rig's
exact garbage model, injection timing, bad-end / dies-ahead accounting and
metrics.  The v1.1 model object is rebuilt in-process by
run_bursty_v1_1_validity.build_v1_1(), the file that is the single source of
truth for what v1.1 is.

Arms use seal_ab's spelling: base | pen_seal:W | pen_noopen:W | veto_seal |
veto_noopen, gated on pre-placement virus_count <= --gate.  "base" leaves
pressure_rig's own _choose_base in place, so the control arm is the shipped
decider byte-for-byte, not a re-implementation.
"""
from __future__ import annotations

import sys
import os
import json
import random
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pressure_rig as PR
from seal_ab import parse_arm

_A = {}          # arm config, per worker process
_FIRE = {"gated": 0, "changed": 0}   # per-GAME counters, reset by _play_seed


def _choose_base_seal(col, vir, ca, cb, na, nb, w, fl, wt, ws):
    """pressure_rig._choose_base + the seal cost.  Same signature and same
    (action, child_board) return, so pressure_rig.play() is unaware."""
    import numpy as np
    import fast_rtl_x as FX
    import root_search as RS
    from fast_sim_x import NCELL, _expand_core
    from terms47 import g_tower, g_stranded
    from seal_terms import n_sealed, n_noopen

    kind, weight, gate = _A["kind"], _A["weight"], _A["gate"]
    vc = int(sum(1 for x in vir if x))
    gated = vc <= gate
    metric = n_sealed if kind == "seal" else n_noopen
    base_pen = int(metric(col, vir)) if gated else 0

    c1 = np.empty(NCELL, dtype=np.int8)
    v1 = np.empty(NCELL, dtype=np.int8)
    best_raw, best_adj = None, None      # (val, action, board) each
    for o4 in range(4):
        var = int(FX._VAR_OF_O4[o4])
        for cc in range(8):
            ok, nv, cells = _expand_core(col, vir, var, cc, ca, cb, c1, v1)
            if ok == 0:
                continue
            val = RS._root_value(c1, v1, nv, cells, na, nb, 8,
                                 FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w, fl)
            if wt:
                val -= wt * g_tower(c1, v1, H0_)
            if ws:
                val -= ws * g_stranded(c1, v1)
            newp = max(0, int(metric(c1, v1)) - base_pen) if gated else 0
            adj = val - (1e12 if (weight is None and newp > 0)
                         else (weight or 0.0) * newp)
            a = var * 8 + cc
            if best_raw is None or val > best_raw[0]:
                best_raw = (val, a, c1.copy())
            if best_adj is None or adj > best_adj[0]:
                best_adj = (adj, a, c1.copy())

    if best_raw is None:
        return None, None
    if not gated:
        return best_raw[1], best_raw[2]
    _FIRE["gated"] += 1
    if best_adj[1] != best_raw[1]:
        _FIRE["changed"] += 1
    return best_adj[1], best_adj[2]


H0_ = PR.H0


def _init(level, wt, ws, model_obj, arm, gate):
    PR._init(level, wt, ws, "bursty", model_obj)
    import seal_terms as ST
    ST.warmup()
    kind, weight = parse_arm(arm)
    _A.update(arm=arm, kind=kind, weight=weight, gate=gate)
    if kind != "base":
        PR._choose_base = _choose_base_seal      # control keeps the shipped path


def _play_seed(seed):
    _FIRE["gated"] = 0
    _FIRE["changed"] = 0
    r = PR.play(seed)
    r["arm"] = _A["arm"]
    r["gated_decisions"] = _FIRE["gated"]
    r["changed_decisions"] = _FIRE["changed"]
    return r


def run_arm(arm, seeds, level, wt, ws, gate, workers, model_obj):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, wt, ws, model_obj, arm, gate)) as ex:
        futs = {ex.submit(_play_seed, s): s for s in seeds}
        for f in as_completed(futs):
            try:
                rows.append(f.result())
            except Exception as e:
                import traceback
                rows.append({"seed": futs[f], "arm": arm, "error": str(e),
                             "tb": traceback.format_exc()[-800:]})
    return rows


def boot_ci(xs, stat=st.mean, n=10000, seed=12345):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    reps = sorted(stat([xs[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return reps[int(0.025 * n)], reps[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--wt", type=int, default=0)
    ap.add_argument("--ws", type=int, default=20)
    ap.add_argument("--gate", type=int, default=8)
    ap.add_argument("--arms", type=str, default="base,veto_seal")
    ap.add_argument("--out", type=str, default="results/pressure.json")
    a = ap.parse_args()

    from run_bursty_v1_1_validity import build_v1_1
    model = build_v1_1()
    s = model.fit_summary()
    print(f"=== bursty v1.1: n_volleys={s['n_volleys']} n_clears={s['n_clears']} "
          f"volley_size_mean={s['volley_size_mean']:.3f} "
          f"gap_mean={s['inter_volley_gap_mean_s']:.2f} ===", flush=True)

    seeds = list(range(a.seed0, a.seed0 + a.seeds))
    arms = a.arms.split(",")
    print(f"=== SEAL UNDER PRESSURE  L{a.level}  n={len(seeds)}  gate=vc<={a.gate}  "
          f"arms={arms}  (champion wt={a.wt} ws={a.ws}) ===", flush=True)

    out = {"args": vars(a), "v1_1_fit": s, "arms": {}}
    for arm in arms:
        rows = run_arm(arm, seeds, a.level, a.wt, a.ws, a.gate, a.workers, model)
        err = [r for r in rows if "error" in r]
        ok = [r for r in rows if "error" not in r]
        if err:
            print(f"  [{arm}] {len(err)} ERRORED: {err[0].get('tb','')[:400]}", flush=True)
        bad = [r for r in ok if r["topout"] or r["stall"]]
        da = sum(r["dies_ahead"] for r in ok)
        ch = sum(r.get("changed_decisions", 0) for r in ok)
        gd = sum(r.get("gated_decisions", 0) for r in ok)
        print(f"  [{arm:14s}] n={len(ok):3d}  bad-ends {len(bad)}/{len(ok)} "
              f"({len(bad)/max(1,len(ok)):.1%})  dies-ahead {da}/{len(ok)} "
              f"({da/max(1,len(ok)):.1%})  won {sum(r['won'] for r in ok)}  "
              f"garbage/g {st.mean([r['garbage_injected'] for r in ok]):.2f}  "
              f"term changed {ch}/{gd} gated decisions", flush=True)
        out["arms"][arm] = {"rows": ok, "errors": err}

    if "base" in out["arms"]:
        b = {r["seed"]: r for r in out["arms"]["base"]["rows"]}
        for arm in arms:
            if arm == "base":
                continue
            t = {r["seed"]: r for r in out["arms"][arm]["rows"]}
            common = sorted(set(b) & set(t))
            dbad = [((t[s]["topout"] or t[s]["stall"]) - (b[s]["topout"] or b[s]["stall"]))
                    for s in common]
            dda = [t[s]["dies_ahead"] - b[s]["dies_ahead"] for s in common]
            both = [s for s in common if t[s]["won"] and b[s]["won"]]
            dp = [t[s]["pills"] - b[s]["pills"] for s in both]
            lo, hi = boot_ci(dbad)
            print(f"\n  PAIRED {arm} - base (n={len(common)})", flush=True)
            print(f"    d_bad_ends {sum(dbad):+d}  rate {st.mean(dbad):+.4f} "
                  f"[{lo:+.4f},{hi:+.4f}]  (negative = FEWER failures = better)", flush=True)
            print(f"    d_dies_ahead {sum(dda):+d}", flush=True)
            if dp:
                plo, phi = boot_ci(dp)
                print(f"    d_pills (both won, n={len(dp)}) {st.mean(dp):+.2f} "
                      f"[{plo:+.2f},{phi:+.2f}]", flush=True)
            out["arms"][arm]["paired"] = {
                "n": len(common), "d_bad_ends": sum(dbad),
                "d_bad_rate": st.mean(dbad), "d_bad_ci": [lo, hi],
                "d_dies_ahead": sum(dda),
                "d_pills_bothwon": (st.mean(dp) if dp else None), "n_both_won": len(dp)}

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh)
    print(f"\nwrote {a.out}\nDONE", flush=True)


if __name__ == "__main__":
    main()
