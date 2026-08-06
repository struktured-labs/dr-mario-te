#!/usr/bin/env python3
"""M3 DEATH-BOARD case study: base32 / reach32 / reachfull decides on the 6
reconstructed tape commits from film_review_20260804/recon/boards.json.

For each commit:
  - build FB(col,vir) from the reconstructed board_colors/board_isvirus
  - run reach_root.choose('base32'/'reach32'/'reachfull', ...)
  - report chosen placement per mode
  - check whether base32's argmax (var,cc) is BFS-reachable at all
    (via the same TE straight-drop lookup reach32 filters against)
  - compute hooks_needed = 32 * DAS-column-edges for each mode's pick
    (edges = min(|col-3|,|col-4|), the nearest spawn half; 32 hooks/edge is
    the driver's own DAS-cadence constant, patch_cartridge_copro.py:1554-1556,
    "NAV_T=5*/frame ... 32-hook cycles = 6.4 frames per edge") and flag any
    choice needing > 40 hooks (the PAIR_LATCH_AUDIT.md Sec.7 historical
    ~40-hook window: reaches 1-column-distant targets, not 3-column ones)
  - note whether the pick lands in the {0,6,7} human-preferred family
"""
from __future__ import annotations
import sys, os, json

HERE = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47"
ROOT = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
for _p in (HERE, ROOT + "/tmp/combo_term", ROOT + "/tmp/endgame", ROOT + "/tmp/tuck",
           ROOT + "/tmp/pillrng", ROOT + "/.claude/worktrees/faithful-sim/src", QA,
           QA + "/tuck_v3"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import reach_root as RR

BOARDS_JSON = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/boards.json"
PROXY_JSON = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/proxy_results.json"

LETTER2COL = {".": 0, "R": 1, "Y": 2, "B": 3}
HUMAN_FAMILY = {0, 6, 7}
HOOKS_PER_EDGE = 32
WINDOW_HOOKS = 40


def build_fb(entry):
    L = RR._lazy()
    FB = L["FB"]
    col = []
    vir = []
    for row_c, row_v in zip(entry["board_colors"], entry["board_isvirus"]):
        for ch, vch in zip(row_c, row_v):
            col.append(LETTER2COL[ch])
            vir.append(1 if vch == "1" else 0)
    return FB(col, vir, None)


def edges_from_spawn(col_target):
    return min(abs(col_target - 3), abs(col_target - 4))


def decode_base_action(action):
    var, cc = action // 8, action % 8
    o4 = var ^ 2
    return var, cc, o4


def describe(mode, out, fb, ca, cb):
    """Normalize a choose() result to {col, o4/orient, val, kind, reachable_note}."""
    if out["kind"] == "base":
        var, cc, o4 = decode_base_action(out["action"])
        orient = "V" if o4 in (0, 1) else "H"
        return {"kind": "base", "col": cc, "o4": o4, "variant": var,
                "orient": orient, "val": float(out["val"])}
    else:  # tuck
        p = out["placement"]
        col_ = p["col"]
        variant = p["variant"]
        o4 = variant ^ 2
        orient = "V" if o4 in (0, 1) else "H"
        return {"kind": "tuck", "col": col_, "o4": o4, "variant": variant,
                "orient": orient, "val": float(out["val"]),
                "margin_over_base": out.get("margin"),
                "best_base_val": out.get("best_base_val")}


def main():
    boards = json.load(open(BOARDS_JSON))["boards"]
    proxy = {b["index"]: b for b in json.load(open(PROXY_JSON))["boards"]}

    RR._lazy()  # warm numba once, up front

    report = []
    for idx, entry in enumerate(boards):
        if entry.get("tape_placement") is None:
            continue  # index 0, control board, no commit
        fb = build_fb(entry)
        col, vir = RR._lazy()["RS"].board_flat_from_fb(fb)
        pill = entry["pill"]
        nxt = entry["next"]
        ca, cb = LETTER2COL[pill[0]], LETTER2COL[pill[1]]
        na, nb = LETTER2COL[nxt[0]], LETTER2COL[nxt[1]]

        outs = {}
        for mode in RR.MODES:
            raw = RR.choose(mode, fb, col, vir, ca, cb, na, nb)
            outs[mode] = (raw, describe(mode, raw, fb, ca, cb))

        # is base32's argmax BFS-reachable at all?
        b32_raw, b32 = outs["base32"]
        lookup = RR._te_straight_lookup(fb, ca, cb)
        te_entry = lookup.get((b32["variant"], b32["col"]))
        base32_reachable = bool(te_entry["reachable"]) if te_entry is not None else None

        # reach32 diagnostics straight from its own output dict
        r32_raw, r32 = outs["reach32"]
        n_base_legal = r32_raw.get("n_base_legal")
        n_reach = r32_raw.get("n_reach")
        fallback = r32_raw.get("fallback_unreachable")

        rf_raw, rf = outs["reachfull"]
        rf["n_tuck_cands"] = rf_raw.get("n_tuck_cands")
        rf["n_tuck_legal"] = rf_raw.get("n_tuck_legal")
        rf["best_base_val"] = rf_raw.get("best_base_val")

        row = {
            "commit_index": idx,
            "t_video": entry["t_video"],
            "pill": pill, "next": nxt,
            "tape_placement": entry["tape_placement"],
            "shipped_strand20_chosen": proxy[idx]["shipped_strand20"]["chosen"],
            "shipped_strand20_family_values": proxy[idx]["shipped_strand20"]
                ["column_family_margin"]["family_values"],
            "base32": {**b32, "reachable": base32_reachable,
                       "n_base_legal_candidates": n_base_legal,
                       "n_reach_of_those": n_reach,
                       "reach32_fallback_to_base32": fallback},
            "reach32": r32,
            "reachfull": rf,
        }
        for mode_name, d in (("base32", b32), ("reach32", r32), ("reachfull", rf)):
            edges = edges_from_spawn(d["col"])
            hooks = HOOKS_PER_EDGE * edges
            row.setdefault("hooks", {})[mode_name] = {
                "col": d["col"], "edges_from_spawn": edges, "hooks_needed": hooks,
                "exceeds_40hook_window": hooks > WINDOW_HOOKS,
            }
            row.setdefault("human_family_match", {})[mode_name] = d["col"] in HUMAN_FAMILY
        report.append(row)

    out_path = "/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/tmp_logs/m3case_raw.json"
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"wrote {out_path}")

    # console summary
    for row in report:
        print(f"\n=== commit {row['commit_index']} t={row['t_video']} pill={row['pill']} next={row['next']} ===")
        print(f"  tape actually placed: col~{row['tape_placement']['cells'][0][1]} orient={row['tape_placement']['orient']} spawn_to_lock_frames={row['tape_placement']['spawn_to_lock_frames']}")
        for mode in RR.MODES:
            d = row[mode]
            h = row["hooks"][mode]
            hm = row["human_family_match"][mode]
            extra = ""
            if mode == "base32":
                extra = f" reachable={d['reachable']} n_reach/n_legal={d['n_reach_of_those']}/{d['n_base_legal_candidates']}"
            print(f"  {mode:>9s}: kind={d['kind']:4s} col={d['col']} o4={d['o4']} orient={d['orient']} "
                  f"val={d['val']:.1f} hooks_needed={h['hooks_needed']} exceeds40={h['exceeds_40hook_window']} "
                  f"human_family={hm}{extra}")


if __name__ == "__main__":
    main()
