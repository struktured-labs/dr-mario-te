#!/bin/bash
# Q=3 finals, chained: 18k probe6 A/B, then the forced-release liveness A/B.
# Each stage checks the previous stage's success marker (a gate that must run
# before data needs its own marker).
set -eo pipefail
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
FRAMES=18000 bash "$D/tools/gate/run_pipeline_battery.sh"
[[ -f "$D/tmp/pipebattery/on.ok" ]] || { echo "battery did not complete -- refusing liveness stage" >&2; exit 3; }
FR=6000 bash "$D/tools/gate/run_prespipe_force.sh"
echo "=== Q3 FINALS COMPLETE"
