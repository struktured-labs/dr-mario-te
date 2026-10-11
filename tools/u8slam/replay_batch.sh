#!/usr/bin/env bash
# u8slam lane: chained + silicon-garbage Mesen replays (tools/execfid/run_probe.sh, execfid_probe.lua) of the slam-gate
# carts on the a16mt lane's case files (dr_mario_rl/tmp/a16mt/cases: 12 games x {v11, a16} timelines, 1,197 pills).
# One Mesen at a time (run_probe.sh waits for any Mesen and holds the lane lock). Meant to run inside a systemd user
# unit; before EVERY run it waits while the shared dr_mario_rl/tmp/PAUSE_ALL (or the lane's PAUSE_U8SLAM) exists.
#   replay_batch.sh "<fwtag> ..." "<game> ..." "<cartname>=<cart.nes> ..."
#   runs <game>_<cartname>_<fwtag>_chain_garb on $CASES/<game>_<fwtag>_chain_garb.lua (maxf 60000); done runs are skipped
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
T=/home/struktured/projects/dr_mario_rl/tmp
export EXECFID_OUT=${EXECFID_OUT:-$T/u8slam/execfid}
CASES=${CASES:-$T/a16mt/cases}
fws=$1; games=$2; carts=$3
for fw in $fws; do
  for g in $games; do
    for c in $carts; do
      name=${c%%=*}; cart=${c#*=}
      tag=${g}_${name}_${fw}_chain_garb
      if command grep -aq "^SUMMARY tag=$tag" "$EXECFID_OUT/runs/$tag/lateflip_$tag.log" 2>/dev/null; then
        echo "SKIP $tag (done)"; continue; fi
      while [ -e $T/PAUSE_ALL ] || [ -e $T/PAUSE_U8SLAM ]; do sleep 10; done
      "$R/tools/execfid/run_probe.sh" "$tag" "$cart" "$CASES/${g}_${fw}_chain_garb.lua" 60000 || echo "FAIL $tag rc=$?"
    done
  done
  echo "$(date -u +%FT%TZ) replays fw=$fw carts=[$(for c in $carts; do printf '%s ' ${c%%=*}; done)] finished" >> $T/u8slam/STATUS.txt
done
echo "BATCH DONE"
