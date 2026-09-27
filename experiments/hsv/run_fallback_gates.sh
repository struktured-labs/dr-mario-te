#!/usr/bin/env bash
# Gates for the DRHSV timing FALLBACK (LeafEval `ifdef DRLEV_SQREG / DRLEV_WRREG / DRLEV_VNPF), reproducible.
# RTL = the NES_MiSTer fork worktree with claude/hsv-leaf checked out.
#   DRLEV_SQREG: enable-free copies of run_h/run_v feed sq() (seed-13 worst: bcell -> Mult5/Mult6 ENA_DFF0)
#   DRLEV_WRREG: host board-window write registered one clk_cpu (seed-13: copro6502 state -> bcell)
#   DRLEV_VNPF:  S_VNEXT's vir_of[vo] prefetched into a flop (seed-2: bcell -> vir_of -> Mux51 -> run_v/wr_/wc enables)
# Proves: identity with no fallback define; bit-exact PHASE1/3 + link-aware NODE; every mutant killed;
# ZERO engine cycles added (tb CYCLES line) and a clock-identical firmware co-sim (real 6502 bus timing).
set -u
RTL=${RTL:-/home/struktured/projects/NES_MiSTer-hsv/rtl/mappers/LeafEval.sv}
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
Q=/home/struktured/projects/dr-mario-qa-wt/fpga/copro
FW=${FW:-/home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/fw540_reachtap.hex}
H=$(cd "$(dirname "$0")" && pwd); T=$(cd "$H/../.." && pwd)/tmp; mkdir -p "$T"
cd "$H/gate"
PIPE="--define DRLEV_SQREG --define DRLEV_WRREG --define DRLEV_VNPF"

# 1. identity: the fallback blocks are invisible unless their define is set
pp() { local out=$1; shift; verilator -E -P "$@" | command grep -a -v '^\s*$' > "$out"; }   # real files: no <(...) (uutils pipe short-reads)
git -C "$(dirname "$RTL")" show cce212acc94044c88a8ce9886bb6721ff793edb7:rtl/mappers/LeafEval.sv > "$T/LeafEval_cce212a.sv"
pp "$T/pp_cce.txt" "$T/LeafEval_cce212a.sv"; pp "$T/pp_new.txt" "$RTL"
cmp -s "$T/pp_cce.txt" "$T/pp_new.txt" && echo "IDENTITY no-define == cce212a: PASS" || echo "IDENTITY no-define: FAIL"
pp "$T/pp_cce_hsv.txt" -DDRHSV "$T/LeafEval_cce212a.sv"; pp "$T/pp_new_hsv.txt" -DDRHSV "$RTL"
cmp -s "$T/pp_cce_hsv.txt" "$T/pp_new_hsv.txt" && echo "IDENTITY DRHSV-only == cce212a DRHSV: PASS" || echo "IDENTITY DRHSV-only: FAIL"

# 2. bit-exact gate: HSV-only (cycle reference), HSV+fallback, fallback-only
$PY gate.py rtl --rtl "$RTL" --define DRHSV --build "$T/gb_on_cyc" > "$T/gate_on_cyc.log" 2>&1 &
$PY gate.py rtl --rtl "$RTL" --define DRHSV $PIPE --build "$T/gb_pipe" > "$T/gate_pipe.log" 2>&1 &
$PY gate.py rtl --rtl "$RTL" $PIPE --build "$T/gb_pipe_off" > "$T/gate_pipe_off.log" 2>&1 &
wait

# 3. link-aware NODE gate (the only gate that writes the LINK plane through the host port)
for v in base:"" pipe:"-DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF"; do n=${v%%:*}; d=${v#*:}; mkdir -p "$T/ln_$n"
  verilator -E -P --pp-comments $d "$RTL" > "$T/ln_$n/LeafEval.sv"
  $PY gate.py linknode --rtl "$T/ln_$n/LeafEval.sv" --build "$T/gl_$n" > "$T/gate_ln_$n.log" 2>&1 &
done; wait

# 4. mutants on the fallback build. HSV's four must still die; the fallback's own must die;
#    sqlag2 is a MARGIN PROBE (2-deep copy) predicted to PASS, sqlag3 must die (the gate sees lag).
$PY - "$RTL" "$T" <<'PY'
import sys, os
rtl, T = sys.argv[1:3]; src = open(rtl).read()
ONE = "reg  [4:0] sq_h_in, sq_v_in;\nalways @(posedge clk) begin sq_h_in <= run_h; sq_v_in <= run_v; end"
M = {
 "row":    ("wr_ < 4'd9 && (wc", "wr_ < 4'd10 && (wc"),
 "col":    ("wc == 4'd5)) ? 15'd512", "wc == 4'd2)) ? 15'd512"),
 "sign":   ("- ((wr_ < 4'd9", "+ ((wr_ < 4'd9"),
 "delta":  ("((wr_ < 4'd9 && (wc", "((!base_mode && wr_ < 4'd9 && (wc"),
 "wrdata": ("bcell[h_waddr] <= h_wdata;", "bcell[h_waddr] <= wdata;"),
 "sqswap": ("sq_h_in <= run_h; sq_v_in <= run_v;", "sq_h_in <= run_v; sq_v_in <= run_h;"),
 "sqlag3": (ONE, "reg  [4:0] sq_h_in, sq_v_in, sq_h_1, sq_v_1, sq_h_2, sq_v_2;\nalways @(posedge clk) begin sq_h_1 <= run_h; sq_v_1 <= run_v; sq_h_2 <= sq_h_1; sq_v_2 <= sq_v_1; sq_h_in <= sq_h_2; sq_v_in <= sq_v_2; end"),
 "sqlag2": (ONE, "reg  [4:0] sq_h_in, sq_v_in, sq_h_1, sq_v_1;\nalways @(posedge clk) begin sq_h_1 <= run_h; sq_v_1 <= run_v; sq_h_in <= sq_h_1; sq_v_in <= sq_v_1; end"),
 "wrlnk":  ("bl_we = 1'b1; bl_wa = h_waddr; bl_wd = h_wlnk;", "bl_we = 1'b1; bl_wa = h_waddr; bl_wd = wlnk;"),
 # VNPF: prefetch the CURRENT vo (must die); drop the S_COLWALK -> vo=0 arm (must die -- survives PHASE1/2 because vo
 # happens to sit at 127 and wraps to 0, dies in PHASE3 once CMD 7 has moved vo)
 "vnself": ("vir_of[7'd0] : vir_of[vo + 7'd1];", "vir_of[7'd0] : vir_of[vo];"),
 "vnnocw": ("(st == S_COLWALK) ? vir_of[7'd0] : vir_of[vo + 7'd1];", "vir_of[vo + 7'd1];"),
}
for k, (a, b) in M.items():
    assert src.count(a) == 1, k
    d = os.path.join(T, "pmut_" + k); os.makedirs(d, exist_ok=True); open(d + "/LeafEval.sv", "w").write(src.replace(a, b, 1))
PY
for m in row col sign delta wrdata sqswap sqlag3 sqlag2 vnself vnnocw; do
  $PY gate.py rtl --rtl "$T/pmut_$m/LeafEval.sv" --define DRHSV $PIPE --build "$T/gbp_$m" > "$T/gate_pmut_$m.log" 2>&1 &
done
mkdir -p "$T/pmut_wrlnk_pp"; verilator -E -P --pp-comments -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF "$T/pmut_wrlnk/LeafEval.sv" > "$T/pmut_wrlnk_pp/LeafEval.sv"
$PY gate.py linknode --rtl "$T/pmut_wrlnk_pp/LeafEval.sv" --build "$T/glp_wrlnk" > "$T/gate_pmut_wrlnk.log" 2>&1 &
wait

for f in on_cyc pipe pipe_off; do echo "== $f: $(command grep -a -E '^(PHASE|CYCLES)' "$T/gate_$f.log" | tr '\n' ' ')"; done
for f in base pipe; do echo "== linknode $f: $(command grep -a -E '^GATE' "$T/gate_ln_$f.log")"; done
for m in row col sign delta wrdata sqswap sqlag3 sqlag2 vnself vnnocw; do echo "== mutant $m: $(command grep -a -E '^PHASE' "$T/gate_pmut_$m.log" | tr '\n' ' ')"; done
echo "== mutant wrlnk: $(command grep -a -E '^GATE' "$T/gate_pmut_wrlnk.log")"

# 5. firmware co-sim: the real 6502 + the shipped firmware on CoproDrMario, HSV-only vs HSV+fallback, 69 real
#    boards (qa-wt hostdata_real.txt). Moves AND GO->DONE clocks must be identical board for board.
C=$T/fwcosim; mkdir -p "$C"; R=$(dirname "$RTL")
sed -e 's|int n; fscanf(f, "%d", &n);|int n; fscanf(f, "%d", \&n); if (argc > 1 \&\& atoi(argv[1]) < n) n = atoi(argv[1]);|' \
    -e 's|#include <cstdio>|#include <cstdio>\n#include <cstdlib>|' "$Q/sim_mister.cpp" > "$C/sim_mister_n.cpp"
cp "$FW" "$C/copro_rom.hex"; cp "$Q/hostdata_real.txt" "$C/hostdata.txt"
for cfg in hsv:"-DDRHSV" pipe:"-DDRHSV -DDRLEV_SQREG -DDRLEV_WRREG -DDRLEV_VNPF"; do n=${cfg%%:*}; d=${cfg#*:}
  (cd "$C" && verilator --cc --exe --build -j 4 -O2 -Wno-fatal $d --top-module CoproDrMario --Mdir obj_$n -o vsim_$n \
     "$R/CoproDrMario.sv" "$R/LeafEval.sv" "$R/copro6502.v" "$R/copro_alu.v" "$Q/dpram.v" "$C/sim_mister_n.cpp" > build_$n.log 2>&1) &
done; wait
(cd "$C" && $PY - <<'PY'
import os
t = open("hostdata.txt").read().split(); n = int(t[0]); rec = 134; body = t[1:]; assert len(body) == n * rec
for s in range(4):
    idx = list(range(s, n, 4)); d = "shard%d" % s; os.makedirs(d, exist_ok=True)
    with open(d + "/hostdata.txt", "w") as f:
        f.write("%d\n" % len(idx)); [f.write(" ".join(body[i * rec:(i + 1) * rec]) + "\n") for i in idx]
    open(d + "/idx.txt", "w").write(" ".join(map(str, idx)) + "\n"); os.system("cp copro_rom.hex " + d + "/")
PY
)
for s in 0 1 2 3; do for b in hsv pipe; do (cd "$C/shard$s" && ../obj_$b/vsim_$b > run_$b.log 2>&1) & done; done; wait
(cd "$C" && $PY "$H/compare_fwcosim.py")
