-- DIAG: does the STUDY2P preview draw run on the HUMAN cart? Logs the gating variables.
local OUT = os.getenv("DS_OUT") or "/home/struktured/projects/dr-mario-rl/tmp/tuckguard/study/"
local lf = io.open(OUT.."diag_study3.log","w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local OAM = emu.memType.nesSpriteRam
local function rd(a) return emu.read(a,NES,false) end
local function oam(i) return emu.read(i,OAM,false) end
local function shot(n) local p=emu.takeScreenshot(); local f=io.open(OUT..n,"wb"); f:write(p); f:close() end
local EMU = dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
local s = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
local MATCH_ACTIVE, S2P_TTL, HOLD_ACTIVE = 0x6164, 0x61B0, 0x6195
local frame=0; local cur=nil; local untl=-1
local hb=0
emu.addMemoryCallback(function() hb=hb+1 end, emu.callbackType.exec, 0xD2CC)
local hbAt={}
emu.addEventCallback(function() if cur and frame<untl then emu.setInput(cur,0) end end, emu.eventType.inputPolled)
local function press(i,d) cur=i; untl=frame+(d or 4) end
local function gates(tag)
  logf(string.format("  [%s] mode=%d players$0727=%d MATCH_ACTIVE=%d S2P_TTL=%d HOLD_ACTIVE=%d heartbeat$D2CC_execs=%d",
    tag, rd(0x46), rd(0x0727), rd(MATCH_ACTIVE), rd(S2P_TTL), rd(HOLD_ACTIVE), hb))
end
local function dumpSlots(tag)
  for slot=32,40 do local b=slot*4
    logf(string.format("  [%s] OAM slot %d: Y=%d tile=$%02X attr=$%02X X=%d", tag, slot, oam(b), oam(b+1), oam(b+2), oam(b+3))) end
  logf(string.format("  [%s] preview colours P1 $031A=%d/$031B=%d | P2 $039A=%d/$039B=%d",
    tag, rd(0x031A), rd(0x031B), rd(0x039A), rd(0x039B)))
end
-- menu driving for a HUMAN cart (no autonav): alternate DOWN / START until mode==4
local firstPlay=nil; local pauseFrame=nil; local navN=0
emu.addEventCallback(function()
  frame=frame+1
  local mode=rd(0x46)
  if mode~=4 and not firstPlay and frame%40==0 then
    navN=navN+1
    if rd(0x0727)~=2 and navN%2==1 then press({down=true},4); logf(string.format("nav f=%d mode=%d press DOWN",frame,mode))
    else press({start=true},4); logf(string.format("nav f=%d mode=%d press START",frame,mode)) end
  end
  if mode==4 and not firstPlay then firstPlay=frame; logf("PLAY at "..frame); gates("play-start") end
  if firstPlay and frame==firstPlay+120 then gates("play+120") end
  if firstPlay and frame==firstPlay+300 and not pauseFrame then
    shot("before.png"); gates("pre-pause"); dumpSlots("play")
    press({start=true},4); pauseFrame=frame; logf("injected START (pause) at "..frame)
  end
  if pauseFrame and (frame==pauseFrame+10 or frame==pauseFrame+30 or frame==pauseFrame+60) then
    gates("paused+"..(frame-pauseFrame))
  end
  if pauseFrame and frame==pauseFrame+60 then
    shot("paused.png"); dumpSlots("paused")
    local p1 = oam(37*4)~=255 and oam(38*4)~=255
    local p2 = oam(39*4)~=255 and oam(40*4)~=255
    local st = oam(32*4)~=255
    logf(string.format("VERDICT studyLetters=%s P1preview=%s P2preview=%s", tostring(st), tostring(p1), tostring(p2)))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
  if frame>=4000 then logf("TIMEOUT never reached play; last mode="..mode); logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end) end
end, emu.eventType.endFrame)
