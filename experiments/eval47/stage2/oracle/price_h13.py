"""Price the H13 endpoint: power at N=9,000, and what it costs to buy.

Rule 25 — a number that is only ever printed is never checked. Every figure in
the GO/NO-GO-on-spending recommendation is computed here, from measured inputs,
so that pricing the wrong arm is not expressible: the cost block takes the
SELECTED design's measured seconds-per-pair, and the power block takes the
census's measured trigger ratio and H12's own published discordance.

INPUTS, all measured, none assumed:
  --trigger-ratio   from analyse_census.py at the primary T (fork-free census)
  --secs-per-pair   from the pilot's own banked rows (H12 arm + H13 arm)
  --usd-per-core-h  anchored on H12's ACTUAL spend, see below
"""
import argparse
import json
import math


def mcnemar_mde(n_disc, alpha=0.05, power=0.80):
    """Smallest discordant split ratio detectable with n_disc discordant pairs.

    McNemar's exact-ish normal approximation: with n discordant pairs and true
    probability p that a discordant pair favours the treatment, the test
    statistic is (2p-1)*sqrt(n). Returns the p that reaches `power` at `alpha`.
    """
    z_a = 1.959963985                       # two-sided 0.05
    z_b = 0.8416212336                      # 80% power
    if n_disc <= 0:
        return float("nan")
    delta = (z_a + z_b) / math.sqrt(n_disc)  # = 2p-1
    return 0.5 * (1.0 + min(delta, 1.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trigger-ratio", type=float, required=True, nargs="+",
                    help="v2/v1 trigger-rate ratio(s), one per --thresholds")
    ap.add_argument("--thresholds", type=int, nargs="+", required=True,
                    help="the T each --trigger-ratio belongs to, e.g. 12 13")
    ap.add_argument("--theta-conversion", type=float, default=1.0,
                    help="MEASURED P(accepted flip | gated) for the v2-only "
                         "population divided by the same for v1. The CENSUS "
                         "CANNOT SEE THIS FACTOR — it is the census's known "
                         "blind spot, and only a paired arm measures it. "
                         "1.0 = assume the trigger ratio carries through")
    ap.add_argument("--secs-per-pair", type=float, required=True,
                    help="measured wall-seconds of CPU for one H12+H13 pair")
    ap.add_argument("--n", type=int, default=9000)
    ap.add_argument("--usd-per-core-h", type=float, default=0.10)
    # H12's published endpoint discordance, dies-ahead (the PRIMARY endpoint):
    ap.add_argument("--h12-da-rescued", type=int, default=896)
    ap.add_argument("--h12-da-broke", type=int, default=466)
    ap.add_argument("--h12-clear-rescued", type=int, default=1310)
    ap.add_argument("--h12-clear-broke", type=int, default=549)
    ap.add_argument("--h12-n", type=int, default=9000)
    ap.add_argument("--null-cost-inflation", type=float, default=1.45,
                    help="null games run longer; H12 measured 1.456M vs "
                         "1.004M plies")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    assert len(a.trigger_ratio) == len(a.thresholds), \
        "one trigger ratio per threshold"
    out = {"theta_conversion": a.theta_conversion, "by_threshold": {}}

    print("=" * 78)
    print("H13 ENDPOINT PRICING — power first, then cost")
    print("=" * 78)
    print("\nH13 flips on a strict SUPERSET of H12's flip plies, so the only "
          "decisions that can\ndiffer from H12 are the extra triggers that "
          "ALSO clear the theta margin.\n")
    if abs(a.theta_conversion - 1.0) > 1e-9:
        print(f"THETA-CONVERSION ADJUSTMENT = {a.theta_conversion:.2f}. The "
              f"census measures the TRIGGER ratio\nexactly but is blind to "
              f"P(margin passes | tie), which it can only observe on "
              f"v1-triggered\nplies. This factor is that blind spot, measured "
              f"on the paired pilot: the v2-only\npopulation converts gated "
              f"plies into accepted flips at {a.theta_conversion:.2f}x the "
              f"v1 rate.\n")

    print("POWER. Projected H13-vs-H12 discordance = H12's PUBLISHED "
          "discordance scaled by the\nextra accepted-flip dose. BREAK-EVEN = "
          "how favourable the extra flips must be,\nRELATIVE to H12's own "
          "flips, for N=9,000 to reach p<0.05 at 80% power.\n")
    hdr = (f"{'T':>3} {'dose':>7} {'endpoint':>11} {'disc':>6} "
           f"{'MDE split':>10} {'H12 split':>10} {'break-even':>11} {'verdict':>22}")
    print(hdr); print("-" * len(hdr))
    for T, ratio in zip(a.thresholds, a.trigger_ratio):
        extra = (ratio - 1.0) * a.theta_conversion
        out["by_threshold"][T] = {"trigger_ratio": ratio,
                                  "extra_flip_dose": extra, "endpoints": {}}
        for name, resc, broke in (("dies-ahead", a.h12_da_rescued,
                                   a.h12_da_broke),
                                  ("clear", a.h12_clear_rescued,
                                   a.h12_clear_broke)):
            disc = resc + broke
            scaled = disc * extra * (a.n / a.h12_n)
            mde = mcnemar_mde(scaled)
            actual = resc / disc
            be = mde / actual
            verdict = ("NEEDS BETTER THAN H12" if be > 1.0
                       else f"needs {100*be:.0f}% of H12")
            print(f"{T:>3} {100*extra:>6.1f}% {name:>11} {scaled:>6.0f} "
                  f"{mde:>10.3f} {actual:>10.3f} {be:>11.2f} {verdict:>22}")
            out["by_threshold"][T]["endpoints"][name] = {
                "scaled_discordant": scaled, "mde_split": mde,
                "h12_split": actual, "break_even_vs_h12": be,
                "needs_better_than_h12": bool(be > 1.0)}
        print()

    print("⚠ THE SCALING IS NOT A BOUND IN EITHER DIRECTION. It assumes the "
          "extra flips change\noutcomes as often as H12's own did. They are "
          "drawn from a DIFFERENT REGIME (median 15\nviruses, off-centre "
          "towers, vs H12's median-3-virus endgame), so this is an\n"
          "extrapolation across exactly the boundary this project has been "
          "burned on before.\nRead these rows as a scale, not as a power "
          "calculation.\n")
    print("⚠ CALIBRATION-POPULATION DRIFT, stated for BOTH thresholds rather "
          "than pre-decided:\n   T=13 admits ~13% more triggers — theta=0.5 "
          "was calibrated on substantially this\n   population, so the "
          "calibration carries.\n   T=12 admits ~26% more, roughly 2.2x the "
          "extra mass. Whether theta=0.5 still\n   describes that population "
          "is a judgment call, not a settled one: it is the owner's\n"
          "   to make, and it would want a re-calibration before an endpoint, "
          "not after.\n")

    core_h_p1 = a.n * a.secs_per_pair / 3600.0
    core_h_p2 = core_h_p1 * a.null_cost_inflation
    core_h = core_h_p1 + core_h_p2
    usd = core_h * a.usd_per_core_h
    print("COST.")
    print(f"  measured                 {a.secs_per_pair:8.1f} core-s / pair "
          f"(H12 arm + H13 arm)")
    print(f"  phase 1 true arm         {core_h_p1:8.0f} core-h")
    print(f"  phase 2 shuffled null    {core_h_p2:8.0f} core-h  "
          f"(x{a.null_cost_inflation} — null games run longer)")
    print(f"  TOTAL                    {core_h:8.0f} core-h")
    print(f"  at ${a.usd_per_core_h:.2f}/core-h  ->    ${usd:8.0f}")
    print(f"  if a dose VOID forces a null re-run (H12 paid this once): "
          f"${usd + core_h_p2*a.usd_per_core_h:.0f}")
    out["cost"] = {"secs_per_pair": a.secs_per_pair,
                   "core_h_phase1": core_h_p1, "core_h_phase2": core_h_p2,
                   "core_h_total": core_h, "usd_per_core_h": a.usd_per_core_h,
                   "usd": usd,
                   "usd_with_void_rerun": usd + core_h_p2*a.usd_per_core_h}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
        print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
