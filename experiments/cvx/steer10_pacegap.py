#!/usr/bin/env python3
"""STEER10 section: the SIM-vs-COUCH PACE GAP. The sim AI (FAIR, LULU race) clears in a median ~149 s; on the couch
(10/05 vs dr. lulu, ANTIBODY_DIST_FAIR) the AI needed ~184-259 s in the games it cleared (and ~265 s at its whole-game
virus pace). Where does the time go?

time to clear = PILLS x SECONDS PER PILL. Decomposed, couch vs sim, from banked rows only (no new games):
  PILLS    couch: silicon pills to clear (the AI's clear games) and pills per game; the brain-only perfect-execution
           replay from p0 on the SAME boards / capsules / garbage (steer10/mech/rep_base_<g>.jsonl, == banked) gives
           the pills the brain alone would have needed -> EXECUTION share of the pill gap; stall pills (act-stalls
           >= 10, couch stall json) vs the sim's stall pills (stuck probe, act >= 10)
  SECONDS  per-pill interval (next spawn - this spawn) on the couch, split by the pill's cascade steps (0 = no clear)
           and whether garbage landed after it, vs the sim race clock (vs_race: BASE_F 45 - 6 (fair tempo) + SOFT_F 2 x
           max(0, 15 - hmax) + CLR_F 40 x lines, garbage free)
  GARBAGE  cells received per game and per minute (couch: her volleys as received; sim: tiles_recv)
  python steer10_pacegap.py [SIM_GLOB ARM_LABEL] -> steer10/pacegap.txt
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.join(HERE, "..", "couch_forensics")
LULU = ("m1g1", "m1g2", "m1g3", "m1g4", "m1g5", "m2g1", "m2g2", "m2g3", "m2g4")


def q(a, ps=(25, 50, 75)):
    a = np.asarray(a, float)
    return "/".join(f"{x:.1f}" for x in np.percentile(a, ps)) if len(a) else "-"


def main(sim_glob, sim_label):
    out = []
    pr = lambda s="": (print(s), out.append(s))
    S = {g["game"]: g for g in json.load(open(os.path.join(CF, "summary_lulu_20261005.json")))["games"]}
    P = [json.loads(l) for l in open(os.path.join(CF, "cases_lulu_20261005_ai_pills.jsonl"))]
    V = [json.loads(l) for l in open(os.path.join(CF, "cases_lulu_20261005_volleys.jsonl"))]
    pr("== COUCH (10/05, AI seat = ANTIBODY_DIST_FAIR, silicon) ==")
    rows = []
    iv = {"noclr": [], "clr1": [], "clr2p": [], "garb": []}
    for g in LULU:
        Pg = sorted([r for r in P if r["game"] == g], key=lambda r: r["k"])
        Q = {q_["p"]: q_ for q_ in map(json.loads, open(os.path.join(CF, f"cases_ai_{g}_lulu_20261005.jsonl")))}
        dur = S[g]["dur_s"] if "dur_s" in S[g] else None
        res = json.load(open(os.path.join(CF, "summary_lulu_20261005.json")))["results"]
        R = {r["game"]: r for r in res}[g]
        dur = R["dur_s"]; ai_clear = S[g]["winner"] == "AI" and S[g]["how"] == "cleared"
        recv = sum(v["recv"]["size"] for v in V if v["game"] == g and v["kind"] == "lulu_send" and v.get("recv"))
        st = json.load(open(os.path.join(CF, f"stall_{g}_lulu_20261005.json"))) if os.path.exists(
            os.path.join(CF, f"stall_{g}_lulu_20261005.json")) else {"stalls": []}
        stall_p = sum(s["pills"] for s in st["stalls"])
        clk = {"act": 0.0, "sim": 0.0, "garb_act": 0.0, "garb_sim": 0.0, "clr_act": 0.0, "clr_sim": 0.0,
               "plain_act": 0.0, "plain_sim": 0.0}
        for a, b in zip(Pg, Pg[1:]):
            dt = b["t_spawn"] - a["t_spawn"]
            gr = Q.get(a["k"], {}).get("garbage_recv", 0) if Q else 0
            # what the sim race clock (vs_race, fair tempo -6) would charge for THIS couch pill
            sim_s = (39.0 + 2.0 * max(0, 15 - a["max_h_before"]) + 40.0 * a["runs"]) / 60.0988
            key = "garb" if gr else ("clr" if a["chain"] else "plain")
            clk["act"] += dt; clk["sim"] += sim_s; clk[key + "_act"] += dt; clk[key + "_sim"] += sim_s
            if gr:
                iv["garb"].append(dt)
            elif a["chain"] == 0:
                iv["noclr"].append(dt)
            elif a["chain"] == 1:
                iv["clr1"].append(dt)
            else:
                iv["clr2p"].append(dt)
        rep = os.path.join(HERE, "steer10", "mech", f"rep_base_{g}.jsonl")
        bo = None
        if os.path.exists(rep):
            r0 = [json.loads(l) for l in open(rep)]
            r0 = [r for r in r0 if r["p0"] == 0]
            if r0:
                bo = (r0[0]["end"], r0[0]["end_p"] + 1 if r0[0]["end"] == "CLEAR" else None, r0[0]["viruses_end"])
        rows.append(dict(g=g, dur=dur, pills=len(Pg), ai_clear=ai_clear, recv=recv, stall_p=stall_p,
                         spp=dur / max(len(Pg), 1), brain=bo, final_ai=R["hud_final_lulu_ai"][1], clk=clk))
        pr(f"  {g}: {'AI CLEARED' if ai_clear else 'AI did not clear (' + str(R['hud_final_lulu_ai'][1]) + ' left)'} "
           f"dur {dur:.1f} s, pills {len(Pg)}, s/pill {dur / len(Pg):.2f}, stall pills (act>=10) {stall_p}, "
           f"garbage cells received {recv} ({60 * recv / dur:.1f}/min), brain-only replay from p0: {bo}")
    cl = [r for r in rows if r["ai_clear"]]
    pr(f"  AI clear games (n={len(cl)}): time {q([r['dur'] for r in cl])} s, pills {q([r['pills'] for r in cl])}, "
       f"s/pill {q([r['spp'] for r in cl])}, stall pills {q([r['stall_p'] for r in cl])}, "
       f"garbage cells {q([r['recv'] for r in cl])}")
    bc = [r for r in cl if r["brain"] and r["brain"][0] == "CLEAR"]
    pr(f"  brain-only perfect execution from p0 (same capsules + garbage), AI clear games: pills to clear "
       f"{[(r['g'], r['brain'][1], r['pills']) for r in cl]} (game, brain-only pills, silicon pills)")
    pr(f"  all 9 games: s/pill {q([r['spp'] for r in rows])}; whole-game pills/min "
       f"{60 * sum(r['pills'] for r in rows) / sum(r['dur'] for r in rows):.1f}")
    pr(f"  per-pill interval (s) p25/50/75: no-clear, no garbage {q(iv['noclr'])} (n={len(iv['noclr'])}); "
       f"1-step clear {q(iv['clr1'])} (n={len(iv['clr1'])}); 2+-step {q(iv['clr2p'])} (n={len(iv['clr2p'])}); "
       f"garbage landed after it {q(iv['garb'])} (n={len(iv['garb'])})")
    pr("")
    pr(f"== SIM ({sim_label}, {sim_glob}) ==")
    R = [json.loads(l) for f in glob.glob(os.path.join(HERE, sim_glob)) for l in open(f)]
    R = [r for r in R if r.get("arm") == sim_label]
    cs = [r for r in R if r["how"] == "clear"]
    st = lambda r: sum(b[2] for b in r["stuck"]["bep"] if b[0] == 1 and b[2] >= 10)
    pr(f"  n={len(R)}, clears {len(cs)}: time to clear {q([r['t_end'] for r in cs])} s, pills {q([r['pills'] for r in cs])}, "
       f"s/pill {q([r['t_end'] / r['pills'] for r in cs])}, mean frames/pill {q([r['mean_f'] for r in cs])}, "
       f"stall pills (act>=10) {q([st(r) for r in cs])}, garbage cells received {q([r['tiles_recv'] for r in cs])} "
       f"({60 * np.sum([r['tiles_recv'] for r in cs]) / np.sum([r['t_end'] for r in cs]):.1f}/min)")
    pr("")
    pr("== DECOMPOSITION (medians; AI clear games on the couch vs sim clears) ==")
    Tc = float(np.median([r["dur"] for r in cl])); Ts = float(np.median([r["t_end"] for r in cs]))
    Nc = float(np.median([r["pills"] for r in cl])); Ns = float(np.median([r["pills"] for r in cs]))
    sc = Tc / Nc; ss = Ts / Ns
    pr(f"  time {Tc:.0f} s couch vs {Ts:.0f} s sim: ratio {Tc / Ts:.2f} = pills {Nc:.0f}/{Ns:.0f} ({Nc / Ns:.2f}) x "
       f"s/pill {sc:.2f}/{ss:.2f} ({sc / ss:.2f})")
    pr(f"  log-share of the gap: pills {np.log(Nc / Ns) / np.log(Tc / Ts):.0%}, seconds per pill "
       f"{np.log(sc / ss) / np.log(Tc / Ts):.0%}")
    if bc:
        pr(f"  of the pill gap, execution (silicon - brain-only on the same boards) = "
           f"{np.median([r['pills'] - r['brain'][1] for r in bc]):.0f} pills median over {len(bc)} clear games "
           f"(brain-only pills {q([r['brain'][1] for r in bc])} vs silicon {q([r['pills'] for r in bc])})")
    pr("  SECONDS: the couch pills re-timed with the SIM race clock (39 + 2 x max(0, 15 - hmax) + 40 x runs frames;"
       " garbage drops cost 0), summed over the AI clear games:")
    K = ("plain", "clr", "garb")
    A_ = {k: sum(r["clk"][k + "_act"] for r in cl) for k in K}; S_ = {k: sum(r["clk"][k + "_sim"] for r in cl) for k in K}
    tot_a = sum(A_.values()); tot_s = sum(S_.values())
    for k, lab in zip(K, ("no clear, no garbage after", "clearing pill (no garbage)", "garbage landed after it")):
        pr(f"    {lab:28s}: couch {A_[k] / len(cl):6.1f} s/game vs sim clock {S_[k] / len(cl):6.1f} s/game -> excess "
           f"{(A_[k] - S_[k]) / len(cl):+6.1f} s/game ({(A_[k] - S_[k]) / max(tot_a - tot_s, 1e-9):.0%} of the per-pill excess)")
    pr(f"    total: couch {tot_a / len(cl):.1f} s/game vs sim clock {tot_s / len(cl):.1f} s/game on the SAME pills "
       f"(excess {(tot_a - tot_s) / len(cl):+.1f} s/game)")
    Tb = np.median([r["brain"][1] for r in bc]) * float(np.median([r["clk"]["sim"] / max(r["pills"] - 1, 1) for r in cl]))
    pr(f"  => couch boards under PERFECT execution and the SIM clock would take ~{Tb:.0f} s (brain-only pills x sim-clock s/pill),"
       f" vs the sim's own median {Ts:.0f} s and silicon's {Tc:.0f} s")
    open(os.path.join(HERE, "steer10", "pacegap.txt"), "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    a = sys.argv[1:] or ["steer8/lulu10_fD_bdepD_*.jsonl", "fD_bdepD~steer"]
    main(a[0], a[1])
