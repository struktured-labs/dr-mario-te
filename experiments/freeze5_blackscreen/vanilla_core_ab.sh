#!/bin/bash
# vanilla_core_ab.sh -- the vanilla-core discriminator, freeze #5 (black-screen core wedge).
#
# QUESTION THIS ANSWERS: is the wedge specific to our RTL/cart family (copro, mapper 100, the
# CvC probe driver), or is it a MiSTer framework/firmware-level bug that just happens to be
# what our cores exercise hardest? Load a STOCK NES core with an ORDINARY, unrelated NES ROM
# under identical wedge_probe.sh observation for up to 30 minutes (or 3 triggers, whichever
# comes first):
#   - SURVIVES (no trigger)  -> fault is in OUR RTL/cart family. Keep digging there.
#   - WEDGES too             -> framework/firmware-level, independent of our work. Pin a
#                                known-good MiSTer framework build for the Sept-12 booth and
#                                escalate the firmware question separately.
#
# Context (2026-08-05): the two cores tested so far (s20b and the pre-strand20 shipped
# champion, 71d2de37) BOTH wedge under continuous CvC play at roughly the same rate --
# s20b/CMD-8 traffic is exonerated, the wedge is at minimum common to both cart builds. This
# is the next split: does it need OUR cart family at all, or does any actively-running core
# do it? See WEDGE_PROBE.md for the full investigation history.
#
# USAGE: bash vanilla_core_ab.sh
#   Optional env overrides:
#     MISTER_IP     -- skip IP resolution, use this host directly
#     TIMEOUT_MIN    -- minutes to observe (default 30)
#     MAX_EVENTS     -- stop early after this many trigger events (default 3)
#
# One command, self-contained: resolves the device, deploys the control .mgl, loads it,
# watches wedge_probe_recovery.log (already running on-device via the boot hook -- this
# script does NOT touch wedge_probe.sh itself) for new AUTO_REBOOT/ALERT_ONLY/WEDGE_CONFIRMED
# lines timestamped after the load, and prints a verdict. Does NOT restore the previous core
# on exit -- the last section of output says how, deliberately left as a manual step so this
# script never fights whatever the human/team wants running next.

set -u

MISTER_IP_TOOL="$HOME/projects/dr-mario-qa-wt/tools/mister_ip.sh"
MISTER_IP="${MISTER_IP:-}"
TIMEOUT_MIN="${TIMEOUT_MIN:-30}"
MAX_EVENTS="${MAX_EVENTS:-3}"

# Stock core + stock ROM, both already present on the SD card (confirmed 2026-08-05, not
# introduced by this script): NES_20240408.rbf is the plain official MiSTer NES core (distinct
# from every NES_stomper*/NES_tuckmb* custom build); Battletoads has nothing to do with Dr.
# Mario, no custom mapper, and is a real, substantial game so the core is genuinely ticking
# (CPU/PPU/APU all active every frame), not sitting on a static unanimated screen.
VANILLA_RBF="_Console/NES_20240408"
VANILLA_ROM="Battletoads (U) [p1].nes"
VANILLA_MGL_NAME="AB_vanilla_control.mgl"
VANILLA_MGL_REMOTE="/media/fat/${VANILLA_MGL_NAME}"

RECOVERY_LOG=/media/fat/wedge_probe_recovery.log

if [ -z "$MISTER_IP" ]; then
  if [ -x "$MISTER_IP_TOOL" ]; then
    MISTER_IP=$("$MISTER_IP_TOOL")
  else
    echo "ERROR: MISTER_IP not set and $MISTER_IP_TOOL not found/executable." >&2
    echo "Set MISTER_IP=<host> explicitly, or fix the tool path, and re-run." >&2
    exit 1
  fi
fi
echo "Resolved MiSTer: $MISTER_IP"

ssh_mister() { timeout 15 ssh "root@${MISTER_IP}" "$@"; }

# Sanity: confirm the stock core + ROM are actually where we expect before deploying anything
# that references them, rather than discovering a typo'd path after the 30-minute wait starts.
if ! ssh_mister "[ -f /media/fat/${VANILLA_RBF}.rbf ]"; then
  echo "ERROR: ${VANILLA_RBF}.rbf not found on the device. Re-check the core filename." >&2
  exit 1
fi
if ! ssh_mister "[ -f \"/media/fat/games/NES/${VANILLA_ROM}\" ]"; then
  echo "ERROR: games/NES/${VANILLA_ROM} not found on the device. Re-check the ROM filename." >&2
  exit 1
fi

# Confirm the probe is actually running before we start a 30-min unattended measurement --
# a silent gap here would produce a false "vanilla survives" reading.
if ! ssh_mister "ps aux 2>/dev/null | command grep -q '[w]edge_probe.sh'"; then
  echo "ERROR: wedge_probe.sh is not running on the device. This measurement needs it (it's" >&2
  echo "the only thing watching for the wedge signature). Start it before running this." >&2
  exit 1
fi

echo "Deploying control mgl: rbf=${VANILLA_RBF} rom=${VANILLA_ROM}"
TMP_MGL=$(mktemp)
cat > "$TMP_MGL" <<EOF
<mistergamedescription>
	<rbf>${VANILLA_RBF}</rbf>
	<file delay="2" type="f" index="0" path="${VANILLA_ROM}"/>
</mistergamedescription>
EOF
scp -q "$TMP_MGL" "root@${MISTER_IP}:${VANILLA_MGL_REMOTE}"
SCP_STATUS=$?
rm -f "$TMP_MGL"
if [ "$SCP_STATUS" -ne 0 ]; then
  echo "ERROR: scp of the control mgl failed (status $SCP_STATUS)." >&2
  exit 1
fi

echo "Loading control core via /dev/MiSTer_cmd ..."
ssh_mister "echo load_core ${VANILLA_MGL_REMOTE} > /dev/MiSTer_cmd"
T0=$(ssh_mister "date -u +%Y-%m-%dT%H:%M:%SZ")
echo "Loaded at ${T0}. Observing for up to ${TIMEOUT_MIN} min or ${MAX_EVENTS} trigger events."

DEADLINE=$(( $(date -u +%s) + TIMEOUT_MIN * 60 ))
EVENTS=()
while [ "$(date -u +%s)" -lt "$DEADLINE" ]; do
  # Only lines strictly after T0 count -- anything from a PRIOR arm must not leak into this one.
  NEW=$(ssh_mister "command grep -E 'ALERT_ONLY wedge_signature_seen|AUTO_REBOOT triggered|WEDGE_CONFIRMED' ${RECOVERY_LOG} 2>/dev/null | awk -v t0=\"$T0\" '\$1 > t0'" 2>/dev/null)
  if [ -n "$NEW" ]; then
    while IFS= read -r line; do
      already=0
      for e in "${EVENTS[@]:-}"; do [ "$e" = "$line" ] && already=1 && break; done
      if [ "$already" -eq 0 ]; then
        EVENTS+=("$line")
        echo "TRIGGER $(( ${#EVENTS[@]} )): $line"
      fi
    done <<< "$NEW"
  fi
  if [ "${#EVENTS[@]}" -ge "$MAX_EVENTS" ]; then
    echo "Reached MAX_EVENTS=${MAX_EVENTS}, stopping early."
    break
  fi
  sleep 30
done

echo ""
echo "=== VERDICT ==="
echo "Control core: ${VANILLA_RBF} + ${VANILLA_ROM}"
echo "Loaded: ${T0}"
echo "Observed: ${TIMEOUT_MIN} min window (or early-stop at ${MAX_EVENTS} events)"
echo "Trigger events: ${#EVENTS[@]}"
if [ "${#EVENTS[@]}" -eq 0 ]; then
  echo "SURVIVED -- no trigger in the observation window. Points at OUR RTL/cart family"
  echo "(copro, mapper 100, or the CvC probe driver) as the fault, not the framework itself."
else
  echo "WEDGED -- the stock core + stock ROM combination also hit the trigger condition."
  echo "Points at a framework/firmware-level bug independent of our cart family. Recommend"
  echo "pinning a known-good MiSTer framework build for the booth and escalating separately."
fi
echo ""
echo "This script did not restore the previous core. To go back to the duel probe:"
echo "  ssh root@${MISTER_IP} 'echo load_core /media/fat/combo_stomper_s20b_probe.mgl > /dev/MiSTer_cmd'"
