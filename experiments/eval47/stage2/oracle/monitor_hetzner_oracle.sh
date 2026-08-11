#!/bin/bash
# Read-only progress/status helper for the sealed Hetzner CLAIR run.
# This file is not imported by the arm and is safe to add while a run is live.
set -euo pipefail

TARGET=${1:?usage: monitor_hetzner_oracle.sh root@HOST KEYFILE [status|fetch] [LOCAL_DIR]}
KEY=${2:?usage: monitor_hetzner_oracle.sh root@HOST KEYFILE [status|fetch] [LOCAL_DIR]}
MODE=${3:-status}
HERE=$(dirname "$(readlink -f "$0")")
REMOTE_ORACLE=/home/struktured/projects/dr-mario-qa-wt/experiments/eval47/stage2/oracle
SSH=(ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=10
     -o StrictHostKeyChecking=accept-new -i "$KEY")
RSH="ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -i $KEY"

status() {
  "${SSH[@]}" "$TARGET" "REMOTE_ORACLE='$REMOTE_ORACLE' bash -s" <<'REMOTE'
set -u
echo "host=$(hostname) now=$(date -Is)"
echo "unit=$(systemctl is-active drm-oracle-clair-a 2>/dev/null || true)"
systemctl show drm-oracle-clair-a \
  -p ActiveState -p SubState -p Result -p ExecMainStatus \
  -p ActiveEnterTimestamp -p InactiveEnterTimestamp --no-pager 2>/dev/null || true
for label in true shuffle; do
  d="$REMOTE_ORACLE/out/full_A_clair_$label"
  if [[ -d "$d" ]]; then
    rows=$(find "$d" -maxdepth 1 -type f -name 'seg_*.jsonl' -exec cat {} + 2>/dev/null | wc -l)
    segments=$(find "$d" -maxdepth 1 -type f -name 'seg_*.summary.json' | wc -l)
    bytes=$(du -sb "$d" | awk '{print $1}')
    printf '%s rows=%s/9000 segments=%s/36 bytes=%s\n' "$label" "$rows" "$segments" "$bytes"
    if [[ -f "$d/META.json" ]]; then
      sha256sum "$d/META.json"
    fi
  else
    echo "$label rows=0/9000 segments=0/36 directory=absent"
  fi
done
echo "recent journal:"
journalctl -u drm-oracle-clair-a -n 20 --no-pager 2>/dev/null || true
echo "capacity:"
df -h "$REMOTE_ORACLE" | tail -1
free -h | sed -n '1,2p'
REMOTE
}

case "$MODE" in
  status)
    status
    ;;
  fetch)
    # A live snapshot is diagnostic only. Re-fetch after ALLDONE before verdict.
    LOCAL_DIR=${4:-$HERE/out/hetzner_snapshot}
    mkdir -p "$LOCAL_DIR"
    status
    for label in true shuffle; do
      mkdir -p "$LOCAL_DIR/full_A_clair_$label"
      rsync -a --partial -e "$RSH" \
        "$TARGET:$REMOTE_ORACLE/out/full_A_clair_$label/" \
        "$LOCAL_DIR/full_A_clair_$label/" 2>/dev/null || true
    done
    mkdir -p "$LOCAL_DIR/logs"
    rsync -a --partial -e "$RSH" \
      "$TARGET:$REMOTE_ORACLE/logs/" "$LOCAL_DIR/logs/"
    echo "snapshot=$LOCAL_DIR"
    echo "LIVE SNAPSHOT ONLY: re-fetch after ALLDONE; do not run a verdict on partial files"
    ;;
  *)
    echo "mode must be status or fetch" >&2
    exit 2
    ;;
esac
