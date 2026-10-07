#!/bin/bash
# a16mt lane (A16 firmware + MIN_THINK cart, 2026-10-07): PAUSE switch + parallelism cap (shared-box rule).
# Copy of the execfid lane throttle (dr_mario_rl/tmp/execfid/tools/throttle.sh) with the scope, the PAUSE path and
# Quartus added to the heavy set (a SIGSTOP only pauses a fit: the flow has no wall-clock limit).
#   Scope: ONLY processes inside this lane's systemd user units named a16mt-*.service (never anyone else's).
#   Heavy = comm matching Mesen/vsim/ffmpeg/python/verilator/cc1plus (anything the lane runs that burns CPU).
#   PAUSE trigger: EITHER the lane's $LANE (tmp/PAUSE_A16MT) OR the shared /home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL exists
#     -> every heavy process of the lane is kill -STOP'ed; both removed -> kill -CONT, up to the cap.
#   Otherwise at most CAP (4) runnable heavy processes: youngest extras STOP'ed, oldest stopped CONT'ed first.
#   Checks every 2 s. Exits after 24 h with no a16mt-* job unit alive.
LANE=/home/struktured/projects/dr_mario_rl/tmp/PAUSE_A16MT
ALL=/home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL
CAP=${CAP:-4}
idle=0
log() { echo "$(date +%H:%M:%S) $*"; }
heavy_re='^(vsim|Vv|Mesen|mesen|ffmpeg|python|verilator|cc1plus|py65|quartus)'
paused_logged=0
while true; do
  mine=()
  units=$(systemctl --user list-units --state=active,activating,deactivating --no-legend --plain 'a16mt-*' | awk '{print $1}' | command grep -a -v '^a16mt-throttle')
  for u in $units; do
    cg=$(systemctl --user show -p ControlGroup --value "$u" 2>/dev/null)
    [ -n "$cg" ] && [ -r "/sys/fs/cgroup$cg/cgroup.procs" ] || continue
    for p in $(cat "/sys/fs/cgroup$cg/cgroup.procs" 2>/dev/null); do
      c=$(cat /proc/$p/comm 2>/dev/null) || continue
      [[ "$c" =~ $heavy_re ]] || continue
      if [ -n "$(cat /proc/$p/task/*/children 2>/dev/null | tr -d ' ')" ]; then continue; fi   # orchestrator
      mine+=("$p")
    done
  done
  allowed=$CAP
  if [ -e $LANE ] || [ -e $ALL ]; then
    allowed=0
    [ $paused_logged -eq 0 ] && log "PAUSE active ($( [ -e $LANE ] && echo PAUSE_A16MT) $( [ -e $ALL ] && echo PAUSE_ALL))"; paused_logged=1
  else
    [ $paused_logged -eq 1 ] && log "PAUSE cleared"; paused_logged=0
  fi
  n=0; declare -A want=()
  for p in $(for q in "${mine[@]}"; do s=$(awk '{print $22}' /proc/$q/stat 2>/dev/null) || continue; echo "$s $q"; done | sort -n | awk '{print $2}'); do
    st=$(awk '{print $3}' /proc/$p/stat 2>/dev/null) || continue
    if [ $allowed -gt 0 ] && [ $n -lt $allowed ]; then want[$p]=1; n=$((n + 1)); fi
    case "$st" in
      T|t) [ -n "${want[$p]:-}" ] && kill -CONT "$p" 2>/dev/null && log "CONT $p $(cat /proc/$p/comm 2>/dev/null)";;
      *)   [ -z "${want[$p]:-}" ] && kill -STOP "$p" 2>/dev/null && log "STOP $p $(cat /proc/$p/comm 2>/dev/null) (allowed $allowed)";;
    esac
  done
  unset want
  if [ -z "$units" ]; then
    idle=$((idle + 2)); [ $idle -ge 86400 ] && { log "no lane jobs for 24 h; exit"; exit 0; }
  else idle=0; fi
  sleep 2
done
