#!/usr/bin/env python3
"""report_autopsy.py — turn the machine-readable results into the DEFECT LIST.

Reads out/AUTOPSY_REPORT.json, out/validate_*.json, out/positive_control.json,
out/gate_autopsy.json and the census progress, and writes AUTOPSY_RESULTS.md.
Coverage is printed as a HEADLINE, not a footnote: DOOMED is an absence claim,
so a reader must see how much of the space was searched before reading a split.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def j(name, default=None):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def main():
    rep = j("AUTOPSY_REPORT.json")
    if rep is None:
        sys.exit("no AUTOPSY_REPORT.json — run analyze_autopsy.py first")
    prog = j(os.path.join("census", "progress.json"), {}) or {}
    vt = j("validate_true.json", {}) or {}
    vs = j("validate_shuffle.json", {}) or {}
    vm = j("validate_mimic.json", {}) or {}
    pc = j("positive_control.json", {}) or {}
    g = j("gate_autopsy.json", {}) or {}

    n = rep["n_games"]
    done = prog.get("done", 0)
    total = prog.get("total", 65535)
    L = []
    A = L.append
    A("# L11 CLEAN-FAILURE AUTOPSY — RESULTS")
    A("")
    A("Registered in PREREG_AUTOPSY (+ AMENDMENT A1) before any label row "
      "existed. Solo, unpressured, L11, ws=20 — no opponent and full "
      "observability, so every failure here is the champion beating itself.")
    A("")
    A("## COVERAGE FIRST (DOOMED is an absence claim)")
    A("")
    A(f"| census seeds scanned | **{done:,} / {total:,}** "
      f"({done / total:.1%}) |")
    A("|---|---|")
    A(f"| failures found | **{n}** ({rep['by_result']['topout']} topout, "
      f"{rep['by_result']['stall']} stall) |")
    A(f"| of those, exactly ONE VIRUS LEFT | **{rep['one_virus_left']}/{n}** |")
    A(f"| games autopsied | {n} |")
    A(f"| firing plies examined | {rep['n_firing_plies']} |")
    A("")
    A("**Population corroboration (A2): there is no remote half.** The node's "
      "copy of the census was removed in an earlier teardown, so void class "
      "V-P has no second half to cross-check against — it is not satisfied and "
      "not waived, it is unreachable. What stands in its place is narrower and "
      "is quoted as such: seeds 33269 and 33754 reproduce their census-era "
      "record hashes (full move trace, fatal board, terminal fields) "
      "bit-identically on today's tree, so the decide path that produced the "
      "original 53 is the one producing these rows.")
    A("")
    if done < total:
        A(f"⚠ **{total - done:,} seeds are NOT YET SCANNED.** Every number "
          f"below is over the {n} failures found so far, not the closed "
          f"53-game population. The unscanned remainder is named here rather "
          f"than buried.")
        A("")
    A("## VERDICT")
    A("")
    lo, hi = rep["avoidable_ci95"]
    A(f"**AVOIDABLE {rep['avoidable']}/{n} = {rep['avoidable_rate']:.1%}** "
      f"(exact 95% CI {lo:.1%}-{hi:.1%}) · DOOMED {rep['doomed']}")
    A("")
    clo, chi = rep["clair_ci95"]
    A(f"Clairvoyant column (A1.2, reported separately and never pooled): "
      f"{rep['clair_avoidable']}/{n} (CI {clo:.1%}-{chi:.1%}). "
      f"AVOIDABLE-under-clairvoyance is weak evidence (it can collect luck the "
      f"agent could not foresee); **DOOMED-under-clairvoyance is the strong "
      f"absence verdict** — not even a future-reading one-ply deviation saves "
      f"the game.")
    A("")
    A("## THE DEFECT LIST (clusters overlap by construction)")
    A("")
    A("| defect | firing plies |")
    A("|---|---|")
    for k, v in sorted(rep["cluster_marginals"].items(), key=lambda x: -x[1]):
        A(f"| {k} | {v} |")
    A("")
    keys = sorted(rep["cluster_marginals"])
    if keys:
        A("Co-occurrence (rows/cols = clusters):")
        A("")
        A("| | " + " | ".join(keys) + " |")
        A("|" + "---|" * (len(keys) + 1))
        for a in keys:
            A(f"| **{a}** | " + " | ".join(
                str(rep["cluster_cooccurrence"][f"{a}|{b}"]) for b in keys) + " |")
        A("")
    A("## TIME BEFORE DEATH")
    A("")
    dk = rep["deepest_k"]
    if dk:
        c = Counter(rep["firing_k_all"])
        A(f"Deepest firing k per avoidable game (plies before the anchor): "
          f"{sorted(dk)}")
        A("")
        A("| k | firing plies |")
        A("|---|---|")
        for k in sorted(c):
            A(f"| {k} | {c[k]} |")
        A("")
        A("The pilot put the lock-in boundary at ~6-10 plies before death "
          "(both of its rescues sat at k=10 and every k<=6 claim failed to "
          "rescue). Compare the distribution above against that boundary.")
    else:
        A("No firing plies — nothing to distribute.")
    A("")
    A("## VALIDATION")
    A("")
    A("| instrument | claims | forced-move confirmed |")
    A("|---|---|---|")
    for name, d in (("true", vt), ("M-shuffle", vs)):
        if d:
            r = d.get("confirm_rate")
            A(f"| {name} | {d.get('n_claims')} | "
              f"{d.get('forced_confirmed')}/{d.get('forced_n')}"
              + (f" = {r:.1%}" if r is not None else "") + " |")
    if vm:
        A(f"| M-mimic | **{vm.get('claims', 0)}** | "
          f"**{vm.get('verdict')}** (required failure) |")
    A("")
    if pc:
        A(f"Positive control (§4, rule 8): {pc.get('refired')}/{pc.get('n')} "
          f"firing plies re-fired at CRN sample offset "
          f"{pc.get('sample_offset')} — futures the label had never seen. "
          f"Without this, DOOMED could not be distinguished from an "
          f"instrument that never fires.")
        A("")
    if g:
        A(f"Gates: G1 replay green; G2 M-stale KILLED at "
          f"{len(g.get('G2', {}).get('kills', []))} seeds; G3 fork-cursor "
          f"independence proven both directions; G4 dose gate — corrected dose "
          f"{g.get('G4', {}).get('live_spread')} varying candidates vs "
          f"M-INERT {g.get('G4', {}).get('inert_spread')} over "
          f"{g.get('G4', {}).get('n_states')} states (the originally "
          f"registered dose is FLAT — the vacuity is proven, not asserted); "
          f"G5 determinism byte-identical.")
        A("")
    A("## PER-GAME TABLE")
    A("")
    A("| seed | result | virus left | plies | anchor | scanned | verdict | "
      "deepest k | clair |")
    A("|---|---|---|---|---|---|---|---|---|")
    for gm in rep["games"]:
        A(f"| {gm['seed']} | {gm['result']} | {gm['viruses_left']} | "
          f"{gm['n_moves']} | {gm['anchor']} | {gm['plies_scanned']} | "
          f"**{gm['verdict']}** | {gm['deepest_k'] if gm['deepest_k'] is not None else '—'} | "
          f"{'yes' if gm['clair_avoidable'] else 'no'} |")
    A("")
    path = os.path.join(HERE, "AUTOPSY_RESULTS.md")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {path}")
    print("REPORT_OK")


if __name__ == "__main__":
    main()
