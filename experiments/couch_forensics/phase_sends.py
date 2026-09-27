"""Phase dependence of the OWNER's sends (owner_sends.py volleys) using the HUD counters (hud_digits.py).

Phase axes:
  time into the game (s since the game's first analysed spawn): opening < 30, mid 30-90, late >= 90
  the OWNER's remaining viruses (HUD P1), read 1.5 s BEFORE the volley's arrival (pre-combo board)
  the AI's remaining viruses (HUD P2), as a check (the owner says sends are not targeted at the AI's board)
Rate per phase = volleys / minutes the game spent in that phase (2-fps HUD samples, 0.5 s each).
Usage: python phase_sends.py OUT.json
"""
import bisect
import json
import os
import sys
from collections import defaultdict

import hud_digits as H

TMP = os.path.expanduser("~/projects/dr-mario-h16-wt/tmp/couch_forensics")
HUD = {"9/24": "hud_n24.jsonl", "9/25": "hud_m25.jsonl", "9/26 AM": "hud_t26a.jsonl", "9/26 PM": "hud_t26m2.jsonl"}
TBINS = [(0, 30, "open <30s"), (30, 90, "mid 30-90s"), (90, 1e9, "late >=90s")]
OBINS = [(31, 99, ">30"), (21, 30, "21-30"), (9, 20, "9-20"), (0, 8, "<=8")]


def bin_of(v, bins):
    for lo, hi, name in bins:
        if lo <= v < hi:
            return name
    return None


def obin(v):
    for lo, hi, name in OBINS:
        if lo <= v <= hi:
            return name
    return None


def main(out):
    tpl = {int(k): v for k, v in json.load(open(os.path.join(TMP, "hud_templates.json"))).items()}
    series = {}
    for sess, f in HUD.items():
        pts = []
        for l in open(os.path.join(TMP, f)):
            s = json.loads(l)
            a = [H.read_digit(s[k], tpl)[0] for k in ("p1t", "p1o", "p2t", "p2o")]
            if None in a:
                continue
            pts.append((s["t"], 10 * a[0] + a[1], 10 * a[2] + a[3]))
        series[sess] = pts
    G = [json.loads(l) for l in open("owner_sends_cases.jsonl")]
    raw_windows = {}
    acc = {ax: defaultdict(lambda: {"time_s": 0.0, "volleys": 0, "cells": 0}) for ax in ("time", "owner", "ai")}
    acc_l11 = {ax: defaultdict(lambda: {"time_s": 0.0, "volleys": 0, "cells": 0}) for ax in ("time", "owner", "ai")}
    for g in G:
        V = [v for v in g["volleys"] if v["size"]]
        # game span from its volleys' file window: use first/last placement time recorded in owner_sends (dur_s)
        pts = series[g["session"]]
        ts = [p[0] for p in pts]
        # game window = [t_first, t_first + dur]; t_first recovered from the earliest volley minus slack is
        # unreliable, so owner_sends stores it: fall back to the HUD run containing the volleys
        t_first = g.get("t_first")
        if t_first is None:
            t_first = min(v["t"] for v in g["volleys"]) if g["volleys"] else None
        t0, t1 = g["t_first"], g["t_first"] + g["dur_s"]
        span = [p for p in pts if t0 <= p[0] <= t1]
        for tgt in ((acc,) if g["level"] != 11 else (acc, acc_l11)):
            for p in span:
                tgt["time"][bin_of(p[0] - t0, TBINS)]["time_s"] += 0.5
                tgt["owner"][obin(p[1])]["time_s"] += 0.5
                tgt["ai"][obin(p[2])]["time_s"] += 0.5
            for v in V:
                i = bisect.bisect_left(ts, v["t"] - 1.5)
                i = min(max(i, 0), len(ts) - 1)
                _, own, ai = pts[i]
                for ax, key in (("time", bin_of(v["t"] - t0, TBINS)), ("owner", obin(own)), ("ai", obin(ai))):
                    tgt[ax][key]["volleys"] += 1; tgt[ax][key]["cells"] += v["size"]
    res = {}
    for name, A in (("all", acc), ("L11", acc_l11)):
        res[name] = {}
        for ax, d in A.items():
            res[name][ax] = {k: {"minutes": round(x["time_s"] / 60, 2), "volleys": x["volleys"], "cells": x["cells"],
                                 "volleys_per_min": round(x["volleys"] / max(x["time_s"] / 60, 1e-9), 2),
                                 "mean_size": round(x["cells"] / max(x["volleys"], 1), 2),
                                 "cells_per_min": round(x["cells"] / max(x["time_s"] / 60, 1e-9), 2)}
                             for k, x in d.items() if k is not None}
    json.dump(res, open(out, "w"), indent=1)
    for name in res:
        for ax in ("time", "owner", "ai"):
            print(f"[{name}] by {ax}:")
            order = [b[2] for b in TBINS] if ax == "time" else [b[2] for b in OBINS]
            for k in order:
                x = res[name][ax].get(k)
                if x:
                    print(f"   {k:11s} {x['minutes']:5.1f} min  volleys {x['volleys']:3d} = {x['volleys_per_min']:4.2f}/min  "
                          f"mean size {x['mean_size']:.2f}  cells {x['cells_per_min']:5.2f}/min")


if __name__ == "__main__":
    main(sys.argv[1])
