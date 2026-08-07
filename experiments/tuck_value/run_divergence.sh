#!/usr/bin/env bash
# Divergence-horizon runs. Waits for run_all.sh to finish first so the lane
# never exceeds its 6-worker budget (the box is shared).
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
N=${N:-300}
W=${W:-6}

echo "=== waiting for run_all.sh to complete $(date -Is) ==="
while ! grep -q "ALL RUNS COMPLETE" logs/run_all.log 2>/dev/null; do
  if ! pgrep -f "[r]un_all\.sh" > /dev/null; then
    echo "run_all.sh is gone without completing -- proceeding anyway $(date -Is)"
    break
  fi
  sleep 60
done

echo "=== START divergence clean $(date -Is) ==="
"$PY" divergence.py --seeds "$N" --workers "$W" --pressure clean \
    --out results/divergence_clean 2>&1
echo "=== END divergence clean rc=$? $(date -Is) ==="

echo "=== START divergence bursty $(date -Is) ==="
"$PY" divergence.py --seeds "$N" --workers "$W" --pressure bursty \
    --out results/divergence_bursty 2>&1
echo "=== END divergence bursty rc=$? $(date -Is) ==="

echo "DIVERGENCE COMPLETE $(date -Is)"
