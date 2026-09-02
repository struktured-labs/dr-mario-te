#!/bin/bash
set -u
ROM=$1; SEED=$2; OUT=$(readlink -f "$3"); FR=${4:-5400}
cat > cfg.lua <<CFGEOF
return { out="$OUT", seed=$SEED, maxframes=$FR }
CFGEOF
export PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
timeout 300 /home/struktured/mesen2-vsrules/Mesen "$ROM" crn.lua --donotsavesettings >/dev/null 2>&1
pkill -x Mesen 2>/dev/null; true
