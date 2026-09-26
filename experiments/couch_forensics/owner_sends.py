"""The OWNER's garbage sends, as received by the AI (P2), across every recorded couch game.

Per consecutive pair of analysed placements (k, k+1) in a game:
  P = S_k + observed landing + faithful resolve()   (the AI's own clear size = cells resolve() removed)
  extras  = cells in S_{k+1} not in P               (garbage singles that survived)
  missing = cells of P gone/changed in S_{k+1}      (garbage completed a line and cleared)
  volley size = extras if missing == 0, else mech_check.explain()'s volley size (the smallest 1-4 single volley,
  repeated columns allowed, that reproduces S_{k+1}); None if unexplained.
Arrival time = t_spawn of k+1 (garbage drops after the AI's lock, before its next spawn). Time resolution is one
placement interval (~0.6-2 s), so two sends inside one interval merge into one volley (flagged if > 4 cells).

Also computes, for the SAME AI clears, what bursty_model.fit_struktured_20260804 would have fired (its gate-(b)
wiring links an owner volley to each AI clear with p_within_k[clear size]).

Usage: python owner_sends.py OUT.jsonl
"""
import json
import os
import sys
from collections import Counter

import numpy as np

import mech_check as MC

TMP = os.path.expanduser("~/projects/dr-mario-h16-wt/tmp/couch_forensics")
# session, level, game label, raw file, time window (None = whole file)
GAMES = [
    ("9/24", 11, "G1", "raw_n24_G1.jsonl", None), ("9/24", 11, "G2", "raw_n24_G2.jsonl", None),
    ("9/24", 11, "G3", "raw_n24_G3.jsonl", None),
    ("9/25", 11, "G1", "raw_m25_G1.jsonl", None), ("9/25", 11, "G2", "raw_m25_G2.jsonl", None),
    ("9/25", 11, "G3", "raw_m25_G3.jsonl", None), ("9/25", 11, "G4", "raw_m25_G4.jsonl", None),
    ("9/26 AM", 11, "G1", "raw_t26.jsonl", (8.9, 103.2)), ("9/26 AM", 11, "G2", "raw_t26.jsonl", (143.5, 276.5)),
    ("9/26 AM", 11, "G3", "raw_t26b.jsonl", (307.1, 564.0)), ("9/26 AM", 11, "G4*", "raw_t26b.jsonl", (599.7, 707.4)),
    ("9/26 PM", 10, "G1", "raw_t26m2.jsonl", (1180.8, 1397.7)), ("9/26 PM", 10, "G2", "raw_t26m2.jsonl", (1413.8, 1458.6)),
    ("9/26 PM", 10, "G3", "raw_t26m2.jsonl", (1481.0, 1726.3)),
]


def ai_clear(r):
    b = MC.A.board_from_strings(r["S"]["color"], r["S"]["virus"], r["S"]["link"])
    o, orow, ocol, ocl = r["landing"]
    if o == "H":
        b.color[orow, ocol], b.color[orow, ocol + 1] = ocl
        b.link[orow, ocol], b.link[orow, ocol + 1] = 4, 3
    else:
        b.color[orow, ocol], b.color[orow + 1, ocol] = ocl
        b.link[orow, ocol], b.link[orow + 1, ocol] = 2, 1
    tot, vir, chain = b.resolve()
    return int(tot), int(chain)


def main(out):
    fit = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cvx", "vendor",
                                      "bursty_owner_fit_20260804.json")))
    pk = {tuple(int(x) for x in k.split("-")): d["p"] for k, d in fit["p_within_k"].items()}

    def p_fire(cs):
        for (lo, hi), p in pk.items():
            if lo <= cs <= hi:
                return p
        return 0.0

    games = []
    for sess, lvl, g, rawf, win in GAMES:
        R = [json.loads(l) for l in open(os.path.join(TMP, rawf))]
        R = [r for r in R if r["landing"] is not None and 0 not in r["cur"] and 0 not in r["nxt"]
             and (win is None or win[0] <= r["t_spawn"] <= win[1])]
        vol = []
        model_expect = 0.0; ai_clears = Counter()
        for i in range(len(R) - 1):
            r, n = R[i], R[i + 1]
            cs, chain = ai_clear(r)
            if cs >= 4:
                ai_clears[cs] += 1
                model_expect += p_fire(cs)
            P = MC.after_pill(r)
            N = np.array([int(ch) for ch in n["S"]["color"]]).reshape(16, 8)
            extras = [(int(a), int(c)) for a, c in np.argwhere((N > 0) & (P.color == 0))]
            missing = int(((P.color > 0) & (N != P.color)).sum())
            if not extras and not missing:
                continue
            if missing == 0:
                size, how = len(extras), "direct"
            else:
                s = MC.explain(r, n)
                size, how = (s, "explained") if s not in (None, 0) else (None, "unexplained")
            if size is None:
                vol.append({"t": n["t_spawn"], "size": None, "how": how, "cols": sorted({c for _, c in extras})})
                continue
            vol.append({"t": n["t_spawn"], "size": size, "how": how, "cols": sorted({c for _, c in extras}),
                        "n_cols": len({c for _, c in extras}), "ai_clear_before": cs})
        dur = R[-1]["t_spawn"] - R[0]["t_spawn"]
        games.append({"session": sess, "level": lvl, "game": g, "dur_s": round(dur, 1), "n_placements": len(R),
                      "volleys": vol, "ai_clears_ge4": sum(ai_clears.values()),
                      "model_expected_volleys": round(model_expect, 2), "t_first": R[0]["t_spawn"]})
    with open(out, "w") as fh:
        for g in games:
            fh.write(json.dumps(g) + "\n")
    print(f"{len(games)} games -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
