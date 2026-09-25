"""Mechanics cross-check WITH opponent garbage (the reader/tracker gate for multi-game runs).

Per placement: P = S_k + observed landing, faithful resolve(). The ROM then drops the opponent's garbage
volley (singles, distinct columns, onto the column tops) and resolves again, which can complete lines
and clear cells the pill alone did not. A step is EXPLAINED if some volley of 0-4 singles (any distinct
columns x any colours) turns P into exactly S_{k+1} (colour grid). Unexplained steps are reader/tracking
errors (or a mechanic outside this model) and are reported per game.

Usage: python mech_check.py RAW.jsonl  ->  prints per-step verdicts summary; --json for machine output
"""
import itertools
import json
import sys

import numpy as np

import analyze_g2 as A

ROWS, COLS = 16, 8


def after_pill(r):
    b = A.board_from_strings(r["S"]["color"], r["S"]["virus"], r["S"]["link"])
    o, orow, ocol, ocl = r["landing"]
    if o == "H":
        b.color[orow, ocol], b.color[orow, ocol + 1] = ocl
        b.link[orow, ocol], b.link[orow, ocol + 1] = 4, 3
        b.is_virus[orow, ocol] = b.is_virus[orow, ocol + 1] = False
    else:
        b.color[orow, ocol], b.color[orow + 1, ocol] = ocl
        b.link[orow, ocol], b.link[orow + 1, ocol] = 2, 1
        b.is_virus[orow, ocol] = b.is_virus[orow + 1, ocol] = False
    b.resolve()
    return b


def drop(b, cols_colours):
    g = b.clone()
    for c, col in cols_colours:
        top = next((r for r in range(ROWS) if g.color[r, c] > 0), ROWS)
        if top == 0:
            return None
        g.color[top - 1, c] = col; g.link[top - 1, c] = 0; g.is_virus[top - 1, c] = False
    g.resolve()
    return g


def explain(r, nxt):
    P = after_pill(r)
    N = np.array([int(ch) for ch in nxt["S"]["color"]]).reshape(ROWS, COLS)
    if np.array_equal(P.color, N):
        return 0
    added = int((N > 0).sum()) - int((P.color > 0).sum())
    for s in range(1, 5):
        for cols in itertools.combinations(range(COLS), s):
            for colours in itertools.product((1, 2, 3), repeat=s):
                g = drop(P, list(zip(cols, colours)))
                if g is not None and np.array_equal(g.color, N):
                    return s
    # a volley can put two singles in one column (seen: 4 cells over 3 columns); cells that SURVIVE are
    # read directly, so only the colours of garbage that got cleared are free -> search multisets
    for s in range(2, 5):
        for cols in itertools.combinations_with_replacement(range(COLS), s):
            if len(set(cols)) == s:
                continue
            for colours in itertools.product((1, 2, 3), repeat=s):
                g = drop(P, list(zip(cols, colours)))
                if g is not None and np.array_equal(g.color, N):
                    return s
    return None


def diff_shape(r, nxt):
    P = after_pill(r)
    N = np.array([int(ch) for ch in nxt["S"]["color"]]).reshape(ROWS, COLS)
    miss = [(int(a), int(c), int(P.color[a, c]), int(N[a, c])) for a, c in np.argwhere((P.color > 0) & (N != P.color))]
    extra = [(int(a), int(c), int(N[a, c])) for a, c in np.argwhere((N > 0) & (P.color == 0))]
    return miss, extra


def run(raw_path):
    R = [json.loads(l) for l in open(raw_path)]
    R = [r for r in R if r["landing"] is not None and 0 not in r["cur"] and 0 not in r["nxt"]]
    out = []
    for i, r in enumerate(R[:-2]):            # the last placement(s) of a game have no settled successor
        v = explain(r, R[i + 1])
        out.append((r["k"], v))
        if v is None and "--why" in sys.argv:
            print("  k", r["k"], r["t_spawn"], "landing", r["landing"], "miss/extra", diff_shape(r, R[i + 1]))
    return out


if __name__ == "__main__":
    res = run(sys.argv[1])
    ok0 = sum(1 for _, v in res if v == 0)
    okg = sum(1 for _, v in res if v not in (None, 0))
    bad = [k for k, v in res if v is None]
    print(json.dumps({"file": sys.argv[1], "steps": len(res), "exact": ok0, "garbage_explained": okg,
                      "unexplained": len(bad), "unexplained_k": bad}))
