import sys, os, time
sys.path.insert(0, "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47")
import bursty_model as BM
import fit_ensemble_source as FE
import pressure_rig as PR

def build_v1_1():
    m_v1 = BM.fit_struktured_20260804()
    raw = m_v1.meta["raw_events"]
    all_volleys, all_clears = [], []
    for mid, res in raw.items():
        all_volleys.extend(res["volleys"]); all_clears.extend(res["clears"])
    opponent_of = dict(BM.DEFAULT_OPPONENT_OF)
    return FE.fit_per_player(all_volleys, all_clears, m_v1.n_matches, "P1", opponent_of)

v1_1 = build_v1_1()
t0 = time.time()
arm = PR.run_arm(11, 40, 4, 0, 20, "bursty", v1_1)
dt = time.time() - t0
print(f"n=40 workers=4 took {dt:.1f}s -> {dt/40:.2f}s/game")
