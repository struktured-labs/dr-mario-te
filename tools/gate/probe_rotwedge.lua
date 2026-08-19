-- ============================================================================
-- probe_rotwedge.lua -- #132 MECHANISM probe.
--
-- QUESTION: when the constant-orient sweep publishes copro orient 3 (= game
-- orient 2) and P2 freezes at the spawn row, WHICH component stopped?
--   H1  the game rejected the rotation (stock collision rules at row 0)
--   H2  the driver stopped emitting the A press
--   H3  gravity is pinned (someone writes GRAV_P2)
--   H4  the game's per-player update is not running at all for P2
--   H5  the whole CPU/game is wedged (P1 frozen too)
-- These are mutually distinguishable ONLY with P1's mirror state, the gravity
-- counters, the raw input bytes and a PC census -- none of which the framedense
-- CSV carries.  So this probe logs all of them, and on stall detection dumps a
-- PC histogram + both boards.
--
-- The publisher is a straight copy of probe_framedense.lua's arm A with the
-- FD_ORIENT knob forced, so the stimulus is identical to the run being
-- explained.  RW_ORIENT is REQUIRED (no default): the whole point is the
-- orient contrast, and a defaulted stimulus is an unattributable log.
--
-- Env: RW_OUT RW_TAG RW_W RW_ORIENT   (RW_MAXF RW_DLAT RW_SEED optional)
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then
    error("\n*** " .. name .. " IS REQUIRED. Refusing to run.\n", 0)
  end
  return v
end
local OUT    = need("RW_OUT")
local TAG    = need("RW_TAG")
local W      = tonumber(need("RW_W"))
local ORIENT = tonumber(need("RW_ORIENT"))
if ORIENT < 0 or ORIENT > 3 then error("RW_ORIENT must be 0..3", 0) end
local MAXF  = tonumber(os.getenv("RW_MAXF") or "20000")
local DLAT  = tonumber(os.getenv("RW_DLAT") or "34")
local SEED  = tonumber(os.getenv("RW_SEED") or "114")
local STALLN = tonumber(os.getenv("RW_STALLN") or "300")   -- frames of frozen P2 py before we declare a wedge

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/rotwedge.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end
local csvf = io.open(OUT .. "/frames.csv", "w")
csvf:write("frame,mode,f43,tgt_o2,tgt_c2,rot_done2,armed2,pend2,delay2,stk2," ..
           "p1x,p1y,p1o,p1step,p1grav,p2x,p2y,p2o,p2step,p2grav," ..
           "f5,f6,f7,f8,p2c a,p2cb,served_or\n")

-- ---- driver symbols ----
local TGT_C2, TGT_O2 = 0x6152, 0x6153
local PEND2, DELAY2  = 0x614F, 0x615F
local ARMED2         = 0x6161
local ROT_DONE2      = 0x616E
local STK2           = 0x615B   -- P2 stagnation counter (patch_cartridge_copro.py:53)

-- ---- game symbols ----
-- P1 mirror base $0300, P2 mirror base $0380.  x=+05 y=+06 step=+07 grav=+12 orient=+25.
local P1X, P1Y, P1STEP, P1GRAV, P1O = 0x0305, 0x0306, 0x0307, 0x0312, 0x0325
local P2X, P2Y, P2STEP, P2GRAV, P2O = 0x0385, 0x0386, 0x0387, 0x0392, 0x03A5

local frame, curFrame = 0, 0

-- ================= Lua copro (identical publisher to framedense arm A) ======
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

-- ================= PC census (H5: is the CPU even running the game?) ========
-- Sampled once per frame at endFrame is useless (always the same place), so we
-- sample inside a memory-read callback on a hot game address instead: every
-- read of the P2 mirror x byte, which the falling-pill handler touches.  If the
-- handler is not running, this callback stops firing -- and THAT is the signal.
local p2x_reads, p1x_reads = 0, 0
emu.addMemoryCallback(function() p2x_reads = p2x_reads + 1 end, emu.callbackType.read, P2X)
emu.addMemoryCallback(function() p1x_reads = p1x_reads + 1 end, emu.callbackType.read, P1X)
-- rotation-handler entry census: $8E2B is fallingPill_checkRotate (dr-mario-rotation-mechanism).
local rot_entries = 0
emu.addMemoryCallback(function() rot_entries = rot_entries + 1 end, emu.callbackType.exec, 0x8E2B)
-- $A5 orientation write census: DEC/INC $A5 both write it.
local a5_writes = 0
emu.addMemoryCallback(function() a5_writes = a5_writes + 1 end, emu.callbackType.write, 0x00A5)

-- ================= input =================
local modeCache = -1
local inCur, inUntil = nil, -1
emu.addEventCallback(function()
  if inCur and frame < inUntil and modeCache ~= 4 then emu.setInput(inCur, 0) end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

local prevMode, lvlPoked, seedPokedRound, round = -1, false, -1, 0
local frozen, lastPy, wedges = 0, -1, 0
local wedgeDumped = false
local pr_prev, p1r_prev, rot_prev, a5_prev = 0, 0, 0, 0
-- ROTATION-BUTTON CENSUS (#114). $F6 is P2's RAW pad byte; the driver writes $80 (A = DEC $A5
-- = CCW) or, on a DRROTDIR cart, $40 (B = INC $A5 = CW).  Counting them is the NOT-INERT check:
-- a DRROTDIR=0 cart must show pressB == 0 by construction, so this cannot pass vacuously.
local pressA, pressB = 0, 0

local function dump_board(base, name)
  for r = 0, 15 do
    local s = {}
    for c = 0, 7 do s[#s + 1] = string.format("%02X", rd(base + r * 8 + c)) end
    log(string.format("  %s r%02d %s", name, r, table.concat(s, " ")))
  end
end

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
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
    csvf:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
      frame, mode, rd(0x43), rd(TGT_O2), rd(TGT_C2), rd(ROT_DONE2), rd(ARMED2), rd(PEND2), rd(DELAY2), rd(STK2),
      rd(P1X), rd(P1Y), rd(P1O), rd(P1STEP), rd(P1GRAV),
      rd(P2X), py, rd(P2O), rd(P2STEP), rd(P2GRAV),
      rd(0xF5), rd(0xF6), rd(0xF7), rd(0xF8), rd(0x0381), rd(0x0382), S.ror))

    local f6 = rd(0xF6)
    if f6 == 0x80 then pressA = pressA + 1 elseif f6 == 0x40 then pressB = pressB + 1 end

    if py == lastPy then frozen = frozen + 1 else frozen = 0; lastPy = py end
    if frozen == STALLN and not wedgeDumped then
      wedgeDumped = true; wedges = wedges + 1
      log(string.format("=== WEDGE f=%d frozen=%d ===", frame, frozen))
      log(string.format("  mode=%d f43=%d TGT_O2=%d TGT_C2=%d ROT_DONE2=%d ARMED2=%d PEND2=%d DELAY2=%d STK2=%d served_or=%d",
        mode, rd(0x43), rd(TGT_O2), rd(TGT_C2), rd(ROT_DONE2), rd(ARMED2), rd(PEND2), rd(DELAY2), rd(STK2), S.ror))
      log(string.format("  P1 x=%d y=%d o=%d step=%d grav=%d   P2 x=%d y=%d o=%d step=%d grav=%d",
        rd(P1X), rd(P1Y), rd(P1O), rd(P1STEP), rd(P1GRAV), rd(P2X), py, rd(P2O), rd(P2STEP), rd(P2GRAV)))
      log(string.format("  raw inputs F5=%02X F6=%02X F7=%02X F8=%02X  zp 5B=%02X 5C=%02X A5=%02X 92=%02X",
        rd(0xF5), rd(0xF6), rd(0xF7), rd(0xF8), rd(0x5B), rd(0x5C), rd(0xA5), rd(0x92)))
      log(string.format("  counters(this frame vs 1 frame ago) p2x_reads=%d(+%d) p1x_reads=%d(+%d) rot8E2B=%d(+%d) a5_writes=%d(+%d)",
        p2x_reads, p2x_reads - pr_prev, p1x_reads, p1x_reads - p1r_prev,
        rot_entries, rot_entries - rot_prev, a5_writes, a5_writes - a5_prev))
      dump_board(0x0500, "P2")
      dump_board(0x0400, "P1")
    end
    pr_prev, p1r_prev, rot_prev, a5_prev = p2x_reads, p1x_reads, rot_entries, a5_writes
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF then
    log(string.format("SUMMARY tag=%s orient=%d frames=%d goes=%d dones=%d wedges=%d " ..
        "p2x_reads=%d p1x_reads=%d rot8E2B=%d a5_writes=%d pressA=%d pressB=%d",
        TAG, ORIENT, frame, S.goes, S.dones, wedges, p2x_reads, p1x_reads, rot_entries, a5_writes, pressA, pressB))
    csvf:flush(); csvf:close(); logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("rotwedge start tag=%s orient=%d out=%s w=$%04X maxf=%d dlat=%d seed=%d",
    TAG, ORIENT, OUT, W, MAXF, DLAT, SEED))
