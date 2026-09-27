-- ============================================================================
-- flicker_gate.lua — GATE detector for the STUDY2P OAM-leak fix (2026-08-08).
-- Derived from tmp/flicker_repro/flicker_repro.lua (the run that confirmed the
-- root cause on the byte-exact field cart 3e7c6ed9); same ground truth:
-- RENDERED OAM from emu.memType.nesSpriteRam, never the $0200 shadow.
--
-- Classification (the one change vs the repro script): a STUDY-rendered frame
-- is UNEXPECTED only when the game is NOT in the pause loop ($978E exec == 0
-- this frame), NOT board-holding, NOT within our own injection window, and
-- $0046==4. On the unfixed cart the leak has pauseExec==0 on every leaked
-- frame (measured), so the detector still fires on the defect — while a real
-- (injected) pause is correctly counted as legitimate STUDY.
--
-- Extra instrumentation for the fix gates:
--   FLK_FAULT=1   inject a spurious START mid-play (house defect-first gate):
--                 measures STUDY onset latency after the press and clearance
--                 latency after the unpause.
--   FLK_ENDGAME=1 poke P2's virus counter ($03A4) to 0 mid-play to drive the
--                 game's own STAGE CLEAR path -> DRHOLDBOARD arm; counts STUDY
--                 frames rendered during the hold (must be 0 on the fix) and
--                 verifies the hold arms + releases.
-- Env: FLK_OUT (dir), FLK_MAXF, FLK_SEED, FLK_QADIR, FLK_FAULT, FLK_ENDGAME.
-- ============================================================================
local OUT   = os.getenv("FLK_OUT") or "."
local FAULT = tonumber(os.getenv("FLK_FAULT") or "0")
local ENDG  = tonumber(os.getenv("FLK_ENDGAME") or "0")
local MAXF  = tonumber(os.getenv("FLK_MAXF") or "36000")
local SEED  = tonumber(os.getenv("FLK_SEED") or "1")
local QADIR = os.getenv("FLK_QADIR") or "/home/struktured/projects/dr-mario-qa-wt/tools/"

math.randomseed(SEED)

local EMU = dofile(QADIR .. "copro_emu.lua")
-- single-window DRPOCKET cart: $5000 serves P2 (board $0500, colors $0381/82)
local cop = EMU.attach{ window = 0x5000, board_src = 0x0500,
                        colA = 0x0381, colB = 0x0382, latency = 12 }

local NES = emu.memType.nesMemory
local SPR = emu.memType.nesSpriteRam
local function rd(a)  return emu.read(a, NES, false) end
local function rds(a) return emu.read(a, SPR, false) end

local logf = io.open(OUT .. "/run.log", "w")
local csvf = io.open(OUT .. "/trace.csv", "w")
csvf:write("frame,m46,z04,p727,f5,f7,hold,hcnt,m0300,m0380,vc1,vc2,capy,dma," ..
           "pauseExec,studyExec,sprY32,sprT32,studyVis,injStart,shadowT32,shadowY32,hygExec,ttl\n")
local function log(s)
  logf:write(s .. "\n"); logf:flush()
end

-- ---- pure-Lua counters bumped from memory callbacks (NO emu.* inside) ----
local dmaCount   = 0
local pauseExec  = 0   -- exec hits at $978E since last frame (real pause loop)
local studyExec  = 0   -- exec hits at $D2CC since last frame (part1 heartbeat)
local hygExec    = 0   -- exec hits at $8712 (R8712 main-loop OAM hygiene)
emu.addMemoryCallback(function() dmaCount = dmaCount + 1 end,
                      emu.callbackType.write, 0x4014)
emu.addMemoryCallback(function() hygExec = hygExec + 1 end,
                      emu.callbackType.exec, 0x8712)
emu.addMemoryCallback(function() pauseExec = pauseExec + 1 end,
                      emu.callbackType.exec, 0x978E)
emu.addMemoryCallback(function() studyExec = studyExec + 1 end,
                      emu.callbackType.exec, 0xD2CC)

-- ---- input policy state ----
local fc          = 0
local playFrames  = 0
local games       = 0
local lastM46     = -1
local injStartUntil = -1
local lastInjStart  = -1e9
local lastStartTap  = -1e9
local holdSince     = -1
local faultDone     = 0
local faultRelease  = -1e9
local faultPress    = -1     -- frame the injected pause press landed
local faultUnpause  = -1     -- frame the unpause press landed
local curAct, actUntil = nil, -1
local endgDone      = 0

-- ---- detector state ----
local studyVisFrames    = 0
local studyUnexpected   = 0
local shots             = 0
local firstUnexpected   = -1
local spontStartFrames  = 0
local dmaAnomalies      = 0
local pauseExecFrames   = 0
local lastPauseFrame    = -1e9  -- last frame with a $978E hit (pause-proximity window)
local lastDma           = 0
local faultOnsetLat     = -1   -- frames press -> STUDY rendered (FAULT arm)
local faultClearLat     = -1   -- frames unpause -> STUDY gone   (FAULT arm)
local pauseStudyFrames  = 0    -- STUDY frames rendered while pause loop live
local holdStudyFrames   = 0    -- STUDY frames rendered while board held (must be 0)
local holdArmedAt       = -1
local holdReleasedAt    = -1
local holdFrames        = 0

local function screenshot(tag)
  if shots >= 12 then return end
  shots = shots + 1
  local png = emu.takeScreenshot()
  local f = io.open(string.format("%s/shot_f%07d_%s.png", OUT, fc, tag), "wb")
  if f then f:write(png); f:close() end
end

local function summary(reason)
  local s = string.format(
    "SUMMARY reason=%s frames=%d games=%d play_frames=%d goes=%d dones=%d " ..
    "studyVisFrames=%d studyUnexpected=%d firstUnexpected=%d spontStartFrames=%d " ..
    "pauseExecFrames=%d pauseStudyFrames=%d dmaAnomalies=%d fault=%d faultDone=%d " ..
    "faultOnsetLat=%d faultClearLat=%d endg=%d holdArmedAt=%d holdReleasedAt=%d " ..
    "holdFrames=%d holdStudyFrames=%d",
    reason, fc, games, playFrames, cop.goes, cop.dones,
    studyVisFrames, studyUnexpected, firstUnexpected, spontStartFrames,
    pauseExecFrames, pauseStudyFrames, dmaAnomalies, FAULT, faultDone,
    faultOnsetLat, faultClearLat, ENDG, holdArmedAt, holdReleasedAt,
    holdFrames, holdStudyFrames)
  log(s)
  local f = io.open(OUT .. "/SUMMARY.txt", "w"); f:write(s .. "\n"); f:close()
end

emu.addEventCallback(function()
  local t = {}
  if fc <= injStartUntil then t.start = true end
  if curAct and fc <= actUntil then t[curAct] = true end
  emu.setInput(t, 0)
end, emu.eventType.inputPolled)

emu.addEventCallback(function()
  fc = fc + 1
  local m46  = rd(0x0046)
  local z04  = rd(0x04)
  local p727 = rd(0x0727)
  local f5   = rd(0xF5)
  local f7   = rd(0xF7)
  local hold = rd(0x6195)
  local hcnt = rd(0x6197) + 256 * rd(0x6198)
  local ttl  = rd(0x61B0)
  local m0300 = rd(0x0300)
  local m0380 = rd(0x0380)
  local vc1  = rd(0x0324)
  local vc2  = rd(0x03A4)
  local capy = rd(0x0386)

  -- ---- STUDY-on-screen detector (sprite RAM = what the PPU rendered) ----
  local y32, t32 = rds(0x80), rds(0x81)
  local t33, t34 = rds(0x85), rds(0x89)
  local studyVis = (t32 == 0x0D and t33 == 0xA0 and t34 == 0x0C and y32 < 0xEF) and 1 or 0
  local shT32, shY32 = rd(0x0281), rd(0x0280)

  local dmaDelta = dmaCount - lastDma; lastDma = dmaCount
  local injRecent = (fc - lastInjStart) <= 90
  if pauseExec > 0 then lastPauseFrame = fc end
  -- pause-PROXIMITY, not same-frame $978E: the spin is not frame-locked (measured beat:
  -- single frames with pauseExec==0 inside a real pause). The leak has pauseExec==0 for
  -- THOUSANDS of consecutive frames, so an 8-frame window cannot mask it.
  local pauseNear = (fc - lastPauseFrame) <= 8

  if studyVis == 1 then
    studyVisFrames = studyVisFrames + 1
    if pauseExec > 0 then pauseStudyFrames = pauseStudyFrames + 1 end
    if hold ~= 0 then
      holdStudyFrames = holdStudyFrames + 1
      if holdStudyFrames <= 6 then
        log(string.format("STUDY_OVER_HELD_BOARD f=%d m46=%d ttl=%d", fc, m46, ttl))
        screenshot("heldstudy")
      end
    end
    -- UNEXPECTED = rendered in play with the game NOT in the pause loop, no
    -- injection window, no hold. The leak has pauseExec==0 on every leaked
    -- frame (measured on 3e7c6ed9), so this still fires on the defect.
    if m46 == 4 and pauseNear == false and injRecent == false and hold == 0 then
      studyUnexpected = studyUnexpected + 1
      if firstUnexpected < 0 then firstUnexpected = fc end
      log(string.format(
        "STUDY_UNEXPECTED f=%d m46=%d f5=%02x f7=%02x hold=%d y32=%02x ttl=%d pauseExec=%d studyExec=%d dma=%d capy=%02x",
        fc, m46, f5, f7, hold, y32, ttl, pauseExec, studyExec, dmaDelta, capy))
      if studyUnexpected <= 6 then screenshot("unexpected") end
    elseif studyUnexpected == 0 and studyVisFrames <= 3 then
      log(string.format("STUDY_VISIBLE(pause/inj/hold) f=%d m46=%d hold=%d inj=%s pauseExec=%d y32=%02x",
        fc, m46, hold, tostring(injRecent), pauseExec, y32))
      screenshot("visible")
    end
    if faultPress >= 0 and faultOnsetLat < 0 then
      faultOnsetLat = fc - faultPress
      log(string.format("FAULT_STUDY_ONSET f=%d lat=%d", fc, faultOnsetLat))
      screenshot("faultpause")
    end
  else
    if faultUnpause >= 0 and faultClearLat < 0 and fc > faultUnpause then
      faultClearLat = fc - faultUnpause
      log(string.format("FAULT_STUDY_CLEARED f=%d lat=%d", fc, faultClearLat))
      screenshot("faultclear")
    end
  end

  local startBit = ((f5 % 32) >= 16) or ((f7 % 32) >= 16)
  if startBit and not injRecent then
    spontStartFrames = spontStartFrames + 1
    if spontStartFrames <= 20 then
      log(string.format("SPONT_START f=%d m46=%d f5=%02x f7=%02x hold=%d", fc, m46, f5, f7, hold))
    end
  end

  if pauseExec > 0 then pauseExecFrames = pauseExecFrames + 1 end
  if hold ~= 0 then holdFrames = holdFrames + 1 end
  if dmaDelta ~= 1 then
    dmaAnomalies = dmaAnomalies + 1
    if dmaAnomalies <= 30 then
      log(string.format("DMA_ANOMALY f=%d delta=%d m46=%d hold=%d", fc, dmaDelta, m46, hold))
    end
  end

  -- ---- mode / hold transitions ----
  if m46 ~= lastM46 then
    log(string.format("MODE f=%d %d->%d p727=%d z04=%d hold=%d vc1=%d vc2=%d",
      fc, lastM46, m46, p727, z04, hold, vc1, vc2))
    if m46 == 4 and lastM46 ~= 4 then games = games + 1; playFrames = 0 end
    lastM46 = m46
  end
  if hold ~= 0 and holdSince < 0 then
    holdSince = fc
    if holdArmedAt < 0 then holdArmedAt = fc end
    log(string.format("HOLD_ARMED f=%d m46=%d vc1=%d vc2=%d", fc, m46, vc1, vc2))
    screenshot("holdarm")
  elseif hold == 0 and holdSince >= 0 then
    holdReleasedAt = fc
    log(string.format("HOLD_RELEASED f=%d after=%d", fc, fc - holdSince))
    holdSince = -1
  end

  -- ---- CSV trace ----
  csvf:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
    fc, m46, z04, p727, f5, f7, hold, hcnt, m0300, m0380, vc1, vc2, capy,
    dmaDelta, pauseExec, studyExec, y32, t32, studyVis,
    (fc <= injStartUntil) and 1 or 0, shT32, shY32, hygExec, ttl))
  pauseExec = 0; studyExec = 0; hygExec = 0

  -- ---- input policy ----
  if m46 == 4 then playFrames = playFrames + 1 end

  if ENDG == 1 and endgDone == 0 and m46 == 4 and hold == 0 and playFrames >= 900 then
    -- drive the game's own STAGE CLEAR: P2's virus counter -> 0 (BCD; 0 is 0)
    emu.write(0x03A4, 0, NES)
    endgDone = 1
    log(string.format("ENDGAME_POKE f=%d vc2->0", fc))
  end

  if hold ~= 0 and holdSince >= 0 and (fc - holdSince) > 240 then
    if fc - lastStartTap > 40 then
      injStartUntil = fc + 2; lastInjStart = fc + 2; lastStartTap = fc
      log(string.format("INJ_START(hold-release) f=%d", fc))
    end
  elseif FAULT == 1 and m46 == 4 and hold == 0 and faultDone == 0 and playFrames >= 600 then
    -- DEFECT-FIRST GATE: simulate the reported fault (spurious START in play)
    injStartUntil = fc + 2; lastInjStart = fc + 2
    faultDone = 1; faultRelease = fc + 240; faultPress = fc
    log(string.format("FAULT_INJECT_START f=%d (simulated spurious START in play)", fc))
  elseif FAULT == 1 and faultDone == 1 and fc >= faultRelease and faultRelease > 0 then
    injStartUntil = fc + 2; lastInjStart = fc + 2; faultRelease = -1
    faultUnpause = fc
    log(string.format("FAULT_UNPAUSE f=%d", fc))
  elseif m46 ~= 4 and m46 ~= 3 and hold == 0 then
    if fc - lastStartTap > 45 then
      injStartUntil = fc + 2; lastInjStart = fc + 2; lastStartTap = fc
    end
  elseif m46 == 4 and hold == 0 then
    if fc > actUntil then
      local r = math.random(100)
      if     r <= 25 then curAct = "left"
      elseif r <= 50 then curAct = "right"
      elseif r <= 65 then curAct = "a"
      elseif r <= 75 then curAct = "b"
      elseif r <= 85 then curAct = "down"
      else                curAct = nil end
      actUntil = fc + math.random(4, 10)
    end
  end

  if fc % 1800 == 0 then
    log(string.format(
      "HB f=%d m46=%d games=%d goes=%d dones=%d hold=%d ttl=%d studyVis=%d unexp=%d spontStart=%d dmaAnom=%d pauseExecF=%d",
      fc, m46, games, cop.goes, cop.dones, hold, ttl, studyVisFrames, studyUnexpected,
      spontStartFrames, dmaAnomalies, pauseExecFrames))
  end

  if fc >= MAXF then
    summary("maxf")
    csvf:close(); logf:flush()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("BOOT fault=%d endg=%d maxf=%d seed=%d out=%s", FAULT, ENDG, MAXF, SEED, OUT))
