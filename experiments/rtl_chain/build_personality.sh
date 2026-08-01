#!/usr/bin/env bash
# Build ONE personality core, with the four gates the 2026-08-01 incident demands.
#
# HISTORY, because the failure mode is subtle and has now appeared TWICE by different
# routes. The copro firmware ROM is loaded with `initial $readmemh("copro_rom.hex", rom)`,
# which Quartus resolves at SYNTHESIS -- and Quartus does NOT track that .hex as a synthesis
# dependency. So:
#   route 1 (swap_arm.sh): `quartus_cdb --update_mif` has nothing to update, exits 0, and
#           quartus_asm re-emits the same bitstream. Three "arms", all rbf f7d3382a.
#   route 2 (this script, first attempt): `quartus_sh --flow compile` looked like the honest
#           fix, but SMART RECOMPILATION silently reduced it to the SAME thing --
#               Info (293003): Smart recompilation skipped module Analysis & Synthesis ...
#               Info (293003): Smart recompilation skipped module Fitter ...
#           -- and produced racer + stomper360 BOTH byte-identical to the shipped chain180
#           core (71d2de37). 55 seconds, "0 errors".
#
# ★ WHY THIS IS DANGEROUS RATHER THAN MERELY WRONG: a core built from the wrong firmware
# STILL PLAYS WELL, because the arm registers power up to 0 = lnk1, a real 60.2% brain. The
# artifact is mislabelled, not broken, so nothing downstream looks wrong and the eventual
# investigation hunts a bug in a chain reward that never ran.
#
# FOUR GATES, each assert-the-mechanism rather than assert-the-outcome:
#   1 firmware identity   -- BEFORE burning an hour, the built hex must match the manifest
#   2 clean database      -- delete db/ + incremental_db/ so synthesis CANNOT be skipped
#   3 poison-check the log-- FAIL if "Smart recompilation skipped" names synthesis or fitter
#   4 baseline distinctness- the new rbf must differ from the SHIP and EVERY known bitstream,
#                            not merely from its siblings
#   + STA freshness       -- a slack number from a report older than the rbf is not a number
#
# ★ GATE 4 IS WORDED THAT WAY BECAUSE OF A REAL HOLE: the first version compared only against
# sibling personality rbfs, so the FIRST build had nothing to compare against and sailed
# through. It was stopped by the fit verdict instead -- which was ITSELF reading a stale
# NES.sta.rpt, because Timing Analyzer had been skipped too. Two independent holes lined up,
# and only luck kept a mislabelled bitstream off a device.
#
#   build_personality.sh <racer|stomper180|stomper360|fixpoint>
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MAN="$HERE/personalities.json"
ARMS=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/arms
SHIPDIR=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship
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
[ -d "$FORK" ] || { echo "no fork tree at $FORK" >&2; exit 65; }

# ---- GATE 1: firmware identity, BEFORE spending an hour ------------------------------
echo "== building firmware"
( cd "$CANON/fpga/copro" \
  && DRCOPRO_TUCK=$TUCK DRCOPRO_ARM=$ARM DRFIX=$FIX DRCHAIN=$DOSE \
     "$PY" dbg_build.py all 0 >/dev/null ) || { echo "firmware build failed" >&2; exit 66; }
GOT=$(md5sum "$CANON/fpga/copro/copro_rom.hex" | cut -d' ' -f1)
if [ "$GOT" != "$FW_MD5" ]; then
  echo "GATE 1 FIRMWARE IDENTITY FAILED: built $GOT, manifest says $FW_MD5" >&2
  echo "  the flags did not produce the recorded image -- do NOT compile this." >&2
  exit 67
fi
echo "   GATE 1 firmware identity OK: $GOT"
cp "$CANON/fpga/copro/copro_rom.hex" "$FORK/copro_rom.hex"
cp "$CANON/fpga/copro/copro_rom.hex" "$OUT/fw_$ID.hex"
( cd "$CANON/fpga/copro" && "$PY" dbg_build.py all 0 >/dev/null )   # canonical tree back to default

# ---- snapshot the baseline set BEFORE we overwrite anything --------------------------
BASELINE=$(mktemp)
{ find "$SHIPDIR" -name '*.rbf' -print0 2>/dev/null | xargs -0 -r md5sum
  find "$OUT" -name 'NES_*.rbf' -print0 2>/dev/null | xargs -0 -r md5sum
  find "$(dirname "$OUT")/bogus_20260801" -name '*.rbf' -print0 2>/dev/null | xargs -0 -r md5sum
} 2>/dev/null | sort -u > "$BASELINE"
echo "   baseline set: $(wc -l < "$BASELINE") known bitstream(s) to be distinct from"

# ---- GATE 2: clean database so synthesis CANNOT be skipped ---------------------------
cd "$FORK" || exit 65
echo "== GATE 2 clearing db/ + incremental_db/ (smart recompilation must have nothing to reuse)"
rm -rf db incremental_db
FLOWLOG="$OUT/flow_$ID.log"
echo "== full compile from a clean database (~40-70 min; the cheap path does not exist)"
"$QBIN/quartus_sh" --flow compile NES -c NES 2>&1 | tee "$FLOWLOG"
FLOWRC=${PIPESTATUS[0]}
[ "$FLOWRC" = 0 ] || { echo "compile failed (rc=$FLOWRC)" >&2; exit 68; }

# ---- GATE 3: poison-check -- assert the MECHANISM, not just the outcome --------------
if command grep -qE "Smart recompilation skipped module (Analysis & Synthesis|Fitter)" "$FLOWLOG"; then
  echo "GATE 3 POISON-CHECK FAILED: the flow skipped synthesis and/or the fitter:" >&2
  command grep -E "Smart recompilation skipped module" "$FLOWLOG" >&2
  echo "  the firmware did NOT enter the bitstream. This is the update_mif defect wearing" >&2
  echo "  a different hat -- see the header. Do not ship this artifact." >&2
  exit 72
fi
echo "   GATE 3 poison-check OK: synthesis and fitter both ran"

RBF="$OUT/NES_$ID.rbf"
cp output_files/NES.rbf "$RBF" || { echo "no rbf produced" >&2; exit 69; }
NEW=$(md5sum "$RBF" | cut -d' ' -f1)

# ---- GATE 4: distinctness against the WHOLE baseline set, not just siblings ----------
if command grep -q "^$NEW " "$BASELINE"; then
  echo "GATE 4 DISTINCTNESS FAILED: $NEW matches a known bitstream:" >&2
  command grep "^$NEW " "$BASELINE" >&2
  echo "  the firmware did not reach the bitstream." >&2
  rm -f "$BASELINE"; exit 70
fi
echo "   GATE 4 distinctness OK: $NEW is new"
rm -f "$BASELINE"

# ---- FIT VERDICT: delegate to the script that knows which clock is which --------------
# ⚠ THIS WAS A LOCAL PARSE AND IT WAS WRONG (caught on the racer build, 2026-08-01). It
# took the report's global "Worst-case setup slack" with head -1. The Setup Summary is
# sorted worst-first and the worst domain on this design is pll_hdmi at 0.094 -- a
# PRE-EXISTING video-clock number that reads identically on the SHIPPED core. The copro
# domain (emu|pll|...counter[0]) was at 0.181, comfortably over the +0.10 bar, so a
# perfectly good bitstream was stamped "HOLD, below the bar".
#
# ★ The false alarm is the mild half. The number it printed does not depend on the copro
# path AT ALL, so a genuinely degraded copro would have printed the SAME 0.094 -- the gate
# could not separate a good build from a bad one in either direction while looking precise.
# fit_verdict.sh parses per-domain, owns the bar, and checks ALM headroom too. One
# authority, not two that can disagree.
echo
echo "personality : $ID ($DISPLAY)"
echo "firmware    : $GOT"
echo "rbf         : $NEW  -> $RBF"
"$HERE/fit_verdict.sh" "$FORK"
FITRC=$?
case $FITRC in
  0) echo "FIT VERDICT: OK" ;;
  66) echo "FIT VERDICT: UNKNOWN -- reports do not describe this build (see above)." >&2
      exit 73 ;;
  *)  echo "FIT VERDICT: HOLD -- a criterion above failed on this pinned seed." >&2
      echo "  Report it; do NOT seed-hunt." >&2
      exit 71 ;;
esac
echo
echo "Deploy with a DEVICE-SIDE md5 check, and do not load it -- the user picks."
