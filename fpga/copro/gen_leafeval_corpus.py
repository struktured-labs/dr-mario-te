#!/usr/bin/env python3
"""Reconstructed generator for the Verilator leaf corpus (tb_leafeval reads
leafeval_cases.txt). The original R47 generator was never committed -- this rebuilds
it on top of the RTL-verified `leaf_r47` mirror (100% cell-exact vs the RTL, see
leaf_r47.py). Scoring a board with leaf_r47 yields EXACTLY what the RTL would post,
so this is a faithful corpus generator; swap the variant to regenerate for a revert.

USAGE (writes to a chosen path -- NEVER clobbers the pinned corpus unless --inplace):
  python gen_leafeval_corpus.py [--variant r47|vrdy12|weekend_burial]
                                [--rand N] [--out PATH] [--inplace]

Typical revert-validation flow (candidate a, W_VRDY 24->12):
  1. python gen_leafeval_corpus.py --variant vrdy12 --out /tmp/wt/leafeval_cases.txt
  2. cp LeafEval.sv dpram.v tb_leafeval.cpp into /tmp/wt/ context, apply the RTL revert,
     verilator --cc --exe --build --top-module LeafEval LeafEval.sv dpram.v tb_leafeval.cpp -o Vsim
  3. run Vsim from the dir holding the generated leafeval_cases.txt -> expect N/N.
By default it reuses the exact boards embedded in the pinned corpus (directly comparable)
plus --rand fresh boards for coverage.
"""
import sys, os, random, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tests"))
import leaf_r47
from test_depth2 import _rand_board

VARIANTS = {
    "r47": leaf_r47.leaf_r47,
    "vrdy12": leaf_r47.leaf_vrdy12,
    "weekend_burial": leaf_r47.leaf_weekend_burial,
    "combined": leaf_r47.leaf_combined,
}


def _pinned_boards():
    p = os.path.join(HERE, "leafeval_cases.txt")
    if not os.path.exists(p):
        return []
    with open(p) as f:
        toks = f.read().split()
    n = int(toks[0]); toks = toks[1:]
    return [[int(x, 16) for x in toks[k * 130:k * 130 + 128]] for k in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, default="r47")
    ap.add_argument("--rand", type=int, default=0, help="extra random boards for coverage")
    ap.add_argument("--seed", type=int, default=20260726)
    ap.add_argument("--out", default=None, help="output path (default: leafeval_cases.<variant>.txt here)")
    ap.add_argument("--inplace", action="store_true",
                    help="DANGER: overwrite the pinned leafeval_cases.txt (only for a real reland)")
    args = ap.parse_args()

    score = VARIANTS[args.variant]
    rng = random.Random(args.seed)
    boards = _pinned_boards() + [_rand_board(rng) for _ in range(args.rand)]

    lines = []
    for b in boards:
        sco, win = score(b)
        lines.append("%s %d %d" % (" ".join("%02x" % (x & 0xFF) for x in b), sco, win))

    if args.inplace:
        out = os.path.join(HERE, "leafeval_cases.txt")
    else:
        out = args.out or os.path.join(HERE, "leafeval_cases.%s.txt" % args.variant)
    with open(out, "w") as f:
        f.write(("%d\n" % len(lines)) + "\n".join(lines) + "\n")
    print("wrote %s: %d boards, variant=%s" % (out, len(lines), args.variant))


if __name__ == "__main__":
    main()
