#!/bin/bash
# run_probe.sh <tag> <cart.nes> <maxf> <window_hex> -- one probe_nmi126 arm.
# Launch discipline copied from tools/gate/run_one.sh (fresh Xvfb per attempt,
# hard single-instance seat wait, tag-verified log before declaring success).
set -u
# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
tag="${1:?tag}"; cart="$(readlink -f "${2:?cart}")"; maxf="${3:-6000}"; win="${4:-0x5000}"
out="$D/tmp/nmi126/$tag"; mkdir -p "$out"

wait_seat() {
  for _ in $(seq 1 "${SEAT_WAIT_POLLS:-90}"); do
    ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || return 0
    sleep 10
  done
  return 1
}

for try in 1 2 3 4 5; do
  if ! wait_seat; then
    echo "[nmi126] $tag: Mesen seat held by another lane -- NOT LAUNCHING (UNRUN, not zero)"
    exit 4
  fi
  disp=$((200 + RANDOM % 60))
  rm -f "/tmp/.X${disp}-lock" "/tmp/.X11-unix/X${disp}"
  Xvfb ":$disp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X${disp}" ] && break; sleep 1; done
  ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || \
    rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null
  rm -f "$out/probe_nmi126.log"
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    export DISPLAY=":$disp" PN_OUT="$out" PN_MAXF="$maxf" PN_TAG="$tag" PN_W="$win"
    timeout -k 10 500 /home/struktured/projects/dr-mario-mods/run_mesen.sh "$cart" \
      "$D/tools/nmi126/probe_nmi126.lua" ) >"$out/stdout.log" 2>&1
  kill "$xpid" 2>/dev/null
  if command grep -aq "SUMMARY tag=$tag" "$out/probe_nmi126.log" 2>/dev/null; then
    command grep -a "SUMMARY\|HIST" "$out/probe_nmi126.log"; exit 0
  fi
  echo "[nmi126] $tag try $try failed (disp :$disp), retrying"
  sleep 2
done
echo "[nmi126] $tag FAILED after retries"; exit 1
