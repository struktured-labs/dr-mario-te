-- ============================================================================
-- probe_d131trace.lua -- #131 step 3: WHICH BRANCH does the dispatcher take?
--
-- probe_rotpc.lua's PC histogram showed the wedge executes a strict SUBSET of
-- healthy play's pages and parks 81.6% of samples in the frame-sync wait at
-- $B662.  A histogram cannot show control flow, so it cannot name the gate.
-- This probe records a LINEAR, ORDERED instruction trace of a whole frame at
-- the same trigger point, so the divergence can be read directly.
--
-- The main loop is $8148: JSR $8157 / JSR $978E / JSR $B654 / JSR $8712 /
-- JMP $8148, and $8157 is LDA $46 + the $B8AC jump-table trampoline (word
-- table at $815C, index = mode).  The trace must show whether the trampoline
-- is reached at all, and where the mode-4 handler returns early.
--
-- CONTROL (required, DT_CTLFRAME>0): the identical trace during HEALTHY play.
-- Without it "the loop dispatches nothing" is unfalsifiable -- a trace of a
-- working frame is what makes the wedge trace's missing region visible.
--
-- Env: DT_OUT DT_TAG DT_W DT_ORIENT (DT_MAXF DT_DLAT DT_SEED DT_STALLN
--      DT_TRFRAMES DT_CTLFRAME optional; DT_CTLFRAME>0 selects control mode)
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then error("\n*** " .. name .. " IS REQUIRED.\n", 0) end
  return v
end
local OUT    = need("DT_OUT")
local TAG    = need("DT_TAG")
local W      = tonumber(need("DT_W"))
local ORIENT = tonumber(need("DT_ORIENT"))
local MAXF     = tonumber(os.getenv("DT_MAXF") or "20000")
local DLAT     = tonumber(os.getenv("DT_DLAT") or "34")
local SEED     = tonumber(os.getenv("DT_SEED") or "114")
local STALLN   = tonumber(os.getenv("DT_STALLN") or "300")
local TRFRAMES = tonumber(os.getenv("DT_TRFRAMES") or "2")
local CTLFRAME = tonumber(os.getenv("DT_CTLFRAME") or "0")
local TRCAP    = tonumber(os.getenv("DT_TRCAP") or "400000")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/d131trace.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local TGT_C2, TGT_O2 = 0x6152, 0x6153
local PEND2, DELAY2  = 0x614F, 0x615F
local ARMED2, ROT_DONE2 = 0x6161, 0x616E
local P1X, P1Y, P1STEP, P1GRAV, P1O = 0x0305, 0x0306, 0x0307, 0x0312, 0x0325
local P2X, P2Y, P2STEP, P2GRAV, P2O = 0x0385, 0x0386, 0x0387, 0x0392, 0x03A5

local frame, curFrame = 0, 0

-- ---- Lua copro publisher (identical to probe_rotpc.lua) ----
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
    S.rcol = brain_col(S.board) % 8; S.ror = ORIENT
    S.done = true; S.pending = false; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return 0xFF   end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return 0xFF   end, emu.callbackType.read, W + 0x88)

-- ================= the linear trace =================
local traceOn, traceInstalled = false, false
local tr, trN, trOver = {}, 0, false
local function trace_cb(addr)
  if not traceOn then return end
  if trN >= TRCAP then trOver = true; return end
  trN = trN + 1; tr[trN] = addr
end
local function install_trace()
  if traceInstalled then return end
  traceInstalled = true
  emu.addMemoryCallback(trace_cb, emu.callbackType.exec, 0x8000, 0xFFFF)
  emu.addMemoryCallback(trace_cb, emu.callbackType.exec, 0x6000, 0x7FFF)
end
-- frame markers so the dump can be split per frame
local marks = {}

local function dump_trace(why)
  traceOn = false
  log(string.format("=== TRACE (%s) n=%d over %d frames capped=%s ===", why, trN, TRFRAMES, tostring(trOver)))
  for i = 1, #marks do log(string.format("  FRAMEMARK idx=%d frame=%d", marks[i][1], marks[i][2])) end
  -- run-length encode consecutive repeats of the same PC to keep this readable
  local out, i = {}, 1
  while i <= trN do
    local a, j = tr[i], i
    while j < trN and tr[j + 1] == a do j = j + 1 end
    local n = j - i + 1
    out[#out + 1] = (n > 1) and string.format("%04X x%d", a, n) or string.format("%04X", a)
    i = j + 1
  end
  log(string.format("  RLE entries=%d", #out))
  -- 8 per line
  local line = {}
  for k = 1, #out do
    line[#line + 1] = out[k]
    if #line == 8 then log("  T " .. table.concat(line, " ")); line = {} end
  end
  if #line > 0 then log("  T " .. table.concat(line, " ")) end
end

local function dump_state(why)
  log(string.format("=== %s f=%d ===", why, frame))
  log(string.format("  mode=%d f43=%d TGT_O2=%d TGT_C2=%d ROT_DONE2=%d ARMED2=%d PEND2=%d DELAY2=%d served_or=%d",
    rd(0x46), rd(0x43), rd(TGT_O2), rd(TGT_C2), rd(ROT_DONE2), rd(ARMED2), rd(PEND2), rd(DELAY2), S.ror))
  log(string.format("  P1 x=%d y=%d o=%d step=%d grav=%d   P2 x=%d y=%d o=%d step=%d grav=%d",
    rd(P1X), rd(P1Y), rd(P1O), rd(P1STEP), rd(P1GRAV), rd(P2X), rd(P2Y), rd(P2O), rd(P2STEP), rd(P2GRAV)))
  log(string.format("  F5=%02X F6=%02X F7=%02X F8=%02X  5B=%02X 5C=%02X A5=%02X 92=%02X  BUSY/NAV $6149=%02X",
    rd(0xF5), rd(0xF6), rd(0xF7), rd(0xF8), rd(0x5B), rd(0x5C), rd(0xA5), rd(0x92), rd(0x6149)))
  -- zero page + the mode-adjacent bytes, so the gate candidate is in the record
  local zp = {}
  for a = 0x00, 0xFF do zp[#zp + 1] = string.format("%02X", rd(a)) end
  log("  ZP " .. table.concat(zp, ""))
  local p7 = {}
  for a = 0x0700, 0x073F do p7[#p7 + 1] = string.format("%02X", rd(a)) end
  log("  P7 " .. table.concat(p7, ""))
end

-- ================= input =================
local modeCache = -1
local inCur, inUntil = nil, -1
emu.addEventCallback(function()
  if inCur and frame < inUntil and modeCache ~= 4 then emu.setInput(inCur, 0) end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

local prevMode, lvlPoked, seedPokedRound, round = -1, false, -1, 0
local frozen, lastPy = 0, -1
local traceStart, finished = -1, false

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    if finished then return end
    local mode = rd(0x46); modeCache = mode
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end
    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d goes=%d dones=%d", frame, prevMode, mode, S.goes, S.dones))
      prevMode = mode
    end
    if mode ~= 4 then
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
      else
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      lastPy = -1; frozen = 0
      return
    end
    if lvlPoked then lvlPoked = false; round = round + 1 end

    local py = rd(P2Y)
    if py == lastPy then frozen = frozen + 1 else frozen = 0; lastPy = py end

    if traceStart < 0 then
      local trigger
      if CTLFRAME > 0 then trigger = (frame >= CTLFRAME) else trigger = (frozen >= STALLN) end
      if trigger then
        dump_state(CTLFRAME > 0 and "CONTROL (healthy play)" or "WEDGE")
        traceStart = frame; install_trace(); traceOn = true
        marks[#marks + 1] = { 0, frame }
      end
    elseif frame - traceStart >= TRFRAMES then
      dump_trace(CTLFRAME > 0 and "control" or "wedge")
      dump_state("post-trace")
      log(string.format("SUMMARY tag=%s orient=%d mode=%s frames=%d goes=%d dones=%d traceN=%d",
          TAG, ORIENT, CTLFRAME > 0 and "CONTROL" or "WEDGE", frame, S.goes, S.dones, trN))
      finished = true; logf:flush(); emu.stop(0)
    else
      marks[#marks + 1] = { trN, frame }
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF and not finished then
    log(string.format("SUMMARY tag=%s orient=%d mode=%s frames=%d goes=%d dones=%d traceN=%d NO_TRIGGER",
        TAG, ORIENT, CTLFRAME > 0 and "CONTROL" or "WEDGE", frame, S.goes, S.dones, trN))
    finished = true; logf:flush(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("d131trace start tag=%s orient=%d w=$%04X maxf=%d ctlframe=%d trframes=%d",
    TAG, ORIENT, W, MAXF, CTLFRAME, TRFRAMES))
