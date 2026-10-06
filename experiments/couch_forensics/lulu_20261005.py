"""2026-10-05 couch: dr. lulu (P1, left, human) vs ANTIBODY_DIST_FAIR (P2, right; couch cart dbbb5007 + rbf 318607aa,
fw 1488e158; fair settle DRSETTLE=3/DRSETTLEPIN=0 + DRPROPHFIRST + DRLATEGUARD + DRSTUDYEND on DIST60), L11 MED.
The AI won both matches, 3-2 and 3-1: the first match wins any bot has taken off dr. lulu.

Recording: /mnt/data/Videos/2026-10-05 20-09-41.mkv (OBS 1080p60 clean HDMI, 2,313 s). 0-11 s = the owner's previous
match-final screen held by DRSTUDYEND (excluded). Reads: scan2_fair_20261004.py at 60 fps, both bottles, geometry
geom_lulu_20261005.json (P2 = the 10/03-10/04 fit; P1 x0 refit 424.1).

This module re-uses the 10/04 pipeline (fair_20261004.py: window / repair / sends / death; refit_sends_202610.volleys
and rom_rule; stall_fair_20261004's tag tracker) by pointing fair_20261004.SCAN and .GAMES at this recording.

Usage: python lulu_20261005.py track       hidden-spawn tracker on both seats of every game (rawh_* in SCAN)
       python lulu_20261005.py hudtpl      HUD digit templates for THIS capture (from the board reader's counts)
       python lulu_20261005.py results     verified results table (window, HUD finals, board finals, death)
       python lulu_20261005.py analyze     both seats per pill, gates, sends, pace, deaths, lane provenance
                                          -> cases_lulu_20261005_*.jsonl, summary_lulu_20261005.json
       python lulu_20261005.py fit         lulu_fit_202610b.json (these 9 games pooled with the 9/27 two)
"""
from __future__ import annotations

import bisect
import json
import os
import statistics as st
import subprocess
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fair_20261004 as FA  # noqa: E402
import hud_digits as H  # noqa: E402
import mech_check as MC  # noqa: E402
import refit_sends_202610 as RS  # noqa: E402

VIDEO = "/mnt/data/Videos/2026-10-05 20-09-41.mkv"
FX = "/home/struktured/projects/dr_mario_rl/tmp/lulu_20261005/fx"
SCAN = os.path.join(FX, "scan")
PY = sys.executable
ROWS, COLS = 16, 8

# name, match, game, scan window (t0, dur) -- quick read from round-end frames (to be verified here)
GAMES = [
    ("m1g1", 1, 1, (11, 359), "lulu topped out 06/04"),
    ("m1g2", 1, 2, (364, 404), "lulu cleared 00/07"),
    ("m1g3", 1, 3, (762, 122), "lulu topped out 25/07"),
    ("m1g4", 1, 4, (878, 236), "AI tapped out 03/16"),
    ("m1g5", 1, 5, (1108, 197), "AI cleared 26/00"),
    ("m2g1", 2, 1, (1299, 268), "lulu topped out 14/01"),
    ("m2g2", 2, 2, (1561, 244), "lulu topped out 06/01"),
    ("m2g3", 2, 3, (1799, 225), "lulu cleared 00/11"),
    ("m2g4", 2, 4, (2018, 295), "AI cleared 14/00"),
]
FA.SCAN = SCAN
FA.GAMES = [(g, "FAIR", m, gi, 1, log) for g, m, gi, _, log in GAMES]
_window_previews = FA.window


def window(g):
    """fair_20261004.window (game over = both previews blank >= 60 frames), with a fallback for the two match-final
    games here: M1 G5 (the next match started 5 s later, so the previews blank for only 1-3 frames) and M2 G4 (the
    recording ends on the DRSTUDYEND hold). Fallback: game over = the first frame after play started from which BOTH
    bottles' colour grids stay unchanged for >= 90 frames (a live capsule moves at least every gravity tick; at game
    over both bottles freeze). final[seat] = the board on that frame; virus_final as fair_20261004 (min over the last
    3 s; a clear's pop tiles read as viruses, so the HUD is the authority for the final counts)."""
    t_round, t_end, final = _window_previews(g)
    if t_end is not None:
        return t_round, t_end, final
    A, B = FA.frames(g, "p1"), FA.frames(g, "p2")
    n = min(len(A), len(B))
    i0 = next(i for i in range(n) if A[i]["t"] >= t_round)
    i_end = None
    for i in range(i0 + 600, n - 90):
        if all(A[j]["color"] == A[i]["color"] and B[j]["color"] == B[i]["color"] for j in range(i, i + 90)):
            i_end = i
            break
    if i_end is None:
        return t_round, None, None
    final = {}
    for seat, F in (("p1", A), ("p2", B)):
        final[seat] = dict(F[i_end], t_last_throw=F[i_end]["t"],
                           virus_final=min(F[i]["virus"].count("1") for i in range(max(i0, i_end - 180), i_end + 1)))
    return t_round, A[i_end]["t"], final


FA.window = window
HUD_TPL = os.path.join(HERE, "hud_templates_lulu_20261005.json")

# mech_check.explain is deterministic in (S_k, landing, S_{k+1} colours) and is called ~6x per step by the shared
# pipeline (repair, gates, volleys, death): memoise it (pure speed; verdicts unchanged).
_explain_orig = MC.explain
_explain_cache = {}


def _explain_cached(r, nxt):
    key = (r["S"]["color"], r["S"]["virus"], r["S"]["link"], json.dumps(r["landing"]), nxt["S"]["color"])
    if key not in _explain_cache:
        _explain_cache[key] = _explain_orig(r, nxt)
    return _explain_cache[key]


MC.explain = _explain_cached


def track():
    for g, *_ in GAMES:
        for seat in ("p1", "p2"):
            fr = os.path.join(SCAN, f"f60_{g}_{seat}.jsonl")
            out = os.path.join(SCAN, f"rawh_{g}_{seat}.jsonl")
            subprocess.run([PY, os.path.join(HERE, "track_hidden_dist60_20261003.py"), fr, out], check=True)


# ------------------------------------------------------------------------------------------------ HUD
def hud_samples(g):
    return [json.loads(l) for l in open(os.path.join(SCAN, f"f60_{g}_hud.jsonl"))]


def hudtpl():
    """Templates per SEAT and digit value from THIS capture's HUD boxes (geom HUD_X/HUD_Y): every HUD sample in a
    stretch where the seat's settled board count is stable (the same count at the spawns before and after) votes its
    tens/ones masks for that count's digits. Per seat, because the P1 boxes sit ~1 NES px off on this capture (P1 vs P2
    masks of the same digit differ by 12-24 of 64 bits, while each seat is self-consistent)."""
    votes = {}
    for g, *_ in GAMES:
        S = hud_samples(g)
        for seat, kt, ko in (("p1", "p1t", "p1o"), ("p2", "p2t", "p2o")):
            R = [json.loads(l) for l in open(os.path.join(SCAN, f"rawh_{g}_{seat}.jsonl"))]
            R = [r for r in R if 0 not in r["cur"]]
            for a, b in zip(R, R[1:]):
                if a["virus_count"] != b["virus_count"] or b["t_spawn"] - a["t_spawn"] > 6:
                    continue
                c = a["virus_count"]
                for s in S:
                    if a["t_spawn"] + 0.3 <= s["t"] <= b["t_spawn"] - 0.3:
                        votes.setdefault((seat, c // 10), []).append(s[kt]); votes.setdefault((seat, c % 10), []).append(s[ko])
    tpl = {"p1": {}, "p2": {}}
    for (seat, d), ms in sorted(votes.items()):
        arr = np.array([[int(ch) for ch in m] for m in ms])
        tpl[seat][str(d)] = "".join(str(int(v)) for v in (arr.mean(0) >= 0.5))
    json.dump(tpl, open(HUD_TPL, "w"), indent=1)
    print({f"{s}:{d}": len(v) for (s, d), v in sorted(votes.items())})
    for seat in ("p1", "p2"):
        ks = sorted(tpl[seat])
        print(seat, "min inter-template hamming", min(H.hamming(tpl[seat][a], tpl[seat][b]) for a in ks for b in ks if a < b))


def hud_series(g):
    T = json.load(open(HUD_TPL))
    tp = {seat: {int(k): v for k, v in T[seat].items()} for seat in ("p1", "p2")}
    out = []
    for s in hud_samples(g):
        a = [H.read_digit(s[k], tp[k[:2]], max_dist=8) for k in ("p1t", "p1o", "p2t", "p2o")]
        if any(x[0] is None for x in a):
            out.append((s["t"], None, None)); continue
        out.append((s["t"], 10 * a[0][0] + a[1][0], 10 * a[2][0] + a[3][0]))
    return out


def hud_at_end(g, t_end):
    """The final HUD counts: the last readable sample in [t_end - 1, t_end + 1] (the counter takes the game-ending
    clear up to ~0.5 s after the boards freeze / the previews blank; the next game's virus field starts filling the
    counter ~1.5 s after a stage clear, e.g. M2 G2 -> 19/19 at +2 s)."""
    ser = [x for x in hud_series(g) if x[1] is not None and t_end - 1 <= x[0] <= t_end + 1]
    if not ser:
        return None
    return (ser[-1][1], ser[-1][2])


# ------------------------------------------------------------------------------------------------ results
def results(verbose=True, only=None):
    rows = []
    for g, m, gi, win, log in GAMES:
        if only and g not in only:
            continue
        t_round, t_end, final = FA.window(g)
        R2 = FA.load_raw(g, "p2", t_round, t_end); R1 = FA.load_raw(g, "p1", t_round, t_end)
        hud = hud_at_end(g, t_end)
        plug = {}
        for seat, R in (("p1", R1), ("p2", R2)):
            vol = RS.volleys(R1 if seat == "p1" else R2)[0]
            d = FA.death(final[seat], R, vol)
            plug[seat] = d
        bv = {s: final[s]["virus_final"] for s in ("p1", "p2")}
        hp1, hp2 = hud if hud else (None, None)
        if hp1 == 0 or (hud is None and bv["p1"] == 0):
            winner, how = "lulu", "cleared"
        elif hp2 == 0:
            winner, how = "AI", "cleared"
        elif plug["p1"]["plug"] and not plug["p2"]["plug"]:
            winner, how = "AI", "lulu topped out"
        elif plug["p2"]["plug"] and not plug["p1"]["plug"]:
            winner, how = "lulu", "AI topped out"
        else:
            winner, how = "?", f"plugs p1 {plug['p1']['plug']} p2 {plug['p2']['plug']}"
        t0 = min(R1[0]["t_spawn"], R2[0]["t_spawn"])
        row = {"game": g, "match": m, "g": gi, "quick_read": log, "t_round": t_round, "t0_first_spawn": t0, "t_end": t_end,
               "dur_s": round(t_end - t0, 1), "hud_final_lulu_ai": hud, "board_final_lulu_ai": [bv["p1"], bv["p2"]],
               "winner": winner, "how": how, "plug_lulu": plug["p1"]["plug"], "plug_ai": plug["p2"]["plug"],
               "pills_lulu": len(R1), "pills_ai": len(R2)}
        rows.append(row)
        if verbose:
            print(json.dumps(row))
    return rows


# ------------------------------------------------------------------------------------------------ analysis
def gate(R):
    m = [MC.explain(R[i], R[i + 1]) for i in range(len(R) - 1)]
    return {"steps": len(m), "exact": sum(1 for v in m if v == 0), "garbage": sum(1 for v in m if v not in (None, 0)),
            "unexplained": sum(1 for v in m if v is None),
            "unexplained_t": [round(R[i]["t_spawn"], 2) for i, v in enumerate(m) if v is None]}


def repairs_summary(fixes):
    c = Counter(f["fix"] + (":" + f["how"] if f.get("how") else "") for f in fixes)
    return dict(c)


def seat_pace(cases, t0, t_end, v_final):
    """pills/min and viruses/min by time window and by the seat's remaining-virus bin (time in a bin = the
    inter-spawn intervals that START in it; the last interval runs to t_end)."""
    T = [c["t_spawn"] for c in cases] + [t_end]
    Vc = [c["virus_count"] for c in cases] + [v_final]
    out = {}
    for lo, hi, lab in ((0, 60, "0-60s"), (60, 120, "60-120s"), (120, 1e9, ">=120s"), (0, 1e9, "all")):
        a, b = t0 + lo, min(t0 + hi, t_end)
        if b <= a:
            continue
        idx = [i for i in range(len(cases)) if a <= T[i] < b]
        va = next((Vc[i] for i in range(len(cases) + 1) if T[i] >= a), v_final)
        vb = next((Vc[i] for i in range(len(cases) + 1) if T[i] >= b), v_final) if b < t_end else v_final
        mins = (b - a) / 60
        out[lab] = {"seconds": round(b - a, 1), "pills": len(idx), "pills_per_min": round(len(idx) / mins, 1),
                    "viruses": va - vb, "viruses_per_min": round((va - vb) / mins, 2)}
    for lo, hi, lab in ((31, 99, ">30 left"), (13, 30, "13-30 left"), (0, 12, "<=12 left")):
        secs = pills = vir = 0
        for i in range(len(cases)):
            if lo <= Vc[i] <= hi:
                secs += T[i + 1] - T[i]; pills += 1; vir += Vc[i] - Vc[i + 1]
        if secs > 0:
            out[lab] = {"seconds": round(secs, 1), "pills": pills, "pills_per_min": round(pills / (secs / 60), 1),
                        "viruses": vir, "viruses_per_min": round(vir / (secs / 60), 2)}
    return out


def lane_provenance(R, final_board, seat_tag="P"):
    """Spawn-lane (cols 3-4) provenance at the seat's death: own pill halves (P), received garbage (G), viruses (V),
    with stall_fair_20261004's tag tracker (lane_fair_20261004.py method)."""
    import stall_fair_20261004 as SF
    A = SF.A
    S0 = FA.grid(R[0]["S"]["color"]); V0 = FA.grid(R[0]["S"]["virus"])
    T = np.full((16, 8), "", dtype=object); T[(S0 > 0) & (V0 > 0)] = "V"; T[(S0 > 0) & (V0 == 0)] = "?"
    Tlast = Plast = None
    for n, r in enumerate(R):
        S = r["S"]; o, orow, ocol, ocl = r["landing"]
        bp = A.board_from_strings(S["color"], S["virus"], S["link"]); Tp = T.copy(); tag = "P%d" % n
        if o == "H":
            bp.color[orow, ocol], bp.color[orow, ocol + 1] = ocl; bp.link[orow, ocol], bp.link[orow, ocol + 1] = 4, 3
            Tp[orow, ocol] = Tp[orow, ocol + 1] = tag
        else:
            bp.color[orow, ocol], bp.color[orow + 1, ocol] = ocl; bp.link[orow, ocol], bp.link[orow + 1, ocol] = 2, 1
            Tp[orow, ocol] = Tp[orow + 1, ocol] = tag
        bp, Tp = SF.resolve_tagged(bp, Tp)
        if n + 1 < len(R):
            T = SF.reconcile(bp.color, Tp, FA.grid(R[n + 1]["S"]["color"]), "G%d" % n)
        else:
            Tlast, Plast = Tp, bp.color
    F = FA.grid(final_board["color"]); Vf = FA.grid(final_board["virus"])
    Tf = SF.reconcile(Plast, Tlast, F, "Gend")
    lane = {}
    for c in (3, 4):
        cells = [(r, int(F[r, c]), str(Tf[r, c])) for r in range(16) if F[r, c] > 0]
        top_v = next((r for r in range(16) if Vf[r, c]), 16)
        above = [x for x in cells if x[0] < top_v]
        lane[c] = {"height": 16 - (cells[0][0] if cells else 16), "cells_above_top_virus": len(above),
                   "by_provenance": dict(Counter(x[2][0] if x[2] else "?" for x in above)),
                   "top_cells": [(x[0], x[2]) for x in cells[:4]]}
    whole = Counter(str(x)[0] if x else "?" for x in Tf.ravel() if x != "")
    return {"lane": lane, "board_cells_by_provenance": dict(whole)}


def analyze(only=None):
    """only = [game]: analyse that game and write its part to FX/scan/part_<game>.json (merge() combines the parts)."""
    res = {r["game"]: r for r in results(verbose=False, only=only)}
    out, c_l, c_a, c_v = [], [], [], []
    for g, m, gi, win, log in GAMES:
        if only and g not in only:
            continue
        t_round, t_end, final = FA.window(g)
        R1, f1 = FA.load_raw(g, "p1", t_round, t_end, with_fixes=True)
        R2, f2 = FA.load_raw(g, "p2", t_round, t_end, with_fixes=True)
        t0 = min(R1[0]["t_spawn"], R2[0]["t_spawn"])
        rr = res[g]
        hud = rr["hud_final_lulu_ai"] or rr["board_final_lulu_ai"]
        fv1, fv2 = hud
        ai_cases, ai_att = FA.ai_attacks(R2, t0)
        lu_cases, lu_att = FA.ai_attacks(R1, t0)           # same sender-side rule, lulu's placements
        vol_to_lulu, dur1 = RS.volleys(R1)
        vol_to_ai, dur2 = RS.volleys(R2)
        for v in vol_to_lulu + vol_to_ai:
            v["t_rel"] = round(v["t"] - t0, 3)
        pa, ga, ua = FA.match_attacks(ai_att, vol_to_lulu)
        pl, gl, ul = FA.match_attacks(lu_att, vol_to_ai)
        mins_ai_track = dur2 / 60
        recv = [v for v in vol_to_ai if v["size"]]
        row = {"game": g, "match": m, "g": gi, "winner": rr["winner"], "how": rr["how"], "t0": t0, "t_end": t_end,
               "dur_s": round(t_end - t0, 1), "final_lulu_ai": [fv1, fv2],
               "pills": {"lulu": len(R1), "ai": len(R2)},
               "hidden_spawns": {"lulu": sum(1 for r in R1 if r.get("spawn_kind") == "hidden"),
                                 "ai": sum(1 for r in R2 if r.get("spawn_kind") == "hidden")},
               "gate": {"lulu": gate(R1), "ai": gate(R2)},
               "repairs": {"lulu": repairs_summary(f1), "ai": repairs_summary(f2)},
               "pace": {"lulu": seat_pace(R1, t0, t_end, fv1), "ai": seat_pace(R2, t0, t_end, fv2)},
               "lulu_sends": {"sender_side_attacks": len(lu_att), "sender_side_sizes": dict(Counter(a["size"] for a in lu_att)),
                              "recv_by_ai_volleys": len(recv), "recv_by_ai_cells": sum(v["size"] for v in recv),
                              "recv_by_ai_sizes": dict(Counter(v["size"] for v in recv)),
                              "recv_unexplained": sum(1 for v in vol_to_ai if not v["size"]),
                              "recv_unexplained_with_new_cells": sum(1 for v in vol_to_ai if not v["size"] and v["cols"]),
                              "ai_track_minutes": round(mins_ai_track, 2),
                              "volleys_per_min": round(len(recv) / mins_ai_track, 2),
                              "cells_per_min": round(sum(v["size"] for v in recv) / mins_ai_track, 2),
                              "rom_column_rule": RS.rom_rule(vol_to_ai),
                              "first_send_s": lu_att[0]["t_rel"] if lu_att else None,
                              "attacks_assigned_to_a_volley": sum(1 for a, v in pl if v),
                              "attacks_in_flight_at_end": sum(1 for a, v in pl if v is None),
                              "recv_size_eq_min_sum4": sum(1 for v, gg in gl if gg and v["size"] == min(sum(a["size"] for a in gg), 4)),
                              "recv_with_merged_sends": sum(1 for v, gg in gl if len(gg) >= 2),
                              "recv_unmatched": len(ul)},
               "ai_sends": {"sender_side_attacks": len(ai_att), "sender_side_sizes": dict(Counter(a["size"] for a in ai_att)),
                            "recv_by_lulu_volleys": sum(1 for v in vol_to_lulu if v["size"]),
                            "recv_by_lulu_cells": sum(v["size"] for v in vol_to_lulu if v["size"]),
                            "recv_by_lulu_sizes": dict(Counter(v["size"] for v in vol_to_lulu if v["size"])),
                            "lulu_track_minutes": round(dur1 / 60, 2),
                            "volleys_per_min": round(sum(1 for v in vol_to_lulu if v["size"]) / (dur1 / 60), 2),
                            "cells_per_min": round(sum(v["size"] for v in vol_to_lulu if v["size"]) / (dur1 / 60), 2),
                            "rom_column_rule": RS.rom_rule(vol_to_lulu),
                            "first_send_s": ai_att[0]["t_rel"] if ai_att else None,
                            "attacks_assigned_to_a_volley": sum(1 for a, v in pa if v),
                            "attacks_in_flight_at_end": sum(1 for a, v in pa if v is None),
                            "recv_size_eq_min_sum4": sum(1 for v, gg in ga if gg and v["size"] == min(sum(a["size"] for a in gg), 4)),
                            "recv_unmatched": len(ua)},
               "death": {"lulu": FA.death(final["p1"], R1, vol_to_lulu), "ai": FA.death(final["p2"], R2, vol_to_ai)}}
        loser = "p1" if rr["winner"] == "AI" and "topped" in rr["how"] else ("p2" if rr["winner"] == "lulu" and "AI topped" in rr["how"] else None)
        if loser:
            row["lane_at_death"] = {"seat": "lulu" if loser == "p1" else "ai",
                                    **lane_provenance(R1 if loser == "p1" else R2, final[loser])}
        row["fit_row"] = {"opp": "lulu", "pop": "1005", "session": "10/05 lulu", "level": 11, "game": g, "tracker": "new",
                          "n_placements": len(R2), "dur_s": round(dur2, 1), "volleys": vol_to_ai,
                          "hidden_spawns": sum(1 for r in R2 if r.get("spawn_kind") == "hidden"),
                          "lulu_viruses": [48, fv1], "game_s": round(t_end - t0, 1),
                          "lulu_vcount_at": [(round(r["t_spawn"] - t0, 2), r["virus_count"]) for r in R1]}
        out.append(row)
        for c in lu_cases:
            c_l.append({"game": g, **c, "heights_before": FA.heights(FA.grid(R1[c["k"]]["S"]["color"]))})
        for c in ai_cases:
            c_a.append({"game": g, **c})
        for a, v in pl:
            c_v.append({"game": g, "kind": "lulu_send", **a, "recv": ({k: v[k] for k in ("t", "t_rel", "size", "how", "cols")} if v else None)})
        for v, gg in gl:
            c_v.append({"game": g, "kind": "ai_recv", **{k: v[k] for k in ("t", "t_rel", "tb", "size", "how", "cols", "n_cols")},
                        "sends": [a["k"] for a in gg], "expected_size": min(sum(a["size"] for a in gg), 4) if gg else None,
                        "rom_cols_ok": RS.rom_rule([v])["conform"] == 1, "rom_cols_checkable": sum(RS.rom_rule([v]).values()) == 1})
        for v in vol_to_ai:
            if not v["size"]:
                c_v.append({"game": g, "kind": "ai_recv_unexplained", **{k: v[k] for k in ("t", "t_rel", "tb", "how", "cols", "n_cols")}})
        for a, v in pa:
            c_v.append({"game": g, "kind": "ai_send", **a, "recv": ({k: v[k] for k in ("t", "t_rel", "size", "how", "cols")} if v else None)})
        for v, gg in ga:
            c_v.append({"game": g, "kind": "lulu_recv", **{k: v[k] for k in ("t", "t_rel", "tb", "size", "how", "cols", "n_cols")},
                        "sends": [a["k"] for a in gg], "rom_cols_ok": RS.rom_rule([v])["conform"] == 1,
                        "rom_cols_checkable": sum(RS.rom_rule([v]).values()) == 1})
        print(g, json.dumps({k: row[k] for k in ("winner", "how", "dur_s", "final_lulu_ai", "pills", "gate", "repairs")}), flush=True)
    if only:
        json.dump({"results": list(res.values()), "games": out, "c_l": c_l, "c_a": c_a, "c_v": c_v},
                  open(os.path.join(SCAN, f"part_{only[0]}.json"), "w"))
        return
    w = lambda name, rows: open(os.path.join(HERE, name), "w").write("".join(json.dumps(r) + "\n" for r in rows))
    w("cases_lulu_20261005_lulu_pills.jsonl", c_l)
    w("cases_lulu_20261005_ai_pills.jsonl", c_a)
    w("cases_lulu_20261005_volleys.jsonl", c_v)
    json.dump({"results": list(res.values()), "games": out}, open(os.path.join(HERE, "summary_lulu_20261005.json"), "w"), indent=1)


def merge():
    """Combine FX/scan/part_<game>.json (analyze <game>, run per game in parallel) into the banked outputs."""
    res, out, c_l, c_a, c_v = [], [], [], [], []
    for g, *_ in GAMES:
        P = json.load(open(os.path.join(SCAN, f"part_{g}.json")))
        res += P["results"]; out += P["games"]; c_l += P["c_l"]; c_a += P["c_a"]; c_v += P["c_v"]
    w = lambda name, rows: open(os.path.join(HERE, name), "w").write("".join(json.dumps(r) + "\n" for r in rows))
    w("cases_lulu_20261005_lulu_pills.jsonl", c_l)
    w("cases_lulu_20261005_ai_pills.jsonl", c_a)
    w("cases_lulu_20261005_volleys.jsonl", c_v)
    json.dump({"results": res, "games": out}, open(os.path.join(HERE, "summary_lulu_20261005.json"), "w"), indent=1)
    for r in res:
        print(json.dumps(r))


def fit():
    """lulu_fit_202610b.json: dr. lulu's sends as RECEIVED by the AI, these 9 games (10/05, fixed tracker, clean 1080p)
    pooled with the 9/27 two (refit_sends_202610_cases.jsonl, new tracker), in lulu_fit_202610's key layout."""
    S = json.load(open(os.path.join(HERE, "summary_lulu_20261005.json")))
    new = [g["fit_row"] for g in S["games"]]
    old = [r for r in map(json.loads, open(os.path.join(HERE, "refit_sends_202610_cases.jsonl")))
           if r["opp"] == "lulu" and r["tracker"] == "new"]
    pooled = RS.stats(new + old); only = RS.stats(new); prev = RS.stats(old)
    f10 = json.load(open(os.path.join(HERE, "lulu_fit_202610.json")))

    def plaus(G):
        return sum(1 for g in G for v in g["volleys"] if not v["size"] and len(v["cols"]) >= 2 and
                   ((len(v["cols"]) == 2 and v["cols"][1] - v["cols"][0] == 4) or len(v["cols"]) in (3, 4)))
    pace = {g["game"]: round((g["final_lulu_ai"][0] is not None and (48 - g["final_lulu_ai"][0])) / (g["dur_s"] / 60), 2)
            for g in S["games"]}
    pace.update({"9/27 " + k: v for k, v in f10["clear_pace_viruses_per_min"].items()})
    # phase (10/05 games only: her remaining viruses from her own track; time from the first spawn)
    ph_t = {}; ph_v = {}
    for g in new:
        vc = g["lulu_vcount_at"]; ts = [x[0] for x in vc]
        t0 = S["games"][[x["game"] for x in S["games"]].index(g["game"])]["t0"]
        for v in g["volleys"]:
            if not v["size"]:
                continue
            tr = v["t"] - t0
            i = max(0, bisect.bisect_right(ts, tr) - 1); left = vc[i][1]
            tk = "open <30s" if tr < 30 else ("30-90s" if tr < 90 else ">=90s")
            vk = ">30" if left > 30 else ("21-30" if left > 20 else ("9-20" if left > 8 else "<=8"))
            for d, k in ((ph_t, tk), (ph_v, vk)):
                d.setdefault(k, [0, 0]); d[k][0] += 1; d[k][1] += v["size"]
    # exposure (minutes) per phase from her own track
    ex_t = Counter(); ex_v = Counter()
    for g in new:
        vc = g["lulu_vcount_at"] + [(g["game_s"], g["lulu_viruses"][1])]
        for (ta, va), (tb, vb) in zip(vc, vc[1:]):
            dt = min(tb - ta, RS.DT_CAP) / 60
            tk = "open <30s" if ta < 30 else ("30-90s" if ta < 90 else ">=90s")
            vk = ">30" if va > 30 else ("21-30" if va > 20 else ("9-20" if va > 8 else "<=8"))
            ex_t[tk] += dt; ex_v[vk] += dt
    phase = {"note": "10/05 games only (her remaining viruses from her own fixed-tracker track; the 9/27 tracks are P2-only)",
             "time": {k: {"minutes": round(ex_t[k], 2), "volleys": ph_t.get(k, [0, 0])[0],
                          "volleys_per_min": round(ph_t.get(k, [0, 0])[0] / ex_t[k], 2) if ex_t[k] else None,
                          "cells_per_min": round(ph_t.get(k, [0, 0])[1] / ex_t[k], 2) if ex_t[k] else None}
                      for k in ("open <30s", "30-90s", ">=90s")},
             "lulu": {k: {"minutes": round(ex_v[k], 2), "volleys": ph_v.get(k, [0, 0])[0],
                          "volleys_per_min": round(ph_v.get(k, [0, 0])[0] / ex_v[k], 2) if ex_v[k] else None,
                          "cells_per_min": round(ph_v.get(k, [0, 0])[1] / ex_v[k], 2) if ex_v[k] else None}
                      for k in (">30", "21-30", "9-20", "<=8")}}
    h = pooled["size_hist"]
    fitd = {
        "name": "lulu_fit_202610b",
        "supersedes": "lulu_fit_202610 (kept unchanged; n=2 games): adds the 9 games of 10/05 (1080p clean HDMI, fixed tracker)",
        "source": "lulu_20261005.py fit: dr. lulu (P1) sends as RECEIVED by ANTIBODY_DIST_FAIR (P2), 10/05 9 games "
                  "(summary_lulu_20261005.json fit_row, refit_sends_202610.volleys verbatim on the hidden-spawn tracker) + the 9/27 2 "
                  "(refit_sends_202610_cases.jsonl, tracker=new)",
        "population": {"games": pooled["games"], "minutes": pooled["minutes"],
                       "note": f"n={pooled['games']} games over 2 sessions (9/27 vs ANTIBODY, 10/05 vs ANTIBODY_DIST_FAIR); "
                               "10/05 she was frustrated by the end (owner report); per-session rates below"},
        "model": "independent renewal process of volleys (same form as owner_fit_202610)",
        "clear_pace_viruses_per_min": pace,
        "rate_volleys_per_min": pooled["rate_volleys_per_min"],
        "rate_ci95_game_bootstrap": pooled["rate_ci95_game_bootstrap"],
        "cells_per_min": pooled["cells_per_min"],
        "size_hist": h,
        "size_pmf": {k: round(h.get(k, 0) / sum(h.get(x, 0) for x in ("2", "3", "4")), 3) for k in ("2", "3", "4")},
        "size_pmf_note": "renormalised over sizes 2-4 (1-cell and >4-cell readings excluded, as in 202609/202610)",
        "p_merged_double": pooled["p_merged_double"],
        "inter_volley_gap_s": {"quantiles": {k: pooled["gap_s"][k] for k in ("p10", "p25", "p50", "p75", "p90")},
                               "mean": pooled["gap_s"]["mean"], "cv": pooled["gap_s"]["cv"], "p_gap_le_3s": pooled["gap_s"]["p_le_3s"],
                               "samples": pooled["gap_samples"]},
        "unexplained_volleys": pooled["unexplained"],
        "unexplained_with_new_cells": pooled["unexplained_with_new_cells"],
        "unexplained_rom_plausible_multi_column": plaus(new + old),
        "rate_upper_bound_volleys_per_min": round((pooled["volleys"] + pooled["unexplained_with_new_cells"]) / pooled["minutes"], 2),
        "rate_plausible_upper_bound_volleys_per_min": round((pooled["volleys"] + plaus(new + old)) / pooled["minutes"], 2),
        "upper_bound_note": "unexplained steps that add cells: 1080p 10/05 + soft 720p 9/27 reader errors (mostly one cell in one column)",
        "rom_column_rule": pooled["rom_column_rule"],
        "per_session_rate": pooled["per_session_rate"],
        "phase": phase,
        "sessions": {k: {kk: d[kk] for kk in ("games", "minutes", "volleys", "rate_volleys_per_min", "rate_ci95_game_bootstrap",
                                               "cells_per_min", "mean_size", "size_hist", "size_pmf_le4", "p_merged_double",
                                               "unexplained", "unexplained_with_new_cells", "rom_column_rule")}
                     | {"gap_s": {kk: d["gap_s"][kk] for kk in ("p10", "p50", "p90", "cv")}}
                     for k, d in (("10/05 only (9 games)", only), ("9/27 only (2 games) = lulu_fit_202610", prev))},
        "compare": {"lulu_fit_202610": {k: f10[k] for k in ("rate_volleys_per_min", "cells_per_min", "size_pmf",
                                                              "rate_upper_bound_volleys_per_min")},
                    "lulu_fit_202610_reproduced": {"rate": prev["rate_volleys_per_min"], "cells_per_min": prev["cells_per_min"]}},
    }
    json.dump(fitd, open(os.path.join(HERE, "lulu_fit_202610b.json"), "w"), indent=1)
    print(json.dumps({k: fitd[k] for k in ("rate_volleys_per_min", "rate_ci95_game_bootstrap", "cells_per_min", "size_hist", "size_pmf",
                                          "p_merged_double", "rom_column_rule", "per_session_rate", "clear_pace_viruses_per_min")}, indent=1))
    print(json.dumps(fitd["inter_volley_gap_s"]["quantiles"]), json.dumps(fitd["sessions"], indent=1), json.dumps(phase, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "analyze" and len(sys.argv) > 2:
        analyze(only=sys.argv[2:3])
    else:
        {"track": track, "hudtpl": hudtpl, "results": results, "analyze": analyze, "merge": merge, "fit": fit}[sys.argv[1]]()
