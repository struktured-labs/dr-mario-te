#!/usr/bin/env python3
"""Apply the PRE-REGISTERED verdict rule to the paired A/B output.

PREREG_ROLLOUT.md sec 4/5, itself PREREG_STAGE2.md sec 6.3/6.4 @ b9725fc.
Nothing in here is chosen after seeing a number.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

B_BOOT = 2000
RNG = 20260810


def load(path):
    rows = []
    seen = set()
    for ln in open(path):
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


def arr(rows, arm, key):
    return np.array([r[arm][key] for r in rows], dtype=np.float64)


def boot_paired(d, B=B_BOOT, seed=RNG):
    """95% CI on the mean of a per-seed paired difference vector."""
    rng = np.random.default_rng(seed)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    m = d[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), \
        float((m < 0).mean()), float((m > 0).mean())


def boot_rate(x, B=B_BOOT, seed=RNG):
    rng = np.random.default_rng(seed)
    n = len(x)
    idx = rng.integers(0, n, size=(B, n))
    m = x[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def mcnemar_exact(b01, b10):
    """Two-sided exact binomial on the discordant pairs."""
    n = b01 + b10
    if n == 0:
        return 1.0
    k = min(b01, b10)
    p = 0.0
    for i in range(0, k + 1):
        p += math.comb(n, i) * 0.5 ** n
    return float(min(1.0, 2 * p))


def summarise(rows, tag):
    n = len(rows)
    seeds = np.array([r["seed"] for r in rows])
    out = {"tag": tag, "n_pairs": n,
           "seed_min": int(seeds.min()), "seed_max": int(seeds.max())}
    metrics = {}
    for key, nm in (("dies_ahead", "dies_ahead"), ("won", "clear"),
                    ("topout", "topout"), ("stall", "stall"),
                    ("pills", "pills")):
        b, t = arr(rows, "base", key), arr(rows, "trt", key)
        lo_b, hi_b = boot_rate(b)
        lo_t, hi_t = boot_rate(t)
        d = t - b
        lo, hi, fneg, fpos = boot_paired(d)
        metrics[nm] = {
            "base": float(b.mean()), "base_ci95": [lo_b, hi_b],
            "trt": float(t.mean()), "trt_ci95": [lo_t, hi_t],
            "diff_trt_minus_base": float(d.mean()), "diff_ci95": [lo, hi],
            "frac_boot_neg": fneg, "frac_boot_pos": fpos,
            "n_base": int(b.sum()) if nm != "pills" else None,
            "n_trt": int(t.sum()) if nm != "pills" else None}
    # net bad-ends
    bb = arr(rows, "base", "topout") + arr(rows, "base", "stall")
    tb = arr(rows, "trt", "topout") + arr(rows, "trt", "stall")
    d = tb - bb
    lo, hi, fneg, fpos = boot_paired(d)
    metrics["bad_ends"] = {"base": float(bb.mean()), "trt": float(tb.mean()),
                           "diff_trt_minus_base": float(d.mean()),
                           "diff_ci95": [lo, hi],
                           "frac_boot_neg": fneg, "frac_boot_pos": fpos,
                           "n_base": int(bb.sum()), "n_trt": int(tb.sum())}
    out["metrics"] = metrics

    # ---- paired discordance tables -------------------------------------
    disc = {}
    for key in ("dies_ahead", "won", "topout", "stall"):
        b, t = arr(rows, "base", key).astype(int), arr(rows, "trt", key).astype(int)
        b01 = int(((b == 0) & (t == 1)).sum())      # trt has it, base does not
        b10 = int(((b == 1) & (t == 0)).sum())      # base has it, trt does not
        disc[key] = {"base1_trt0": b10, "base0_trt1": b01,
                     "mcnemar_exact_p": mcnemar_exact(b01, b10),
                     "concordant11": int(((b == 1) & (t == 1)).sum()),
                     "concordant00": int(((b == 0) & (t == 0)).sum())}
    out["discordance"] = disc

    # ---- BREAKAGE ACCOUNTING (PREREG_ROLLOUT sec 5) ---------------------
    cb, ct = arr(rows, "base", "won").astype(int), arr(rows, "trt", "won").astype(int)
    breakage = int(((cb == 1) & (ct == 0)).sum())
    rescue = int(((cb == 0) & (ct == 1)).sum())
    dab, dat = (arr(rows, "base", "dies_ahead").astype(int),
                arr(rows, "trt", "dies_ahead").astype(int))
    da_rescue = int(((dab == 1) & (dat == 0)).sum())
    da_break = int(((dab == 0) & (dat == 1)).sum())
    seeds_arr = np.array([r["seed"] for r in rows])
    out["breakage_seeds"] = {
        "broken_clears": seeds_arr[(cb == 1) & (ct == 0)].tolist()[:200],
        "rescued_clears": seeds_arr[(cb == 0) & (ct == 1)].tolist()[:200],
        "da_rescued": seeds_arr[(dab == 1) & (dat == 0)].tolist()[:200],
        "da_broken": seeds_arr[(dab == 0) & (dat == 1)].tolist()[:200]}
    out["breakage"] = {
        "clears_broken_base1_trt0": breakage,
        "clears_rescued_base0_trt1": rescue,
        "net_clears_trt_minus_base": rescue - breakage,
        "clear_mcnemar_exact_p": mcnemar_exact(rescue, breakage),
        "da_rescued_base1_trt0": da_rescue,
        "da_broken_base0_trt1": da_break,
        "net_da_reduction_base_minus_trt": da_rescue - da_break,
        "population_ratio_clears_per_da": 6.4,
        "net_in_clear_equivalents":
            (rescue - breakage) + (da_rescue - da_break) / 6.4,
        "note": ("uniform population sampling prices breakage at the true ratio; "
                 "net_in_clear_equivalents converts the DA win into lost-clear "
                 "units at the census ratio 9,576:1,501 = 6.4:1")}

    # ---- pills among BOTH-CLEAR pairs (tempo tax) -----------------------
    both = (cb == 1) & (ct == 1)
    if both.sum() > 0:
        pb = arr(rows, "base", "pills")[both]
        pt = arr(rows, "trt", "pills")[both]
        lo, hi, fneg, fpos = boot_paired(pt - pb)
        out["pills_both_clear"] = {"n": int(both.sum()),
                                   "base": float(pb.mean()),
                                   "trt": float(pt.mean()),
                                   "diff": float((pt - pb).mean()),
                                   "diff_ci95": [lo, hi]}
    # ---- realised flip rate ---------------------------------------------
    fl = np.array([r["trt"].get("flips", 0) for r in rows], dtype=float)
    pl = np.array([r["trt"].get("plies_scored", 0) for r in rows], dtype=float)
    out["realised_flip_rate"] = float(fl.sum() / max(1.0, pl.sum()))
    out["games_with_any_flip"] = int((fl > 0).sum())
    out["identical_outcome_pairs"] = int(sum(
        1 for r in rows if r["base"]["res"] == r["trt"]["res"]
        and r["base"]["pills"] == r["trt"]["pills"]))
    return out


def verdict(s, primary=True):
    """PREREG_STAGE2 sec 6.3/6.4 verdict rule, applied verbatim."""
    m = s["metrics"]
    n = s["n_pairs"]
    da = m["dies_ahead"]
    clr = m["clear"]
    be = m["bad_ends"]
    reasons = []
    if not primary:
        return {"verdict": "NO VERDICT AUTHORITY (secondary regime)",
                "reasons": ["PREREG_ROLLOUT sec 3: the drip regime is a "
                            "generalisation check, not a decider"]}
    if n < 1500:
        return {"verdict": "INCONCLUSIVE",
                "reasons": [f"achieved N={n} < 1,500 (PREREG_ROLLOUT sec 3 "
                            f"early-stop rule): underpowered, reported as "
                            f"INCONCLUSIVE, not as GO or NO-GO"]}
    # N1 clear-rate non-inferiority: upper bound of CI on (base - trt) < +1.0pp
    # diff_ci95 is on (trt - base); (base - trt) upper bound = -diff_lo
    clear_loss_upper = -clr["diff_ci95"][0]
    n1 = clear_loss_upper >= 0.01
    # N2 dies-ahead CI includes 0 (need CI entirely below 0)
    n2 = not (da["diff_ci95"][1] < 0)
    mcp = s["discordance"]["dies_ahead"]["mcnemar_exact_p"]
    n2b = not (mcp < 0.05)
    # N3 DA falls but net bad-ends do not
    n3 = (da["diff_trt_minus_base"] < 0) and (be["diff_trt_minus_base"] >= 0)
    if n1:
        reasons.append(f"N1 clear-rate loss upper 95% bound "
                       f"{clear_loss_upper*100:+.2f}pp >= +1.00pp")
    if n2:
        reasons.append(f"N2 dies-ahead 95% CI on (trt-base) "
                       f"[{da['diff_ci95'][0]*100:+.3f},"
                       f"{da['diff_ci95'][1]*100:+.3f}]pp includes/crosses 0")
    if n2b:
        reasons.append(f"N2 McNemar exact two-sided p={mcp:.4f} >= 0.05")
    if n3:
        reasons.append(f"N3 dies-ahead falls but net bad-ends do not "
                       f"({be['diff_trt_minus_base']*100:+.2f}pp)")
    v = "NO_GO" if reasons else "GO"
    return {"verdict": v, "reasons": reasons or ["all pre-registered GO "
                                                 "conditions met"],
            "clear_loss_upper_95_pp": clear_loss_upper * 100,
            "mcnemar_p": mcp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lulu", required=True)
    ap.add_argument("--drip")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {"prereg": "PREREG_ROLLOUT.md (this lane) -> PREREG_STAGE2.md sec 6.3 @ b9725fc",
           "caveat": ("Corpus s2lulu: generating policy = shipped champion "
                      "(bit-exact), environment = dr. lulu fitted bursty "
                      "pressure, clear rate 79.80% - BELOW the 96.9% "
                      "label-quality screen. Labels are game outcomes broadcast "
                      "onto decisions; no counterfactual attribution."),
           "contamination": ("model S1br2_lut8_q64 is ROUND-2 / "
                             "CONTAMINATION-FLAGGED (PREREG_SHIPPABLE deviation 7)"),
           "arms": {}}
    s = summarise(load(a.lulu), "lulu")
    res["arms"]["lulu"] = s
    res["verdict_lulu_PRIMARY"] = verdict(s, primary=True)
    if a.drip and os.path.exists(a.drip):
        s2 = summarise(load(a.drip), "drip")
        res["arms"]["drip"] = s2
        res["verdict_drip"] = verdict(s2, primary=False)
    json.dump(res, open(a.out, "w"), indent=1, default=float)

    for k, s in res["arms"].items():
        m = s["metrics"]
        print(f"\n===== {k}  N={s['n_pairs']} paired seeds "
              f"({s['seed_min']}..{s['seed_max']}) =====")
        print(f"{'metric':14s} {'BASE':>18s} {'TRT':>18s} "
              f"{'diff (trt-base)':>26s}")
        for nm in ("dies_ahead", "clear", "topout", "stall", "bad_ends", "pills"):
            d = m[nm]
            sc = 1.0 if nm == "pills" else 100.0
            u = "" if nm == "pills" else "%"
            bci = d.get("base_ci95")
            tci = d.get("trt_ci95")
            bs = (f"{d['base']*sc:.2f}{u} [{bci[0]*sc:.2f},{bci[1]*sc:.2f}]"
                  if bci else f"{d['base']*sc:.2f}{u}")
            ts = (f"{d['trt']*sc:.2f}{u} [{tci[0]*sc:.2f},{tci[1]*sc:.2f}]"
                  if tci else f"{d['trt']*sc:.2f}{u}")
            print(f"{nm:14s} {bs:>18s} {ts:>18s} "
                  f"{d['diff_trt_minus_base']*sc:>+10.3f}{u} "
                  f"[{d['diff_ci95'][0]*sc:+.3f},{d['diff_ci95'][1]*sc:+.3f}]")
        b = s["breakage"]
        print(f"BREAKAGE  clears base-only {b['clears_broken_base1_trt0']} | "
              f"trt-only {b['clears_rescued_base0_trt1']} | net "
              f"{b['net_clears_trt_minus_base']:+d} "
              f"(McNemar p={b['clear_mcnemar_exact_p']:.4f})")
        print(f"DIES-AHEAD rescued {b['da_rescued_base1_trt0']} | broken "
              f"{b['da_broken_base0_trt1']} | net "
              f"{b['net_da_reduction_base_minus_trt']:+d} "
              f"(McNemar p="
              f"{s['discordance']['dies_ahead']['mcnemar_exact_p']:.4f})")
        print(f"NET in clear-equivalents (6.4:1): "
              f"{b['net_in_clear_equivalents']:+.2f}")
        print(f"realised flip rate {s['realised_flip_rate']*100:.2f}% of plies; "
              f"{s['games_with_any_flip']}/{s['n_pairs']} games flipped >=1 ply; "
              f"{s['identical_outcome_pairs']} pairs identical")
    print("\nVERDICT (lulu, PRIMARY): "
          f"{res['verdict_lulu_PRIMARY']['verdict']}")
    for r in res["verdict_lulu_PRIMARY"]["reasons"]:
        print("  - " + r)


if __name__ == "__main__":
    main()
