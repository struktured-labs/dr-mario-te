#!/usr/bin/env python3
"""vocab2 dataset invariant checks -- run after extract_windows.py --run.

Checks (fail loud, exit nonzero):
  1. chosen action's candidate value equals the nan-max of cand_vals row-wise
     (argmax consistency), and n_legal == count of non-NaN entries.
  2. t_to_end ranges: fatal windows in [0, K_LAST-1]; last decision (t=0)
     present exactly once per game.
  3. outcome/dies_ahead labels constant within a game and consistent with
     game_meta.json.
  4. cross-check vs census: for 25 random fatal decisions, the stored action
     equals the census trace entry at the same pill_idx (independent source:
     the Hetzner rows, not our replayer).
  5. covariate sanity: viruses == nonzero(board_vir); occ == nonzero(board_col);
     max_height consistent with board_col.
"""
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CENSUS = "/home/struktured/projects/dr-mario-qa-wt/experiments/hetzner/results/pressured_drip/census.jsonl"
K_LAST = 10

fails = []


def check(name, cond, detail=""):
    print(f"  [{'OK' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def load(name):
    return dict(np.load(os.path.join(HERE, name)))


def per_file(tag, d, expect_last_window):
    n = d["seed"].shape[0]
    vals = d["cand_vals"]
    legal = ~np.isnan(vals)
    check(f"{tag}: n_legal == non-NaN count",
          bool((legal.sum(axis=1) == d["n_legal"]).all()))
    act = d["action"].astype(int)
    chosen = vals[np.arange(n), act]
    mx = np.nanmax(vals, axis=1)
    check(f"{tag}: chosen value == row nanmax", bool(np.array_equal(chosen, mx)),
          f"n={n}")
    check(f"{tag}: chosen action always legal", bool(~np.isnan(chosen).all()
          and not np.isnan(chosen).any()))
    # covariates from boards
    bv = d["board_vir"].astype(bool).sum(axis=1)
    bc = d["board_col"].astype(bool).sum(axis=1)
    check(f"{tag}: viruses == nonzero(board_vir)", bool((bv == d["viruses"]).all()))
    check(f"{tag}: occ == nonzero(board_col)", bool((bc == d["occ"]).all()))
    b = d["board_col"].reshape(n, 16, 8).astype(bool).any(axis=2)
    top = np.where(b.any(axis=1), b.argmax(axis=1), 16)
    check(f"{tag}: max_height consistent", bool(((16 - top) == d["max_height"]).all()))
    if expect_last_window:
        check(f"{tag}: t_to_end within [0,{K_LAST - 1}]",
              bool(d["t_to_end"].min() >= 0 and d["t_to_end"].max() <= K_LAST - 1))
        seeds, counts = np.unique(d["seed"], return_counts=True)
        t0 = d["seed"][d["t_to_end"] == 0]
        check(f"{tag}: exactly one t_to_end==0 per game",
              bool(len(np.unique(t0)) == len(seeds) == len(t0)),
              f"{len(seeds)} games, window sizes min={counts.min()} max={counts.max()}")
    else:
        check(f"{tag}: t_to_end==0 once per game",
              bool((np.unique(d["seed"][d["t_to_end"] == 0]).shape[0]
                    == np.unique(d["seed"]).shape[0]
                    == (d["t_to_end"] == 0).sum())))
    # labels constant per game
    for lab in ("outcome", "dies_ahead"):
        m = {}
        bad = 0
        for s, v in zip(d["seed"].tolist(), d[lab].tolist()):
            if s in m and m[s] != v:
                bad += 1
            m[s] = v
        check(f"{tag}: {lab} constant within game", bad == 0)
    return n


def main():
    fatal = load("fatal_windows.npz")
    ctrl = load("controls.npz")
    meta = json.load(open(os.path.join(HERE, "dataset_meta.json")))
    gm = json.load(open(os.path.join(HERE, "game_meta.json")))

    nf = per_file("fatal", fatal, expect_last_window=True)
    nc = per_file("ctrl", ctrl, expect_last_window=False)
    check("ctrl outcomes all clear", bool((ctrl["outcome"] == 0).all()))
    check("fatal outcomes all topout/stall", bool(np.isin(fatal["outcome"], [1, 2]).all()))
    to_games = len(np.unique(fatal["seed"][fatal["outcome"] == 1]))
    st_games = len(np.unique(fatal["seed"][fatal["outcome"] == 2]))
    check("fatal game counts", to_games == meta["counts"]["topout_games"]
          and st_games == meta["counts"]["stall_games_sampled"],
          f"topout {to_games}, stall {st_games}")
    check("labels match game_meta", all(
        gm[str(s)]["result"] == {0: "clear", 1: "topout", 2: "stall"}[int(o)]
        for s, o in zip(fatal["seed"][:2000].tolist(), fatal["outcome"][:2000].tolist())))

    # independent cross-check vs the census traces
    need = set(np.unique(fatal["seed"]).tolist())
    traces = {}
    with open(CENSUS) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["seed"] in need and r.get("trace"):
                traces[r["seed"]] = {i: a for i, a in r["trace"]}
    rng = random.Random(99)
    idxs = rng.sample(range(nf), 25)
    ok = all(traces[int(fatal["seed"][i])][int(fatal["pill_idx"][i])]
             == int(fatal["action"][i]) for i in idxs)
    check("25 random fatal decisions match census trace actions", ok)

    print(f"\nfatal decisions {nf}, control decisions {nc}")
    print("VALIDATION " + ("PASS" if not fails else f"FAIL: {fails}"))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
