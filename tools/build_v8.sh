#!/bin/bash
# build_v8.sh <tag> [extra DRFLAG=VAL ...]
#
# v8 (rematch cart) = the cen6c-both configuration + DRPRESTART.
#   cen6c-both is the acceptance-passed v6c config with DRHOLDBOARD=0. DRHOLDBOARD is the
#   flag that soft-bricks the cart after one match ([[dr-mario-holdboard-softbrick]]); the
#   owner ruled "ship v8 without holdboard we will come back to it".
#   DRBUILDID is pinned 0 so the build stamp cannot move 1868 bytes underneath a comparison.
#
# Flags are taken verbatim from roms/manifests/cen6c-both.json's flag_snapshot so the recipe
# has ONE source of truth and cannot drift from the cart that actually passed acceptance.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:?usage: build_v8.sh <tag> [DRFLAG=VAL ...]}"; shift || true
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

# export cen6c-both's flag snapshot, then the v8 deltas, then any caller overrides
eval "$($PY - <<'EOF'
import json
f = json.load(open("roms/manifests/cen6c-both.json"))["flag_snapshot"]
f["DRPRESTART"] = "1"     # v8 delta: the rematch feature
f["DRHOLDBOARD"] = "0"    # explicit: the soft-brick trigger stays OFF
f["DRBUILDID"] = "0"      # pinned so the stamp never moves under a comparison
for k, v in sorted(f.items()):
    print(f"export {k}={v!r}")
EOF
)"
for kv in "$@"; do export "${kv?}"; done

echo "--- v8 build: tag=$TAG ---"
env | command grep -a '^DR' | sort | sed 's/^/    /'
$PY tools/romgen.py build --out "roms/${TAG}.nes" --base drmario_v28cs.nes --tag "$TAG"
md5sum "roms/${TAG}.nes"
