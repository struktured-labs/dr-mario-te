#!/bin/bash
# run_probe9.sh <tag> <cart> <frames> <arm|ctrl|base> <ram.hex>
# One isolated headless probe9 arm for task #129 (soak-wedge reproduction gate).
# Same shape as run_probe.sh: Mesen's -testrunner, so no Avalonia / no X11 / no
# single-instance pipe -- which sidesteps the Xvfb-dies-after-one-launch and
# stale-mutex traps documented in dr-mario-mesen-launch-verification.
set -euo pipefail

D="$(cd "$(dirname "$0")/../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json

tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:?frames}"; mode="${4:?arm|ctrl|base}"; ram="${5:-}"

[[ -f "$cart"  ]] || { echo "missing cart: $cart" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }
[[ "$mode" == "base" || -f "$ram" ]] || { echo "missing ram hex: $ram" >&2; exit 2; }

out="$D/tmp/probe/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/probe9.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] mode=$mode cart md5 $(md5sum "$cart" | cut -d' ' -f1)"

for _ in $(seq 1 600); do
  ps -eo args | command grep -a "$MESEN" | command grep -av grep >/dev/null || break
  sleep 2
done

deadline=$(( maxf / 25 + 240 ))
for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export DOTNET_GCHeapHardLimit=40000000
    export P9_OUT="$out" P9_MAXF="$maxf" P9_TAG="$tag" P9_MODE="$mode" P9_RAM="$ram"
    export P9_W="${PROBE_W:-0x5200}" P9_INJF="${P9_INJF:-3000}" P9_OBSF="${P9_OBSF:-1800}"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe9.lua" -testrunner "-timeout=$deadline"
  ) >"$out/stdout.log" 2>&1 &
  runpid=$!

  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    if command grep -aq "SUMMARY tag=$tag" "$log" 2>/dev/null; then ok=1; break; fi
    if ! kill -0 "$runpid" 2>/dev/null; then
      sleep 3
      command grep -aq "SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1
      break
    fi
    sleep 2
  done
  kill "$runpid" 2>/dev/null || true
  wait "$runpid" 2>/dev/null || true
  if [[ "$ok" == 1 ]]; then
    echo "[$tag] OK on try $try"
    command grep -a "^SUMMARY" "$log"
    exit 0
  fi
  echo "[$tag] try $try produced no tagged SUMMARY; retrying" >&2
  sleep 5
done
echo "[$tag] FAILED after retries" >&2
exit 1
