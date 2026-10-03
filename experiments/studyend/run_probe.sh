#!/usr/bin/env bash
# Run probe_end.lua on a couch (DRHUMAN, mapper-100) cart in headless Mesen: P1 idle -> tops out, P2 = tools/copro_emu.lua.
# Records the mid-game STUDY pause/resume and three 2P round-end screens (dumps + screenshots + exec/write counters).
#   usage: experiments/studyend/run_probe.sh <cart.nes> <tag> [hold_frames]
# Uses Mesen's --testrunner mode: no GUI, no X display, and it returns BEFORE Mesen's single-instance check, so it cannot
# forward into (or receive) another agent's Mesen. The private XDG_CONFIG_HOME (SingleInstance=false, io allowed) lives
# under tmp/ (gitignored). One instance at a time; run under nice.
set -euo pipefail
CART=${1:?usage: run_probe.sh <cart.nes> <tag> [hold]}; TAG=${2:?tag}; HOLD=${3:-1500}
R=$(cd "$(dirname "$0")/../.." && pwd)
MESEN=${MESEN:-/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen}
PY=${PY:-python3}
W=$R/tmp/studyend_probe; OUT=$W/out/; mkdir -p "$OUT" "$W/home/Mesen2"
cat > "$W/home/Mesen2/settings.json" <<'JSON'
{ "Preferences": { "SingleInstance": false, "PauseWhenInBackground": false, "PauseWhenInMenusAndConfig": false },
  "Debug": { "ScriptWindow": { "AllowIoOsAccess": true } }, "ScriptWindow": { "AllowIoOsAccess": true } }
JSON
"$PY" "$R/tools/remap_mapper100_mmc1.py" "$CART" "$W/${TAG}_mmc1.nes" >/dev/null
nice -n 19 timeout 600 env SE_OUT="$OUT" SE_TAG="$TAG" SE_HOLD="$HOLD" SE_EMU="$R/tools/copro_emu.lua" \
  XDG_CONFIG_HOME="$W/home" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet" \
  "$MESEN" --testrunner --timeout=550 "$W/${TAG}_mmc1.nes" "$R/experiments/studyend/probe_end.lua" > "$OUT/${TAG}_stdout.txt" 2>&1 \
  || { echo "probe exit $? (0 expected) -- see $OUT${TAG}_probe.log"; exit 1; }
grep -a -E "^(PLAY|ROUNDEND|RESUME_CHECK|PHANTOM|FINAL)" "$OUT${TAG}_probe.log"
echo "outputs: $OUT${TAG}_*"
