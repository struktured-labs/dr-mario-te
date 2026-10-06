#!/bin/bash
# One headless Mesen run of the late-flip probe (abort-stale lane copy: tmp/abort_stale/tools/lateflip/lateflip_probe.lua,
# read-only) on one cart -- tools/lateflip/run_lateflip.sh with every WALL-CLOCK limit made PAUSE-aware:
#   * Mesen's own test-runner -timeout is set to 1 day (it is wall clock: a SIGSTOP would otherwise expire it)
#   * the watchdog counts only seconds during which the shared-box PAUSE file is ABSENT (the lane throttle SIGSTOPs Mesen
#     while it exists), so a pause can never kill a run
#   * the single-Mesen seat wait is unbounded (never runs two Mesens; never kills one it did not start)
#   run_mesen.sh <tag> <cart.nes> <cases.lua> [maxframes] [stale 0|1]     (outputs: $V11/mesen/runs/<tag>/)
set -euo pipefail
D=/home/struktured/projects/dr-mario-lateflip-wt   # remap_mapper.py only (read-only)
V11=/home/struktured/projects/dr_mario_rl/tmp/v11
PAUSE=$V11/PAUSE
PROBE=/home/struktured/projects/dr_mario_rl/tmp/abort_stale/tools/lateflip/lateflip_probe.lua
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json

tag="${1:?tag}"; cart="$(realpath "${2:?cart}")"; cases="$(realpath "${3:?cases.lua}")"; maxf="${4:-20000}"; stale="${5:-0}"
[[ -f "$cart" && -f "$cases" && -x "$MESEN" ]] || { echo "missing cart/cases/Mesen" >&2; exit 2; }
out="$V11/mesen/runs/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
mkdir -p "$runtime_tmp/xdg/Mesen2"; cp "$SANDBOX" "$runtime_tmp/xdg/Mesen2/settings.json"
mmc1="$out/${tag}_mmc1.nes"; log="$out/lateflip_${tag}.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart md5 $(md5sum "$cart" | cut -d' ' -f1)  mmc1 $(md5sum "$mmc1" | cut -d' ' -f1)  cases $(md5sum "$cases" | cut -d' ' -f1)"
while pgrep -x Mesen >/dev/null || [ -e "$PAUSE" ]; do sleep 2; done      # one Mesen at a time; not while paused
budget=$(( maxf / 20 + 300 ))                                              # ACTIVE seconds (paused time not counted)
(
  cd "$(dirname "$MESEN")"
  export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg" DOTNET_GCHeapHardLimit=40000000
  export LF_OUT="$out/" LF_TAG="$tag" LF_CASES="$cases" LF_MAXF="$maxf" LF_STALE="$stale"
  exec nice -n 19 "$RUN_MESEN" "$mmc1" "$PROBE" -testrunner "-timeout=86400"
) >"$out/stdout.log" 2>&1 &
runpid=$!
ok=0; active=0
while [ $active -lt $budget ]; do
  if command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null; then ok=1; break; fi
  kill -0 "$runpid" 2>/dev/null || { sleep 2; command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1; break; }
  sleep 2
  [ -e "$PAUSE" ] || active=$((active + 2))
done
kill "$runpid" 2>/dev/null || true; wait "$runpid" 2>/dev/null || true
if [[ "$ok" == 1 ]]; then command grep -a "^SUMMARY" "$log"; exit 0; fi
echo "[$tag] no SUMMARY after $active active s (see $out/stdout.log, $log)" >&2; exit 4
