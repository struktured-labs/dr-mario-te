#!/bin/bash
# probe6 arm runner: LOGIC-ONLY gate. Descriptors come from probe6's geometric/synth finder,
# NOT firmware -- probe6's own header: "Rates from this finder measure the PROBE, not the
# firmware". CRN via P6_SEED held constant across arms.
set -u
CART=$1; TAG=$2; MODE=$3; SEED=${4:-114}; FR=${5:-14000}
RT=$(mktemp -d /tmp/p6rt.XXXX); mkdir -p "$RT/xdg/Mesen2"
export XDG_CONFIG_HOME="$RT/xdg" TMPDIR="$RT" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
export P6_OUT="$PWD/p6_$TAG.log" P6_MAXF=$FR P6_SEED=$SEED P6_TUCK=$MODE P6_W=0x5200
timeout 600 /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen \
  "$CART" /home/struktured/projects/dr-mario-tempo-wt/tools/gate/probe6.lua --donotsavesettings >/dev/null 2>&1
pkill -x Mesen 2>/dev/null; sleep 1; rm -rf "$RT"; true
echo "$TAG done: $(command grep -ac SUMMARY "$PWD/p6_$TAG.log" 2>/dev/null) summary lines"
