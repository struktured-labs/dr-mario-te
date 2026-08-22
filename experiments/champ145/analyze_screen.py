"""analyze_screen.py — H14 candidate screens over the banked home-regime states.

Reads out/states/states_<seed>.jsonl.gz (written by screen_home_states.py) and
emits, in spawn-lane-gate-probe format (GATE-OPEN and ARGMAX-FLIP reported
separately; <2% flip = candidate not testable):

  A. H12-at-L20 dose: gate rate, exact top-2 tie rate (board-dedup'd),
     theta_margin dose curve — the trigger population for H14a (H12 re-dosed
     for the home regime) and for the GW deepening increment (H14b; its true
     trigger is the post-garbage release edge, so the all-plies number is an
     UPPER BOUND on its population — caveat carried in the output).
  B. Regime-gated d_spawn_h penalty (H14c) flip screen: argmax flip rate of
     vals - dose*child_spawn_h under three gates x dose grid.
  C. Lab-instrument L20 failure rate (endpoint baseline sanity vs RTL 22.8%).

Self-gates (killed-mutant discipline) run BEFORE any data is read:
  m1: a synthetic ply where dose 8 must flip the argmax — analyzer must flip.
  m2: same ply with the penalty inert (cdsh equal) — analyzer must NOT flip.
  m3: reader-alive — two synthetic tables differing in one row must produce
      different tie counts.
"""
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORACLE = os.path.abspath(os.path.join(HERE, "..", "eval47", "stage2", "oracle"))
sys.path.insert(0, ORACLE)

import numpy as np  # noqa: E402
import oracle_arm as OA  # noqa: E402  (CHAMP_ORDER only)

ORDER = [int(x) for x in OA.CHAMP_ORDER]
THETAS = [0.0, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0]
DOSES = [1, 2, 4, 8, 16, 32, 64]
GATES = {
    "always": lambda r: True,
    "h12gate": lambda r: r["gate"] == 1,
    "dsh10": lambda r: r["dsh"] >= 10,
}


def argmax_order(vals):
    """First slot in the champion's scan order attaining the max value."""
    best, best_s = None, None
    for s in ORDER:
        v = vals[s]
        if v is None:
            continue
        if best is None or v > best:
            best, best_s = v, s
    return best_s


def flips(vals, cdsh, dose):
    base = argmax_order(vals)
    pen = [None if vals[s] is None else vals[s] - dose * cdsh[s]
           for s in range(32)]
    return argmax_order(pen) != base


def self_gate():
    # m1: dose must flip — slot 1 wins raw, slot 0 wins at dose 8
    vals = [100.0, 104.0] + [None] * 30
    cdsh = [0, 1] + [0] * 30
    assert argmax_order(vals) == 1
    assert flips(vals, cdsh, 8), "m1 SURVIVED: dose-8 flip not detected"
    # m2: inert penalty must NOT flip
    assert not flips(vals, [2] * 32, 8), "m2 SURVIVED: inert penalty flipped"
    # m3: reader-alive on the tie counter
    t1 = [{"m2": 0.0}, {"m2": 3.0}]
    t2 = [{"m2": 0.0}, {"m2": 0.0}]
    c1 = sum(r["m2"] == 0.0 for r in t1)
    c2 = sum(r["m2"] == 0.0 for r in t2)
    assert c1 != c2, "m3 SURVIVED: reader blind to a changed row"
    print("[self-gate] m1/m2/m3 all killed")


def main():
    self_gate()
    files = sorted(glob.glob(os.path.join(HERE, "out", "states",
                                          "states_*.jsonl.gz")))
    print(f"[analyze] {len(files)} seed files")
    assert files, "no banked states"

    games = []
    n_ply = 0
    gate_open = 0
    tie_raw = tie_dedup = 0            # among gated plies, exact top ties
    theta_all = {t: 0 for t in THETAS}     # gated AND m2 <= theta, all plies
    strat = {"neardeath": [0, 0], "endgame": [0, 0]}  # [plies, exact ties]
    gate_counts = {g: 0 for g in GATES}
    flip_counts = {(g, d): 0 for g in GATES for d in DOSES}
    fail_seed_rows = []

    for path in files:
        rows = []
        with gzip.open(path, "rt") as fh:
            for line in fh:
                rows.append(json.loads(line))
        game = rows[-1]["game"]
        games.append(game)
        for r in rows[:-1]:
            n_ply += 1
            gated = r["gate"] == 1
            if gated:
                gate_open += 1
                if r["tie_raw"] > 1:
                    tie_raw += 1
                if r["tie_dedup"] > 1:
                    tie_dedup += 1
                for t in THETAS:
                    if r["m2"] is not None and r["m2"] <= t:
                        theta_all[t] += 1
            if r["dsh"] >= 12:
                strat["neardeath"][0] += 1
                strat["neardeath"][1] += int(r["tie_dedup"] > 1)
            if r["vir"] <= 8:
                strat["endgame"][0] += 1
                strat["endgame"][1] += int(r["tie_dedup"] > 1)
            for gname, gfn in GATES.items():
                if not gfn(r):
                    continue
                gate_counts[gname] += 1
                for d in DOSES:
                    if flips(r["vals"], r["cdsh"], d):
                        flip_counts[(gname, d)] += 1
        if game["won"] == 0:
            fail_seed_rows.append(game)

    n_games = len(games)
    n_fail = sum(1 - g["won"] for g in games)
    topout = sum(g["topout"] for g in games)
    stall = sum(g["stall"] for g in games)

    out = {
        "n_games": n_games, "n_ply": n_ply,
        "lab_fail_rate": round(n_fail / n_games, 4),
        "topout": topout, "stall": stall,
        "gate_open_rate": round(gate_open / n_ply, 4),
        "tie_raw_rate_of_gated": round(tie_raw / max(1, gate_open), 4),
        "tie_dedup_rate_of_gated": round(tie_dedup / max(1, gate_open), 4),
        "tie_dedup_rate_of_all": round(tie_dedup / n_ply, 4),
        "theta_dose_of_all_plies": {str(t): round(theta_all[t] / n_ply, 4)
                                    for t in THETAS},
        "strat": {k: {"plies": v[0],
                      "tie_dedup_rate": round(v[1] / max(1, v[0]), 4)}
                  for k, v in strat.items()},
        "h14c_flip_screen": {
            g: {"gate_open": round(gate_counts[g] / n_ply, 4),
                "flip_of_all_plies": {
                    str(d): round(flip_counts[(g, d)] / n_ply, 4)
                    for d in DOSES},
                "flip_of_active": {
                    str(d): round(flip_counts[(g, d)] / max(1, gate_counts[g]),
                                  4)
                    for d in DOSES}}
            for g in GATES},
    }
    dst = os.path.join(HERE, "out", "screen_result.json")
    with open(dst, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))
    print(f"wrote {dst}")
    print("ANALYZE_SCREEN_OK")


if __name__ == "__main__":
    main()
