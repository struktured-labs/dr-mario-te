-- ============================================================================
-- qa_harness.lua — reusable Mesen QA runner for Dr. Mario COPRO carts.
-- Loads copro_emu.lua (the mailbox emulator) so the mapper-100 cart's driver runs, drives it
-- into VS-CPU play (the cart self-navigates), proves the AI places pills, then pauses into the
-- DRSTUDY screen and dumps/screenshots the STUDY text + both next-pill previews.
--
-- Edit CFG below per cart, then launch (see README):
--   cd <mesen Release dir>
--   timeout 130 run_mesen.sh <cart_mmc1.nes> qa_harness.lua --donotsavesettings
-- Screenshots + qa_harness.log land in CFG.outdir. The Lua calls emu.stop(0) when finished.
-- ============================================================================
local CFG = {
  dir      = (os and os.getenv and os.getenv("DRQA_DIR")) or error("set DRQA_DIR to the folder holding copro_emu.lua"),
  outdir   = (os and os.getenv and os.getenv("DRQA_OUT")) or "/tmp/",
  -- copro mailbox (single-window Pocket build: window $5000 serves P2; board source = P2 playfield)
  window   = 0x5000, board_src = 0x0500, colA = 0x0381, colB = 0x0382,
  latency  = 24,        -- frames of "search" before DONE flips (silicon ~15-50; tune to taste)
  do_study = true,      -- also pause into STUDY and verify both previews
}
if CFG.dir:sub(-1) ~= "/" then CFG.dir = CFG.dir .. "/" end
if CFG.outdir:sub(-1) ~= "/" then CFG.outdir = CFG.outdir .. "/" end

local OUT = CFG.outdir
local lf = io.open(OUT.."qa_harness.log", "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local OAM = emu.memType.nesSpriteRam
local function rd(a) return emu.read(a, NES, false) end
local function oam(i) return emu.read(i, OAM, false) end
local function shot(name) local p=emu.takeScreenshot(); local f=io.open(OUT..name,"wb"); f:write(p); f:close() end
local function fill(base) local n=0; for i=0,127 do local c=rd(base+i); if c~=0xFF and c~=0x00 then n=n+1 end end; return n end

local EMU = dofile(CFG.dir.."copro_emu.lua")
if not EMU then logf("FATAL: dofile copro_emu.lua returned nil"); return end
local s = EMU.attach{ window=CFG.window, board_src=CFG.board_src, colA=CFG.colA, colB=CFG.colB, latency=CFG.latency }
logf(string.format("copro_emu attached window=$%04X board_src=$%04X latency=%d", CFG.window, CFG.board_src, CFG.latency))

-- input injection: port 0. In the single-window Pocket build P1 is the un-driven side, so its
-- START reaches the game (pause). The AI (P2) is driven entirely by the emulated mailbox.
local frame=0; local cur=nil; local untl=-1
emu.addEventCallback(function() if cur and frame<untl then emu.setInput(cur,0) end end, emu.eventType.inputPolled)
local function press(i,d) cur=i; untl=frame+(d or 4) end

local function dumpSlots(tag)
  for slot=32,40 do local b=slot*4
    logf(string.format("  [%s] OAM slot %d: Y=%d tile=$%02X attr=$%02X X=%d", tag, slot, oam(b), oam(b+1), oam(b+2), oam(b+3))) end
  logf(string.format("  [%s] preview colors P1 $031A=%d/$031B=%d | P2 $039A=%d/$039B=%d",
    tag, rd(0x031A), rd(0x031B), rd(0x039A), rd(0x039B)))
end

local firstPlay=nil; local minV=99; local pauseFrame=nil; local shotN=0
emu.addEventCallback(function()
  frame=frame+1
  local mode=rd(0x46)
  if mode==4 and not firstPlay then firstPlay=frame; logf("PLAY at "..frame.." players$0727="..rd(0x0727)) end
  if mode==4 then local v=rd(0x03A4); if v<minV then minV=v end end
  -- prove placement: screenshots + telemetry over the first ~5s of play
  if mode==4 and firstPlay and (frame-firstPlay)%90==0 then
    logf(string.format("t=%d(+%d) vP2=%d(min %d) TGT_C2=%d P2x=%d fillP2=%d GO=%d DONE=%d",
      frame, frame-firstPlay, rd(0x03A4), minV, rd(0x6152), rd(0x0385), fill(0x0500), s.goes, s.dones))
  end
  if mode==4 and firstPlay and shotN<3 and (frame-firstPlay)==(shotN+1)*120 then shotN=shotN+1; shot(string.format("play_%02d.png",shotN)) end
  -- STUDY: after ~4s of play, pause and inspect both previews
  if CFG.do_study and firstPlay and frame==firstPlay+300 and not pauseFrame then
    shot("study_before.png"); dumpSlots("play")
    press({start=true},4); pauseFrame=frame; logf("injected START (pause) at "..frame)
  end
  if pauseFrame and frame==pauseFrame+30 then shot("study_paused.png"); dumpSlots("paused")
    -- verdict
    local p1 = oam(37*4)~=255 and oam(38*4)~=255
    local p2 = oam(39*4)~=255 and oam(40*4)~=255
    logf(string.format("STUDY VERDICT bothPreviews=%s (P1@x=%d,%d  P2@x=%d,%d)",
      tostring(p1 and p2), oam(37*4+3), oam(38*4+3), oam(39*4+3), oam(40*4+3)))
    press({start=true},4); logf("injected START (resume) at "..frame)
  end
  if pauseFrame and frame==pauseFrame+90 then shot("study_resumed.png"); logf("resume mode="..rd(0x46)) end
  local endF = pauseFrame and (pauseFrame+120) or (firstPlay and firstPlay+700)
  if (endF and frame>=endF) or frame>=2400 then
    logf(string.format("SUMMARY GO=%d DONE=%d minVirusP2=%d (placement proven if GO>3 && TGT varied)", s.goes, s.dones, minV))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
logf("qa_harness loaded")
