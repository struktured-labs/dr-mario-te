#!/usr/bin/env bash
# a16mt lane: chained + silicon-garbage Mesen replays (tools/execfid/run_probe.sh, execfid_probe.lua) of several carts on
# several case files. One Mesen at a time (run_probe.sh waits for any Mesen and holds the lane lock); meant to run
# inside a systemd user unit a16mt-* so tools/a16mt/throttle.sh can pause it (PAUSE_A16MT / PAUSE_ALL).
#   replay_batch.sh <fwtag> <cases-dir> "<game> ..." "<cartname>=<cart.nes> ..."
#   runs <game>_<cartname>_<fwtag>_chain_garb on <cases-dir>/<game>_<fwtag>_chain_garb.lua (maxf 60000)
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
export EXECFID_OUT=${EXECFID_OUT:-/home/struktured/projects/dr_mario_rl/tmp/a16mt/execfid}
fw=$1; cases=$2; games=$3; carts=$4
for g in $games; do
  for c in $carts; do
    name=${c%%=*}; cart=${c#*=}
    tag=${g}_${name}_${fw}_chain_garb
    if command grep -aq "^SUMMARY tag=$tag" "$EXECFID_OUT/runs/$tag/lateflip_$tag.log" 2>/dev/null; then
      echo "SKIP $tag (done)"; continue; fi
    "$R/tools/execfid/run_probe.sh" "$tag" "$cart" "$cases/${g}_${fw}_chain_garb.lua" 60000 || echo "FAIL $tag rc=$?"
  done
done
echo "BATCH DONE $fw"
