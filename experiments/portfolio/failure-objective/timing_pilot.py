#!/usr/bin/env python3
"""Timing pilot: how long does one bursty-v1.1 arm of n seeds take at
workers=4 (portfolio cap)? Used to size the real sweep budget."""
from __future__ import annotations
import sys, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL47 = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
for _p in (EVAL47,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

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


if __name__ == "__main__":
    v1_1 = build_v1_1()
    t0 = time.time()
    arm = PR.run_arm(11, 12, 4, 0, 20, "bursty", v1_1)
    dt = time.time() - t0
    print(f"n=12 workers=4 wt=0 ws=20 took {dt:.1f}s -> {dt/12:.2f}s/seed-equivalent (parallel)")
