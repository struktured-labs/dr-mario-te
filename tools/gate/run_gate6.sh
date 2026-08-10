#!/bin/bash
# run_gate6.sh <lua> <envprefix> <logname> <tag> <mmc1.nes> <maxf> [deadline_s]
#
# One arm, seat-safe and courteous. Same shape as the tuck lane's run_one5.sh (its poll-and-reap
# idiom, reused rather than re-derived) generalised over the lua/env-prefix so it drives BOTH
# probe3 (mechanism) and fieldplay (multi-match).
#
# Four hazards, all handled:
#  1. Mesen is single-instance: launching while ANOTHER lane's instance is alive FORWARDS this
#     ROM+lua into their emulator and corrupts THEIR run. Hard-wait for an empty seat; never
#     clear the single-instance artifacts while any Mesen is alive.
#  2. Mesen does not reliably exit on emu.stop(0) -- measured resident 6.5 min after writing its
#     SUMMARY. So POLL for this arm's SUMMARY and reap the instant it lands, rather than letting
#     a fixed timeout hold the seat behind us.
#  3. A fixed ceiling below the run's real cost truncates it into a log with no SUMMARY, which
#     looks like a run. 18,000 frames needs ~700 s => default deadline 900 s.
#  4. Xvfb degrades after the first Mesen launch on it -- fresh display per attempt.
# VERIFY: the log must exist AND carry this arm's own tag, else the arm is UNREPORTED, not zero.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
LUA="${1:?lua}"; PFX="${2:?env prefix}"; LOGNAME="${3:?logname}"
tag="${4:?tag}"; mmc1="${5:?cart}"; maxf="${6:?maxframes}"; deadline="${7:-900}"
out="$D/tmp/clean/$tag"; mkdir -p "$out"

wait_seat() {
  for _ in $(seq 1 "${SEAT_WAIT_POLLS:-180}"); do
    ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || return 0
    sleep 10
  done
  return 1
}

for try in 1 2 3; do
  wait_seat || { echo "[gate6] $tag UNRUN: Mesen seat never freed (not launching, would forward)"; exit 3; }
  disp=$((200 + RANDOM % 60))
  rm -f "/tmp/.X${disp}-lock" "/tmp/.X11-unix/X${disp}"
  Xvfb ":$disp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X${disp}" ] && break; sleep 1; done
  ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || \
    rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null
  rm -f "$out/$LOGNAME"
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    export DISPLAY=":$disp"
    export "${PFX}_OUT=$out" "${PFX}_MAXF=$maxf" "${PFX}_TAG=$tag" "${PFX}_DLAT=34" \
           "${PFX}_SEED=114" "${PFX}_WARM=0"
    exec /home/struktured/projects/dr-mario-mods/run_mesen.sh "$mmc1" "$LUA" ) >"$out/stdout.log" 2>&1 &
  runpid=$!
  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    if command grep -aq "SUMMARY tag=$tag" "$out/$LOGNAME" 2>/dev/null; then ok=1; break; fi
    kill -0 "$runpid" 2>/dev/null || { sleep 3; \
      command grep -aq "SUMMARY tag=$tag" "$out/$LOGNAME" 2>/dev/null && ok=1; break; }
    sleep 2
  done
  # reap OUR instance only, identified by the cart path we launched -- never a name-pattern sweep
  pkill -9 -f "$mmc1" 2>/dev/null
  kill -9 "$runpid" 2>/dev/null
  kill "$xpid" 2>/dev/null
  sleep 2
  [ "$ok" = 1 ] && { command grep -a "SUMMARY tag=$tag" "$out/$LOGNAME"; exit 0; }
  echo "[gate6] $tag try $try produced no SUMMARY (disp :$disp), retrying"
done
echo "[gate6] $tag UNRUN after retries -- report as unrun, NOT as zero"; exit 1
