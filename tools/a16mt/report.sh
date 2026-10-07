#!/usr/bin/env bash
# a16mt lane: the replay record (experiments/a16mt/REPLAYS.txt) from the banked runs under dr_mario_rl/tmp/a16mt/.
#   tools/a16mt/report.sh > experiments/a16mt/REPLAYS.txt
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
A=/home/struktured/projects/dr_mario_rl/tmp/a16mt
RUNS=$A/execfid/runs
X=/home/struktured/projects/dr-mario-h16-wt/experiments/execfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
E=/home/struktured/projects/dr_mario_rl/tmp/execfid/runs
V1G2=/home/struktured/projects/dr_mario_rl/tmp/fair_v1_replay/timelines/pubtrace_G2_fwa1ef31c8_fwlane.jsonl
echo "# a16mt replays ($(date -u +%Y-%m-%dT%H:%MZ)): Mesen, real carts, chained, silicon garbage delivered (tools/execfid/execfid_probe.lua)"
echo "# carts: f2p = FAIR2PLUS 5a1695da | mt2 = FAIR2PLUS + DRMINTHINK=4 170f179d"
echo "# a landing is HYBRID when it is neither the copro final nor any published candidate of that pill's timeline"
echo
echo "## A. V11 (c51d2e21) timelines: the FAIR2 games of 10/04 (banked V11 case files) + 10/03 G2 (banked V1 a1ef31c8 case file;"
echo "##    V11 == V1 on G2, LEFLUSH.txt section 3) -- CONTROL: f2p must reproduce the execfid lane's banked A_lgp_row2 runs"
$PY tools/a16mt/replay_table.py $RUNS v11 f2p,mt2 \
  m2g1=$X/timelines/pubtrace_m2g1_fair_20261004.jsonl m2g2=$X/timelines/pubtrace_m2g2_fair_20261004.jsonl \
  m2g3=$X/timelines/pubtrace_m2g3_fair_20261004.jsonl m4g1=$X/timelines/pubtrace_m4g1_fair_20261004.jsonl \
  m4g2=$CF/pubtrace_m4g2_fair_20261004.jsonl G2=$V1G2 \
  --ctl m2g1=$E/m2g1_A_lgp_row2_chain_garb/lateflip_m2g1_A_lgp_row2_chain_garb.log \
  --ctl m2g2=$E/m2g2_A_lgp_row2_chain_garb/lateflip_m2g2_A_lgp_row2_chain_garb.log \
  --ctl m2g3=$E/m2g3_A_lgp_row2_chain_garb/lateflip_m2g3_A_lgp_row2_chain_garb.log \
  --ctl m4g1=$E/m4g1_A_lgp_row2_chain_garb/lateflip_m4g1_A_lgp_row2_chain_garb.log \
  --ctl m4g2=$E/M4G2_A_lgp_row2_chain_garb/lateflip_M4G2_A_lgp_row2_chain_garb.log \
  --ctl G2=$E/G2_1003_A_lgp_row2_v1_chain_garb/lateflip_G2_1003_A_lgp_row2_v1_chain_garb.log
echo
echo "## A2. the FAIR-owner games of 10/04 on NEW V11 timelines (co-sim this lane; their banked timelines are 1488e158)"
$PY tools/a16mt/replay_table.py $RUNS v11 f2p,mt2 \
  m1g1=$A/timelines/pubtrace_m1g1_v11.jsonl m1g2=$A/timelines/pubtrace_m1g2_v11.jsonl m3g1=$A/timelines/pubtrace_m3g1_v11.jsonl \
  m3g2=$A/timelines/pubtrace_m3g2_v11.jsonl m3g3=$A/timelines/pubtrace_m3g3_v11.jsonl m5g2=$A/timelines/pubtrace_m5g2_v11.jsonl
echo
echo "## C. V11 + A16 (b545d740) timelines, every game (A16 co-sim for <= 16 viruses, V11 records for > 16: merge logs below)"
for g in m2g1 m2g2 m2g3 m4g1 m4g2 G2 m1g1 m1g2 m3g1 m3g2 m3g3 m5g2; do
  echo "merge $g: $(command grep -a -v '^MERGE' $A/logs/merge_$g.log 2>/dev/null | tr '\n' ' ')$(tail -n 1 $A/logs/merge_$g.log 2>/dev/null | cut -d: -f1)"
done
args=()
for g in m2g1 m2g2 m2g3 m4g1 m4g2 G2 m1g1 m1g2 m3g1 m3g2 m3g3 m5g2; do args+=("$g=$A/timelines/pubtrace_${g}_a16.jsonl"); done
$PY tools/a16mt/replay_table.py $RUNS a16 f2p,mt2 "${args[@]}"
echo
echo "## C2. firmware effect at a fixed cart: the same carts, V11 vs V11 + A16 timelines (landing == copro final of ITS timeline)"
for c in f2p mt2; do
  for fw in v11 a16; do
    n=0; fin=0; hyb=0
    for g in m2g1 m2g2 m2g3 m4g1 m4g2 G2 m1g1 m1g2 m3g1 m3g2 m3g3 m5g2; do
      case $fw:$g in
        v11:m2g1|v11:m2g2|v11:m2g3|v11:m4g1) pub=$X/timelines/pubtrace_${g}_fair_20261004.jsonl;;
        v11:m4g2) pub=$CF/pubtrace_m4g2_fair_20261004.jsonl;; v11:G2) pub=$V1G2;;
        v11:*) pub=$A/timelines/pubtrace_${g}_v11.jsonl;; a16:*) pub=$A/timelines/pubtrace_${g}_a16.jsonl;;
      esac
      tag=${g}_${c}_${fw}_chain_garb
      line=$($PY tools/a16mt/replay_table.py $RUNS $fw $c "$g=$pub" 2>/dev/null | command grep -a "^  $c ")
      set -- $(echo "$line" | sed -E 's/.*n=([0-9]+) ==silicon [0-9]+ ==final ([0-9]+) hybrid ([0-9]+).*/\1 \2 \3/')
      n=$((n + ${1:-0})); fin=$((fin + ${2:-0})); hyb=$((hyb + ${3:-0}))
    done
    echo "  $c on $fw: n=$n ==final $fin hybrid $hyb"
  done
done
echo
echo "## C3. are A16's changed answers executed? (tools/a16mt/fw_effect.py)"
fwargs=()
for g in m2g1 m2g2 m2g3 m4g1; do fwargs+=("$g=$X/timelines/pubtrace_${g}_fair_20261004.jsonl"); done
fwargs+=("m4g2=$CF/pubtrace_m4g2_fair_20261004.jsonl" "G2=$A/timelines/pubtrace_G2_v11.jsonl")
for g in m1g1 m1g2 m3g1 m3g2 m3g3 m5g2; do fwargs+=("$g=$A/timelines/pubtrace_${g}_v11.jsonl"); done
for c in f2p mt2; do $PY tools/a16mt/fw_effect.py $RUNS $A/timelines $c "${fwargs[@]}"; done
