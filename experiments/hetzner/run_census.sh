#!/usr/bin/env bash
# run_census.sh -- keepalive wrapper for the FULL-SPACE seed census (0..65535).
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
OUT=$BASE/results/full
LOG=$BASE/logs/census.log

mkdir -p "$OUT" "$BASE/logs"

for attempt in $(seq 1 200); do
    echo "=== [runner] attempt $attempt at $(date -Is) ===" >> "$LOG"
    # Completion must be judged from THIS attempt only. Grepping the whole log
    # would let a "BLOCK COMPLETE" left over from a previous, differently-ranged
    # run end the loop before the current block finished.
    marker=$(mktemp)
    "$PY" "$BASE/census.py" --lo 0 --hi 65536 --workers 4 --chunk 200 \
        --out "$OUT" 2>&1 | tee -a "$LOG" | tail -5 > "$marker"
    rc=${PIPESTATUS[0]}
    if grep -q "BLOCK COMPLETE" "$marker"; then
        rm -f "$marker"
        echo "=== [runner] block complete at $(date -Is) ===" >> "$LOG"
        exit 0
    fi
    rm -f "$marker"
    echo "=== [runner] exited rc=$rc, retrying in 20s ===" >> "$LOG"
    sleep 20
done
echo "=== [runner] gave up after 200 attempts ===" >> "$LOG"
exit 1
