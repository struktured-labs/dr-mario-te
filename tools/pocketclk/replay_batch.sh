#!/usr/bin/env bash
# pocketclk lane: u8slam replay_batch.sh with the lane's own output dir and the RE-TIMED (54.669 MHz) case files.
#   replay_batch.sh "<fw> ..." "<game> ..." "<arm>=<cart.nes> ..."   (waits while dr_mario_rl/tmp/PAUSE_ALL exists)
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
T=/home/struktured/projects/dr_mario_rl/tmp
export EXECFID_OUT=${EXECFID_OUT:-$T/pocketclk/execfid}
CASES=${CASES:-$T/pocketclk/cases}
for fw in $1; do for g in $2; do for c in $3; do
  name=${c%%=*}; cart=${c#*=}; tag=${g}_${name}_${fw}_chain_garb
  command grep -aq "^SUMMARY tag=$tag" "$EXECFID_OUT/runs/$tag/lateflip_$tag.log" 2>/dev/null && { echo "SKIP $tag"; continue; }
  while [ -e $T/PAUSE_ALL ]; do sleep 10; done
  "$R/tools/execfid/run_probe.sh" "$tag" "$cart" "$CASES/${g}_${fw}_chain_garb.lua" 60000 || echo "FAIL $tag rc=$?"
done; done; echo "$(date -u +%FT%TZ) fw=$fw arms=[$3] finished" >> $T/pocketclk/STATUS.txt; done
echo "BATCH DONE"
