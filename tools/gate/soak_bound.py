#!/usr/bin/env python3
"""soak_bound.py -- turn a soak log into a BOUND, in the unit the owner cares about.

A bare "zero events" is not a result; the question is always "zero over how much play?".
This reads probe_soak.log and prints, per canary, the one-sided 95% upper confidence limit on
the event rate expressed as MINUTES OF PLAY between events.

  k = 0  -> rule of three: lambda_hi = 3/N per frame, so >= N/3 frames between events.
  k > 0  -> exact Poisson upper limit: the lambda_hi solving P(X <= k | lambda_hi) = 0.05,
            found by bisection on the Poisson CDF (no scipy dependency).

⚠ Two honesty notes that belong next to any number this prints:
  * Frames are converted at the NES NTSC rate 60.0988 fps. That is EMULATED play time, which is
    the right unit -- the soak runs faster than real time but a frame is still a frame.
  * The gate's matches are short (P1 is an idle human seat, so it tops out fast). Match COUNT
    therefore is not comparable to real matches against a person; frames are. Both are printed.

Usage: soak_bound.py <probe_soak.log> [more logs...]
"""
import math
import re
import sys

FPS = 60.0988

# canary name -> (regex key in the SUMMARY/SOAK line, human description)
CANARIES = [
    ("MIXED_PRG_nonboot", "mixed shift-register load into the PRG register (the catastrophic MMC1 interleave)"),
    # ⚠ RAW `wipes` IS NOT AN EVENT COUNT. The detector fires on any $0324 (virus counter)
    # transition >0 -> 0, and the END OF EVERY MATCH legitimately does exactly that. The tuck-phase
    # gate saw 19 zeroings against 19 match-ends and they were all the normal path. So the healthy
    # baseline is ~1 per match-end, NOT zero, and printing the raw number in a table of canaries
    # would read as hundreds of RAM wipes on a clean cart -- a false alarm loud enough to discredit
    # every other row. The anomalous count is what matters: wipes - match_ends, floored at 0, and
    # cross-checked against the per-MATCH d_wipes distribution (any match with d_wipes >= 2 is a
    # real candidate). Both numbers are printed.
    ("wipes", "$0324 zeroings -- RAW, includes the legitimate one per match end"),
    ("wipes_anom", "RAM wipes IN EXCESS of one per match end (the real canary)"),
    # ⚠ Same trap as `wipes`: $8036 is executed ONCE legitimately at power-on, so the healthy
    # baseline is 1 PER BOOT, not 0 -- the tuck-phase gate recorded exactly "1 bank-0 entry (the
    # boot one)". Each seed segment is its own boot, so the pooled baseline is one per segment.
    ("soft8036", "bank-0 entries at $8036 -- RAW, includes the power-on one"),
    ("soft8036_anom", "bank-0 soft entries BEYOND the power-on one (the real canary)"),
    ("brk_a02e", "BRK-loop hit at $A02E"),
    ("ABORT_4to0", "catastrophic mid-match abort to title (the v6c signature)"),
    ("title0", "unrequested return to title from a live state"),
    ("busyEp", "stuck-BUSY episode (driver re-entrancy latch held)"),
    ("modeStall", "hard hang (one mode held past threshold)"),
    ("gapStall", "failure to progress across a match boundary"),
    ("srchStall", "search stall (mode 4 with the AI no longer asking)"),
    # ⚠ key is MISMATCH, which is what the ACHK line actually emits. It was "amism" here,
    # which appears in no log, so `if key not in vals: continue` skipped the single most
    # important new canary SILENTLY -- the A-check would have been absent from the bound
    # table while everything else looked complete.
    ("MISMATCH", "accumulator corrupted across the NMI (the v8 DRRTIVEC defect)"),
    ("tuckwr", "write to the tuck executor's cart state (must be 0 on a DRTUCK=0 cart)"),
]


def poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) for Poisson(lam), computed stably in log space."""
    if lam <= 0:
        return 1.0
    total = 0.0
    log_lam = math.log(lam)
    for i in range(k + 1):
        total += math.exp(-lam + i * log_lam - math.lgamma(i + 1))
    return min(total, 1.0)


def upper_limit(k: int, conf: float = 0.95) -> float:
    """One-sided upper confidence limit on the Poisson mean given k observed events."""
    alpha = 1.0 - conf
    if k == 0:
        return -math.log(alpha)          # = 3.0 to 2 dp -- the "rule of three"
    lo, hi = float(k), float(k) + 10.0
    while poisson_cdf(k, hi) > alpha:
        hi *= 2.0
        if hi > 1e9:
            return hi
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if poisson_cdf(k, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def fmt_time(frames: float) -> str:
    if frames == float("inf"):
        return "inf"
    secs = frames / FPS
    if secs < 90:
        return f"{secs:.0f} s"
    if secs < 5400:
        return f"{secs / 60:.1f} min"
    return f"{secs / 3600:.2f} h"


def parse(path: str) -> dict:
    vals, meta = {}, {}
    txt = open(path, "r", errors="replace").read()
    for line in txt.splitlines():
        if line.startswith(("SUMMARY ", "SOAK ", "SOAK2 ", "ACHK ")):
            for m in re.finditer(r"(\w+)=([-\w.]+)", line):
                vals[m.group(1)] = m.group(2)
        if line.startswith("CKPT "):
            meta["last_ckpt"] = line
    return vals, meta


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    pool = {"frames": 0, "play4": 0, "ends": 0, "logs": 0, "achk": [], "k": {}}
    for path in sys.argv[1:]:
        vals, meta = parse(path)
        if not vals:
            print(f"\n=== {path}\n  NO SUMMARY/SOAK LINE -- this log is not a result. "
                  f"{'last ' + meta['last_ckpt'] if 'last_ckpt' in meta else 'no checkpoints either.'}")
            continue
        try:
            n = int(vals.get("frames", "0"))
        except ValueError:
            n = 0
        print(f"\n=== {path}")
        print(f"  tag                 {vals.get('tag')}")
        print(f"  frames              {n:,}   = {fmt_time(n)} of emulated play")
        print(f"  matches started     {vals.get('matches_started')}")
        print(f"  matches ended       {vals.get('matches_ended')}  (clean {vals.get('clean_ends')})")
        print(f"  wall / fps          {vals.get('wall')} / {vals.get('fps')}")
        print(f"  A-integrity verdict {vals.get('verdict', '<absent>')}"
              f"  shield_hits={vals.get('shield_CEEC')} nmi={vals.get('nmi_events')}")
        if n <= 0:
            print("  frames=0 -- no bound computable")
            continue
        # ⚠ CHOOSING THE DENOMINATOR. Frames are the right exposure unit for a per-hook fault
        # (the MMC1 interleave fires inside the driver hook, which runs every frame). They are the
        # WRONG unit for the DRHOLDBOARD/v6c class, which can only fire when a match ENDS: for
        # those the exposure is match boundaries, and this rig deliberately produces them far
        # faster than real play does, because P1 is an idle seat that tops out in ~500 frames.
        # Reporting only the frame bound would understate boundary coverage by more than an order
        # of magnitude; reporting only the match bound would overstate per-frame coverage. Both.
        # Faults that can only fire when a match ENDS get match-ends as their denominator.
        BOUNDARY = {"ABORT_4to0", "title0", "gapStall"}
        # Faults that fire inside the per-frame driver hook get LIVE-PLAY frames, not wall frames.
        # play4 <= frames always, so this is the conservative choice, and it is also the unit the
        # owner actually means by "how long can I play".
        PLAY = {"MIXED_PRG_nonboot", "wipes_anom", "soft8036_anom", "brk_a02e", "MISMATCH", "busyEp", "srchStall"}
        try:
            m = int(vals.get("matches_ended", "0"))
        except ValueError:
            m = 0
        try:
            p4 = int(vals.get("play4_frames", "0"))
        except ValueError:
            p4 = 0
        if p4:
            print(f"  live-play frames    {p4:,}   = {fmt_time(p4)} in mode 4 "
                  f"({100.0 * p4 / n:.0f}% of the run)")
        # derived: zeroings beyond the one-per-match-end the normal path produces
        try:
            vals["wipes_anom"] = str(max(0, int(vals.get("wipes", 0)) - m))
        except ValueError:
            pass
        try:
            vals["soft8036_anom"] = str(max(0, int(vals.get("soft8036", 0)) - 1))
        except ValueError:
            pass
        print(f"  {'canary':<22} {'k':>5}  {'95% upper bound on the rate':<32} description")
        for key, desc in CANARIES:
            if key not in vals:
                continue
            try:
                k = int(vals[key])
            except ValueError:
                continue
            lam_hi = upper_limit(k)                 # events per whole run
            RAW_BASELINED = {"wipes": "expected ~1 per match end",
                             "soft8036": "expected 1 per boot (power-on)"}
            flag = "   <<< FIRED" if (k > 0 and key not in RAW_BASELINED) else ""
            if key in RAW_BASELINED and k > 0:
                flag = f"   ({RAW_BASELINED[key]})"
            if key in BOUNDARY and m > 0:
                bound = f"<= 1 per {m / lam_hi:,.0f} match-ends"
            elif key in PLAY and p4 > 0:
                bound = f"<= 1 per {fmt_time(p4 / lam_hi)} of live play"
            else:
                bound = f"<= 1 per {fmt_time(n / lam_hi)}"
            print(f"  {key:<22} {k:>5}  {bound:<32} {desc}{flag}")
        if m > 0:
            print(f"  [{m} match-ends observed; a match here is ~{n / m:.0f} frames because P1 is an")
            print("   idle seat, so match-ends accrue MUCH faster than in real play. Total frames")
            print("   therefore overstate real-match exposure -- which is why the crash class is")
            print("   bounded per match-end and the per-hook class per live-play minute.]")
        # accumulate for the pooled bound
        pool["logs"] += 1
        pool["frames"] += n
        pool["play4"] += p4
        pool["ends"] += m
        pool["achk"].append(vals.get("verdict", "<absent>"))
        for key, _ in CANARIES:
            if key in vals:
                try:
                    pool["k"][key] = pool["k"].get(key, 0) + int(vals[key])
                except ValueError:
                    pass

    # ---------------- POOLED ----------------
    # ⚠ THE HEADLINE IS THE POOLED BOUND, NOT THE PER-SEGMENT ONE. The soak is split into seed
    # segments so that a crash costs one segment instead of the run, and so that four independent
    # capsule streams are covered rather than one. But each segment reporting "1 per N/3 frames"
    # UNDERSTATES the evidence by the number of segments: the segments are independent observations
    # of the same cart, so their exposure ADDS. Four clean segments of N frames bound the rate at
    # 1 per 4N/3, not 1 per N/3. Printing only the per-segment numbers would have thrown away 75%
    # of a five-hour run.
    if pool["logs"] > 1:
        n, p4, m = pool["frames"], pool["play4"], pool["ends"]
        print("\n" + "=" * 78)
        print(f"POOLED OVER {pool['logs']} SEGMENTS  (independent seeds, same cart -- exposure adds)")
        print("=" * 78)
        print(f"  frames              {n:,}   = {fmt_time(n)} of emulated play")
        print(f"  live-play frames    {p4:,}   = {fmt_time(p4)} in mode 4"
              + (f" ({100.0 * p4 / n:.0f}% of the run)" if n else ""))
        print(f"  match-ends          {m}")
        print(f"  A-integrity         {', '.join(pool['achk'])}")
        BOUNDARY = {"ABORT_4to0", "title0", "gapStall"}
        PLAY = {"MIXED_PRG_nonboot", "wipes_anom", "soft8036_anom", "brk_a02e", "MISMATCH", "busyEp", "srchStall"}
        pool["k"]["wipes_anom"] = max(0, pool["k"].get("wipes", 0) - m)
        # soft8036_anom is already summed per-log (one boot allowance PER SEGMENT);
        # do NOT recompute it as pooled-minus-one, which would allow only one boot
        # across four segments and manufacture three phantom events.
        print(f"  {'canary':<22} {'k':>5}  {'95% upper bound on the rate':<34} description")
        for key, desc in CANARIES:
            if key not in pool["k"]:
                continue
            k = pool["k"][key]
            lam_hi = upper_limit(k)
            RAW_BASELINED = {"wipes": "expected ~1 per match end",
                             "soft8036": "expected 1 per boot (power-on)"}
            flag = "   <<< FIRED" if (k > 0 and key not in RAW_BASELINED) else ""
            if key in RAW_BASELINED and k > 0:
                flag = f"   ({RAW_BASELINED[key]})"
            if key in BOUNDARY and m > 0:
                bound = f"<= 1 per {m / lam_hi:,.0f} match-ends"
            elif key in PLAY and p4 > 0:
                bound = f"<= 1 per {fmt_time(p4 / lam_hi)} of live play"
            else:
                bound = f"<= 1 per {fmt_time(n / lam_hi)}"
            print(f"  {key:<22} {k:>5}  {bound:<34} {desc}{flag}")
        if p4:
            print(f"\n  HEADLINE, conservative unit: with zero events, 95% upper bound is")
            print(f"    1 catastrophic event per {fmt_time(p4 / upper_limit(0))} OF LIVE PLAY")
            print(f"    (per wall-clock emulated time, {fmt_time(n / upper_limit(0))})")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
