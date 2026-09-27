"""T_stop determination — BLIND. Uses ROUND COUNTS ONLY (a quantity the admission
criterion permits below the floor). No outcome, no arm rate, is read or printed.

Pre-registered stop: >=120 completed rounds per arm OR the 6 h clock, WHICHEVER FIRST.
"""
import csv, datetime, os, sys
import rounds, reloads

CLOCK_STOP = datetime.datetime(2026, 9, 1, 6, 19, 0, tzinfo=datetime.timezone.utc).timestamp()
FLOOR = 120
R = reloads.reload_epochs()

rows = []
for i, f in enumerate(("ab_samples_L20_seg1.csv", "ab_samples_L20.csv")):
    if os.path.exists(f):
        for r in csv.DictReader(open(f)):
            r["block"] = "s%d_%s" % (i, r["block"]); rows.append(r)
blocks = {}
for r in rows:
    blocks.setdefault((r["arm"], r["block"]), []).append(
        (float(r["t_epoch"]),
         int(r["p1"]) if r["p1"] not in ("", "None") else None,
         int(r["p2"]) if r["p2"] not in ("", "None") else None,
         float(r["fill_p1"]), float(r["fill_p2"]),
         int(r["throat_p1"]), int(r["throat_p2"]),
         int(r["topcells_p1"]), int(r["topcells_p2"])))

# round-END timestamps per arm, reload-excluded (Amendment 3)
ends = {}
for (a, b), ser in blocks.items():
    kept, _ = reloads.drop_reload_rounds(rounds.transitions(ser), R)
    ends.setdefault(a, []).extend(r["end"] for r in kept)
for a in ends:
    ends[a].sort()

def iso(t): return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

print("completed rounds per arm, whole file: " +
      ", ".join("%s %d" % (a, len(ends[a])) for a in sorted(ends)))
floor_t = None
if all(len(v) >= FLOOR for v in ends.values()):
    floor_t = max(ends[a][FLOOR - 1] for a in sorted(ends))
    print("earliest instant BOTH arms had >=%d rounds: %s" % (FLOOR, iso(floor_t)))
    for a in sorted(ends):
        print("   %-9s reached %d rounds at %s" % (a, FLOOR, iso(ends[a][FLOOR - 1])))
else:
    print("floor never reached on at least one arm within the file")
print("6 h clock arm of the rule: %s" % iso(CLOCK_STOP))

T = min([t for t in (floor_t, CLOCK_STOP) if t is not None])
which = "FLOOR (>=120 rounds/arm)" if floor_t is not None and floor_t <= CLOCK_STOP else "6 h CLOCK"
print("\nT_stop = %s   (binding arm: %s)" % (iso(T), which))
disc = {a: sum(1 for t in ends[a] if t > T) for a in sorted(ends)}
print("rounds discarded as OUT OF PROTOCOL (after T_stop): " +
      ", ".join("%s %d" % (a, disc[a]) for a in sorted(disc)))
print("rounds retained: " + ", ".join("%s %d" % (a, len(ends[a]) - disc[a]) for a in sorted(disc)))
open("T_STOP.txt", "w").write("%f\n%s\n%s\n" % (T, iso(T), which))
print("\nwrote T_STOP.txt")
