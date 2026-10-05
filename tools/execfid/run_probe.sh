#!/bin/bash
# execfid lane: one headless Mesen run of execfid_probe.lua on one cart (tools/lateflip/run_lateflip.sh + no wall clock).
#   run_probe.sh <tag> <cart.nes> <cases.lua> [maxframes] [stale 0|1]
# Differences: output under $EXECFID_OUT (default tmp/execfid)/runs/<tag>; NO wall-clock deadline that a PAUSE (SIGSTOP) could trip
# (Mesen -timeout and the poll loop are 6 h); meant to be launched inside a systemd user unit execfid-* so the lane's
# throttle (tools/throttle.sh: execfid/PAUSE or tmp/PAUSE_ALL) can stop it. One Mesen at a time: waits for any Mesen.
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
E=${EXECFID_OUT:-$R/tmp/execfid}; mkdir -p "$E"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
PROBE=${PROBE:-$R/tools/execfid/execfid_probe.lua}
tag="${1:?tag}"; cart="$(realpath "${2:?cart}")"; cases="$(realpath "${3:?cases.lua}")"; maxf="${4:-60000}"; stale="${5:-0}"
[[ -f "$cart" && -f "$cases" && -x "$MESEN" ]] || { echo "missing cart/cases/Mesen" >&2; exit 2; }
out="$E/runs/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
mkdir -p "$runtime_tmp/xdg/Mesen2"; cp "$SANDBOX" "$runtime_tmp/xdg/Mesen2/settings.json"
mmc1="$out/${tag}_mmc1.nes"; log="$out/lateflip_${tag}.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$R/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart md5 $(md5sum "$cart" | cut -d' ' -f1)  mmc1 $(md5sum "$mmc1" | cut -d' ' -f1)  cases $(md5sum "$cases" | cut -d' ' -f1) probe $(md5sum "$PROBE" | cut -c1-8)"
exec 9>"$E/mesen.lock"; flock 9                        # serialise this lane's own batches (lock held to exit)
while pgrep -x Mesen >/dev/null; do sleep 2; done      # the single Mesen seat (other lanes' Mesens too)
deadline=21600
(
  cd "$(dirname "$MESEN")"
  export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg" DOTNET_GCHeapHardLimit=40000000
  export LF_OUT="$out/" LF_TAG="$tag" LF_CASES="$cases" LF_MAXF="$maxf" LF_STALE="$stale"
  exec nice -n 19 "$RUN_MESEN" "$mmc1" "$PROBE" -testrunner "-timeout=$deadline"
) >"$out/stdout.log" 2>&1 &
runpid=$!
ok=0
while true; do
  if command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null; then ok=1; break; fi
  kill -0 "$runpid" 2>/dev/null || { sleep 2; command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1; break; }
  sleep 2
done
kill "$runpid" 2>/dev/null || true; wait "$runpid" 2>/dev/null || true
if [[ "$ok" == 1 ]]; then command grep -a "^SUMMARY" "$log"; exit 0; fi
echo "[$tag] no SUMMARY (see $out/stdout.log, $log)" >&2; exit 4
