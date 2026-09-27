#!/bin/bash
# One isolated, headless p1live arm for #101 (Pocket theta400 tuck cart v2).
#   run_p1live.sh <tag> <cart> <frames> <p1drive 0|1>
# Uses Mesen's built-in test runner: no Avalonia, no X11, no single-instance pipe,
# which sidesteps the Xvfb-dies-after-one-launch and stale-mutex traps.
set -euo pipefail

D="$(cd "$(dirname "$0")/../.." && pwd)"
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json

tag="${1:?tag}"; cart="${2:?cart}"; maxf="${3:?frames}"; p1drive="${4:?0-or-1}"

[[ -f "$cart"  ]] || { echo "missing cart: $cart" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

out="$D/tmp/p1live/$tag"
mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"
log="$out/run.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart md5 $(md5sum "$cart" | cut -d' ' -f1)  mmc1 $(md5sum "$mmc1" | cut -d' ' -f1)"

# One Mesen process at a time (host resource contention, not the SI pipe).
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
    export FP_OUT="$out" FP_MAXF="$maxf" FP_TAG="$tag" FP_P1DRIVE="$p1drive"
    export FP_DLAT=34 FP_SEED=114 FP_WARM=0
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/p1live.lua" -testrunner "-timeout=$deadline"
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
    command grep -a "^P1LIVE\|^SUMMARY" "$log"
    exit 0
  fi
  echo "[$tag] try $try produced no tagged SUMMARY; retrying" >&2
  sleep 5
done
echo "[$tag] FAILED after 3 tries" >&2
exit 4
