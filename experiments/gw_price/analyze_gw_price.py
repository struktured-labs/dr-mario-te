#!/usr/bin/env python3
"""Conditional-split analysis for the GW pricing run (PREREG_GW_PRICE §5-§6).

Reads the farm JSONL, emits the operating-point table, ordering control, the
P(completes|h) x d(h) product, the MDE statement, and the routed verdict.

The verdict router is a pure function over a summary table so G6 can drive it
with synthetic fixtures (gate-standard: analysis code must be shown to
discriminate too).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

H_BANDS = (("h<=7", 0, 7), ("h8-10", 8, 10), ("h11-13", 11, 13),
           ("h>=14", 14, 99), ("h=-1", -1, -1))
MDE_PP = 0.84                     # H12-scale endpoint MDE (PREREG_S0B_REFORK §1)
H12_GAMES = 9000
NTSC_FPS = 60.0988
POCKET_HZ = 54.669358e6
POCKET_CYC_PER_F = POCKET_HZ / NTSC_FPS       # 909,652.11 — derived, not quoted
MISTER_RATIO = 1.57
DEEPEN_COST_MULT = 3.0            # base + 2-candidate 1-ply deepening (spec)


def load(path):
    rows = [json.loads(l) for l in open(path)]
    by = {}
    for r in rows:
        by[(r["seed"], r["arm"])] = r
    return by


def paired(by, arm, seeds):
    """Per-seed paired deltas (arm - base). Returns (diverged, zero_ok, rows)."""
    out = []
    for s in seeds:
        a, b = by.get((s, arm)), by.get((s, "base"))
        if a is None or b is None:
            continue
        trig = max(a["n_iv"], 0)
        d = {"seed": s, "n_iv": trig,
             "d_vc": a["viruses_cleared"] - b["viruses_cleared"],
             "d_won": a["won"] - b["won"],
             "d_da": a["dies_ahead"] - b["dies_ahead"],
             "d_pills": a["pills"] - b["pills"],
             "h_first": (a["ivs"][0]["h_hit"] if a["ivs"] else None)}
        out.append(d)
    diverged = [d for d in out if d["n_iv"] > 0]
    zeros = [d for d in out if d["n_iv"] == 0]
    zero_ok = all(d["d_vc"] == 0 and d["d_won"] == 0 and d["d_pills"] == 0
                  for d in zeros)
    return diverged, zero_ok, out


def boot_ci(xs, n=10000, seed=1):
    import random
    if not xs:
        return (float("nan"), float("nan"), float("nan"))
    rng = random.Random(seed)
    m = sum(xs) / len(xs)
    means = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return (m, means[int(0.025 * n)], means[int(0.975 * n) - 1])


def p_complete_by_h(costs_path="/mnt/data/drmario_cosim/results/prestart_pilot.jsonl"):
    """P(DEEPEN_COST_MULT x cost <= W(h)) from the banked 1,500 per-decision
    copro-cycle costs, both clock domains."""
    costs = []
    for line in open(costs_path):
        r = json.loads(line)
        for lat in r.get("lat", []):
            costs.append(int(lat[0]))
    out = {}
    for h in range(0, 17):
        w_frames = 264 - 16 * h
        for dom, cyc_per_f in (("pocket", POCKET_CYC_PER_F),
                               ("mister", POCKET_CYC_PER_F * MISTER_RATIO)):
            budget = w_frames * cyc_per_f
            fit = sum(1 for c in costs if DEEPEN_COST_MULT * c <= budget)
            out.setdefault(h, {})[dom] = fit / len(costs)
    out["n_costs"] = len(costs)
    return out


def band_of(h):
    for name, lo, hi in H_BANDS:
        if lo <= h <= hi:
            return name
    return "h=-1"


def route_verdict(t):
    """PREREG §6 router. `t` is the summary dict (pure function — G6 drives it
    with synthetic fixtures)."""
    if t["void_reason"]:
        return "VOID", t["void_reason"]
    if not t["ordering_green"]:
        return ("INDETERMINATE",
                "ordering control not green — deepen sign not read")
    lo, pt, hi = t["d_vc_ci_lo"], t["d_vc_mean"], t["d_vc_ci_hi"]
    if hi <= 0:
        return "NO-GO", "deepen CI upper <= 0"
    if t["proj_pp_hi"] < MDE_PP:
        return ("NO-GO",
                f"projected full-N effect even at CI upper "
                f"({t['proj_pp_hi']:.3f} pp) < MDE {MDE_PP} pp")
    if lo > 0 and t["proj_pp_point"] >= MDE_PP:
        return "GO", "CI lower > 0 and projected effect >= MDE"
    return "INDETERMINATE", "CI includes 0 or projection below MDE at point"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--farm", default=os.path.join(HERE, "out", "farm.jsonl"))
    ap.add_argument("--prescreen", default=os.path.join(
        HERE, "out", "prescreen_52100.jsonl.summary.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out",
                                                  "pricing_verdict.json"))
    a = ap.parse_args()
    by = load(a.farm)
    ps = json.load(open(a.prescreen))
    n1 = ps["N1_seeds"]
    n2 = ps["N2_seeds"]

    res = {"farm": a.farm}
    void = []

    # pairing integrity + arm tables
    tabs = {}
    for arm, seeds in (("deepen", n1), ("rand", n2), ("worst", n2)):
        div, zok, allrows = paired(by, arm, seeds)
        if not zok:
            void.append(f"nonzero delta on an untriggered seed ({arm})")
        m, lo, hi = boot_ci([d["d_vc"] for d in div])
        tabs[arm] = {"n_seeds": len(allrows), "n_diverged": len(div),
                     "d_vc_mean": m, "d_vc_ci": [lo, hi],
                     "d_won_mean": (sum(d["d_won"] for d in div) / len(div))
                     if div else float("nan"),
                     "d_da_mean": (sum(d["d_da"] for d in div) / len(div))
                     if div else float("nan"),
                     "d_pills_mean": (sum(d["d_pills"] for d in div) /
                                      len(div)) if div else float("nan"),
                     "rows": div}
    res["arms"] = {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                   for k, v in tabs.items()}

    # PREREG §4: first trigger ply must be common to all arms of a seed
    for s_ in set(k[0] for k in by):
        firsts = {arm: by[(s_, arm)]["ivs"][0]["ply"]
                  for arm in ("base", "deepen", "rand", "worst")
                  if (s_, arm) in by and by[(s_, arm)]["ivs"]}
        if len(set(firsts.values())) > 1:
            void.append(f"first-trigger ply differs across arms at seed {s_}: "
                        f"{firsts}")

    # mirror-mismatch VOID check (PREREG §4: >10% of tie plies)
    n_tie = sum(r["n_tie"] for r in by.values())
    n_mm = sum(r["n_mirror_mismatch"] for r in by.values())
    res["mirror_mismatch"] = {"n_tie": n_tie, "n_mm": n_mm,
                              "rate": n_mm / n_tie if n_tie else 0.0}
    if n_tie and n_mm / n_tie > 0.10:
        void.append(f"mirror mismatch {n_mm}/{n_tie} > 10%")

    dp = tabs["deepen"]
    if dp["n_diverged"] < 10:
        void.append(f"only {dp['n_diverged']} triggered seeds (<10)")

    # ordering control
    ordering_green = False
    if tabs["worst"]["n_diverged"] and tabs["rand"]["n_diverged"]:
        w, r = tabs["worst"], tabs["rand"]
        ordering_green = (w["d_vc_mean"] < r["d_vc_mean"] < 0
                          and w["d_vc_ci"][1] < 0)
    res["ordering"] = {"green": ordering_green,
                       "worst": tabs["worst"]["d_vc_mean"],
                       "rand": tabs["rand"]["d_vc_mean"],
                       "worst_ci": tabs["worst"]["d_vc_ci"]}

    # h-stratified operating-point table (deepen)
    strat = {}
    for name, lo_, hi_ in H_BANDS:
        sub = [d for d in tabs["deepen"]["rows"]
               if d["h_first"] is not None and band_of(d["h_first"]) == name]
        if sub:
            m, lo, hi = boot_ci([d["d_vc"] for d in sub])
            strat[name] = {"n": len(sub), "d_vc_mean": m, "d_vc_ci": [lo, hi]}
    res["strata"] = strat

    # left factor + product
    pc = p_complete_by_h()
    res["p_complete"] = pc
    prod = {}
    for name, lo_, hi_ in H_BANDS:
        if name in strat and name != "h=-1":
            hs = [h for h in range(0, 17) if band_of(h) == name]
            for dom in ("pocket", "mister"):
                p = sum(pc[h][dom] for h in hs) / len(hs)
                prod.setdefault(name, {})[dom] = {
                    "P_complete": p,
                    "effect": p * strat[name]["d_vc_mean"]}
    res["product"] = prod

    # MDE projection (dose from the prescreen: fires per game under v1.1)
    fires_per_game = ps["n_fire_total"] / ps["n_seeds"]
    div = tabs["deepen"]["rows"]
    if div:
        dwon = [d["d_won"] for d in div]
        mw, lw, hw = boot_ci(dwon)
        # weight per-trigger clear delta by the affordability at the observed
        # trigger heights (pocket domain, conservative)
        p_by_seed = [sum(pc[h]["pocket"] for h in range(0, 17)
                         if band_of(h) == band_of(d["h_first"])) /
                     max(1, len([h for h in range(0, 17)
                                 if band_of(h) == band_of(d["h_first"])]))
                     if d["h_first"] is not None and d["h_first"] >= 0 else
                     pc[7]["pocket"] for d in div]
        pbar = sum(p_by_seed) / len(p_by_seed)
    else:
        mw = lw = hw = float("nan")
        pbar = 0.0
    proj_point = fires_per_game * pbar * mw * 100 if div else float("nan")
    proj_hi = fires_per_game * pbar * hw * 100 if div else float("nan")
    res["mde"] = {"fires_per_game": fires_per_game, "p_complete_bar": pbar,
                  "d_won_per_trigger": [mw, lw, hw],
                  "projected_pp_point": proj_point,
                  "projected_pp_ci_hi": proj_hi,
                  "mde_pp": MDE_PP, "h12_games": H12_GAMES}
    # n to resolve measured d_vc at 80% power (paired, normal approx)
    xs = [d["d_vc"] for d in div]
    if len(xs) > 2 and (sum(xs) / len(xs)) != 0:
        m = sum(xs) / len(xs)
        var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
        n_needed = math.ceil(((1.96 + 0.8416) ** 2) * var / (m * m))
        res["mde"]["n_triggered_seeds_for_80pct_power"] = n_needed
    summary = {"void_reason": "; ".join(void),
               "ordering_green": ordering_green,
               "d_vc_mean": dp["d_vc_mean"],
               "d_vc_ci_lo": dp["d_vc_ci"][0],
               "d_vc_ci_hi": dp["d_vc_ci"][1],
               "proj_pp_point": proj_point, "proj_pp_hi": proj_hi}
    verdict, why = route_verdict(summary)
    res["verdict"] = {"verdict": verdict, "why": why, "summary": summary}
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res["verdict"], indent=1))
    print(json.dumps({"arms": res["arms"], "ordering": res["ordering"],
                      "strata": strat, "product": prod, "mde": res["mde"],
                      "mirror_mismatch": res["mirror_mismatch"]}, indent=1))


if __name__ == "__main__":
    main()
