#!/bin/bash
# STEER14 (steersim lane) pause switch + parallelism cap. Runs as systemd user unit steer14-throttle.
#   Targets: python processes inside the cgroups of systemd user units named steer14-*.service
#            (every STEER14 farm / mechanism job is launched with `systemd-run --user --unit steer14-<name>`),
#            excluding this unit. No other lane uses the steer14- unit prefix.
#   PAUSE:   if EITHER $PAUSE_MINE (/home/struktured/projects/dr_mario_rl/tmp/PAUSE_STEER14) or /home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL exists -> kill -STOP all
#            targets (0 runnable). Removed -> kill -CONT, oldest first, up to the cap.
#   CAP:     otherwise at most CAP (10) non-stopped targets: youngest extras STOP'ed, oldest stopped CONT'ed first.
#   Desk analyses (steer14-desk-* units) rank as OLDEST, so the cap pauses a farm job instead of them.
#   Checks every 2 s. Runs until the unit is stopped (no idle exit; the lane stops it at the end).
O=/home/struktured/projects/dr_mario_rl/tmp/steer14
PAUSE_MINE=${PAUSE_MINE_PATH:-/home/struktured/projects/dr_mario_rl/tmp/PAUSE_STEER14}   # override only for the self-test
PAUSE_ALL=${PAUSE_ALL_PATH:-/home/struktured/projects/dr_mario_rl/tmp/PAUSE_ALL}   # override only for the self-test
CG=/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service
CAP=${CAP:-10}
log() { echo "$(date +%H:%M:%S) $*"; }
last_state=""
while true; do
  mine=(); desk=()
  for f in "$CG"/*/steer14-*.service/cgroup.procs; do
    [ -e "$f" ] || continue
    case "$f" in *steer14-throttle.service*) continue;; esac
    while read -r p; do
      [ -n "$p" ] || continue
      c=$(cat /proc/$p/comm 2>/dev/null) || continue
      case "$c" in python*) mine+=("$p"); case "$f" in *steer14-desk-*) desk+=("$p");; esac;; esac
    done < "$f"
  done
  allowed=$CAP; why=cap
  if [ -e "$PAUSE_MINE" ] || [ -e "$PAUSE_ALL" ]; then allowed=0; why=PAUSE; fi
  run=(); stopped=()
  for p in $(for q in "${mine[@]}"; do s=$(awk '{print $22}' /proc/$q/stat 2>/dev/null) && { case " ${desk[*]} " in *" $q "*) s=0;; esac; echo "$s $q"; }; done | sort -n | awk '{print $2}'); do
    st=$(awk '{print $3}' /proc/$p/stat 2>/dev/null)
    case "$st" in T|t) stopped+=("$p");; "") ;; *) run+=("$p");; esac
  done
  n=${#run[@]}
  if [ "$n" -gt "$allowed" ]; then
    for p in "${run[@]:$allowed}"; do kill -STOP "$p" 2>/dev/null && log "STOP $p ($why: runnable $n > $allowed)"; done
  elif [ "$n" -lt "$allowed" ] && [ ${#stopped[@]} -gt 0 ]; then
    k=$((allowed - n))
    for p in "${stopped[@]:0:$k}"; do kill -CONT "$p" 2>/dev/null && log "CONT $p"; done
  elif [ "$allowed" -gt 0 ] && [ "$n" -eq "$allowed" ]; then
    # a stopped DESK analysis preempts the youngest running non-desk job (total runnable stays at the cap)
    for d in "${stopped[@]}"; do
      case " ${desk[*]} " in *" $d "*) ;; *) continue;; esac
      for ((i=${#run[@]}-1; i>=0; i--)); do
        v=${run[$i]}; case " ${desk[*]} " in *" $v "*) continue;; esac
        kill -STOP "$v" 2>/dev/null && kill -CONT "$d" 2>/dev/null && log "PREEMPT $v for desk $d"
        unset 'run[$i]'; run=("${run[@]}"); break
      done
    done
  fi
  st_now="$why targets=${#mine[@]}"
  [ "$st_now" != "$last_state" ] && { log "state $st_now"; last_state=$st_now; }
  sleep 2
done
