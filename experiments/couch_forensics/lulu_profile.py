"""dr. lulu profile from the 2026-09-27 clean-HDMI recording (she is P1; ANTIBODY is P2).

  clear pace   from the HUD P1 counter (hud_digits.py templates): viruses/min per game, time per game
  sends        her volleys as received by the AI (owner_sends.py method on raw_lulu_G*.jsonl): volleys/min, size mix,
               inter-volley gaps, bursts, cells/min, and phase (time into game; HER remaining viruses from the HUD)
  output       lulu_fit_202609.json in the owner_fit_202609.json format
Usage: python lulu_profile.py OUT_CASES.jsonl OUT_FIT.json
"""
import bisect
import json
import os
import statistics as st
import sys
from collections import Counter

import numpy as np

import hud_digits as H
import mech_check as MC
from owner_sends import ai_clear

TMP = os.path.expanduser("~/projects/dr-mario-h16-wt/tmp/couch_forensics")
GAMES = [("G1", "raw_lulu_G1.jsonl", (0.0, 494.1), "ANTIBODY won (lulu topped out at 2, AI at 1)"),
         ("G2", "raw_lulu_G2.jsonl", (504.8, 793.4), "lulu won (cleared first; AI at 5)")]
TBINS = [(0, 30, "open <30s"), (30, 90, "mid 30-90s"), (90, 1e9, "late >=90s")]
OBINS = [(31, 99, ">30"), (21, 30, "21-30"), (9, 20, "9-20"), (0, 8, "<=8")]


def hud_series():
    tpl = {int(k): v for k, v in json.load(open(os.path.join(TMP, "hud_templates.json"))).items()}
    pts = []
    for l in open(os.path.join(TMP, "hud_lulu.jsonl")):
        s = json.loads(l)
        a = [H.read_digit(s[k], tpl)[0] for k in ("p1t", "p1o", "p2t", "p2o")]
        if None not in a:
            pts.append((s["t"], 10 * a[0] + a[1], 10 * a[2] + a[3]))
    return pts


def main(out_cases, out_fit):
    pts = hud_series(); ts = [p[0] for p in pts]
    games = []
    for g, rawf, (t0, t1), outcome in GAMES:
        R = [json.loads(l) for l in open(os.path.join(TMP, rawf))]
        R = [r for r in R if r["landing"] is not None and 0 not in r["cur"] and 0 not in r["nxt"] and t0 <= r["t_spawn"] <= t1]
        vol = []
        for i in range(len(R) - 1):
            r, n = R[i], R[i + 1]
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
            vol.append({"t": n["t_spawn"], "size": size, "how": how, "cols": sorted({c for _, c in extras})})
        span = [p for p in pts if t0 <= p[0] <= t1]
        # the first HUD samples can still show the previous screen: take her max count in the first 10 s of play
        lulu0 = max(p[1] for p in span if R[0]["t_spawn"] + 1 <= p[0] <= R[0]["t_spawn"] + 10); lulu1 = span[-1][1]
        dur = R[-1]["t_spawn"] - R[0]["t_spawn"]
        games.append({"game": g, "outcome": outcome, "t_first": R[0]["t_spawn"], "dur_s": round(dur, 1),
                      "lulu_start": lulu0, "lulu_end": lulu1, "ai_end": span[-1][2],
                      "lulu_viruses_per_min": round((lulu0 - lulu1) / (dur / 60), 2), "volleys": vol,
                      "hud_series": [(round(p[0] - R[0]["t_spawn"], 1), p[1], p[2]) for p in span[::4]]})
    with open(out_cases, "w") as fh:
        for g in games:
            fh.write(json.dumps(g) + "\n")
    # pooled send stats
    V = [v for g in games for v in g["volleys"] if v["size"]]
    dur = sum(g["dur_s"] for g in games)
    sizes = Counter(v["size"] for v in V)
    gaps = []
    for g in games:
        tt = [v["t"] for v in g["volleys"] if v["size"]]
        gaps += [round(b - a, 2) for a, b in zip(tt, tt[1:])]
    gs = sorted(gaps); q = lambda p: gs[int(p * (len(gs) - 1))] if gs else None
    n4 = [v for v in V if v["size"] <= 4]
    pmf = {str(k): round(sum(1 for v in n4 if v["size"] == k) / len(n4), 3) for k in (2, 3, 4)} if n4 else {}
    # phase
    acc = {ax: {} for ax in ("time", "lulu")}
    def bump(ax, key, f, x):
        d = acc[ax].setdefault(key, {"time_s": 0.0, "volleys": 0, "cells": 0}); d[f] += x
    for g in games:
        t0 = g["t_first"]; t1 = t0 + g["dur_s"]
        for p in pts:
            if t0 <= p[0] <= t1:
                bump("time", next(n for a, b, n in TBINS if a <= p[0] - t0 < b), "time_s", 0.5)
                bump("lulu", next(n for a, b, n in OBINS if a <= p[1] <= b), "time_s", 0.5)
        for v in g["volleys"]:
            if not v["size"]:
                continue
            i = min(max(bisect.bisect_left(ts, v["t"] - 1.5), 0), len(ts) - 1)
            for ax, key in (("time", next(n for a, b, n in TBINS if a <= v["t"] - t0 < b)),
                            ("lulu", next(n for a, b, n in OBINS if a <= pts[i][1] <= b))):
                bump(ax, key, "volleys", 1); bump(ax, key, "cells", v["size"])
    phase = {ax: {k: {"minutes": round(d["time_s"] / 60, 2), "volleys": d["volleys"],
                      "volleys_per_min": round(d["volleys"] / max(d["time_s"] / 60, 1e-9), 2),
                      "mean_size": round(d["cells"] / max(d["volleys"], 1), 2),
                      "cells_per_min": round(d["cells"] / max(d["time_s"] / 60, 1e-9), 2)} for k, d in A.items()}
             for ax, A in acc.items()}
    fit = {"name": "lulu_fit_202609",
           "source": "RESULT_COUCH_LULU.md; dr. lulu (P1) sends as RECEIVED by ANTIBODY (P2), clean-HDMI 2026-09-27, L11, 2 games",
           "population": {"games": 2, "minutes": round(dur / 60, 1), "note": "n=2 games: PROVISIONAL (<10 games)"},
           "model": "independent renewal process of volleys (same form as owner_fit_202609)",
           "clear_pace_viruses_per_min": {g["game"]: g["lulu_viruses_per_min"] for g in games},
           "rate_volleys_per_min": round(len(V) / (dur / 60), 2),
           "cells_per_min": round(sum(v["size"] for v in V) / (dur / 60), 2),
           "size_hist": {str(k): c for k, c in sorted(sizes.items())},
           "size_pmf": pmf, "p_merged_double": round(sum(1 for v in V if v["size"] > 4) / max(len(V), 1), 3),
           "inter_volley_gap_s": {"quantiles": {"p10": q(.1), "p25": q(.25), "p50": q(.5), "p75": q(.75), "p90": q(.9)},
                                  "mean": round(st.mean(gs), 2) if gs else None,
                                  "cv": round(st.pstdev(gs) / st.mean(gs), 2) if len(gs) > 1 else None,
                                  "p_gap_le_3s": round(sum(1 for x in gs if x <= 3) / max(len(gs), 1), 3), "samples": gaps},
           "unexplained_volleys": sum(1 for g in games for v in g["volleys"] if not v["size"]),
           "unexplained_with_new_cells": sum(1 for g in games for v in g["volleys"] if not v["size"] and v["cols"]),
           "rate_upper_bound_volleys_per_min": round((len(V) + sum(1 for g in games for v in g["volleys"] if not v["size"] and v["cols"])) / (dur / 60), 2),
           "phase": phase}
    json.dump(fit, open(out_fit, "w"), indent=1)
    print(json.dumps({k: fit[k] for k in ("clear_pace_viruses_per_min", "rate_volleys_per_min", "cells_per_min",
                                          "size_hist", "size_pmf", "p_merged_double", "unexplained_volleys",
                                          "unexplained_with_new_cells", "rate_upper_bound_volleys_per_min")}))
    print("gaps", fit["inter_volley_gap_s"]["quantiles"], "cv", fit["inter_volley_gap_s"]["cv"], "p<=3s", fit["inter_volley_gap_s"]["p_gap_le_3s"])
    for ax in phase:
        print(ax, phase[ax])
    for g in games:
        print(g["game"], g["outcome"], "dur", g["dur_s"], "lulu", g["lulu_start"], "->", g["lulu_end"], "pace", g["lulu_viruses_per_min"],
              "/min | volleys", sum(1 for v in g["volleys"] if v["size"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
