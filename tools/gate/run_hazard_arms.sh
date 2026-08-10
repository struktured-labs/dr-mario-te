#!/bin/bash
set -u
D=/home/struktured/projects/dr-mario-v8-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
mkdir -p "$D/tmp/haz"
for tag in a-v6crepro b-fixon d-mmc1only c-v8ship; do
  $PY "$D/tools/gate/remap_mapper.py" "$D/roms/$tag.nes" "$D/tmp/haz/${tag}_mmc1.nes" >/dev/null
  echo "[haz] === $tag ==="
  bash "$D/tools/gate/launch_p3.sh" "$D/tmp/haz/$tag" "$D/tmp/haz/${tag}_mmc1.nes" "$tag" 3000 0 114 34 300
  command grep -a SUMMARY "$D/tmp/haz/$tag/probe3.log" 2>/dev/null
done
echo "[haz] ALL DONE"
