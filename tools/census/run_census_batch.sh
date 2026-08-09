#!/bin/bash
# run_census_batch.sh — serial census launches (single Mesen seat; NEVER parallel).
# Each launch = fresh boot = fresh LCG-poked seed at level-select.
# Arms: DLAT=12 (fast copro / MiSTer-like DONE) and DLAT=34 (measured Pocket median DONE).
set -u
CEN=/mnt/data/drmario/pocket-copro/mesen_copro_qa/census
BATCH="${1:?batch name}"
N="${2:-10}"          # number of launches
FRAMES="${3:-11000}"
mkdir -p "$CEN/logs/$BATCH"
for i in $(seq 1 "$N"); do
  DLAT=12
  if [ $((i % 2)) -eq 0 ]; then DLAT=34; fi
  OUT="$CEN/logs/$BATCH/run$i"
  SEED=$((100 + i * 7))
  TMO=$((FRAMES / 60 + 60))
  echo "[batch] launch $i/$N dlat=$DLAT seed=$SEED frames=$FRAMES"
  bash "$CEN/launch_census.sh" "$OUT" "$FRAMES" 2 "$DLAT" 0 "$SEED" :158 "$TMO"
  tail -1 "$OUT/run.log" 2>/dev/null
done
echo "[batch] all done"
