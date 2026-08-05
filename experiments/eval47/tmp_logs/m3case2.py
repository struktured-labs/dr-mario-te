#!/usr/bin/env python3
"""M3 DEATH-BOARD case study, ITERATION 2 (task #60): all 6 reach_root.py
modes -- base32 / reach32 / reachfull (pre-fix, kept for before/after) /
reach32t / reachfull2 (THE FIX) / reachfull2t -- on the same 6 reconstructed
tape commits m3case.py used. Supersedes m3case.py's console report (which is
hardcoded to the original 3 modes) without touching that file, since
m3case.py's own raw JSON / selftest-adjacent role stays valid for the
before/after comparison this iteration's acceptance check needs.

Acceptance check (REACH_ROOT_VERDICT.md ITERATION 2 prescription): reachfull2
must DIVERGE from base32 on the 4/6 commits where base32's own argmax is
BFS-unreachable (1, 2, 4, 6) -- the old reachfull's defect was 0/6 divergence
there.
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

import reach_root as RR

BOARDS_JSON = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/boards.json"
PROXY_JSON = "/home/struktured/projects/dr_mario_rl/tmp/film_review_20260804/recon/proxy_results.json"

LETTER2COL = {".": 0, "R": 1, "Y": 2, "B": 3}
HUMAN_FAMILY = {0, 6, 7}
# historical (STALE, CART_FIX_REPORT.md-section-7-prose) window, kept for
# continuity with REACH_ROOT_M3CASE.md's own table -- NOT what the new
# reach32t/reachfull2t filters actually use (they use reach_root.py's live
# DIST_DASEDGE/DIST_GRAVROW, silicon-measured 2026-08-05, see that file).
HOOKS_PER_EDGE_HISTORICAL = 32
WINDOW_HOOKS_HISTORICAL = 40


def build_fb(entry):
    L = RR._lazy()
    FB = L["FB"]
    col, vir = [], []
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


def describe(out):
    if out["kind"] == "base":
        var, cc, o4 = decode_base_action(out["action"])
        orient = "V" if o4 in (0, 1) else "H"
        return {"kind": "base", "col": cc, "o4": o4, "variant": var,
                "orient": orient, "val": float(out["val"])}
    p = out["placement"]
    col_, variant = p["col"], p["variant"]
    o4 = variant ^ 2
    orient = "V" if o4 in (0, 1) else "H"
    return {"kind": "tuck", "col": col_, "o4": o4, "variant": variant,
            "orient": orient, "val": float(out["val"]),
            "margin_over_base": out.get("margin"), "best_base_val": out.get("best_base_val")}


def main():
    boards = json.load(open(BOARDS_JSON))["boards"]
    proxy = {b["index"]: b for b in json.load(open(PROXY_JSON))["boards"]}
    RR._lazy()

    report = []
    for idx, entry in enumerate(boards):
        if entry.get("tape_placement") is None:
            continue
        fb = build_fb(entry)
        col, vir = RR._lazy()["RS"].board_flat_from_fb(fb)
        pill, nxt = entry["pill"], entry["next"]
        ca, cb = LETTER2COL[pill[0]], LETTER2COL[pill[1]]
        na, nb = LETTER2COL[nxt[0]], LETTER2COL[nxt[1]]

        outs = {}
        for mode in RR.MODES:
            raw = RR.choose(mode, fb, col, vir, ca, cb, na, nb)
            outs[mode] = (raw, describe(raw))

        lookup = RR._te_straight_lookup(fb, ca, cb)

        def reachable_of(desc):
            """For a 'base' pick, is (variant, col) BFS-reachable? None for
            'tuck' picks (tucks are reachable by construction -- TE.enumerate
            only emits reachable=True tuck candidates)."""
            if desc["kind"] != "base":
                return None
            p = lookup.get((desc["variant"], desc["col"]))
            return bool(p is not None and p["reachable"])

        b32_raw, b32 = outs["base32"]
        base32_reachable = reachable_of(b32)

        row = {"commit_index": idx, "t_video": entry["t_video"], "pill": pill, "next": nxt,
               "tape_placement": entry["tape_placement"],
               "shipped_strand20_chosen": proxy[idx]["shipped_strand20"]["chosen"]}

        for mode in RR.MODES:
            raw, d = outs[mode]
            reach_ok = reachable_of(d)
            edges = edges_from_spawn(d["col"])
            hooks_hist = HOOKS_PER_EDGE_HISTORICAL * edges
            # new/corrected hooks arithmetic (reach_root.py live constants)
            hooks_needed_new = RR.DIST_DASEDGE * edges
            # divergence from base32: different (kind, col, orient) tuple
            diverges = (d["kind"], d["col"], d["orient"]) != (b32["kind"], b32["col"], b32["orient"])
            row[mode] = {
                "kind": d["kind"], "col": d["col"], "orient": d["orient"], "val": d["val"],
                "reachable": reach_ok,
                "human_family": d["col"] in HUMAN_FAMILY,
                "edges_from_spawn": edges,
                "hooks_needed_historical_32perEdge": hooks_hist,
                "exceeds40_historical": hooks_hist > WINDOW_HOOKS_HISTORICAL,
                "hooks_needed_corrected_%dperEdge" % RR.DIST_DASEDGE: hooks_needed_new,
                "diverges_from_base32": diverges,
                "n_base_legal": raw.get("n_base_legal"), "n_reach": raw.get("n_reach"),
                "n_within_budget": raw.get("n_within_budget"),
                "fallback_time": raw.get("fallback_time"),
                "fallback_unreachable": raw.get("fallback_unreachable"),
            }
        row["base32_argmax_reachable"] = base32_reachable
        report.append(row)

    out_path = f"{HERE}/tmp_logs/m3case2_raw.json"
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"wrote {out_path}\n")

    # ---- console summary --------------------------------------------------
    modes = list(RR.MODES)
    hdr = f"{'commit':>6} {'base32_reach':>12} " + " ".join(f"{m:>28}" for m in modes)
    print(hdr)
    for row in report:
        line = f"{row['commit_index']:>6} {str(row['base32_argmax_reachable']):>12} "
        for m in modes:
            d = row[m]
            tag = f"{d['kind']}:c{d['col']}{d['orient']} div={int(d['diverges_from_base32'])}"
            line += f"{tag:>28} "
        print(line)

    print("\n=== acceptance check: reachfull2 vs base32-unreachable-argmax boards ===")
    unreach_boards = [r for r in report if r["base32_argmax_reachable"] is False]
    print(f"boards where base32's own argmax is BFS-unreachable: "
          f"{len(unreach_boards)}/{len(report)} "
          f"(commits {[r['commit_index'] for r in unreach_boards]})")
    for mode in ("reachfull", "reachfull2", "reachfull2t"):
        n_div = sum(1 for r in unreach_boards if r[mode]["diverges_from_base32"])
        n_still_unreach = sum(1 for r in unreach_boards
                              if r[mode]["kind"] == "base" and r[mode]["reachable"] is False)
        print(f"  {mode:>12}: diverges from base32 on {n_div}/{len(unreach_boards)}; "
              f"still picks an UNREACHABLE base placement on {n_still_unreach}/{len(unreach_boards)}"
              f"  <-- must be 0 for the fix to be confirmed")

    print("\n=== hooks_needed: historical (32/edge) vs corrected "
          f"({RR.DIST_DASEDGE}/edge) window ===")
    for row in report:
        b = row["base32"]
        print(f"  commit {row['commit_index']}: base32 hooks_needed "
              f"historical={b['hooks_needed_historical_32perEdge']} "
              f"(exceeds40={b['exceeds40_historical']})  "
              f"corrected={b['hooks_needed_corrected_%dperEdge' % RR.DIST_DASEDGE]}")

    print("\n=== reach32t / reachfull2t divergence + within-budget summary ===")
    for mode in ("reach32t", "reachfull2t"):
        n_div = sum(1 for r in report if r[mode]["diverges_from_base32"])
        print(f"  {mode:>12}: diverges from base32 on {n_div}/{len(report)}")
        for r in report:
            d = r[mode]
            print(f"    commit {r['commit_index']}: kind={d['kind']} col={d['col']} "
                  f"orient={d['orient']} n_reach={d['n_reach']} "
                  f"n_within_budget={d['n_within_budget']} "
                  f"fallback_time={d['fallback_time']} fallback_unreachable={d['fallback_unreachable']}")

    print("\n=== human-family ({0,6,7}) match, all 6 modes ===")
    for row in report:
        line = f"  commit {row['commit_index']}: "
        line += " ".join(f"{m}={'Y' if row[m]['human_family'] else 'n'}" for m in modes)
        print(line)


if __name__ == "__main__":
    main()
