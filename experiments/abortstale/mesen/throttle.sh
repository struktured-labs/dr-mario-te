#!/bin/bash
# Pause switch + parallelism cap for THIS lane's co-sims only (coordinator request 2026-10-03).
#   - targets only processes whose executable is this lane's vsim_chain binary (no other lane uses that path)
#   - PAUSE file present -> every one of them is kill -STOP'ed (0 runnable); removed -> kill -CONT, up to the cap
#   - otherwise at most CAP (8) runnable: the youngest extras are STOP'ed, the oldest stopped ones CONT'ed first
#   - checks every 2 s; exits once no lane job and no lane service has been alive for 2 minutes
O=/home/struktured/projects/dr_mario_rl/tmp/abort_stale
BIN=$O/cosim/obj_chain/vsim_chain
CAP=${CAP:-8}
idle=0
log() { echo "$(date +%H:%M:%S) $*"; }
while true; do
  mine=()
  for p in $(pgrep -x vsim_chain); do
    [ "$(readlink /proc/$p/exe 2>/dev/null)" = "$BIN" ] && mine+=("$p")
  done
  allowed=$CAP; [ -e $O/PAUSE ] && allowed=0
  run=(); stopped=()
  # sort by start time (field 22 of /proc/PID/stat), oldest first
  for p in $(for q in "${mine[@]}"; do s=$(awk '{print $22}' /proc/$q/stat 2>/dev/null) && echo "$s $q"; done | sort -n | awk '{print $2}'); do
    st=$(awk '{print $3}' /proc/$p/stat 2>/dev/null)
    case "$st" in T|t) stopped+=("$p");; "") ;; *) run+=("$p");; esac
  done
  n=${#run[@]}
  if [ $n -gt $allowed ]; then
    for p in "${run[@]:$allowed}"; do kill -STOP "$p" 2>/dev/null && log "STOP $p (runnable $n > $allowed)"; done
  elif [ $n -lt $allowed ] && [ ${#stopped[@]} -gt 0 ]; then
    k=$((allowed - n))
    for p in "${stopped[@]:0:$k}"; do kill -CONT "$p" 2>/dev/null && log "CONT $p"; done
  fi
  if [ ${#mine[@]} -eq 0 ] && ! systemctl --user list-units --state=active --no-legend 'abortstale-*' | command grep -q 'abortstale-\(chain\|pairs\|ref\|adv\|regen\)'; then
    idle=$((idle + 2)); [ $idle -ge 120 ] && { log "no lane jobs for 2 min; exit"; exit 0; }
  else idle=0; fi
  sleep 2
done
