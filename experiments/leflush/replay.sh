#!/bin/bash
# Mesen replay of the V1 + DRLEFLUSH firmware (c51d2e21) on the abort cart b1b57638 (couch fair kit D + DRABORTSTALE),
# G2 / G3 / G4, the same way the abort-stale lane replayed V1 (REPLAY_G234.txt, row AV1):
#   1. case files: regen_cases.py (claude/abort-stale) = the banked V1 case pills (board, upload, colours, silicon /
#      python actions) with THIS firmware's fresh co-sim timelines (pubs, DONE, final, tuck). Tooling check first:
#      regenerating from this lane's V1 fresh refs must reproduce the banked chained V1 case file byte for byte.
#   2. Mesen (run_mesen.sh: one at a time, PAUSE-aware, nice 19): tag <game>_AV11
#   3. eval_v11.py: AV1 (banked lane runs) vs AV11
# Run inside a v11-* systemd user unit (the lane throttle SIGSTOPs Mesen while the PAUSE file exists).
set -u
V=/home/struktured/projects/dr_mario_rl/tmp/v11
P=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
H=$(cd "$(dirname "$0")" && pwd)
REGEN=/home/struktured/projects/dr-mario-abortstale-wt/experiments/abortstale/regen_cases.py
TLD=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines
BANKC=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/cases
CA=/home/struktured/projects/dr_mario_rl/tmp/abort_stale/carts/drmario_te_couch_fair_abort_b1b57638.nes
FW=${FW:-c51d2e21}; TL=${TL:-V11}; TAG=${TAG:-AV11}
mkdir -p $V/mesen/cases
[ "$(md5sum < $CA | cut -c1-8)" = b1b57638 ] || { echo "abort cart md5"; exit 1; }
LANEREF=/home/struktured/projects/dr_mario_rl/tmp/abort_stale/cosim/ref
for g in G2 G3 G4; do
  ref1=$V/cosim/ref/${g}_a1ef31c8.jsonl; [ -s $ref1 ] || ref1=$LANEREF/${g}_a1ef31c8.jsonl   # lane's V1 refs until ours exist
  $P $REGEN $TLD/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl $ref1 \
    $V/mesen/cases/cases_${g}_V1chk.jsonl $V/mesen/cases/cases_${g}_V1chk.lua > /dev/null
  if cmp -s $V/mesen/cases/cases_${g}_V1chk.lua $BANKC/cases_${g}_fwa1ef31c8_chain.lua; then
    echo "TOOLING $g: regen(V1 fresh refs $ref1) == banked chained V1 case file: PASS"
  else echo "TOOLING $g: regen(V1 fresh refs) != banked case file: FAIL"; fi
  $P $REGEN $TLD/pubtrace_${g}_fwa1ef31c8_fwlane.jsonl $V/cosim/ref/${g}_$FW.jsonl \
    $V/mesen/cases/cases_${g}_$TL.jsonl $V/mesen/cases/cases_${g}_$TL.lua > /dev/null
  echo "CASES $g $TL: $(md5sum < $V/mesen/cases/cases_${g}_$TL.lua | cut -c1-8) (V1 banked $(md5sum < $BANKC/cases_${g}_fwa1ef31c8_chain.lua | cut -c1-8))"
done
for g in ${GAMES:-G2 G3 G4}; do
  $H/run_mesen.sh ${g}_$TAG $CA $V/mesen/cases/cases_${g}_$TL.lua 20000 0 2>&1 | tail -2
done
$P $H/eval_v11.py $TAG:$TL
echo REPLAY_DONE
