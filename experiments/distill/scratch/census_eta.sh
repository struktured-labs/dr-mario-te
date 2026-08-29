#!/bin/bash
# census_eta.sh — post a MEASURED census rate once it has run 30 min at 15
# workers. Wired rather than promised: the trigger is hours away (after the
# handoff fires) and a promise that depends on someone being awake is how the
# owner ends up planning a Saturday around a projection.
#
# ⚠ Reports the rate MEASURED AT 15 WORKERS ONLY — games banked before the
# handoff ran at 3 workers and would drag the average into a number that
# describes neither configuration.
set -uo pipefail
cd /home/struktured/projects/dr-mario-distill-wt/experiments/distill
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
D=out/labels_m1/L20_census_fresh
say() { echo "[census-eta $(date +%H:%M:%S)] $*"; }

say "armed; waiting for the handoff to put the census on 15 workers"
# ⚠ NOT pgrep -f on the pattern: this script's OWN cmdline contains that
# string, so pgrep matches itself and fires instantly at 3 workers. That is
# the harness-pgrep-self-match trap already banked in this project's memory —
# match on a string UNIQUE TO THE TARGET, or better, do not pattern-match at
# all. Read the unit's own main PID instead.
worker_count() {
  local pid; pid=$(systemctl --user show -p MainPID --value drm-a5-census 2>/dev/null)
  [ -z "$pid" ] || [ "$pid" = "0" ] && { echo 0; return; }
  tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null \
    | grep -oE '\-\-workers [0-9]+' | grep -oE '[0-9]+' || echo 0
}
while [ "$(worker_count)" != "15" ]; do sleep 60; done
T0=$(date +%s)
N0=$(ls $D | grep -c '^seed_')
F0=$($PY - "$D" <<'PYX'
import glob,gzip,json,sys
print(sum(json.load(gzip.open(f,"rt"))["counters"]["tribunal_forks"]
          for f in glob.glob(sys.argv[1]+"/seed_*.json.gz")))
PYX
)
say "census at 15 workers; baseline ${N0}/128 games, ${F0} forks"
sleep 1800
T1=$(date +%s)
$PY - "$D" "$F0" "$T0" "$T1" <<'PYX'
"""⚠ REWRITTEN TO A WORKLOAD BASIS. The first version measured GAMES/HOUR over
30 minutes — the exact method shown biased for an imap_unordered pool, applied
at the point of MAXIMUM bias (the first 30 min returns the cheapest games), and
piped into an owner-facing ETA that compared itself to a projection built with
the same bias. Biased confirming biased reads as corroboration.

⚠ Forks/h is not bias-free either, but it errs the OTHER way and that is the
safe direction: per-fork cost FALLS as games get bigger (measured: 2.29 s/fork
at 253 forks/game vs 0.92 at 5495, slope 7.6 SE), so a rate measured on early
SMALL games understates later throughput. This ETA therefore runs LATE, not
early."""
import glob, gzip, json, sys, time, datetime, os
import numpy as np
D, F0, T0, T1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
recs = glob.glob(D + "/seed_*.json.gz")
F1 = sum(json.load(gzip.open(f, "rt"))["counters"]["tribunal_forks"] for f in recs)
hrs = (T1 - T0) / 3600
dF, n = F1 - F0, len(recs)
print("=== MEASURED CENSUS THROUGHPUT AT 15 WORKERS (workload basis) ===")
print(f"  {dF:,.0f} forks in {hrs*60:.0f} min = {dF/hrs:,.0f} forks/h "
      f"({n}/128 games banked)")
if dF < 20000:
    print(f"  ⚠ only {dF:,.0f} forks in the window — too little to quote a rate.")
    raise SystemExit(0)
BASE = "/home/struktured/projects/dr-mario-distill-wt/experiments/distill/out/labels_m1/L20"
tp = []
for f in sorted(glob.glob(BASE + "/seed_*.json.gz")):
    r = json.load(gzip.open(f, "rt"))
    if r["smoke"]:
        continue
    tp.append(sum(1 for _p, h in enumerate(r["heights_trace"])
                  if max(h[3], h[4]) >= 13))
tp = np.array(tp, float)
left = 128 - n
tot, se = left * tp.mean(), np.sqrt(left) * tp.std(ddof=1)
rate = dF / hrs
fmt = lambda t: datetime.datetime.fromtimestamp(t).strftime("%a %d %H:%M")
now = time.time()
print(f"  remaining {left} games: {tot:,.0f} +/- {se:,.0f} trigger plies "
      f"(ESTIMATED — these seeds were unplayed, no traces)")
for lab, t in (("-1 SE", tot - se), ("CENTRAL", tot), ("+1 SE", tot + se)):
    print(f"    {lab:>8}  census done {fmt(now + t*95.0/rate*3600)}")
print("  (⚠ errs LATE: rate measured on early SMALL games, which have the")
print("   WORST per-fork throughput. Team-lead's 11:30-12:30 projection used")
print("   worker-min/GAME from the cheap end and is optimistic by ~1.5x.)")
PYX
