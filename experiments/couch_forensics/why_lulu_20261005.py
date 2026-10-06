"""2026-10-05 couch: WHY THE AI WON (dr. lulu vs ANTIBODY_DIST_FAIR), per game and across games.

Inputs (banked): summary_lulu_20261005.json (lulu_20261005.py analyze/merge: pace, sends, deaths, lane provenance),
cases_lulu_20261005_{lulu,ai}_pills.jsonl (both seats per pill: virus count at each spawn), ai_lulu_20261005.json
(AI fidelity labels, stalls).

Per game:
  race       each seat's remaining viruses at 30/60/90/120/180 s and who led; the time each seat first reached 24 / 12 / 6
  tempo      viruses/min by phase (0-60, 60-120, >=120 s) and pills/min, both seats
  stall      the AI's longest run at one virus count (s, pills, count) and her longest
  garbage    cells each seat received (/min), her garbage cells in the AI's sealing (stall), AI garbage in her lane at death
  margin     the loser's remaining viruses at the end and the time they would still have needed at their own pace over
             the game's last 60 s (her finishing deficit)
  errors     her top-outs: own-pill vs garbage cells in the spawn lane (lane provenance)
Across games: her wins vs her losses on each factor (game = unit; n = 3 vs 6, PROVISIONAL).
Usage: python why_lulu_20261005.py  -> why_lulu_20261005.json + printed tables
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def series(rows, g, t0):
    return [(r["t_spawn"] - t0, r["virus_count"]) for r in rows if r["game"] == g]


def at(ser, t, final):
    v = 48
    for tt, vc in ser:
        if tt <= t:
            v = vc
    return v


def first_le(ser, n, t_end, final):
    for tt, vc in ser:
        if vc <= n:
            return round(tt, 1)
    return round(t_end, 1) if final <= n else None


def longest_stall(ser, t_end):
    best = (0.0, None, 0, None)
    i = 0
    while i < len(ser):
        j = i
        while j + 1 < len(ser) and ser[j + 1][1] == ser[i][1]:
            j += 1
        dt = (ser[j + 1][0] if j + 1 < len(ser) else t_end) - ser[i][0]
        if dt > best[0]:
            best = (round(dt, 1), ser[i][1], j - i + 1, round(ser[i][0], 1))
        i = j + 1
    return {"seconds": best[0], "viruses": best[1], "pills": best[2], "from_s": best[3]}


def main():
    S = json.load(open(os.path.join(HERE, "summary_lulu_20261005.json")))
    L = [json.loads(l) for l in open(os.path.join(HERE, "cases_lulu_20261005_lulu_pills.jsonl"))]
    Aq = [json.loads(l) for l in open(os.path.join(HERE, "cases_lulu_20261005_ai_pills.jsonl"))]
    AI = {g["game"]: g for g in json.load(open(os.path.join(HERE, "ai_lulu_20261005.json")))["games"]} \
        if os.path.exists(os.path.join(HERE, "ai_lulu_20261005.json")) else {}
    out = []
    for G in S["games"]:
        g = G["game"]; t0 = G["t0"]; T = G["t_end"] - t0
        fl, fa = G["final_lulu_ai"]
        sl = [(r["t_rel"], r["virus_count"]) for r in L if r["game"] == g]
        sa = [(r["t_rel"], r["virus_count"]) for r in Aq if r["game"] == g]
        race = {}
        for t in (30, 60, 90, 120, 150, 180, 210, 240):
            if t <= T:
                a, b = at(sl, t, fl), at(sa, t, fa)
                race[str(t)] = [a, b]
        reach = {who: {str(n): first_le(s, n, T, f) for n in (24, 12, 6, 0)} for who, s, f in (("lulu", sl, fl), ("ai", sa, fa))}
        P = G["pace"]

        def rate_last60(s, f):
            a = at(s, T - 60, f) if T > 60 else 48
            return round((a - f) / min(60, T) * 60, 2)
        rl, ra = rate_last60(sl, fl), rate_last60(sa, fa)
        if G["winner"] == "AI":
            deficit = {"loser": "lulu", "viruses_left": fl, "her_rate_last60_per_min": rl,
                       "seconds_still_needed_at_that_rate": round(fl / rl * 60, 1) if rl > 0 else None}
        else:
            deficit = {"loser": "ai", "viruses_left": fa, "ai_rate_last60_per_min": ra,
                       "seconds_still_needed_at_that_rate": round(fa / ra * 60, 1) if ra > 0 else None}
        lane = G.get("lane_at_death")
        row = {"game": g, "winner": G["winner"], "how": G["how"], "final_lulu_ai": [fl, fa], "dur_s": G["dur_s"],
               "race_lulu_ai": race, "first_reached": reach,
               "lulu_vpm": {k: P["lulu"][k]["viruses_per_min"] for k in ("0-60s", "60-120s", ">=120s", "all") if k in P["lulu"]},
               "ai_vpm": {k: P["ai"][k]["viruses_per_min"] for k in ("0-60s", "60-120s", ">=120s", "all") if k in P["ai"]},
               "lulu_ppm": P["lulu"]["all"]["pills_per_min"], "ai_ppm": P["ai"]["all"]["pills_per_min"],
               "ai_longest_stall": longest_stall(sa, T), "lulu_longest_stall": longest_stall(sl, T),
               "garbage_cells_to_lulu": G["ai_sends"]["recv_by_lulu_cells"], "garbage_cells_to_ai": G["lulu_sends"]["recv_by_ai_cells"],
               "garbage_to_lulu_per_min": G["ai_sends"]["cells_per_min"], "garbage_to_ai_per_min": G["lulu_sends"]["cells_per_min"],
               "finishing_deficit": deficit, "lane_at_death": lane,
               "ai_silicon_eq_brain_pct": (lambda C: round(100 * sum(1 for q in C if q["category"] == "MATCH") / len(C), 1))(
                   [json.loads(l) for l in open(os.path.join(HERE, f"cases_ai_{g}_lulu_20261005.jsonl"))])}
        out.append(row)
    W = [r for r in out if r["winner"] == "lulu"]; Lo = [r for r in out if r["winner"] == "AI"]

    def cmp(name, f):
        a = [x for x in (f(r) for r in W) if x is not None]; b = [x for x in (f(r) for r in Lo) if x is not None]
        return {"her_wins": a, "her_losses": b, "mean_wins": round(st.mean(a), 2) if a else None,
                "mean_losses": round(st.mean(b), 2) if b else None}
    across = {
        "ai_longest_stall_s": cmp("stall", lambda r: r["ai_longest_stall"]["seconds"]),
        "lead_at_60s_ai_minus_lulu_viruses": cmp("60", lambda r: r["race_lulu_ai"]["60"][0] - r["race_lulu_ai"]["60"][1]),
        "lead_at_120s_ai_minus_lulu_viruses": cmp("120", lambda r: (r["race_lulu_ai"]["120"][0] - r["race_lulu_ai"]["120"][1]) if "120" in r["race_lulu_ai"] else None),
        "lulu_vpm_0_60": cmp("l60", lambda r: r["lulu_vpm"]["0-60s"]),
        "ai_vpm_0_60": cmp("a60", lambda r: r["ai_vpm"]["0-60s"]),
        "lulu_vpm_all": cmp("lall", lambda r: r["lulu_vpm"]["all"]),
        "ai_vpm_all": cmp("aall", lambda r: r["ai_vpm"]["all"]),
        "garbage_to_lulu_per_min": cmp("gl", lambda r: r["garbage_to_lulu_per_min"]),
        "garbage_to_ai_per_min": cmp("ga", lambda r: r["garbage_to_ai_per_min"]),
        "ai_silicon_eq_brain_pct": cmp("fid", lambda r: r["ai_silicon_eq_brain_pct"] or 0),
    }
    json.dump({"games": out, "her_wins_vs_losses": across}, open(os.path.join(HERE, "why_lulu_20261005.json"), "w"), indent=1)
    for r in out:
        print(json.dumps({k: r[k] for k in ("game", "winner", "how", "final_lulu_ai", "race_lulu_ai", "lulu_vpm", "ai_vpm",
                                            "ai_longest_stall", "garbage_to_lulu_per_min", "garbage_to_ai_per_min", "finishing_deficit",
                                            "ai_silicon_eq_brain_pct")}))
    print(json.dumps(across, indent=1))


if __name__ == "__main__":
    main()
