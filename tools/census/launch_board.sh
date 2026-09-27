#!/bin/bash
# launch_census.sh <outdir> <maxframes> [rlat] [dlat] [shots] [seed] [display] [timeout_s]
# Runs the v4 pocket-human cart (MMC1 remap) in Mesen under Xvfb with census_run.lua.
# Mesen2 is SINGLE-INSTANCE: a second launch forwards args into the running instance.
# => wait for (then kill) any lingering Mesen before launching. Serial use only.
set -u
CEN=/mnt/data/drmario/pocket-copro/mesen_copro_qa/census
OUTDIR="${1:?outdir}"; MAXF="${2:?maxframes}"
RLAT="${3:-2}"; DLAT="${4:-12}"; SHOTS="${5:-0}"; SEED="${6:-1}"
DISP="${7:-:158}"; TMO="${8:-600}"
MESEN_BIN=/home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release/Mesen
mkdir -p "$OUTDIR"

# --- claim the Mesen seat: reap any lingering instance (ours; census runs serially) ---
for _ in $(seq 1 30); do
  PIDS=$(pgrep -f "^${MESEN_BIN}" || true)
  [ -z "$PIDS" ] && break
  kill $PIDS 2>/dev/null
  sleep 2
done

# --- Xvfb: reuse a live server on $DISP, else clear stale lock and start one ---
DNUM="${DISP#:}"
STARTED_XVFB=0
XPID=""
if [ -e "/tmp/.X${DNUM}-lock" ] || [ -e "/tmp/.X11-unix/X${DNUM}" ]; then
  LPID=$(command cat "/tmp/.X${DNUM}-lock" 2>/dev/null | tr -d ' ')
  if [ -n "${LPID:-}" ] && kill -0 "$LPID" 2>/dev/null; then
    : # live server; reuse
  else
    rm -f "/tmp/.X${DNUM}-lock" "/tmp/.X11-unix/X${DNUM}"
  fi
fi
if [ ! -e "/tmp/.X11-unix/X${DNUM}" ]; then
  Xvfb "$DISP" -screen 0 1280x720x24 -ac -nolisten tcp &
  XPID=$!
  STARTED_XVFB=1
  sleep 2
fi

cd /home/struktured/projects/dr-mario-mods/mesen2/bin/linux-x64/Release
DISPLAY="$DISP" CEN_OUT="$OUTDIR" CEN_MAXF="$MAXF" CEN_RLAT="$RLAT" CEN_DLAT="$DLAT" \
CEN_SHOTS="$SHOTS" CEN_SEED="$SEED" \
timeout -k 10 "$TMO" /home/struktured/projects/dr-mario-mods/run_mesen.sh \
  "$CEN/v4_mmc1.nes" "$CEN/census_run_board.lua" > "$OUTDIR/mesen_stdout.log" 2>&1
RC=$?
[ "$STARTED_XVFB" = 1 ] && [ -n "$XPID" ] && kill "$XPID" 2>/dev/null
echo "launch_census done rc=$RC out=$OUTDIR"
