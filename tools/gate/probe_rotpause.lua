-- ============================================================================
-- probe_rotpause.lua -- #132 step 3: is the "orient-2 livelock" a PAUSE the
-- HARNESS caused?
--
-- probe_rotwedge.lua showed that at the wedge BOTH players are frozen (x=3
-- y=15 o=0 step=0 grav=0), $8E2B is never entered, $A5 is never written, and
-- the NMI is plainly still running.  Nothing about that is P2-specific or
-- rotation-specific -- it is the whole play update stopping, which is exactly
-- what PAUSE looks like.
--
-- And the harness can cause a pause.  probe_framedense.lua (and rotwedge,
-- copied from it) drives menus by pressing START, gated on `modeCache ~= 4` --
-- a value cached ONCE PER FRAME at endFrame.  On the frame the game enters
-- mode 4, modeCache still holds the previous mode, so START is delivered INTO
-- the first frames of play.  Either player's START pauses Dr. Mario, and the
-- harness then stops pressing START (modeCache is 4 now), so the pause is
-- permanent.  The rotwedge trace shows exactly this: at f1171, the 8->4 frame,
-- $F5 = $10 = START.
--
-- THREE ARMS (RQ_ARM), same cart, same seed, same publisher:
--   leak  reproduce: START gated on the CACHED mode (the existing harness)
--   fix   START gated on the LIVE mode read inside the poll callback
--   poke  = leak, but on wedge detection press START again and record whether
--           play RESUMES.  A resume is positive proof the state was PAUSE.
--
-- `fix` is the causal test and `poke` is the mechanism test; they can disagree
-- only if there are two wedges, which is itself the finding.  `leak` is the
-- positive control -- if it does not wedge, the run is VOID for this question,
-- not evidence of a fix.
--
-- Env: RQ_OUT RQ_TAG RQ_W RQ_ORIENT RQ_ARM  (RQ_MAXF RQ_DLAT RQ_SEED RQ_STALLN)
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then error("\n*** " .. name .. " IS REQUIRED.\n", 0) end
  return v
end
local OUT    = need("RQ_OUT")
local TAG    = need("RQ_TAG")
local W      = tonumber(need("RQ_W"))
local ORIENT = tonumber(need("RQ_ORIENT"))
local ARM    = need("RQ_ARM")
if ARM ~= "leak" and ARM ~= "fix" and ARM ~= "poke" then
  error("\n*** RQ_ARM must be leak|fix|poke (got '" .. tostring(ARM) .. "')\n", 0)
end
local MAXF   = tonumber(os.getenv("RQ_MAXF") or "12000")
local DLAT   = tonumber(os.getenv("RQ_DLAT") or "34")
local SEED   = tonumber(os.getenv("RQ_SEED") or "114")
local STALLN = tonumber(os.getenv("RQ_STALLN") or "300")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/rotpause.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local TGT_O2, ROT_DONE2, ARMED2 = 0x6153, 0x616E, 0x6161
local P1X, P1Y, P1STEP, P1GRAV = 0x0305, 0x0306, 0x0307, 0x0312
local P2X, P2Y, P2STEP, P2GRAV, P2O = 0x0385, 0x0386, 0x0387, 0x0392, 0x03A5

local frame, curFrame = 0, 0

-- ---- Lua copro publisher (identical to probe_rotwedge.lua) ----
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

-- ================= input =================
local modeCache = -1
local inCur, inUntil = nil, -1
local startInPlay = 0            -- how many polls delivered START while the LIVE mode was 4
local pokeUntil = -1             -- `poke` arm: deliver START through this frame regardless of mode
emu.addEventCallback(function()
  if frame <= pokeUntil then emu.setInput({ start = true }, 0); return end
  if inCur and frame < inUntil then
    local m = (ARM == "fix") and rd(0x46) or modeCache
    if m ~= 4 then
      if rd(0x46) == 4 then startInPlay = startInPlay + 1 end   -- census: leaked into play
      emu.setInput(inCur, 0)
    end
  end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

local prevMode, lvlPoked, seedPokedRound, round = -1, false, -1, 0
local frozen, lastPy = 0, -1
local wedges, pokes, resumes = 0, 0, 0
local wedgeF, pokeWatchUntil = -1, -1

local function state_line(why)
  return string.format("%s f=%d mode=%d TGT_O2=%d ROT_DONE2=%d ARMED2=%d served=%d | " ..
    "P1 x=%d y=%d step=%d grav=%d | P2 x=%d y=%d o=%d step=%d grav=%d | F5=%02X F6=%02X",
    why, frame, rd(0x46), rd(TGT_O2), rd(ROT_DONE2), rd(ARMED2), S.ror,
    rd(P1X), rd(P1Y), rd(P1STEP), rd(P1GRAV),
    rd(P2X), rd(P2Y), rd(P2O), rd(P2STEP), rd(P2GRAV), rd(0xF5), rd(0xF6))
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
      lastPy = -1; frozen = 0; pokeWatchUntil = -1
      return
    end
    if lvlPoked then lvlPoked = false; round = round + 1 end

    local py = rd(P2Y)
    if py == lastPy then frozen = frozen + 1 else frozen = 0; lastPy = py end

    -- did a poked unpause take effect?
    if pokeWatchUntil > 0 and frame <= pokeWatchUntil then
      if frozen == 0 then
        resumes = resumes + 1
        log(state_line(string.format("RESUMED after poke (+%d f)", frame - wedgeF)))
        pokeWatchUntil = -1
      end
    elseif pokeWatchUntil > 0 then
      log(state_line("NO RESUME after poke"))
      pokeWatchUntil = -1
    end

    if frozen == STALLN then
      wedges = wedges + 1; wedgeF = frame
      log(state_line(string.format("WEDGE #%d", wedges)))
      if ARM == "poke" then
        pokes = pokes + 1
        pokeUntil = frame + 4                  -- deliver START into mode 4 on purpose
        pokeWatchUntil = frame + 180
        log(string.format("POKE f=%d: delivering START for 5 frames, watching 180", frame))
      end
      frozen = 0                                -- re-arm so a second wedge is still counted
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF then
    log(string.format("SUMMARY tag=%s arm=%s orient=%d frames=%d goes=%d dones=%d " ..
        "wedges=%d pokes=%d resumes=%d start_leaked_into_play=%d",
        TAG, ARM, ORIENT, frame, S.goes, S.dones, wedges, pokes, resumes, startInPlay))
    logf:flush(); logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("rotpause start tag=%s arm=%s orient=%d w=$%04X maxf=%d seed=%d", TAG, ARM, ORIENT, W, MAXF, SEED))
