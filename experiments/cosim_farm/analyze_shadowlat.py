#!/usr/bin/env python3
"""Shadow-price the copro's per-decision search cost against the game's real-time
budgets, from the report-only `lat` field game.py now emits (one entry per decision:
[clocks, entry_row, max_h, post_garbage, h_hit]).

The capture stores RAW co-sim clocks on purpose: the verilated sim ticks clk and
clk_cpu in lockstep (48 master clocks per NES CPU cycle) while real silicon runs the
copro on its own 54.669 MHz async tap -- the two domains differ 1.57x. Conversion
therefore happens HERE, at analysis time, and every number is reported in BOTH
domains:

    silicon frames      = clocks / 909,650        (54.669e6 / 60.0988 NTSC fps)
    sim-lockstep frames = clocks / (48 * 29,780.5) (master clocks per NES frame)

Budgets priced against:

  (a) FALL BUDGET -- at L11 the capsule falls at 13 frames/row (soft-drop 2 f/row,
      not used: 13 f/row is the time the driver gets for free before the pill would
      land on its own). A decision is "late vs fall" when its frames exceed
      13 * entry_row, the fall time from the spawn row (row 0) to the entry row the
      search itself chose. entry_row == -1 (the illegal-placement topout path, where
      nothing was applied) is excluded and counted separately.

  (b) GARBAGE WINDOW -- for decisions flagged post_garbage=1 (made at the
      release+settle edge of a bursty injection), the measured window is
      264 - 16*h frames where h = h_hit, the SHALLOWEST PRE-garbage stack height
      among the VOLLEY'S OWN target columns (game.garbage_hit_h, #124). The window
      is set by the tile that falls furthest, so it is a MIN, of the heights the
      tiles fell ONTO -- not a max, and not the post-settle heights. A decision is
      "late vs window" when its frames exceed that.

      The column set is re-derived from the injector's own model draw, never
      inferred from a board difference: garbage that lands in a column which then
      CLEARS grows in neither height nor occupancy, so any inferred set silently
      drops the binding column and takes the min over the survivors. That error
      hides in clear-triggering volleys -- exactly the longest windows.

      h_hit == H_HIT_UNKNOWN (-1) means no column was targeted at all. Once a volley
      has fired this cannot happen (a non-zero cell count implies a non-empty draw),
      so the skip below is defensive, not an expected path. It exists because an
      unguarded -1 scores as 264 + 16 = 280 f, longer than the physical maximum of
      264, and does so silently. Such a release stays in n_post_garbage (the release
      denominator) and is counted in n_window_unscorable. A NON-ZERO
      n_window_unscorable is therefore a signal to go look at the injector, not a
      routine exclusion to skim past.

      FIDELITY CEILING (filed separately, not a defect in this file): bursty_model
      draws random distinct columns, while the ROM releases maximally spread sets
      ({c, c+4} etc., checkReleaseAttack $9C01). Spread sets find a shallow column
      more often, so the real h_min is LOWER and real windows LONGER than anything
      reported here. Every late_vs_window count below is therefore an upper bound.

      PROVENANCE: jsonl written before #124 carries a DIFFERENT h_hit quantity (max
      over board-inferred hits, post-settle heights) and never emits -1. Such files
      still parse and look entirely healthy, so nothing here can detect them.

      ⚠ A pre-fix file CANNOT BE REPAIRED BY RE-ANALYSIS -- not by this module, not
      by any other. A lat row is exactly five fields, and the corrected h_hit needs
      the volley's COLUMN DRAW plus the PRE-GARBAGE per-column heights. Neither is
      in the file (verified on prestart_pilot.jsonl: 1500/1500 lat rows five wide,
      `garbage` only a scalar cell count). The draw is deterministic in
      (seed, pills_placed), but the release's pills_placed is not recorded either,
      and the heights need board state regardless. Re-running the capture is the
      only route. Read "do not pool" as "the data is not there", NOT as "re-analyze
      more carefully".

      Specifically NOT covered by the S0-A recompute (n=23,792): that screen carries
      no latencies, so it re-derives the h_hit DISTRIBUTION only. Every
      late_vs_window statistic pairs a per-decision latency with a per-release
      window and has never been recomputed by anyone.

All output is COUNTS (n late / n total per band), not adjectives. Constants are
module-level so test_lat_conversion.py can gate them with hand-computed cases.

Denominators differ on purpose: "% of releases" divides by n_post_garbage, while
late_vs_window_pct divides by n_window_scored = n_post_garbage - n_window_unscorable.
"""
from __future__ import annotations

import argparse
import json
import sys

# --- conversion constants (gated by test_lat_conversion.py) --------------------
SILICON_CLOCKS_PER_FRAME = 909650.0       # 54.669e6 / 60.0988, pinned (see gate)
SIM_CLOCKS_PER_FRAME = 48 * 29780.5       # = 1,429,464.0 master clocks / NES frame

# --- budget constants -----------------------------------------------------------
FALL_FRAMES_PER_ROW = 13                  # L11 gravity, frames per row
GARBAGE_WINDOW_BASE = 264                 # measured window = 264 - 16*h (8/8 exact)
GARBAGE_WINDOW_PER_H = 16
H_HIT_UNKNOWN = -1                        # game.garbage_hit_h: no column was targeted

HEIGHT_BANDS = ((0, 4), (5, 8), (9, 12), (13, 99))


def silicon_frames(clocks: float) -> float:
    return clocks / SILICON_CLOCKS_PER_FRAME


def sim_frames(clocks: float) -> float:
    return clocks / SIM_CLOCKS_PER_FRAME


def fall_budget_frames(entry_row: int) -> int:
    """Frames the capsule takes to fall unaided from the spawn row (0) to entry_row."""
    return FALL_FRAMES_PER_ROW * entry_row


def garbage_window_frames(h_hit: int) -> int:
    """Window for a real hit height. Callers must skip h_hit < 0 (see analyze)."""
    if h_hit < 0:
        raise ValueError(
            f"garbage_window_frames called with h_hit={h_hit} (no column targeted); "
            "that release is unscorable, not a 280-frame window")
    return GARBAGE_WINDOW_BASE - GARBAGE_WINDOW_PER_H * h_hit


def band_of(h: int) -> str:
    for lo, hi in HEIGHT_BANDS:
        if lo <= h <= hi:
            return f"{lo}-{hi}" if hi < 99 else f"{lo}+"
    return "?"


def analyze(rows):
    per_domain = {
        "silicon": {"frames": silicon_frames},
        "sim_lockstep": {"frames": sim_frames},
    }
    out = {
        "n_games": 0,
        "n_decisions": 0,
        "n_entry_row_unset": 0,      # illegal-placement path; excluded from (a)
        "n_post_garbage": 0,
        "n_window_unscorable": 0,    # post_garbage rows with h_hit == -1; excluded from (b)
        "clocks": {"max": 0, "sum": 0},
    }
    bands = {}
    for lo, hi in HEIGHT_BANDS:
        bands[f"{lo}-{hi}" if hi < 99 else f"{lo}+"] = {
            "n": 0,
            "n_fall_scored": 0,
            "late_fall": {"silicon": 0, "sim_lockstep": 0},
            "n_post_garbage": 0,
            "n_window_unscorable": 0,
            "late_window": {"silicon": 0, "sim_lockstep": 0},
        }
    for dom in per_domain:
        out[dom] = {
            "late_vs_fall": 0, "n_fall_scored": 0,
            "late_vs_window": 0, "n_window_scored": 0,
            "max_frames": 0.0,
        }
    worst = []
    for r in rows:
        lat = r.get("lat")
        if lat is None:
            continue
        out["n_games"] += 1
        for clocks, entry_row, max_h, post_garbage, h_hit in lat:
            out["n_decisions"] += 1
            out["clocks"]["sum"] += clocks
            out["clocks"]["max"] = max(out["clocks"]["max"], clocks)
            b = bands[band_of(max_h)]
            b["n"] += 1
            fr = {d: per_domain[d]["frames"](clocks) for d in per_domain}
            for d in per_domain:
                out[d]["max_frames"] = max(out[d]["max_frames"], fr[d])
            if entry_row < 0:
                out["n_entry_row_unset"] += 1
            else:
                budget = fall_budget_frames(entry_row)
                b["n_fall_scored"] += 1
                for d in per_domain:
                    out[d]["n_fall_scored"] += 1
                    if fr[d] > budget:
                        out[d]["late_vs_fall"] += 1
                        b["late_fall"][d] += 1
                if fr["silicon"] > budget:
                    worst.append((round(fr["silicon"] - budget, 2), r.get("seed"),
                                  clocks, entry_row, max_h))
            if post_garbage:
                out["n_post_garbage"] += 1
                b["n_post_garbage"] += 1
                if h_hit < 0:
                    # No column targeted (#124) -- unreachable once a volley has
                    # fired. Defensive: stays in the release denominator, scored
                    # against no window.
                    out["n_window_unscorable"] += 1
                    b["n_window_unscorable"] += 1
                else:
                    win = garbage_window_frames(h_hit)
                    for d in per_domain:
                        out[d]["n_window_scored"] += 1
                        if fr[d] > win:
                            out[d]["late_vs_window"] += 1
                            b["late_window"][d] += 1
    out["bands"] = bands
    worst.sort(reverse=True)
    out["worst_fall_overruns_silicon"] = [
        {"overrun_frames": o, "seed": s, "clocks": c, "entry_row": e, "max_h": h}
        for o, s, c, e, h in worst[:10]]
    for d in per_domain:
        n = out[d]["n_fall_scored"]
        nw = out[d]["n_window_scored"]
        out[d]["late_vs_fall_pct"] = round(100.0 * out[d]["late_vs_fall"] / n, 3) if n else None
        out[d]["late_vs_window_pct"] = (
            round(100.0 * out[d]["late_vs_window"] / nw, 3) if nw else None)
        out[d]["max_frames"] = round(out[d]["max_frames"], 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+")
    ap.add_argument("--arm", help="only rows with this arm label")
    ap.add_argument("--json-out", help="write the full report dict here")
    a = ap.parse_args()
    rows = []
    for path in a.jsonl:
        with open(path) as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                r = json.loads(ln)
                if a.arm and r.get("arm") != a.arm:
                    continue
                rows.append(r)
    rep = analyze(rows)
    if a.json_out:
        with open(a.json_out, "w") as fh:
            json.dump(rep, fh, indent=1)
    print(f"games={rep['n_games']} decisions={rep['n_decisions']} "
          f"entry_row_unset(illegal)={rep['n_entry_row_unset']} "
          f"post_garbage={rep['n_post_garbage']} "
          f"window_unscorable(h_hit=-1)={rep['n_window_unscorable']}")
    print(f"clocks: max={rep['clocks']['max']:,} sum={rep['clocks']['sum']:,}")
    for d in ("silicon", "sim_lockstep"):
        r = rep[d]
        print(f"[{d}] late_vs_fall {r['late_vs_fall']}/{r['n_fall_scored']}"
              f" ({r['late_vs_fall_pct']}%)   late_vs_window "
              f"{r['late_vs_window']}/{r['n_window_scored']}"
              f" ({r['late_vs_window_pct']}%)   max_frames={r['max_frames']}")
    print("by max_h band (n / late_fall si / late_fall sim / pg / late_win si):")
    for name, b in rep["bands"].items():
        print(f"  h {name:>5}: n={b['n']:5d} fall_scored={b['n_fall_scored']:5d} "
              f"late_si={b['late_fall']['silicon']:4d} "
              f"late_sim={b['late_fall']['sim_lockstep']:4d}  "
              f"pg={b['n_post_garbage']:3d} "
              f"pg_unscorable={b['n_window_unscorable']:3d} "
              f"late_win_si={b['late_window']['silicon']:3d} "
              f"late_win_sim={b['late_window']['sim_lockstep']:3d}")
    if rep["worst_fall_overruns_silicon"]:
        print("worst silicon fall overruns (frames over budget):")
        for w in rep["worst_fall_overruns_silicon"]:
            print(f"  +{w['overrun_frames']}f seed={w['seed']} clocks={w['clocks']:,} "
                  f"entry_row={w['entry_row']} max_h={w['max_h']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
