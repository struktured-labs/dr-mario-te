#!/bin/bash
# sileval_watchdog.sh — 2h preventive core-reload + seed-jitter loop for the NEW
# MiSTer's unattended soaks (hardened-cart shakedown). Clone of the live box's
# preventive_reload_theta400.sh, with three deliberate differences:
#   1. EXPLICIT IP from sileval.env — never mister_ip.sh discovery (both boxes
#      share the default MAC; discovery could grab the LIVE soak box).
#   2. Its OWN log (never the live soak's preventive_reload.log).
#   3. MGL + template + slot are parameters, so the same script soaks any
#      staged cart on the new box.
#
# Usage (as a systemd user unit so it survives terminal death AND is not
# nohup'd — nohup defeats the harness re-invoke):
#   systemd-run --user --unit drm-sileval-watchdog \
#     env SILEVAL_WD_MGL=/media/fat/sileval_ship.mgl \
#         SILEVAL_WD_TEMPLATE="$TEMPLATE_SHIP" \
#     "$HOME/projects/dr-mario-sileval-wt/experiments/sileval/sileval_watchdog.sh"
# Status: systemctl --user status drm-sileval-watchdog
# Stop:   systemctl --user stop drm-sileval-watchdog
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SILEVAL_ENV:-$HERE/sileval.env}"
. "$ENV_FILE"
MGL="${SILEVAL_WD_MGL:?set SILEVAL_WD_MGL (mgl path on the new box)}"
TEMPLATE="${SILEVAL_WD_TEMPLATE:?set SILEVAL_WD_TEMPLATE (local pre-generation .ss)}"
LOG="${SILEVAL_WD_LOG:-$HERE/out/sileval_watchdog.log}"
PERIOD="${SILEVAL_WD_PERIOD:-7200}"
mkdir -p "$(dirname "$LOG")"

case "$NEWMISTER_IP" in ""|FILL_ME_IN) echo "NEWMISTER_IP unset" >&2; exit 2;; esac
[ "$NEWMISTER_IP" = "$LIVE_MISTER_IP" ] && { echo "refusing: IP is the LIVE box" >&2; exit 2; }
ARMED="${SILEVAL_ARMED:-$HERE/out/ARMED}"
[ -f "$ARMED" ] || { echo "not armed: touch $ARMED first" >&2; exit 2; }
ssh -o ConnectTimeout=10 -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP" "test -f /media/fat/SILEVAL_BOX_ID" \
  || { echo "SILEVAL_BOX_ID sentinel absent — refusing" >&2; exit 2; }

CARTB=$(basename "$MGL" .mgl)   # slot file keys on the CART basename, resolved per cycle below
while true; do
  SEED=$(( ( $(od -An -N2 -tu2 </dev/urandom) % 65535 ) + 1 ))
  {
    # hash the cart the MGL will boot, every cycle (watchdog-fallback lesson)
    CART=$(ssh -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP" "command grep -o 'path=\"[^\"]*\"' '$MGL'" | head -1 | sed 's/path=\"//;s/\"//')
    CART_PATH="/media/fat/games/NES/$CART"
    CART_MD5=$(ssh -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP" "md5sum '$CART_PATH'" | cut -d' ' -f1)
    SLOT="/media/fat/savestates/NES/$(basename "$CART" .nes)_1.ss"
    PATCHED=$(mktemp "${TMPDIR:-/tmp}/silevalwd.XXXXXX.ss"); trap 'rm -f "$PATCHED"' EXIT
    python3 "$HERE/vendor/seedjit_ss.py" seed "$TEMPLATE" "$PATCHED" "$SEED" >/dev/null &&
    scp -q -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "$PATCHED" "root@$NEWMISTER_IP:$SLOT" &&
    ssh -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP" "echo load_core /media/fat/menu.rbf > /dev/MiSTer_cmd" && sleep 10 &&
    ssh -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP" "echo load_core $MGL > /dev/MiSTer_cmd" && sleep 15 &&
    ssh -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP" "test -p /tmp/sileval_input.fifo && echo 'combo f1' > /tmp/sileval_input.fifo" &&
    printf '%s sileval-wd seed=%s cart_md5=%s template_md5=%s mgl=%s ip=%s\n' \
      "$(date -Is)" "$SEED" "$CART_MD5" "$(md5sum "$TEMPLATE" | cut -d' ' -f1)" "$MGL" "$NEWMISTER_IP" \
    || echo "$(date -Is) sileval-wd CYCLE FAILED seed=$SEED"
    rm -f "$PATCHED"
  } >>"$LOG" 2>&1
  sleep "$PERIOD"
done
