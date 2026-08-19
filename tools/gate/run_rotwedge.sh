#!/bin/bash
# run_rotwedge.sh <orient 0..3> <frames> -- one constant-orient arm of the #132 mechanism probe.
# Launch discipline copied verbatim from run_framedense.sh (dr-mario-mesen-launch-verification):
# headless -testrunner, per-arm TMPDIR/XDG/output dir, log deleted then required to reappear
# carrying THIS arm's tag, exact-pid reap, no name-pattern kills.
set -euo pipefail

D=/home/struktured/projects/dr-mario-rotexec-wt
SRC=/home/struktured/projects/dr-mario-pockettuck-wt
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
MESEN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
RUN_MESEN=/home/struktured/projects/dr-mario-mods/run_mesen.sh
SANDBOX=/home/struktured/projects/dr-mario-te/v8-source/tools/gate/mesen_sandbox_settings.json
# Cart under test. Defaults to the reference CvC tuck cart; RW_CART/RW_CARTMD5 select an arm.
# The md5 is ALWAYS checked -- an arm that silently ran the wrong cart is the whole hazard
# ([[dr-mario-watchdog-mgl-silent-cart-fallback]]: filename is not provenance).
CART="${RW_CART:-$SRC/roms/drmario_tuck_cvc_mister.nes}"
CART_MD5="${RW_CARTMD5:-9fefaedba9a27ba10f058ac239eeb77d}"
W=0x5200

orient="${1:?orient 0..3}"; maxf="${2:?frames}"; seed="${RW_SEED:-114}"
tag="rw_${RW_ARMTAG:-ref}_o${orient}_${maxf}_s${seed}"

got=$(md5sum "$CART" | cut -d' ' -f1)
[[ "$got" == "$CART_MD5" ]] || { echo "CART MD5 MISMATCH: $got != $CART_MD5" >&2; exit 2; }
[[ -x "$MESEN" ]] || { echo "missing Mesen: $MESEN" >&2; exit 2; }

# SEAT CHECK on the process NAME, not on `ps -eo args`. Matching the args string
# 'Release/Mesen' self-matched the calling shell -- whose own command line carries that path
# from this very check -- and refused 22 of 24 cells of a paired ladder while reporting
# nothing ([[harness-pgrep-self-match]], second sighting). `pgrep -x` matches comm only.
# ZOMBIES DO NOT COUNT. A previous arm's Mesen can sit <defunct> for a while when the shell
# that spawned it was abandoned; `pgrep` reports it, `ps -o args=` shows nothing, and the arm
# refuses against a process that is already dead. Filter on run state, and WAIT for a live
# one rather than refusing instantly -- this batch is sequential, so a live Mesen means the
# previous cell has not finished teardown yet, not that someone else is using the box.
live_mesen() {
  local p s out=""
  for p in $(pgrep -x Mesen 2>/dev/null); do
    s=$(ps -o state= -p "$p" 2>/dev/null | tr -d ' ')
    case "$s" in ""|Z*) ;; *) out="$out $p";; esac
  done
  printf '%s' "$out"
}
for _ in $(seq 1 900); do
  [ -z "$(live_mesen)" ] && break
  sleep 2
done
if [ -n "$(live_mesen)" ]; then
  echo "a Mesen is still alive after 30 min (pids:$(live_mesen)) -- refusing to run two arms concurrently" >&2
  exit 3
fi

out="$D/tmp/rotwedge/$tag"; mkdir -p "$out"
runtime_tmp="$out/runtime-tmp"; rm -rf -- "$runtime_tmp"
config_dir="$runtime_tmp/xdg/Mesen2"; mkdir -p "$config_dir"
cp "$SANDBOX" "$config_dir/settings.json"

mmc1="$out/${tag}_mmc1.nes"; log="$out/rotwedge.log"
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
    export RW_OUT="$out" RW_TAG="$tag" RW_W="$W" RW_ORIENT="$orient" RW_MAXF="$maxf" \
           RW_SEED="$seed" RW_DLAT="${RW_DLAT:-34}" RW_STALLN="${RW_STALLN:-300}"
    exec "$RUN_MESEN" "$mmc1" "$D/tools/gate/probe_rotwedge.lua" -testrunner "-timeout=$deadline"
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
