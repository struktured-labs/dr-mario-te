-- ============================================================================
-- probe_rotpc.lua -- #132 step 2: WHERE is the CPU parked during the wedge?
--
-- probe_rotwedge.lua established that at the wedge BOTH players are frozen
-- (x=3 y=15 o=0 step=0 grav=0), the rotation handler $8E2B is never entered,
-- and $A5 is never written -- i.e. the game's play update is not running while
-- the NMI plainly is.  That rules out "the rotation was rejected" and points at
-- the main loop.  This probe answers WHERE.
--
-- METHOD: identical stimulus and wedge detector; on detection, install a
-- FULL-RANGE exec callback and histogram the program counter for RW_PCFRAMES
-- frames, at both page ($xx00) and exact-address granularity, then dump and
-- stop.  The range callback is installed ONLY at that point: registering it up
-- front costs a callback per instruction for the whole run.
--
-- CONTROL (required, RW_PCCTL=1): install the census at a FIXED frame during
-- HEALTHY play instead of at a wedge.  Without it a PC histogram has never been
-- shown to look different when nothing is wrong, and "the CPU is in the play
-- loop" would be unfalsifiable.
--
-- Env: RP_OUT RP_TAG RP_W RP_ORIENT  (RP_MAXF RP_DLAT RP_SEED RP_STALLN
--      RP_PCFRAMES RP_CTLFRAME optional; RP_CTLFRAME>0 selects control mode)
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then error("\n*** " .. name .. " IS REQUIRED.\n", 0) end
  return v
end
local OUT    = need("RP_OUT")
local TAG    = need("RP_TAG")
local W      = tonumber(need("RP_W"))
local ORIENT = tonumber(need("RP_ORIENT"))
local MAXF     = tonumber(os.getenv("RP_MAXF") or "20000")
local DLAT     = tonumber(os.getenv("RP_DLAT") or "34")
local SEED     = tonumber(os.getenv("RP_SEED") or "114")
local STALLN   = tonumber(os.getenv("RP_STALLN") or "300")
local PCFRAMES = tonumber(os.getenv("RP_PCFRAMES") or "40")
local CTLFRAME = tonumber(os.getenv("RP_CTLFRAME") or "0")   -- >0 => control mode

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/rotpc.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local TGT_C2, TGT_O2 = 0x6152, 0x6153
local PEND2, DELAY2  = 0x614F, 0x615F
local ARMED2, ROT_DONE2 = 0x6161, 0x616E
local P1X, P1Y, P1STEP, P1GRAV, P1O = 0x0305, 0x0306, 0x0307, 0x0312, 0x0325
local P2X, P2Y, P2STEP, P2GRAV, P2O = 0x0385, 0x0386, 0x0387, 0x0392, 0x03A5

local frame, curFrame = 0, 0

-- ---- Lua copro publisher (same as probe_rotwedge.lua) ----
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

-- ================= the PC census =================
local censusOn, censusInstalled = false, false
local pageHist, exactHist, censusN = {}, {}, 0
local function census_cb(addr)
  if not censusOn then return end
  censusN = censusN + 1
  local p = math.floor(addr / 256)
  pageHist[p] = (pageHist[p] or 0) + 1
  exactHist[addr] = (exactHist[addr] or 0) + 1
end
local function install_census()
  if censusInstalled then return end
  censusInstalled = true
  emu.addMemoryCallback(census_cb, emu.callbackType.exec, 0x8000, 0xFFFF)
  emu.addMemoryCallback(census_cb, emu.callbackType.exec, 0x6000, 0x7FFF)
  censusOn = true
end
local function dump_census(why)
  censusOn = false
  log(string.format("=== PC CENSUS (%s) samples=%d over %d frames ===", why, censusN, PCFRAMES))
  local pages = {}
  for p, n in pairs(pageHist) do pages[#pages + 1] = { p, n } end
  table.sort(pages, function(a, b) return a[2] > b[2] end)
  for i = 1, math.min(#pages, 12) do
    log(string.format("  PAGE $%02X00  n=%d  (%.1f%%)", pages[i][1], pages[i][2], 100 * pages[i][2] / math.max(censusN, 1)))
  end
  local ex = {}
  for a, n in pairs(exactHist) do ex[#ex + 1] = { a, n } end
  table.sort(ex, function(a, b) return a[2] > b[2] end)
  for i = 1, math.min(#ex, 24) do
    log(string.format("  PC $%04X  n=%d  (%.2f%%)", ex[i][1], ex[i][2], 100 * ex[i][2] / math.max(censusN, 1)))
  end
  log(string.format("  distinct pages=%d distinct PCs=%d", #pages, #ex))
end

local function dump_state(why)
  log(string.format("=== %s f=%d ===", why, frame))
  log(string.format("  mode=%d f43=%d TGT_O2=%d TGT_C2=%d ROT_DONE2=%d ARMED2=%d PEND2=%d DELAY2=%d served_or=%d",
    rd(0x46), rd(0x43), rd(TGT_O2), rd(TGT_C2), rd(ROT_DONE2), rd(ARMED2), rd(PEND2), rd(DELAY2), S.ror))
  log(string.format("  P1 x=%d y=%d o=%d step=%d grav=%d   P2 x=%d y=%d o=%d step=%d grav=%d",
    rd(P1X), rd(P1Y), rd(P1O), rd(P1STEP), rd(P1GRAV), rd(P2X), rd(P2Y), rd(P2O), rd(P2STEP), rd(P2GRAV)))
  log(string.format("  F5=%02X F6=%02X F7=%02X F8=%02X  5B=%02X 5C=%02X A5=%02X 92=%02X  BUSY/NAV $6149=%02X",
    rd(0xF5), rd(0xF6), rd(0xF7), rd(0xF8), rd(0x5B), rd(0x5C), rd(0xA5), rd(0x92), rd(0x6149)))
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
local censusStart, finished = -1, false

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

    if censusStart < 0 then
      local trigger = false
      if CTLFRAME > 0 then
        trigger = (frame >= CTLFRAME)                 -- CONTROL: census healthy play
      else
        trigger = (frozen >= STALLN)                  -- WEDGE
      end
      if trigger then
        dump_state(CTLFRAME > 0 and "CONTROL (healthy play)" or "WEDGE")
        censusStart = frame; install_census()
      end
    elseif frame - censusStart >= PCFRAMES then
      dump_census(CTLFRAME > 0 and "control" or "wedge")
      dump_state("post-census")
      log(string.format("SUMMARY tag=%s orient=%d mode=%s frames=%d goes=%d dones=%d censusN=%d",
          TAG, ORIENT, CTLFRAME > 0 and "CONTROL" or "WEDGE", frame, S.goes, S.dones, censusN))
      finished = true; logf:flush(); emu.stop(0)
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF and not finished then
    log(string.format("SUMMARY tag=%s orient=%d mode=%s frames=%d goes=%d dones=%d censusN=%d NO_TRIGGER",
        TAG, ORIENT, CTLFRAME > 0 and "CONTROL" or "WEDGE", frame, S.goes, S.dones, censusN))
    finished = true; logf:flush(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("rotpc start tag=%s orient=%d w=$%04X maxf=%d ctlframe=%d pcframes=%d",
    TAG, ORIENT, W, MAXF, CTLFRAME, PCFRAMES))
