#!/usr/bin/env python3
"""build_report.py -- final Hunt A deliverable assembly.

Reads the finished census (census/census_results.jsonl + CENSUS_DONE) and
census/failures_with_boards.json (from replay_failures.py), computes the
slowest-decile via adversary_harness.classify_slow, pulls opening-board +
pill-prefix signature features for the slow-decile seeds (cheap, no replay)
and for a matched random control group of ordinary (clear, non-slow) seeds,
and writes:
  census/TAIL_SEEDS.json   -- topout + stall + slow-decile seeds, each with
                              its board material (fatal_board for topout/
                              stall, opening_board+features for all three)
  SEED_CENSUS.md            -- the human-readable report
"""
from __future__ import annotations

import sys
import os
import json
import random
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import adversary_harness as AH
import signature as SG

CENSUS_DIR = os.path.join(HERE, "census")
RESULTS_PATH = os.path.join(CENSUS_DIR, "census_results.jsonl")
DONE_PATH = os.path.join(CENSUS_DIR, "CENSUS_DONE")
FAILURES_WITH_BOARDS = os.path.join(CENSUS_DIR, "failures_with_boards.json")
TAIL_OUT = os.path.join(CENSUS_DIR, "TAIL_SEEDS.json")
REPORT_OUT = os.path.join(HERE, "SEED_CENSUS.md")  # experiments/adversary/SEED_CENSUS.md, per task spec

CONTROL_RNG_SEED = 20260806111  # fixed, logged
SLOW_DECILE = 0.9
FEATURE_KEYS = [
    "n_virus", "min_row_near_spawn", "n_virus_top4",
    "pill_color_entropy_first20", "n_mono_pills_first20",
    "longest_color_run_first20", "n_distinct_colors_first10pills",
]


def load_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean_std(xs):
    xs = list(xs)
    if not xs:
        return (float("nan"), float("nan"), 0)
    m = st.mean(xs)
    s = st.pstdev(xs) if len(xs) > 1 else 0.0
    return (m, s, len(xs))


def compare_groups(tail_feats, control_feats, label):
    lines = [f"### {label} (n_tail={len(tail_feats)}, n_control={len(control_feats)})", ""]
    if not tail_feats:
        lines.append("_no seeds in this group -- nothing to compare_")
        return lines
    lines.append("| feature | tail mean±sd | control mean±sd | |Δ|/pooled_sd | flag |")
    lines.append("|---|---|---|---|---|")
    n_flags = 0
    for k in FEATURE_KEYS:
        t_m, t_s, t_n = mean_std(f[k] for f in tail_feats)
        c_m, c_s, c_n = mean_std(f[k] for f in control_feats)
        pooled = ((t_s ** 2 + c_s ** 2) / 2) ** 0.5 if (t_s or c_s) else 0.0
        z = abs(t_m - c_m) / pooled if pooled > 1e-9 else float("inf") if t_m != c_m else 0.0
        flag = "CANDIDATE" if (pooled > 1e-9 and z > 1.5) else ""
        if flag:
            n_flags += 1
        lines.append(f"| {k} | {t_m:.3f}±{t_s:.3f} | {c_m:.3f}±{c_s:.3f} | "
                      f"{z:.2f} | {flag} |")
    # virus color histogram (vector feature, compare per-color)
    for ci, cname in enumerate(("red", "yellow", "blue")):
        t_m, t_s, _ = mean_std(f["virus_color_hist"][ci] for f in tail_feats)
        c_m, c_s, _ = mean_std(f["virus_color_hist"][ci] for f in control_feats)
        pooled = ((t_s ** 2 + c_s ** 2) / 2) ** 0.5 if (t_s or c_s) else 0.0
        z = abs(t_m - c_m) / pooled if pooled > 1e-9 else 0.0
        flag = "CANDIDATE" if (pooled > 1e-9 and z > 1.5) else ""
        if flag:
            n_flags += 1
        lines.append(f"| virus_color_{cname} | {t_m:.3f}±{t_s:.3f} | {c_m:.3f}±{c_s:.3f} | "
                      f"{z:.2f} | {flag} |")
    lines.append("")
    if n_flags == 0:
        lines.append(f"**NO SIGNATURE**: no feature in {label} differs from the matched "
                      f"control by >1.5 pooled-sd. Honest negative -- {len(tail_feats)} "
                      f"tail seeds vs {len(control_feats)} matched controls.")
    else:
        lines.append(f"**{n_flags} CANDIDATE flag(s) present** -- "
                      "these are >1.5-pooled-sd gaps at this n, NOT a confirmed effect. "
                      "Per house rule, a candidate is not a finding until it passes a "
                      "transfer filter (independent seed batch / larger n).")
    lines.append("")
    return lines


def main():
    if not os.path.exists(DONE_PATH):
        print("[build_report] CENSUS_DONE marker missing -- census not finished. Aborting.")
        sys.exit(1)
    done = json.load(open(DONE_PATH))
    rows = load_jsonl(RESULTS_PATH)
    n = len(rows)
    print(f"[build_report] loaded {n} census rows", flush=True)

    counts = {"clear": 0, "topout": 0, "stall": 0}
    for r in rows:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    n_dies_ahead = sum(1 for r in rows if r.get("dies_ahead"))

    slow_seeds = AH.classify_slow(rows, decile=SLOW_DECILE)
    failure_seeds = {r["seed"] for r in rows if r["result"] in ("topout", "stall")}
    print(f"[build_report] {len(failure_seeds)} failure seeds, {len(slow_seeds)} slow-decile seeds "
          f"(overlap={len(failure_seeds & slow_seeds)})", flush=True)

    # ---- pull board material for the tail ----
    failures_detail = {}
    if os.path.exists(FAILURES_WITH_BOARDS):
        for rec in json.load(open(FAILURES_WITH_BOARDS)):
            failures_detail[rec["seed"]] = rec
    missing_replay = failure_seeds - set(failures_detail.keys())
    if missing_replay:
        print(f"[build_report] WARNING: {len(missing_replay)} failure seeds have no replay "
              f"record (run replay_failures.py first) -- proceeding without their fatal boards",
              flush=True)

    slow_only = slow_seeds - failure_seeds
    print(f"[build_report] pulling opening-board+pill signature for {len(slow_only)} "
          f"slow-only seeds (cheap, no replay)...", flush=True)
    slow_detail = {}
    for s in sorted(slow_only):
        rec = SG.opening_and_pills(s, n_pills=20)
        feats = SG.features_from_opening(rec)
        pills_row = next((r for r in rows if r["seed"] == s), None)
        slow_detail[s] = {
            "seed": s, "result": "clear", "pills": pills_row["pills"] if pills_row else None,
            "viruses_left": 0, "dies_ahead": False, "fatal_board": None,
            "opening_board": rec["opening_board"], "pills_prefix": rec["pills_prefix"],
            "features": feats,
        }

    # ---- matched control group: ordinary clear, non-slow seeds ----
    tail_all = failure_seeds | slow_seeds
    normal_pool = [r["seed"] for r in rows if r["result"] == "clear" and r["seed"] not in tail_all]
    control_n = min(len(tail_all) * 2, len(normal_pool)) if tail_all else min(500, len(normal_pool))
    control_seeds = random.Random(CONTROL_RNG_SEED).sample(normal_pool, control_n) if normal_pool else []
    print(f"[build_report] pulling signature for {len(control_seeds)} matched-control seeds...", flush=True)
    control_feats = []
    for s in control_seeds:
        rec = SG.opening_and_pills(s, n_pills=20)
        control_feats.append(SG.features_from_opening(rec))

    # ---- assemble TAIL_SEEDS.json ----
    tail_out = []
    for s in sorted(failure_seeds):
        rec = failures_detail.get(s)
        if rec is None:
            r = next(r for r in rows if r["seed"] == s)
            tail_out.append({"seed": s, "result": r["result"], "pills": r["pills"],
                              "viruses_left": r["viruses_left"], "dies_ahead": r["dies_ahead"],
                              "fatal_board": None, "opening_board": None, "pills_prefix": None,
                              "features": None, "tail_reason": r["result"],
                              "note": "replay_failures.py not run for this seed"})
            continue
        rec = dict(rec)
        rec["tail_reason"] = rec["result"]
        tail_out.append(rec)
    for s in sorted(slow_only):
        rec = dict(slow_detail[s])
        rec["tail_reason"] = "slow"
        tail_out.append(rec)
    for s in sorted(slow_seeds & failure_seeds):
        # already emitted under failure_seeds above -- mark dual membership
        for rec in tail_out:
            if rec["seed"] == s:
                rec["tail_reason"] = rec["result"] + "+slow"

    with open(TAIL_OUT, "w") as f:
        json.dump(tail_out, f, indent=2)
    print(f"[build_report] wrote {TAIL_OUT} ({len(tail_out)} tail seeds)", flush=True)

    # ---- feature comparison ----
    bad_end_feats = [failures_detail[s]["features"] for s in sorted(failure_seeds)
                      if s in failures_detail]
    slow_feats_all = [failures_detail[s]["features"] if s in failures_detail else slow_detail[s]["features"]
                       for s in sorted(slow_seeds)]
    combined_feats = bad_end_feats + [slow_detail[s]["features"] for s in sorted(slow_only)]

    md = []
    md.append("# SEED CENSUS -- Hunt A (solo play, no pressure, strand20 champion)")
    md.append("")
    md.append(f"Champion: fast_rtl_x.variant(\"winner\") leaf + eval47/terms47.g_stranded, "
              f"ws=20, root-only -- ab47.py::_choose_base(wt=0, ws=20) bit-exact, via "
              f"eval47/reach_root.py::choose_base32. Level {AH.LEVEL}. No pressure model "
              f"(clean solo play). Failure taxonomy: house definitions "
              f"(TOPOUT/DIES-AHEAD/STALL/SLOW), not invented.")
    md.append("")
    md.append("## Run parameters")
    md.append("")
    md.append(f"- Seed order: `range(65536)` shuffled once under fixed RNG seed "
              f"`{done.get('shuffle_rng_seed')}` -- any prefix consumed is a genuine uniform "
              f"sample of the FULL 16-bit seed space, not just low seed values.")
    md.append(f"- Workers: {done.get('workers')}, wave size: {done.get('wave')}, "
              f"warmup (untimed): {done.get('warmup_seeds')} seeds")
    md.append(f"- Wall-clock budget: {done.get('budget_seconds', 0)/3600:.2f}h "
              f"(measured elapsed: {done.get('elapsed_s', 0)/3600:.2f}h)")
    md.append(f"- **n = {n}** seeds played ({n/AH.SEED_SPACE:.2%} of the {AH.SEED_SPACE}-seed space)")
    rate = n / done.get('elapsed_s', 1) if done.get('elapsed_s') else float('nan')
    md.append(f"- Measured throughput this run: {rate:.3f} games/sec "
              f"(box was concurrently running other agents' jobs -- see honesty note below; "
              f"this is LOWER than the harness's isolated calibration of 1.421 games/sec "
              f"measured earlier at `census/../throughput_run.log`)")
    md.append("")
    md.append("## Outcome distribution")
    md.append("")
    md.append("| result | n | rate |")
    md.append("|---|---|---|")
    for k in ("clear", "topout", "stall"):
        c = counts.get(k, 0)
        md.append(f"| {k} | {c} | {c/n:.4%} |" if n else f"| {k} | {c} | n/a |")
    md.append(f"| **DIES_AHEAD** (topout, viruses_left<=12) | {n_dies_ahead} | "
              f"{n_dies_ahead/n:.4%} |" if n else f"| DIES_AHEAD | {n_dies_ahead} | n/a |")
    md.append(f"| **SLOW** (worst decile of pills-to-clear, decile={SLOW_DECILE}) | "
              f"{len(slow_seeds)} | {len(slow_seeds)/max(1,counts.get('clear',0)):.2%} of clears |")
    md.append("")
    if counts.get("clear", 0):
        clears = sorted(r["pills"] for r in rows if r["result"] == "clear")
        md.append(f"Pills-to-clear over {len(clears)} clears: min={clears[0]}, "
                  f"median={st.median(clears)}, p90={clears[int(0.9*len(clears))]}, "
                  f"max={clears[-1]}.")
        md.append("")

    md.append("## The tail")
    md.append("")
    md.append(f"- **{len(failure_seeds)}** seeds ended TOPOUT or STALL (the true bad-end tail).")
    md.append(f"- **{len(slow_seeds)}** seeds are in the worst decile of pills-to-clear "
              f"({len(slow_seeds & failure_seeds)} of those are ALSO bad-ends -- n/a since "
              f"bad-ends aren't in the 'clear' pool classify_slow draws from, so this is "
              f"always 0 by construction).")
    md.append(f"- Full detail (fatal board for topout/stall, opening board + pill prefix for "
              f"all three) is in `census/TAIL_SEEDS.json` ({len(tail_out)} records).")
    md.append("")

    md.append("## Structure check: do tail seeds share a signature?")
    md.append("")
    md.append("Comparing each tail sub-population's OPENING virus layout + first-20-pill-half "
              "color stream against a matched random control drawn from ordinary (clear, "
              "non-slow) seeds in the SAME census run, same size class. `|Δ|/pooled_sd > 1.5` "
              "is flagged CANDIDATE only -- not a claim of effect at this n.")
    md.append("")
    md.extend(compare_groups(bad_end_feats, control_feats, "TOPOUT+STALL vs control"))
    md.extend(compare_groups(slow_feats_all, control_feats, "SLOW-decile vs control"))
    md.extend(compare_groups(combined_feats, control_feats, "Combined tail (bad-end ∪ slow) vs control"))

    md.append("## Honesty notes")
    md.append("")
    md.append("- This box ran other agents' CPU-heavy jobs (search_adversary.py, "
              "death_corpus.py, both at up to 6 workers each) concurrently with this census "
              "for at least part of the run -- observed throughput is below the isolated "
              "calibration and is reported as MEASURED, not assumed.")
    md.append(f"- n={n} is {'the FULL' if n >= AH.SEED_SPACE else 'a'} seed space sample; "
              f"if n < {AH.SEED_SPACE} this is a partial census bounded by the {done.get('budget_seconds',0)/3600:.1f}h "
              "wall-clock budget, not the full 65536-seed space (full census would take "
              f"~{AH.SEED_SPACE/max(rate,1e-9)/3600:.1f}h at the rate measured in THIS run).")
    md.append("- A candidate flag above is not a finding until it survives an independent "
              "seed batch (transfer filter) -- not attempted in this task's scope.")
    md.append("")

    with open(REPORT_OUT, "w") as f:
        f.write("\n".join(md))
    print(f"[build_report] wrote {REPORT_OUT}", flush=True)

    summary = {
        "n": n, "counts": counts, "n_dies_ahead": n_dies_ahead,
        "n_failure_seeds": len(failure_seeds), "n_slow_seeds": len(slow_seeds),
        "n_tail_total": len(tail_out), "rate_measured": rate,
        "elapsed_s": done.get("elapsed_s"),
    }
    print("SUMMARY_JSON " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
