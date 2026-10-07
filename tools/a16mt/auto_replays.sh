#!/usr/bin/env bash
# a16mt lane: as the co-sim timelines land (tools/a16mt/pubtrace_games.sh), build the chained + garbage case files and run
# FAIR2PLUS (f2p, 5a1695da) and FAIR2PLUS+MT2 (mt2, 170f179d) on them.
#   stage v11 : the 10/04 FAIR-owner games (m1g1 m1g2 m3g1 m3g2 m3g3 m5g2) on NEW V11 timelines (their banked timelines
#               are fw 1488e158, the FAIR build's); the FAIR2 games + 10/03 G2 ran on the banked V11/V1 case files.
#   stage a16 : every game on the V11 + A16 (b545d740) timeline = A16 co-sim records for <= 16 viruses + V11 records
#               for > 16 (tools/a16mt/merge_timelines.py checks the identity on <= 4 and on a > 16 sample).
#   auto_replays.sh v11|a16 [game ...]      (a16: each game waits until its V11 base and A16 timelines exist and no
#                                             a16mt-pubtrace* unit is still writing them)
set -uo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
A=/home/struktured/projects/dr_mario_rl/tmp/a16mt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
X=/home/struktured/projects/dr-mario-h16-wt/experiments/execfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
CARTS="f2p=$A/carts/fair2plus_5a1695da.nes mt2=$A/carts/fair2plus_mt2_170f179d.nes"
cases_of() { case $1 in m4g2) echo $CF/cases_m4g2_fair_20261004.jsonl;; G2) echo $CF/cases_g2_dist60_20261003.jsonl;;
                        *) echo $X/cases/cases_${1}_fair_20261004.jsonl;; esac; }
v11_of() { case $1 in m2g1|m2g2|m2g3|m4g1) echo $X/timelines/pubtrace_${1}_fair_20261004.jsonl;;
                      m4g2) echo $CF/pubtrace_m4g2_fair_20261004.jsonl;; *) echo $A/timelines/pubtrace_${1}_v11.jsonl;; esac; }
waitfor() { until [ -s "$1" ]; do sleep 20; done; }
stage=$1; shift
if [ "$stage" = v11 ]; then
  for g in ${@:-m3g1 m3g2 m3g3 m1g2 m1g1 m5g2}; do
    waitfor "$(v11_of $g)"
    [ -s $A/cases/${g}_v11_chain_garb.lua ] || $PY "$R/tools/execfid/gen_cases_garb.py" "$(v11_of $g)" "$(cases_of $g)" $A/cases/${g}_v11_chain_garb.lua
    "$R/tools/a16mt/replay_batch.sh" v11 $A/cases "$g" "$CARTS"
  done
else
  for g in ${@:-m2g2 m2g3 m4g1 m4g2 m2g1 G2 m3g1 m3g2 m3g3 m1g2 m1g1 m5g2}; do
    # inputs complete: the V11 base, the A16 <= 16 file, and no co-sim still running for this game (a .part file)
    until [ -s "$(v11_of $g)" ] && [ -e $A/timelines/pubtrace_${g}_a16_le16.jsonl ] && \
          ! ls $A/timelines/pubtrace_${g}_*.part >/dev/null 2>&1 && \
          ! command grep -aq "^$g sel=gt16s" <(tail -n 1 $A/logs/pubtrace_unit.log $A/logs/pubtrace_unit3.log 2>/dev/null); do sleep 30; done
    "$PY" "$R/tools/a16mt/merge_timelines.py" "$(v11_of $g)" $A/timelines/pubtrace_${g}_a16_le16.jsonl \
        $A/timelines/pubtrace_${g}_a16_gt16s.jsonl $A/timelines/pubtrace_${g}_a16.jsonl > $A/logs/merge_$g.log 2>&1
    echo "merge $g: $(tail -1 $A/logs/merge_$g.log)"
    $PY "$R/tools/execfid/gen_cases_garb.py" $A/timelines/pubtrace_${g}_a16.jsonl "$(cases_of $g)" $A/cases/${g}_a16_chain_garb.lua
    "$R/tools/a16mt/replay_batch.sh" a16 $A/cases "$g" "$CARTS"
  done
fi
echo "AUTO DONE $stage"
