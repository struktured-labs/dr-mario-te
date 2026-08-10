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
    ("wipes", "RAM wipe (virus counter latched to 0 outside the end-of-match path)"),
    ("soft8036", "bank-0 soft entry at $8036"),
    ("brk_a02e", "BRK-loop hit at $A02E"),
    ("ABORT_4to0", "catastrophic mid-match abort to title (the v6c signature)"),
    ("title0", "unrequested return to title from a live state"),
    ("busyEp", "stuck-BUSY episode (driver re-entrancy latch held)"),
    ("modeStall", "hard hang (one mode held past threshold)"),
    ("gapStall", "failure to progress across a match boundary"),
    ("srchStall", "search stall (mode 4 with the AI no longer asking)"),
    ("amism", "accumulator corrupted across the NMI (the v8 DRRTIVEC defect)"),
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
        BOUNDARY = {"ABORT_4to0", "title0", "gapStall"}
        try:
            m = int(vals.get("matches_ended", "0"))
        except ValueError:
            m = 0
        print(f"  {'canary':<22} {'k':>5}  {'95% upper bound on the rate':<30} description")
        for key, desc in CANARIES:
            if key not in vals:
                continue
            try:
                k = int(vals[key])
            except ValueError:
                continue
            lam_hi = upper_limit(k)                 # events per whole run
            flag = "   <<< FIRED" if k > 0 else ""
            if key in BOUNDARY and m > 0:
                per = lam_hi / m
                bound = f"<= 1 per {1.0 / per:,.0f} match-ends"
            else:
                per_frame = lam_hi / n
                bound = f"<= 1 per {fmt_time(1.0 / per_frame)}"
            print(f"  {key:<22} {k:>5}  {bound:<30} {desc}{flag}")
        if m > 0:
            print(f"  [{m} match-ends observed; a match here is ~{n / m:.0f} frames because P1 is an")
            print("   idle seat, so match-ends accrue much faster than in real play]")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
