#!/usr/bin/env bash
# TAPOUT autopilot: waits for the screen farm, applies the pre-registered screen rule, runs the main phase (selected arms,
# 5,100 seeds) then Q2 (the main block's lowest-kill arm at k32, 2,000 seeds), then the analysis. Nothing is committed
# or pushed by this script. Launch: systemd-run --user --unit tapout-auto -p Nice=19 tapout_auto.sh
set -uo pipefail
CVX=$(cd "$(dirname "$0")" && pwd); TMP=$CVX/../../tmp/tapout; PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd "$CVX"; W=${TAPOUT_WORKERS:-16}
until grep -q DONE "$TMP/STATUS_screen.txt" 2>/dev/null; do sleep 120; done
$PY analyze_tapout.py screen > "$TMP/auto.log" 2>&1 || exit 3
mkdir -p tapout/main; : > tapout/jobs_main.txt
for a in $(cat tapout/selected.txt); do for i in $(seq 0 101); do lo=$((44300 + 100 * i))
  echo "50 tapout/main/T_${a}_u8_$lo.jsonl race T_${a}_u8 2.84 lulu202610b $lo 50 2 tapout/main/T_${a}_u8_$lo.jsonl" >> tapout/jobs_main.txt; done; done
"$CVX/tapout_farm.sh" "$CVX/tapout/jobs_main.txt" main "$W"
best=$($PY - <<'P'
import json,glob,sys
sys.path.insert(0,"."); import import_pin; import_pin.pin()
from analyze_tapout import rows, oc
sel=open("tapout/selected.txt").read().split()
print(min(sel,key=lambda a: sum(oc(r)["kill"] for r in rows(f"tapout/main/T_{a}_u8_*.jsonl",f"T_{a}_u8").values())))
P
)
echo "Q2 arm $best" >> "$TMP/auto.log"; : > tapout/jobs_q2.txt
for i in $(seq 0 39); do lo=$((44300 + 100 * i)); echo "50 tapout/main/T_${best}_k32_$lo.jsonl race T_${best}_k32 2.84 lulu202610b $lo 50 2 tapout/main/T_${best}_k32_$lo.jsonl" >> tapout/jobs_q2.txt; done
"$CVX/tapout_farm.sh" "$CVX/tapout/jobs_q2.txt" q2 "$W"
$PY analyze_tapout.py main >> "$TMP/auto.log" 2>&1
echo "AUTO DONE $(date -u +%FT%TZ)" >> "$TMP/auto.log"
