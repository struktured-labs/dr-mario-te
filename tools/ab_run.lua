-- ab_run.lua — definitive TWO-WINDOW proof: attach copro_emu on BOTH copro windows of the AB
-- dual-copro cart and prove BOTH AI players place pills with ZERO input. Validates that
-- copro_emu.lua is reusable for a multi-window cart (the load-bearing "any cart" claim).
--   P1: window $5000 board $0400 colA/B $0301/$0302 virus $0324 tgtC $6150
--   P2: window $5200 board $0500 colA/B $0381/$0382 virus $03A4 tgtC $6152
local DIR = (os and os.getenv and os.getenv("DRQA_DIR")) or error("set DRQA_DIR to the folder holding copro_emu.lua")
if DIR:sub(-1) ~= "/" then DIR = DIR .. "/" end
local OUT = (os and os.getenv and os.getenv("DRQA_OUT")) or (DIR .. "shots/")
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local lf = io.open(OUT.."ab_run.log", "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function shot(n) local p=emu.takeScreenshot(); local f=io.open(OUT..n,"wb"); f:write(p); f:close() end
local function fill(base) local n=0; for i=0,127 do local c=rd(base+i); if c~=0xFF and c~=0x00 then n=n+1 end end; return n end

local EMU = dofile(DIR.."copro_emu.lua")
if not EMU then logf("FATAL: copro_emu.lua returned nil"); pcall(function() emu.stop(1) end); return end
local LAT = 24
local p1 = EMU.attach{ window=0x5000, board_src=0x0400, colA=0x0301, colB=0x0302, latency=LAT }
local p2 = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=LAT }
logf(string.format("copro_emu attached BOTH windows: P1 $5000/$0400  P2 $5200/$0500  latency=%d", LAT))

local frame=0; local firstPlay=nil; local shotN=0
local v1min,v2min=99,99
emu.addEventCallback(function()
  frame=frame+1
  local mode=rd(0x46)
  if mode==4 and not firstPlay then firstPlay=frame; logf("PLAY at "..frame.." players$0727="..rd(0x0727)) end
  if mode==4 then local a=rd(0x0324); if a<v1min then v1min=a end; local b=rd(0x03A4); if b<v2min then v2min=b end end
  if mode==4 and firstPlay and (frame-firstPlay)%120==0 then
    logf(string.format("t=%d(+%d)  P1: vir=%d(min%d) fill=%d tgtC=%d px=%d GO=%d DONE=%d | P2: vir=%d(min%d) fill=%d tgtC=%d px=%d GO=%d DONE=%d",
      frame, frame-firstPlay,
      rd(0x0324), v1min, fill(0x0400), rd(0x6150), rd(0x0305), p1.goes, p1.dones,
      rd(0x03A4), v2min, fill(0x0500), rd(0x6152), rd(0x0385), p2.goes, p2.dones))
  end
  if mode==4 and firstPlay and shotN<3 and (frame-firstPlay)==(shotN+1)*180 then shotN=shotN+1; shot(string.format("ab_play_%02d.png",shotN)) end
  if (firstPlay and frame>=firstPlay+780) or frame>=3000 then
    logf(string.format("SUMMARY  P1 GO=%d DONE=%d virMin=%d | P2 GO=%d DONE=%d virMin=%d  (dual-window plumbing proven if BOTH GO>3 && tgtC varied)",
      p1.goes, p1.dones, v1min, p2.goes, p2.dones, v2min))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
logf("ab_run loaded")
