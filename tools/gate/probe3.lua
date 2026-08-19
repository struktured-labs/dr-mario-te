-- probe3.lua -- MMC1 shift-register MODEL + bank0/RAM-wipe canaries.
--
-- WHY NOT probe2's counter: probe2 flagged "a run of writes to one address whose length is not a
-- multiple of 5". DRMMC1RST prepends a bit-7 reset write to every _sel, making the driver's run
-- SIX writes long -- which that heuristic scores as a straddle. It would report the fix as the
-- defect. So this models the actual hardware instead of pattern-matching the write stream.
--
-- MMC1 (upstream MMC1.sv, which mapper 100 routes to, so this is cart-real):
--   * write to $8000-$FFFF
--   * value bit7 SET  -> shift register resets (count=0), control |= $0C   [PRG mode 3]
--   * value bit7 CLEAR-> shift in bit0; count++; on the 5th, LOAD the register selected by
--     address bits 14-13 of THAT FIFTH WRITE: 0=CTRL 1=CHR0 2=CHR1 3=PRG
--
-- THE HAZARD, stated exactly: a load whose five contributing writes did not all come from the
-- same address -- the base game's $DFFF (CHR1) sequence and the driver's $FFF0 (PRG) sequence
-- interleaving on the one shared register. A MIXED load into register 3 (PRG) is the
-- catastrophic case: it selects a garbage bank, maps unit 0, and the trampoline's next JSR $8000
-- lands in the base soft-entry -> RAM wipe -> title.
--
-- Env: P3_OUT P3_MAXF P3_DLAT P3_SEED P3_TAG
local OUT  = os.getenv("P3_OUT")  or "."
local MAXF = tonumber(os.getenv("P3_MAXF") or "3000")
local DLAT = tonumber(os.getenv("P3_DLAT") or "34")
local SEED = tonumber(os.getenv("P3_SEED") or "114")
local TAG  = os.getenv("P3_TAG") or "probe3"
local BOOTF = tonumber(os.getenv("P3_BOOTF") or "10")   -- frames <= this are "power-on"

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/probe3.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local frame = 0
local events = {}
local function ev(s) events[#events + 1] = s end

-- ---------------- MMC1 shift-register model ----------------
local REGNAME = { [0] = "CTRL", [1] = "CHR0", [2] = "CHR1", [3] = "PRG" }
local sr_count, sr_srcs = 0, {}
local loads, mixed_total, mixed_prg, mixed_boot = 0, 0, 0, 0
local resets = 0
local mixedLog = {}

emu.addMemoryCallback(function(addr, value)
  if value >= 0x80 then                      -- bit7: reset the shift register
    resets = resets + 1
    sr_count = 0; sr_srcs = {}
    return
  end
  sr_count = sr_count + 1
  sr_srcs[sr_count] = addr
  if sr_count == 5 then
    loads = loads + 1
    local reg = math.floor(addr / 8192) % 4  -- addr bits 14-13 of the FIFTH write
    local mixed = false
    for i = 2, 5 do if sr_srcs[i] ~= sr_srcs[1] then mixed = true end end
    if mixed then
      mixed_total = mixed_total + 1
      if frame <= BOOTF then mixed_boot = mixed_boot + 1 end
      local tag = ""
      if reg == 3 then
        if frame > BOOTF then mixed_prg = mixed_prg + 1 end
        tag = "  <<< MIXED LOAD INTO PRG -- THE CATASTROPHIC CASE"
      end
      if #mixedLog < 60 then
        local srcs = ""
        for i = 1, 5 do srcs = srcs .. string.format("$%04X ", sr_srcs[i]) end
        mixedLog[#mixedLog + 1] = string.format(
          "MIXEDLOAD f=%d reg=%s(%d) srcs=[ %s]%s%s",
          frame, REGNAME[reg], reg, srcs, (frame <= BOOTF and "  (power-on)" or ""), tag)
      end
    end
    sr_count = 0; sr_srcs = {}
  end
end, emu.callbackType.write, 0x8000, 0xFFFF)

-- ---------------- crash canaries ----------------
local soft8036 = 0
emu.addMemoryCallback(function()
  soft8036 = soft8036 + 1
  ev(string.format("*** BANK0 SOFT-ENTRY exec $8036 f=%d (#%d) ***", frame, soft8036))
end, emu.callbackType.exec, 0x8036)

local wipes, lastVC = 0, -1
emu.addMemoryCallback(function(addr, value)
  if value ~= lastVC then
    if lastVC > 0 and value == 0 then
      wipes = wipes + 1
      ev(string.format("!!! VC1 WIPE f=%d  %d -> 0 (#%d) !!!", frame, lastVC, wipes))
    end
    lastVC = value
  end
end, emu.callbackType.write, 0x0324)

-- BRK-loop canary for the RTIVEC/MMC1RST composition (killed mutant M3): the drafted-but-wrong
-- design vectors an ordinary game NMI into a driver stub while the BASE bank is mapped low, where
-- $A02E reads $00 = BRK, whose IRQ vector is the same stub -> unbreakable loop.
local brkhits = 0
emu.addMemoryCallback(function()
  brkhits = brkhits + 1
  if brkhits <= 5 then ev(string.format("### exec $A02E f=%d (#%d) -- BRK-loop watch ###", frame, brkhits)) end
end, emu.callbackType.exec, 0xA02E)

-- ---------------- copro mailbox ----------------
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

local lcg = SEED
local function nextrand() lcg = (lcg * 1103515245 + 12345) % 2147483648; return math.floor(lcg / 65536) % 256 end
local prevMode, lvlPoked, seedPoked, round = -1, false, -1, 0

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    if #events > 0 then
      for _, s in ipairs(events) do log(s) end
      events = {}
    end
    local mode = rd(0x46); modeCache = mode
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end
    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d match=%d hold=%d vc1=%d vc2=%d mixed=%d mixedPRG=%d soft=%d",
          frame, prevMode, mode, rd(0x6164), rd(0x6195), rd(0x0324), rd(0x03A4),
          mixed_total, mixed_prg, soft8036))
      prevMode = mode
    end
    if mode ~= 4 then
      if mode >= 1 and mode <= 3 then
        if not lvlPoked then
          if rd(0x0316) ~= 11 then wr(0x0316, 11) end
          if rd(0x0396) ~= 11 then wr(0x0396, 11) end
          wr(0x96, 11); wr(0x45, 1); lvlPoked = true
        end
        if seedPoked ~= round then
          local s1, s2 = nextrand(), nextrand()
          if s1 == 0 and s2 == 0 then s1 = 0x89 end
          wr(0x17, s1); wr(0x18, s2); seedPoked = round
        end
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
    for _, s in ipairs(mixedLog) do log(s) end
    log(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d sr_loads=%d sr_resets=%d " ..
        "MIXED_total=%d MIXED_boot=%d MIXED_PRG_nonboot=%d soft8036=%d wipes=%d brk_a02e=%d",
        TAG, frame, S.goes, S.dones, loads, resets, mixed_total, mixed_boot, mixed_prg,
        soft8036, wipes, brkhits))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe3 start tag=%s maxf=%d bootf=%d", TAG, MAXF, BOOTF))
