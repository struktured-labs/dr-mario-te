#!/bin/bash
# Wait for the labelling job, then run every Stage-1 analysis in one place.
#
# The wait deliberately does NOT use `pgrep -f 'stage1.py label'`: that string also
# appears in the command line of any shell that ever quoted it, so a pattern wait
# can block forever on something that is not the job. It also does not use a bare
# `kill -0 PID`: the labeller's parent shell is still alive, so after exit the PID
# lingers as a ZOMBIE and kill -0 keeps succeeding. Exit on either the process
# being gone/zombie, or the output reaching the expected record count.
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
LPID=1124145
WANT=140
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay
while :; do
  n=$(wc -l < out/labels_main.jsonl 2>/dev/null || echo 0)
  [ "$n" -ge "$WANT" ] && break
  if [ ! -d /proc/$LPID ]; then break; fi
  s=$(awk '{print $3}' /proc/$LPID/stat 2>/dev/null || echo Z)
  [ "$s" = "Z" ] && break
  sleep 30
done
sleep 5
{
  echo "=============== STAGE 1 RESULTS  $(date -Is) ==============="
  echo "labelled positions: $(wc -l < out/labels_main.jsonl)"
  echo
  $PY stage1.py analyze --labels out/labels_main.jsonl --json-out out/stage1.json
  echo; echo "=============== 1d  DE-NOISED ORACLE GAIN ==============="
  $PY stage1_denoise.py --labels out/labels_main.jsonl --json-out out/denoise.json
  echo; echo "=============== 1b  HEADROOM SPLIT ==============="
  $PY stage1_features.py extract --labels out/labels_main.jsonl \
      --corpus out/corpus.npz --out out/feats.npz && \
  $PY stage1_features.py fit --feats out/feats.npz \
      --labels out/labels_main.jsonl --corpus out/corpus.npz --folds 5
  echo; echo "=============== 1e  WHERE / IS IT EXPRESSIBLE ==============="
  $PY stage1_diagnose.py --labels out/labels_main.jsonl --feats out/feats.npz
} > logs/stage1_results.txt 2>&1
echo "DONE $(date -Is)" >> logs/stage1_results.txt
