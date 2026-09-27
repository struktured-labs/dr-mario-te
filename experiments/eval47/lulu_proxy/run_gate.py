#!/usr/bin/env python3
"""LULU-PROXY STRIKER GATE (killed-mutant standard).

Four gates, each with a demonstrated KILL (a non-equivalent mutant the
checker must catch).  A checker that has not been shown to FAIL on wrong
input is not evidence (dr-mario-gate-standard-killed-mutants.md).

  G1 TIMING PREDICATE  check_release_log over a 20-game probe.
       PASS  real striker            -> 0 violations
       KILL  inverted      (h<=2)    -> violations
       KILL  inverted_lt   (h<H)     -> violations  (the literal inversion)
       KILL  random        (p=0.15)  -> violations
       KILL  ignores_bank  (fire at earn, never bank) -> violations
       KILL  blind control's own log -> violations
  G2 PAIRING           check_pairing: same seed => same virus layout (md5 of
       the opening color+virus planes), same capsule stream, and -- for a
       striker-vs-striker rerun -- the same banked volley sequence
       (pill indices + sizes + count).
       PASS  striker rerun vs striker  (all three)
       PASS  striker vs blind          (layout + capsule stream)
       KILL  pair_break: game seed +2 in one arm (+2, NOT +1: seeds 2k and
             2k+1 are the SAME game, dr-mario-seed-space-is-32767.md, so a
             +1 mutant would be EQUIVALENT on even seeds)
  G3 MATCHED CONTROL   check_matched_volume: per seed the blind schedule
       carries the striker's exact volley COUNT and TOTAL CELLS.
       PASS  real schedule builder
       KILL  drop_one=True (silently drops the largest volley)
  G4 REGRESSION        blind-bursty through the NEW play() must reproduce
       the OLD pressure_rig.play() bursty arm EXACTLY on 20 seeds (all
       outcome fields).  Comparator kill: the same comparison against the
       old rig at ws=0 must FAIL (so "identical" is not vacuous).

Usage:  run_gate.py [--n 20] [--H 6] [--workers 3] [--out results/gate]
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_striker_ab as R    # noqa: E402
import striker_model as SM    # noqa: E402
import pressure_rig as PR     # noqa: E402

LOG = []


def say(msg=""):
    print(msg, flush=True)
    LOG.append(msg)


def _viol(rows, H, TO):
    out = []
    for s in sorted(rows):
        out += [f"seed {s}: {v}" for v in
                SM.check_release_log(rows[s]["release_log"], H, TO)]
    return out


def _nrel(rows):
    return sum(len(rows[s]["release_log"]) for s in rows)


def _release_keys(rows):
    return {s: sorted(ev["pill"] for ev in rows[s]["release_log"])
            for s in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--H", type=int, default=6)
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=SM.BANK_TIMEOUT_PILLS)
    ap.add_argument("--height-metric", default="scaffold",
                    choices=SM.HEIGHT_METRICS)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "gate"))
    a = ap.parse_args()
    W = min(a.workers, R.MAX_WORKERS)
    H, TO, LV, HM = a.H, a.timeout, a.level, a.height_metric

    seeds = R._seed_list(a.n)
    model = R._load_model()
    started = datetime.datetime.now().isoformat(timespec="seconds")
    say(f"=== LULU-PROXY STRIKER GATE  {started} ===")
    say(f"seeds n={len(seeds)} (seed 1 excluded): {seeds}")
    say(f"H={H} timeout={TO} metric={HM} level={LV} workers={W} "
        f"decider=champion (wt={R.CHAMPION_WT} ws={R.CHAMPION_WS})")
    say(f"bursty-v1 fit: n_matches={model.n_matches} "
        f"n_volleys={model.n_volleys} n_clears={model.n_clears}")
    say()

    verdicts = {}
    killed = 0

    def arm(mutant="none", model_kind="striker", schedules=None,
            seed_offset=0, tag=""):
        return R.run_arm(LV, seeds, W, "champion", None, model_kind, model,
                         H, TO, mutant=mutant, schedules=schedules,
                         height_metric=HM, tag=tag, seed_offset=seed_offset)

    # ---------------------------------------------------------------- G1
    say("---------------- G1  TIMING-PREDICATE GATE ----------------")
    real = arm(tag="G1 real")
    v = _viol(real, H, TO)
    say(f"  real striker        : {len(v)} violations / {_nrel(real)} "
        f"releases  -> {'PASS' if not v else 'FAIL'}")
    for x in v[:5]:
        say(f"      {x}")
    g1_real_ok = not v
    hs = [ev["h_at_release"] for s in real for ev in real[s]["release_log"]]
    ages = [ev["age_newest"] for s in real for ev in real[s]["release_log"]]
    reasons = {}
    for s in real:
        for ev in real[s]["release_log"]:
            reasons[ev["reason"]] = reasons.get(ev["reason"], 0) + 1
    say(f"      real release heights min={min(hs)} max={max(hs)}  "
        f"bank age_newest min={min(ages)}  reasons={reasons}")

    g1_kills = {}
    real_keys = _release_keys(real)
    for mut in ("inverted", "inverted_lt", "random", "ignores_bank"):
        rows = arm(mutant=mut, tag=f"G1 {mut}")
        mv = _viol(rows, H, TO)
        mk = _release_keys(rows)
        differs = sum(1 for s in seeds if mk.get(s) != real_keys.get(s))
        g1_kills[mut] = {"violations": len(mv), "releases": _nrel(rows),
                         "seeds_differing_from_real": differs,
                         "killed": bool(mv), "example": mv[:3]}
        say(f"  mutant {mut:<13}: {len(mv)} violations / {_nrel(rows)} "
            f"releases  -> {'KILLED' if mv else 'SURVIVED (GATE BROKEN)'}"
            f"   [non-equivalence: {differs}/{len(seeds)} seeds have a "
            f"different release sequence than the real striker]")
        for x in mv[:2]:
            say(f"      {x}")
        killed += bool(mv)

    scheds = R._schedules_for(real)
    blind = arm(model_kind="blind", schedules=scheds, tag="G1 blind")
    bv = _viol(blind, H, TO)
    say(f"  blind control's log : {len(bv)} violations / {_nrel(blind)} "
        f"releases  -> {'KILLED' if bv else 'SURVIVED (GATE BROKEN)'}")
    for x in bv[:2]:
        say(f"      {x}")
    killed += bool(bv)
    g1_kills["blind_log"] = {"violations": len(bv), "releases": _nrel(blind),
                             "killed": bool(bv), "example": bv[:3]}
    verdicts["G1_timing_predicate"] = {
        "real_violations": len(v), "real_releases": _nrel(real),
        "real_release_height_min": min(hs), "real_bank_age_min": min(ages),
        "real_reasons": reasons, "pass": g1_real_ok,
        "mutants": g1_kills,
        "all_mutants_killed": all(d["killed"] for d in g1_kills.values())}
    say()

    # ---------------------------------------------------------------- G2
    say("---------------- G2  PAIRING GATE ----------------")
    rerun = arm(tag="G2 rerun")
    p_rerun = SM.check_pairing(real, rerun, require_volleys=True)
    say(f"  striker vs striker rerun (layout+capsules+banked volleys): "
        f"{len(p_rerun)} violations -> {'PASS' if not p_rerun else 'FAIL'}")
    for x in p_rerun[:3]:
        say(f"      {x}")
    p_blind = SM.check_pairing(real, blind, require_volleys=False)
    say(f"  striker vs blind   (layout+capsule stream): "
        f"{len(p_blind)} violations -> {'PASS' if not p_blind else 'FAIL'}")
    for x in p_blind[:3]:
        say(f"      {x}")
    nvol = sum(len(ev["sizes"]) for s in real for ev in real[s]["release_log"])
    cap_len = min(len(real[s]["capsule_seq"]) for s in seeds)
    say(f"      evidence: {len(seeds)} seeds, {len(set(real[s]['virus_sig'] for s in seeds))}"
        f" distinct virus layouts across seeds (so the md5 is not a constant),"
        f" shortest compared capsule prefix {cap_len} placements,"
        f" {nvol} banked volleys reproduced")

    brk = arm(seed_offset=2, tag="G2 pair_break")
    p_brk = SM.check_pairing(real, brk, require_volleys=True)
    say(f"  MUTANT pair_break (game seed +2): {len(p_brk)} violations -> "
        f"{'KILLED' if p_brk else 'SURVIVED (GATE BROKEN)'}")
    for x in p_brk[:3]:
        say(f"      {x}")
    killed += bool(p_brk)
    verdicts["G2_pairing"] = {
        "striker_vs_rerun_violations": len(p_rerun),
        "striker_vs_blind_violations": len(p_blind),
        "distinct_virus_layouts": len(set(real[s]["virus_sig"] for s in seeds)),
        "shortest_capsule_prefix": cap_len,
        "banked_volleys_reproduced": nvol,
        "mutant_pair_break_violations": len(p_brk),
        "mutant_killed": bool(p_brk),
        "pass": (not p_rerun) and (not p_blind) and bool(p_brk)}
    say()

    # ---------------------------------------------------------------- G3
    say("---------------- G3  MATCHED-CONTROL GATE ----------------")
    mv_real = SM.check_matched_volume(real, scheds)
    per_seed = []
    for s in seeds:
        rel = [x for ev in real[s]["release_log"] for x in ev["sizes"]]
        sch = [x for _i, x in scheds[s]]
        per_seed.append({"seed": s, "striker_volleys": len(rel),
                         "control_volleys": len(sch),
                         "striker_cells": sum(rel),
                         "control_cells": sum(sch),
                         "striker_landed": real[s]["garbage_injected"],
                         "control_landed": blind[s]["garbage_injected"],
                         "control_undelivered": blind[s]["bank_leftover"]})
    say(f"  scheduled vs released, per seed: {len(mv_real)} violations -> "
        f"{'PASS' if not mv_real else 'FAIL'}")
    say(f"  {'seed':>5} {'volleys(str/ctl)':>18} {'cells(str/ctl)':>16} "
        f"{'landed(str/ctl)':>17} {'ctl undeliv':>12}")
    for d in per_seed:
        say(f"  {d['seed']:>5} {d['striker_volleys']:>8}/{d['control_volleys']:<9}"
            f" {d['striker_cells']:>7}/{d['control_cells']:<8}"
            f" {d['striker_landed']:>8}/{d['control_landed']:<8}"
            f" {d['control_undelivered']:>12}")
    tot_v = sum(d["striker_volleys"] for d in per_seed)
    tot_c = sum(d["striker_cells"] for d in per_seed)
    say(f"  totals: {tot_v} volleys / {tot_c} cells scheduled identically "
        f"in both arms; LANDED differs only via full-column skips and "
        f"early game ends (reported, not asserted)")

    scheds_drop = R._schedules_for(real, drop_one=True)
    mv_drop = SM.check_matched_volume(real, scheds_drop)
    say(f"  MUTANT drop_one (control loses its largest volley): "
        f"{len(mv_drop)} violations -> "
        f"{'KILLED' if mv_drop else 'SURVIVED (GATE BROKEN)'}")
    for x in mv_drop[:3]:
        say(f"      {x}")
    killed += bool(mv_drop)
    verdicts["G3_matched_control"] = {
        "violations": len(mv_real), "per_seed": per_seed,
        "total_volleys": tot_v, "total_cells": tot_c,
        "mutant_drop_one_violations": len(mv_drop),
        "mutant_killed": bool(mv_drop),
        "pass": (not mv_real) and bool(mv_drop)}
    say()

    # ---------------------------------------------------------------- G4
    say("---------------- G4  REGRESSION (new path == old blind bursty) ----")
    new_bursty = arm(model_kind="bursty", tag="G4 new bursty")
    old_bursty = PR.run_arm(LV, max(seeds) + 1, W, R.CHAMPION_WT,
                            R.CHAMPION_WS, "bursty", model)
    FIELDS = ("won", "topout", "stall", "pills", "garbage_injected",
              "stranded_final", "tower_final", "viruses_left_at_end",
              "dies_ahead")
    diffs = []
    for s in seeds:
        for f in FIELDS:
            if new_bursty[s][f] != old_bursty[s][f]:
                diffs.append(f"seed {s}: {f} {new_bursty[s][f]} != "
                             f"{old_bursty[s][f]}")
    say(f"  new play(bursty) vs pressure_rig.play(bursty) over "
        f"{len(seeds)} seeds x {len(FIELDS)} fields: {len(diffs)} diffs "
        f"-> {'PASS' if not diffs else 'FAIL'}")
    for x in diffs[:5]:
        say(f"      {x}")
    say(f"      evidence the comparison is non-trivial: total pills "
        f"{sum(old_bursty[s]['pills'] for s in seeds)}, clears "
        f"{sum(old_bursty[s]['won'] for s in seeds)}/{len(seeds)}, "
        f"garbage halves {sum(old_bursty[s]['garbage_injected'] for s in seeds)}")
    off = PR.run_arm(LV, max(seeds) + 1, W, R.CHAMPION_WT, 0, "bursty", model)
    off_diffs = [s for s in seeds
                 if any(new_bursty[s][f] != off[s][f] for f in FIELDS)]
    say(f"  COMPARATOR KILL: same comparison vs the old rig at ws=0 "
        f"(wrong champion): {len(off_diffs)}/{len(seeds)} seeds differ -> "
        f"{'KILLED' if off_diffs else 'SURVIVED (COMPARATOR VACUOUS)'}")
    killed += bool(off_diffs)
    verdicts["G4_regression"] = {
        "field_diffs": len(diffs), "examples": diffs[:5],
        "fields": list(FIELDS), "n_seeds": len(seeds),
        "old_total_pills": sum(old_bursty[s]["pills"] for s in seeds),
        "old_clears": sum(old_bursty[s]["won"] for s in seeds),
        "old_garbage_halves": sum(old_bursty[s]["garbage_injected"]
                                  for s in seeds),
        "comparator_kill_seeds_differing_at_ws0": len(off_diffs),
        "comparator_killed": bool(off_diffs),
        "pass": (not diffs) and bool(off_diffs)}
    say()

    # ---------------------------------------------------------------- verdict
    passed = all(v["pass"] for v in verdicts.values()) and \
        verdicts["G1_timing_predicate"]["all_mutants_killed"]
    say("================ VERDICT ================")
    for k, vv in verdicts.items():
        say(f"  {k:<24} {'PASS' if vv['pass'] else 'FAIL'}")
    say(f"  mutants killed: {killed} "
        f"(G1 inverted/inverted_lt/random/ignores_bank/blind-log, "
        f"G2 pair_break, G3 drop_one, G4 ws0-comparator)")
    say(f"  GATE {'PASSED' if passed else 'FAILED'}")

    os.makedirs(a.out, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(a.out, f"gate_{stamp}.log")
    json_path = os.path.join(a.out, f"gate_{stamp}.json")
    with open(log_path, "w") as fh:
        fh.write("\n".join(LOG) + "\n")
    with open(json_path, "w") as fh:
        json.dump({"started": started, "n": len(seeds), "seeds": seeds,
                   "H": H, "timeout": TO, "height_metric": HM,
                   "level": LV, "mutants_killed": killed,
                   "passed": passed, "verdicts": verdicts}, fh, indent=1)
    print(f"log  -> {log_path}")
    print(f"json -> {json_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
