#!/bin/bash
# run_probe6_hardened.sh <manifest.json> [frames] -- the hardened cart's full-match play gate:
# the leak-patched probe6 (NEVER run_one6.sh -- diverged probe + dead $5000 window on these
# carts), 18k frames default, W=$5200 (the P2 mailbox on DRPOCKET=0 dual-window carts),
# D135 census on. Launch discipline per run_d115_rerun.sh (headless -testrunner, per-arm
# TMPDIR/XDG, tagged-SUMMARY-or-fail, exact-pid reap).
set -euo pipefail

# Worktree-relative (dispatcher-hook pattern, 2026-08-20 #140): a hardcoded worktree
# here silently gated ANOTHER worktree's carts when run from a foreign checkout.
D=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel) || exit 2
[ -f "$D/patch_cartridge_copro.py" ] || { echo "FAIL: resolved worktree $D lacks the emitter -- refusing to gate the wrong tree" >&2; exit 2; }
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
W=0x5200

manifest="${1:?manifest json}"; maxf="${2:-18000}"
cart="$D/roms/$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['output']['name'])" "$manifest")"
want_md5=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['output']['md5'])" "$manifest")
got=$(md5sum "$cart" | cut -d' ' -f1)
[[ "$got" == "$want_md5" ]] || { echo "CART MD5 MISMATCH: $got != $want_md5" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

cname="$(basename "$cart" .nes)"
tag="p6_${cname}_${maxf}"

for _ in $(seq 1 900); do
  ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
    | command grep -av '^Z' >/dev/null || break
  sleep 10
done

out="$D/tmp/hgate/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/probe6.log"
rm -f "$log" "$out/stdout.log" "$out/d135_census.txt"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart_md5=$got frames=$maxf w=$W probe6_md5=$(md5sum "$D/tools/gate/probe6.lua" | cut -d' ' -f1)"

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export D135_OUT="$out"
    export P6_OUT="$out" P6_TAG="$tag" P6_MAXF="$maxf" P6_SEED="${P6_SEED:-114}" \
           P6_DLAT=34 P6_TUCK=1 P6_W="$W"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe6.lua" -testrunner "-timeout=$deadline"
  ) >"$out/stdout.log" 2>&1 &
  runpid=$!

  ok=0
  for _ in $(seq 1 $((deadline / 2))); do
    command grep -aq "SUMMARY tag=$tag" "$log" 2>/dev/null && { ok=1; break; }
    kill -0 "$runpid" 2>/dev/null || { sleep 3
      command grep -aq "SUMMARY tag=$tag" "$log" 2>/dev/null && ok=1; break; }
    sleep 5
  done
  kill "$runpid" 2>/dev/null || true
  wait "$runpid" 2>/dev/null || true

  if [[ "$ok" == 1 ]]; then
    mt=$(stat -c %Y "$log")
    (( mt >= launched )) || { echo "[$tag] STALE LOG" >&2; exit 4; }
    echo "[$tag] OK try $try"
    command grep -a "^SUMMARY" "$log"
    cat "$out/d135_census.txt" 2>/dev/null || echo "NO d135 census -- FAILURE, not zero"
    exit 0
  fi
  echo "[$tag] try $try: no tagged SUMMARY; retrying" >&2
  sleep 5
done
echo "[$tag] FAILED after retries" >&2
exit 1
