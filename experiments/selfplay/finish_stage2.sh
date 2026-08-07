#!/bin/bash
# Wait on the labeller's PID and /proc state (not a -f pattern, which self-matches
# any shell that quoted it, and not a bare kill -0, which succeeds on a zombie).
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
LPID=3583692
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay
while :; do
  n=$(wc -l < out/s2_labels.jsonl 2>/dev/null || echo 0)
  [ "$n" -ge 2900 ] && break
  [ ! -d /proc/$LPID ] && break
  s=$(awk '{print $3}' /proc/$LPID/stat 2>/dev/null || echo Z)
  [ "$s" = "Z" ] && break
  sleep 60
done
sleep 10
{
  echo "=== STAGE 2 RESULTS $(date -Is)  n=$(wc -l < out/s2_labels.jsonl) ==="
  $PY stage2_fit.py --labels out/s2_labels.jsonl --corpus out/s2_corpus.npz
} > STAGE2_RESULTS.txt 2>&1
echo "EXIT $?" >> STAGE2_RESULTS.txt
echo "STAGE2 DONE $(date -Is)" >> STAGE2_RESULTS.txt
