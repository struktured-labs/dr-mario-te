"""Healthy vs dying TAP-build couch games (2026-09-26): what separates them?

Per game, from analyze_tap.py output (settled board at each spawn) + track.py raw (for garbage):
  match      silicon == masked brain (tap mask P=2)
  lane       spawn-lane height = max(h3, h4); max, seconds with lane > 10 (time-weighted by inter-spawn time)
  hivir      viruses in cols 3-5 at rows <= 8 ("above row 9"): max count, virus-seconds, seconds with >= 1
  garbage    garbage-like new cells after each placement (S_{k+1} cells not explained by the pill + resolve),
             and the number of steps that received any
  proph      placements where DRPROPH's trigger condition held (first occupied row of c3/c4 <= 2)
  init       first analysed board: viruses total, in cols 3-5 at rows <= 8, top virus row of c3/c4/c5
Usage: python contrast_tap.py OUT.jsonl  (inputs are listed in GAMES below; paths under $TMPDIR)
"""
import json
import os
import sys

import numpy as np

import mech_check as MC

TMP = os.environ.get("TMPDIR_CF", os.path.expanduser("~/projects/dr-mario-h16-wt/tmp/couch_forensics"))
GAMES = [  # label, tap analysis, raw, game index in that analysis, outcome
    ("AM-G1", "tap_t26.jsonl", "raw_t26.jsonl", 1, "AI TAP-OUT (16 vs 32)"),
    ("AM-G2", "tap_t26.jsonl", "raw_t26.jsonl", 2, "AI TAP-OUT (7 vs 29)"),
    ("AM-G3", "tap_t26b.jsonl", "raw_t26b.jsonl", 1, "AI clear (owner 20)"),
    ("PM-G1", "tap_t26m2.jsonl", "raw_t26m2.jsonl", 1, "AI clear (owner 4)"),
    ("PM-G2", "tap_t26m2.jsonl", "raw_t26m2.jsonl", 2, "owner top-out (38 vs 24)"),
    ("PM-G3", "tap_t26m2.jsonl", "raw_t26m2.jsonl", 3, "AI clear (owner 10)"),
]


def grid(s):
    return np.array([int(ch) for ch in s]).reshape(16, 8)


def main(out):
    rows = []
    for label, tapf, rawf, g, outcome in GAMES:
        T = [json.loads(l) for l in open(os.path.join(TMP, tapf))]
        T = [t for t in T if t["game"] == g]
        raw = {json.loads(l)["k"]: json.loads(l) for l in open(os.path.join(TMP, rawf))}
        ts = [t["t_spawn"] for t in T]
        dts = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)] + [0.0]
        lane = [max(t["heights"][3], t["heights"][4]) for t in T]
        hv = []
        for t in T:
            V = grid(t["S"]["virus"])
            hv.append(int(V[:9, 3:6].sum()))
        # garbage: next analysed placement's settled board vs this pill + resolve
        gcells = gsteps = 0
        for i in range(len(T) - 1):
            r, n = raw[T[i]["k"]], raw[T[i + 1]["k"]]
            P = MC.after_pill(r)
            N = grid(n["S"]["color"])
            ex = int(((N > 0) & (P.color == 0)).sum())
            gcells += ex; gsteps += int(ex > 0)
        V0, C0 = grid(T[0]["S"]["virus"]), grid(T[0]["S"]["color"])
        top = [next((rr for rr in range(16) if V0[rr, c]), 16) for c in (3, 4, 5)]
        dur = ts[-1] - ts[0]
        rec = {"game": label, "outcome": outcome, "n": len(T), "dur_s": round(dur, 1),
               "match_masked": sum(t["match_masked"] for t in T),
               "lane_max": max(lane), "lane_gt10_s": round(sum(d for l, d in zip(lane, dts) if l > 10), 1),
               "lane_gt10_frac": round(sum(d for l, d in zip(lane, dts) if l > 10) / max(dur, 1e-9), 3),
               "hivir_max": max(hv), "hivir_virus_s": round(sum(h * d for h, d in zip(hv, dts)), 1),
               "hivir_any_s": round(sum(d for h, d in zip(hv, dts) if h > 0), 1),
               "garbage_cells": gcells, "garbage_steps": gsteps,
               "garbage_per_min": round(gcells / max(dur / 60, 1e-9), 2),
               "proph": sum(t["proph"] in ("L", "R") for t in T),
               "init_viruses": int(V0.sum()), "init_hivir_c345": int(V0[:9, 3:6].sum()),
               "init_top_virus_row_c3c4c5": top,
               "lane_series": [(round(t["t_spawn"] - ts[0], 1), l, h) for t, l, h in zip(T, lane, hv)]}
        rows.append(rec)
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    hdr = ("game", "outcome", "n", "dur_s", "match", "lane_max", "lane>10 s (frac)", "hivir max", "hivir vir·s",
           "hivir any s", "garbage cells (steps, /min)", "PROPH", "init vir", "init hivir c3-5", "init top row c3/4/5")
    print(" | ".join(hdr))
    for r in rows:
        print(" | ".join(str(x) for x in (r["game"], r["outcome"], r["n"], r["dur_s"],
              f"{r['match_masked']}/{r['n']} ({100*r['match_masked']/r['n']:.0f}%)", r["lane_max"],
              f"{r['lane_gt10_s']} ({r['lane_gt10_frac']:.2f})", r["hivir_max"], r["hivir_virus_s"], r["hivir_any_s"],
              f"{r['garbage_cells']} ({r['garbage_steps']}, {r['garbage_per_min']})", r["proph"], r["init_viruses"],
              r["init_hivir_c345"], r["init_top_virus_row_c3c4c5"])))


if __name__ == "__main__":
    main(sys.argv[1])
