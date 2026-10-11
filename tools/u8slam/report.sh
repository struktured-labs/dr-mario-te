#!/usr/bin/env bash
# u8slam lane: the replay record (experiments/u8slam/REPLAYS.txt) from the banked runs under dr_mario_rl/tmp/u8slam/.
#   tools/u8slam/report.sh > experiments/u8slam/REPLAYS.txt       (also writes experiments/u8slam/pills_{v11,a16}.jsonl)
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
RUNS=/home/struktured/projects/dr_mario_rl/tmp/u8slam/execfid/runs
BANK=/home/struktured/projects/dr_mario_rl/tmp/a16mt/execfid/runs
ARMS=${ARMS:-f2p,u8,k8,e8}
echo "# u8slam replays ($(date -u +%Y-%m-%dT%H:%MZ)): Mesen, real carts, chained, silicon garbage delivered (tools/execfid/execfid_probe.lua)"
echo "# carts: f2p = FAIR2PLUS 5a1695da (KOPEN 32 / KEND 255) | u8 = KOPEN 8 / KEND 8 1ebd386e | k8 = KOPEN 8 only 4b53df67 |"
echo "#        e8 = KEND 8 only 1792aecf. Case files and timelines: the a16mt lane's (dr_mario_rl/tmp/a16mt/cases), 12 games, 1,197 pills"
for fw in v11 a16; do
  echo; echo "################ $fw timelines ($([ $fw = v11 ] && echo 'V11 c51d2e21' || echo 'V11 + A16 b545d740'))"
  $PY tools/u8slam/analyze.py $RUNS $fw $ARMS --ctl $BANK --pills experiments/u8slam/pills_$fw.jsonl --list 200
  echo
  $PY tools/u8slam/late_finals.py $RUNS $fw $ARMS
  echo
  $PY tools/u8slam/model_vs_cart.py $RUNS $fw f2p=32:255,u8=8:8,k8=8:255,e8=32:8 --out experiments/u8slam/model_pills_$fw.jsonl
done
