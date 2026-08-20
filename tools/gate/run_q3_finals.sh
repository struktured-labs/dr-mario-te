#!/bin/bash
# Q=3 finals, chained: 18k probe6 A/B, then the forced-release liveness A/B.
# Each stage checks the previous stage's success marker (a gate that must run
# before data needs its own marker).
set -eo pipefail
D=/home/struktured/projects/dr-mario-pipeline-wt
FRAMES=18000 bash "$D/tools/gate/run_pipeline_battery.sh"
[[ -f "$D/tmp/pipebattery/on.ok" ]] || { echo "battery did not complete -- refusing liveness stage" >&2; exit 3; }
FR=6000 bash "$D/tools/gate/run_prespipe_force.sh"
echo "=== Q3 FINALS COMPLETE"
