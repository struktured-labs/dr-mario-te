#!/usr/bin/env bash
# THE SHIP BUILD: one seed-pinned, fully-archived, provenance-stamped bitstream.
#
# WHY THIS IS SEPARATE FROM seed_sweep.sh. The sweep is a SEARCH: it pins a seed, fits,
# scores, and its EXIT trap restores NES.qsf so a dying sweep cannot leave a seed silently
# pinned. That restore is correct -- and it means a winning seed's configuration is
# TRANSIENT BY DESIGN. "First seed wins" is fine; "first seed wins, the trap unpins it, and
# we ship a default-seed rebuild" is the failure mode, and it is the same family as a sweep
# clobbering the artifact it was sweeping for. So the search does not produce the
# deliverable. This does.
#
# It also absorbs an obligation we already owed: the `ifdef VERILATOR` bypass witness landed
# AFTER the fits that measured the design, so the shipped bitstream's source hash had to be
# re-established against the committed RTL regardless. That is the same run.
#
# Rebuild recipe = re-pin this seed + refit + verify the same slack. The seed is recorded
# in the manifest, because a shipped seed is PROVENANCE, not shame.
#
# ⚠ The project qsf ALREADY CARRIES a seed (`set_global_assignment -name SEED 5` at line
# 55 of NES.qsf), so appending a second SEED line leaves TWO in the file and the result
# depends on Quartus's last-wins behaviour. That is an ambiguity you cannot sign off on, so
# every seed change here STRIPS existing SEED assignments first and writes exactly one.
# Corollary worth knowing: the "default" fits in this campaign were never seed-less -- they
# were SEED 5 all along.
#
# Usage: ship_build.sh <seed> [tag]
set -uo pipefail
SEED="${1:?usage: ship_build.sh <seed> [tag]}"
TAG="${2:-combostomper}"
FORK=/home/struktured/projects/NES_MiSTer-winner
HERE=$(dirname "$(readlink -f "$0")")
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/ship/$TAG-seed$SEED
QSF="$FORK/NES.qsf"

# The bitstream must correspond to COMMITTED source, or the stamp means nothing.
dirty=$(git -C "$FORK" status --porcelain -- rtl/ | head -5)
if [ -n "$dirty" ]; then
  echo "REFUSING: uncommitted RTL in $FORK -- the stamp would record a hash nobody can check:" >&2
  echo "$dirty" >&2
  exit 65
fi

mkdir -p "$OUT"
cp "$QSF" "$QSF.shipbak"
restore() { [ -f "$QSF.shipbak" ] && mv "$QSF.shipbak" "$QSF"; }
trap restore EXIT INT TERM

sed -i '/set_global_assignment -name SEED /d' "$QSF"
printf '\nset_global_assignment -name SEED %s\n' "$SEED" >> "$QSF"
n=$(command grep -c 'name SEED ' "$QSF")
[ "$n" = 1 ] || { echo "qsf has $n SEED lines, expected exactly 1" >&2; exit 70; }
cp "$QSF" "$OUT/NES.qsf.used"          # the exact configuration, archived BEFORE the trap

echo "== ship build: seed $SEED, RTL $(git -C "$FORK" rev-parse --short HEAD) =="
( cd "$FORK" && rm -rf db incremental_db output_files/NES.done && ./run_fit.sh ) \
  > "$OUT/fit.log" 2>&1

# Score BEFORE archiving the bitstream: a build that misses the bar is not a deliverable.
"$HERE/fit_verdict.sh" "$FORK" 2>&1 | tee "$OUT/verdict.txt"
rc=${PIPESTATUS[0]}

for f in NES.rbf NES.sof NES.fit.summary NES.sta.summary NES.fit.rpt NES.sta.rpt; do
  [ -f "$FORK/output_files/$f" ] && cp "$FORK/output_files/$f" "$OUT/"
done
cp "$FORK/rtl/mappers/LeafEval.sv" "$FORK/rtl/mappers/CoproDrMario.sv" "$OUT/" 2>/dev/null
[ -f "$FORK/copro_rom.hex" ] && cp "$FORK/copro_rom.hex" "$OUT/"

{
  echo "{"
  echo "  \"tag\": \"$TAG\","
  echo "  \"seed\": $SEED,"
  echo "  \"rtl_commit\": \"$(git -C "$FORK" rev-parse HEAD)\","
  echo "  \"rtl_branch\": \"$(git -C "$FORK" rev-parse --abbrev-ref HEAD)\","
  echo "  \"leafeval_md5\": \"$(md5sum "$FORK/rtl/mappers/LeafEval.sv" | cut -d' ' -f1)\","
  echo "  \"copro_md5\": \"$(md5sum "$FORK/rtl/mappers/CoproDrMario.sv" | cut -d' ' -f1)\","
  echo "  \"firmware_md5\": \"$(md5sum "$FORK/copro_rom.hex" 2>/dev/null | cut -d' ' -f1)\","
  echo "  \"rbf_md5\": \"$(md5sum "$OUT/NES.rbf" 2>/dev/null | cut -d' ' -f1)\","
  echo "  \"verdict_rc\": $rc,"
  echo "  \"when\": \"$(date -Is)\","
  echo "  \"rebuild\": \"re-pin SEED $SEED in NES.qsf, clean fit, expect the same slack\""
  echo "}"
} > "$OUT/manifest.json"

echo
echo "archived: $OUT"
ls "$OUT"
if [ "$rc" != 0 ]; then
  echo
  echo "⚠ THIS BUILD DID NOT MEET THE BAR -- archived for the record, NOT for deployment."
fi
exit "$rc"
