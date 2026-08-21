#!/bin/bash
# run_sggate.sh <manifest.json> <arm site1|site2|pause2e> <frames> [SG_FORCEMODE]
# One probe_sg.lua arm against the cart a romgen manifest describes. The cart is content-
# verified against the manifest's output md5, and the instrumentation addresses are asked of
# the EMITTER under the manifest's own flag snapshot (dump_labels.py) -- never pinned offsets
# (#120 gate rot). Launch discipline as run_hgate.sh.
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

manifest="${1:?manifest json}"; arm="${2:?site1|site2|pause2e}"; maxf="${3:?frames}"
forcemode="${4:-4}"

cart="$D/roms/$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['output']['name'])" "$manifest")"
want_md5=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['output']['md5'])" "$manifest")
got=$(md5sum "$cart" | cut -d' ' -f1)
[[ "$got" == "$want_md5" ]] || { echo "CART MD5 MISMATCH: $got != $want_md5" >&2; exit 2; }

# label addresses under the manifest's own flag snapshot
labels=$(cd "$D" && eval "$($PY -c "
import json,sys
for k,v in sorted(json.load(open(sys.argv[1]))['flag_snapshot'].items()):
    print(f'export {k}={v!r}')" "$manifest")" && $PY tools/gate/dump_labels.py \
    inj_guard inj_sta an_st_ret fc_press fc_clear 2>/dev/null | command grep -a '=0x')
inj_guard=$(echo "$labels" | command grep -a '^inj_guard=' | cut -d= -f2)
inj_sta=$(echo "$labels"   | command grep -a '^inj_sta='   | cut -d= -f2)
an_ret=$(echo "$labels"    | command grep -a '^an_st_ret=' | cut -d= -f2)
fc_press=$(echo "$labels"  | command grep -a '^fc_press='  | cut -d= -f2)
fc_clear=$(echo "$labels"  | command grep -a '^fc_clear='  | cut -d= -f2)
for v in "$inj_guard" "$inj_sta" "$an_ret" "$fc_press" "$fc_clear"; do
  [[ -n "$v" ]] || { echo "label derivation failed:"; echo "$labels"; exit 5; } >&2
done

cname="$(basename "$cart" .nes)"
tag="sg_${cname}_${arm}_m${forcemode}_${maxf}"
echo "[$tag] cart_md5=$got injGuard=$inj_guard injSta=$inj_sta anRet=$an_ret fcPress=$fc_press fcClear=$fc_clear"

if ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
     | command grep -av '^Z' >/dev/null; then
  echo "a Mesen is already alive -- refusing to run two arms concurrently" >&2; exit 3
fi

out="$D/tmp/sggate/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/sg.log"
rm -f "$log" "$out/stdout.log"
"$PY" "$D/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export SG_OUT="$out" SG_TAG="$tag" SG_ARM="$arm" SG_W="$W" SG_MAXF="$maxf" \
           SG_INJ_GUARD="$inj_guard" SG_INJ_STA="$inj_sta" SG_AN_RET="$an_ret" \
           SG_FC_PRESS="$fc_press" SG_FC_CLEAR="$fc_clear" SG_FORCEMODE="$forcemode" \
           SG_SEED="${SG_SEED:-114}" SG_HOLDF="${SG_HOLDF:-240}"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_sg.lua" -testrunner "-timeout=$deadline"
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
