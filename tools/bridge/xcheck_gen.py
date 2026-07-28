#!/usr/bin/env python3
"""xcheck_gen.py — generate the cross-check corpus that gates coef-opt's numba decide()
before it's trusted in the cadence study.

For each of N diverse boards we record the DEPLOY-config depth-3 decision (col, orient4) from
the pure-python reference (nes_d3_golden.decide_d3 + RTL-exact leaf_r47), for BOTH arms
w_vrdy=24 (shipped cart) and w_vrdy=12 (r47b5 in flight). coef-opt runs their fast decide() on
the same inputs and must reproduce ref24/ref12 EXACTLY (same enumeration order + tie-breaks,
seed=0). Board encoding == leaf_r47 / tb_leafeval: 128 cells, $FF empty, virus hi-nibble $D,
color low nibble, row-major 8x16.

Output: xcheck_corpus.jsonl — one object per line:
  {"idx", "vir", "fill", "pA","pB","nA","nB", "board":[128], "ref24":[col,o4], "ref12":[col,o4]}

Run with the .venv python (has py65):
  /home/struktured/projects/dr-mario-mods/.venv/bin/python xcheck_gen.py --n 200
"""
import os, sys, json, random, argparse, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import planner_bridge as PB   # brings in nes_d3_golden as PB.G, leaf_r47 as PB.LR, D3.THIRD


def _rand_board(rng):
    """A plausible mid-game board: a stack of the bottom rows with viruses + some cover,
    varied virus count and fill so the corpus exercises burial/matched/setup/vrdy terms."""
    b = [0xFF] * 128
    nvir = rng.choice([8, 12, 20, 28, 36, 44, 56])
    # place viruses in the lower ~10 rows (rows 6..15), like real boards
    placed = 0
    guard = 0
    while placed < nvir and guard < 4000:
        guard += 1
        r = rng.randint(6, 15); c = rng.randint(0, 7); off = r * 8 + c
        if b[off] == 0xFF:
            b[off] = 0xD0 | rng.randint(0, 2); placed += 1
    # sprinkle non-virus color cover cells (pills already dropped), some on top of viruses
    ncover = rng.randint(0, 40)
    for _ in range(ncover):
        r = rng.randint(2, 15); c = rng.randint(0, 7); off = r * 8 + c
        if b[off] == 0xFF:
            b[off] = rng.randint(0, 2)     # non-virus colored cell
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=4747)
    ap.add_argument("--out", default=os.path.join(HERE, "xcheck_corpus.jsonl"))
    a = ap.parse_args()

    rng = random.Random(a.seed)
    PB.apply_deploy_config()

    t0 = time.time()
    n_ok = 0
    with open(a.out, "w") as f:
        for idx in range(a.n):
            board = _rand_board(rng)
            pA, pB = rng.randint(0, 2), rng.randint(0, 2)
            nA, nB = rng.randint(0, 2), rng.randint(0, 2)
            vir = sum(1 for x in board if (x & 0xF0) == 0xD0)
            fill = sum(1 for x in board if x != 0xFF)
            # arm 24
            PB.install_r47_leaf(24)
            r24 = PB.G.decide_d3(list(board), pA, pB, nA, nB,
                                 topk1=32, topk2=8, third=PB.D3.THIRD, seed=0)
            # arm 12
            PB.install_r47_leaf(12)
            r12 = PB.G.decide_d3(list(board), pA, pB, nA, nB,
                                 topk1=32, topk2=8, third=PB.D3.THIRD, seed=0)
            rec = dict(idx=idx, vir=vir, fill=fill, pA=pA, pB=pB, nA=nA, nB=nB,
                       board=board,
                       ref24=list(r24) if r24 else None,
                       ref12=list(r12) if r12 else None)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            n_ok += 1
            if (idx + 1) % 10 == 0:
                dt = time.time() - t0
                print(f"[xcheck] {idx+1}/{a.n}  ({dt:.0f}s, {dt/(idx+1):.2f}s/board)  "
                      f"last vir={vir} fill={fill} ref24={rec['ref24']} ref12={rec['ref12']}",
                      flush=True)
    dt = time.time() - t0
    same = 0
    with open(a.out) as f:
        recs = [json.loads(l) for l in f]
    for r in recs:
        if r["ref24"] == r["ref12"]:
            same += 1
    print(f"[xcheck] DONE {n_ok} boards in {dt:.0f}s -> {a.out}")
    print(f"[xcheck] arms agree on {same}/{n_ok} boards ({n_ok-same} where w_vrdy 24 vs 12 "
          f"changes the move -> those are the sensitive cases coef-opt's decode MUST match)")


if __name__ == "__main__":
    main()
