"""Did the census arm slow PHASE 1? Compares equal-length windows either side
of the census start, so the comparison is not confounded by window length.

Promised as a 01:45 re-check rather than trusted to memory — the 11-minute
window available at 00:58 was too short to claim anything (R49), and an
underpowered comparison that says "no slowdown" is exactly the reassurance
that should not be manufactured.
"""
import datetime, glob, os, time
CENSUS_START = datetime.datetime(2026, 8, 29, 0, 47, 42).timestamp()
D = "out/labels_m1/L20_unthin_held"
ts = sorted(os.path.getmtime(f) for f in glob.glob(os.path.join(D, "seed_*.json.gz")))
now = time.time()
after_h = (now - CENSUS_START) / 3600
if after_h < 0.75:
    print(f"only {after_h*60:.0f} min since census start — window still too "
          f"short to compare (need >=45 min). NOT claiming anything.")
    raise SystemExit(0)
w = min(after_h, (CENSUS_START - ts[0]) / 3600)     # equal-length windows
before = [t for t in ts if CENSUS_START - w * 3600 <= t < CENSUS_START]
after = [t for t in ts if t >= CENSUS_START]
rb, ra = len(before) / w, len(after) / after_h
print(f"equal windows of {w*60:.0f} min each")
print(f"  BEFORE census: {len(before):3d} games = {rb:5.1f} games/h")
print(f"  AFTER  census: {len(after):3d} games = {ra:5.1f} games/h")
d = (ra - rb) / rb * 100 if rb else float('nan')
print(f"  change: {d:+.0f}%")
# a rate difference this size is well inside Poisson noise at these counts
import math
se = math.sqrt(len(before) + len(after)) / w if w else float('inf')
print(f"  ~Poisson SE on the difference ~= {se:.1f} games/h; "
      f"observed difference {abs(ra-rb):.1f}")
print("  => " + ("NO evidence of slowdown (difference within noise); leave the "
                 "census running" if abs(ra - rb) < 2 * se else
                 "POSSIBLE slowdown — consider pausing the census"))
