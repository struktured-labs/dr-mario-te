#!/bin/bash
# build_rotdir.sh <tag> [DRFLAG=VAL ...] -- build from the EXACT flag_snapshot of the cart
# under test (tuck-cvc-mister = 9fefaedb), plus caller overrides. Same single-source-of-truth
# discipline as build_v8tuck.sh, pointed at the #114 baseline. DRBUILDID stays 0.
set -euo pipefail
cd "$(dirname "$0")/../.."
TAG="${1:?usage: build_rotdir.sh <tag> [DRFLAG=VAL ...]}"; shift || true
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
eval "$($PY - <<'PYEOF'
import json
f = json.load(open("roms/manifests/tuck-cvc-mister.json"))["flag_snapshot"]
for k, v in sorted(f.items()):
    print(f"export {k}={v!r}")
PYEOF
)"
for kv in "$@"; do export "${kv?}"; done
echo "--- build: tag=$TAG ---"
env | command grep -a '^DR' | sort | sed 's/^/    /'
$PY tools/romgen.py build --out "roms/${TAG}.nes" --base drmario_v28cs.nes --tag "$TAG"
md5sum "roms/${TAG}.nes"
