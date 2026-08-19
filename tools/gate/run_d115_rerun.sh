#!/bin/bash
# run_d115_rerun.sh <tag> <already-remapped cart.nes> <seed> [frames] -- one cell of the #115
# re-run, on the PATCHED probe6 (#135 shape U).
#
# WHY NOT run_one6.sh: it hardcodes D=dr-mario-v8-wt, so it would run the DIVERGED probe6
# (md5 cd9eb4cd) -- not the copy I patched -- and it pins P6_SEED=114 and leaves P6_W at its
# $5000 default, which on a DRPOCKET=0 cart is OPEN BUS (the P2 mailbox is $5200). Using it
# would have re-measured a different probe on a dead mailbox and called it a reproduction.
#
# The carts passed in are the ALREADY-MMC1-REMAPPED images preserved in the Aug-16 run dirs,
# so these are the exact bytes that produced the original numbers -- no rebuild, no re-remap,
# nothing to drift.
#
# Launch discipline per dr-mario-mesen-launch-verification: headless -testrunner (no Xvfb, no
# .NET mutex), per-arm TMPDIR/XDG/out dir, log deleted before launch and required to reappear
# with THIS tag AND newer than the launch, exact-pid reap, seat check on the BINARY not a name.
set -u

D=/home/struktured/projects/dr-mario-hygiene-wt
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json

tag="${1:?tag}"; cart="${2:?remapped cart}"; seed="${3:?seed}"; maxf="${4:-18000}"
W=0x5200          # DRPOCKET=0 => P2's window. $5000 would be OPEN BUS = silently inert.

[ -f "$cart" ] || { echo "no such cart: $cart" >&2; exit 2; }
[ -x "$MESEN" ] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

for _ in $(seq 1 900); do
  ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
    | command grep -av '^Z' >/dev/null || break
  sleep 10
done

out="$D/tmp/d115/${tag}_s${seed}"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"
log="$out/probe6.log"; rm -f "$log" "$out/stdout.log" "$out/d135_census.txt"

body=$(tail -c +17 "$cart" | sha256sum | cut -c1-16)
echo "[$tag s$seed] cart=$(basename "$cart") body_sha=$body frames=$maxf w=$W"

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export D135_OUT="$out"
    export P6_OUT="$out" P6_TAG="$tag" P6_MAXF="$maxf" P6_SEED="$seed" \
           P6_DLAT=34 P6_TUCK=1 P6_W="$W"
    exec "$RUN_MESEN" "$cart" "$D/tools/gate/probe6.lua" -testrunner "-timeout=$deadline"
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

  if [ "$ok" = 1 ]; then
    mt=$(stat -c %Y "$log")
    [ "$mt" -lt "$launched" ] && { echo "[$tag s$seed] STALE LOG" >&2; exit 4; }
    echo "[$tag s$seed] OK try $try"
    exit 0
  fi
  echo "[$tag s$seed] try $try: no tagged SUMMARY; retrying" >&2
  sleep 5
done
# No SUMMARY is a FAILURE, never "no wedge seen".
echo "[$tag s$seed] FAILED after retries" >&2
exit 1
