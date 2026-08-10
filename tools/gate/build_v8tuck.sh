#!/bin/bash
# build_v8tuck.sh <tag> [DRFLAG=VAL ...]
#
# Build a cart from c-v8ship.json's EXACT flag_snapshot, plus caller overrides.
# ONE source of truth: the manifest of the cart that actually passed the v8 gate, so a
# "v8 + one flag" arm cannot silently drift in any other flag.
# DRBUILDID stays 0 (pinned in that snapshot) so the stamp never moves under a comparison.
set -euo pipefail
cd "$(dirname "$0")/../.."
TAG="${1:?usage: build_v8tuck.sh <tag> [DRFLAG=VAL ...]}"; shift || true
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python

eval "$($PY - <<'EOF'
import json
f = json.load(open("roms/manifests/c-v8ship.json"))["flag_snapshot"]
for k, v in sorted(f.items()):
    print(f"export {k}={v!r}")
EOF
)"
for kv in "$@"; do export "${kv?}"; done

echo "--- build: tag=$TAG ---"
env | command grep -a '^DR' | sort | sed 's/^/    /'
$PY tools/romgen.py build --out "roms/${TAG}.nes" --base drmario_v28cs.nes --tag "$TAG"
md5sum "roms/${TAG}.nes"
