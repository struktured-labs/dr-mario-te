#!/bin/bash
set -u
ROM=$1; OUT=$(readlink -f "$2"); FR=${3:-12000}
cat > cfge.lua <<CFGEOF
return { out="$OUT", maxframes=$FR }
CFGEOF
# per-run XDG isolation: the unix sun_path limit makes Mesen die in ListenForArguments
RT=$(mktemp -d /tmp/mesenrt.XXXX); mkdir -p "$RT/xdg/Mesen2"
export XDG_CONFIG_HOME="$RT/xdg" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
timeout 400 /home/struktured/mesen2-vsrules/Mesen "$ROM" engage.lua --donotsavesettings >/dev/null 2>&1
pkill -x Mesen 2>/dev/null; sleep 1; rm -rf "$RT"; true
