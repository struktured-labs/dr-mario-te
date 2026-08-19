#!/bin/bash
# batch_d131gate.sh -- run the five #131 gate arms one at a time.
# `leak` runs FIRST and is the positive control: if it does not reproduce the
# wedge, no other arm's verdict means anything (dr-mario-gate-artifact-low-goes).
# Mesen is single-instance on this box, and other lanes share it, so each arm
# waits for a free emulator rather than killing anything by name pattern.
set -u
D=/home/struktured/projects/dr-mario-dispatch131-wt

wait_for_mesen() {
  for _ in $(seq 1 480); do
    ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
      | command grep -av '^Z' >/dev/null || return 0
    sleep 15
  done
  echo "TIMED OUT waiting for a free Mesen" >&2; return 1
}

for arm in leak unpause serve serve0 nostart; do
  wait_for_mesen || exit 1
  D1_SEED=114 D1_ARM="$arm" "$D/tools/gate/run_d131gate.sh" 3 "${MAXF:-4000}" </dev/null 2>&1 \
    | command grep -a "^SUMMARY\|FAILED\|MISMATCH\|already alive"
done
