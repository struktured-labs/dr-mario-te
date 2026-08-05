#!/bin/bash
# copro_noncvc_ab.sh -- the CvC-vs-human-cart isolation split, freeze #5 (black-screen core
# wedge). Adapted from vanilla_core_ab.sh; same structure, different core+cart, and a real
# screenshot-TIMEOUT ground-truth check added instead of trusting ALERT_ONLY/frame content
# (see WEDGE_PROBE.md "CORRECTION" section -- a screenshot response, of ANY content, means the
# display path is alive; only a TIMEOUT proves a wedge. The probe's consec/busy_frac heuristic
# fires on healthy play too and is NOT ground truth on its own).
#
# QUESTION THIS ANSWERS: both copro cores (s20b, pre-strand20) wedge under continuous CvC
# (computer-vs-computer, both sides driven by the copro's autonav/driver loop); a stock NES
# core does not. That means the fault is in our core family, not the framework -- but that
# still leaves two suspects: the copro/mapper-100 RTL itself, or the CvC driver's own busy
# pattern (autonav placing pills back-to-back with no human-paced gaps). This test removes the
# CvC driver loop while keeping our RTL: same s20b bitstream, but a HUMAN-play cart (no
# autonav, no back-to-back driver activity) instead of the CvC probe cart.
#   - SURVIVES (no timeout in the window) -> the CvC driver's busy pattern is the trigger.
#     Fixable in the driver (pacing / DRSTALLWD-style gating). Booth is safe since humans
#     don't run autonav.
#   - WEDGES (a timeout occurs)          -> the copro RTL itself is the trigger
#     (mapper-100/HPS-bridge interaction). RTL work, and the booth risk stands.
#
# USAGE: bash copro_noncvc_ab.sh
#   Optional env overrides:
#     MISTER_IP        -- skip IP resolution, use this host directly
#     TIMEOUT_MIN       -- minutes to observe (default 30)
#     CHECK_INTERVAL_S  -- seconds between screenshot ground-truth checks (default 120, ~2min)
#     SHOT_TIMEOUT_S    -- seconds before a screenshot attempt counts as a WEDGE (default 10)

set -u

MISTER_IP_TOOL="$HOME/projects/dr-mario-qa-wt/tools/mister_ip.sh"
MISTER_IP="${MISTER_IP:-}"
TIMEOUT_MIN="${TIMEOUT_MIN:-30}"
CHECK_INTERVAL_S="${CHECK_INTERVAL_S:-120}"
SHOT_TIMEOUT_S="${SHOT_TIMEOUT_S:-10}"

# Same s20b bitstream as one of the two confirmed-wedging arms, paired with a human-play cart
# instead of the CvC probe cart -- "drmario_HUMAN_latchfix.nes", team-lead's "human latchfix
# cart", already on the SD card (dated 2026-07-28), not previously paired with s20b's rbf. The
# copro cart family's ROM/RBF pairings are already established cross-compatible in this
# project (the CvC probe ROM itself runs unmodified on both the old and s20b rbfs).
COPRO_RBF="_Console/NES_stomper180s20b_20260804"
HUMAN_ROM="drmario_HUMAN_latchfix.nes"
MGL_NAME="AB_copro_human_latchfix.mgl"
MGL_REMOTE="/media/fat/${MGL_NAME}"

SCREENSHOT_DIR="/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad"
mkdir -p "$SCREENSHOT_DIR"

if [ -z "$MISTER_IP" ]; then
  if [ -x "$MISTER_IP_TOOL" ]; then
    MISTER_IP=$("$MISTER_IP_TOOL")
  else
    echo "ERROR: MISTER_IP not set and $MISTER_IP_TOOL not found/executable." >&2
    exit 1
  fi
fi
echo "Resolved MiSTer: $MISTER_IP"

ssh_mister() { timeout 15 ssh "root@${MISTER_IP}" "$@"; }

if ! ssh_mister "[ -f /media/fat/${COPRO_RBF}.rbf ]"; then
  echo "ERROR: ${COPRO_RBF}.rbf not found on the device." >&2
  exit 1
fi
if ! ssh_mister "[ -f \"/media/fat/games/NES/${HUMAN_ROM}\" ]"; then
  echo "ERROR: games/NES/${HUMAN_ROM} not found on the device." >&2
  exit 1
fi

echo "Deploying: rbf=${COPRO_RBF} rom=${HUMAN_ROM}"
TMP_MGL=$(mktemp)
cat > "$TMP_MGL" <<EOF
<mistergamedescription>
	<rbf>${COPRO_RBF}</rbf>
	<file delay="2" type="f" index="0" path="${HUMAN_ROM}"/>
</mistergamedescription>
EOF
scp -q "$TMP_MGL" "root@${MISTER_IP}:${MGL_REMOTE}"
SCP_STATUS=$?
rm -f "$TMP_MGL"
if [ "$SCP_STATUS" -ne 0 ]; then
  echo "ERROR: scp of the mgl failed (status $SCP_STATUS)." >&2
  exit 1
fi

echo "Loading via /dev/MiSTer_cmd ..."
ssh_mister "echo load_core ${MGL_REMOTE} > /dev/MiSTer_cmd"
T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
T0_EPOCH=$(date -u +%s)
echo "Loaded at ${T0}. Ground-truth check every ${CHECK_INTERVAL_S}s (screenshot TIMEOUT = wedge, any response = alive), up to ${TIMEOUT_MIN} min."

DEADLINE=$(( T0_EPOCH + TIMEOUT_MIN * 60 ))
CHECK_N=0
WEDGE_AT=""
while [ "$(date -u +%s)" -lt "$DEADLINE" ]; do
  sleep "$CHECK_INTERVAL_S"
  CHECK_N=$((CHECK_N + 1))
  NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  ELAPSED=$(( $(date -u +%s) - T0_EPOCH ))
  OUT_FILE="${SCREENSHOT_DIR}/copro_noncvc_check${CHECK_N}_$(date -u +%H%M%SZ).png"
  START_T=$(date -u +%s.%N)
  if timeout "$SHOT_TIMEOUT_S" misterclaw-send --host "$MISTER_IP" screenshot --output "$OUT_FILE" >/tmp/shotcheck_out.$$ 2>&1; then
    END_T=$(date -u +%s.%N)
    DUR=$(awk -v a="$START_T" -v b="$END_T" 'BEGIN{printf "%.2f", b-a}')
    echo "CHECK ${CHECK_N} @ ${NOW} (${ELAPSED}s after load): ALIVE (screenshot returned in ${DUR}s) -> ${OUT_FILE}"
  else
    STATUS=$?
    echo "CHECK ${CHECK_N} @ ${NOW} (${ELAPSED}s after load): WEDGE -- screenshot attempt timed out/failed (exit ${STATUS}, budget ${SHOT_TIMEOUT_S}s)"
    WEDGE_AT="${NOW} (${ELAPSED}s after load)"
    break
  fi
  rm -f /tmp/shotcheck_out.$$
done

echo ""
echo "=== VERDICT ==="
echo "Core+cart: ${COPRO_RBF} + ${HUMAN_ROM} (copro RTL, human-play cart, no CvC autonav)"
echo "Loaded: ${T0}"
echo "Checks performed: ${CHECK_N} (every ${CHECK_INTERVAL_S}s, ${SHOT_TIMEOUT_S}s timeout budget each)"
if [ -n "$WEDGE_AT" ]; then
  echo "WEDGED at ${WEDGE_AT}"
  echo "-> the copro RTL/mapper-100 itself is implicated (not just the CvC driver pattern)."
  echo "   RTL work needed; the Sept-12 booth risk stands even for human play."
else
  echo "SURVIVED the full ${TIMEOUT_MIN}-minute window with no screenshot timeout."
  echo "-> the CvC driver's busy pattern (autonav placing pills back-to-back) is implicated,"
  echo "   not the RTL itself. Fixable in the driver (pacing/DRSTALLWD-style gating)."
  echo "   Human play at the booth should be safe on this evidence."
fi
echo ""
echo "This script did not restore the previous core. To go back to the duel probe:"
echo "  ssh root@${MISTER_IP} 'echo load_core /media/fat/combo_stomper_s20b_probe.mgl > /dev/MiSTer_cmd'"
