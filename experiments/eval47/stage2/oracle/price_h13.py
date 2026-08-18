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
    ap.add_argument("--trigger-ratio", type=float, required=True,
                    help="v2/v1 trigger-rate ratio at the primary T")
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

    extra = a.trigger_ratio - 1.0
    out = {"trigger_ratio": a.trigger_ratio, "extra_trigger_frac": extra}

    print("=" * 72)
    print("H13 ENDPOINT PRICING — power first, then cost")
    print("=" * 72)
    print(f"\nMeasured extra trigger dose at the primary threshold: "
          f"{100*extra:+.1f}%")
    print("H13 flips on a strict SUPERSET of H12's flip plies, so the only "
          "decisions that\ncan differ are the extra triggers that also pass "
          "the theta margin.\n")

    print("POWER. H12-vs-champion discordance is published; H13-vs-H12 "
          "discordance is\nthat scaled by the extra dose. This is an UPPER "
          "bound on the discordance and\ntherefore an OPTIMISTIC power "
          "estimate: it assumes the extra triggers change\noutcomes as often "
          "as H12's own triggers did.\n")
    print(f"{'endpoint':>8} {'H12 disc':>9} {'scaled':>8} "
          f"{'MDE split':>10} {'H12 actual split':>18} {'detectable?':>12}")
    for name, resc, broke in (("dies-ahead", a.h12_da_rescued, a.h12_da_broke),
                              ("clear", a.h12_clear_rescued,
                               a.h12_clear_broke)):
        disc = resc + broke
        scaled = disc * extra * (a.n / a.h12_n)
        mde = mcnemar_mde(scaled)
        actual = resc / disc
        det = "YES" if actual >= mde else "NO"
        print(f"{name:>8} {disc:>9d} {scaled:>8.0f} {mde:>10.3f} "
              f"{actual:>18.3f} {det:>12}")
        out[name] = {"h12_discordant": disc, "scaled_discordant": scaled,
                     "mde_split": mde, "h12_split": actual,
                     "detectable_at_h12_effect_size": det == "YES"}

    print("\nRead this as: at N=9,000 the H13-vs-H12 contrast can only reach "
          "significance\nif the EXTRA triggers are at least as favourable, "
          "per flip, as H12's own were.\nThe forced-move pricing of the 13:21 "
          "exhibit argues the opposite direction.\n")

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
