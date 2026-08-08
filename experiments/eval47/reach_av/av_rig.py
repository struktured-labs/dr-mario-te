#!/usr/bin/env python3
"""A_v DOSE-RESPONSE under bursty-v1.1 garbage pressure.

Arms (all wt=0, ws=20 -- the shipped strand180_20 champion):
  baseline   reach=OFF, w_rdyext=8            (the champion itself)
  A_v        reach=ON,  w_rdyext in 8/16/24/32/48
  control    reach=OFF, w_rdyext=<scale-matched>   <-- MANDATORY.  A_v changes both
             the SHAPE and the SCALE of the term; without a scalar-only arm at a
             matched mean contribution, a win is attributable to the scalar, which
             coefficient optimisation already searched and closed.

The game loop, garbage model, metrics and dies-ahead definition are the SHIPPED
`pressure_rig.py` -- not a copy.  This module only swaps the decider function that
`pressure_rig.play()` calls, so the two arms cannot drift apart in anything except
the thing under test.  `--selfcheck` proves that: reach=OFF/w=8 through the patched
path must reproduce pressure_rig's own arm ROW-FOR-ROW.

PRIMARY endpoint: paired dies-ahead (McNemar, discordant counts printed).
Secondary: bad-ends (topout + stall).

Usage:
  av_rig.py --selfcheck --seeds 24 --workers 6
  av_rig.py --seeds 300 --workers 6 --out results/av_bursty_n300
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import reach_leaf as RL
import pressure_rig as PR

WS = 20      # shipped strand180_20
WT = 0
LEVEL = 11
CHAMPION_W_RDYEXT = 8.0
DOSES = [8, 16, 24, 32, 48]

_SHIPPED_CHOOSE_BASE = PR._choose_base     # kept so --selfcheck can compare


def _init(level, reach, w_rdyext, model_kind, bursty_model_obj):
    """Worker init: the shipped rig's own _init, then (a) the dosed weight vector
    and (b) the reach-aware decider swapped in."""
    RL.warmup()
    PR._init(level, WT, WS, model_kind, bursty_model_obj)
    PR._C["w"][RL.R_RDYEXT] = float(w_rdyext)
    reach = int(reach)
    if reach or float(w_rdyext) != CHAMPION_W_RDYEXT:
        def _choose(col, vir, ca, cb, na, nb, w, fl, wt, ws, _r=reach):
            return RL.choose_base_rx(col, vir, ca, cb, na, nb, w, fl, wt, ws, _r)
        PR._choose_base = _choose
    else:
        # champion arm: leave the SHIPPED function in place, so the baseline is
        # literally the shipped code path and not a re-implementation of it.
        PR._choose_base = _SHIPPED_CHOOSE_BASE


def _init_patched_always(level, reach, w_rdyext, model_kind, bursty_model_obj):
    """--selfcheck variant: force the patched decider even for the champion arm."""
    RL.warmup()
    PR._init(level, WT, WS, model_kind, bursty_model_obj)
    PR._C["w"][RL.R_RDYEXT] = float(w_rdyext)
    reach = int(reach)

    def _choose(col, vir, ca, cb, na, nb, w, fl, wt, ws, _r=reach):
        return RL.choose_base_rx(col, vir, ca, cb, na, nb, w, fl, wt, ws, _r)
    PR._choose_base = _choose


def run_arm(level, seeds, workers, reach, w_rdyext, model_kind, bursty_model_obj,
            init=_init, seed_list=None):
    rows = []
    slist = list(range(seeds)) if seed_list is None else list(seed_list)
    with ProcessPoolExecutor(max_workers=workers, initializer=init,
                             initargs=(level, reach, w_rdyext, model_kind,
                                       bursty_model_obj)) as ex:
        futs = [ex.submit(PR.play, s) for s in slist]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, len(slist) // 4) == 0 or (i + 1) == len(slist):
                PR._log_rss(f"reach={reach} w={w_rdyext} {i + 1}/{len(slist)}")
    stamp = RL.arm_stamp(reach, w_rdyext, WT, WS)
    for r in rows:
        r.update(stamp)
    print(f"  arm reach={reach} w_rdyext={w_rdyext} done ({len(rows)} games)", flush=True)
    return {r["seed"]: r for r in rows}


# ------------------------------------------------------------------ statistics
def mcnemar(ctrl, arm, key):
    """Exact two-sided McNemar on a 0/1 per-seed outcome.  `key` is a BAD event:
    b = ctrl bad & arm good, c = ctrl good & arm bad."""
    ss = sorted(set(ctrl) & set(arm))
    b = sum(1 for s in ss if ctrl[s][key] and not arm[s][key])
    c = sum(1 for s in ss if not ctrl[s][key] and arm[s][key])
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 0.0
    for i in range(0, k + 1):
        p += math.comb(n, i) * (0.5 ** n)
    p = min(1.0, 2.0 * p)
    return b, c, p


def summarise(ctrl, arm, tag):
    ss = sorted(set(ctrl) & set(arm))
    n = len(ss)
    da0 = sum(ctrl[s]["dies_ahead"] for s in ss)
    da1 = sum(arm[s]["dies_ahead"] for s in ss)
    be0 = sum(ctrl[s]["topout"] + ctrl[s]["stall"] for s in ss)
    be1 = sum(arm[s]["topout"] + arm[s]["stall"] for s in ss)
    cl0 = sum(ctrl[s]["won"] for s in ss)
    cl1 = sum(arm[s]["won"] for s in ss)
    for s in ss:
        ctrl[s]["_bad"] = int(bool(ctrl[s]["topout"] or ctrl[s]["stall"]))
        arm[s]["_bad"] = int(bool(arm[s]["topout"] or arm[s]["stall"]))
    b_da, c_da, p_da = mcnemar(ctrl, arm, "dies_ahead")
    b_be, c_be, p_be = mcnemar(ctrl, arm, "_bad")
    both = [s for s in ss if ctrl[s]["won"] and arm[s]["won"]]
    d = [arm[s]["pills"] - ctrl[s]["pills"] for s in both]
    lo, hi = PR.boot_ci(d) if d else (float("nan"), float("nan"))
    gb0 = st.mean([ctrl[s]["garbage_injected"] for s in ss])
    gb1 = st.mean([arm[s]["garbage_injected"] for s in ss])
    row = {"tag": tag, "n": n,
           "dies_ahead0": da0, "dies_ahead1": da1,
           "dies_ahead_rate0": da0 / n, "dies_ahead_rate1": da1 / n,
           "dies_ahead_delta_pts": 100.0 * (da0 - da1) / n,
           "da_discordant_b": b_da, "da_discordant_c": c_da,
           "da_discordant_n": b_da + c_da, "da_p": p_da,
           "bad_ends0": be0, "bad_ends1": be1,
           "bad_rate0": be0 / n, "bad_rate1": be1 / n,
           "bad_delta_pts": 100.0 * (be0 - be1) / n,
           "be_discordant_b": b_be, "be_discordant_c": c_be,
           "be_discordant_n": b_be + c_be, "be_p": p_be,
           "clear0": cl0 / n, "clear1": cl1 / n,
           "pills_delta": (st.mean(d) if d else None), "pills_ci": [lo, hi],
           "pills_n": len(d),
           "garbage0": gb0, "garbage1": gb1,
           "kernel_hash": RL.kernel_hash()}
    print(f"  {tag:>34s}  n={n}  "
          f"dies-ahead {da0}/{n}={da0 / n:6.2%} -> {da1}/{n}={da1 / n:6.2%} "
          f"(delta {row['dies_ahead_delta_pts']:+5.2f} pts, disc b={b_da} c={c_da} "
          f"N={b_da + c_da}, p={p_da:.4f})", flush=True)
    print(f"  {'':>34s}  bad-ends   {be0}/{n}={be0 / n:6.2%} -> {be1}/{n}={be1 / n:6.2%} "
          f"(delta {row['bad_delta_pts']:+5.2f} pts, disc b={b_be} c={c_be} "
          f"N={b_be + c_be}, p={p_be:.4f})  clear {cl0 / n:.1%}->{cl1 / n:.1%}", flush=True)
    return row


# ------------------------------------------------------------------- selfcheck
def selfcheck(seeds, workers, bursty_model_obj):
    """The patched decider at reach=0, w_rdyext=8 must reproduce the SHIPPED
    pressure_rig arm row-for-row.  Any difference here voids every A/B number."""
    print(f"=== SELFCHECK: patched path (reach=0, w=8) vs shipped pressure_rig, "
          f"n={seeds} bursty seeds ===", flush=True)
    shipped = run_arm(LEVEL, seeds, workers, 0, CHAMPION_W_RDYEXT, "bursty",
                      bursty_model_obj, init=_init)
    patched = run_arm(LEVEL, seeds, workers, 0, CHAMPION_W_RDYEXT, "bursty",
                      bursty_model_obj, init=_init_patched_always)
    keys = ("won", "topout", "stall", "pills", "funnel", "funnel_mm", "mm_vert",
            "garbage_injected", "stranded_final", "tower_final",
            "viruses_left_at_end", "dies_ahead")
    bad = []
    for s in sorted(shipped):
        for k in keys:
            if shipped[s][k] != patched[s][k]:
                bad.append(f"seed {s} {k}: shipped {shipped[s][k]} != patched {patched[s][k]}")
    if bad:
        print(f"SELFCHECK FAILED -- {len(bad)} field mismatch(es):")
        for x in bad[:20]:
            print("   ", x)
        return False
    print(f"SELFCHECK PASSED: {len(shipped)} games, {len(keys)} fields each, "
          f"{len(shipped) * len(keys)} comparisons, 0 mismatches", flush=True)
    return True


def build_v11():
    import run_bursty_v1_1_validity as V11
    m = V11.build_v1_1()
    s = m.fit_summary()
    print(f"=== bursty v1.1 (honest, struktured-only): n_volleys={s['n_volleys']} "
          f"n_clears={s['n_clears']} volley_size_mean={s['volley_size_mean']:.3f} ===",
          flush=True)
    assert s["n_volleys"] == 28 and s["n_clears"] == 89, (
        f"CONTAMINATED POOL: n_volleys={s['n_volleys']} n_clears={s['n_clears']} "
        f"-- want 28/89 (61/188 is the pool-contaminated v1). STOP.")
    m.meta = {k: v for k, v in m.meta.items() if k != "raw_events"}
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=300)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--level", type=int, default=LEVEL)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--selfcheck-seeds", type=int, default=24)
    ap.add_argument("--control-weight", type=float, nargs="+", default=None,
                    help="scale-matched reach=OFF control weight(s) (from av_audit.py's "
                         "scale-match ratio, one per dose). Required unless --selfcheck.")
    ap.add_argument("--doses", type=float, nargs="+", default=DOSES)
    ap.add_argument("--out", type=str, default=None)
    a = ap.parse_args()

    RL.warmup()
    print(f"=== A_v DOSE-RESPONSE  kernel_hash={RL.kernel_hash()}  "
          f"L{a.level} n={a.seeds} wt={WT} ws={WS} model=bursty-v1.1 ===", flush=True)
    bm = build_v11()

    if a.selfcheck:
        ok = selfcheck(a.selfcheck_seeds, a.workers, bm)
        return 0 if ok else 1

    if a.control_weight is None:
        print("ERROR: --control-weight is mandatory (see av_audit.py's scale-match "
              "ratio). Refusing to run a dose sweep without the scalar control.")
        return 2

    base = run_arm(a.level, a.seeds, a.workers, 0, CHAMPION_W_RDYEXT, "bursty", bm)
    n = len(base)
    da = sum(base[s]["dies_ahead"] for s in base)
    be = sum(base[s]["topout"] + base[s]["stall"] for s in base)
    print(f"\nBASELINE (champion, reach=OFF w_rdyext=8, wt=0 ws=20): "
          f"dies-ahead {da}/{n} = {da / n:.2%}   bad-ends {be}/{n} = {be / n:.2%}   "
          f"clear {sum(base[s]['won'] for s in base) / n:.1%}\n", flush=True)

    arms = ([(1, float(d)) for d in a.doses]
            + [(0, float(cw)) for cw in a.control_weight])
    results = []
    raw = {"baseline": [base[s] for s in sorted(base)]}
    for reach, wv in arms:
        got = run_arm(a.level, a.seeds, a.workers, reach, wv, "bursty", bm)
        tag = (f"A_v w_rdyext={wv:g}" if reach
               else f"SCALE-CTRL (no reach) w={wv:g}")
        results.append(summarise(base, got, tag))
        raw[f"reach{reach}_w{wv:g}"] = [got[s] for s in sorted(got)]
        if a.out:
            with open(f"{a.out}.json", "w") as fh:
                json.dump({"kernel_hash": RL.kernel_hash(), "n": a.seeds,
                           "level": a.level, "wt": WT, "ws": WS,
                           "control_weight": a.control_weight,
                           "baseline": {"n": n, "dies_ahead": da, "bad_ends": be},
                           "arms": results, "raw": raw}, fh)

    print("\n=== SUMMARY (baseline = champion strand180_20, reach OFF, w_rdyext=8) ===")
    print(f"  baseline: dies-ahead {da}/{n} = {da / n:.2%}   bad-ends {be}/{n} = {be / n:.2%}")
    for r in results:
        print(f"  {r['tag']:>34s}  DA {r['dies_ahead1']:3d}/{r['n']} "
              f"({r['dies_ahead_rate1']:6.2%}, {r['dies_ahead_delta_pts']:+5.2f} pts, "
              f"disc {r['da_discordant_n']:3d}, p={r['da_p']:.4f})   "
              f"BE {r['bad_ends1']:3d}/{r['n']} ({r['bad_rate1']:6.2%}, "
              f"{r['bad_delta_pts']:+5.2f} pts, disc {r['be_discordant_n']:3d}, "
              f"p={r['be_p']:.4f})")
    print("\nDONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
