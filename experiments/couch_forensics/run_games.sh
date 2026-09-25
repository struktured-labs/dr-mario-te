#!/bin/bash
# Prevalence run: slice each game's frames out of a full-video scan and push it through the G2 pipeline.
# Usage: run_games.sh FRAMES_FULL.jsonl TAG "G1:T0:T1 G2:T0:T1 ..." OUTDIR
set -e
cd "$(dirname "$0")"
PY=${PY:-python}
FULL=$1; TAG=$2; GAMES=$3; OUT=$4
for g in $GAMES; do
  IFS=: read name t0 t1 <<< "$g"
  $PY -c "
import json,sys
with open('$FULL') as fi, open('$OUT/frames_${TAG}_${name}.jsonl','w') as fo:
    for l in fi:
        t=json.loads(l)['t']
        if $t0 <= t <= $t1: fo.write(l)
"
  $PY track.py $OUT/frames_${TAG}_${name}.jsonl $OUT/raw_${TAG}_${name}.jsonl
  $PY analyze_g2.py run $OUT/raw_${TAG}_${name}.jsonl $OUT/an_${TAG}_${name}.jsonl
  $PY classify_g2.py $OUT/an_${TAG}_${name}.jsonl $OUT/raw_${TAG}_${name}.jsonl cases_${TAG}_${name}.jsonl
done
