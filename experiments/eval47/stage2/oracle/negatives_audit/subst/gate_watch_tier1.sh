#!/bin/bash
# EXTERNAL interim checkpoint for TIER 1 (N=110). The in-process trigger is `if n == 200:` and
# therefore CANNOT FIRE at N=110 — defect nine exactly. This supplies the coverage externally.
#
# ⚠ --registered-n IS DELIBERATELY 100000, AND THIS IS NOT NEUTERING THE GATE.
# interim_gate.py bundles THREE checks into one exit code:
#   (1) implied_N <= registered_n   — a SIZING check against Tier 1's OLD sizing rule
#                                      (SE <= 3.085pp on cap(DSH)), which Amendment 1 REPLACED:
#                                      N=110 is now sized to resolve a -7.3pt effect. Leaving it
#                                      armed would FALSE-STOP a 1.4h run on a superseded criterion.
#   (2) flips/seed vs the 5.05 ANCHOR — catches RECORDS SILENTLY DROPPING. Kept BLOCKING.
#   (3) implied_N >= 20             — catches DEGENERATE VARIANCE. Kept BLOCKING.
# Raising registered_n disarms (1) ONLY. (2) and (3) still stop the run.
set -u
QA=/home/struktured/projects/dr-mario-qa-wt/experiments
export PYTHONPATH="/root/drm/subst:$QA/eval47/stage2/oracle:$QA/eval47/stage2/oracle/bootstrap:$QA/eval47/stage2/rollout:$QA/eval47/vocab2:$QA/eval47:$QA"
export NUMBA_CACHE_DIR=/tmp/drm-numba-cache
OUT=/root/drm/subst/out_tier1
for CK in 50; do
  while :; do
    n=$(ls $OUT/*.jsonl.gz 2>/dev/null | wc -l)
    systemctl is-active --quiet drm-tier1 || { echo "GATEWATCH: drm-tier1 no longer active, exiting"; exit 0; }
    [ "$n" -ge "$CK" ] && break
    sleep 60
  done
  echo "GATEWATCH: checkpoint $CK reached (n=$n) — running gate WITH --stop-on-fail"
  /root/drm/venv/bin/python /root/drm/subst/interim_gate.py \
    --dir $OUT --min-seeds $CK --registered-n 100000 --unit drm-tier1 --stop-on-fail
  rc=$?
  echo "GATEWATCH: checkpoint $CK exit=$rc"
  if [ "$rc" -ne 0 ]; then
    echo "GATEWATCH: gate FAILED at $CK — run stopped, no further checkpoints"
    exit 1
  fi
done
echo "GATEWATCH: all checkpoints passed"
