#!/usr/bin/env bash
# BOUNDED fitter-seed sampling, and the narrow conditions under which it is legitimate.
#
# Seed-chasing is normally a way to buy a lottery ticket on a design that does not close.
# It is NOT that here, and the distinction is the whole justification:
#
#   * The DESIGN point already closes. fit9 sits at +0.096 ns against a +0.10 bar -- a gap
#     of FOUR PICOSECONDS, far inside placement noise.
#   * The worst path is INTERCONNECT-dominated, not logic-dominated. Measured on fit9:
#     11.096 ns of data delay, of which roughly 6 ns is routing, including single hops of
#     2.147 ns and 1.695 ns as a 128:1 bcell mux is spread across LABCELL_X33 -> X23 -> X11,
#     half the die. Four mux levels is not a deep path; it is a badly placed one, and
#     placement is exactly what a seed moves.
#   * The next path in the copro domain is at +0.164, so there is 68 ps of room behind the
#     leader -- fixing it structurally would not be blocked by a cluster.
#   * The alternative structural fix means restructuring BASELINE eval accumulators
#     (gate-protected, but the shipped eval's inner loop) to chase 4 ps, and it would not
#     touch the interconnect that dominates the path.
#
# The ship criterion is unchanged and is what makes this sound: a signoff STA of >= +0.10
# on the ACTUAL shipped netlist. That is valid physics whichever seed found the placement.
# A shipped seed is PROVENANCE, not shame -- it is recorded in the manifest with the whole
# sampled distribution, so nobody later wonders whether the number was cherry-picked.
#
# Sequential by design: two Quartus flows in one project directory corrupt each other's db
# (that is what produced a phantom "92% fits" reading earlier in this work).
#
# ⚠ The project qsf ALREADY CARRIES a seed (`set_global_assignment -name SEED 5` at line
# 55 of NES.qsf), so appending a second SEED line leaves TWO in the file and the result
# depends on Quartus's last-wins behaviour. That is an ambiguity you cannot sign off on, so
# every seed change here STRIPS existing SEED assignments first and writes exactly one.
# Corollary worth knowing: the "default" fits in this campaign were never seed-less -- they
# were SEED 5 all along.
#
# Usage: seed_sweep.sh [seed ...]        default: 2 3 4 5
set -uo pipefail
FORK=/home/struktured/projects/NES_MiSTer-winner
HERE=$(dirname "$(readlink -f "$0")")
OUT=/home/struktured/projects/dr_mario_rl/tmp/rtl_chain/seeds
SEEDS=("$@"); [ ${#SEEDS[@]} -eq 0 ] && SEEDS=(2 3 4 5)
mkdir -p "$OUT"

QSF="$FORK/NES.qsf"
cp "$QSF" "$QSF.seedbak"
restore() { cp "$QSF.seedbak" "$QSF"; rm -f "$QSF.seedbak"; }
trap restore EXIT INT TERM        # a sweep that dies must not leave a seed pinned

echo "RTL under test: $(md5sum "$FORK/rtl/mappers/LeafEval.sv" | cut -d' ' -f1)"
for s in "${SEEDS[@]}"; do
  echo
  echo "================ SEED $s  ($(date -Is)) ================"
  cp "$QSF.seedbak" "$QSF"
  sed -i '/set_global_assignment -name SEED /d' "$QSF"
  printf '\nset_global_assignment -name SEED %s\n' "$s" >> "$QSF"
  n=$(command grep -c 'name SEED ' "$QSF")
  [ "$n" = 1 ] || { echo "qsf has $n SEED lines, expected exactly 1" >&2; exit 70; }
  ( cd "$FORK" && rm -rf db incremental_db output_files/NES.done \
    && ./run_fit.sh ) > "$OUT/fit_seed$s.log" 2>&1
  "$HERE/fit_verdict.sh" "$FORK" 2>&1 | tee "$OUT/verdict_seed$s.txt"
  cp "$FORK/output_files/NES.fit.summary" "$OUT/fit_seed$s.summary" 2>/dev/null
  cp "$FORK/output_files/NES.sta.summary" "$OUT/sta_seed$s.summary" 2>/dev/null
done

echo
echo "================ DISTRIBUTION ================"
for s in "${SEEDS[@]}"; do
  v="$OUT/verdict_seed$s.txt"
  [ -f "$v" ] && printf "seed %-3s %s | %s\n" "$s" \
    "$(command grep 'copro slack' "$v" | sed 's/^ *//')" \
    "$(command grep 'ALMs' "$v" | sed 's/^ *//')"
done
echo
echo "Ship the FIRST seed meeting the bar; record every sampled seed in the manifest."
