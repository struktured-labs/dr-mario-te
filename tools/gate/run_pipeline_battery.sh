#!/bin/bash
# #126 enforcement 2 play battery: probe6 18k on the flag-ON pipelined cart and its
# control, run as a chained A/B. The control arm runs FIRST and writes a success
# marker; the ON arm refuses to start without it, so an ON-only result can never be
# read as an A/B (a gate that must run before data needs its own marker).
set -eo pipefail
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
OUT=$D/tmp/pipebattery; mkdir -p "$OUT"
FRAMES="${FRAMES:-18000}"

run_arm () {  # $1 manifest  $2 marker
  bash "$D/tools/gate/run_probe6_pipeline.sh" "$1" "$FRAMES" 2>&1 | tee -a "$OUT/battery.log"
  touch "$OUT/$2"
}

rm -f "$OUT/control.ok" "$OUT/on.ok"
echo "=== ARM A control hardened-prestart-20260820 (DRPRESPIPE unset)" | tee -a "$OUT/battery.log"
run_arm "$D/roms/manifests/hardened-prestart-20260820.json" control.ok

[[ -f "$OUT/control.ok" ]] || { echo "control arm produced no marker -- refusing to run the ON arm" >&2; exit 3; }

echo "=== ARM B flag-ON prespipe-hardened-q3 (DRPRESPIPE=1, Q=3 default)" | tee -a "$OUT/battery.log"
run_arm "$D/roms/manifests/prespipe-hardened-q3.json" on.ok
echo "=== BATTERY COMPLETE" | tee -a "$OUT/battery.log"
