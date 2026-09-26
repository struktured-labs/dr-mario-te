project_open NES
create_timing_netlist
read_sdc
update_timing_netlist
set clk [get_clocks {emu|pll|pll_inst|altera_pll_i|cyclonev_pll|counter[0].output_counter|divclk}]
report_timing -setup -to_clock $clk -npaths 30 -detail summary -file /home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/worst_paths.txt
report_timing -setup -to_clock $clk -npaths 1 -detail full_path -file /home/struktured/projects/dr-mario-h16-wt/tmp/chain540_reach_tap_hsv/worst_path_full.txt
delete_timing_netlist
project_close
