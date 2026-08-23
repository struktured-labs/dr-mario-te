#!/bin/bash
# oldbox_gates.sh — population-B validity gates on the OLD box (AMENDMENT 1).
# Sources sileval_ab.sh in library mode, so the env gates, box-identity checks
# and hardware helpers are literally the same code the run uses.
#
#   SILEVAL_ENV=$PWD/sileval_oldbox.env ./oldbox_gates.sh
#
# Writes ONLY to $OUT_DIR/gates/ — never to rows/. No gate output is a row.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SILEVAL_LIB_ONLY=1 . "$HERE/sileval_ab.sh"

G="$OUT_DIR/gates"; mkdir -p "$G"
IP="$NEWMISTER_IP"
say() { echo "$(date -Is) [gate] $*"; }

# boot one arm's MGL with MOTION VERIFICATION (3 shots, distinct hashes).
# On this box Main is 2024-05-07 and the MGLs use the old index="1"/relative
# idiom; a silently-skipped <file> would load the core with NO cart, which is a
# single static frame forever. Motion is what distinguishes them.
boot_arm() { # $1 arm, $2 tagdir
  local arm=$1 d=$2 mgl slot; mgl=$(arm_mgl "$arm"); slot=$(arm_slot "$arm")
  mkdir -p "$d"
  $SSH "root@$IP" "echo load_core /media/fat/menu.rbf > /dev/MiSTer_cmd"; sleep 10
  $SSH "root@$IP" "echo load_core $mgl > /dev/MiSTer_cmd" ; sleep 18
  ensure_inputd || { say "FAIL inputd"; return 1; }
  # $3=norestore for the cold-boot gate: an F1 there would restore a slot and
  # the "cold" RNG read would be whatever we last injected, not the boot value.
  [ "${3:-restore}" = "restore" ] && { send_combo f1; sleep 3; }
  take_shot "$d/mv1.png"; sleep 4; take_shot "$d/mv2.png"; sleep 4; take_shot "$d/mv3.png"
  local n; n=$(md5sum "$d"/mv*.png 2>/dev/null | cut -d' ' -f1 | sort -u | wc -l)
  say "$arm motion: $n distinct frames of 3 (need >=2)"
  [ "$n" -ge 2 ]
}

# inject a seed, boot, sample one save-state, print its virus cell set
cells_for() { # $1 arm, $2 seed, $3 tagdir -> writes $3/cells.txt
  local arm=$1 seed=$2 d=$3 tmpl slot save2 pre
  tmpl=$(arm_template "$arm"); slot=$(arm_slot "$arm"); save2=$(arm_saveslot2 "$arm")
  mkdir -p "$d"
  python3 "$HERE/vendor/seedjit_ss.py" seed "$tmpl" "$d/patched.ss" "$seed" >/dev/null || return 1
  scp -q -o BatchMode=yes -o IdentitiesOnly=yes -i "$HOME/.ssh/id_rsa" "$d/patched.ss" "root@$IP:$slot" || return 1
  boot_arm "$arm" "$d" || return 1
  sleep 6
  pre=$($SSH "root@$IP" "stat -c '%Y' '$save2' 2>/dev/null" || echo 0)
  send_combo leftalt f2
  pull_state "$save2" "$d/s.ss" "$pre" || { say "FAIL pull"; return 1; }
  python3 "$HERE/vendor/seedjit_ss.py" board "$d/s.ss" > "$d/cells.txt" || return 1
  python3 "$HERE/vendor/seedjit_ss.py" info  "$d/s.ss" > "$d/info.txt" || return 1
  say "$arm seed=$seed -> $(cat "$d/info.txt")"
}

overlap() { # $1 cellsA $2 cellsB -> prints "P1 m/n  P2 m/n"
  python3 - "$1" "$2" <<'PY'
import sys,re
def parse(f):
    out={}
    for line in open(f):
        m=re.match(r'(P[12]) n=\d+ \[(.*)\]',line.strip())
        if m: out[m.group(1)]=set(int(x) for x in m.group(2).split(',') if x.strip())
    return out
a,b=parse(sys.argv[1]),parse(sys.argv[2])
parts=[]
for k in ('P1','P2'):
    sa,sb=a.get(k,set()),b.get(k,set())
    parts.append(f"{k} {len(sa&sb)}/{max(len(sa),len(sb),1)}")
print("  ".join(parts))
PY
}

# ---- gate sequence ----------------------------------------------------------
say "=== G0 cold-boot RNG (uninjected load, read rng0/rng1 at title) ==="
boot_arm ship "$G/g0_coldboot" norestore && { sleep 4
  pre=$($SSH "root@$IP" "stat -c '%Y' '$(arm_saveslot2 ship)' 2>/dev/null" || echo 0)
  send_combo leftalt f2
  pull_state "$(arm_saveslot2 ship)" "$G/g0_coldboot/s.ss" "$pre" \
    && python3 "$HERE/vendor/seedjit_ss.py" info "$G/g0_coldboot/s.ss" | tee "$G/g0_coldboot/info.txt"; }

say "=== G1/G2 same-seed reproducibility, SHIP arm, seed 4242 (expect HIGH) ==="
cells_for ship 4242 "$G/g1_ship_4242_a"
cells_for ship 4242 "$G/g2_ship_4242_b"

say "=== G3 different-seed control, SHIP arm, seed 27875 (expect LOW) ==="
cells_for ship 27875 "$G/g3_ship_27875"

say "=== G4 paired-seed premise ACROSS ARMS, SLICE arm, seed 4242 (expect HIGH vs G1) ==="
cells_for slice 4242 "$G/g4_slice_4242"

say "=== RESULTS ==="
echo -n "G1 vs G2  same seed,  same arm  (HIGH expected): "; overlap "$G/g1_ship_4242_a/cells.txt" "$G/g2_ship_4242_b/cells.txt"
echo -n "G1 vs G3  DIFF seed,  same arm  (LOW  expected): "; overlap "$G/g1_ship_4242_a/cells.txt" "$G/g3_ship_27875/cells.txt"
echo -n "G1 vs G4  same seed,  DIFF arm  (HIGH expected): "; overlap "$G/g1_ship_4242_a/cells.txt" "$G/g4_slice_4242/cells.txt"
