#!/usr/bin/env python3
"""Firmware THETA mini-sweep (task #17 stage 3, team-lead directive after pass-1's L11
wash: paired pills -3.84 [-10.14,+2.51], fires/game 4.38 in firmware vs 2.80 at the
offline theta*=150 -- the same NUMERIC theta is a LOOSER gate in shipped-eval units,
consistent with the already-documented vrdy12/matched60 value-scale gap between
fast_rtl_x.py's offline proof and build_copro_d3.build_image()'s real shipped weights.
Off-arm cross-validation was clean (98.3%), so this is a genuine transfer question, not
a broken harness.

Runs the ON-ARM ONLY at theta in {250, 400}, n=40 (the FIRST 40 seeds of pass-1's L11
seed set, i.e. seeds 0..39 -- pass-1 used seed_offset=0 for its n=120 run, so these are
a strict prefix, not a different sample), against pass-1's ALREADY-MEASURED OFF-ARM
results loaded from pass1_L11.json rather than re-running the off arm (theta has zero
effect on it -- EMIT_TUCK_V3=False never assembles tuck_root_extension, verified via
the image-hash self-check in tuck_v3.py's commit message: off-arm hashes are IDENTICAL
across theta in {150,250,400}). Also reports theta=150's own n=40 slice (pulled from the
same pass-1 JSON, both arms) as the sweep's own zeroth point, so all three theta values
land in one comparable table.

Self-check inherited from ab_root_firmware.py's startup assert: each arm's hash is
printed, and theta=150 is asserted byte-identical to pass-1's recorded on-arm hash
before any of THIS script's own real compute runs (belt-and-suspenders on top of the
per-commit verification already done for the THETA knob itself).
"""
from __future__ import annotations

import sys
import os
import json
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ab_root_firmware as AF  # noqa: E402  reuses _init/play/boot_ci/sign_test_p/_log_rss

PASS1_ON_HASH = "74d34cc5a1b6a0d5f88e299051e1d5fea4b6e456015ee2f8e588ffae60c6ff75"
PASS1_L11_JSON = os.path.join(
    "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/"
    "02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tuck_repro/pass1_out", "pass1_L11.json")

N_SWEEP = 40
SEED_OFFSET = 0   # first 40 of pass-1's own seed set (which used seed_offset=0, n=120)
TARGET_FIRES = 2.8   # the offline theta*=150 reference rate


def _init_on_arm(level, theta):
    AF._init(level, tuck=1, theta=theta)


def run_on_arm(level, seeds, workers, theta, seed_offset=0):
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_on_arm,
                              initargs=(level, theta)) as ex:
        h = ex.submit(AF._report_hash).result()
        print(f"  theta={theta} on-arm image sha256={h}", flush=True)
        if theta == 150:
            assert h == PASS1_ON_HASH, (
                f"theta=150 self-check FAILED: this build hashes {h}, pass-1's recorded "
                f"on-arm hash was {PASS1_ON_HASH} -- refusing to trust this sweep's "
                f"theta=150 comparison point until that's understood.")
        futs = [ex.submit(AF.play, s) for s in range(seed_offset, seed_offset + seeds)]
        rows = []
        for i, f in enumerate(as_completed(futs)):
            rows.append(f.result())
            if (i + 1) % max(1, seeds // 4) == 0 or (i + 1) == seeds:
                AF._log_rss(f"L{level} theta={theta} on-arm after {i + 1}/{seeds} games")
    print(f"  L{level} theta={theta} on-arm done ({len(rows)} games)", flush=True)
    return {r["seed"]: r for r in rows}


def compare(off, on, seeds, theta):
    both = [s for s in seeds if off[s]["won"] and on[s]["won"]]
    d = [on[s]["pills"] - off[s]["pills"] for s in both]
    lo, hi = AF.boot_ci(d)
    better = sum(1 for x in d if x < 0)
    worse = sum(1 for x in d if x > 0)
    c_off = sum(off[s]["won"] for s in seeds) / len(seeds)
    c_on = sum(on[s]["won"] for s in seeds) / len(seeds)
    fires = [on[s]["fired"] for s in seeds]
    import statistics as st
    out = {
        "theta": theta, "n": len(seeds),
        "paired_pills_delta_mean": st.mean(d) if d else float("nan"),
        "paired_pills_ci": [lo, hi],
        "paired_n": len(both), "better": better, "worse": worse, "tie": len(d) - better - worse,
        "clear_off": c_off, "clear_on": c_on,
        "fires_per_game": st.mean(fires) if fires else 0.0,
    }
    real = (hi < 0 or lo > 0)
    verdict = "REAL" if real else "WASH"
    print(f"theta={theta}: paired pills {out['paired_pills_delta_mean']:+.2f} "
          f"[{lo:+.2f},{hi:+.2f}] {verdict}  clear {c_off:.1%}->{c_on:.1%}  "
          f"fires/g {out['fires_per_game']:.2f}  (n={len(seeds)}, paired n={len(both)})",
          flush=True)
    return out, real


def interpolate_theta(points):
    """Linear interpolation across the swept (theta, fires/game) points to estimate
    where fires/game would cross TARGET_FIRES=2.8 (the offline theta*=150 reference
    rate) -- a calibration estimate, not a claim that the relationship is truly linear
    outside the swept range."""
    pts = sorted(points, key=lambda p: p[0])
    for (t0, f0), (t1, f1) in zip(pts, pts[1:]):
        if (f0 - TARGET_FIRES) * (f1 - TARGET_FIRES) <= 0 and f0 != f1:
            frac = (TARGET_FIRES - f0) / (f1 - f0)
            return t0 + frac * (t1 - t0)
    return None   # target not bracketed by the swept points -- extrapolation not attempted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--full-n", type=int, default=120,
                     help="n to use for the confirm run if a theta turns the delta real")
    a = ap.parse_args()

    print(f"Loading pass-1 off-arm results from {PASS1_L11_JSON}", flush=True)
    with open(PASS1_L11_JSON) as fh:
        pass1 = json.load(fh)
    off_all = {r["seed"]: r for r in pass1["off"]}
    on_150_all = {r["seed"]: r for r in pass1["on"]}
    sweep_seeds = list(range(SEED_OFFSET, SEED_OFFSET + N_SWEEP))
    assert all(s in off_all for s in sweep_seeds), "pass-1 off-arm JSON missing seeds 0-39"
    assert all(s in on_150_all for s in sweep_seeds), "pass-1 on-arm JSON missing seeds 0-39"
    off = {s: off_all[s] for s in sweep_seeds}

    print(f"\n=== THETA MINI-SWEEP, L11, n={N_SWEEP} (seeds {sweep_seeds[0]}-{sweep_seeds[-1]}) ===")
    points = []   # (theta, out_dict, real_bool)

    on_150 = {s: on_150_all[s] for s in sweep_seeds}
    out150, real150 = compare(off, on_150, sweep_seeds, 150)
    points.append((150, out150, real150))

    for theta in (250, 400):
        on = run_on_arm(11, N_SWEEP, a.workers, theta, seed_offset=SEED_OFFSET)
        out, real = compare(off, on, sweep_seeds, theta)
        points.append((theta, out, real))

    print("\n=== SWEEP SUMMARY (n=40 each) ===")
    for theta, out, real in points:
        print(f"  theta={theta:4d}  delta {out['paired_pills_delta_mean']:+7.2f} "
              f"[{out['paired_pills_ci'][0]:+7.2f},{out['paired_pills_ci'][1]:+7.2f}]  "
              f"{'REAL' if real else 'WASH'}  fires/g {out['fires_per_game']:.2f}")

    fire_points = [(t, o["fires_per_game"]) for t, o, _ in points]
    theta_star = interpolate_theta(fire_points)
    if theta_star is not None:
        print(f"\nInterpolated theta at fires/game~={TARGET_FIRES}: {theta_star:.0f}")
    else:
        print(f"\nfires/game did not bracket {TARGET_FIRES} across the swept thetas "
              f"({[f'{t}:{f:.2f}' for t, f in fire_points]}) -- no interpolation.")

    any_real = [(t, o) for t, o, r in points if r]
    if any_real:
        print(f"\n{len(any_real)} theta(s) turned the delta REAL at n=40: "
              f"{[t for t, _ in any_real]}. Confirming at n={a.full_n} (standing pass-1 "
              f"full-sample size) for each.")
        for theta, _ in any_real:
            on_full = run_on_arm(11, a.full_n, a.workers, theta, seed_offset=0)
            off_full = {s: off_all[s] for s in range(a.full_n) if s in off_all}
            # off-arm at n=120 already fully covers 0..119 from pass-1's own run;
            # on_full only just ran the same range for this theta.
            full_seeds = sorted(set(off_full) & set(on_full))
            out_full, real_full = compare(off_full, on_full, full_seeds, theta)
            print(f"  CONFIRM theta={theta} at n={len(full_seeds)}: "
                  f"{'REAL' if real_full else 'WASH ON CONFIRM'}")
    else:
        print("\nEVERYTHING WASHES across {150, 250, 400} at n=40 -- per standing "
              "instruction, this is a genuine firmware-transfer question, not a tuning "
              "problem. Next step is DIAGNOSIS: a 20-board offline-root-value vs "
              "firmware-D_V1 comparison for the SAME tuck candidate, to localize which "
              "of {eh add-on scale at the theta compare, DISC blend arithmetic, imm "
              "scale} actually diverges -- not another theta value.")

    print("\nDONE")


if __name__ == "__main__":
    main()
