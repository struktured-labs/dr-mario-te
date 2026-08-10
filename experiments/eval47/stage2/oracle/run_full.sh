#!/bin/bash
# ORACLE-CEILING ARM — the full pre-registered run.  ONE LINE, resumable.
#
#   bash run_full.sh <TIER> <WORKERS>
#     TIER    A (N=9,000, PREREG_ORACLE sec 5 primary) | B (N=5,500, fallback)
#     WORKERS parallel processes (LOCAL CAP IS 6 — this box has been OOM-killed
#             5 times.  On Hetzner pass the core count.)
#
# Runs the oracle arm and its KILLED MUTANT over the SAME seed block, then
# applies the pre-registered verdict rule.  Re-running the identical command
# after an interruption skips every seed already banked on disk; each segment
# writes its own SUMMARY, so partial work is never lost and is readable without
# waiting for the whole run.
#
# The pilot's seeds 30000..30249 are the first segment of the block and are
# reused rather than re-played (PREREG_ORACLE sec 6).
set -u
cd "$(dirname "$(readlink -f "$0")")"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
TIER=${1:-A}
W=${2:-5}
case "$TIER" in
  A) N=9000 ;;
  B) N=5500 ;;
  *) echo "TIER must be A or B (see PREREG_ORACLE.md sec 5)"; exit 2 ;;
esac
mkdir -p out logs

echo "=== GATES (PREREG_ORACLE sec 2) — a failure here VOIDS the arm ==="
$PY -u gate_identity.py --seeds 12 --seed-start 40000 \
    2>&1 | tee logs/gate_identity.log
grep -q "GATES PASS" logs/gate_identity.log || { echo "GATES FAILED — ARM VOID"; exit 1; }

echo "=== ORACLE ARM   tier $TIER  N=$N  workers=$W ==="
$PY -u run_oracle.py --model lulu --label true --seed-start 30000 \
    --seed-count $N --segment 250 --workers "$W" \
    --outdir out/full_${TIER}_true >> logs/full_${TIER}_true.log 2>&1

echo "=== KILLED MUTANT (shuffled survival label), same seeds ==="
$PY -u run_oracle.py --model lulu --label shuffle --seed-start 30000 \
    --seed-count $N --segment 250 --workers "$W" \
    --outdir out/full_${TIER}_shuffle >> logs/full_${TIER}_shuffle.log 2>&1

echo "=== PRE-REGISTERED VERDICT ==="
$PY -u analyse_oracle.py --true-run out/full_${TIER}_true \
    --mutant-run out/full_${TIER}_shuffle \
    --out out/VERDICT_${TIER}.json --label "oracle_tier${TIER}" \
    2>&1 | tee logs/verdict_${TIER}.log
echo "ALLDONE $(date -Is)"
