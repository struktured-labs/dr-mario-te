#!/bin/bash
# C-deep chain: resync redmage at current commit, re-run the cross-box gate
# (registered rule: resync at a new commit re-gates), then launch BOTH boxes.
set -eo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
cd "$HERE"

echo "[cdeep] resync redmage..."
rsync -a --delete ~/projects/dr-mario-labels146-wt/experiments/labels146/ \
  redmage:~/projects/dr-mario-labels146-wt/experiments/labels146/ \
  --exclude 'garbage/out/labels' --exclude 'tmp-numba-cache'
COMMIT=$(git -C ~/projects/dr-mario-labels146-wt log -1 --format=%H)
ssh -o BatchMode=yes redmage "printf 'resynced %s commit %s\n' \"\$(date -Is)\" '$COMMIT' >> ~/projects/dr-mario-labels146-wt/SYNC_MANIFEST.txt"

echo "[cdeep] re-run cross-box gate on redmage..."
ssh -o BatchMode=yes redmage 'bash ~/gate_xbox.sh 2>&1 | tail -3' | tee /tmp/xbox_regate.txt
grep -q 'XBOX_BYTE_EQUAL PASS' /tmp/xbox_regate.txt

echo "[cdeep] launch redmage (14 workers)..."
ssh -o BatchMode=yes redmage 'systemd-run --user --unit=drm-cdeep-red --collect \
  -p MemoryMax=26G -p MemorySwapMax=0 -p Nice=5 \
  bash -c "cd ~/projects/dr-mario-labels146-wt/experiments/labels146/garbage && \
    PYTHONPATH=\"\$PWD:\$PWD/..:\$PWD/../../eval47/stage2/oracle:\$PWD/../../eval47/stage2/oracle/bootstrap:\$HOME/projects/dr-mario-qa-wt/experiments\" \
    NUMBA_CACHE_DIR=\"\$PWD/../tmp-numba-cache\" \
    ~/projects/dr_mario_rl/tmp/venv/bin/python -u harvest_garbage.py \
      --set cdeep-redmage --workers 14 2>&1 | tee -a out/cdeep_redmage.log"'

echo "[cdeep] launch blackmage (20 workers)..."
systemd-run --user --unit=drm-cdeep-black --collect \
  -p MemoryMax=48G -p MemorySwapMax=0 -p Nice=10 \
  bash -c "cd $HERE && \
    PYTHONPATH=\"$HERE:$HERE/..:$HERE/../../eval47/stage2/oracle:$HERE/../../eval47/stage2/oracle/bootstrap:/home/struktured/projects/dr-mario-qa-wt/experiments\" \
    NUMBA_CACHE_DIR=\"$HERE/../tmp-numba-cache\" \
    /home/struktured/projects/dr_mario_rl/tmp/venv/bin/python -u harvest_garbage.py \
      --set cdeep-blackmage --workers 20 2>&1 | tee -a out/cdeep_blackmage.log"
echo "[cdeep] both launched"
