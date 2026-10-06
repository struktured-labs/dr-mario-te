#!/bin/bash
# silfid: Mesen FAIR replay of M1 G4 (banked seed-0 timelines) dumping RAM every 37 frames -> synthetic save-states
S=/home/struktured/projects/dr_mario_rl/tmp/silfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
XW=/home/struktured/projects/dr-mario-execfid-wt/tools/execfid
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
mkdir -p $S/mesen/cases
$PY $XW/gen_cases_garb.py $CF/pubtrace_m1g4_lulu_20261005.jsonl $CF/cases_ai_m1g4_lulu_20261005.jsonl $S/mesen/cases/dump_m1g4.lua > /dev/null 2>&1
LF_DUMP_EVERY=37 LF_DUMP_MAX=200 PROBE=$S/tools/silfid_dump_probe.lua EXECFID_OUT=$S/mesen $XW/run_probe.sh dump_m1g4 \
  /home/struktured/projects/dr_mario_rl/tmp/couch_kit/fair_20261003/drmario_te_couch_fair_dbbb5007.nes $S/mesen/cases/dump_m1g4.lua 20000 0
echo "$(date +%T) DUMPRUN DONE rc=$?"
