"""Score the flip screen and ROUTE the pre-registered decision.

The decision rule is PREREG_H13.md sec 9, fixed before any screen data existed:
  NEGATIVE (mean fair gain < 0, CI excludes 0) -> gate-v2 REFUTED, close #110
  NULL     (CI spans 0, |mean| small)          -> churn, NO-GO on the endpoint
  POSITIVE (CI excludes 0, mean > 0)           -> endpoint spend unblocked

It is encoded here rather than applied by hand, and `--selftest` drives it with
synthetic tables straddling every threshold — including the case built to catch
the failure this lane most expects (a positive mean that the RAND control
matches, i.e. "better than the keep" at the scale of picking a legal move at
random). A verdict script that has only ever seen one real table has not been
shown to discriminate either ([[dr-mario-measurement-rules]] #28 corollary).

ENDPOINT: mean over flips of (mean fork progress on the H13 flip) minus (mean
fork progress on the H12 keep), both averaged over the SAME K unseen capsule
streams. Flip-clustered bootstrap CI, because the K streams within one flip are
not independent observations.

THE CONTROL IS PART OF THE VERDICT, not a footnote: `rand` is a legal action
that is neither the keep nor the flip, scored on the identical streams. If
flip-vs-keep is not distinguishable from rand-vs-keep, the screen has not shown
that gate-v2 selects anything — it has shown that perturbing the champion's
choice at these plies is roughly neutral, which is the churn hypothesis.
"""
import argparse
import json
import sys

import numpy as np


def load(path):
    flips = []
    games = 0
    for line in open(path):
        try:
            d = json.loads(line)
        except Exception:
            continue
        games += 1
        for e in d.get("events", []):
            k = np.array([p for _s, p in e["keep"]], float)
            f = np.array([p for _s, p in e["flip"]], float)
            r = (np.array([p for _s, p in e["rand"]], float)
                 if e.get("rand") else None)
            ks = np.array([s for s, _p in e["keep"]], float)
            fs = np.array([s for s, _p in e["flip"]], float)
            flips.append({
                "seed": e["seed"], "ply": e["ply"], "maxh": e["maxh"],
                "viruses": e["viruses"], "K": len(k),
                "d_flip": float(f.mean() - k.mean()),
                "d_rand": (float(r.mean() - k.mean())
                           if r is not None and len(r) else np.nan),
                "surv_keep": float(ks.mean()), "surv_flip": float(fs.mean()),
                "wins": int((f > k).sum()), "ties": int((f == k).sum()),
                "losses": int((f < k).sum())})
    return flips, games


def boot_ci(x, n=10000, seed=20260818):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    m = x[idx].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def route(mean, lo, hi, rand_mean, rand_lo, rand_hi, n, floor):
    """The pre-registered routing. Returns (verdict, reason)."""
    if n < 40:
        return "UNDERPOWERED", (
            f"only {n} screened flips; the rule needs a usable n before it "
            f"may be read. UNDERPOWERED is not NULL (rule 13)")
    if hi < 0:
        return "REFUTED", "mean fair gain is negative and the CI excludes 0"
    if lo > 0:
        if not (rand_hi < lo):
            return "POSITIVE_BUT_UNCONTROLLED", (
                "flip beats keep, but the RANDOM-action control is not "
                "separated from it — consistent with 'perturbing the choice "
                "here is neutral-to-good', not with gate-v2 selecting well")
        return "POSITIVE", (
            "mean fair gain is positive, CI excludes 0, and the flip is "
            "separated from the random-action control")
    if abs(mean) < floor:
        return "NULL", (
            f"CI spans 0 and |mean| {abs(mean):.3f} is below the "
            f"interpretability floor {floor}: churn, not judgment")
    return "NULL_WIDE", "CI spans 0 but the point estimate is not small; more n"


def selftest(floor):
    """Drive the router with tables straddling every threshold."""
    cases = [
        ("clear negative",  -1.2, -1.9, -0.5,  0.0, -0.4,  0.4, 200, "REFUTED"),
        ("clear positive",  +1.2, +0.5, +1.9, -0.1, -0.5,  0.3, 200, "POSITIVE"),
        ("positive but rand matches", +1.2, +0.5, +1.9,
                                       +1.0, +0.4, +1.6, 200,
         "POSITIVE_BUT_UNCONTROLLED"),
        ("tiny null",       +0.01, -0.2, +0.2, 0.0, -0.3, 0.3, 200, "NULL"),
        ("wide null",       +0.9, -0.4, +2.2,  0.0, -0.4, 0.4, 200, "NULL_WIDE"),
        ("too few flips",   -1.2, -1.9, -0.5,  0.0, -0.4, 0.4,  12,
         "UNDERPOWERED"),
        ("boundary hi==0",  -0.5, -1.0,  0.0,  0.0, -0.4, 0.4, 200, "NULL_WIDE"),
    ]
    ok = True
    print("ROUTER SELFTEST (synthetic tables, no real data):")
    for name, m, lo, hi, rm, rlo, rhi, n, want in cases:
        got, _ = route(m, lo, hi, rm, rlo, rhi, n, floor)
        good = got == want
        ok &= good
        print(f"  {name:28s} -> {got:26s} {'ok' if good else 'FAIL want '+want}")
    print("ROUTER SELFTEST", "PASS" if ok else "FAIL")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen")
    ap.add_argument("--floor", type=float, default=0.25,
                    help="interpretability floor on mean fork-progress gain")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest(a.floor) else 1)
    if not a.screen:
        ap.error("--screen is required unless --selftest")

    flips, games = load(a.screen)
    n = len(flips)
    print(f"SCREEN {a.screen}: {games} games, {n} screened v2-only flips "
          f"({n/max(games,1):.2f} per game)")
    if n == 0:
        print("no flips yet")
        return
    d = np.array([f["d_flip"] for f in flips])
    r = np.array([f["d_rand"] for f in flips])
    r = r[~np.isnan(r)]
    lo, hi = boot_ci(d)
    rlo, rhi = (boot_ci(r) if len(r) else (float("nan"), float("nan")))
    w = sum(f["wins"] for f in flips)
    t = sum(f["ties"] for f in flips)
    l = sum(f["losses"] for f in flips)

    print(f"\n  FLIP vs KEEP   mean {d.mean():+.3f} viruses "
          f"[{lo:+.3f}, {hi:+.3f}]   median {np.median(d):+.3f}")
    print(f"  RAND vs KEEP   mean {r.mean():+.3f} "
          f"[{rlo:+.3f}, {rhi:+.3f}]   <- control: a legal non-keep, "
          f"non-flip action")
    print(f"  per-stream W/T/L on progress: {w}/{t}/{l}")
    print(f"  flips with d_flip > 0: {int((d>0).sum())}/{n}")
    print(f"  survival  keep {np.mean([f['surv_keep'] for f in flips]):.3f}  "
          f"flip {np.mean([f['surv_flip'] for f in flips]):.3f}")

    verdict, reason = route(d.mean(), lo, hi, r.mean() if len(r) else 0.0,
                            rlo if len(r) else 0.0, rhi if len(r) else 0.0,
                            n, a.floor)
    print(f"\n  PRE-REGISTERED VERDICT: {verdict}\n  {reason}")
    print("\n  SCOPE: prices PER-FLIP quality, not the compounding of many "
          "flips across a\n  game. RULE-OUT instrument: a negative kills "
          "gate-v2; a positive licenses the\n  endpoint, it does not replace "
          "it.")
    if a.out:
        json.dump({"screen": a.screen, "games": games, "n_flips": n,
                   "mean_flip_vs_keep": float(d.mean()), "ci95": [lo, hi],
                   "mean_rand_vs_keep": (float(r.mean()) if len(r) else None),
                   "rand_ci95": [rlo, rhi], "wins": w, "ties": t, "losses": l,
                   "verdict": verdict, "reason": reason,
                   "floor": a.floor}, open(a.out, "w"), indent=1)
        print(f"-> {a.out}")


if __name__ == "__main__":
    main()
