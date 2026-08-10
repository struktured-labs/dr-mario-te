#!/bin/bash
# launch_fp.sh <outdir> <cart.nes> <tag> <maxframes> <warm> [seed] [dlat] [timeout_s]
# Mesen2 is SINGLE-INSTANCE and shared with other lanes: WAIT for a free seat, never kill.
set -u
OUTDIR="${1:?outdir}"; CART="${2:?cart}"; TAG="${3:?tag}"; MAXF="${4:?maxframes}"
WARM="${5:-0}"; SEED="${6:-114}"; DLAT="${7:-34}"; TMO="${8:-300}"
MESEN_BIN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
DISP=:167
mkdir -p "$OUTDIR"

# --- wait for the Mesen seat (up to ~5 min); do NOT kill another lane's run ---
for i in $(seq 1 150); do
  PIDS=$(pgrep -f "Release/Mesen" | command grep -av "^$$\$" || true)
  [ -z "$PIDS" ] && break
  [ "$i" = 1 ] && echo "[fp] Mesen seat busy (pids: $PIDS) -- waiting, not killing"
  sleep 2
done
PIDS=$(pgrep -f "Release/Mesen" || true)
if [ -n "$PIDS" ]; then echo "[fp] ABORT: seat still held by $PIDS"; exit 3; fi

DNUM="${DISP#:}"
if [ -e "/tmp/.X${DNUM}-lock" ] && ! kill -0 "$(command cat /tmp/.X${DNUM}-lock 2>/dev/null | tr -d ' ')" 2>/dev/null; then
  rm -f "/tmp/.X${DNUM}-lock" "/tmp/.X11-unix/X${DNUM}"
fi
STARTED=0; XPID=""
if [ ! -e "/tmp/.X11-unix/X${DNUM}" ]; then
  Xvfb "$DISP" -screen 0 1280x720x24 -ac -nolisten tcp & XPID=$!; STARTED=1; sleep 2
fi

cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
DISPLAY="$DISP" FP_OUT="$OUTDIR" FP_MAXF="$MAXF" FP_DLAT="$DLAT" FP_SEED="$SEED" \
FP_WARM="$WARM" FP_TAG="$TAG" \
timeout -k 10 "$TMO" /home/struktured/projects/dr-mario-mods/run_mesen.sh \
  "$CART" /home/struktured/projects/dr-mario-v8-wt/tools/gate/fieldplay.lua \
  > "$OUTDIR/mesen_stdout.log" 2>&1
RC=$?
[ "$STARTED" = 1 ] && [ -n "$XPID" ] && kill "$XPID" 2>/dev/null
echo "[fp] done tag=$TAG rc=$RC out=$OUTDIR"
