-- ============================================================================
-- probe_d131gate.lua -- #131 step 4: NAME THE GATE AND PROVE IT IS CAUSAL.
--
-- probe_d131trace.lua recorded a linear instruction trace of a wedged frame and
-- found the CPU cycling  $97C7 -> $97D3 (JSR $88F6 sound) -> $97D6 -> $97E2
-- (JSR $B654 waitForNMI+OAM clear) -> $97E5 (JMP $97C7).  That is the stock ROM
-- PAUSE LOOP, reached from the main loop's  $814B: JSR $978E:
--
--   $97A3  LDA $54     ; play active?
--   $97A5  BEQ  exit
--   $97A7  LDA $F5     ; P1 NEWLY-PRESSED latch  (edge-detected at $B7E9-$B7F5)
--   $97A9  AND #$10    ; START
--   $97AB  BEQ  exit   ; <== ENTRY GATE
--   ...
--   $97D6  LDA $F5     ; <== EXIT GATE, the named flag
--   $97D8  CMP #$10    ;     must read EXACTLY $10 (START alone, newly pressed)
--   $97DA  BEQ $97E8   ;     $97E8 = unpause: $5D=$FF, $2001=$1E, $068D=0
--
-- So the dispatcher is NOT gated on anything exotic: mode 4's handler is simply
-- never reached because $978E (called BEFORE the mode dispatch returns) parks
-- the CPU inside the pause loop.  $0046 stays 4 throughout, which is why the
-- mode byte looked innocent.
--
-- ARMS (D1_ARM):
--   leak     baseline / positive control -- must still wedge, else the rig is
--            not reproducing and every other arm is uninterpretable.
--   unpause  on wedge, deliver a REAL START edge through the ordinary input
--            path with NO mode gating.  If play resumes, the wedge is an
--            input-SCHEDULING artifact of the harness, not a cart defect.
--   serve    on wedge, intercept the CPU's read of $00F5 at $97D6 and serve
--            $10 for exactly that one read.  Isolates the named byte from the
--            input path entirely.
--   serve0   MUTANT of `serve`: serve $00 instead of $10.  Must NOT resume.
--            Without it, "serving a value resumed play" could be an artifact
--            of intercepting the read at all.
--   nostart  never press START while a LIVE read of $46 says 4.  Tests the
--            ENTRY side: if the wedge disappears, the harness's own one-frame
--            START leak across the 8->4 transit is what pauses the match.
--
-- Resume is judged on ROM CONTROL FLOW, not on a screenshot: $97E8 (the
-- unpause branch target) must EXECUTE, and P2's y must then take >= 3 distinct
-- values within RESUMEW frames.  Both are required.
--
-- Env: D1_OUT D1_TAG D1_W D1_ORIENT D1_ARM (D1_MAXF D1_DLAT D1_SEED D1_STALLN
--      D1_RESUMEW optional)
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then error("\n*** " .. name .. " IS REQUIRED.\n", 0) end
  return v
end
local OUT    = need("D1_OUT")
local TAG    = need("D1_TAG")
local W      = tonumber(need("D1_W"))
local ORIENT = tonumber(need("D1_ORIENT"))
local ARM    = need("D1_ARM")
local VALID = { leak = true, unpause = true, serve = true, serve0 = true, nostart = true,
                who = true, menuonly = true, fix = true }
if not VALID[ARM] then
  error("\n*** D1_ARM must be leak|unpause|serve|serve0|nostart|who|menuonly|fix (got '" ..
        tostring(ARM) .. "')\n", 0)
end
local MAXF    = tonumber(os.getenv("D1_MAXF") or "20000")
local DLAT    = tonumber(os.getenv("D1_DLAT") or "34")
local SEED    = tonumber(os.getenv("D1_SEED") or "114")
local STALLN  = tonumber(os.getenv("D1_STALLN") or "300")
local RESUMEW = tonumber(os.getenv("D1_RESUMEW") or "180")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/d131gate.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local P1Y = 0x0306
local P2X, P2Y, P2STEP, P2GRAV = 0x0385, 0x0386, 0x0387, 0x0392

local frame, curFrame = 0, 0

-- ---- Lua copro publisher (identical to probe_rotpc.lua / probe_d131trace.lua) ----
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

-- ================= pause-loop instrumentation =================
local pauseIters, exitTaken, exitFrame = 0, 0, -1
local entryHits, entryFrame = 0, -1
emu.addMemoryCallback(function() pauseIters = pauseIters + 1 end, emu.callbackType.exec, 0x97C7)
emu.addMemoryCallback(function()
  exitTaken = exitTaken + 1
  if exitFrame < 0 then exitFrame = curFrame end
end, emu.callbackType.exec, 0x97E8)
-- $97AD is the first instruction past the ENTRY gate: reaching it means a START
-- edge was accepted while $54 was live.
emu.addMemoryCallback(function()
  entryHits = entryHits + 1
  if entryFrame < 0 then entryFrame = curFrame end
end, emu.callbackType.exec, 0x97AD)

-- ---- WHO planted the START? ----------------------------------------------
-- `nostart` alone cannot attribute the entry: the harness presses START on a
-- frame whose LIVE $46 still reads 8, and the ROM only advances 8->4 later in
-- that same frame, so a correctly-gated harness press can still be sitting in
-- $F5 when $978E runs.  The driver has the identical staleness -- its three nav
-- START sites are gated on its OWN cached state ($6147 AND #$1F), not on $46:
--   $8171 LDA #$10 / $8173 STA $F5      (guard at $816D, derived counter)
--   $822A LDA #$10 / $822C STA $F5      (guard at $8226, $6147 AND #$1F)
--   $8327 LDA #$10 / $8329 STA $F5      (guard at $8322, $6147 AND #$1F)
-- So the only honest attribution is to watch the sites themselves.  These
-- callbacks are always installed (they cost nothing on arms that never hit
-- them) and every hit is logged with its frame, alongside the value of $F5
-- observed at the entry gate $97A7 itself.
local navStart = { [0x8173] = "nav$8173", [0x822C] = "nav$822C", [0x8329] = "nav$8329" }
local navHits, navLog = 0, {}
for addr, name in pairs(navStart) do
  emu.addMemoryCallback(function()
    navHits = navHits + 1
    if #navLog < 64 then navLog[#navLog + 1] = string.format("%s@f%d", name, curFrame) end
  end, emu.callbackType.exec, addr)
end
local gateSeen, gateLog = 0, {}
emu.addMemoryCallback(function()
  gateSeen = gateSeen + 1
  if #gateLog < 64 then gateLog[#gateLog + 1] = string.format("f%d:F5=%02X", curFrame, rd(0xF5)) end
end, emu.callbackType.exec, 0x97A7)

-- serve / serve0: one-shot override of the CPU's read of $00F5 at $97D6.
local serveArmed, serveOneShot, servedN = false, false, 0
local SERVEVAL = (ARM == "serve0") and 0x00 or 0x10
if ARM == "serve" or ARM == "serve0" then
  emu.addMemoryCallback(function() if serveArmed then serveOneShot = true end end,
                        emu.callbackType.exec, 0x97D6)
  emu.addMemoryCallback(function()
    if serveOneShot then serveOneShot = false; servedN = servedN + 1; return SERVEVAL end
  end, emu.callbackType.read, 0x00F5)
end

local function dump_state(why)
  log(string.format("=== %s f=%d arm=%s ===", why, frame, ARM))
  log(string.format("  mode=%d 54=%02X F5=%02X F6=%02X F7=%02X F8=%02X 5D=%02X 068D=%02X",
    rd(0x46), rd(0x54), rd(0xF5), rd(0xF6), rd(0xF7), rd(0xF8), rd(0x5D), rd(0x068D)))
  log(string.format("  P1 y=%d   P2 x=%d y=%d step=%d grav=%d",
    rd(P1Y), rd(P2X), rd(P2Y), rd(P2STEP), rd(P2GRAV)))
  log(string.format("  pauseIters=%d entryHits=%d entryFrame=%d exitTaken=%d exitFrame=%d servedN=%d",
    pauseIters, entryHits, entryFrame, exitTaken, exitFrame, servedN))
  log(string.format("  navStartHits=%d  %s", navHits, table.concat(navLog, " ")))
  log(string.format("  entryGateSeen=%d  %s", gateSeen, table.concat(gateLog, " ")))
end

-- ================= input =================
local modeCache = -1
local inCur, inUntil = nil, -1
local forceStartFrom, forceStartTo = -1, -1
emu.addEventCallback(function()
  -- `unpause` arm: an unconditional, properly-edged START, ignoring every gate
  if forceStartFrom >= 0 and frame >= forceStartFrom and frame <= forceStartTo then
    emu.setInput({ start = true }, 0); return
  end
  if not inCur or frame >= inUntil then return end
  -- `nostart` reads the mode LIVE at the instant of the poll; every other arm
  -- uses the cached mode.  NOTE `nostart` is NOT a clean exoneration of the
  -- harness: the poll happens in NMI at the top of the frame, and the ROM can
  -- advance 8->4 later in that SAME frame, so a press correctly permitted at
  -- mode 8 is still sitting in $F5 when $978E runs.  `menuonly` closes that by
  -- never pressing START outside the level-select modes at all.
  -- `fix` is the SHIPPING rule.  Mode 8 (intro) is the ONLY predecessor of mode
  -- 4 on this cart -- both entries into play are 8->4 -- and the transition
  -- happens in the main loop, AFTER the frame's NMI input poll.  So a START
  -- delivered at mode 8 is still in $F5 when $978E runs a few thousand cycles
  -- later, already in mode 4, and the ROM pauses.  Suppressing START while the
  -- LIVE mode is 4 or 8 closes the whole window without giving up the presses
  -- that drive modes 0/5/6/7 on carts whose autonav does not cover them.
  if ARM == "fix" then
    local live = rd(0x46)
    if live == 4 or live == 8 then return end
    emu.setInput(inCur, 0); return
  end
  local m = (ARM == "nostart") and rd(0x46) or modeCache
  if m ~= 4 then emu.setInput(inCur, 0) end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

local prevMode, lvlPoked, seedPokedRound, round = -1, false, -1, 0
local frozen, lastPy = 0, -1
local wedgeFrame, finished = -1, false
local resumeYs, resumeSeen = {}, 0
local verdict = "NONE"

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
      log(string.format("MODE f=%d %d->%d goes=%d dones=%d pauseIters=%d", frame, prevMode, mode, S.goes, S.dones, pauseIters))
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
      elseif ARM ~= "menuonly" then
        -- modes 0/5/6/7/8.  `menuonly` presses START ONLY in modes 1-3, so no
        -- harness START exists anywhere near the 8->4 transit; if the wedge
        -- survives that, the START in $F5 was planted by the CART, not by us.
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      lastPy = -1; frozen = 0
      return
    end
    if lvlPoked then lvlPoked = false; round = round + 1 end

    local py = rd(P2Y)
    if py == lastPy then frozen = frozen + 1 else frozen = 0; lastPy = py end

    if wedgeFrame < 0 then
      if frozen >= STALLN then
        wedgeFrame = frame
        dump_state("WEDGE")
        if ARM == "unpause" then
          -- release for 2 frames, then press for 2: a clean edge for $B7E9
          forceStartFrom, forceStartTo = frame + 3, frame + 4
          log(string.format("INTERVENE arm=unpause start-edge frames %d..%d", forceStartFrom, forceStartTo))
        elseif ARM == "serve" or ARM == "serve0" then
          serveArmed = true
          log(string.format("INTERVENE arm=%s serving $%02X to the $97D6 read", ARM, SERVEVAL))
        else
          log("INTERVENE arm=" .. ARM .. " (none)")
        end
      end
    else
      local dy = rd(P2Y)
      local fresh = true
      for i = 1, resumeSeen do if resumeYs[i] == dy then fresh = false; break end end
      if fresh then resumeSeen = resumeSeen + 1; resumeYs[resumeSeen] = dy end
      if frame - wedgeFrame >= RESUMEW then
        local resumed = (exitTaken > 0) and (resumeSeen >= 3)
        verdict = resumed and "RESUMED" or "STILL_WEDGED"
        dump_state("POST")
        log(string.format("SUMMARY tag=%s arm=%s orient=%d verdict=%s wedgeFrame=%d exitTaken=%d " ..
            "distinctP2Y=%d pauseIters=%d entryHits=%d entryFrame=%d servedN=%d frames=%d goes=%d dones=%d",
            TAG, ARM, ORIENT, verdict, wedgeFrame, exitTaken, resumeSeen, pauseIters,
            entryHits, entryFrame, servedN, frame, S.goes, S.dones))
        finished = true; logf:flush(); emu.stop(0)
      end
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF and not finished then
    verdict = (wedgeFrame < 0) and "NO_WEDGE" or "TIMEOUT"
    dump_state("MAXF")
    log(string.format("SUMMARY tag=%s arm=%s orient=%d verdict=%s wedgeFrame=%d exitTaken=%d " ..
        "distinctP2Y=%d pauseIters=%d entryHits=%d entryFrame=%d servedN=%d frames=%d goes=%d dones=%d",
        TAG, ARM, ORIENT, verdict, wedgeFrame, exitTaken, resumeSeen, pauseIters,
        entryHits, entryFrame, servedN, frame, S.goes, S.dones))
    finished = true; logf:flush(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("d131gate start tag=%s arm=%s orient=%d w=$%04X maxf=%d stalln=%d resumew=%d",
    TAG, ARM, ORIENT, W, MAXF, STALLN, RESUMEW))
