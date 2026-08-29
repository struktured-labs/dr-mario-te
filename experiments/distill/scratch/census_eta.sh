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
say "census now at 15 workers; baseline ${N0}/128 at $(date +%H:%M:%S)"
sleep 1800
N1=$(ls $D | grep -c '^seed_'); T1=$(date +%s)
H=$(python3 -c "print(($T1-$T0)/3600)")
$PY - "$N0" "$N1" "$H" <<'PYEOF'
import sys, datetime, time
n0, n1, h = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
done, rate = n1 - n0, (n1 - n0) / h
print(f"=== MEASURED CENSUS RATE AT 15 WORKERS ===")
print(f"  {done} games in {h*60:.0f} min = {rate:.1f} games/h")
if done < 3:
    print(f"  ⚠ only {done} games in the window — too few to quote a rate (R49)."
          f" Re-measure over a longer window before telling anyone a time.")
else:
    rem = 128 - n1
    eta = time.time() + rem / rate * 3600
    dt = datetime.datetime.fromtimestamp(eta)
    print(f"  banked {n1}/128, remaining {rem}")
    print(f"  ETA at the OBSERVED rate: {dt.strftime('%a %d %H:%M')} local"
          f"  (+{rem/rate:.1f} h)")
    print(f"  team-lead's modelled figure was 11:30-12:30 local")
    print(f"  => {'AGREES with the projection' if 11 <= dt.hour <= 13 else 'DIVERGES from the projection — correct it with the owner'}")
PYEOF
