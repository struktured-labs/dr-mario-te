#!/usr/bin/env python3
"""Phase 2: priced fire-gate dose-response sweep for root-action tucks (v3).

Adds a margin gate theta to root_search.choose_root_with_tucks: a tuck candidate is
chosen only if its value beats the best BASE action's value by >= theta. theta=0.0 is
EXACTLY phase 1 (no gate) -- verified two ways, see `verify_theta0()`:
  (a) root_search.equivalence_selftest() already proves theta=0's base-only path is
      byte-identical to the untouched shipped decider (unaffected by this phase's changes
      -- the margin gate only touches the tuck branch).
  (b) NEW: replay a handful of the seeds from phase 1's own stored JSON rows through
      play(theta=0.0) and assert pills/fired/won match EXACTLY. This is the "assert on a
      handful of seeds" the phase-2 task literally asked for.

REUSE, not re-run: the OFF arm (tuck disabled) does not depend on theta at all -- with
tuck_cands forced to [] there is nothing for the gate to touch. Phase 1's off-arm rows
(results/root_v3_L{level}.json, seeds 0..119) are loaded as a cache; only seeds beyond
what phase 1 already ran (L20 needs seeds 120..239 for its n=240 leg) are computed fresh,
and the extended cache is written back so a second sweep point at the same n is instant.

Usage:
  python3 sweep_theta.py --verify-theta0        # (b) above, cheap, run first
  python3 sweep_theta.py --level 11 --seeds 120 --thetas 0 50 100 200 400 800 1600 --workers 16
  python3 sweep_theta.py --level 20 --seeds 240 --thetas 0 100 200 400 --workers 16 --out results/sweep
"""
from __future__ import annotations

import sys
import os
import json
import argparse
import statistics as st
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ab_root as AB   # noqa: E402  (reuses _init, play, boot_ci, sign_test_p)


def _offarm_cache_path(level):
    return os.path.join(HERE, "results", f"offcache_L{level}.json")


def _phase1_path(level):
    return os.path.join(HERE, "results", f"root_v3_L{level}.json")


def load_offarm_cache(level):
    """{seed: row}, seeded from the offcache file if present, else phase 1's stored
    off-arm rows (results/root_v3_L{level}.json), else empty."""
    cp = _offarm_cache_path(level)
    if os.path.exists(cp):
        with open(cp) as fh:
            raw = json.load(fh)
        return {int(k): v for k, v in raw.items()}
    p1 = _phase1_path(level)
    if os.path.exists(p1):
        with open(p1) as fh:
            data = json.load(fh)
        return {r["seed"]: r for r in data["off"]}
    return {}


def save_offarm_cache(level, cache):
    with open(_offarm_cache_path(level), "w") as fh:
        json.dump({str(k): v for k, v in cache.items()}, fh)


def ensure_offarm(level, seeds, P, exec_only, workers):
    """Return {seed: row} for seed in range(seeds), extending the cache if needed."""
    cache = load_offarm_cache(level)
    missing = [s for s in range(seeds) if s not in cache]
    if missing:
        print(f"  off-arm cache has {len(cache)} seeds; running {len(missing)} missing "
              f"({missing[0]}..{missing[-1]})", flush=True)
        with ProcessPoolExecutor(max_workers=workers, initializer=AB._init,
                                 initargs=(level, 0, P, exec_only)) as ex:
            for f in as_completed([ex.submit(AB.play, s) for s in missing]):
                r = f.result()
                cache[r["seed"]] = r
        save_offarm_cache(level, cache)
    return {s: cache[s] for s in range(seeds)}


def run_onarm(level, theta, seeds, P, exec_only, workers):
    rows = {}
    with ProcessPoolExecutor(max_workers=workers, initializer=AB._init,
                             initargs=(level, 1, P, exec_only, theta)) as ex:
        for f in as_completed([ex.submit(AB.play, s) for s in range(seeds)]):
            r = f.result()
            rows[r["seed"]] = r
    return rows


def paired_stats(off, on, seeds, level, theta):
    all_seeds = sorted(set(off) & set(on) & set(range(seeds)))
    both = [s for s in all_seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = AB.boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)

    c_off = sum(off[s]["won"] for s in all_seeds) / len(all_seeds)
    c_on = sum(on[s]["won"] for s in all_seeds) / len(all_seeds)
    disc = [(off[s]["won"], on[s]["won"]) for s in all_seeds if off[s]["won"] != on[s]["won"]]
    won_only_on = sum(1 for o, n in disc if n)
    won_only_off = len(disc) - won_only_on
    p_clear = AB.sign_test_p(won_only_on, won_only_off)

    # clear-rate delta paired CI (for theta* selection: "L20 clear-rate delta CI incl 0")
    clear_delta = [on[s]["won"] - off[s]["won"] for s in all_seeds]
    lo_c, hi_c = AB.boot_ci(clear_delta)

    fires = [on[s]["fired"] for s in all_seeds]

    # WHERE do tuck-only-loss seeds fire, vs tuck-only-win seeds, by regime?
    loss_seeds = [s for s in all_seeds if off[s]["won"] and not on[s]["won"]]
    win_seeds = [s for s in all_seeds if not off[s]["won"] and on[s]["won"]]

    def regime_totals(seedlist):
        tot = {"open": 0, "mid": 0, "end": 0}
        for s in seedlist:
            fbr = on[s].get("fired_by_regime", {})
            for k in tot:
                tot[k] += fbr.get(k, 0)
        return tot

    loss_regime = regime_totals(loss_seeds)
    win_regime = regime_totals(win_seeds)

    all_margins = [m for s in all_seeds for m in on[s].get("margins", [])]

    return {
        "level": level, "theta": theta, "seeds": len(all_seeds),
        "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
        "paired_pills_ci": [lo, hi],
        "paired_n": len(both), "better": better, "worse": worse, "tie": len(d) - better - worse,
        "clear_off": c_off, "clear_on": c_on,
        "clear_delta_ci": [lo_c, hi_c],
        "discordant": len(disc), "tuck_only_wins": won_only_on, "tuck_only_losses": won_only_off,
        "sign_test_p": p_clear,
        "fires_per_game": st.mean(fires) if fires else 0.0,
        "loss_seeds": loss_seeds, "win_seeds": win_seeds,
        "loss_fires_by_regime": loss_regime, "win_fires_by_regime": win_regime,
        "margin_p50": (st.median(all_margins) if all_margins else float("nan")),
        "margin_min": (min(all_margins) if all_margins else float("nan")),
        "margin_max": (max(all_margins) if all_margins else float("nan")),
    }


def print_row(s):
    lo, hi = s["paired_pills_ci"]
    verdict = "REAL" if (hi < 0 or lo > 0) else "wash"
    lo_c, hi_c = s["clear_delta_ci"]
    clear_verdict = "incl.0" if (lo_c <= 0 <= hi_c) else ("ALL+" if lo_c > 0 else "ALL-")
    print(f"theta={s['theta']:>7.1f}  pills {s['paired_pills_delta_mean']:+7.2f} "
          f"[{lo:+7.2f},{hi:+7.2f}] {verdict:4s}  clear {s['clear_off']:.1%}->{s['clear_on']:.1%} "
          f"(delta CI {clear_verdict})  fires/g {s['fires_per_game']:5.2f}  "
          f"disc {s['discordant']:2d} (W{s['tuck_only_wins']}/L{s['tuck_only_losses']}) "
          f"p={s['sign_test_p']:.3f}")


def verify_theta0(level=11, n_check=10, P=12, exec_only=True):
    """(b) from the module docstring: replay N seeds from phase 1's STORED on-arm JSON
    rows through play(theta=0.0) and assert pills/fired/won match exactly."""
    p1 = _phase1_path(level)
    with open(p1) as fh:
        data = json.load(fh)
    stored = {r["seed"]: r for r in data["on"]}
    AB._init(level, 1, P, exec_only, theta=0.0)
    checked = mism = 0
    for s in sorted(stored)[:n_check]:
        got = AB.play(s)
        ref = stored[s]
        ok = (got["pills"] == ref["pills"] and got["fired"] == ref["fired"]
              and got["won"] == ref["won"])
        checked += 1
        if not ok:
            mism += 1
            print(f"  MISMATCH seed={s}: got pills={got['pills']} fired={got['fired']} "
                  f"won={got['won']}  vs phase1 pills={ref['pills']} fired={ref['fired']} "
                  f"won={ref['won']}")
    print(f"verify_theta0: {checked} seeds replayed against phase-1 L{level} JSON, "
          f"{mism} mismatches")
    return mism == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--thetas", type=float, nargs="+", default=[0.0])
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--P", type=int, default=12)
    ap.add_argument("--exec-only", type=int, default=1)
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--verify-theta0", action="store_true")
    ap.add_argument("--verify-level", type=int, default=11)
    a = ap.parse_args()

    if a.verify_theta0:
        ok = verify_theta0(a.verify_level)
        sys.exit(0 if ok else 1)

    print(f"=== theta sweep, L{a.level}, n={a.seeds}, thetas={a.thetas} ===", flush=True)
    off = ensure_offarm(a.level, a.seeds, a.P, bool(a.exec_only), a.workers)
    print(f"  off-arm ready: {len(off)} seeds", flush=True)

    results = []
    for theta in a.thetas:
        on = run_onarm(a.level, theta, a.seeds, a.P, bool(a.exec_only), a.workers)
        s = paired_stats(off, on, a.seeds, a.level, theta)
        print_row(s)
        results.append(s)
        if a.out:
            fn = f"{a.out}_L{a.level}_theta{theta:g}.json"
            with open(fn, "w") as fh:
                json.dump({"summary": s, "on": [on[k] for k in sorted(on)]}, fh)

    if a.out:
        fn = f"{a.out}_L{a.level}_curve.json"
        with open(fn, "w") as fh:
            json.dump(results, fh)
        print(f"wrote {fn}")


if __name__ == "__main__":
    main()
