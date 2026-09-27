#!/bin/bash
cd /home/struktured/projects/dr-mario-h16-wt/experiments/cvx
export NUMBA_CACHE_DIR=/root/drm/nbc_fw DRM_VENDOR=1
xargs -P 4 -L 1 /root/drm/venv/bin/python gate_b.py < /root/drm/l15gb/jobs.txt
echo L15GB_DONE
