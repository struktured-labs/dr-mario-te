#!/usr/bin/env bash
# Run probe_final.lua (match final / 1P game over + START + next-match start) on a couch cart in headless Mesen.
#   usage: experiments/studyend/run_final.sh <cart.nes> <tag> <final2p|final3|oneplayer> [final_hold_frames]
# Same harness as run_probe.sh: Mesen --testrunner (no GUI, returns before the single-instance check), private
# XDG_CONFIG_HOME under tmp/, nice 19, one instance at a time.
set -euo pipefail
CART=${1:?usage: run_final.sh <cart.nes> <tag> <scen> [hold]}; TAG=${2:?tag}; SCEN=${3:?scenario}; FHOLD=${4:-400}
R=$(cd "$(dirname "$0")/../.." && pwd)
MESEN=${MESEN:-/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen}
PY=${PY:-python3}
W=$R/tmp/studyend_probe; OUT=$W/out/; mkdir -p "$OUT" "$W/home/Mesen2"
cat > "$W/home/Mesen2/settings.json" <<'JSON'
{ "Preferences": { "SingleInstance": false, "PauseWhenInBackground": false, "PauseWhenInMenusAndConfig": false },
  "Debug": { "ScriptWindow": { "AllowIoOsAccess": true } }, "ScriptWindow": { "AllowIoOsAccess": true } }
JSON
"$PY" "$R/tools/remap_mapper100_mmc1.py" "$CART" "$W/${TAG}_mmc1.nes" >/dev/null
nice -n 19 timeout 600 env SE_FULLLO="${SE_FULLLO:--1}" SE_FULLHI="${SE_FULLHI:--1}" SE_OUT="$OUT" SE_TAG="$TAG" SE_SCEN="$SCEN" SE_FHOLD="$FHOLD" SE_EMU="$R/tools/copro_emu.lua" \
  XDG_CONFIG_HOME="$W/home" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet" \
  "$MESEN" --testrunner --timeout=550 "$W/${TAG}_mmc1.nes" "$R/experiments/studyend/probe_final.lua" > "$OUT/${TAG}_stdout.txt" 2>&1 \
  || { echo "probe exit $? (0 expected) -- see $OUT${TAG}_final.log"; exit 1; }
grep -a -E "^(PLAY|ROUNDEND|START|NEXT|PHANTOM|POKE|DONE)" "$OUT${TAG}_final.log"
echo "outputs: $OUT${TAG}_*"
