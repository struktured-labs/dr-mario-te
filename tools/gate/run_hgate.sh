#!/bin/bash
# run_hgate.sh <cart.nes> <expected_md5> <orient> <frames> -- one probe_d131gate arm against an
# ARBITRARY cart (the hardened-129-133-134 gate family). Same launch discipline as
# run_d131gate.sh (headless -testrunner, per-arm TMPDIR/XDG, tagged-SUMMARY-or-fail, exact-pid
# reap), but the cart is a parameter + content-verified, so the same runner gates every arm of
# a killed-mutant pair instead of being pinned to one shipped image.
# Env: D1_ARM required; D1_SEED/D1_DLAT/D1_STALLN/D1_RESUMEW optional; HG_TAG optional suffix.
set -euo pipefail

D=/home/struktured/projects/dr-mario-v8-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
W=0x5200

cart="${1:?cart path}"; want_md5="${2:?expected md5}"
orient="${3:?orient 0..3}"; maxf="${4:?frames}"; seed="${D1_SEED:-114}"
cname="$(basename "$cart" .nes)"
tag="hg_${cname}_o${orient}_${maxf}_s${seed}_${D1_ARM:?D1_ARM required}${HG_TAG:+_$HG_TAG}"

got=$(md5sum "$cart" | cut -d' ' -f1)
[[ "$got" == "$want_md5" ]] || { echo "CART MD5 MISMATCH: $got != $want_md5" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

if ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
     | command grep -av '^Z' >/dev/null; then
  echo "a Mesen is already alive -- refusing to run two arms concurrently" >&2; exit 3
fi

out="$D/tmp/hgate/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/d131gate.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart_md5=$got orient=$orient frames=$maxf seed=$seed arm=$D1_ARM"

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export D1_OUT="$out" D1_TAG="$tag" D1_W="$W" D1_ORIENT="$orient" D1_MAXF="$maxf" \
           D1_SEED="$seed" D1_DLAT="${D1_DLAT:-34}" D1_STALLN="${D1_STALLN:-300}" \
           D1_RESUMEW="${D1_RESUMEW:-180}" D1_ARM="$D1_ARM"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_d131gate.lua" -testrunner "-timeout=$deadline"
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
