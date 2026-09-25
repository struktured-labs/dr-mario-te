#!/bin/bash
cd /home/struktured/projects/dr-mario-h16-wt/experiments/cvx
export NUMBA_CACHE_DIR=/root/drm/nbc_fw
xargs -P 4 -L 1 /root/drm/venv/bin/python vs_race.py < /root/drm/l15/jobs.txt
echo L15_DONE
