"""Gate (b) with DEATH BOARDS: same play as gate_b.play (identity-checked vs existing gateb rows), plus per game:
final column heights, spawn-lane (cols 3,4) height history, and the STALL = placements since the last virus
cleared before the end. Question (couch 2026-09-25): does DRCHAIN 540 die with spawn-lane towers / long
virus stalls more than 180?"""
import sys, os, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import gate_b as G, vs_race as V
import bursty_model as BM

def heights(board):
    occ = board.color != 0
    return [int(16 - np.argmax(occ[:, c])) if occ[:, c].any() else 0 for c in range(8)]

def play(seed, arm, model):
    choose = V._decider(arm)
    hist = {"spawn": [], "vir": []}
    orig_step = None
    from drmario.faithful_env import FaithfulDrMarioEnv
    # wrap env.step to sample the board after every placement, without changing play
    real_step = FaithfulDrMarioEnv.step
    def step(self, a):
        out = real_step(self, a)
        h = heights(self.board); hist["spawn"].append(max(h[3], h[4])); hist["vir"].append(int(self.board.virus_count()))
        hist["last_h"] = h
        return out
    FaithfulDrMarioEnv.step = step
    try:
        r = G.play(seed, None, model, choose=choose)
    finally:
        FaithfulDrMarioEnv.step = real_step
    v = hist["vir"]; stall = 0
    for i in range(len(v) - 1, 0, -1):
        if v[i] < v[i - 1]: break
        stall += 1
    sp = hist["spawn"]
    r.update({"arm": arm, "final_h": hist.get("last_h"), "stall": stall,
              "spawn_ge12_frac": round(sum(1 for x in sp if x >= 12) / max(1, len(sp)), 3),
              "spawn_last20_max": max(sp[-20:]) if sp else 0})
    return r

if __name__ == "__main__":
    arm, lo, cnt, step, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    m = BM.fit_struktured_20260804()
    with open(out, "w") as fh:
        for i in range(cnt):
            fh.write(json.dumps(play(lo + i * step, arm, m)) + "\n"); fh.flush()
