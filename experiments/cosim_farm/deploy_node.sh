#!/usr/bin/env bash
# Ship the farm to another machine. No toolchain install required on the target.
#
# The co-sim binary is built ONCE, here, with -O2 and deliberately WITHOUT -march=native
# (measured: native bought nothing and would have pinned the binary to this CPU). It is
# therefore portable to any x86-64 Linux with a compatible libstdc++ -- verified by
# running a decision on the Hetzner box, which has no verilator at all.
#
# Firmware travels as the copro_rom.hex the arm actually uses; the remote prints the md5
# it loaded so the arm is confirmed from content, never from a directory name.
#
# Usage: deploy_node.sh <ssh-target> [ssh-key] [remote-dir]
#   deploy_node.sh root@178.104.197.190 ~/.ssh/hetzner_rbm /root/drm_cosim
set -e
TARGET="${1:?usage: deploy_node.sh <ssh-target> [key] [remote-dir]}"
KEY="${2:-}"
RDIR="${3:-/root/drm_cosim}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FW_SRC="${FW_SRC:-/mnt/data/drmario_cosim/fw}"

SSH="ssh -o ConnectTimeout=15"
SCP="scp -o ConnectTimeout=15"
[ -n "$KEY" ] && { SSH="$SSH -i $KEY"; SCP="$SCP -i $KEY"; }

echo "== staging $RDIR on $TARGET =="
$SSH "$TARGET" "mkdir -p $RDIR/fw $RDIR/results $RDIR/logs"

echo "== binary + harness =="
$SCP "$HERE/build/obj_farm/farm_vsim" "$TARGET:$RDIR/farm_vsim"
$SCP "$HERE/cosim.py" "$HERE/game.py" "$HERE/run_farm.py" "$HERE/analyze.py" \
     "$TARGET:$RDIR/"

echo "== firmware arms =="
for arm in "$FW_SRC"/*/; do
  name="$(basename "$arm")"
  [ -f "$arm/copro_rom.hex" ] || continue
  $SSH "$TARGET" "mkdir -p $RDIR/fw/$name"
  $SCP "$arm/copro_rom.hex" "$TARGET:$RDIR/fw/$name/"
  echo "   $name $(md5sum "$arm/copro_rom.hex" | cut -d' ' -f1)"
done

echo "== smoke: one decision on an empty board, per arm =="
$SSH "$TARGET" "cd $RDIR && for d in fw/*/; do \
    printf '1 2 1 3'; python3 -c \"print(' '+('ff '*128).strip())\" ; done \
  | true; \
  for d in fw/*/; do \
    r=\$(cd \$d && echo \"1 2 1 3 \$(python3 -c \"print((\\\"ff \\\"*128).strip())\")\" \
        | $RDIR/farm_vsim); \
    echo \"   \$d -> \$r  (md5 \$(md5sum \$d/copro_rom.hex | cut -d' ' -f1))\"; \
  done"

cat <<EOF

== deployed. run a disjoint seed slice there, e.g.:
$SSH $TARGET "cd $RDIR && nohup nice -n 10 python3 run_farm.py \\
   --arm s20b --fw $RDIR/fw/s20b --out $RDIR/results/ab.jsonl \\
   --seed-start 1000 --seed-count 50 --workers 3 \\
   > $RDIR/logs/s20b.log 2>&1 < /dev/null & disown"

   Shards are disjoint seed ranges with no shared state, so results concatenate:
   scp back and cat into one JSONL before analyze.py.
   NOTE: run_farm.py imports the faithful sim (drmario.*) and nes_pills; a target
   without them can still serve DECISIONS via farm_vsim but cannot play games.
EOF
