#!/usr/bin/env python3
"""Validity rerun: bursty v1.1 (struktured's SEPARATED sending stream only,
n=28 volleys, OK confidence) vs the pool-contaminated v1 (61 volleys, of
which 33 were the AI copro's own -- see STYLE_ENSEMBLE_V1.md pass 3 and
team-lead's contamination note). Reuses pressure_rig.run_arm()/compare()
directly with the v1.1 model object passed in, exactly as
refit_dr_lulu.py does for a new-capture model -- pressure_rig.py itself is
untouched.

v1.1 is rebuilt in-process from bursty_model.fit_struktured_20260804()'s
live raw_events (not loaded from a saved JSON -- BurstyPressureModel has no
loader, only to_json for archival) via fit_ensemble_source.fit_per_player(),
so this script is the single source of truth for "what v1.1 is," not a
copy that could drift from the style-ensemble fit.

Usage: run_bursty_v1_1_validity.py --seeds 120 --workers 6 --level 11
"""
from __future__ import annotations

import sys
import os
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bursty_model as BM
import fit_ensemble_source as FE
import pressure_rig as PR


def build_v1_1():
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    all_volleys, all_clears = [], []
    for mid, res in raw.items():
        all_volleys.extend(res["volleys"])
        all_clears.extend(res["clears"])
    opponent_of = dict(BM.DEFAULT_OPPONENT_OF)
    return FE.fit_per_player(all_volleys, all_clears, m_v1.n_matches, "P1", opponent_of)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=120)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--out", type=str, default="results/bursty_v1_1_n120")
    a = ap.parse_args()

    v1_1 = build_v1_1()
    s = v1_1.fit_summary()
    print(f"=== bursty v1.1: n_volleys={s['n_volleys']} n_clears={s['n_clears']} "
          f"volley_size_mean={s['volley_size_mean']:.3f} "
          f"gap_mean={s['inter_volley_gap_mean_s']:.2f} "
          f"p_within_k={s['p_volley_within_k_by_clear_size']} ===", flush=True)

    print(f"=== validity rerun: L{a.level}, n={a.seeds}, model=bursty-v1.1 (struktured-only), "
          f"arms=['0:20'] ===", flush=True)
    ctrl = PR.run_arm(a.level, a.seeds, a.workers, 0, 0, "bursty", v1_1)
    arm = PR.run_arm(a.level, a.seeds, a.workers, 0, 20, "bursty", v1_1)
    summary = PR.compare(ctrl, arm, "wt=0 ws=20 (bursty v1.1)")

    with open(f"{a.out}_wt0_ws20.json", "w") as fh:
        json.dump({"summary": summary,
                   "v1_1_fit_summary": s,
                   "ctrl": [ctrl[x] for x in sorted(ctrl)],
                   "arm": [arm[x] for x in sorted(arm)]}, fh)

    da0 = summary.get("dies_ahead0", 0)
    da1 = summary.get("dies_ahead1", 0)
    print(f"\nDONE. control bad-ends {summary['bad_ends0']}/{a.seeds} "
          f"({summary['bad_ends0']/a.seeds:.1%})  dies-ahead {da0}/{a.seeds} ({da0/a.seeds:.1%})")
    print(f"      ws=20 bad-ends {summary['bad_ends1']}/{a.seeds} "
          f"({summary['bad_ends1']/a.seeds:.1%})  dies-ahead {da1}/{a.seeds} ({da1/a.seeds:.1%})")
    print(f"      garbage/g {summary['garbage0']:.2f} -> {summary['garbage1']:.2f}")


if __name__ == "__main__":
    main()
