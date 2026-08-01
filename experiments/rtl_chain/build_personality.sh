#!/usr/bin/env bash
# Build ONE personality core, with the acceptance gate that swap_arm.sh's failure demands.
#
# This is the WORKING replacement for swap_arm.sh. It does a FULL clean compile, because
# the cheap path does not exist: the firmware ROM is loaded via `initial $readmemh(...)`,
# resolved at SYNTHESIS, so `--update_mif` updates nothing, exits 0, and re-emits the same
# bitstream (measured: three arms, all rbf f7d3382a).
#
# ★ THE GATE IS THE POINT. That failure is silent AND flattering: a core built from the
# wrong firmware still plays well, because the arm registers power up to 0 = lnk1, a real
# 60.2% brain. So it is not enough for the commands to succeed --
#   1. the firmware placed must hash to the manifest's md5, and
#   2. the produced rbf must DIFFER from every other personality's rbf.
# A flag existing is not a flag applying. Verify the ARTIFACT CHANGED.
#
#   build_personality.sh <racer|stomper180|stomper360|fixpoint>
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MAN="$HERE/personalities.json"
ARMS=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/arms
FORK=/home/struktured/projects/NES_MiSTer-winner
CANON=/home/struktured/projects/dr-mario-canonical-wt
QBIN=/home/struktured/intelFPGA_lite/23.1std/quartus/bin
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
OUT="$ARMS"

ID="${1:?usage: build_personality.sh <racer|stomper180|stomper360|fixpoint>}"

read -r FW_REL FW_MD5 DISPLAY TUCK ARM FIX DOSE < <(
  "$PY" - "$MAN" "$ID" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
p = next((p for p in m["personalities"] if p["id"] == sys.argv[2]), None)
if p is None:
    sys.exit("unknown personality '%s' (have: %s)"
             % (sys.argv[2], ", ".join(q["id"] for q in m["personalities"])))
f = p["flags"]
print(p["firmware"]["file"], p["firmware"]["md5"], p["display"].replace(" ", "_"),
      f["DRCOPRO_TUCK"], f["DRCOPRO_ARM"], f["DRFIX"], f["DRCHAIN"])
PY
) || exit 64

echo "== personality: $ID ($DISPLAY)  a_fix=$FIX  DRCHAIN=$DOSE"

if [ ! -d "$FORK" ]; then echo "no fork tree at $FORK" >&2; exit 65; fi

# ---- 1. firmware, and PROVE it is the manifest's image -------------------------------
echo "== building firmware"
( cd "$CANON/fpga/copro" \
  && DRCOPRO_TUCK=$TUCK DRCOPRO_ARM=$ARM DRFIX=$FIX DRCHAIN=$DOSE \
     "$PY" dbg_build.py all 0 >/dev/null ) || { echo "firmware build failed" >&2; exit 66; }
GOT=$(md5sum "$CANON/fpga/copro/copro_rom.hex" | cut -d' ' -f1)
if [ "$GOT" != "$FW_MD5" ]; then
  echo "FIRMWARE IDENTITY GATE FAILED: built $GOT, manifest says $FW_MD5" >&2
  echo "  the flags did not produce the recorded image -- do NOT compile this." >&2
  exit 67
fi
echo "   firmware identity OK: $GOT"
cp "$CANON/fpga/copro/copro_rom.hex" "$FORK/copro_rom.hex"
cp "$CANON/fpga/copro/copro_rom.hex" "$OUT/fw_$ID.hex"
# leave the canonical tree on its default firmware, never an arm build
( cd "$CANON/fpga/copro" && "$PY" dbg_build.py all 0 >/dev/null )

# ---- 2. FULL compile (no update_mif shortcut -- see header) ---------------------------
echo "== full clean compile (this is ~40-70 min; the cheap path does not exist)"
cd "$FORK" || exit 65
"$QBIN/quartus_sh" --flow compile NES -c NES || { echo "compile failed" >&2; exit 68; }

RBF="$OUT/NES_$ID.rbf"
cp output_files/NES.rbf "$RBF" || { echo "no rbf produced" >&2; exit 69; }
NEW=$(md5sum "$RBF" | cut -d' ' -f1)

# ---- 3. DISTINCTNESS GATE: the exact defect swap_arm.sh hit ---------------------------
for other in "$OUT"/NES_*.rbf; do
  [ "$other" = "$RBF" ] && continue
  [ -f "$other" ] || continue
  if [ "$(md5sum "$other" | cut -d' ' -f1)" = "$NEW" ]; then
    echo "DISTINCTNESS GATE FAILED: $RBF is byte-identical to $other" >&2
    echo "  that is swap_arm.sh's defect -- the firmware did not reach the bitstream." >&2
    exit 70
  fi
done

# ---- 4. fit verdict ------------------------------------------------------------------
SLACK=$(command grep -oE 'Worst-case (setup )?slack is [-0-9.]+' output_files/NES.sta.rpt 2>/dev/null \
        | head -1 | command grep -oE '[-0-9.]+$')
echo
echo "personality : $ID ($DISPLAY)"
echo "firmware    : $GOT"
echo "rbf         : $NEW  -> $RBF"
echo "worst slack : ${SLACK:-UNKNOWN}"
if [ -n "${SLACK:-}" ] && [ "$(echo "$SLACK < 0.10" | bc -l 2>/dev/null)" = "1" ]; then
  echo "FIT VERDICT: HOLD -- slack $SLACK is below the +0.10 bar on this pinned seed." >&2
  echo "  Report it; do NOT seed-hunt." >&2
  exit 71
fi
echo "FIT VERDICT: OK"
echo
echo "Deploy with a DEVICE-SIDE md5 check, and do not load it -- the user picks."
