project_open NES
create_timing_netlist
read_sdc
update_timing_netlist
set clk [get_clocks {emu|pll|pll_inst|altera_pll_i|cyclonev_pll|counter[0].output_counter|divclk}]
report_timing -setup -to_clock $clk -npaths 30 -detail summary -file /home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/worst_paths.txt
# WIDE: worst path per ENDPOINT (-nworst 1), 3000 endpoints -- predicts the fallback: the worst endpoint NOT removed by
# DRLEV_SQREG (DSP ENA) / DRLEV_WRREG (copro6502 -> bcell) is the floor the fallback cannot lift.
report_timing -setup -to_clock $clk -npaths 3000 -nworst 1 -detail summary -file /home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/worst_paths.txt.wide
report_timing -setup -to_clock $clk -npaths 1 -detail full_path -file /home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/worst_path_full.txt
# FLOOR detail: the worst full path INTO each walk-control register the fallback must also cover (logic, not just endpoints)
set W /home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv
set dbg [open "$W/worst_paths.txt.floor_debug" w]
foreach r {p wc wr_ run_v run_h vo st vn_hit sq_h_in sq_v_in h_waddr} {
  set got 0
  foreach pat [list {*|LeafEval:leafeval|@R\[*\]*} {*|LeafEval:leafeval|@R\[*} {*leafeval|@R\[*} {*|LeafEval:leafeval|@R} {*leafeval|@R*}] {
    set pp [string map [list @R $r] $pat]
    set dst [get_registers -nowarn $pp]
    set n [get_collection_size $dst]
    puts $dbg "$r  $pp  -> $n"
    if {$n > 0} {
      report_timing -setup -to $dst -npaths 1 -detail full_path -file "$W/worst_paths.txt.floor_${r}"
      set got 1; break
    }
  }
  if {!$got} { puts $dbg "$r  NO MATCH" }
}
close $dbg
delete_timing_netlist
project_close
