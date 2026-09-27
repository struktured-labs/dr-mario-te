#!/bin/bash
RT=$(mktemp -d /tmp/mesenrt.XXXX); mkdir -p "$RT/xdg/Mesen2"
export XDG_CONFIG_HOME="$RT/xdg" PATH="$HOME/.dotnet:$PATH" DOTNET_ROOT="$HOME/.dotnet"
timeout 300 /home/struktured/mesen2-vsrules/Mesen "$1" diag.lua --donotsavesettings >/dev/null 2>&1
pkill -x Mesen 2>/dev/null; sleep 1; rm -rf "$RT"; true
