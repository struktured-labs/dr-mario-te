#!/bin/bash
# Auto-start the 2x run the moment the machine-checkable conditions are met.
# No human in the loop and no preference in the loop: the policy comes from the
# MEASURED SE via the rule encoded in stage2_scale.py (SE > 3.8 -> champion).
set -u
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
cd /home/struktured/projects/dr-mario-selfplay-wt/experiments/selfplay

while [ ! -f SE_D3DELTA.txt ] || ! grep -q "SE MEASURE DONE" SE_D3DELTA.txt; do sleep 60; done

SE=$(grep -oP 'per-label SE \(CRN\)\s+\K[0-9.]+' SE_D3DELTA.txt | head -1)
if [ -z "$SE" ]; then
  echo "could not parse SE from SE_D3DELTA.txt -- defaulting to CHAMPION" >> logs/start_2x.log
  POL=champion
else
  POL=$($PY - "$SE" <<'PYEOF'
import sys
se = float(sys.argv[1])
print("d3delta" if se <= 3.8 else "champion")
PYEOF
)
fi
echo "measured SE=${SE:-parse-failed} -> policy=$POL  $(date -Is)" >> logs/start_2x.log
$PY stage2_scale.py --se-d3delta "${SE:-3.99}" >> logs/start_2x.log 2>&1

# 560 positions total; Stage 1's 140 are reused, so ~420 are new.
$PY -u scale_label.py --policy "$POL" --positions 560 --rollouts 8 --workers 8 \
    --out out/scale_labels.jsonl --max-rss-gb 24 >> logs/scale_label.log 2>&1
echo "2X LABELLING DONE $(date -Is)" >> logs/start_2x.log
