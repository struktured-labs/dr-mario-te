#!/bin/bash
# One headless Mesen run of lateflip_probe.lua on one cart.
#   run_lateflip.sh <tag> <cart.nes> <cases.lua> [maxframes] [stale 0|1]
# Mesen's built-in test runner (no Avalonia/X11/single-instance pipe), private TMPDIR/XDG config, one Mesen at a
# time: waits while ANY Mesen process is running (another lane may own the seat) and never kills one it did not start.
set -euo pipefail
D="$(cd "$(dirname "$0")/../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json

tag="${1:?tag}"; cart="$(realpath "${2:?cart}")"; cases="$(realpath "${3:?cases.lua}")"; maxf="${4:-60000}"; stale="${5:-0}"
[[ -f "$cart" && -f "$cases" && -x "$MESEN" ]] || { echo "missing cart/cases/Mesen" >&2; exit 2; }
out="$D/tmp/lateflip/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
mkdir -p "$runtime_tmp/xdg/Mesen2"; cp "$SANDBOX" "$runtime_tmp/xdg/Mesen2/settings.json"
mmc1="$out/${tag}_mmc1.nes"; log="$out/lateflip_${tag}.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart md5 $(md5sum "$cart" | cut -d' ' -f1)  mmc1 $(md5sum "$mmc1" | cut -d' ' -f1)  cases $(md5sum "$cases" | cut -d' ' -f1)"

for _ in $(seq 1 1800); do            # the single Mesen seat: wait for every other Mesen to exit (up to 1 h)
  pgrep -x Mesen >/dev/null || break
  sleep 2
done
pgrep -x Mesen >/dev/null && { echo "[$tag] Mesen seat still busy after 1 h; giving up" >&2; exit 3; }

deadline=$(( maxf / 20 + 300 ))
(
  cd "$(dirname "$MESEN")"
  export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg" DOTNET_GCHeapHardLimit=40000000
  export LF_OUT="$out/" LF_TAG="$tag" LF_CASES="$cases" LF_MAXF="$maxf" LF_STALE="$stale"
  exec nice -n 19 "$RUN_MESEN" "$mmc1" "$D/tools/lateflip/lateflip_probe.lua" -testrunner "-timeout=$deadline"
) >"$out/stdout.log" 2>&1 &
runpid=$!
ok=0
for _ in $(seq 1 $((deadline / 2))); do
  if command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null; then ok=1; break; fi
  kill -0 "$runpid" 2>/dev/null || { sleep 2; command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1; break; }
  sleep 2
done
kill "$runpid" 2>/dev/null || true; wait "$runpid" 2>/dev/null || true
if [[ "$ok" == 1 ]]; then command grep -a "^SUMMARY" "$log"; exit 0; fi
echo "[$tag] no SUMMARY (see $out/stdout.log, $log)" >&2; exit 4
