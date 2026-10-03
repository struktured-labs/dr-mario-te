-- lateflip_nmi.lua -- lateflip_probe.lua (banked couch timelines, real cart) + nmi_witness.lua (NMI cycles + lateguard /
-- prestart-phase witnesses). Env: LN_DIR (this directory) + everything both scripts read.
local D = os.getenv("LN_DIR") or error("LN_DIR")
dofile(D .. "/nmi_witness.lua")
-- lateflip_probe ends the run with emu.stop(); write the NMI summary first. If the host table refuses the override
-- the periodic TICK lines (every 3000 frames) still carry the running numbers.
local real_stop = emu.stop
local ok = pcall(function() emu.stop = function(code) pcall(NMIW_summary, "SUMMARY"); return real_stop(code) end end)
if not ok then io.stderr:write("lateflip_nmi: emu.stop not overridable; rely on TICK lines\n") end
dofile(D .. "/lateflip_probe.lua")
