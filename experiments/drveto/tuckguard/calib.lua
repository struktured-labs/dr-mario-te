-- Mesen calibration harness: GROUND TRUTH FROM RAM for the DRPROPH death detector.
-- Ground truth = the ROM's own loss condition read from RAM: cells (0,3)/(0,4) of a seat's
-- board occupied. Latched EVERY frame during play, because the boards are DESTROYED
-- SYNCHRONOUSLY at match end (RB337_STAGE_CLEAR/TOP_7) -- sampling at the transition reads
-- a wiped board and logs plausible garbage.
local CFG = dofile("/home/struktured/projects/dr-mario-rl/tmp/prophcvc/mesen/cfg.lua")
local OUT = CFG.outdir
local lf = io.open(OUT.."calib.log","w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local EMU = dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
if not EMU then logf("FATAL: copro_emu nil"); return end
local s = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=CFG.latency }
logf(string.format("attached window=$5200 latency=%d arm=%s", CFG.latency, CFG.arm))

-- throat = cells (0,3),(0,4); board index = row*8+col, empty is $00 or $FF
local function throat(base)
  local a,b = rd(base+3), rd(base+4)
  local function occ(v) return v~=0x00 and v~=0xFF end
  return (occ(a) or occ(b)) and 1 or 0
end
local function fo(base,col)
  for r=0,15 do local v=rd(base+r*8+col); if v~=0 and v~=0xFF then return r end end
  return 16
end
local function gate(base,col)   -- rows 0-1 of a pass column free?
  local function occ(v) return v~=0x00 and v~=0xFF end
  return (not occ(rd(base+col)) and not occ(rd(base+8+col))) and 1 or 0
end
local function topcells(base)
  local n=0
  for r=0,2 do for c=0,7 do local v=rd(base+r*8+c); if v~=0 and v~=0xFF then n=n+1 end end end
  return n
end

local frame=0; local deaths=0; local prevMode=-1
local L = {t1=0,t2=0,v1=0,v2=0,tc1=0,tc2=0,f3=16,f4=16,g2=0,g5=0}     -- last-live latch
local cap = -1; local capName = ""

emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  if mode == 4 then
    L.t1 = throat(0x0400); L.t2 = throat(0x0500)
    L.v1 = rd(0x0324);     L.v2 = rd(0x03A4)
    L.tc1 = topcells(0x0400); L.tc2 = topcells(0x0500)
    L.f3 = fo(0x0500,3); L.f4 = fo(0x0500,4)
    L.g2 = gate(0x0500,2); L.g5 = gate(0x0500,5)
    -- start capturing as soon as a throat is occupied: the death is imminent
    if cap < 0 and (L.t1 == 1 or L.t2 == 1) then
      cap = 0; capName = string.format("d%03d", deaths)
    end
  end
  if cap >= 0 and cap < CFG.capframes then
    local p = emu.takeScreenshot()
    local f = io.open(string.format("%s%s_%04d.png", OUT, capName, cap), "wb")
    if f then f:write(p); f:close() end
    cap = cap + 1
  end
  -- match end: mode leaves 4. The LATCH holds the last live values (boards now wiped).
  if prevMode == 4 and mode ~= 4 then
    deaths = deaths + 1
    logf(string.format("DEATH %03d frame=%d throat_p1=%d throat_p2=%d v1=%02X v2=%02X tc1=%d tc2=%d fo3=%d fo4=%d g2=%d g5=%d cap=%s",
      deaths, frame, L.t1, L.t2, L.v1, L.v2, L.tc1, L.tc2, L.f3 or 16, L.f4 or 16, L.g2 or 0, L.g5 or 0, capName))
    cap = -1
  end
  prevMode = mode
  if frame >= CFG.maxframes or deaths >= CFG.maxdeaths then
    logf(string.format("SUMMARY frames=%d deaths=%d GO=%d DONE=%d", frame, deaths, s.goes, s.dones))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
logf("calib loaded")
