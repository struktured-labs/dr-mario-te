#!/bin/bash
# silfid lane (silicon-fidelity, 2026-10-06): PAUSE switch + parallelism cap (shared-box rule; copy of execfid/tools/throttle.sh).
#   Scope: ONLY processes inside this lane's systemd user units named silfid-*.service (never anyone else's).
#   PAUSE trigger: EITHER /home/struktured/projects/dr_mario_rl/tmp/silfid/PAUSE OR tmp/PAUSE_ALL exists
#     -> every heavy process of the lane is kill -STOP'ed; both removed -> kill -CONT, up to the cap.
#   Otherwise at most CAP (6) runnable heavy processes: youngest extras STOP'ed, oldest stopped CONT'ed first.
#   Checks every 2 s. Exits after 24 h with no silfid-* job unit alive.
O=/home/struktured/projects/dr_mario_rl/tmp/silfid
ALL=/home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL
CAP=${CAP:-6}
idle=0
log() { echo "$(date +%H:%M:%S) $*"; }
heavy_re='^(vsim|Vv|Mesen|mesen|ffmpeg|python|verilator|cc1plus|py65)'
paused_logged=0
while true; do
  mine=()
  units=$(systemctl --user list-units --state=active,activating,deactivating --no-legend --plain 'silfid-*' | awk '{print $1}' | command grep -a -v '^silfid-throttle')
  for u in $units; do
    cg=$(systemctl --user show -p ControlGroup --value "$u" 2>/dev/null)
    [ -n "$cg" ] && [ -r "/sys/fs/cgroup$cg/cgroup.procs" ] || continue
    for p in $(cat "/sys/fs/cgroup$cg/cgroup.procs" 2>/dev/null); do
      c=$(cat /proc/$p/comm 2>/dev/null) || continue
      [[ "$c" =~ $heavy_re ]] || continue
      if [ -n "$(cat /proc/$p/task/*/children 2>/dev/null | tr -d ' ')" ]; then continue; fi   # orchestrator (has children)
      mine+=("$p")
    done
  done
  allowed=$CAP
  if [ -e $O/PAUSE ] || [ -e $ALL ]; then
    allowed=0
    [ $paused_logged -eq 0 ] && log "PAUSE active ($( [ -e $O/PAUSE ] && echo silfid/PAUSE) $( [ -e $ALL ] && echo PAUSE_ALL))"; paused_logged=1
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
