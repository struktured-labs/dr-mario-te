#!/bin/bash
# #140 combined-cart Mesen battery, chained:
#   stage 1  probe6 18k A/B -- control = prespipe-hardened-q3 (the certified
#            predecessor), ON = combo-hardened-pp3sl (DRP1SLICE=1 on top).
#            Marker discipline from run_pipeline_battery.sh: the ON arm refuses
#            to run without the control's marker.
#   stage 2  forced-release dual liveness (probe_combo_live.lua), three arms:
#            control (sl counters must read ZERO -- positive control in
#            reverse), combo (all live, viol==0), NOGUARD byte-patched mutant
#            (viol MUST fire -- a witness that cannot fire proves nothing).
set -eo pipefail
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
OUT=$D/tmp/combobatt; mkdir -p "$OUT"
FRAMES="${FRAMES:-18000}"
FR="${FR:-6000}"

# ---- stage 1: probe6 18k A/B ------------------------------------------------
rm -f "$OUT/control.ok" "$OUT/on.ok"
echo "=== ARM A control prespipe-hardened-q3 (DRP1SLICE unset)" | tee -a "$OUT/battery.log"
bash "$D/tools/gate/run_probe6_pipeline.sh" "$D/roms/manifests/prespipe-hardened-q3.json" "$FRAMES" 2>&1 | tee -a "$OUT/battery.log"
touch "$OUT/control.ok"
[[ -f "$OUT/control.ok" ]] || { echo "control arm produced no marker" >&2; exit 3; }
echo "=== ARM B combo-hardened-pp3sl (DRP1SLICE=1)" | tee -a "$OUT/battery.log"
bash "$D/tools/gate/run_probe6_pipeline.sh" "$D/roms/manifests/combo-hardened-pp3sl-20260820.json" "$FRAMES" 2>&1 | tee -a "$OUT/battery.log"
touch "$OUT/on.ok"

# ---- stage 2: forced-release dual liveness, 3 arms --------------------------
arm () {  # $1 cart  $2 tag
  local out="$OUT/force_$2"; mkdir -p "$out"
  local rt="$out/runtime-tmp"; rm -rf -- "$rt"; mkdir -p "$rt/xdg/Mesen2"
  cp "$SANDBOX" "$rt/xdg/Mesen2/settings.json"
  local mmc1="$out/$2_mmc1.nes"
  rm -f "$out/force.log"
  local launched; launched=$(date +%s)
  "$PY" "$D/tools/gate/remap_mapper.py" "$1" "$mmc1" >"$out/remap.log" 2>&1
  echo "[$2] cart=$(md5sum "$1" | cut -d' ' -f1)"
  ( cd "$(dirname "$MESEN")"
    export TMPDIR="$rt" XDG_CONFIG_HOME="$rt/xdg"
    export PS_OUT="$out" PS_TAG="$2" PS_MAXF="$FR"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_combo_live.lua" -testrunner "-timeout=$((FR/12+300))"
  ) >"$out/stdout.log" 2>&1 &
  local pid=$!
  for _ in $(seq 1 $((FR/12+300))); do
    command grep -aq "SUMMARY tag=$2" "$out/force.log" 2>/dev/null && break
    kill -0 "$pid" 2>/dev/null || break
    sleep 5
  done
  kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true
  [[ -f "$out/force.log" ]] || { echo "[$2] NO LOG -- FAILURE, not zero" >&2; return 1; }
  local mt; mt=$(stat -c %Y "$out/force.log")
  (( mt >= launched )) || { echo "[$2] STALE LOG -- refusing to report it" >&2; return 4; }
  command grep -a "^SUMMARY" "$out/force.log" || { echo "[$2] NO SUMMARY -- FAILURE, not zero" >&2; return 1; }
}

arm "$D/roms/prespipe-hardened-q3.nes" control
arm "$D/roms/combo-hardened-pp3sl-20260820.nes" combo
arm "$D/tmp/combo/combo-noguard-MUTANT.nes" noguard
echo "=== COMBO BATTERY COMPLETE" | tee -a "$OUT/battery.log"
