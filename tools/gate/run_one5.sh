#!/bin/bash
# run_one5.sh <tag> <cart.nes> <maxf> [P5_TUCK] -- ONE probe5 arm, FRESH Xvfb, verified.
#
# Same three flaky-launch defences as run_one.sh (stale .NET single-instance mutex/pipe, Xvfb
# degrading after the first launch on a display, startup SIGABRT), PLUS:
#   * a seat wait, so this never kills another lane's Mesen;
#   * ⚠ MEASURED HERE: Mesen does NOT always exit on `emu.stop(0)` -- a 2500-frame arm was still
#     resident 6.5 minutes after writing its SUMMARY. run_one.sh's fixed `timeout` therefore
#     burns its whole budget per arm. So: launch Mesen in the background, POLL the probe log for
#     this arm's SUMMARY, and reap as soon as it lands.
# Verifies the log exists AND carries THIS arm's tag before declaring success.
# The cart is header-remapped to MMC1 here (PRG+CHR untouched) so Mesen boots the ship bytes.
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:-18000}"; pubt="${4:-1}"
out="$D/tmp/clean/$tag"; mkdir -p "$out"
mmc1="$out/${tag}_mmc1.nes"
$PY "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1 || { echo "[one5] remap failed"; exit 2; }
# generous ceiling: ~1 wall-second per 25 emulated frames, floor 240s
deadline=$(( maxf / 25 + 240 ))

wait_seat() {
  for _ in $(seq 1 600); do
    ps -eo args | command grep -a "$MESEN" | command grep -av grep >/dev/null || return 0
    sleep 2
  done
  return 1
}

for try in 1 2 3; do
  wait_seat || { echo "[one5] $tag ABORT: Mesen seat never freed"; exit 3; }
  disp=$((200 + RANDOM % 60))
  rm -f "/tmp/.X${disp}-lock" "/tmp/.X11-unix/X${disp}"
  Xvfb ":$disp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X${disp}" ] && break; sleep 1; done
  rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null
  rm -f "$out/probe5.log"
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    export DISPLAY=":$disp" P5_OUT="$out" P5_MAXF="$maxf" P5_TAG="$tag" P5_DLAT=34 P5_SEED=114 P5_TUCK="$pubt"
    exec /home/struktured/projects/dr-mario-mods/run_mesen.sh "$mmc1" \
      "$D/tools/gate/probe5.lua" ) >"$out/stdout.log" 2>&1 &
  runpid=$!
  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    if command grep -aq "SUMMARY tag=$tag" "$out/probe5.log" 2>/dev/null; then ok=1; break; fi
    kill -0 "$runpid" 2>/dev/null || { sleep 3; \
      command grep -aq "SUMMARY tag=$tag" "$out/probe5.log" 2>/dev/null && ok=1; break; }
    sleep 2
  done
  pkill -9 -f "$mmc1" 2>/dev/null
  kill -9 "$runpid" 2>/dev/null
  kill "$xpid" 2>/dev/null
  sleep 2
  if [ "$ok" = 1 ]; then command grep -a "SUMMARY tag=$tag" "$out/probe5.log"; exit 0; fi
  echo "[one5] $tag try $try failed (disp :$disp), retrying"
  sleep 2
done
echo "[one5] $tag FAILED after retries"; exit 1
