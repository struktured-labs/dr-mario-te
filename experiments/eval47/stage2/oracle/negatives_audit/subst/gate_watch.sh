#!/bin/bash
# EXTERNAL interim checkpoints. The in-process trigger was `if n == 200:` — ONE-SHOT — and it
# fired at 04:49Z with the broken statistic, 13 min before the fix landed. The live process holds
# the old subst_run.py in memory, so editing that file changes nothing. This supplies the coverage
# for the remaining ~80% of the run WITHOUT restarting anything: interim_gate.py takes --dir, so it
# can be invoked externally against the PRODUCER'S OWN directory (never a mirror — see rule 54).
set -u
QA=/home/struktured/projects/dr-mario-qa-wt/experiments
export PYTHONPATH="/root/drm/subst:$QA/eval47/stage2/oracle:$QA/eval47/stage2/oracle/bootstrap:$QA/eval47/stage2/rollout:$QA/eval47/vocab2:$QA/eval47:$QA"
export NUMBA_CACHE_DIR=/tmp/drm-numba-cache
OUT=/root/drm/subst/out_flips
for CK in 400 800 1200; do
  while :; do
    n=$(ls $OUT/*.jsonl.gz 2>/dev/null | wc -l)
    systemctl is-active --quiet drm-subst || { echo "GATEWATCH: drm-subst no longer active, exiting"; exit 0; }
    [ "$n" -ge "$CK" ] && break
    sleep 120
  done
  echo "GATEWATCH: checkpoint $CK reached (n=$n) — running gate WITH --stop-on-fail"
  /root/drm/venv/bin/python /root/drm/subst/interim_gate.py \
    --dir $OUT --min-seeds $CK --registered-n 1666 --unit drm-subst --stop-on-fail
  rc=$?
  echo "GATEWATCH: checkpoint $CK exit=$rc"
  # Explicit `if` rather than `[ ... ] && { ... }`, for READABILITY only.
  # ⚠ A believed hazard here was TESTED AND REFUTED (bash 5.2.37): it was claimed that under
  # `set -e` the `&&` form, being the last statement in the loop body, would kill the watcher
  # whenever a checkpoint PASSED. It does not. `set -e` is exempt for a command that fails as a
  # non-final part of an AND-OR list, so a false `[ ... ]` never triggers errexit.
  #   T1 `&&` last in a for-loop body, condition false, set -e -> loop completed, exit 0
  #   T2 same at script level                                  -> exit 0
  #   T3 CONTROL: bare `false` last in loop body, set -e        -> exit 1  (errexit IS active)
  # The control is what makes T1/T2 meaningful rather than a dead test. So both forms are safe;
  # this one is merely clearer. Do NOT "harden" it back on the strength of the old comment.
  if [ "$rc" -ne 0 ]; then
    echo "GATEWATCH: gate FAILED at $CK — run stopped, no further checkpoints"
    exit 1
  fi
done
echo "GATEWATCH: all checkpoints passed"
