#!/bin/bash
# sileval_ab.sh — DRP1SLICE silicon A/B driver (prereg: PREREG_SLICE_SILICON.md).
#
# Paired-seed, ABBA-blocked, resumable. One JSONL row per (seed, arm), written
# atomically; all per-row artifacts (save-state samples + screenshots) kept so
# scoring is a pure offline pass (score_rows.py).
#
# NEVER discovers the box. NEWMISTER_IP comes from sileval.env, and the driver
# hard-stops if it equals LIVE_MISTER_IP or if the /media/fat/SILEVAL_BOX_ID
# sentinel is missing (both MiSTers share the default MAC — discovery is unsafe).
#
# Run under systemd so it survives terminal death and is stoppable:
#   systemd-run --user --unit drm-sileval-ab \
#     "$HOME/projects/dr-mario-sileval-wt/experiments/sileval/sileval_ab.sh"
# Graceful stop: touch "$OUT_DIR/HALT" (finishes the in-flight arm, then exits).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SILEVAL_ENV:-$HERE/sileval.env}"
[ -f "$ENV_FILE" ] || { echo "FATAL: $ENV_FILE missing (copy sileval.env.example)"; exit 2; }
# shellcheck disable=SC1090
. "$ENV_FILE"

SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
fatal() { echo "$(date -Is) FATAL: $*" >&2; exit 2; }
note()  { echo "$(date -Is) $*"; }

# ---- registration + identity gates (every start, cheap) ----------------------
case "$NEWMISTER_IP" in ""|FILL_ME_IN) fatal "NEWMISTER_IP not set in $ENV_FILE";; esac
[ "$NEWMISTER_IP" = "$LIVE_MISTER_IP" ] && fatal "NEWMISTER_IP equals the LIVE soak box — refused"
[ -n "$TEMPLATE_SHIP" ] && [ -n "$TEMPLATE_SLICE" ] || fatal "templates not pinned (runbook step 6)"
for t in SHIP SLICE; do
  eval f=\$TEMPLATE_$t; eval want=\$TEMPLATE_${t}_MD5
  [ -f "$f" ] || fatal "template $f missing"
  got=$(md5sum "$f" | cut -d' ' -f1)
  [ "$got" = "$want" ] || fatal "template $t md5 $got != pinned $want (different template = different experiment)"
done
$SSH "root@$NEWMISTER_IP" "test -f /media/fat/SILEVAL_BOX_ID" \
  || fatal "SILEVAL_BOX_ID sentinel absent on $NEWMISTER_IP — is this really the NEW box?"
BOX_ID=$($SSH "root@$NEWMISTER_IP" "cat /media/fat/SILEVAL_BOX_ID")

mkdir -p "$OUT_DIR/rows" "$OUT_DIR/artifacts"

arm_cart_md5()  { case "$1" in ship) echo "$CART_SHIP_MD5";;  slice) echo "$CART_SLICE_MD5";;  esac; }
arm_sd_cart()   { case "$1" in ship) echo "$SD_CART_SHIP";;   slice) echo "$SD_CART_SLICE";;   esac; }
arm_mgl()       { case "$1" in ship) echo "$SD_MGL_SHIP";;    slice) echo "$SD_MGL_SLICE";;    esac; }
arm_template()  { case "$1" in ship) echo "$TEMPLATE_SHIP";;  slice) echo "$TEMPLATE_SLICE";;  esac; }
arm_slot()      { b=$(basename "$(arm_sd_cart "$1")" .nes); echo "/media/fat/savestates/NES/${b}_1.ss"; }
arm_saveslot2() { b=$(basename "$(arm_sd_cart "$1")" .nes); echo "/media/fat/savestates/NES/${b}_2.ss"; }

# Save-state pull with the save/scp race guard: poll remote size+mtime until the
# file stops growing AND mtime moved past the pre-save stamp; 0-byte pulls are VOID.
pull_state() { # $1 remote path, $2 local path, $3 pre-save mtime
  local r=$1 l=$2 pre=$3 s1 s2 m
  for _ in $(seq 1 12); do
    read -r s1 m <<<"$($SSH "root@$NEWMISTER_IP" "stat -c '%s %Y' '$r' 2>/dev/null" || echo "0 0")"
    [ "$m" != "$pre" ] && [ "$s1" -gt 0 ] || { sleep 1; continue; }
    sleep 1
    s2=$($SSH "root@$NEWMISTER_IP" "stat -c '%s' '$r' 2>/dev/null" || echo 0)
    [ "$s1" = "$s2" ] && { scp -q "root@$NEWMISTER_IP:$r" "$l" && return 0; }
  done
  return 1
}

run_arm() { # $1 seed, $2 arm  -> writes rows/<seed>_<arm>.json
  local seed=$1 arm=$2
  local row="$OUT_DIR/rows/${seed}_${arm}.json"
  [ -f "$row" ] && command grep -q '"status": *"OK"' "$row" && { note "skip $seed/$arm (done)"; return 0; }
  local adir="$OUT_DIR/artifacts/${seed}_${arm}"; mkdir -p "$adir"
  local sd_cart mgl slot save2 tmpl cart_want
  sd_cart=$(arm_sd_cart "$arm"); mgl=$(arm_mgl "$arm"); slot=$(arm_slot "$arm")
  save2=$(arm_saveslot2 "$arm"); tmpl=$(arm_template "$arm"); cart_want=$(arm_cart_md5 "$arm")

  # provenance: hash the cart that is ABOUT TO BOOT + the core the MGL names
  local cart_md5 rbf_md5
  cart_md5=$($SSH "root@$NEWMISTER_IP" "md5sum '$sd_cart'" | cut -d' ' -f1) || cart_md5=SSH_FAIL
  rbf_md5=$($SSH "root@$NEWMISTER_IP" "md5sum '$SD_RBF'" | cut -d' ' -f1) || rbf_md5=SSH_FAIL
  [ "$cart_md5" = "$cart_want" ] || { void_row "$row" "$seed" "$arm" "cart_hash_mismatch got=$cart_md5 want=$cart_want"; fatal "cart hash mismatch on SD — run halted (prereg VOID 1)"; }
  [ "$rbf_md5" = "$RBF_MD5" ]   || { void_row "$row" "$seed" "$arm" "rbf_hash_mismatch got=$rbf_md5";  fatal "rbf hash mismatch on SD — run halted"; }

  # inject seed into THIS arm's template, push, boot, restore
  local patched="$adir/patched.ss"
  python3 "$HERE/vendor/seedjit_ss.py" seed "$tmpl" "$patched" "$seed" >/dev/null \
    || { void_row "$row" "$seed" "$arm" "seedjit_patch_failed"; return 1; }
  scp -q "$patched" "root@$NEWMISTER_IP:$slot" || { void_row "$row" "$seed" "$arm" "scp_slot_failed"; return 1; }
  $SSH "root@$NEWMISTER_IP" "echo load_core /media/fat/menu.rbf > /dev/MiSTer_cmd" || { void_row "$row" "$seed" "$arm" "menu_load_failed"; return 1; }
  sleep 10
  $SSH "root@$NEWMISTER_IP" "echo load_core $mgl > /dev/MiSTer_cmd" || { void_row "$row" "$seed" "$arm" "mgl_load_failed"; return 1; }
  sleep 15
  misterclaw-send --host "$NEWMISTER_IP" --timeout 30 input combo f1 >/dev/null 2>&1 \
    || { void_row "$row" "$seed" "$arm" "f1_restore_failed"; return 1; }
  local corename t0 n=0 shot_fail=0 pull_fail=0
  corename=$($SSH "root@$NEWMISTER_IP" "cat /tmp/CORENAME 2>/dev/null" || echo "?")
  t0=$(date +%s)

  # sample loop
  local wedge_suspect=0 h1="" h2="" h3=""
  while :; do
    local now=$(date +%s); local el=$(( now - t0 ))
    [ "$el" -ge "$CYCLE_SECS" ] && break
    local tgt=$(( t0 + (n+1)*SAMPLE_SECS )); local w=$(( tgt - now )); [ "$w" -gt 0 ] && sleep "$w"
    n=$(( n + 1 ))
    local pre; pre=$($SSH "root@$NEWMISTER_IP" "stat -c '%Y' '$save2' 2>/dev/null" || echo 0)
    misterclaw-send --host "$NEWMISTER_IP" --timeout 30 input combo leftalt f2 >/dev/null 2>&1
    pull_state "$save2" "$adir/s$(printf %03d "$n").ss" "$pre" || pull_fail=$(( pull_fail + 1 ))
    misterclaw-send --host "$NEWMISTER_IP" --timeout 30 screenshot \
      --output "$adir/s$(printf %03d "$n").png" >/dev/null 2>&1 || shot_fail=$(( shot_fail + 1 ))
    # motion check on the last 3 screenshots (wedge SUSPECT only — adjudication
    # is by the prereg's screenshot-timeout/no-motion rule, offline)
    if [ -f "$adir/s$(printf %03d "$n").png" ]; then
      h3=$h2; h2=$h1; h1=$(md5sum "$adir/s$(printf %03d "$n").png" | cut -d' ' -f1)
      [ -n "$h3" ] && [ "$h1" = "$h2" ] && [ "$h2" = "$h3" ] && wedge_suspect=1
    fi
  done

  # atomic row
  local tmp="$row.tmp"
  cat > "$tmp" <<JSON
{"ts": "$(date -Is)", "seed": $seed, "arm": "$arm", "status": "OK",
 "box_id": "$BOX_ID", "ip": "$NEWMISTER_IP", "corename": "$corename",
 "cart_md5": "$cart_md5", "rbf_md5": "$rbf_md5",
 "template_md5": "$(md5sum "$tmpl" | cut -d' ' -f1)",
 "patched_md5": "$(md5sum "$patched" | cut -d' ' -f1)",
 "cycle_secs": $CYCLE_SECS, "samples": $n,
 "pull_fail": $pull_fail, "shot_fail": $shot_fail,
 "wedge_suspect": $wedge_suspect}
JSON
  mv "$tmp" "$row"
  note "row OK seed=$seed arm=$arm samples=$n pull_fail=$pull_fail shot_fail=$shot_fail wedge_suspect=$wedge_suspect"
}

void_row() { # $1 row, $2 seed, $3 arm, $4 reason
  local tmp="$1.tmp"
  printf '{"ts": "%s", "seed": %s, "arm": "%s", "status": "VOID", "reason": "%s"}\n' \
    "$(date -Is)" "$2" "$3" "$4" > "$tmp" && mv "$tmp" "$1"
  note "row VOID seed=$2 arm=$3 reason=$4"
}

# ---- main: ABBA over the registered seed list --------------------------------
i=0
while read -r seed; do
  [ -f "$OUT_DIR/HALT" ] && { note "HALT file present — stopping"; exit 0; }
  case $(( i % 2 )) in
    0) run_arm "$seed" ship;  run_arm "$seed" slice ;;
    1) run_arm "$seed" slice; run_arm "$seed" ship  ;;
  esac
  i=$(( i + 1 ))
done < "$SEEDS_FILE"
note "seed list complete"
