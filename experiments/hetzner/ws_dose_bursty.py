#!/usr/bin/env python3
"""ws_dose_bursty.py -- the SHAPE of failure rate vs the g_stranded dose `ws`,
under human-fitted bursty v1.1 pressure.

THE QUESTION. The shipped champion pins ws=20, chosen on mirror margin and VS
win rate -- SPEED and ATTACK. `BURSTY_V1_RESULTS.md` §5 already establishes two
points of the curve at n=120 under bursty v1.1:

    ws=0   47/120 bad-ends (39.2%),  dies-ahead 33/120 (27.5%)
    ws=20  20/120 bad-ends (16.7%),  dies-ahead  9/120 ( 7.5%)

So the dose helps a lot. Nobody has asked the next question: **is 20 the
failure-optimal dose, or merely the first one tried?** This fills in the curve
above and below it. The finding is the DIRECTION and SIZE of any gap between
the failure-optimal dose and the shipped 20 -- not the winning number.

WHY IT'S A HYPOTHESIS TEST, not a tuning run. The project's current framing is
that the champion is RISK-NEUTRAL near an absorbing state: it maximises expected
clearing progress while the real objective is P(win), and "dies while ahead" is
close to a definition of that failure. If the failure-optimal dose sits well
above 20, the shipped constant is tuned for speed at a measurable cost in
survival, and the two objectives genuinely diverge. **If failure-optimal is
approximately 20, the objectives coincide here and the risk-neutrality story is
weaker than assumed -- that outcome gets reported just as loudly.**

WHY IT DRIVES pressure_rig.run_arm INSTEAD OF A PRIVATE COPY. run_arm is the
exact code path that produced the §5 anchors. Driving it means these numbers are
directly comparable to the published ones rather than merely similar, and the
ws=0/ws=20 arms here double as a replication of §5 at larger n -- a built-in
control on the whole rig. A private reimplementation would have to earn that
trust separately.

⚠ Bursty pairing is by SEED, not by garbage sequence. The volley trigger is the
arm's OWN clear timing, so once two doses diverge they see different garbage.
That is inherent to the model (BURSTY_V1_RESULTS.md §1 says so explicitly); the
seed is the honest pairing unit and McNemar is computed on it.

Usage: ws_dose_bursty.py --doses 0 10 20 40 80 --n 300 --workers 4 --out DIR
"""
from __future__ import annotations

import sys
import os
import json
import time
import argparse
from math import comb

QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (QA + "/eval47", QA):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bursty_model as BM          # noqa: E402
import fit_ensemble_source as FE   # noqa: E402
import pressure_rig as PR          # noqa: E402

CONTROL_WS = 20     # the shipped dose


HERE = os.path.dirname(os.path.abspath(__file__))
PKL = os.path.join(HERE, "bursty_v1_1.pkl")


def build_v1_1():
    """bursty v1.1, either unpickled (compute nodes) or fitted from footage.

    The fit reads 1fps JPEG frames plus a `vision.py` calibrated against them,
    which is not present on a compute node and shouldn't be. `fit_bursty_v11.py`
    performs the fit once where the footage lives and pickles the result; this
    prefers that file and falls back to fitting. Shipping the fitted OBJECT is
    also better provenance than two independent re-fits that are merely supposed
    to agree."""
    if os.path.exists(PKL):
        import pickle
        with open(PKL, "rb") as f:
            return pickle.load(f)
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    all_volleys, all_clears = [], []
    for _mid, res in raw.items():
        all_volleys.extend(res["volleys"])
        all_clears.extend(res["clears"])
    return FE.fit_per_player(all_volleys, all_clears, m_v1.n_matches, "P1",
                             dict(BM.DEFAULT_OPPONENT_OF))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) * (0.5 ** n))


def failed(row):
    """A game is a BAD END if it wasn't won -- topout or stall alike. Matches
    pressure_rig/compare's own 'deaths+stalls' convention."""
    return not row["won"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doses", type=int, nargs="+", default=[0, 10, 20, 40, 80])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)

    v1_1 = build_v1_1()
    s = v1_1.fit_summary()
    print(f"[bursty v1.1] n_volleys={s['n_volleys']} n_clears={s['n_clears']} "
          f"volley_size_mean={s['volley_size_mean']:.3f} "
          f"gap_mean={s['inter_volley_gap_mean_s']:.2f}", flush=True)
    # Guard: v1.1 is the struktured-only fit (28 volleys / 89 clears). If this
    # prints v1's 61/188 we are measuring the AI-contaminated model by mistake.
    if int(s["n_volleys"]) != 28:
        print(f"  ⚠ EXPECTED n_volleys=28 for v1.1, got {s['n_volleys']} -- "
              f"this may be the CONTAMINATED v1 pool", flush=True)

    arms = {}
    for ws in a.doses:
        path = os.path.join(a.out, f"arm_ws{ws}.json")
        if os.path.exists(path):            # resumable at dose granularity
            with open(path) as f:
                arms[ws] = {int(k): v for k, v in json.load(f).items()}
            print(f"[arm ws={ws}] loaded {len(arms[ws])} games from disk", flush=True)
            continue
        t0 = time.monotonic()
        print(f"[arm ws={ws}] running n={a.n} ...", flush=True)
        rows = PR.run_arm(a.level, a.n, a.workers, 0, ws, "bursty", v1_1)
        with open(path, "w") as f:
            json.dump({str(k): v for k, v in rows.items()}, f)
        arms[ws] = rows
        dt = time.monotonic() - t0
        nf = sum(1 for r in rows.values() if failed(r))
        print(f"[arm ws={ws}] {len(rows)} games in {dt / 60:.1f}m "
              f"({len(rows) / dt:.2f} g/s)  bad-ends {nf}/{len(rows)} "
              f"({100 * nf / len(rows):.1f}%)", flush=True)

    report(arms, a.out)


def report(arms, out_dir):
    doses = sorted(arms)
    ctrl = arms.get(CONTROL_WS)

    print(f"\n{'ws':>4} {'n':>5} {'bad-end':>9} {'dies-ahead':>11} "
          f"{'resc':>5} {'brok':>5} {'net':>5} {'McNemar p':>10}")
    print("-" * 64)
    table = []
    for ws in doses:
        arm = arms[ws]
        n = len(arm)
        nf = sum(1 for r in arm.values() if failed(r))
        nda = sum(1 for r in arm.values() if r.get("dies_ahead"))
        resc = brok = 0
        p = float("nan")
        if ctrl is not None and ws != CONTROL_WS:
            common = sorted(set(arm) & set(ctrl))
            resc = sum(1 for s in common if failed(ctrl[s]) and not failed(arm[s]))
            brok = sum(1 for s in common if not failed(ctrl[s]) and failed(arm[s]))
            p = mcnemar_exact(resc, brok)
        tag = "  <-- SHIPPED" if ws == CONTROL_WS else ""
        print(f"{ws:>4} {n:>5} {nf:>4}/{n:<4} {100 * nf / n:>5.1f}% "
              f"{nda:>4} ({100 * nda / n:>4.1f}%) "
              f"{resc:>5} {brok:>5} {resc - brok:>5} {p:>10.4f}{tag}")
        table.append({"ws": ws, "n": n, "bad_ends": nf, "bad_end_rate": nf / n,
                      "dies_ahead": nda, "dies_ahead_rate": nda / n,
                      "rescued_vs_ws20": resc, "broken_vs_ws20": brok,
                      "net_vs_ws20": resc - brok, "mcnemar_p": p})

    best = min(table, key=lambda r: r["bad_end_rate"])
    shipped = next((r for r in table if r["ws"] == CONTROL_WS), None)
    print(f"\nfailure-optimal dose in this grid: ws={best['ws']} "
          f"({100 * best['bad_end_rate']:.1f}% bad-ends)")
    if shipped:
        gap = shipped["bad_end_rate"] - best["bad_end_rate"]
        print(f"shipped ws=20: {100 * shipped['bad_end_rate']:.1f}%  "
              f"=> gap {100 * gap:+.1f} points")
        if best["ws"] == CONTROL_WS:
            print("SHIPPED DOSE IS FAILURE-OPTIMAL in this grid -- speed-tuned and "
                  "survival-tuned coincide here; that WEAKENS the risk-neutrality story.")
        else:
            print(f"failure-optimal is {'ABOVE' if best['ws'] > CONTROL_WS else 'BELOW'} "
                  f"the shipped dose -- direction and size are the finding, "
                  f"but check net/McNemar before believing it.")

    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump({"table": table, "control_ws": CONTROL_WS}, f, indent=2)
    print(f"\nwrote {os.path.join(out_dir, 'summary.json')}")


if __name__ == "__main__":
    main()
