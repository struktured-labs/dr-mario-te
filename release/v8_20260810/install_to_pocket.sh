#!/usr/bin/env bash
# Copy the gated v8 rematch cart onto the Analogue Pocket SD card.
#
# Safe by construction: it only ever ADDS a file, never deletes or overwrites, and refuses to
# run if the card is not mounted.
#
# The copy is staged through a ".part" file and only moved into place AFTER its md5 is verified
# on the card. A failed or truncated write therefore leaves no file at the real name — it leaves
# a self-evidently incomplete ".part". This matters: an earlier version copied directly to the
# final name, and `set -e` aborted before the verify could run, so a truncated cart could be left
# on the card undetected — and the refuse-to-overwrite guard then reported it as "already
# installed" on the next run, concealing the damage.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CART="$HERE/v8 REMATCH (hardened).nes"
WANT_MD5="c0082cb34259007854120d3d4ab9fa27"

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
PART="$TARGET.part"

if [ -e "$TARGET" ]; then
  echo "A file of that name is already on the card:"
  ls -la "$TARGET"
  echo "Its md5: $(md5sum "$TARGET" | cut -d' ' -f1)   (expected $WANT_MD5)"
  echo "Refusing to overwrite. Remove or rename it first if you want a fresh copy."
  exit 1
fi
if [ -e "$PART" ]; then
  echo "ABORT: a leftover $PART exists — a previous copy did not complete." >&2
  echo "       Delete it and re-run." >&2
  exit 1
fi

# Any failure from here leaves only the .part, never a file at the real name.
cleanup() { rm -f "$PART" 2>/dev/null || true; }
trap cleanup EXIT

echo "== copying (staged) =="
cp "$CART" "$PART"
sync

echo "== verifying the staged copy ON THE CARD =="
oncard="$(md5sum "$PART" | cut -d' ' -f1)"
if [ "$oncard" != "$WANT_MD5" ]; then
  echo "ABORT: staged copy reads $oncard, expected $WANT_MD5 — the write did not land cleanly." >&2
  echo "       Nothing was installed; the incomplete file is being removed." >&2
  exit 1
fi

mv "$PART" "$TARGET"
sync
trap - EXIT

final="$(md5sum "$TARGET" | cut -d' ' -f1)"
if [ "$final" != "$WANT_MD5" ]; then
  echo "ABORT: after move, $TARGET reads $final. Remove it before playing." >&2
  exit 1
fi

echo
echo "DONE. On the card and verified: $TARGET"
echo "md5 $final"
echo
echo "Note: v4 and every other cart already on the card are untouched."
