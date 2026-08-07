#!/usr/bin/env bash
# Single-maneuver isolation, queued behind queue2. Waits so the lane stays at
# 6 workers on a shared box.
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
while pgrep -x -f "bash run_queue2.sh" > /dev/null; do sleep 30; done
echo "=== START divergence_single clean $(date -Is) ==="
"$PY" divergence_single.py --seeds 300 --workers 6 --pressure clean \
    --out results/divergence_single_clean 2>&1
echo "=== END divergence_single clean rc=$? $(date -Is) ==="
echo "QUEUE3 COMPLETE $(date -Is)"
