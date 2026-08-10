#!/bin/bash
# run_v8_gate.sh -- multi-match ship gate for the v8 candidates.
# 18000 frames ~ 20 matches at the ~900 frames/match the control arm measured.
set -u
D=/home/struktured/projects/dr-mario-v8-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
F=${F:-18000}
mkdir -p "$D/tmp/gate"
for tag in v8-rematch v8-fcgate; do
  $PY "$D/tools/gate/remap_mapper.py" "$D/roms/$tag.nes" "$D/tmp/gate/${tag}_mmc1.nes" >/dev/null
  echo "[gate] === $tag ==="
  bash "$D/tools/gate/launch_fp.sh" "$D/tmp/gate/$tag" "$D/tmp/gate/${tag}_mmc1.nes" "$tag" "$F" 0 114 34 700
  command grep -a SUMMARY "$D/tmp/gate/$tag/run.log" 2>/dev/null
done
echo "[gate] ALL DONE"
