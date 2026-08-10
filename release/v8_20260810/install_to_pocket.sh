#!/usr/bin/env bash
# Copy the gated v8 rematch cart onto the Analogue Pocket SD card.
#
# Safe by construction: it only ever ADDS a file. It never deletes or overwrites
# anything already on the card, and it refuses to run if the card is not mounted.
# Run it once the SD card is back in the reader.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CART="$HERE/v8 REMATCH (hardened).nes"
WANT_MD5="087ff959ac510c613bbbd2eb1ac5ecf3"

echo "== verifying the artifact before touching the card =="
have="$(md5sum "$CART" | cut -d' ' -f1)"
if [ "$have" != "$WANT_MD5" ]; then
  echo "ABORT: cart md5 is $have, expected $WANT_MD5" >&2
  exit 1
fi
echo "ok: $WANT_MD5"

echo "== locating the Pocket SD card =="
MNT="$(lsblk -o LABEL,MOUNTPOINT -nr | awk '$1=="POCKET-SD" && $2!="" {print $2; exit}')"
if [ -z "${MNT:-}" ]; then
  echo "ABORT: no mounted volume labelled POCKET-SD." >&2
  echo "       Insert the card, let it mount, then re-run this script." >&2
  exit 1
fi
echo "card at: $MNT"

DEST="$MNT/Assets/nes/common"
if [ ! -d "$DEST" ]; then
  echo "ABORT: $DEST does not exist — is this the right card?" >&2
  exit 1
fi

TARGET="$DEST/v8 REMATCH (hardened).nes"
if [ -e "$TARGET" ]; then
  echo "A file of that name is already on the card:"
  ls -la "$TARGET"
  echo "Refusing to overwrite. Remove or rename it first if you want a fresh copy."
  exit 1
fi

echo "== copying =="
cp "$CART" "$TARGET"
sync
echo "== verifying the copy ON THE CARD =="
oncard="$(md5sum "$TARGET" | cut -d' ' -f1)"
if [ "$oncard" != "$WANT_MD5" ]; then
  echo "ABORT: copy on card reads $oncard — the write did not land cleanly." >&2
  exit 1
fi

echo
echo "DONE. On the card and verified: $TARGET"
echo "md5 $oncard"
echo
echo "Note: v4 and every other cart already on the card are untouched."
