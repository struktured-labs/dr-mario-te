#!/bin/bash
# ORACLE-CEILING ARM — the full pre-registered run.  ONE LINE, resumable.
#
#   bash run_full.sh <TIER> <WORKERS>
#     TIER    A (N=9,000, PREREG_ORACLE sec 5 primary) | B (N=5,500, fallback)
#     WORKERS parallel processes (measured cap 12 on the 77-GB local box;
#             use 4 on the 2-core+SMT Hetzner CCX23.)
#
# Runs the ideal CLAIR arm and its dose-matched KILLED MUTANT over the SAME seed block, then
# applies the pre-registered verdict rule.  Re-running the identical command
# after an interruption skips every seed already banked on disk; each segment
# writes its own SUMMARY, so partial work is never lost and is readable without
# waiting for the whole run.
#
# The historical pilot used the prefix, but its rows predate the frozen runtime
# manifest and shared provenance schema. A10 requires replay under this runner;
# old rows are never mixed into the Tier-A output directory.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
PY=${DRM_PY:-/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python}
[[ -x "$PY" ]] || PY=/root/drm/venv/bin/python
export NUMBA_CACHE_DIR=${NUMBA_CACHE_DIR:-/tmp/dr-mario-te-numba-cache}
mkdir -p "$NUMBA_CACHE_DIR"
CANONICAL_QA=/home/struktured/projects/dr-mario-qa-wt/experiments
export PYTHONPATH="$PWD/bootstrap:$CANONICAL_QA${PYTHONPATH:+:$PYTHONPATH}"
TIER=${1:-A}
W=${2:-5}
case "$TIER" in
  A) N=9000 ;;
  B) N=5500 ;;
  *) echo "TIER must be A or B (see PREREG_ORACLE.md sec 5)"; exit 2 ;;
esac
mkdir -p out logs

DOSE_FILE=NULL_DOSE.json
test -f "$DOSE_FILE" || {
  echo "MISSING $DOSE_FILE — run: bash run_calibration.sh $W";
  echo "Then record amendment A6 before endpoint execution.";
  exit 2;
}
read -r KEEP_NUM KEEP_DEN < <(
  "$PY" -c 'import json; d=json.load(open("NULL_DOSE.json")); assert d.get("validated") is True, "NULL_DOSE is not validated"; print(d["null_keep_num"], d["null_keep_den"])'
)

echo "=== GATES (PREREG_ORACLE sec 2) — a failure here VOIDS the arm ==="
$PY gate_runtime_manifest.py 2>&1 | tee logs/gate_runtime_manifest.log
grep -q "RUNTIME MANIFEST GATE: PASS" logs/gate_runtime_manifest.log || { echo "MANIFEST GATE FAILED — ARM VOID"; exit 1; }
$PY -u gate_identity.py --seeds 12 --seed-start 40000 \
    2>&1 | tee logs/gate_identity.log
grep -q "GATES PASS" logs/gate_identity.log || { echo "GATES FAILED — ARM VOID"; exit 1; }
$PY -u gate_forkleak.py --seeds 4 --seed-start 41000 \
    2>&1 | tee logs/gate_forkleak.log
grep -q "G1g PASS" logs/gate_forkleak.log || { echo "G1g FAILED — ARM VOID"; exit 1; }
$PY gate_dist.py 2>&1 | tee logs/gate_dist.log
grep -q "G1h DIST KEY GATE: PASS" logs/gate_dist.log || { echo "G1h FAILED — ARM VOID"; exit 1; }
$PY gate_null_thinning.py 2>&1 | tee logs/gate_null_thinning.log
grep -q "G1i NULL-THINNING GATE: PASS" logs/gate_null_thinning.log || { echo "G1i FAILED — ARM VOID"; exit 1; }
$PY test_oracle_verdict.py 2>&1 | tee logs/test_oracle_verdict.log
grep -q "ORACLE VERDICT MUTATION GATE: PASS" logs/test_oracle_verdict.log || { echo "VERDICT GATE FAILED — ARM VOID"; exit 1; }
$PY test_runner_banking.py 2>&1 | tee logs/test_runner_banking.log
grep -q "RUNNER BANKING MUTATION GATE: PASS" logs/test_runner_banking.log || { echo "BANKING GATE FAILED — ARM VOID"; exit 1; }

echo "=== ORACLE-CLAIR IDEAL ARM   tier $TIER  N=$N  workers=$W ==="
$PY -u run_oracle.py --model lulu --future clair --label true --seed-start 30000 \
    --seed-count $N --segment 250 --workers "$W" \
    --outdir out/full_${TIER}_clair_true >> logs/full_${TIER}_clair_true.log 2>&1

echo "=== DOSE-MATCHED KILLED MUTANT, keep $KEEP_NUM/$KEEP_DEN ==="
$PY -u run_oracle.py --model lulu --future clair --label shuffle --seed-start 30000 \
    --seed-count $N --segment 250 --workers "$W" \
    --null-keep-num "$KEEP_NUM" --null-keep-den "$KEEP_DEN" \
    --outdir out/full_${TIER}_clair_shuffle >> logs/full_${TIER}_clair_shuffle.log 2>&1

echo "=== PRE-REGISTERED VERDICT ==="
$PY -u analyse_oracle.py --true-run out/full_${TIER}_clair_true \
    --mutant-run out/full_${TIER}_clair_shuffle \
    --out out/VERDICT_${TIER}_CLAIR.json --label "oracle_clair_tier${TIER}" \
    2>&1 | tee logs/verdict_${TIER}.log
echo "ALLDONE $(date -Is)"
