#!/bin/bash
# silfid: full-game validation of a seed class: co-sim EVERY pill of GAME at SEED (the disagreeing pills are already in
# seedcls.jsonl), build the full timeline, Mesen-replay the FAIR cart. Args via env: PAIRS="m1g1:25 m1g2:1 ..."
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd $S/an
for gs in $PAIRS; do
  g=${gs%%:*}; s=${gs#*:}
  spec=$($PY allpills.py $g $s $S/cosim/seedcls.jsonl $S/cosim/full.jsonl 2>/dev/null)
  [ "${spec#*:}" != "" ] && SEED=$s J=5 $PY cosim.py $S/cosim/full.jsonl $spec
  echo "$(date +%T) cosim $g s$s done"
  $PY mkpub.py $S/timelines/full_s${s}_$g.jsonl $g seedcls $s $S/cosim/seedcls.jsonl $S/cosim/full.jsonl
  $S/tools/replay.sh full_s${s}_$g $g $S/timelines/full_s${s}_$g.jsonl > $S/logs/full_s${s}_$g.log 2>&1
  echo "$(date +%T) replay $g s$s rc=$?"
done
echo "$(date +%T) FULLSEED DONE"
