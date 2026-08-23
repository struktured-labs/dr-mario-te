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

# BatchMode+IdentitiesOnly: a connection that CAN prompt is a bug (team-lead
# rule after key-wipe popups on the owner's desktop) — fail loudly instead.
# -n: ssh must NEVER read stdin — an ssh inside the seed loop slurped the
# remaining 239 seeds as its stdin on 2026-08-21 and the run "completed" after
# one pair. Belt (ssh -n) and suspenders (loop reads fd 3, below).
SSH="ssh -n -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes -o IdentitiesOnly=yes -i $HOME/.ssh/id_rsa"
fatal() { echo "$(date -Is) FATAL: $*" >&2; exit 2; }
note()  { echo "$(date -Is) $*"; }
INPUTD_CTL=/media/fat/linux/sileval_inputd_ctl.sh

# ---- authorization gate: no hardware contact without explicit arming ---------
# (added after an offline sanity run reached a live box: the driver is only ever
# started deliberately, via `touch out/ARMED` + systemd-run. A missing ARMED
# file is a refusal BEFORE any ssh/scp is attempted.)
[ -f "$OUT_DIR/ARMED" ] || fatal "not armed: touch $OUT_DIR/ARMED to authorize hardware contact"

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
# Box identity: CONTENT + MAC, never existence and never IP (AMENDMENT 1).
# Sentinel-EXISTS is no longer a discriminator — BOTH boxes now carry a
# SILEVAL_BOX_ID, so the old check would have happily run population B on the
# owner's TV box if a lease moved. The sentinel's md5 and the NIC's MAC are
# properties of the machine; the IP is not.
$SSH "root@$NEWMISTER_IP" "test -f /media/fat/SILEVAL_BOX_ID" \
  || fatal "SILEVAL_BOX_ID sentinel absent on $NEWMISTER_IP — wrong box?"
BOX_ID=$($SSH "root@$NEWMISTER_IP" "cat /media/fat/SILEVAL_BOX_ID")
got_bid=$($SSH "root@$NEWMISTER_IP" "md5sum /media/fat/SILEVAL_BOX_ID" | cut -d' ' -f1)
[ "$got_bid" = "$EXPECT_BOX_ID_MD5" ] \
  || fatal "sentinel md5 $got_bid != expected $EXPECT_BOX_ID_MD5 — this is NOT the registered box for this population"
got_mac=$($SSH "root@$NEWMISTER_IP" "cat /sys/class/net/eth0/address")
[ "$got_mac" = "$FORBIDDEN_MAC" ] \
  && fatal "target MAC $got_mac is the FORBIDDEN box (owner TV/play box) — refused"
[ "$got_mac" = "$EXPECT_MAC" ] \
  || fatal "target MAC $got_mac != registered $EXPECT_MAC — refused"
note "box identity OK: mac=$got_mac sentinel_md5=$got_bid"

mkdir -p "$OUT_DIR/rows" "$OUT_DIR/artifacts"

# The registered design is 240 paired seeds. A seed list of any other length is
# a WIRING FAULT, never a smaller experiment — refuse before touching hardware.
REGISTERED_SEEDS=240
n_seeds=$(command grep -c . "$SEEDS_FILE")
[ "$n_seeds" -eq "$REGISTERED_SEEDS" ] || fatal "seed list $SEEDS_FILE has $n_seeds seeds, registered n is $REGISTERED_SEEDS"

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
    [ "$s1" = "$s2" ] && { scp -q -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP:$r" "$l" && return 0; }
  done
  return 1
}

# Input + screenshot via the on-box channels (the new box has no misterclaw):
# hotkeys through the sileval_inputd FIFO (onbox/inputd.py), screenshots through
# the stock 'screenshot' MiSTer_cmd. ensure_inputd restarts the daemon if an
# owner power-cycle killed it; the FIFO must be a real fifo (a dead daemon plus
# a stray echo leaves a REGULAR file that swallows keys silently).
ensure_inputd() {
  # defense in depth: the hardware-touching helpers re-check ARMED themselves,
  # so no call path (sourcing, future refactor) can reach the box unarmed.
  [ -f "$OUT_DIR/ARMED" ] || fatal "not armed (ensure_inputd)"
  # Liveness is decided ON the box by sileval_inputd_ctl.sh. Two bugs this fixes:
  #  (1) the old check was `test -p <fifo>` — FILE EXISTENCE, not liveness. A
  #      dead daemon leaves its fifo behind, so the check reported ready forever
  #      while every keystroke went into a fifo with no reader (verified: old
  #      check says READY on a killed daemon, ctl says DEAD).
  #  (2) any ssh one-liner that greps for the daemon MATCHES ITS OWN COMMAND
  #      LINE and killed the ssh session (observed: exit 255). The pattern must
  #      live in a file on the box, not in the command we send.
  $SSH "root@$NEWMISTER_IP" "sh $INPUTD_CTL status" >/dev/null 2>&1 && return 0
  note "inputd not alive — starting"
  $SSH "root@$NEWMISTER_IP" "sh $INPUTD_CTL start" >/dev/null 2>&1
  $SSH "root@$NEWMISTER_IP" "sh $INPUTD_CTL status" >/dev/null 2>&1
}
send_combo() { # $*: key names
  [ -f "$OUT_DIR/ARMED" ] || fatal "not armed (send_combo)"
  $SSH "root@$NEWMISTER_IP" "test -p /tmp/sileval_input.fifo && echo 'combo $*' > /tmp/sileval_input.fifo"
}
take_shot() { # $1 local path
  [ -f "$OUT_DIR/ARMED" ] || fatal "not armed (take_shot)"
  local tag="sv$$_$RANDOM"
  $SSH "root@$NEWMISTER_IP" "echo 'screenshot $tag' > /dev/MiSTer_cmd" || return 1
  sleep 2
  local remote
  remote=$($SSH "root@$NEWMISTER_IP" "ls /media/fat/screenshots/NES/*-$tag.png 2>/dev/null | head -1")
  [ -n "$remote" ] && scp -q -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "root@$NEWMISTER_IP:$remote" "$1" && $SSH "root@$NEWMISTER_IP" "rm -f '$remote'"
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
  # An UNREADABLE hash and a SUBSTITUTED cart are different events and only one
  # of them means "someone changed the cart". Population A filed an ssh failure
  # (got= EMPTY) under VOID 1 and halted the run as if the cart had been swapped.
  # `... | cut` also hid the failure: the pipeline's status is cut's, so the
  # `|| cart_md5=SSH_FAIL` fallback never fired. Capture first, then classify.
  local cart_md5 rbf_md5 raw
  raw=$($SSH "root@$NEWMISTER_IP" "md5sum '$sd_cart'") && cart_md5=$(echo "$raw" | cut -d' ' -f1) || cart_md5=""
  raw=$($SSH "root@$NEWMISTER_IP" "md5sum '$SD_RBF'")  && rbf_md5=$(echo "$raw" | cut -d' ' -f1)  || rbf_md5=""
  case "$cart_md5" in
    "")          void_row "$row" "$seed" "$arm" "cart_hash_unreadable_ssh"; return 1 ;;  # transient, retried on resume
    "$cart_want") : ;;
    *)           void_row "$row" "$seed" "$arm" "cart_hash_mismatch got=$cart_md5 want=$cart_want"
                 fatal "cart hash mismatch on SD — a DIFFERENT cart is in place — run halted (prereg VOID 1)" ;;
  esac
  case "$rbf_md5" in
    "")         void_row "$row" "$seed" "$arm" "rbf_hash_unreadable_ssh"; return 1 ;;
    "$RBF_MD5") : ;;
    *)          void_row "$row" "$seed" "$arm" "rbf_hash_mismatch got=$rbf_md5"
                fatal "rbf hash mismatch on SD — run halted" ;;
  esac

  # inject seed into THIS arm's template, push, boot, restore
  local patched="$adir/patched.ss"
  python3 "$HERE/vendor/seedjit_ss.py" seed "$tmpl" "$patched" "$seed" >/dev/null \
    || { void_row "$row" "$seed" "$arm" "seedjit_patch_failed"; return 1; }
  scp -q -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "$patched" "root@$NEWMISTER_IP:$slot" || { void_row "$row" "$seed" "$arm" "scp_slot_failed"; return 1; }
  $SSH "root@$NEWMISTER_IP" "echo load_core /media/fat/menu.rbf > /dev/MiSTer_cmd" || { void_row "$row" "$seed" "$arm" "menu_load_failed"; return 1; }
  sleep 10
  $SSH "root@$NEWMISTER_IP" "echo load_core $mgl > /dev/MiSTer_cmd" || { void_row "$row" "$seed" "$arm" "mgl_load_failed"; return 1; }
  sleep 15
  ensure_inputd || { void_row "$row" "$seed" "$arm" "inputd_unavailable"; return 1; }
  send_combo f1 \
    || { void_row "$row" "$seed" "$arm" "f1_restore_failed"; return 1; }
  local corename t0 n=0 shot_fail=0 pull_fail=0
  corename=$($SSH "root@$NEWMISTER_IP" "cat /tmp/CORENAME 2>/dev/null" || echo "?")
  # no-cart boot gate (Main 260707 MGL hazard): a silently-skipped <file> entry
  # loads the core with NO cart — one static frame forever. Post-F1 we are in
  # live CvC play, so two shots 3 s apart MUST differ; identical twice = VOID.
  take_shot "$adir/boot_a.png"; sleep 3; take_shot "$adir/boot_b.png"
  if [ -f "$adir/boot_a.png" ] && [ -f "$adir/boot_b.png" ]; then
    if [ "$(md5sum < "$adir/boot_a.png")" = "$(md5sum < "$adir/boot_b.png")" ]; then
      sleep 3; take_shot "$adir/boot_c.png"
      [ -f "$adir/boot_c.png" ] && [ "$(md5sum < "$adir/boot_b.png")" = "$(md5sum < "$adir/boot_c.png")" ]         && { void_row "$row" "$seed" "$arm" "no_cart_or_static_boot"; return 1; }
    fi
  else
    # The box being mid-reboot (or the screenshot service not yet up) is
    # TRANSIENT. Population A burned 79 seeds VOIDing on this — and the real
    # cause was our own `ls -t` over a 22,840-file dir, not the owner's power
    # cycling. Wait for the box to answer, re-take, and only VOID if it still
    # fails; the seed stays retriable either way (resume skips only OK rows).
    local try
    for try in 1 2 3; do
      note "boot motion shots missing (try $try) — waiting for the box"
      sleep 20
      $SSH "root@$NEWMISTER_IP" "test -e /dev/MiSTer_cmd" || continue
      ensure_inputd || continue
      rm -f "$adir/boot_a.png" "$adir/boot_b.png"
      take_shot "$adir/boot_a.png"; sleep 3; take_shot "$adir/boot_b.png"
      [ -f "$adir/boot_a.png" ] && [ -f "$adir/boot_b.png" ] && break
    done
    if [ ! -f "$adir/boot_a.png" ] || [ ! -f "$adir/boot_b.png" ]; then
      void_row "$row" "$seed" "$arm" "boot_motion_shots_failed_after_retries"; return 1
    fi
    if [ "$(md5sum < "$adir/boot_a.png")" = "$(md5sum < "$adir/boot_b.png")" ]; then
      sleep 3; take_shot "$adir/boot_c.png"
      [ -f "$adir/boot_c.png" ] && [ "$(md5sum < "$adir/boot_b.png")" = "$(md5sum < "$adir/boot_c.png")" ] \
        && { void_row "$row" "$seed" "$arm" "no_cart_or_static_boot"; return 1; }
    fi
  fi
  t0=$(date +%s)

  # sample loop
  local wedge_suspect=0 h1="" h2="" h3=""
  while :; do
    local now=$(date +%s); local el=$(( now - t0 ))
    [ "$el" -ge "$CYCLE_SECS" ] && break
    local tgt=$(( t0 + (n+1)*SAMPLE_SECS )); local w=$(( tgt - now )); [ "$w" -gt 0 ] && sleep "$w"
    n=$(( n + 1 ))
    local pre; pre=$($SSH "root@$NEWMISTER_IP" "stat -c '%Y' '$save2' 2>/dev/null" || echo 0)
    send_combo leftalt f2
    pull_state "$save2" "$adir/s$(printf %03d "$n").ss" "$pre" || pull_fail=$(( pull_fail + 1 ))
    take_shot "$adir/s$(printf %03d "$n").png" || shot_fail=$(( shot_fail + 1 ))
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

# ---- library mode -----------------------------------------------------------
# The on-box gate scripts (oldbox_gates.sh) need the SAME env gates, identity
# checks and hardware helpers as the run itself. Sourcing this file with
# SILEVAL_LIB_ONLY=1 gives them exactly that and stops here, so there is ONE
# implementation of "how this lane touches a box" rather than two that
# "should agree" (measurement rule 3).
[ -n "${SILEVAL_LIB_ONLY:-}" ] && return 0

# ---- main: ABBA over the registered seed list --------------------------------
i=0
while read -r -u3 seed; do
  [ -f "$OUT_DIR/HALT" ] && { note "HALT file present — stopping"; exit 0; }
  case $(( i % 2 )) in
    0) run_arm "$seed" ship;  run_arm "$seed" slice ;;
    1) run_arm "$seed" slice; run_arm "$seed" ship  ;;
  esac
  i=$(( i + 1 ))
done 3< "$SEEDS_FILE"

# Completion is only completion if the row ledger says so — a clean exit with
# fewer OK rows than the registered set is an ALARM, never a success.
ok_rows=$(command grep -l '"status": "OK"' "$OUT_DIR"/rows/*.json 2>/dev/null | wc -l)
if [ "$ok_rows" -lt $(( REGISTERED_SEEDS * 2 )) ]; then
  fatal "seed loop ended with $ok_rows OK rows < registered $(( REGISTERED_SEEDS * 2 )) — incomplete run, investigate"
fi
note "seed list complete: $ok_rows/$(( REGISTERED_SEEDS * 2 )) OK rows"
