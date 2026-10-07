#!/usr/bin/env bash
# a16mt lane: Verilator co-sim publish timelines (h16 experiments/lateflip/pubtrace_g2.py, vsim_pub2 = RTL 3b164c7) for
# the 10/04 couch games and the 10/03 G2 boards, for one firmware.
#   pubtrace_games.sh <fwtag> <fw.hex> <sel> <game> ...
#     sel = all      -> every pill
#           le16     -> only pills with <= 16 viruses on the uploaded board (where A16's target can differ from V11's)
#           gt16s    -> an identity sample of > 16-virus pills (every 6th, plus every 17-virus pill)
#   -> $A/timelines/pubtrace_<game>_<fwtag>[_<sel>].jsonl     (J parallel vsims, default 4; nice 19)
# Cases: 10/04 games = h16 experiments/execfid/cases (m4g2: couch_forensics); G2 = couch_forensics cases_g2_dist60_20261003.
set -uo pipefail
fwtag=$1; fw=$2; sel=$3; shift 3
A=/home/struktured/projects/dr_mario_rl/tmp/a16mt; mkdir -p "$A/timelines"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
X=/home/struktured/projects/dr-mario-h16-wt/experiments/execfid
CF=/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics
PT=/home/struktured/projects/dr-mario-h16-wt/experiments/lateflip/pubtrace_g2.py
for g in "$@"; do
  case $g in
    m4g2) cs=$CF/cases_m4g2_fair_20261004.jsonl;;
    G2)   cs=$CF/cases_g2_dist60_20261003.jsonl;;
    *)    cs=$X/cases/cases_${g}_fair_20261004.jsonl;;
  esac
  ps=$($PY - "$cs" "$sel" <<'PYEOF'
import json, sys
Q = [json.loads(l) for l in open(sys.argv[1])]
sel = sys.argv[2]
if sel == "all":
    P = [q["p"] for q in Q]
elif sel == "le16":
    P = [q["p"] for q in Q if q["virus_count"] <= 16]
else:
    big = [q for q in Q if q["virus_count"] > 16]
    P = sorted({q["p"] for k, q in enumerate(big) if k % 6 == 0 or q["virus_count"] == 17})
print(" ".join(map(str, P)))
PYEOF
)
  out=$A/timelines/pubtrace_${g}_${fwtag}$([ "$sel" = all ] || echo "_$sel").jsonl
  if [ -s "$out" ]; then echo "$g SKIP (exists $out)"; continue; fi
  n=$(echo $ps | wc -w)
  if [ "$n" = 0 ]; then : > "$out"; echo "$g sel=$sel 0 pills (empty file)"; continue; fi
  echo "$g sel=$sel $n pills -> $out  $(date -Is)"
  CASES=$cs FW=$fw J=${J:-4} nice -n 19 $PY $PT "$out.part" $ps > "$A/logs/pubtrace_${g}_${fwtag}_$sel.log" 2>&1 \
    && mv "$out.part" "$out"
  echo "$g rc=$? fw=$(md5sum < "$fw" | cut -c1-8) $(date -Is)"
done
echo "PUBTRACE DONE $fwtag $sel"
