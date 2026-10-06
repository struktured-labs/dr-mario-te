#!/usr/bin/env bash
# Build the ANTIBODY_DIST couch cart with DRLATEGUARD off (IDENTITY: must reproduce the shipped c960dd49) and on.
# Flags = the c960dd49 DRFLAGSNAPSHOT (experiments/lateflip/couch_c960dd49_flags.json) + DRLATEGUARD; the TE branding
# comes from the te-v8.2 worktree's build_copro_branded_env.py, run from this worktree (its patch_cartridge_copro.py
# is picked up via cwd), exactly as experiments/reach/build_spawnedge_carts.sh does.
#   tools/lateflip/build_couch_lateguard.sh [outdir]      (default tmp/carts)
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$R"
OUT="${1:-tmp/carts}"; mkdir -p "$OUT"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
TE_DIR=/home/struktured/projects/dr-mario-te-v8.2
ENV=$($PY -c "
import json
s = json.load(open('experiments/lateflip/couch_c960dd49_flags.json'))['flag_snapshot']
print(' '.join(f'{k}={v}' for k, v in sorted(s.items())))")
for LG in 0 1; do
  env $ENV TE_FOOTER=0 DRLATEGUARD=$LG TE_DIR=$TE_DIR nice -n 19 $PY $TE_DIR/build_copro_branded_env.py drmario_v28cs.nes \
      "$OUT/couch_lateguard$LG.nes" > "$OUT/couch_lateguard$LG.log" 2>&1
done
md5sum "$OUT/couch_lateguard0.nes" "$OUT/couch_lateguard1.nes"
[ "$(md5sum < "$OUT/couch_lateguard0.nes" | cut -c1-32)" = c960dd499e877f01c483af1347ed8df6 ] \
  && echo "IDENTITY couch DRLATEGUARD=0 == c960dd49: PASS" || { echo "IDENTITY couch DRLATEGUARD=0: FAIL"; exit 1; }
