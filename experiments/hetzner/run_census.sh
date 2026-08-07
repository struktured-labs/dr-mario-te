#!/usr/bin/env bash
# run_census.sh -- keepalive wrapper for the upper-half seed census.
#
# census.py is resumable (it reads back its own JSONL and skips finished
# seeds), so the recovery strategy for ANY failure -- crash, OOM, the box
# rebooting -- is simply to run it again. This loop does that, with a short
# backoff so a hard-failing binary doesn't spin the CPU.
#
# Exits 0 only when census.py itself reports the block complete.
set -u

BASE=/home/struktured/projects/dr-mario-qa-wt/experiments/hetzner
PY=/root/drm/venv/bin/python
OUT=$BASE/results/upper
LOG=$BASE/logs/census.log

mkdir -p "$OUT" "$BASE/logs"

for attempt in $(seq 1 100); do
    echo "=== [runner] attempt $attempt at $(date -Is) ===" >> "$LOG"
    "$PY" "$BASE/census.py" --lo 32768 --hi 65536 --workers 4 --chunk 200 \
        --out "$OUT" >> "$LOG" 2>&1
    rc=$?
    if grep -q "BLOCK COMPLETE" "$LOG"; then
        echo "=== [runner] block complete at $(date -Is) ===" >> "$LOG"
        exit 0
    fi
    echo "=== [runner] exited rc=$rc, retrying in 20s ===" >> "$LOG"
    sleep 20
done
echo "=== [runner] gave up after 100 attempts ===" >> "$LOG"
exit 1
