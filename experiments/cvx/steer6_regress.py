"""STEER6 phase 3 REGRESSION CASES: replay the two couch stuck-virus boards through each candidate decider.

  lulu G1  (cases_lulu_20260927.jsonl, '9/27 lulu G1'): yellow VIRUS at (8,2) sealed under `r b y b r b r y`; 4
           viruses left from k86; silicon unlocked it at k184 (the lulu-G1 200-s stall).
  M1-G3    (cases_hsv_20260927.jsonl, '9/27 HSV G3'): yellow VIRUS at (8,3) walled in by a short landing (k9),
           owner garbage (k41, k56) and a tuck (k63); 0/88 candidates could clear it; 43 -> 14 viruses meanwhile.

Rollout from a couch board at pill k0 with the TRUE pill sequence (the NES sequence does not depend on placements)
and the opponent's REPLAYED garbage: after pill k, the cells that landed on the couch (S_{k+1} minus the actual
placement + resolve) are dropped into the same columns with the same colours. Straight execution (the decider's
intent, no steering). Reports pills until the target virus is gone, D(target) along the way, viruses cleared,
top-out. Deterministic. D in the trace = kdig 3, cap 40 (graded even when walled in).

  python steer6_regress.py [ARM ...]      # default: every ARM below
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import numpy as np
from drmario.faithful_game import FaithfulBoard, Pill, ORIENT_H, ORIENT_V

CF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "couch_forensics")
CASES = {
    "luluG1": dict(file="cases_lulu_20260927.jsonl", label="9/27 lulu G1", target=(8, 2), starts=(80, 120)),
    "m1G3": dict(file="cases_hsv_20260927.jsonl", label="9/27 HSV G3", target=(8, 3), starts=(9, 41, 63)),
}


def board_from_S(S):
    b = FaithfulBoard(16, 8)
    b.color = np.array([int(ch) for ch in S["color"]], np.int8).reshape(16, 8)
    b.is_virus = np.array([ch == "1" for ch in S["virus"]], bool).reshape(16, 8)
    b.link = np.array([int(ch) for ch in S["link"]], np.int8).reshape(16, 8)
    return b


def after_actual(r):
    b = board_from_S(r["S"])
    o, ocol, ocl, orow = r["actual"]
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


def load_case(name):
    c = CASES[name]
    R = {r["k_game"]: r for r in map(json.loads, open(os.path.join(CF, c["file"]))) if r["game_label"] == c["label"]}
    ks = sorted(R); kmax = ks[-1]
    seq = {}
    for k in range(ks[0], kmax + 2):
        if k in R:
            seq[k] = tuple(R[k]["cur"])
        elif k - 1 in R:
            seq[k] = tuple(R[k - 1]["nxt"])
        else:
            seq[k] = (1, 2)
    garb = {}
    for k in ks:
        if k + 1 in R and R[k]["actual"] is not None:
            P = after_actual(R[k]); N = np.array([int(ch) for ch in R[k + 1]["S"]["color"]]).reshape(16, 8)
            cells = [(int(cc), int(N[rr, cc])) for rr, cc in np.argwhere((N > 0) & (P.color == 0))]
            if cells:
                garb[k] = cells
    return c, R, seq, garb, kmax


def drop(b, cells):
    for c, colour in cells:
        top = next((r for r in range(16) if b.color[r, c] > 0), 16)
        if top == 0:
            continue
        b.color[top - 1, c] = colour; b.link[top - 1, c] = 0; b.is_virus[top - 1, c] = False
    b._apply_gravity(); b.resolve()


def decode(a, cur):
    var, col = a // 8, a % 8
    pa, pb = cur
    return {0: (ORIENT_H, col, Pill(pa, pb)), 1: (ORIENT_H, col, Pill(pb, pa)),
            2: (ORIENT_V, col, Pill(pa, pb)), 3: (ORIENT_V, col, Pill(pb, pa))}[var]


def dist_of(board, target):
    import cascade_leaf6_x as L6
    from cascade_link_x import board_flat
    col, vir = board_flat(board)
    out = np.empty(128, dtype=np.int64)
    L6._root_dists(col, vir, 40, out, 3)
    return int(out[target[0] * 8 + target[1]])


def rollout(dec, name, k0, garbage=True, maxp=160):
    c, R, seq, garb, kmax = load_case(name)
    b = board_from_S(R[k0]["S"]); tr = c["target"]
    v0 = int(b.is_virus.sum()); trace = []
    for k in range(k0, min(kmax, k0 + maxp) + 1):
        if not b.is_virus[tr]:
            return dict(case=name, k0=k0, cleared_at=k, pills=k - k0, v0=v0, v=int(b.is_virus.sum()), how="target_cleared", trace=trace)
        trace.append(dist_of(b, tr))
        cur, nxt = seq[k], seq[k + 1]
        a = dec.choose(b, Pill(*cur), Pill(*nxt), k)
        if a is None:
            return dict(case=name, k0=k0, cleared_at=None, pills=k - k0, v0=v0, v=int(b.is_virus.sum()), how="nomove", trace=trace)
        o, col, p = decode(a, cur)
        if not b.place_pill(p, o, col):
            return dict(case=name, k0=k0, cleared_at=None, pills=k - k0, v0=v0, v=int(b.is_virus.sum()), how="illegal", trace=trace)
        b.resolve()
        if b.is_virus.sum() == 0:
            return dict(case=name, k0=k0, cleared_at=k, pills=k - k0 + 1, v0=v0, v=0, how="board_clear", trace=trace)
        if garbage and k in garb:
            drop(b, garb[k])
        if b.spawn_blocked():
            return dict(case=name, k0=k0, cleared_at=None, pills=k - k0 + 1, v0=v0, v=int(b.is_virus.sum()), how="topout", trace=trace)
    return dict(case=name, k0=k0, cleared_at=None, pills=min(kmax, k0 + maxp) - k0 + 1, v0=v0, v=int(b.is_virus.sum()),
                how="end_of_data", trace=trace)


ARMS = {
    "base": dict(mode="off"),
    "dist_end20": dict(mode="dist_end", W=20), "dist_end60": dict(mode="dist_end", W=60), "dist_end180": dict(mode="dist_end", W=180),
    "dist_end60k3": dict(mode="dist_end", W=60, kdig=3, cap=24),
    "rowsup_end60": dict(mode="rowsup_end", W=60), "rowsup_end180": dict(mode="rowsup_end", W=180),
    "dist_stall60": dict(mode="dist_stall", W=60), "dist_stall180": dict(mode="dist_stall", W=180),
    "dist_stall60k3": dict(mode="dist_stall", W=60, kdig=3, cap=24),
    "dist_target60": dict(mode="dist_target", W=60), "dist_target180": dict(mode="dist_target", W=180),
    "dist_target60k3": dict(mode="dist_target", W=60, kdig=3, cap=24),
    "dist_hsv60": dict(mode="dist_hsv", W=60), "dist_hsv180": dict(mode="dist_hsv", W=180),
    "dist_hsv60k3": dict(mode="dist_hsv", W=60, kdig=3, cap=24),
}


def make_dec(arm):
    import fast_rtl_x as FX
    import cascade_leaf6_x as L6
    w, fl = FX.variant("winner")
    return L6.Leaf6Decider(w, fl, topk2=8, maxpass=0, w_chain=540, ws=20, tap=2, **ARMS[arm])


if __name__ == "__main__":
    import cascade_chain_x as C
    C.warmup_chain(topk2=8)
    arms = sys.argv[1:] or list(ARMS)
    out = open(os.environ.get("S6R_OUT", "steer6/regress.jsonl"), "a")
    for arm in arms:
        for name, c in CASES.items():
            for k0 in c["starts"]:
                for g in (True, False):
                    dec = make_dec(arm)
                    r = rollout(dec, name, k0, garbage=g)
                    r.update(arm=arm, garbage=g, active=dec.active, decisions=dec.decisions)
                    tr = r.pop("trace")
                    r["d_trace"] = tr[::5]
                    print(f"{arm:15s} {name:6s} k0={k0:3d} garb={int(g)}  {r['how']:14s} pills={r['pills']:3d}  v {r['v0']}->{r['v']}  "
                          f"active {r['active']}/{r['decisions']}  D {tr[:1]}..{tr[-3:]}", flush=True)
                    out.write(json.dumps(r) + "\n"); out.flush()
