#!/bin/bash
# run_d131trace.sh <orient 0..3> <frames> -- one constant-orient arm of the #132 mechanism probe.
# Launch discipline copied verbatim from run_framedense.sh (dr-mario-mesen-launch-verification):
# headless -testrunner, per-arm TMPDIR/XDG/output dir, log deleted then required to reappear
# carrying THIS arm's tag, exact-pid reap, no name-pattern kills.
set -euo pipefail

D=/home/struktured/projects/dr-mario-dispatch131-wt
SRC=/home/struktured/projects/dr-mario-pockettuck-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
CART="$SRC/roms/drmario_tuck_cvc_mister.nes"
CART_MD5=9fefaedba9a27ba10f058ac239eeb77d
W=0x5200

orient="${1:?orient 0..3}"; maxf="${2:?frames}"; seed="${DT_SEED:-114}"
tag="dt_o${orient}_${maxf}_s${seed}${DT_CTLFRAME:+_ctl$DT_CTLFRAME}"

got=$(md5sum "$CART" | cut -d' ' -f1)
[[ "$got" == "$CART_MD5" ]] || { echo "CART MD5 MISMATCH: $got != $CART_MD5" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

if ps -eo args | command grep -a 'Release/Mesen' | command grep -av grep >/dev/null; then
  echo "a Mesen is already alive -- refusing to run two arms concurrently" >&2; exit 3
fi

out="$D/tmp/d131trace/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/d131trace.log"
rm -f "$log" "$out/stdout.log" "$out/frames.csv"
"$PY" "$SRC/tools/gate/remap_mapper.py" "$CART" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] orient=$orient frames=$maxf seed=$seed cart_md5=$got"

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export DT_OUT="$out" DT_TAG="$tag" DT_W="$W" DT_ORIENT="$orient" DT_MAXF="$maxf" \
           DT_SEED="$seed" DT_DLAT="${DT_DLAT:-34}" DT_STALLN="${DT_STALLN:-300}" \
           DT_TRFRAMES="${DT_TRFRAMES:-40}" DT_CTLFRAME="${DT_CTLFRAME:-0}"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_d131trace.lua" -testrunner "-timeout=$deadline"
  ) >"$out/stdout.log" 2>&1 &
  runpid=$!

  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    if command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null; then ok=1; break; fi
    if ! kill -0 "$runpid" 2>/dev/null; then
      sleep 3
      command grep -aq "^SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1
      break
    fi
    sleep 5
  done
  kill "$runpid" 2>/dev/null || true
  wait "$runpid" 2>/dev/null || true

  if [[ "$ok" == 1 ]]; then
    mt=$(stat -c %Y "$log")
    if (( mt < launched )); then echo "[$tag] STALE LOG" >&2; exit 4; fi
    echo "[$tag] OK on try $try"
    command grep -a "^SUMMARY" "$log"
    exit 0
  fi
  echo "[$tag] try $try produced no tagged SUMMARY; retrying" >&2
  sleep 5
done
echo "[$tag] FAILED after retries" >&2
exit 1
