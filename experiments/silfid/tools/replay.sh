#!/bin/bash
# silfid: chained + garbage Mesen replay of one game from a pubtrace JSONL on a cart (FAIR by default).
#   replay.sh <tag> <game> <pubtrace.jsonl> [cart] [stale 0|1]     -> $S/mesen/runs/<tag>/lateflip_<tag>.log
set -euo pipefail
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
XW=/home/struktured/projects/dr-mario-execfid-wt/tools/execfid
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
tag=$1; g=$2; pub=$3; cart=${4:-/home/struktured/projects/dr_mario_rl/tmp/couch_kit/fair_20261003/drmario_te_couch_fair_dbbb5007.nes}; stale=${5:-0}
mkdir -p $S/mesen/cases
lua=$S/mesen/cases/${tag}.lua
$PY $XW/gen_cases_garb.py $pub $CF/cases_ai_${g}_lulu_20261005.jsonl $lua > $S/mesen/cases/${tag}.gen.log 2>&1
command grep -aq "^SUMMARY" $S/mesen/runs/$tag/lateflip_$tag.log 2>/dev/null && { echo "skip $tag"; exit 0; }
PROBE=$S/tools/silfid_probe.lua EXECFID_OUT=$S/mesen $XW/run_probe.sh $tag $cart $lua 40000 $stale
