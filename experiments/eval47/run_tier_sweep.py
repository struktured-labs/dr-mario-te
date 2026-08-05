#!/usr/bin/env python3
"""ITERATION 4 PREP (task #67, team-lead follow-on): tier-parametric sweep
harness for the executability-tier knee sweep. Generalizes iteration 3's
reachexec reconciliation into an N-arm paired sweep over max_tier values,
using reach_root.py's choose_reach_tier(..., max_tier, tier_fn).

STUB VALIDATION (this run): tier_fn defaults to reach_root._stub_tier_of, a
TWO-TIER PLACEHOLDER (tier1 = TL.executable, tier2 = STUB_MAX_TIER =
everything) standing in for the tuck-bfs agent's eventual tier_of(col,
candidate) -> int (BFS-parent-chain-derived executability tiers, exact
number/definition of tiers is that agent's call). Sweeping max_tier over
(1, STUB_MAX_TIER) with this stub MUST reproduce choose_reachexec
(max_tier=1) and choose_reachfull2 (max_tier=STUB_MAX_TIER) EXACTLY -- both
at the fast decision level (reach_root.py's own
`_selftest_reach_tier_endpoints`, run separately, 0/60 mismatches) AND here,
end-to-end, by diffing this run's own max_tier=1/max_tier=STUB_MAX_TIER
per-seed game rows against the already-committed n=120 iteration-3 numbers
(results/reachexec_bursty_n120.json). This double proof (unit-level +
full-game-level) is the self-test that the sweep MACHINERY (this script's
own game loop, McNemar plumbing, N-arm pairing) adds nothing of its own --
only the chooser function differs.

ONE-LINE INVOCATION FOR WHEN REAL TIERS LAND: once the tuck-bfs agent's
extended translatable.py exposes tier_of(col, candidate) -> int, change
TIER_SWEEP below to the real tier range (e.g. `range(1, N + 1)`) and pass
`tier_fn=translatable.tier_of` into every `RR.choose_reach_tier(...)` call
in `play()` (currently omitted so the stub default applies) -- nothing else
in this file changes. Concretely:
    TIER_SWEEP = range(1, N + 1)                    # was (1, RR.STUB_MAX_TIER)
    RR.choose_reach_tier(fb, col, vir, ca, cb, na, nb, max_tier,
                          tier_fn=translatable.tier_of)   # add tier_fn=...
"""
from __future__ import annotations
import sys
import os
import json
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reach_root as RR
import reach_root_ab as AB
import bursty_model

SEEDS = 120
WORKERS = 6
LEVEL = 11

# The sweep: which max_tier values to run, each paired against base32 AND
# the reachfull2 oracle. With the two-tier stub these ARE the exact
# endpoints (1 = reachexec-equivalent, STUB_MAX_TIER = reachfull2-
# equivalent) -- see the module docstring for what changes when real tiers
# land.
TIER_SWEEP = (1, RR.STUB_MAX_TIER)

_C = {}


def _init(level, max_tier, pressure, bursty_model_obj=None):
    RR._lazy()
    _C.update(level=level, max_tier=max_tier, pressure=pressure, bursty_model_obj=bursty_model_obj)


def play(seed):
    """Same game loop/conventions as reach_root_ab.py's play() (bursty
    injection rule, dies_ahead threshold, tuck-cell execution), parameterized
    by max_tier instead of a fixed mode string. Deliberately duplicated
    rather than refactoring the already-validated play() in place, matching
    this program's own established convention (m3case2.py alongside
    m3case.py, tmp_logs/m3case_sensitivity.py alongside both) of adding a
    new file instead of risking already-committed numbers."""
    import numpy as np
    from drmario.faithful_env import FaithfulDrMarioEnv
    from drmario.faithful_game import LINK_LEFT, LINK_RIGHT, LINK_UP, LINK_DOWN
    from nes_pills import NesPillSource

    level, max_tier, pressure = _C["level"], _C["max_tier"], _C["pressure"]
    bursty_model_obj = _C.get("bursty_model_obj")
    if pressure == "bursty":
        from bursty_model import inject_bursty_garbage

    L = RR._lazy()
    FB, RS = L["FB"], L["RS"]

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=300)
    env.reset()
    NesPillSource(seed=seed).attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    res = "stall"
    fired_tuck = 0
    garbage_injected = 0
    v_at_topout = None   # matches reach_root_ab.py's own convention exactly

    for _ in range(300):
        fb = FB.from_board(env.board)
        if env.board.virus_count() == 0:
            res = "clear"
            break
        col, vir = RS.board_flat_from_fb(fb)
        ca, cb, na, nb = int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)
        # tier_fn omitted -> reach_root.choose_reach_tier defaults to the
        # stub. See module docstring for the one-line change when real
        # tiers land.
        best = RR.choose_reach_tier(fb, col, vir, ca, cb, na, nb, max_tier)

        occ_before = int(np.count_nonzero(env.board.color)) if pressure == "bursty" else 0

        if best["kind"] == "tuck":
            p = best["placement"]
            r0, c0, r1, c1 = p["cells"]
            col0, col1 = best["ca"], best["cb"]
            b = env.board
            b.color[r0, c0] = col0
            b.color[r1, c1] = col1
            if r0 == r1:
                b.link[r0, c0] = LINK_RIGHT
                b.link[r1, c1] = LINK_LEFT
            else:
                b.link[r0, c0] = LINK_DOWN
                b.link[r1, c1] = LINK_UP
            b.is_virus[r0, c0] = False
            b.is_virus[r1, c1] = False
            b.resolve()
            env.pills_placed += 1
            env.cur = env.nxt
            env.nxt = env._rand_pill()
            fired_tuck += 1
            if b.virus_count() == 0:
                res = "clear"
                break
            if b.spawn_blocked():
                res = "topout"
                v_at_topout = b.virus_count()
                break
            if env.pills_placed >= 300:
                break
        else:
            action = best["action"]
            if action is None:
                break
            _, _, term, trunc, info = env.step(int(action))
            if term:
                res = "clear" if info["won"] else "topout"
                if res == "topout":
                    v_at_topout = env.board.virus_count()
                break
            if trunc:
                break

        if pressure == "bursty" and env.pills_placed >= AB.GARBAGE_MIN_PILLS:
            occ_after = int(np.count_nonzero(env.board.color))
            clear_size = max(0, occ_before + 2 - occ_after)
            if clear_size > 0:
                landed = inject_bursty_garbage(
                    env.board, bursty_model_obj, seed, env.pills_placed, clear_size)
                garbage_injected += landed
            if env.board.virus_count() == 0:
                res = "clear"
                break
            if env.board.spawn_blocked():
                res = "topout"
                v_at_topout = env.board.virus_count()
                break

    dies_ahead = int(res == "topout" and v_at_topout is not None
                      and v_at_topout <= AB.DIES_AHEAD_VIRUS_THRESHOLD)
    return {"seed": seed, "won": int(res == "clear"), "topout": int(res == "topout"),
            "stall": int(res == "stall"), "pills": env.pills_placed,
            "fired_tuck": fired_tuck, "garbage_injected": garbage_injected,
            "viruses_left_at_end": v_at_topout if v_at_topout is not None else env.board.virus_count(),
            "dies_ahead": dies_ahead}


def run_tier_arm(level, seeds, workers, max_tier, pressure, bursty_model_obj):
    rows = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(level, max_tier, pressure, bursty_model_obj)) as ex:
        futs = [ex.submit(play, s) for s in range(seeds)]
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 5) == 0 or (i + 1) == seeds:
                print(f"  max_tier={max_tier} pressure={pressure} {i + 1}/{seeds}", flush=True)
    return {r["seed"]: r for r in rows}


_ROW_FIELDS = ("won", "topout", "stall", "pills", "fired_tuck", "garbage_injected",
              "viruses_left_at_end", "dies_ahead")


def _diff_rows(a, b):
    """Count seeds where any of _ROW_FIELDS differs between two {seed: row}
    dicts. Returns (n_diff, first 3 examples) for a readable report."""
    n_diff = 0
    examples = []
    for s in sorted(set(a) & set(b)):
        ra, rb = a[s], b[s]
        bad = [f for f in _ROW_FIELDS if ra.get(f) != rb.get(f)]
        if bad:
            n_diff += 1
            if len(examples) < 3:
                examples.append((s, bad, {f: ra.get(f) for f in bad}, {f: rb.get(f) for f in bad}))
    return n_diff, examples


def main():
    bursty_model_obj = bursty_model.fit_struktured_20260804()
    bursty_model_obj.meta = {k: v for k, v in bursty_model_obj.meta.items() if k != "raw_events"}
    print(f"=== bursty-v1 fit: n_matches={bursty_model_obj.n_matches} "
          f"n_volleys={bursty_model_obj.n_volleys} n_clears={bursty_model_obj.n_clears} ===", flush=True)
    print(f"=== tier sweep, L{LEVEL}, n={SEEDS}, pressure=bursty, "
          f"tiers={TIER_SWEEP} (stub: 1=TL.executable, {RR.STUB_MAX_TIER}=everything) ===", flush=True)

    base32 = AB.run_arm(LEVEL, SEEDS, WORKERS, "base32", "bursty", bursty_model_obj)
    reachfull2 = AB.run_arm(LEVEL, SEEDS, WORKERS, "reachfull2", "bursty", bursty_model_obj)

    tier_rows = {}
    for max_tier in TIER_SWEEP:
        tier_rows[max_tier] = run_tier_arm(LEVEL, SEEDS, WORKERS, max_tier, "bursty", bursty_model_obj)

    print()
    summaries = {}
    for max_tier in TIER_SWEEP:
        rows = tier_rows[max_tier]
        s_base = AB.compare(base32, rows, f"tier<={max_tier} vs base32   ")
        s_oracle = AB.compare(reachfull2, rows, f"tier<={max_tier} vs reachfull2")
        summaries[max_tier] = {"vs_base32": s_base, "vs_reachfull2": s_oracle}

    # ---- bad-ends-survival-vs-tier curve --------------------------------
    base_bad = sum(base32[s]["topout"] + base32[s]["stall"] for s in base32)
    oracle_bad = sum(reachfull2[s]["topout"] + reachfull2[s]["stall"] for s in reachfull2)
    oracle_rescue = base_bad - oracle_bad
    print("\n=== bad-ends-survival-vs-tier curve ===")
    print(f"base32 bad-ends={base_bad}  reachfull2(oracle) bad-ends={oracle_bad}  "
          f"oracle rescue={oracle_rescue}")
    print(f"{'max_tier':>8} {'bad_ends':>9} {'rescued':>8} {'survival_of_oracle_rescue':>27}")
    curve = []
    for max_tier in TIER_SWEEP:
        rows = tier_rows[max_tier]
        be = sum(rows[s]["topout"] + rows[s]["stall"] for s in rows)
        rescued = base_bad - be
        survival = rescued / oracle_rescue if oracle_rescue else float("nan")
        print(f"{max_tier:>8} {be:>9} {rescued:>8} {survival:>26.1%}")
        curve.append({"max_tier": max_tier, "bad_ends": be, "rescued": rescued,
                       "survival_of_oracle_rescue": survival})

    # ---- McNemar table vs BOTH base32 and the reachfull2 oracle ---------
    print("\n=== McNemar table, every tier vs base32 AND vs the reachfull2 oracle ===")
    for max_tier in TIER_SWEEP:
        sb, so = summaries[max_tier]["vs_base32"], summaries[max_tier]["vs_reachfull2"]
        print(f"  max_tier={max_tier}: vs base32    rescued={sb['mcnemar_rescued']} "
              f"harmed={sb['mcnemar_harmed']} p={sb['mcnemar_p']:.4g}")
        print(f"              vs reachfull2 rescued={so['mcnemar_rescued']} "
              f"harmed={so['mcnemar_harmed']} p={so['mcnemar_p']:.4g}")

    # ---- END-TO-END STUB VALIDATION: diff against the committed          --
    # ---- iteration-3 numbers (results/reachexec_bursty_n120.json)        --
    print("\n=== STUB ENDPOINT VALIDATION vs already-committed iteration-3 rows ===")
    prior_path = f"{HERE}/results/reachexec_bursty_n120.json"
    validation = {"skipped": True, "reason": "prior file not found"}
    if os.path.exists(prior_path):
        prior = json.load(open(prior_path))
        prior_reachexec = {r["seed"]: r for r in prior["raw"]["reachexec"]}
        prior_reachfull2 = {r["seed"]: r for r in prior["raw"]["reachfull2"]}

        n_diff_lo, ex_lo = _diff_rows(tier_rows[1], prior_reachexec)
        n_diff_hi, ex_hi = _diff_rows(tier_rows[RR.STUB_MAX_TIER], prior_reachfull2)
        # also cross-check THIS run's own freshly-computed reachfull2 arm
        # against the prior committed reachfull2 rows (both should be
        # identical too -- same deterministic seeds, same code path).
        n_diff_fresh, ex_fresh = _diff_rows(reachfull2, prior_reachfull2)

        ok = n_diff_lo == 0 and n_diff_hi == 0 and n_diff_fresh == 0
        print(f"  max_tier=1 vs prior reachexec rows:            "
              f"{n_diff_lo}/{SEEDS} seeds differ  {'PASS' if n_diff_lo == 0 else 'FAIL ' + str(ex_lo)}")
        print(f"  max_tier={RR.STUB_MAX_TIER} vs prior reachfull2 rows:            "
              f"{n_diff_hi}/{SEEDS} seeds differ  {'PASS' if n_diff_hi == 0 else 'FAIL ' + str(ex_hi)}")
        print(f"  this run's fresh reachfull2 vs prior reachfull2 rows: "
              f"{n_diff_fresh}/{SEEDS} seeds differ  {'PASS' if n_diff_fresh == 0 else 'FAIL ' + str(ex_fresh)}")
        print(f"\n  STUB ENDPOINT VALIDATION: {'PASS' if ok else 'FAIL'}")
        validation = {"skipped": False, "pass": ok, "n_diff_tier1_vs_reachexec": n_diff_lo,
                      "n_diff_tierN_vs_reachfull2": n_diff_hi,
                      "n_diff_fresh_reachfull2_vs_prior": n_diff_fresh}
    else:
        print(f"  SKIPPED: {prior_path} not found")

    out = {"tier_sweep": list(TIER_SWEEP), "stub_max_tier": RR.STUB_MAX_TIER,
           "summaries": {str(k): v for k, v in summaries.items()},
           "bad_ends_survival_curve": curve,
           "base32_bad_ends": base_bad, "reachfull2_bad_ends": oracle_bad,
           "stub_endpoint_validation": validation}
    out_path = f"{HERE}/results/tier_sweep_bursty_n120_stub.json"
    with open(out_path, "w") as fh:
        json.dump(out, fh)
    print(f"\nwrote {out_path}")
    print("\nDONE")


if __name__ == "__main__":
    main()
