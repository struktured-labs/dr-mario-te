#!/bin/bash
# run_one5.sh <tag> <cart.nes> <maxf> [P5_TUCK]  -- ONE probe5 arm, FRESH Xvfb, verified.
#
# Same three flaky-launch defences as run_one.sh (stale .NET mutex/pipe, Xvfb degrading after
# the first launch on a display, startup SIGABRT), PLUS a seat wait so this never kills another
# lane's Mesen. Verifies the log exists AND carries THIS arm's tag before declaring success.
# The cart is header-remapped to MMC1 here (PRG+CHR untouched) so Mesen boots the ship bytes.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:-18000}"; pubt="${4:-1}"
out="$D/tmp/clean/$tag"; mkdir -p "$out"
mmc1="$out/${tag}_mmc1.nes"
$PY "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1 || { echo "[one5] remap failed"; exit 2; }

wait_seat() {
  for _ in $(seq 1 300); do
    ps -eo args | command grep -a "$MESEN" | command grep -av grep >/dev/null || return 0
    sleep 2
  done
  return 1
}

for try in 1 2 3 4 5; do
  wait_seat || { echo "[one5] $tag ABORT: Mesen seat never freed"; exit 3; }
  disp=$((200 + RANDOM % 60))
  rm -f "/tmp/.X${disp}-lock" "/tmp/.X11-unix/X${disp}"
  Xvfb ":$disp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X${disp}" ] && break; sleep 1; done
  ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || \
    rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null
  rm -f "$out/probe5.log"
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    export DISPLAY=":$disp" P5_OUT="$out" P5_MAXF="$maxf" P5_TAG="$tag" P5_DLAT=34 P5_SEED=114 P5_TUCK="$pubt"
    timeout -k 10 2400 /home/struktured/projects/dr-mario-mods/run_mesen.sh "$mmc1" \
      "$D/tools/gate/probe5.lua" ) >"$out/stdout.log" 2>&1
  kill "$xpid" 2>/dev/null
  if command grep -aq "tag=$tag" "$out/probe5.log" 2>/dev/null; then
    command grep -a SUMMARY "$out/probe5.log"; exit 0
  fi
  echo "[one5] $tag try $try failed (disp :$disp), retrying"
  sleep 2
done
echo "[one5] $tag FAILED after retries"; exit 1
