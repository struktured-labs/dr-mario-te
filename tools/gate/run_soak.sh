#!/bin/bash
# run_soak.sh <tag> <boot.nes> <maxf> [timeout_s] -- ONE probe8 arm, fresh Xvfb, verified.
#
# Same launch discipline as run_one.sh (the three SILENT Mesen failure modes: stale .NET
# single-instance mutex/pipe, Xvfb degrading after its first launch, and intermittent startup
# SIGABRT rc=134), with the changes a MULTI-HOUR run needs:
#
#   * timeout is an argument, not a hardcoded 400 s.
#   * RETRY IS EARLY-ONLY. run_one.sh retries any failed arm; retrying an arm that already ran
#     for three hours would throw away the soak's whole value. So a retry happens only when the
#     attempt died before EARLY_S seconds AND produced no tagged log. A long attempt that ends
#     without a SUMMARY is reported as PARTIAL and kept -- for a soak, partial frames are real
#     frames and still bound the event rate.
#   * the log is checked for THIS arm's tag before anything is accepted, and the exit status
#     distinguishes CLEAN / PARTIAL / UNRUN so a caller can never read "no log" as "no events".
#
# Exit: 0 = completed (SUMMARY present)  2 = PARTIAL (tagged log, no SUMMARY)
#       1 = failed to produce a tagged log   4 = seat held by another lane, NOT LAUNCHED
set -u
D=/home/struktured/projects/dr-mario-v8-wt
tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:-18000}"; tmo="${4:-600}"
out="${PS_OUTDIR:-$D/tmp/soak}/$tag"; mkdir -p "$out"
EARLY_S="${EARLY_S:-180}"

wait_seat() {
  for _ in $(seq 1 "${SEAT_WAIT_POLLS:-180}"); do
    ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || return 0
    sleep 10
  done
  return 1
}

for try in 1 2 3; do
  if ! wait_seat; then
    echo "[soak] $tag: Mesen seat held by another lane for the whole wait -- NOT LAUNCHING"
    echo "       (a launch would forward into their instance). Reporting UNRUN, not zero."
    exit 4
  fi
  disp=$((200 + RANDOM % 60))
  rm -f "/tmp/.X${disp}-lock" "/tmp/.X11-unix/X${disp}"
  Xvfb ":$disp" -screen 0 1280x720x24 -ac -nolisten tcp >/dev/null 2>&1 &
  xpid=$!
  for _ in $(seq 1 15); do [ -e "/tmp/.X11-unix/X${disp}" ] && break; sleep 1; done
  ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null || \
    rm -f /tmp/.dotnet/shm/global/* /tmp/CoreFxPipe_* 2>/dev/null
  rm -f "$out/probe_soak.log"
  t0=$(date +%s)
  ( cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
    export DISPLAY=":$disp"
    export PS_OUT="$out" PS_MAXF="$maxf" PS_TAG="$tag"
    export PS_DLAT="${PS_DLAT:-34}" PS_SEED="${PS_SEED:-114}" PS_TUCK="${PS_TUCK:-4}"
    export PS_CKPT="${PS_CKPT:-30000}" PS_INJECT="${PS_INJECT:-0}" PS_ACHK="${PS_ACHK:-0}"
    export PS_INJA="${PS_INJA:-1500}" PS_INJB="${PS_INJB:-2100}"
    timeout -k 15 "$tmo" /home/struktured/projects/dr-mario-mods/run_mesen.sh "$cart" \
      "$D/tools/gate/probe_soak.lua" ) >"$out/stdout.log" 2>&1
  rc=$?
  el=$(( $(date +%s) - t0 ))
  kill "$xpid" 2>/dev/null
  if command grep -aq "tag=$tag" "$out/probe_soak.log" 2>/dev/null; then
    if command grep -aq '^SUMMARY ' "$out/probe_soak.log"; then
      echo "[soak] $tag COMPLETE rc=$rc wall=${el}s"
      command grep -a '^SUMMARY \|^SOAK \|^SOAK2 ' "$out/probe_soak.log"
      exit 0
    fi
    lastf=$(command grep -a '^CKPT ' "$out/probe_soak.log" | command tail -1)
    echo "[soak] $tag PARTIAL rc=$rc wall=${el}s -- tagged log kept, no SUMMARY"
    echo "[soak] last checkpoint: ${lastf:-<none>}"
    exit 2
  fi
  echo "[soak] $tag try $try produced no tagged log (rc=$rc wall=${el}s disp=:$disp)"
  if [ "$el" -ge "$EARLY_S" ]; then
    echo "[soak] ...and it ran >= ${EARLY_S}s, so this is NOT a launch flake. Not retrying."
    exit 1
  fi
  sleep 3
done
echo "[soak] $tag FAILED after retries"; exit 1
