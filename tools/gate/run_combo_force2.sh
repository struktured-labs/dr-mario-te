#!/bin/bash
# #140 overlap-FORCED rerun of the interlock witness arms (combo + NOGUARD).
# The first force run was VACUOUS for the interlock: with the 600-frame poke
# grid, no pipeline hook ever landed while a slice search was active
# (combo and NOGUARD byte-identical, viol=0, no opportunity). PS_SLONLY=1
# pokes only while SL_PH != 0 and PS_EVERY=120 raises the volley rate, and
# the probe now reports ov_hooks (overlap opportunities) so a zero-opportunity
# run reads VOID rather than PASS.
set -eo pipefail
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140).
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
FR="${FR:-6000}"

arm () {  # $1 cart  $2 tag
  local out="$D/tmp/combobatt/force2_$2"; mkdir -p "$out"
  local rt="$out/runtime-tmp"; rm -rf -- "$rt"; mkdir -p "$rt/xdg/Mesen2"
  cp "$SANDBOX" "$rt/xdg/Mesen2/settings.json"
  local mmc1="$out/$2_mmc1.nes"
  rm -f "$out/force.log"
  local launched; launched=$(date +%s)
  "$PY" "$D/tools/gate/remap_mapper.py" "$1" "$mmc1" >"$out/remap.log" 2>&1
  echo "[$2] cart=$(md5sum "$1" | cut -d' ' -f1)"
  ( cd "$(dirname "$MESEN")"
    export TMPDIR="$rt" XDG_CONFIG_HOME="$rt/xdg"
    export PS_OUT="$out" PS_TAG="$2" PS_MAXF="$FR" PS_SLONLY=1 PS_EVERY=120
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

arm "$D/roms/combo-hardened-pp3sl-20260820.nes" combo
arm "$D/tmp/combo/combo-noguard-MUTANT.nes" noguard
echo "=== FORCE2 COMPLETE"
