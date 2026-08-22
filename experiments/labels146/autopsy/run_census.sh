#!/usr/bin/env bash
# Autopsy census producer: regenerate the FULL-SPACE clean solo census locally
# (PREREG_AUTOPSY §0). census.py is resumable and single-writer-locked, so the
# recovery strategy for any failure is to run it again.
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
CENSUS=/home/struktured/projects/dr-mario-labels146-wt/experiments/hetzner/census.py
OUT="$HERE/out/census"
LOG="$HERE/logs/census.log"
W=${1:-8}
mkdir -p "$OUT" "$HERE/logs"

# STARTUP ASSERT: the provenance gate must be on disk and green before a single
# census row is written (PREREG_AUTOPSY §0).
"$PY" - <<'PYEOF' || exit 1
import json, sys
d = json.load(open("/home/struktured/projects/dr-mario-labels146-wt/experiments/labels146/autopsy/out/gate_provenance.json"))
exp = "219e2e1518c4bc23c037ea0ae843f891027d9a0af67d17f1bcc154e12586410f"
assert d["digest"] == exp, f"PROVENANCE GATE RED: {d['digest']} != {exp}"
assert d["n_seeds"] == 2 and d["seeds"] == [33269, 33754], "gate seed list wrong"
print("[assert] provenance gate GREEN", d["digest"][:16])
PYEOF

for attempt in $(seq 1 200); do
    echo "=== [runner] attempt $attempt at $(date -Is) ===" >> "$LOG"
    marker=$(mktemp)
    nice -n 5 "$PY" "$CENSUS" --lo 0 --hi 65536 --workers "$W" --chunk 200 \
        --out "$OUT" 2>&1 | tee -a "$LOG" | tail -5 > "$marker"
    rc=${PIPESTATUS[0]}
    if command grep -aq "BLOCK COMPLETE" "$marker"; then
        rm -f "$marker"
        echo "=== [runner] CENSUS_COMPLETE at $(date -Is) ===" | tee -a "$LOG"
        exit 0
    fi
    rm -f "$marker"
    echo "=== [runner] exited rc=$rc, retrying in 20s ===" >> "$LOG"
    sleep 20
done
exit 1
