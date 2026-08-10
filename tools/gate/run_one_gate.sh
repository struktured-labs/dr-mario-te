#!/bin/bash
# run_one.sh <tag> <mmc1.nes> <maxf> -- ONE arm on a FRESH Xvfb, with verification.
# Three known flaky-launch causes, all handled:
#   (1) stale .NET single-instance mutex/pipe -> "Pipe hasn't been connected yet", no log
#   (2) Mesen startup SIGABRT (rc=134) -- documented, retry
#   (3) ⚠ Xvfb DEGRADES after the first Mesen launch on it (project memory: "one clean shot per
#       Xvfb session") -- so every attempt gets its OWN display, started fresh and torn down.
# Verifies the log exists AND carries this arm's tag before declaring success.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:-3000}"
out="$D/tmp/clean/$tag"; mkdir -p "$out"
for try in 1 2 3 4 5; do
  disp=$((200 + RANDOM % 60))
  rm -f "/tmp/.X${disp}-lock" "/tmp/.X11-unix/X${disp}"
  Xvfb ":$disp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X${disp}" ] && break; sleep 1; done
  ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || \
    rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null
  rm -f "$out/run.log"
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    export DISPLAY=":$disp" FP_OUT="$out" FP_MAXF="$maxf" FP_TAG="$tag" FP_DLAT=34 FP_SEED=114 FP_WARM=0
    timeout -k 10 400 /home/struktured/projects/dr-mario-mods/run_mesen.sh "$cart" \
      "$D/tools/gate/fieldplay.lua" ) >"$out/stdout.log" 2>&1
  kill "$xpid" 2>/dev/null
  if command grep -aq "tag=$tag" "$out/run.log" 2>/dev/null; then
    command grep -a SUMMARY "$out/run.log"; exit 0
  fi
  echo "[one] $tag try $try failed (disp :$disp), retrying"
  sleep 2
done
echo "[one] $tag FAILED after retries"; exit 1
