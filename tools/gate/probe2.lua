-- probe2.lua -- is the mid-match drop-to-title a BANK0 SOFT-ENTRY + RAM WIPE?
--
-- Field bug 5: live VS match -> 7 black frames -> unrequested TITLE, match gone, title then
-- alternates clean/corrupt with gameplay nametable fragments. Predicted mechanism (team-lead,
-- from the prestart autotest gate): MMC1 shift-register interleave -> corrupted PRG bank ->
-- bank0 soft-entry (LDX #0; JMP $8036) -> RAM wipe -> title.
--
-- My earlier fieldplay run already shows the candidate event: at f681 (v6c ship, first match)
-- $0046, $0400/$0500 and $0324/$03A4 all go to zero in one step while PRG-RAM survives. I
-- previously read "the CPU wrote $0046<-0" as excluding a reset -- that was wrong: a RAM-clear
-- loop writes $0046<-0 too. This probe distinguishes them directly.
--
-- INSTRUMENTS
--   * exec canary at $8036 (bank0 soft-entry target) and at $FF54 (the BUSY-guard wrapper)
--   * MMC1 serial-port write ring ($8000-$FFFF): addr+value+frame, dumped around the event.
--     The interleave signature is a 5-write sequence to one reg straddled by writes to another.
--   * write canary on $0324 (P1 virus count): 72->0 marks the wipe onset
--   * write canary on $61B0 (S2P_TTL) -- team-lead's random-STUDY observable
--   * write canary on $0046
-- All callbacks are pure Lua (no emu.* inside a memory callback).
local OUT  = os.getenv("PB_OUT")  or "."
local MAXF = tonumber(os.getenv("PB_MAXF") or "1200")
local DLAT = tonumber(os.getenv("PB_DLAT") or "34")
local SEED = tonumber(os.getenv("PB_SEED") or "114")
local TAG  = os.getenv("PB_TAG") or "probe2"

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/probe2.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local frame = 0
local events = {}
local function ev(s) events[#events + 1] = s end

-- ---- MMC1 serial-port write ring ----
local RING, RN = {}, 220
local rp = 0
local mmc1Writes = 0
-- STRADDLE COUNTER: MMC1 has ONE 5-bit shift register shared by all four config regs, so a
-- register load is exactly 5 consecutive writes. If a run of writes to one address ends on a
-- count that is not a multiple of 5 and the next write goes to a DIFFERENT address, the second
-- writer has interleaved into a half-loaded shift register -- the bits mix and the load lands
-- in the wrong register with the wrong value. That is the hazard; count every occurrence.
local lastAddr, runLen = -1, 0
local straddles, straddleLog = 0, {}
emu.addMemoryCallback(function(addr, value)
  mmc1Writes = mmc1Writes + 1
  if addr == lastAddr then
    runLen = runLen + 1
  else
    if lastAddr >= 0 and runLen % 5 ~= 0 then
      straddles = straddles + 1
      if #straddleLog < 40 then
        straddleLog[#straddleLog + 1] =
          string.format("STRADDLE f=%d: $%04X run=%d (not x5) then $%04X", frame, lastAddr, runLen, addr)
      end
    end
    lastAddr = addr; runLen = 1
  end
  rp = rp + 1
  RING[(rp - 1) % RN + 1] = string.format("f%d $%04X<-%02X", frame, addr, value)
end, emu.callbackType.write, 0x8000, 0xFFFF)

-- ---- exec canaries ----
local soft8036, ff54 = 0, 0
emu.addMemoryCallback(function()
  soft8036 = soft8036 + 1
  ev(string.format("*** BANK0 SOFT-ENTRY exec $8036 f=%d (#%d) ***", frame, soft8036))
end, emu.callbackType.exec, 0x8036)

-- ---- state canaries ----
local lastVC = -1
emu.addMemoryCallback(function(addr, value)
  if value ~= lastVC then
    if lastVC > 0 and value == 0 then
      ev(string.format("!!! VC1 WIPE f=%d  %d -> 0 !!!", frame, lastVC))
    end
    lastVC = value
  end
end, emu.callbackType.write, 0x0324)

local ttlWrites = 0
emu.addMemoryCallback(function(addr, value)
  ttlWrites = ttlWrites + 1
  ev(string.format("W S2P_TTL($61B0) f=%d <- %d", frame, value))
end, emu.callbackType.write, 0x61B0)

emu.addMemoryCallback(function(addr, value) ev(string.format("W MODE f=%d <- %d", frame, value)) end,
                      emu.callbackType.write, 0x0046)

-- ---- copro mailbox ----
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

-- ---- input (mode-4 guarded: zero input reaches live play) ----
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
local dumped = false

local function dump_ring(why)
  log("---- MMC1 serial-port write ring (oldest..newest) : " .. why .. " ----")
  local n = math.min(rp, RN)
  for k = 0, n - 1 do
    local idx = (rp - n + k) % RN + 1
    log("   " .. tostring(RING[idx]))
  end
  log("---- end ring (total mmc1-region writes so far: " .. mmc1Writes .. ") ----")
end

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
      log(string.format("MODE f=%d %d->%d match=%d hold=%d vc1=%d vc2=%d fill=%d/%d ttlw=%d soft8036=%d",
          frame, prevMode, mode, rd(0x6164), rd(0x6195), rd(0x0324), rd(0x03A4),
          (function() local n=0; for i=0,127 do local v=rd(0x0400+i); if v~=0 and v~=0xFF then n=n+1 end end; return n end)(),
          (function() local n=0; for i=0,127 do local v=rd(0x0500+i); if v~=0 and v~=0xFF then n=n+1 end end; return n end)(),
          ttlWrites, soft8036))
      -- the catastrophic transition: dump the mapper-write history that led into it
      if prevMode == 4 and mode ~= 4 and mode ~= 5 and not dumped then
        dumped = true
        dump_ring(string.format("mid-match %d->%d at f%d", prevMode, mode, frame))
      end
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
    for _, s in ipairs(straddleLog) do log(s) end
    log(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d soft8036=%d ttl_writes=%d " ..
        "mmc1_writes=%d STRADDLES=%d", TAG, frame, S.goes, S.dones, soft8036, ttlWrites,
        mmc1Writes, straddles))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe2 start tag=%s maxf=%d", TAG, MAXF))
