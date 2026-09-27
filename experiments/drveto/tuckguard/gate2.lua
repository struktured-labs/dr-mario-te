-- GATE 2 (DRSEATLOG): does the CART's latch agree with independently-computed RAM truth?
-- Truth is computed HERE, in Lua, from the LIVE boards every frame -- the cart never sees it.
-- The correct build latches during play and must AGREE. The `transition` mutant samples after
-- RB337_STAGE_CLEAR/TOP_7 have wiped $0400/$0500 and must DISAGREE. If this gate cannot kill
-- the mutant it is not testing the thing that matters.
local CFG = dofile("/home/struktured/projects/dr-mario-rl/tmp/prophcvc/mesen/cfg2.lua")
local lf = io.open(CFG.out, "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local EMU = dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
local s = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
local SEAT_T1,SEAT_T2,SEAT_V1,SEAT_V2 = 0x61C7,0x61C8,0x61C9,0x61CA
local function occ(v) return v~=0x00 and v~=0xFF end
local function throat(b) return (occ(rd(b+3)) or occ(rd(b+4))) and 1 or 0 end
local frame,deaths,agree,dis,prevMode = 0,0,0,0,-1
local T = {t1=0,t2=0}
emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  if mode == 4 then T.t1 = throat(0x0400); T.t2 = throat(0x0500) end   -- LUA truth, live boards
  if prevMode == 4 and mode ~= 4 then
    deaths = deaths + 1
    local c1,c2 = rd(SEAT_T1), rd(SEAT_T2)                              -- what the CART latched
    local ok = (c1 == T.t1 and c2 == T.t2)
    if ok then agree = agree + 1 else dis = dis + 1 end
    logf(string.format("DEATH %02d truth(t1=%d,t2=%d) cart(t1=%d,t2=%d) %s",
      deaths, T.t1, T.t2, c1, c2, ok and "AGREE" or "DISAGREE"))
  end
  prevMode = mode
  if frame >= 20000 or deaths >= CFG.ndeaths then
    logf(string.format("VERDICT arm=%s deaths=%d agree=%d disagree=%d", CFG.arm, deaths, agree, dis))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
