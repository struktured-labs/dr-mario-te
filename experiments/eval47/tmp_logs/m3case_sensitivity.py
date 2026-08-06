#!/usr/bin/env python3
"""M3 case study, LATE-START SENSITIVITY (team-lead follow-on to task #60
iteration 2): does a search-latency penalty on the time budget change the
reach32t/reachfull2t story on the 6 real death-board commits?

Motivation (team-lead, 2026-08-05): the corrected DIST_TABLE constants
(DIST_DASEDGE=12, DIST_GRAVROW=30 -- CART_FIX_REPORT.md section 7.6, commit
6e3612d) make a 3-column-edge traverse (36 hooks) fit comfortably inside the
historical ~40-hook window "IF steering starts immediately." But this
program's own reach32t/reachfull2t compute the budget from a SPAWN-TIME
snapshot -- they implicitly assume steering can begin at hook 0. If the
search itself eats hooks before a target is even known (decide-then-steer,
not steer-while-deciding), the EFFECTIVE budget at the moment steering can
actually start is smaller. This script re-derives, for each of the 6 M3
boards, whether a `late_start_hooks` penalty (representing that eaten time)
changes which candidates clear the time budget -- i.e. does the m3-case
zero-divergence result (REACH_ROOT_M3CASE2.md) hold up, or does it flip once
decision latency is accounted for?

Does NOT modify reach_root.py's shipped choosers (reach32t/reachfull2t stay
exactly as validated/committed) -- this is a read-only diagnostic re-scoring
of the SAME candidate data (_scored_base_candidates), swapping in a
late-start-adjusted budget locally.
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
LETTER2COL = {".": 0, "R": 1, "Y": 2, "B": 3}
HUMAN_FAMILY = {0, 6, 7}

# Sensitivity sweep: 0 = the already-shipped/committed reach32t/reachfull2t
# behavior (no penalty); 20 = the team-lead's requested probe point. Extended
# out to 84 (= DIST_DASEDGE * 7, the max possible hooks_available at
# saturation) to actually locate the flip point, not just confirm "not by 40."
LATE_START_SWEEP = (0, 10, 20, 30, 40, 50, 60, 70, 80, 84)


def build_fb(entry):
    L = RR._lazy()
    FB = L["FB"]
    col, vir = [], []
    for row_c, row_v in zip(entry["board_colors"], entry["board_isvirus"]):
        for ch, vch in zip(row_c, row_v):
            col.append(LETTER2COL[ch])
            vir.append(1 if vch == "1" else 0)
    return FB(col, vir, None)


def budget_edges_late(fall_rows, late_start_hooks):
    """Same DIST_TABLE formula as RR._dist_table_budget_edges, but the
    hooks_available is first reduced by `late_start_hooks` (search-latency
    penalty) before comparing -- i.e. recomputed at the hooks level, not the
    edges level, so the floor-at-1-edge rule still applies to the RAW
    (undiscounted) budget, matching DIST_TABLE's own semantics; the penalty
    represents hooks burned BEFORE steering could start, which is a
    hooks-domain quantity."""
    raw_hooks = RR._dist_table_budget_edges(fall_rows) * RR.DIST_DASEDGE
    return max(0, raw_hooks - late_start_hooks)


def main():
    boards = json.load(open(BOARDS_JSON))["boards"]
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

        cands = RR._scored_base_candidates(fb, col, vir, ca, cb, na, nb, RR.WS, RR.TOPK2)
        reach_cands = [c for c in cands if c["reachable"]]

        b32 = RR.choose_base32(col, vir, ca, cb, na, nb)
        b32_var, b32_cc = b32["action"] // 8, b32["action"] % 8

        row = {"commit_index": idx, "n_reach": len(reach_cands),
               "base32_col": b32_cc, "sweep": {}}
        for late in LATE_START_SWEEP:
            timed = [c for c in reach_cands
                     if RR._edges_from_spawn(c["col"]) * RR.DIST_DASEDGE
                        <= budget_edges_late(c["row"], late)]
            if timed:
                best = max(timed, key=lambda c: c["val"])
                pick_col, kind, fell_back = best["col"], "timed-base", False
            elif reach_cands:
                best = max(reach_cands, key=lambda c: c["val"])
                pick_col, kind, fell_back = best["col"], "fallback-reach32", True
            else:
                pick_col, kind, fell_back = b32_cc, "fallback-base32", True
            row["sweep"][late] = {
                "n_within_budget": len(timed), "pick_col": pick_col, "kind": kind,
                "fell_back_to_untimed": fell_back,
                "diverges_from_base32": pick_col != b32_cc,
                "human_family": pick_col in HUMAN_FAMILY,
            }
        report.append(row)

    out_path = f"{HERE}/tmp_logs/m3case_sensitivity_raw.json"
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"wrote {out_path}\n")

    print(f"{'commit':>6} {'base32_col':>10} {'n_reach':>8}  " +
          "  ".join(f"late={l:>3d}" for l in LATE_START_SWEEP))
    for row in report:
        cells = []
        for late in LATE_START_SWEEP:
            s = row["sweep"][late]
            tag = f"c{s['pick_col']}({s['n_within_budget']}/{row['n_reach']})"
            if s["diverges_from_base32"]:
                tag += "*"
            cells.append(f"{tag:>10}")
        print(f"{row['commit_index']:>6} {row['base32_col']:>10} {row['n_reach']:>8}  " +
              "  ".join(cells))
    print("\n(* = diverges from base32 at that late-start penalty; "
          "n_within_budget/n_reach shown in parens)")

    print("\n=== does ANY late-start penalty in the sweep flip a board from "
          "'time filter agrees with reach32t/reachfull2t (0 divergence)' to "
          "'time filter would exclude the far pick'? ===")
    any_flip = False
    for row in report:
        base_late0 = row["sweep"][0]["pick_col"]
        for late in LATE_START_SWEEP[1:]:
            if row["sweep"][late]["pick_col"] != base_late0:
                any_flip = True
                print(f"  commit {row['commit_index']}: late=0 picks col{base_late0}, "
                      f"late={late} picks col{row['sweep'][late]['pick_col']} "
                      f"(n_within_budget {row['sweep'][late]['n_within_budget']}/{row['n_reach']})")
    if not any_flip:
        print("  NO FLIP on any of the 6 boards at any penalty in "
              f"{LATE_START_SWEEP} hooks. The time filter's pick is identical "
              "regardless of the late-start penalty tested.")


if __name__ == "__main__":
    main()
