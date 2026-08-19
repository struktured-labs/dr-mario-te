#!/bin/bash
# run_d114_rerun.sh <armtag> <cart.nes> <expected md5> <seed> [frames] -- one cell of the
# PREREG_ROTDIR_V3 re-run, on the LEAK-PATCHED probe_rotwedge.
#
# ⚠ WHY NOT rot-exec's run_rotwedge.sh: it hardcodes D=dr-mario-rotexec-wt, whose
# probe_rotwedge.lua is md5 0c640972 -- the UNPATCHED copy, i.e. exactly the harness whose
# START leak ate v2's cells and produced the NO-VERDICT this run exists to clear. Re-running
# the ladder on it would reproduce the blocker and call it data.
#
# Launch discipline per dr-mario-mesen-launch-verification: headless -testrunner, per-cell
# TMPDIR/XDG/out dir, log deleted before launch then required to reappear with THIS tag AND
# newer than the launch, exact-pid reap, seat check on the BINARY (never a name pattern --
# this script's own argv carries the cart path and would match itself).
set -u

D=/home/struktured/projects/dr-mario-hygiene-wt
SRC=/home/struktured/projects/dr-mario-rotexec-wt      # carts + remap_mapper.py only
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
W=0x5200          # DRPOCKET=0 => P2's window. $5000 is OPEN BUS = silently inert.
ORIENT="${D114_ORIENT:-1}"   # PREREG_ROTDIR_V3: WIN orient (1) for the main sheet. The mutant
                  # table also needs the delta-3 CONTROL half (orient 0) -- m2b is chosen
                  # precisely to sail through a win-only gate and die on the control.

arm="${1:?armtag}"; cart="${2:?cart}"; want="${3:?expected md5}"; seed="${4:?seed}"
maxf="${5:-12000}"
tag="d114_${arm}_o${ORIENT}_${maxf}_s${seed}"

[ -f "$cart" ] || { echo "no such cart: $cart" >&2; exit 2; }
got=$(md5sum "$cart" | cut -d' ' -f1)
[ "$got" = "$want" ] || { echo "CART MD5 MISMATCH $cart: $got != $want" >&2; exit 2; }
[ -x "$MESEN" ] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

for _ in $(seq 1 900); do
  ps -eo stat,args | command grep -a 'Release/Mesen' | command grep -av grep \
    | command grep -av '^Z' >/dev/null || break
  sleep 10
done

out="$D/tmp/d114/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/rotwedge.log"
rm -f "$log" "$out/stdout.log" "$out/d135_census.txt"
"$PY" "$SRC/tools/gate/remap_mapper.py" "$cart" "$mmc1" >"$out/remap.log" 2>&1
echo "[$tag] cart=$(basename "$cart") md5=$got seed=$seed frames=$maxf w=$W orient=$ORIENT"

deadline=$(( maxf / 12 + 300 ))
launched=$(date +%s)

for try in 1 2 3; do
  rm -f "$log"
  (
    cd "$(dirname "$MESEN")"
    export TMPDIR="$runtime_tmp" XDG_CONFIG_HOME="$runtime_tmp/xdg"
    export D135_OUT="$out"
    export RW_OUT="$out" RW_TAG="$tag" RW_W="$W" RW_ORIENT="$ORIENT" RW_MAXF="$maxf" \
           RW_SEED="$seed" RW_DLAT="${RW_DLAT:-34}" RW_STALLN="${RW_STALLN:-300}"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_rotwedge.lua" -testrunner "-timeout=$deadline"
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
    [ "$mt" -lt "$launched" ] && { echo "[$tag] STALE LOG" >&2; exit 4; }
    echo "[$tag] OK try $try: $(command grep -a '^SUMMARY' "$log" | tail -1 | cut -c1-120)"
    exit 0
  fi
  echo "[$tag] try $try: no tagged SUMMARY; retrying" >&2
  sleep 5
done
# A missing SUMMARY is a FAILURE, never "clean". v2's seed-4014 hole is exactly this.
echo "[$tag] FAILED after retries" >&2
exit 1
