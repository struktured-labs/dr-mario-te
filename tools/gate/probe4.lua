-- probe4.lua -- WHY does DRMMC1RST wedge the cart? Diagnostics on the simplest failing arm.
--
-- Established already: the mechanism is fixed (0 mixed PRG loads) but the cart enters play and
-- never leaves mode 4, and d-mmc1only (RTIVEC OFF) strobes the copro GO line ZERO times. The
-- "forced PRG mode 3 remaps the high bank" story is REFUTED -- bank1 and bank3 are byte-exact
-- duplicates in that build (verified on the ROM), so _sel(0) and _sel(2) map identically under
-- mode 3 and under 32KB mode.
--
-- So this separates the remaining possibilities:
--   * $43   game frame counter  -- is the GAME still running, or is the whole cart frozen?
--   * $6147 NAV_T               -- INC'd every driver hook: is the HOOK still being called?
--   * $6176 BUSY                -- the re-entrancy guard. Latched => every hook bails at the door.
--   * $6161/$6162 ARMED2/WDOG2  -- P2 search state: armed and waiting, or never armed?
--   * MMC1 control register     -- modelled, incl. the bit-7 `control |= $0C` side effect, and
--                                 the PRG bank actually selected by each load.
-- Env: P4_OUT P4_MAXF P4_TAG
local OUT  = os.getenv("P4_OUT")  or "."
local MAXF = tonumber(os.getenv("P4_MAXF") or "1200")
local TAG  = os.getenv("P4_TAG") or "probe4"
local DLAT = tonumber(os.getenv("P4_DLAT") or "34")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/probe4.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local frame = 0
local events = {}
local function ev(s) events[#events + 1] = s end

-- ---------------- MMC1 model incl. control register ----------------
local control, prgbank, chr0, chr1 = 0x0C, 0, 0, 0   -- power-on control is commonly $0C (mode 3)
local sr_count, sr_val = 0, 0
local loadLog, nloads = {}, 0
emu.addMemoryCallback(function(addr, value)
  if value >= 0x80 then
    sr_count = 0; sr_val = 0
    control = control | 0x0C                       -- the MMC1.sv:110 side effect
    if #loadLog < 40 then
      loadLog[#loadLog + 1] = string.format("f=%d RESET  control|=0x0C -> $%02X", frame, control)
    end
    return
  end
  sr_val = sr_val | ((value & 1) << sr_count)
  sr_count = sr_count + 1
  if sr_count == 5 then
    local reg = math.floor(addr / 8192) % 4
    if reg == 0 then control = sr_val
    elseif reg == 1 then chr0 = sr_val
    elseif reg == 2 then chr1 = sr_val
    else prgbank = sr_val end
    nloads = nloads + 1
    if #loadLog < 40 then
      local prgmode = (control >> 2) & 3
      loadLog[#loadLog + 1] = string.format(
        "f=%d LOAD reg=%d val=$%02X  control=$%02X (prgmode=%d) prgbank=%d",
        frame, reg, sr_val, control, prgmode, prgbank)
    end
    sr_count = 0; sr_val = 0
  end
end, emu.callbackType.write, 0x8000, 0xFFFF)

-- ---------------- copro mailbox (so the cart can actually play) ----------------
local W = 0x5000
local S = { board = {}, done = false, go_f = -1, rcol = 0, ror = 0xFF,
            pending = false, need_snap = false, goes = 0, dones = 0 }
for i = 0, 127 do S.board[i] = 0xFF end
local curFrame = 0
local function brain(bd)
  local bc, bf = 0, 99
  for c = 0, 7 do
    local f = 0
    for r = 0, 15 do local v = bd[r * 8 + c]; if v ~= 0xFF and v ~= 0x00 then f = f + 1 end end
    if f < bf then bf = f; bc = c end
  end
  return bc, 0
end
emu.addMemoryCallback(function()
  S.go_f = curFrame; S.done = false; S.pending = true; S.need_snap = true; S.ror = 0xFF; S.goes = S.goes + 1
  ev(string.format("GO f=%d (#%d)", curFrame, S.goes))
end, emu.callbackType.write, W + 0x84)
emu.addMemoryCallback(function()
  if S.done then return 1 end
  if S.pending and not S.need_snap and (curFrame - S.go_f) >= DLAT then
    local c, o = brain(S.board); S.rcol = c % 8; S.ror = o % 4
    S.done = true; S.pending = false; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)

-- ---------------- input (mode-4 guarded) ----------------
local inCur, inUntil, modeCache = nil, -1, -1
-- ---- #131/#135 START-leak guard (adopted from probe_rotwedge; gate gate_d135_adopt.sh) ----
-- modeCache is sampled once per frame at endFrame, but this poll runs in NMI at the TOP of the
-- frame and the ROM advances 8->4 LATER in that same frame.  A press permitted here at mode 8 is
-- therefore still in the P1 newly-pressed latch $F5 when the stock pause routine $978E runs,
-- already in mode 4.  $97A7 accepts it, the match pauses at spawn, and on a P1-native cart that
-- pause is UNEXITABLE (#133) -- the run wedges forever.  Mode 8 is the only predecessor of 4.
-- D135_LEAK=1 restores the pre-fix behaviour: that is the KILLED MUTANT, and it must make
-- leaked > 0.  `blocked` is the non-vacuity control -- a fixed run that never blocked anything
-- did not exercise the guard, and the gate FAILS it rather than reading it as clean.
local D135_LEAK = (os.getenv("D135_LEAK") == "1")
local D135_OUT  = os.getenv("D135_OUT")
local d135_blocked, d135_leaked = 0, 0
local function d135_report()
  if not D135_OUT then return end
  local f = io.open(D135_OUT .. "/d135_census.txt", "w")
  if not f then return end
  f:write(string.format("D135 blocked=%d leaked=%d guard=%s\n",
    d135_blocked, d135_leaked, D135_LEAK and "OFF" or "ON"))
  f:close()
end
d135_report()   -- write at load, so "probe never ran" is distinguishable from "no hazard seen"
local function d135_block(i)
  local live = emu.read(0x46, emu.memType.nesMemory, false)
  if not (live == 8 or (live == 4 and i.start)) then return false end
  if D135_LEAK then
    d135_leaked = d135_leaked + 1
    if d135_leaked <= 10 or d135_leaked % 500 == 0 then d135_report() end
    return false
  end
  d135_blocked = d135_blocked + 1
  if d135_blocked <= 10 or d135_blocked % 500 == 0 then d135_report() end
  return true
end
emu.addEventCallback(function()
  if inCur and frame < inUntil and modeCache ~= 4 and not d135_block(inCur) then
    emu.setInput(inCur, 0)
  end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

local lvlPoked, seedPoked, round, prevMode = false, -1, 0, -1
local lastNav, navStuck = -1, 0
local csv = io.open(OUT .. "/state.csv", "w")
csv:write("frame,mode,f43,nav_t,busy,armed2,wdog2,match,vc1,control,prgmode,prgbank,goes\n")

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    if #events > 0 then for _, s in ipairs(events) do log(s) end; events = {} end
    local mode = rd(0x46); modeCache = mode
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end
    local navt = rd(0x6147)
    if navt == lastNav then navStuck = navStuck + 1 else navStuck = 0; lastNav = navt end

    if frame % 2 == 0 or mode ~= prevMode then
      csv:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", frame, mode,
        rd(0x43), navt, rd(0x6176), rd(0x6161), rd(0x6162), rd(0x6164), rd(0x0324),
        control, (control >> 2) & 3, prgbank, S.goes))
    end
    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d  f43=%d nav_t=%d BUSY=%d ARMED2=%d WDOG2=%d goes=%d",
        frame, prevMode, mode, rd(0x43), navt, rd(0x6176), rd(0x6161), rd(0x6162), S.goes))
      prevMode = mode
    end
    if mode ~= 4 then
      if mode >= 1 and mode <= 3 then
        if not lvlPoked then
          if rd(0x0316) ~= 11 then wr(0x0316, 11) end
          if rd(0x0396) ~= 11 then wr(0x0396, 11) end
          wr(0x96, 11); wr(0x45, 1); lvlPoked = true
        end
        if seedPoked ~= round then wr(0x17, 114); wr(0x18, 57); seedPoked = round end
        if frame % 12 == 0 then press({ start = true }, 4) end
      else
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      return
    end
    if lvlPoked then lvlPoked = false; round = round + 1 end
  end)
  if not ok then log("ERR " .. tostring(err)) end
  if frame >= MAXF then
    log("---- first MMC1 register loads ----")
    for _, s in ipairs(loadLog) do log("   " .. s) end
    log(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d loads=%d " ..
      "END: mode=%d f43=%d nav_t=%d navStuckFrames=%d BUSY=%d ARMED2=%d WDOG2=%d match=%d " ..
      "control=$%02X prgmode=%d prgbank=%d",
      TAG, frame, S.goes, S.dones, nloads, rd(0x46), rd(0x43), rd(0x6147), navStuck,
      rd(0x6176), rd(0x6161), rd(0x6162), rd(0x6164), control, (control >> 2) & 3, prgbank))
    csv:close(); logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe4 start tag=%s maxf=%d", TAG, MAXF))
