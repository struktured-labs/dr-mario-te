"""Refit of the opponent SEND models with the hidden-spawn tracker (2026-10-03).

The old fits (owner_fit_202609.json via owner_sends.py, lulu_fit_202609.json via lulu_profile.py) used track.py,
which misses a spawn whose next capsule has the same colours; the merged second pill then appears as "extras" in
S_{k+1} and owner_sends counted it as a 2-cell VOLLEY. Here every source is re-tracked from its BANKED per-frame reads
(no video decode) with track_hidden_dist60_20261003.py, and the identical volley extraction (owner_sends.main's loop,
copied verbatim into volleys()) is re-run.

Steps
  retrack   frames -> rawh_<src>.jsonl (+ old-tracker identity check: track.py today == the banked raw)
  fit       volleys from OLD raw and NEW rawh for every game; old must reproduce the banked fit's counts;
            writes refit_sends_202610_cases.jsonl, owner_fit_202610.json, lulu_fit_202610.json
Diagnostic: an "extras" set that is exactly one LINKED 2-cell capsule (halves pointing at each other) is a pill, not
garbage (ROM garbage is unlinked singles); counted as residual_linked_pairs (expect ~0 with the new tracker).

Usage: python refit_sends_202610.py retrack|fit OUTDIR
"""
from __future__ import annotations

import json
import os
import statistics as st
import subprocess
import sys
from collections import Counter

import numpy as np

import mech_check as MC

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.expanduser("~/projects/dr-mario-h16-wt/tmp/couch_forensics")
O3 = os.path.expanduser("~/projects/dr_mario_rl/tmp/dist60_20261003")
PY = sys.executable

# src name -> (frames file, banked old raw file or None)
SOURCES = {
    "n24_G1": (f"{TMP}/frames_n24_G1.jsonl", f"{TMP}/raw_n24_G1.jsonl"),
    "n24_G2": (f"{TMP}/frames_n24_G2.jsonl", f"{TMP}/raw_n24_G2.jsonl"),
    "n24_G3": (f"{TMP}/frames_n24_G3.jsonl", f"{TMP}/raw_n24_G3.jsonl"),
    "m25_G1": (f"{TMP}/frames_m25_G1.jsonl", f"{TMP}/raw_m25_G1.jsonl"),
    "m25_G2": (f"{TMP}/frames_m25_G2.jsonl", f"{TMP}/raw_m25_G2.jsonl"),
    "m25_G3": (f"{TMP}/frames_m25_G3.jsonl", f"{TMP}/raw_m25_G3.jsonl"),
    "m25_G4": (f"{TMP}/frames_m25_G4.jsonl", f"{TMP}/raw_m25_G4.jsonl"),
    "t26": (f"{TMP}/frames_t26_0_280.jsonl", f"{TMP}/raw_t26.jsonl"),
    "t26b": (f"{TMP}/frames_t26_300_710.jsonl", f"{TMP}/raw_t26b.jsonl"),
    "t26m2": (f"{TMP}/frames_t26m2.jsonl", f"{TMP}/raw_t26m2.jsonl"),
    "lulu_G1": (f"{TMP}/frames_lulu_G1.jsonl", f"{TMP}/raw_lulu_G1.jsonl"),
    "lulu_G2": (f"{TMP}/frames_lulu_G2.jsonl", f"{TMP}/raw_lulu_G2.jsonl"),
    # 9/27 owner matches (HSV build): not in owner_fit_202609; used for the sensitivity block only
    "t27_G1": (f"{TMP}/frames_t27_G1.jsonl", f"{TMP}/raw_t27_G1.jsonl"),
    "t27_G2": (f"{TMP}/frames_t27_G2.jsonl", f"{TMP}/raw_t27_G2.jsonl"),
    "t27_G3": (f"{TMP}/frames_t27_G3.jsonl", f"{TMP}/raw_t27_G3.jsonl"),
    "t27m2_G1": (f"{TMP}/frames_t27m2_G1.jsonl", f"{TMP}/raw_t27m2_G1.jsonl"),
    "t27m2_G2": (f"{TMP}/frames_t27m2_G2.jsonl", f"{TMP}/raw_t27m2_G2.jsonl"),
    "t27m2_G3": (f"{TMP}/frames_t27m2_G3.jsonl", f"{TMP}/raw_t27m2_G3.jsonl"),
    # 10/03 match 1 (ANTIBODY_DIST), scanned with geom_dist60_20261003.json
    "o03_G1": (f"{O3}/frames_G1.jsonl", None),
    "o03_G2": (f"{O3}/frames_G2.jsonl", None),
    "o03_G3": (f"{O3}/frames_G3.jsonl", None),
    "o03_G4a": (f"{O3}/frames_G4a.jsonl", None),
    "o03_G4b": (f"{O3}/frames_G4b.jsonl", None),
}

# opponent, population, session, level, game, [(src, window)], note.  window None = whole file.
# Owner windows are owner_sends.GAMES verbatim; lulu windows are lulu_profile.GAMES verbatim.
GAMES = [
    ("owner", "base", "9/24", 11, "G1", [("n24_G1", None)]), ("owner", "base", "9/24", 11, "G2", [("n24_G2", None)]),
    ("owner", "base", "9/24", 11, "G3", [("n24_G3", None)]),
    ("owner", "base", "9/25", 11, "G1", [("m25_G1", None)]), ("owner", "base", "9/25", 11, "G2", [("m25_G2", None)]),
    ("owner", "base", "9/25", 11, "G3", [("m25_G3", None)]), ("owner", "base", "9/25", 11, "G4", [("m25_G4", None)]),
    ("owner", "base", "9/26 AM", 11, "G1", [("t26", (8.9, 103.2))]), ("owner", "base", "9/26 AM", 11, "G2", [("t26", (143.5, 276.5))]),
    ("owner", "base", "9/26 AM", 11, "G3", [("t26b", (307.1, 564.0))]), ("owner", "base", "9/26 AM", 11, "G4*", [("t26b", (599.7, 707.4))]),
    ("owner", "base", "9/26 PM", 10, "G1", [("t26m2", (1180.8, 1397.7))]), ("owner", "base", "9/26 PM", 10, "G2", [("t26m2", (1413.8, 1458.6))]),
    ("owner", "base", "9/26 PM", 10, "G3", [("t26m2", (1481.0, 1726.3))]),
    ("owner", "new", "10/03", 11, "G1", [("o03_G1", None)]), ("owner", "new", "10/03", 11, "G2", [("o03_G2", None)]),
    ("owner", "new", "10/03", 11, "G3", [("o03_G3", None)]), ("owner", "new", "10/03", 11, "G4", [("o03_G4a", None), ("o03_G4b", None)]),
    ("owner", "sens", "9/27", 11, "M1G1", [("t27_G1", None)]), ("owner", "sens", "9/27", 11, "M1G2", [("t27_G2", None)]),
    ("owner", "sens", "9/27", 11, "M1G3", [("t27_G3", None)]),
    ("owner", "sens", "9/27", 11, "M2G1", [("t27m2_G1", None)]), ("owner", "sens", "9/27", 11, "M2G2", [("t27m2_G2", None)]),
    ("owner", "sens", "9/27", 11, "M2G3", [("t27m2_G3", None)]),
    ("lulu", "base", "9/27 lulu", 11, "G1", [("lulu_G1", (0.0, 494.1))]),
    ("lulu", "base", "9/27 lulu", 11, "G2", [("lulu_G2", (504.8, 793.4))]),
]
DT_CAP = 15.0     # an inter-spawn interval longer than this is a pause (STUDY screen), not board time


def retrack(outdir):
    os.makedirs(outdir, exist_ok=True)
    for src, (frames, old) in SOURCES.items():
        if not os.path.exists(frames):
            print(f"{src}: frames missing ({frames}) -- skipped"); continue
        new = os.path.join(outdir, f"rawh_{src}.jsonl")
        subprocess.run([PY, os.path.join(HERE, "track_hidden_dist60_20261003.py"), frames, new], check=True)
        if old:
            chk = os.path.join(outdir, f"rawold_{src}.jsonl")
            subprocess.run([PY, os.path.join(HERE, "track.py"), frames, chk], check=True, capture_output=True)
            A = [json.loads(l) for l in open(chk)]; B = [json.loads(l) for l in open(old)]
            same = len(A) == len(B) and all(a["S"]["color"] == b["S"]["color"] and a["landing"] == b["landing"]
                                            for a, b in zip(A, B))
            print(f"   {src}: old tracker today == banked raw: {same} ({len(A)} vs {len(B)} records)")


def load_game(spec, outdir, which):
    """Concatenate a game's segments (G4: study pause junction). which = 'old' (banked raw) | 'new' (rawh)."""
    R = []
    for src, win in spec:
        p = SOURCES[src][1] if which == "old" else os.path.join(outdir, f"rawh_{src}.jsonl")
        if p is None:
            return None
        rr = [json.loads(l) for l in open(p)]
        rr = [r for r in rr if r["landing"] is not None and 0 not in r["cur"] and 0 not in r["nxt"]
              and (win is None or win[0] <= r["t_spawn"] <= win[1])]
        R += rr
    return R


def linked_pair(N, extras, L):
    if len(extras) != 2:
        return False
    (a, b), (c, d) = sorted(extras)
    la, lc = int(L[a, b]), int(L[c, d])
    return (a == c and d == b + 1 and la == 4 and lc == 3) or (b == d and c == a + 1 and la == 2 and lc == 1)


def volleys(R):
    """owner_sends.main's per-pair extraction, verbatim, + the linked-pair diagnostic + board-time duration."""
    vol = []; dur = 0.0
    for i in range(len(R) - 1):
        r, n = R[i], R[i + 1]
        dur += min(n["t_spawn"] - r["t_spawn"], DT_CAP)          # board time: a > 15 s interval is a STUDY pause
        P = MC.after_pill(r)
        N = np.array([int(ch) for ch in n["S"]["color"]]).reshape(16, 8)
        L = np.array([int(ch) for ch in n["S"]["link"]]).reshape(16, 8)
        extras = [(int(a), int(c)) for a, c in np.argwhere((N > 0) & (P.color == 0))]
        missing = int(((P.color > 0) & (N != P.color)).sum())
        if not extras and not missing:
            continue
        if missing == 0:
            size, how = len(extras), "direct"
        else:
            s = MC.explain(r, n)
            size, how = (s, "explained") if s not in (None, 0) else (None, "unexplained")
        vol.append({"t": n["t_spawn"], "tb": round(dur, 2), "size": size, "how": how, "cols": sorted({c for _, c in extras}),
                    "n_cols": len({c for _, c in extras}), "linked_pair": linked_pair(N, extras, L),
                    "same_col_pair": len(extras) == 2 and extras[0][1] == extras[1][1]})
    return vol, dur


def rom_rule(V):
    """ROM attack columns (rom_attack_rule.py): size 2 -> {s, s+4}; 3 -> {s, s+2, s+4}; 4 -> {s, s+2, s+4, s+6}.
    Checkable = fully visible ('direct') volleys with one cell per column."""
    ok = bad = 0
    for v in V:
        s, cols = v["size"], v["cols"]
        if v["how"] != "direct" or len(cols) != s or s not in (2, 3, 4):
            continue
        good = ((s == 2 and cols[1] - cols[0] == 4) or (s == 3 and cols == [cols[0], cols[0] + 2, cols[0] + 4])
                or (s == 4 and cols == [cols[0], cols[0] + 2, cols[0] + 4, cols[0] + 6]))
        ok += int(good); bad += int(not good)
    return {"conform": ok, "violate": bad}


def stats(games):
    V = [v for g in games for v in g["volleys"] if v["size"]]
    mins = sum(g["dur_s"] for g in games) / 60
    sizes = Counter(v["size"] for v in V)
    n4 = [v for v in V if v["size"] <= 4]
    pmf = {str(k): round(sum(1 for v in n4 if v["size"] == k) / max(len(n4), 1), 3) for k in (1, 2, 3, 4)}
    gaps = []
    for g in games:
        tt = [v["tb"] for v in g["volleys"] if v["size"]]            # board time (pauses capped)
        gaps += [round(b - a, 2) for a, b in zip(tt, tt[1:])]
    gs = sorted(gaps); q = lambda p: gs[int(p * (len(gs) - 1))] if gs else None
    rng = np.random.default_rng(0)
    per = [(sum(1 for v in g["volleys"] if v["size"]), g["dur_s"] / 60) for g in games]
    bs = []
    for _ in range(4000):
        idx = rng.integers(0, len(per), len(per))
        bs.append(sum(per[i][0] for i in idx) / max(sum(per[i][1] for i in idx), 1e-9))
    two = [v for v in V if v["size"] == 2 and v["how"] == "direct"]
    return {"games": len(games), "minutes": round(mins, 2), "volleys": len(V),
            "rate_volleys_per_min": round(len(V) / mins, 2),
            "rate_ci95_game_bootstrap": [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)],
            "cells_per_min": round(sum(v["size"] for v in V) / mins, 2),
            "mean_size": round(sum(v["size"] for v in V) / max(len(V), 1), 2),
            "size_hist": {str(k): c for k, c in sorted(sizes.items())}, "size_pmf_le4": pmf,
            "p_merged_double": round(sum(1 for v in V if v["size"] > 4) / max(len(V), 1), 3),
            "two_cell_same_col_share": round(sum(1 for v in two if v["same_col_pair"]) / max(len(two), 1), 3),
            "residual_linked_pairs": sum(1 for v in V if v["linked_pair"]),
            "unexplained": sum(1 for g in games for v in g["volleys"] if not v["size"]),
            "unexplained_with_new_cells": sum(1 for g in games for v in g["volleys"] if not v["size"] and v["cols"]),
            "rom_column_rule": rom_rule(V),
            "per_session_rate": {sess: round(sum(1 for g in games if g["session"] == sess for v in g["volleys"] if v["size"])
                                             / (sum(g["dur_s"] for g in games if g["session"] == sess) / 60), 2)
                                 for sess in sorted({g["session"] for g in games})},
            "gap_s": {"p10": q(.1), "p25": q(.25), "p50": q(.5), "p75": q(.75), "p90": q(.9),
                      "mean": round(st.mean(gs), 2) if gs else None,
                      "cv": round(st.pstdev(gs) / st.mean(gs), 2) if len(gs) > 1 else None,
                      "p_le_3s": round(sum(1 for x in gs if x <= 3) / max(len(gs), 1), 3)},
            "gap_samples": gaps}


def fit(outdir):
    rows = []
    for opp, pop, sess, lvl, g, spec in GAMES:
        for which in ("old", "new"):
            R = load_game(spec, outdir, which)
            if R is None or len(R) < 2:
                continue
            vol, dur = volleys(R)
            rows.append({"opp": opp, "pop": pop, "session": sess, "level": lvl, "game": g, "tracker": which,
                         "n_placements": len(R), "dur_s": round(dur, 1), "volleys": vol,
                         "hidden_spawns": sum(1 for r in R if r.get("spawn_kind") == "hidden")})
    with open(os.path.join(HERE, "refit_sends_202610_cases.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    sel = lambda opp, pops, lvl, which: [r for r in rows if r["opp"] == opp and r["pop"] in pops and r["level"] == lvl
                                         and r["tracker"] == which]
    table = {}
    for lab, opp, pops, lvl in (("owner L11 9/24-26 (owner_fit_202609 population)", "owner", ("base",), 11),
                                ("owner L10 9/26 PM", "owner", ("base",), 10),
                                ("owner L11 10/03 match 1", "owner", ("new",), 11),
                                ("owner L11 9/27 (HSV days, sensitivity)", "owner", ("sens",), 11),
                                ("owner L11 9/24-26 + 10/03 (owner_fit_202610)", "owner", ("base", "new"), 11),
                                ("owner L11 all (9/24-27 + 10/03, sensitivity)", "owner", ("base", "new", "sens"), 11),
                                ("dr. lulu L11 9/27 (lulu_fit_202610)", "lulu", ("base",), 11)):
        table[lab] = {w: stats(sel(opp, pops, lvl, w)) for w in ("old", "new") if sel(opp, pops, lvl, w)}
    for lab, d in table.items():
        print(f"\n== {lab}")
        for w, s in d.items():
            print(f"  {w}: games {s['games']} min {s['minutes']} volleys {s['volleys']} rate {s['rate_volleys_per_min']} "
                  f"{s['rate_ci95_game_bootstrap']} cells/min {s['cells_per_min']} mean {s['mean_size']} pmf {s['size_pmf_le4']} "
                  f"hist {s['size_hist']} doubles {s['p_merged_double']} 2-same-col {s['two_cell_same_col_share']} "
                  f"linked-pairs {s['residual_linked_pairs']} unexpl {s['unexplained']} gap p50 {s['gap_s']['p50']} cv {s['gap_s']['cv']}")
    json.dump({k: {w: {kk: vv for kk, vv in s.items() if kk != "gap_samples"} for w, s in d.items()} for k, d in table.items()},
              open(os.path.join(HERE, "refit_sends_202610_table.json"), "w"), indent=1)
    return table


if __name__ == "__main__":
    mode, outdir = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    if mode == "write":
        pass
    elif mode == "retrack":
        retrack(outdir)
    else:
        fit(outdir)


def write_fits():
    """owner_fit_202610.json / lulu_fit_202610.json from refit_sends_202610_cases.jsonl (NEW tracker), in the
    202609 snapshots' key layout (opp_owner202609.py / opp_lulu202609.py read: inter_volley_gap_s.samples[_L11],
    size_pmf, p_double_in_one_placement_interval / p_merged_double)."""
    rows = [json.loads(l) for l in open(os.path.join(HERE, "refit_sends_202610_cases.jsonl"))]
    sel = lambda opp, pops, lvl, w: [r for r in rows if r["opp"] == opp and r["pop"] in pops and r["level"] == lvl and r["tracker"] == w]
    o_new = stats(sel("owner", ("base", "new"), 11, "new")); o_l10 = stats(sel("owner", ("base",), 10, "new"))
    o_old = stats(sel("owner", ("base",), 11, "old")); o_all = stats(sel("owner", ("base", "new", "sens"), 11, "new"))
    o_same = stats(sel("owner", ("base",), 11, "new"))
    old09 = json.load(open(os.path.join(HERE, "owner_fit_202609.json")))
    pmf = {k: v for k, v in o_new["size_pmf_le4"].items() if k in ("2", "3", "4")}
    owner = {
        "name": "owner_fit_202610",
        "supersedes": "owner_fit_202609 (kept unchanged): its volleys included missed same-colour spawns (a 2nd pill read as a 2-cell volley)",
        "source": "refit_sends_202610.py on the banked per-frame reads, hidden-spawn tracker (track_hidden_dist60_20261003.py); "
                  "owner sends as RECEIVED by the AI (P2): 9/24-26 (owner_fit_202609's games) + 10/03 match 1",
        "population": {"L11_games": o_new["games"], "L11_minutes": o_new["minutes"], "L10_games": o_l10["games"],
                       "note": "10/03 match 1 owner self-reported groggy, cat on lap (rate 1.91/min, lowest session)"},
        "model": "NOT linked to the AI's clears or board; independent renewal process of volleys (as 202609)",
        "rate_volleys_per_min": {"L11": o_new["rate_volleys_per_min"], "L11_ci95_game_bootstrap": o_new["rate_ci95_game_bootstrap"],
                                 "L10": o_l10["rate_volleys_per_min"], "per_session": o_new["per_session_rate"]},
        "cells_per_min": {"L11": o_new["cells_per_min"], "L10": o_l10["cells_per_min"]},
        "size_pmf": {**pmf, "note": "L11, sizes <= 4; with the fixed tracker 4-cell sends are rare (most old '4s' were two merged hidden pills)"},
        "size_hist_L11": o_new["size_hist"],
        "p_double_in_one_placement_interval": o_new["p_merged_double"],
        "inter_volley_gap_s": {"quantiles": {k: o_new["gap_s"][k] for k in ("p10", "p25", "p50", "p75", "p90")},
                               "mean": o_new["gap_s"]["mean"], "cv": o_new["gap_s"]["cv"], "p_gap_le_3s": o_new["gap_s"]["p_le_3s"],
                               "samples_L11": o_new["gap_samples"],
                               "note": "board time (inter-spawn intervals > 15 s = STUDY pauses are capped, as the durations)"},
        "columns": {"rom_column_rule_checkable_volleys": o_new["rom_column_rule"],
                    "2_cells": "always 2 columns 4 apart ({0,4},{1,5},{2,6},{3,7}: rom_attack_rule.py); the 202609 '23% same column' were vertical pills",
                    "note": "every checkable volley conforms to the ROM attack-column rule with the new tracker (0 violations); the old extraction had "
                            f"{o_old['rom_column_rule']['violate']} violations of {o_old['rom_column_rule']['violate'] + o_old['rom_column_rule']['conform']}"},
        "phase": {"note": "NOT recomputed; the 202609 phase table counted hidden pills as volleys. Treat the rate as flat."},
        "sensitivity": {"L11_all_incl_9_27_HSV_days": {k: o_all[k] for k in ("games", "minutes", "rate_volleys_per_min",
                                                                              "rate_ci95_game_bootstrap", "cells_per_min", "size_pmf_le4")},
                        "L11_same_games_as_202609": {k: o_same[k] for k in ("games", "minutes", "rate_volleys_per_min",
                                                                             "rate_ci95_game_bootstrap", "cells_per_min", "size_pmf_le4")}},
        "compare": {"owner_fit_202609": {"rate_L11": old09["rate_volleys_per_min"]["L11"], "cells_per_min_L11": old09["cells_per_min"]["L11"],
                                         "size_pmf": {k: old09["size_pmf"][k] for k in ("2", "3", "4")}},
                    "old_method_reproduced_on_same_games": {"rate": o_old["rate_volleys_per_min"], "cells_per_min": o_old["cells_per_min"]},
                    "vs_race_model": old09["compare"]["vs_race_model"]},
    }
    json.dump(owner, open(os.path.join(HERE, "owner_fit_202610.json"), "w"), indent=1)
    l_new = stats(sel("lulu", ("base",), 11, "new")); l_old = stats(sel("lulu", ("base",), 11, "old"))
    old_l = json.load(open(os.path.join(HERE, "lulu_fit_202609.json")))
    LR = sel("lulu", ("base",), 11, "new")
    plaus = sum(1 for g in LR for v in g["volleys"] if not v["size"] and len(v["cols"]) >= 2 and
                ((len(v["cols"]) == 2 and v["cols"][1] - v["cols"][0] == 4) or len(v["cols"]) in (3, 4)))
    lulu = {
        "name": "lulu_fit_202610",
        "supersedes": "lulu_fit_202609 (kept unchanged): its volleys included missed same-colour spawns",
        "source": "refit_sends_202610.py, hidden-spawn tracker on the banked 9/27 clean-HDMI per-frame reads; dr. lulu (P1) sends as RECEIVED by ANTIBODY (P2)",
        "population": {"games": l_new["games"], "minutes": l_new["minutes"], "note": "n=2 games: PROVISIONAL (<10 games)"},
        "model": "independent renewal process of volleys (same form as owner_fit_202610)",
        "clear_pace_viruses_per_min": old_l["clear_pace_viruses_per_min"],
        "rate_volleys_per_min": l_new["rate_volleys_per_min"],
        "cells_per_min": l_new["cells_per_min"],
        "size_hist": l_new["size_hist"],
        "size_pmf": (lambda h: {k: round(h.get(k, 0) / sum(h.get(x, 0) for x in ("2", "3", "4")), 3) for k in ("2", "3", "4")})(l_new["size_hist"]),
        "size_pmf_note": "renormalised over sizes 2-4 (one 1-cell and one 6-cell reading are excluded, as in 202609)",
        "p_merged_double": l_new["p_merged_double"],
        "inter_volley_gap_s": {"quantiles": {k: l_new["gap_s"][k] for k in ("p10", "p25", "p50", "p75", "p90")},
                               "mean": l_new["gap_s"]["mean"], "cv": l_new["gap_s"]["cv"], "p_gap_le_3s": l_new["gap_s"]["p_le_3s"],
                               "samples": l_new["gap_samples"]},
        "unexplained_volleys": l_new["unexplained"],
        "unexplained_with_new_cells": l_new["unexplained_with_new_cells"],
        "unexplained_rom_plausible_multi_column": plaus,
        "rate_upper_bound_volleys_per_min": round((l_new["volleys"] + l_new["unexplained_with_new_cells"]) / l_new["minutes"], 2),
        "rate_plausible_upper_bound_volleys_per_min": round((l_new["volleys"] + plaus) / l_new["minutes"], 2),
        "upper_bound_note": "soft 720p capture: most unexplained steps add ONE cell in one column (reader errors, not a ROM volley shape)",
        "rom_column_rule": l_new["rom_column_rule"],
        "phase": {"note": "NOT recomputed (202609 phase counted hidden pills)"},
        "compare": {"lulu_fit_202609": {k: old_l[k] for k in ("rate_volleys_per_min", "cells_per_min", "size_pmf", "rate_upper_bound_volleys_per_min")},
                    "old_method_reproduced": {"rate": l_old["rate_volleys_per_min"], "cells_per_min": l_old["cells_per_min"]}},
    }
    json.dump(lulu, open(os.path.join(HERE, "lulu_fit_202610.json"), "w"), indent=1)
    print(json.dumps({"owner": {k: owner[k] for k in ("rate_volleys_per_min", "cells_per_min", "size_pmf", "p_double_in_one_placement_interval")},
                      "owner_gap": owner["inter_volley_gap_s"]["quantiles"],
                      "lulu": {k: lulu[k] for k in ("rate_volleys_per_min", "cells_per_min", "size_pmf", "rate_upper_bound_volleys_per_min",
                                                    "rate_plausible_upper_bound_volleys_per_min")}}, indent=1))


if __name__ == "__main__" and sys.argv[1] == "write":
    write_fits()
