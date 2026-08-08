"""Cache the shadow-latency pilot summary for player_stats_notebook.py.

Imports the gated analyzer (`shadowlat_analyze.py`, task #92) and reuses ITS budget
functions and constants rather than restating them -- restating is how a 1.57x domain
error travels. Refuses to write unless the analyzer's own selftest passes, so a cached
summary can never outlive the gate that certifies it.

The pilot JSONL lives on /mnt/data, outside the worktree; this produces the small
committed artifact the notebook reads.
"""
import json
import os
import statistics as st
import sys

ANALYZER_DIR = "/home/struktured/projects/dr-mario-prestart-wt/experiments/prestart"
PILOT = "/mnt/data/drmario_cosim/results/prestart_pilot.jsonl"
OUT = ("/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/results/"
       "shadowlat_pilot_summary.json")

sys.path.insert(0, ANALYZER_DIR)
import shadowlat_analyze as S  # noqa: E402


def pct(vals, p):
    vals = sorted(vals)
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return vals[f] if f == c else vals[f] + (vals[c] - vals[f]) * (k - f)


def summarize(decisions, clocks_per_frame):
    """Fall-budget overruns and per-decision latency, in one clock domain."""
    frames = [d["clocks"] / clocks_per_frame for d in decisions]
    late = [
        d for d in decisions
        if d["entry_row"] >= 0
        and d["clocks"] / clocks_per_frame > S.fall_budget_frames(d["entry_row"])
    ]
    usable = [d for d in decisions if d["entry_row"] >= 0]
    band = [d for d in usable if 9 <= d["max_h"] <= 12]
    band_late = [
        d for d in band
        if d["clocks"] / clocks_per_frame > S.fall_budget_frames(d["entry_row"])
    ]
    return {
        "n_decisions": len(decisions),
        "median_frames": st.median(frames),
        "p90_frames": pct(frames, 0.90),
        "median_seconds": st.median(frames) / S.NTSC_FPS,
        "late_pct": 100.0 * len(late) / len(usable),
        "late_n": len(late),
        "band_9_12_late_pct": 100.0 * len(band_late) / len(band) if band else None,
        "band_9_12_n": len(band),
    }


def window_miss(decisions, clocks_per_frame, h_min=13):
    """Post-garbage decisions that miss the 264-16h pre-spawn window at h>=h_min."""
    pg = [d for d in decisions if d["post_garbage"] and d["h_hit"] >= h_min]
    miss = [
        d for d in pg
        if d["clocks"] / clocks_per_frame > S.window_budget_frames(d["h_hit"])
    ]
    return {"n": len(pg), "miss": len(miss),
            "miss_pct": 100.0 * len(miss) / len(pg) if pg else None}


def main():
    # selftest() returns an EXIT CODE (0 = pass), not a bool -- `not S.selftest()`
    # inverts it and treats a passing gate as a failure.
    if S.selftest() != 0:
        print("ANALYZER SELFTEST FAILED -- refusing to cache", file=sys.stderr)
        return 1

    decisions, diag = S.load([PILOT])
    # diag rows are tuples: (path, state, n_rows, n_lat, n_decisions)
    path, state, n_rows, n_lat, n_dec = diag[0]
    if state != "ok":
        print(f"pilot file state={state} -- refusing to cache", file=sys.stderr)
        return 1

    out = {
        "source_jsonl": PILOT,
        "analyzer": os.path.join(ANALYZER_DIR, "shadowlat_analyze.py"),
        "analyzer_selftest": "PASS",
        "n_games": n_rows,
        "domain_ratio": S.SIM_CLOCKS_PER_FRAME / S.SILICON_CLOCKS_PER_FRAME,
        "silicon": summarize(decisions, S.SILICON_CLOCKS_PER_FRAME),
        "sim_lockstep": summarize(decisions, S.SIM_CLOCKS_PER_FRAME),
        "window_miss_h13plus_silicon": window_miss(decisions, S.SILICON_CLOCKS_PER_FRAME),
        "window_miss_h13plus_sim": window_miss(decisions, S.SIM_CLOCKS_PER_FRAME),
        "arm": "champion s20b, drop+bursty",
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {OUT}")
    for dom in ("silicon", "sim_lockstep"):
        s = out[dom]
        print(f"  {dom:13s} med {s['median_frames']:.1f} f  p90 {s['p90_frames']:.1f} f  "
              f"late {s['late_pct']:.1f}%  band9-12 {s['band_9_12_late_pct']:.1f}%")
    w = out["window_miss_h13plus_silicon"]
    print(f"  window miss h>=13 (silicon): {w['miss']}/{w['n']} = {w['miss_pct']:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
