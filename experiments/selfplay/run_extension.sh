#!/bin/bash
# Extension to ~900 positions, then merge, then fit -- ALL IN THE FOREGROUND.
#
# NO pgrep, NO /proc, NO pattern matching of any kind. finish_2x.sh waited on
# `pgrep -f 'venv/bin/python -u scale_label.py'`, and the Claude shell wrapper that
# LAUNCHED it carries that exact string in its own command line -- so the chain
# waited on its own parent and deadlocked for ten hours with the labelling long
# finished. That is the third time tonight this trap has bitten, twice after I had
# already fixed it elsewhere, so the fix here is structural: run the steps as
# sequential foreground children and let the shell's own exit codes do the waiting.
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay

$PY -u scale_label.py --policy champion --positions 900 --rollouts 8 --workers 8 \
    --out out/scale_labels.jsonl --max-rss-gb 24 >> logs/scale_label.log 2>&1
rc=$?
echo "labeller exited rc=$rc $(date -Is)" >> logs/ext.log
if [ "$rc" -ne 0 ]; then echo "LABELLER FAILED rc=$rc" > RESULT_900.txt; exit "$rc"; fi

$PY merge_2x.py out/labels_main.jsonl out/scale_labels.jsonl out/merged_900.jsonl \
    > logs/merge_900.log 2>&1
{
  echo "=== ~900-POSITION RESULT $(date -Is) ==="
  cat logs/merge_900.log
  echo
  $PY stage2_fit.py --labels out/merged_900.jsonl --corpus out/corpus.npz
  echo "EXIT $?"
} > RESULT_900.txt 2>&1
echo "900 DONE $(date -Is)" >> RESULT_900.txt
