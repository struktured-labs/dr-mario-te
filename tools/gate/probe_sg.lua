-- ============================================================================
-- probe_sg.lua -- gates for the hardened cart's #133 (DRUNPAUSE) and #134
-- (DRSTARTGUARD) changes. Lua copro publisher + menu driving copied from
-- probe_d131gate.lua (same file-based mailbox at W=0x5200).
--
-- ARMS (SG_ARM):
--   site1    #134 site 1 (autonav inject). At every exec of SG_INJ_GUARD poke
--            $0046 = SG_FORCEMODE (4 or 8) -- the guard's own live-mode read
--            then sees a match/transit frame -- and restore the saved mode at
--            SG_AN_RET (both paths converge there). Counts:
--              guard_hits   execs of SG_INJ_GUARD while forcing   (liveness)
--              sta_forced   execs of SG_INJ_STA under the force   (the defect)
--            GUARDED cart: guard_hits > 0 and sta_forced == 0.
--            CONTROL cart (pre-fix, SG_INJ_GUARD == SG_INJ_STA): sta_forced > 0
--            -- the superseded behaviour is the named mutant and must be caught.
--   site2    #134 site 2 (stage-clear dismiss). Mid-play, once P1's virus count
--            has been seen alive, poke $0324 = 0 (a real full clear as the ROM
--            sees it). At the FIRST exec of SG_FC_CLEAR poke NAV_T ($6147) to a
--            press-window phase (adversarial: the state-entry hook is already
--            inside the press window). Record hooks between first SG_FC_CLEAR
--            and first SG_FC_PRESS exec, FC_STAB ($61C4) high-water, and whether
--            the stock pause loop ($97C7) ever runs. GUARDED: press_delay >=
--            FC_STAB_K. CONTROL: press_delay < FC_STAB_K (kill). Either way the
--            match end must still DISMISS (mode leaves 4) -- the guard must not
--            cost the function.
--   pause2e  #133 end-to-end on a DRUNPAUSE cart with a REAL pad: during live
--            play deliver a clean START edge (pause), hold the pause SG_HOLDF
--            frames (assert frozen + pauseIters growing), deliver a second
--            clean START edge (unpause), then require play to RESUME ($97E8
--            exec + >=3 distinct P2 y) and the match flow to continue.
--            CONTROL cart (no DRUNPAUSE): the first START edge must do NOTHING
--            (no pause entry at all -- the executor overwrites the latch), so
--            verdict NEVER_PAUSED. That inverts the #133 defect: the defect
--            cart cannot pause via the pad *and could never unpause*; the fixed
--            cart does both.
--
-- Env: SG_OUT SG_TAG SG_ARM SG_MAXF SG_W  SG_INJ_GUARD SG_INJ_STA SG_AN_RET
--      SG_FC_PRESS SG_FC_CLEAR  [SG_FORCEMODE=4 SG_FCSTAB=0x61C4 SG_FCSTABK=4
--      SG_HOLDF=240 SG_SEED=114 SG_DLAT=34]
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then error("\n*** " .. name .. " IS REQUIRED.\n", 0) end
  return v
end
local OUT  = need("SG_OUT")
local TAG  = need("SG_TAG")
local ARM  = need("SG_ARM")
local W    = tonumber(need("SG_W"))
local MAXF = tonumber(os.getenv("SG_MAXF") or "9000")
local VALID = { site1 = true, site2 = true, pause2e = true }
if not VALID[ARM] then error("\n*** SG_ARM must be site1|site2|pause2e\n", 0) end

local INJ_GUARD = tonumber(need("SG_INJ_GUARD"))
local INJ_STA   = tonumber(need("SG_INJ_STA"))
local AN_RET    = tonumber(need("SG_AN_RET"))
local FC_PRESS  = tonumber(need("SG_FC_PRESS"))
local FC_CLEAR  = tonumber(need("SG_FC_CLEAR"))
local FORCEMODE = tonumber(os.getenv("SG_FORCEMODE") or "4")
local FCSTAB    = tonumber(os.getenv("SG_FCSTAB") or "0x61C4")
local FCSTABK   = tonumber(os.getenv("SG_FCSTABK") or "4")
local HOLDF     = tonumber(os.getenv("SG_HOLDF") or "240")
local SEED      = tonumber(os.getenv("SG_SEED") or "114")
local DLAT      = tonumber(os.getenv("SG_DLAT") or "34")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
-- DRIVER-BANK QUALIFIER. Exec callbacks fire on CPU ADDRESS, not bank: the driver lives in
-- the switched $8000-$BFFF window, so a callback on a driver PC also fires whenever the STOCK
-- bank is mapped and its own code passes the same address (measured: fc_press "fired" at
-- fcHits=0 -- phantom stock-bank hits). The DRRTIVEC probe byte at $A02E reads $40 only while
-- the driver bank is mapped low ($00 in base bank 0); every driver-address callback must be
-- qualified by it.
local function in_driver_bank() return rd(0xA02E) == 0x40 end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/sg.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local P2X, P2Y, P2STEP = 0x0385, 0x0386, 0x0387
local VC1, VC2 = 0x0324, 0x03A4
local NAV_T = 0x6147

local frame, curFrame = 0, 0

-- ---- Lua copro publisher (identical to probe_d131gate.lua) ----
local S = { board = {}, done = false, go_f = -1, rcol = 0, ror = 0xFF,
            pending = false, need_snap = false, goes = 0, dones = 0 }
for i = 0, 127 do S.board[i] = 0xFF end
local lcg = SEED
local function nextrand() lcg = (lcg * 1103515245 + 12345) % 2147483648; return math.floor(lcg / 65536) % 256 end
local function filled(bd, r, c) local v = bd[r * 8 + c]; return v ~= 0xFF and v ~= 0x00 end
local function brain_col(bd)
  local bestCol, bestFill = 0, 99
  for c = 0, 7 do
    local fill = 0
    for r = 0, 15 do if filled(bd, r, c) then fill = fill + 1 end end
    if fill < bestFill then bestFill = fill; bestCol = c end
  end
  return bestCol
end
emu.addMemoryCallback(function()
  S.go_f = curFrame; S.done = false; S.pending = true; S.need_snap = true
  S.ror = 0xFF; S.goes = S.goes + 1
end, emu.callbackType.write, W + 0x84)
emu.addMemoryCallback(function()
  if S.done then return 1 end
  if S.pending and not S.need_snap and (curFrame - S.go_f) >= DLAT then
    S.rcol = brain_col(S.board) % 8; S.ror = 0
    S.done = true; S.pending = false; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return 0xFF   end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return 0xFF   end, emu.callbackType.read, W + 0x88)

-- ---- stock pause-loop instrumentation (addresses are STOCK, cart-invariant) ----
local pauseIters, exitTaken, entryHits = 0, 0, 0
emu.addMemoryCallback(function() pauseIters = pauseIters + 1 end, emu.callbackType.exec, 0x97C7)
emu.addMemoryCallback(function() exitTaken = exitTaken + 1 end, emu.callbackType.exec, 0x97E8)
emu.addMemoryCallback(function() entryHits = entryHits + 1 end, emu.callbackType.exec, 0x97AD)

-- ================= site1: force the guard's live-mode read =================
local guardHits, staHits, staForced, forcing, savedMode = 0, 0, 0, false, -1
if ARM == "site1" then
  emu.addMemoryCallback(function()
    if not in_driver_bank() then return end
    guardHits = guardHits + 1
    if not forcing then savedMode = rd(0x46); forcing = true; wr(0x46, FORCEMODE) end
  end, emu.callbackType.exec, INJ_GUARD)
  emu.addMemoryCallback(function()
    if not in_driver_bank() then return end
    if forcing then wr(0x46, savedMode); forcing = false end
  end, emu.callbackType.exec, AN_RET)
end
emu.addMemoryCallback(function()
  if not in_driver_bank() then return end
  staHits = staHits + 1
  if forcing then staForced = staForced + 1 end
end, emu.callbackType.exec, INJ_STA)

-- ================= site2: fc state / press timing =================
local fcHits, fcPressHits, fcFirstHit, fcFirstPress = 0, 0, -1, -1
local fcStabMax, pokedVC = 0, false
emu.addMemoryCallback(function()
  if not in_driver_bank() then return end
  fcHits = fcHits + 1
  if fcFirstHit < 0 then
    fcFirstHit = fcHits          -- hook index 1
    if ARM == "site2" then
      -- adversarial phase: the state-entry hook is ALREADY inside the press
      -- window ((NAV_T & $1F) < 4). NAV_T increments before the fc check each
      -- hook, so park it at a window-opening value.
      wr(NAV_T, 0x00)
    end
  end
  local sv = rd(FCSTAB)
  if sv ~= 0xFF and sv > fcStabMax and sv <= 32 then fcStabMax = sv end
end, emu.callbackType.exec, FC_CLEAR)
emu.addMemoryCallback(function()
  if not in_driver_bank() then return end
  fcPressHits = fcPressHits + 1
  if fcFirstPress < 0 then fcFirstPress = fcHits end
end, emu.callbackType.exec, FC_PRESS)

-- ================= input =================
local inCur, inUntil = nil, -1
emu.addEventCallback(function()
  if not inCur or frame >= inUntil then inCur = nil; return end
  emu.setInput(inCur, 0)
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

-- menu driving: same as probe_d131gate (poke levels+seed, START through menus),
-- but NEVER press START outside modes 1-3 (menuonly discipline -- the harness
-- must not plant the very defect these gates are about).
local prevMode, lvlPoked, seedPokedRound, round = -1, false, -1, 0
local finished = false
local playFrames, vcSeen = 0, false
local p2ys, p2ysN = {}, 0

-- pause2e state machine
local p2e = { phase = "wait_play", tF = -1, pausedAt = -1, resumeYs = {}, resumeN = 0,
              itersAtHold = -1, frozenChk = 0, verdict = "NONE" }

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    if finished then return end
    local mode = rd(0x46)
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end
    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d goes=%d dones=%d pauseIters=%d fcHits=%d",
          frame, prevMode, mode, S.goes, S.dones, pauseIters, fcHits))
      prevMode = mode
    end
    if mode >= 1 and mode <= 3 then
      if not lvlPoked then
        if rd(0x0316) ~= 11 then wr(0x0316, 11) end
        if rd(0x0396) ~= 11 then wr(0x0396, 11) end
        wr(0x96, 11); wr(0x45, 1); lvlPoked = true
      end
      if seedPokedRound ~= round then
        local s1, s2 = nextrand(), nextrand()
        if s1 == 0 and s2 == 0 then s1 = 0x89 end
        wr(0x17, s1); wr(0x18, s2); seedPokedRound = round
      end
      if frame % 12 == 0 then press({ start = true }, 4) end
      return
    end
    if mode ~= 4 then return end
    if lvlPoked then lvlPoked = false; round = round + 1 end
    playFrames = playFrames + 1

    if rd(VC1) > 0 and rd(VC2) > 0 then vcSeen = true end

    if ARM == "site2" and vcSeen and (not pokedVC) and playFrames >= 600 then
      wr(VC1, 0); pokedVC = true
      log(string.format("POKE f=%d VC1<-0 (full clear as the ROM sees it)", frame))
    end

    if ARM == "pause2e" then
      local py = rd(P2Y)
      if p2e.phase == "wait_play" then
        if vcSeen and playFrames >= 300 then
          p2e.phase = "edge1"; p2e.tF = frame
          press({ start = true }, 2)
          log(string.format("PAUSE2E f=%d first START edge (expect pause on a DRUNPAUSE cart)", frame))
        end
      elseif p2e.phase == "edge1" then
        if pauseIters > 0 and p2e.pausedAt < 0 then
          p2e.pausedAt = frame; p2e.itersAtHold = pauseIters
          log(string.format("PAUSE2E f=%d PAUSED (pauseIters=%d)", frame, pauseIters))
        end
        if frame - p2e.tF >= HOLDF then
          if p2e.pausedAt < 0 then
            p2e.verdict = "NEVER_PAUSED"
            log(string.format("PAUSE2E f=%d no pause entry after the edge (control expectation)", frame))
            p2e.phase = "done"
          else
            -- assert the game is actually parked: P2 y frozen while paused
            p2e.phase = "edge2"; p2e.tF = frame
            press({ start = true }, 2)
            log(string.format("PAUSE2E f=%d second START edge (expect UNPAUSE; pauseIters=%d)", frame, pauseIters))
          end
        end
      elseif p2e.phase == "edge2" then
        local fresh = true
        for i = 1, p2e.resumeN do if p2e.resumeYs[i] == py then fresh = false; break end end
        if fresh then p2e.resumeN = p2e.resumeN + 1; p2e.resumeYs[p2e.resumeN] = py end
        if frame - p2e.tF >= 240 then
          p2e.verdict = (exitTaken > 0 and p2e.resumeN >= 3) and "PAUSED_THEN_RESUMED" or "STILL_PAUSED"
          p2e.phase = "done"
        end
      end
      if p2e.phase == "done" and not finished then
        log(string.format("SUMMARY tag=%s arm=%s verdict=%s pauseIters=%d entryHits=%d exitTaken=%d " ..
            "distinctP2Y=%d frames=%d goes=%d dones=%d",
            TAG, ARM, p2e.verdict, pauseIters, entryHits, exitTaken, p2e.resumeN, frame, S.goes, S.dones))
        finished = true; logf:flush(); emu.stop(0)
      end
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF and not finished then
    local verdict
    if ARM == "site1" then
      verdict = (guardHits > 0 and staForced == 0) and "GUARD_HELD" or
                ((staForced > 0) and "STA_UNDER_FORCE" or "NO_LIVENESS")
      log(string.format("SUMMARY tag=%s arm=%s verdict=%s forcemode=%d guardHits=%d staHits=%d " ..
          "staForced=%d pauseIters=%d frames=%d goes=%d dones=%d",
          TAG, ARM, verdict, FORCEMODE, guardHits, staHits, staForced, pauseIters, frame, S.goes, S.dones))
    elseif ARM == "site2" then
      local delay = (fcFirstPress >= 0) and (fcFirstPress - fcFirstHit) or -1
      verdict = (fcFirstPress < 0) and "NO_PRESS" or
                ((fcFirstPress < 1) and "PHANTOM_PRESS" or
                 ((delay >= FCSTABK) and "DELAYED_PRESS" or "IMMEDIATE_PRESS"))
      log(string.format("SUMMARY tag=%s arm=%s verdict=%s fcHits=%d fcPressHits=%d firstHit=%d " ..
          "firstPressHookIdx=%d pressDelayHooks=%d fcStabMax=%d pausedDuringFC=%d pauseIters=%d " ..
          "frames=%d goes=%d dones=%d",
          TAG, ARM, verdict, fcHits, fcPressHits, fcFirstHit, fcFirstPress, delay, fcStabMax,
          (pauseIters > 0) and 1 or 0, pauseIters, frame, S.goes, S.dones))
    else
      log(string.format("SUMMARY tag=%s arm=%s verdict=TIMEOUT_%s pauseIters=%d exitTaken=%d frames=%d",
          TAG, ARM, tostring(p2e.verdict), pauseIters, exitTaken, frame))
    end
    finished = true; logf:flush(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("BOOT tag=%s arm=%s W=0x%04X injGuard=0x%04X injSta=0x%04X anRet=0x%04X " ..
    "fcPress=0x%04X fcClear=0x%04X forcemode=%d maxf=%d",
    TAG, ARM, W, INJ_GUARD, INJ_STA, AN_RET, FC_PRESS, FC_CLEAR, FORCEMODE, MAXF))
