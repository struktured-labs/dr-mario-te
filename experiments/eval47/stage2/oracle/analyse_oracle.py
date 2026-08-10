#!/usr/bin/env python3
"""Apply the PRE-REGISTERED verdict rule to the oracle-ceiling output.

The statistics are NOT re-implemented here.  `summarise()` and `verdict()` are
imported verbatim from `../rollout/analyse.py`, the code that produced the
stage-2 rollout numbers and whose verdict function is itself mutant-tested
(`../rollout/test_verdict.py`).  Reusing it is deliberate: the oracle arm and
the stage-2 arm must be scored by the SAME instrument or their effect sizes are
not comparable, and comparability is the entire point of a calibration arm.

This file adds only what the oracle arm needs on top:
  * segment-aware loading (`out/<run>/seg_*.jsonl`),
  * the pre-registered POWER-ADEQUACY check (PREREG_ORACLE sec 5) -- the
    clear-rate non-inferiority gate is only decidable if the achieved paired CI
    half-width is below the +1.0pp margin, and the stage-2 run was NOT,
  * stall accounting at parity with topouts (PREREG_ORACLE sec 4 N3'),
  * the difference-in-differences against the killed mutant,
  * the per-ply flip provenance rollup.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROLLOUT = os.path.join(os.path.dirname(HERE), "rollout")
sys.path.insert(0, ROLLOUT)
sys.path.insert(0, HERE)

from analyse import summarise, verdict, boot_paired, mcnemar_exact  # noqa: E402

CLEAR_MARGIN_PP = 1.0          # pre-registered non-inferiority margin
N_MIN_INCONCLUSIVE = 1500      # below this the primary reads INCONCLUSIVE


def load_run(outdir):
    rows, seen = [], set()
    for fn in sorted(os.listdir(outdir)):
        if not (fn.startswith("seg_") and fn.endswith(".jsonl")):
            continue
        for ln in open(os.path.join(outdir, fn)):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r["seed"] in seen:
                continue
            seen.add(r["seed"])
            rows.append(r)
    rows.sort(key=lambda r: r["seed"])
    return rows


def power_adequacy(s):
    """PREREG_ORACLE sec 5.  Is the clear-rate gate DECIDABLE at this N?

    A non-inferiority gate whose CI half-width exceeds its own margin cannot be
    passed by any true effect, however good.  Stage 2 shipped exactly that gate
    and it could not have passed even if the model were perfect.  This check is
    computed and reported BEFORE the verdict, every time.
    """
    clr = s["metrics"]["clear"]
    lo, hi = clr["diff_ci95"]
    half = (hi - lo) / 2.0 * 100.0
    d = s["discordance"]["won"]
    disc = d["base1_trt0"] + d["base0_trt1"]
    n = s["n_pairs"]
    # N needed for half-width < margin at this discordance rate:
    #   1.96*sqrt(disc_rate/N) < margin  =>  N > disc_rate*(1.96/margin)^2
    rate = disc / max(1, n)
    need = rate * (1.96 / (CLEAR_MARGIN_PP / 100.0)) ** 2
    return {"clear_ci_halfwidth_pp": half,
            "margin_pp": CLEAR_MARGIN_PP,
            "decidable": bool(half < CLEAR_MARGIN_PP),
            "discordant_clear_pairs": disc,
            "discordance_rate": rate,
            "n_needed_for_decidable_clear_gate": int(np.ceil(need)),
            "n_achieved": n}


def hazard_rate(rows):
    """PREREG_ORACLE A4 -- dies-ahead per 100 pills, ALONGSIDE the raw endpoint.

    The oracle finishes games faster, so it is exposed to fewer injection events
    and fewer chances to die.  Part of any dies-ahead reduction is therefore
    REDUCED EXPOSURE rather than better decisions, and the raw per-game endpoint
    cannot separate the two.

    THE TEMPO GAIN IS NOT NETTED OUT, DELIBERATELY.  The north star is beating a
    human and speed is how the champion loses; finishing sooner is a win
    condition in this programme, not merely a nuisance variable.  Both views are
    reported and the write-up must state which of the two the ceiling is made
    of -- i.e. how much of the movement survives this normalisation.
    """
    db = np.array([r["base"]["dies_ahead"] for r in rows], float)
    dt = np.array([r["trt"]["dies_ahead"] for r in rows], float)
    pb = np.array([r["base"]["pills"] for r in rows], float)
    pt = np.array([r["trt"]["pills"] for r in rows], float)
    hb = 100.0 * db / np.maximum(pb, 1.0)      # per-seed hazard
    ht = 100.0 * dt / np.maximum(pt, 1.0)
    lo, hi, fneg, fpos = boot_paired(ht - hb)
    return {"base_per_game_pp": float(db.mean() * 100),
            "trt_per_game_pp": float(dt.mean() * 100),
            "base_per_100_pills": float(100.0 * db.sum() / max(pb.sum(), 1.0)),
            "trt_per_100_pills": float(100.0 * dt.sum() / max(pt.sum(), 1.0)),
            "paired_hazard_diff": float((ht - hb).mean()),
            "paired_hazard_ci95": [lo, hi],
            "frac_boot_neg": fneg, "frac_boot_pos": fpos,
            "mean_pills_base": float(pb.mean()),
            "mean_pills_trt": float(pt.mean()),
            "exposure_ratio_trt_over_base":
                float(pt.sum() / max(pb.sum(), 1.0))}


def stall_parity(s):
    """N3' -- stalls scored at parity with topouts.

    In stage 2, 19 of the 28 topouts avoided reappeared as 300-pill STALLS and
    the stall condition never fired because NET bad-ends still fell.  The
    oracle arm scores the two together, explicitly, as a named condition.
    """
    m = s["metrics"]
    be = m["bad_ends"]
    return {"topout_diff_pp": m["topout"]["diff_trt_minus_base"] * 100,
            "stall_diff_pp": m["stall"]["diff_trt_minus_base"] * 100,
            "bad_ends_diff_pp": be["diff_trt_minus_base"] * 100,
            "bad_ends_ci95_pp": [be["diff_ci95"][0] * 100,
                                 be["diff_ci95"][1] * 100],
            "topouts_converted_to_stalls":
                (m["topout"]["diff_trt_minus_base"] < 0
                 and m["stall"]["diff_trt_minus_base"] > 0)}


def flip_provenance(rows):
    """Roll up the per-ply flip records (CHAMPION_ITER_PLAN P0: mandatory)."""
    recs = [f for r in rows for f in r["trt"].get("flip_log", [])]
    if not recs:
        return {"n_flips_logged": 0}
    t = np.array([f["t_to_end"] for f in recs], float)
    v = np.array([f["viruses"] for f in recs], float)
    h = np.array([f["maxh"] for f in recs], float)
    ds = np.array([f["d_spawn_h"] for f in recs], float)
    rk = np.array([f["champ_rank_chosen"] for f in recs], float)
    tie = np.array([bool(f["tie"]) for f in recs])
    return {"n_flips_logged": len(recs),
            "t_to_end": {"mean": float(t.mean()),
                         "p10": float(np.percentile(t, 10)),
                         "median": float(np.median(t)),
                         "p90": float(np.percentile(t, 90))},
            "viruses_at_flip_median": float(np.median(v)),
            "maxh_at_flip_median": float(np.median(h)),
            "d_spawn_h_at_flip_median": float(np.median(ds)),
            "champ_rank_chosen_hist":
                {str(k): int((rk == k).sum()) for k in (0, 1, 2, 3)},
            "frac_flips_that_tied_champion_label": float(tie.mean()),
            "frac_flips_in_last_10_plies": float((t <= 10).mean())}


def did(rows_true, rows_mut):
    """Difference-in-differences on dies-ahead, over the COMMON seed set."""
    a = {r["seed"]: r for r in rows_true}
    b = {r["seed"]: r for r in rows_mut}
    common = sorted(set(a) & set(b))
    if not common:
        return {"n_common": 0}
    drift = sum(1 for s in common
                if (a[s]["base"]["res"], a[s]["base"]["pills"])
                != (b[s]["base"]["res"], b[s]["base"]["pills"]))
    dt = np.array([a[s]["trt"]["dies_ahead"] - a[s]["base"]["dies_ahead"]
                   for s in common], float)
    dm = np.array([b[s]["trt"]["dies_ahead"] - b[s]["base"]["dies_ahead"]
                   for s in common], float)
    lo, hi, fneg, fpos = boot_paired(dt - dm)
    return {"n_common": len(common),
            "base_drift_mismatches": drift,
            "da_diff_true_pp": float(dt.mean() * 100),
            "da_diff_mutant_pp": float(dm.mean() * 100),
            "did_true_minus_mutant_pp": float((dt - dm).mean() * 100),
            "did_ci95_pp": [lo * 100, hi * 100],
            "frac_boot_neg": fneg, "frac_boot_pos": fpos}


def report(s, tag, primary):
    m = s["metrics"]
    print(f"\n===== {tag}  N={s['n_pairs']} paired seeds "
          f"({s['seed_min']}..{s['seed_max']}) =====")
    print(f"{'metric':12s} {'BASE':>20s} {'TRT':>20s} {'diff (trt-base)':>28s}")
    for nm in ("dies_ahead", "clear", "topout", "stall", "bad_ends", "pills"):
        d = m[nm]
        sc = 1.0 if nm == "pills" else 100.0
        u = "" if nm == "pills" else "%"
        bci, tci = d.get("base_ci95"), d.get("trt_ci95")
        bs = (f"{d['base']*sc:.2f}{u} [{bci[0]*sc:.2f},{bci[1]*sc:.2f}]"
              if bci else f"{d['base']*sc:.2f}{u}")
        ts = (f"{d['trt']*sc:.2f}{u} [{tci[0]*sc:.2f},{tci[1]*sc:.2f}]"
              if tci else f"{d['trt']*sc:.2f}{u}")
        print(f"{nm:12s} {bs:>20s} {ts:>20s} "
              f"{d['diff_trt_minus_base']*sc:>+10.3f}{u} "
              f"[{d['diff_ci95'][0]*sc:+.3f},{d['diff_ci95'][1]*sc:+.3f}]")
    b = s["breakage"]
    print(f"BREAKAGE clears base-only {b['clears_broken_base1_trt0']} | "
          f"trt-only {b['clears_rescued_base0_trt1']} | net "
          f"{b['net_clears_trt_minus_base']:+d} "
          f"(McNemar p={b['clear_mcnemar_exact_p']:.4f})")
    print(f"DIES-AHEAD rescued {b['da_rescued_base1_trt0']} | broken "
          f"{b['da_broken_base0_trt1']} | McNemar p="
          f"{s['discordance']['dies_ahead']['mcnemar_exact_p']:.4f}")
    print(f"NET in clear-equivalents (6.4:1): "
          f"{b['net_in_clear_equivalents']:+.2f}")
    print(f"realised flip rate {s['realised_flip_rate']*100:.2f}% of plies; "
          f"{s['games_with_any_flip']}/{s['n_pairs']} games flipped >=1 ply")
    pa = s["power_adequacy"]
    print(f"POWER  clear-rate CI half-width {pa['clear_ci_halfwidth_pp']:.3f}pp "
          f"vs margin {pa['margin_pp']:.2f}pp -> "
          f"{'DECIDABLE' if pa['decidable'] else 'NOT DECIDABLE'}; "
          f"N needed {pa['n_needed_for_decidable_clear_gate']:,} "
          f"(achieved {pa['n_achieved']:,})")
    sp = s["stall_parity"]
    print(f"STALL PARITY topout {sp['topout_diff_pp']:+.2f}pp  stall "
          f"{sp['stall_diff_pp']:+.2f}pp  bad-ends {sp['bad_ends_diff_pp']:+.2f}pp"
          f"  topouts->stalls conversion: {sp['topouts_converted_to_stalls']}")
    hz = s["hazard_rate"]
    print(f"HAZARD (A4)  dies-ahead/game {hz['base_per_game_pp']:.2f}pp -> "
          f"{hz['trt_per_game_pp']:.2f}pp   |   per 100 pills "
          f"{hz['base_per_100_pills']:.3f} -> {hz['trt_per_100_pills']:.3f}   "
          f"paired {hz['paired_hazard_diff']:+.3f} "
          f"[{hz['paired_hazard_ci95'][0]:+.3f},{hz['paired_hazard_ci95'][1]:+.3f}]"
          f"   exposure x{hz['exposure_ratio_trt_over_base']:.3f}")
    fp = s["flip_provenance"]
    if fp.get("n_flips_logged"):
        print(f"FLIP PROVENANCE n={fp['n_flips_logged']}  t_to_end median "
              f"{fp['t_to_end']['median']:.0f} (p10 {fp['t_to_end']['p10']:.0f}, "
              f"p90 {fp['t_to_end']['p90']:.0f})  viruses@flip median "
              f"{fp['viruses_at_flip_median']:.0f}  maxh {fp['maxh_at_flip_median']:.0f}"
              f"  rank chosen {fp['champ_rank_chosen_hist']}"
              f"  frac in last 10 plies {fp['frac_flips_in_last_10_plies']*100:.1f}%")
    print(f"VERDICT ({tag}, {'PRIMARY' if primary else 'no authority'}): "
          f"{s['verdict']['verdict']}")
    for r in s["verdict"]["reasons"]:
        print("  - " + r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--true-run", required=True,
                    help="outdir of the label=true run")
    ap.add_argument("--mutant-run", help="outdir of the label=shuffle run")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="oracle")
    a = ap.parse_args()

    res = {"prereg": "PREREG_ORACLE.md -> PREREG_ROLLOUT.md -> "
                     "PREREG_STAGE2.md sec 6.3/6.4",
           "arms": {}}
    rt = load_run(a.true_run)
    s = summarise(rt, a.label)
    s["power_adequacy"] = power_adequacy(s)
    s["stall_parity"] = stall_parity(s)
    s["hazard_rate"] = hazard_rate(rt)
    s["flip_provenance"] = flip_provenance(rt)
    s["verdict"] = verdict(s, primary=True)
    res["arms"]["true"] = s
    report(s, "ORACLE (true label)", True)

    if a.mutant_run and os.path.isdir(a.mutant_run):
        rm = load_run(a.mutant_run)
        sm = summarise(rm, a.label + "_shuffled")
        sm["power_adequacy"] = power_adequacy(sm)
        sm["stall_parity"] = stall_parity(sm)
        sm["hazard_rate"] = hazard_rate(rm)
        sm["flip_provenance"] = flip_provenance(rm)
        sm["verdict"] = verdict(sm, primary=True)
        res["arms"]["shuffled_mutant"] = sm
        report(sm, "KILLED MUTANT (shuffled survival label)", True)
        res["did"] = did(rt, rm)
        d = res["did"]
        print(f"\nDIFFERENCE-IN-DIFFERENCES (dies-ahead), n_common="
              f"{d['n_common']}, base drift mismatches "
              f"{d['base_drift_mismatches']}")
        print(f"  true {d['da_diff_true_pp']:+.3f}pp   mutant "
              f"{d['da_diff_mutant_pp']:+.3f}pp   DiD "
              f"{d['did_true_minus_mutant_pp']:+.3f}pp "
              f"[{d['did_ci95_pp'][0]:+.3f},{d['did_ci95_pp'][1]:+.3f}]")
        print("\nKILLED-MUTANT GATE: the shuffled arm must NOT read GO.")
        print(f"  mutant verdict = {sm['verdict']['verdict']}  -> "
              f"{'RED (correct)' if sm['verdict']['verdict'] != 'GO' else 'GREEN (GATE IS BROKEN)'}")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
