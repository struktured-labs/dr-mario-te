#!/bin/bash
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
for s in 153 145 155 147; do
  until command grep -aq "seed $s done" $S/logs/seedhi.log; do sleep 30; done
  for g in m1g1 m1g2 m1g4 m2g2 m2g3; do
    (cd $S/an && $PY mkpub.py $S/timelines/seed${s}_$g.jsonl $g seedcls $s $S/cosim/seedcls.jsonl)
    $S/tools/replay.sh seed${s}_$g $g $S/timelines/seed${s}_$g.jsonl > $S/logs/seedrep_${s}_$g.log 2>&1; echo "$(date +%T) seed $s $g rc=$?"
  done
done
echo "$(date +%T) SEEDREPLAY_HI DONE"
