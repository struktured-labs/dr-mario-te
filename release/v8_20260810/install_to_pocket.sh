#!/usr/bin/env bash
# Copy the gated v8 rematch cart onto the Analogue Pocket SD card.
#
# Safe by construction: it only ever ADDS a file, never deletes or overwrites, and refuses to
# run unless exactly one card is present.
#
# ⚠ THE STAGING IS THE PROTECTION, NOT THE MD5 VERIFY. The copy goes to a ".part" and is only
# renamed into place after checking. On the failure that motivated this design — a truncated
# write — `cp` dies by signal and `set -e` exits BEFORE the verify line ever runs. What keeps a
# corrupt cart off the card is that nothing was ever written at the real name, plus the EXIT
# trap. So do NOT "simplify" this by copying straight to the final name while keeping the md5
# check: that reintroduces the original bug while leaving a verify step visible in the code.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CART="$HERE/v8 REMATCH (hardened).nes"
WANT_MD5="c0082cb34259007854120d3d4ab9fa27"
CARTNAME="v8 REMATCH (hardened).nes"

echo "== verifying the artifact before touching the card =="
have="$(md5sum "$CART" | cut -d' ' -f1)"
if [ "$have" != "$WANT_MD5" ]; then
  echo "ABORT: cart md5 is $have, expected $WANT_MD5" >&2
  exit 1
fi
echo "ok: $WANT_MD5"

echo "== locating the Pocket SD card =="
# Collect ALL matches. Taking the first would silently install to a backup card if two were
# inserted, and print DONE while doing it.
mapfile -t MNTS < <(lsblk -o LABEL,MOUNTPOINT -nr | awk '$1=="POCKET-SD" && $2!="" {print $2}')
if [ "${#MNTS[@]}" -eq 0 ]; then
  echo "ABORT: no mounted volume labelled POCKET-SD." >&2
  echo "       Insert the card, let it mount, then re-run this script." >&2
  exit 1
fi
if [ "${#MNTS[@]}" -gt 1 ]; then
  echo "ABORT: ${#MNTS[@]} volumes are labelled POCKET-SD:" >&2
  printf '         %s\n' "${MNTS[@]}" >&2
  echo "       Refusing to guess which one you meant. Unmount all but the target and re-run." >&2
  exit 1
fi
MNT="${MNTS[0]}"
echo "card at: $MNT"

DEST="$MNT/Assets/nes/common"
if [ ! -d "$DEST" ]; then
  echo "ABORT: $DEST does not exist — is this the right card?" >&2
  echo "       (If the mountpoint contains spaces, lsblk -r escapes them and this is expected.)" >&2
  exit 1
fi

TARGET="$DEST/$CARTNAME"
PART="$TARGET.part"

if [ -e "$TARGET" ]; then
  oncard="$(md5sum "$TARGET" | cut -d' ' -f1)"
  if [ "$oncard" = "$WANT_MD5" ]; then
    echo
    echo "ALREADY INSTALLED AND VERIFIED: $TARGET"
    echo "md5 $oncard — nothing to do."
    exit 0
  fi
  echo "A DIFFERENT file of that name is already on the card:" >&2
  ls -la "$TARGET" >&2
  echo "  its md5: $oncard" >&2
  echo "  expected: $WANT_MD5" >&2
  echo "Refusing to overwrite. Remove or rename it first." >&2
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
sync -f "$PART" 2>/dev/null || sync || true   # flush this filesystem; never fatal

# NOTE: this reads back through the page cache, so it compares against what the kernel holds,
# not necessarily against the medium. It reliably catches a truncated or mangled write — the
# failure this design exists for — but it is NOT proof the flash itself is good.
echo "== verifying the staged copy as written =="
staged="$(md5sum "$PART" | cut -d' ' -f1)"
if [ "$staged" != "$WANT_MD5" ]; then
  echo "ABORT: staged copy reads $staged, expected $WANT_MD5 — the write did not land cleanly." >&2
  echo "       Nothing was installed; the incomplete file is being removed." >&2
  exit 1
fi

mv -n "$PART" "$TARGET"
sync -f "$TARGET" 2>/dev/null || sync || true
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
