#!/bin/bash
# Duel ledger v3: staleness-guarded. A row is only written from a capture FILE NEWER than
# the previous one; repeated settle-failures emit STALE markers instead of silent stale rows.
OUT=~/projects/dr-mario-qa-wt/experiments/duel_ledger/ledger_$(date +%Y%m%d_%H%M)_v3.csv
LC=~/projects/dr_mario_rl/tmp/livecatch
echo "ts,mode,vc_p1,vc_p2,file,status" > "$OUT"
last=""
fails=0
while true; do
  MISTER_HOST=$(~/projects/dr_mario_rl/tmp/mister_ip.sh) bash ~/projects/dr-mario-qa-wt/tools/livecatch/ring_capture.sh --once >/dev/null 2>&1
  SS=$(ls -t "$LC"/*.ss 2>/dev/null | head -1)
  if [ -n "$SS" ] && [ "$SS" != "$last" ]; then
    last="$SS"; fails=0
    /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python - "$SS" >> "$OUT" <<'PYEOF'
import sys, time, os
f=open(sys.argv[1],"rb").read()
ram=f[0x102B08:0x102B08+0x800]
v1=sum(1 for x in ram[0x400:0x480] if (x&0xF0)==0xD0)
v2=sum(1 for x in ram[0x500:0x580] if (x&0xF0)==0xD0)
print("%d,%d,%d,%d,%s,OK" % (time.time(), ram[0x46], v1, v2, os.path.basename(sys.argv[1])))
PYEOF
  else
    fails=$((fails+1))
    echo "$(date +%s),,,,,STALE_x${fails}" >> "$OUT"
    if [ $((fails % 5)) -eq 0 ]; then echo "WEDGE-SUSPECT: ${fails} consecutive stale captures" >&2; fi
  fi
  # FROZEN-COUNTS alarm (freeze #6 gap, 2026-08-04): a save-CAPABLE mid-play stall
  # produces NEW capture files whose (mode,v1,v2) never change -- the stale-file
  # alarm above cannot see it (8 identical rows / 25 min sailed through). Alarm on
  # >=3 consecutive identical in-play rows (~9 min; legit boards change faster).
  idr=$(tail -3 "$OUT" | awk -F, '$2==4 {print $2","$3","$4}' | sort -u | wc -l)
  nin=$(tail -3 "$OUT" | awk -F, '$2==4' | wc -l)
  if [ "$nin" -eq 3 ] && [ "$idr" -eq 1 ]; then
    echo "WEDGE-SUSPECT: frozen in-play counts across 3 captures ($(tail -1 "$OUT" | cut -d, -f2-4))" >&2
  fi
  sleep 180
done
