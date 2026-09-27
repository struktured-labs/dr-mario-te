#!/bin/bash
set -u
CART=$1; TAG=$2; FR=${3:-9000}
RT=$(mktemp -d /tmp/ptrt.XXXX); mkdir -p "$RT/xdg/Mesen2"
cp /home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json "$RT/xdg/Mesen2/settings.json" 2>/dev/null || true
export XDG_CONFIG_HOME="$RT/xdg" TMPDIR="$RT" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
export PT_OUT="$PWD/pred_$TAG.log" PT_MAXF=$FR
cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
timeout 1500 ./Mesen "$CART" /home/struktured/projects/dr-mario-rl/tmp/tuckguard/predtest2.lua --donotsavesettings >/dev/null 2>&1
pkill -x Mesen 2>/dev/null; sleep 1; rm -rf "$RT"; true
