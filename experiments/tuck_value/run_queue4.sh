#!/usr/bin/env bash
# Re-run the divergence horizon with the truncation defect fixed. The first
# run's outputs are kept under results/superseded/ rather than deleted, so the
# defect and its correction stay auditable.
set -u
cd "$(dirname "$0")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
echo "=== START divergence_clean REFIXED $(date -Is) ==="
"$PY" divergence.py --seeds 300 --workers 6 --pressure clean \
    --out results/divergence_clean 2>&1
echo "=== END divergence_clean rc=$? $(date -Is) ==="
echo "=== START divergence_bursty REFIXED $(date -Is) ==="
"$PY" divergence.py --seeds 300 --workers 6 --pressure bursty \
    --out results/divergence_bursty 2>&1
echo "=== END divergence_bursty rc=$? $(date -Is) ==="
echo "QUEUE4 COMPLETE $(date -Is)"
