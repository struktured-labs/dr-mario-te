-- te_release_qa.lua -- full-game Mesen QA for the STANDALONE Training Edition release (no copro).
--
-- Drives BOTH controllers from Lua through real games (no RAM pokes): 1P games to game over,
-- 2P human-vs-human matches through every round end and the match final, the next match after
-- START, STUDY pause/resume, and an optional long mixed soak. Records per frame a RAM hash so two
-- ROMs given the same script can be diffed frame by frame (tools/te_release_qa/analyze_qa.py).
--
-- env: QA_OUT=<dir/>  QA_SCEN=onep|twop|soak|title  QA_SEED=<int>  QA_SOAK_FRAMES=<int, default 40000>
--      QA_PAUSE=1|0 (onep: take the STUDY pause, default 1)
--
-- Freeze detection (the TE history: a KIL jams the 6502, so the NMI-driven frame clock stops):
--   * CLOCK STALL  -- $43 (L43_CLOCK, incremented by the NMI) unchanged for > 120 frames
--   * RAM EXEC     -- any instruction fetched from $0000-$07FF (stock Dr. Mario never runs code
--                     from RAM; the v6 KIL ran $0301 = $02)
--   * NO PROGRESS  -- in play, neither capsule counter ($0327/$03A7) moves for 3000 frames; elsewhere
--                     (outside the title / START-wait screens) the top state is stuck for 3000 frames
-- Any of these stops the run with code 3 and a FREEZE line in the log.
--
-- RAM map (brianhuffman/drmario labels): $46 top state (0 title, 1 options, 3 level init,
-- 4 play, 5 round-end check, 7 end screen), $43 clock, $54 pause enable, $55 round winner,
-- $61 who failed, $0727 players, $031E/$039E wins, $0324/$03A4 virus BCD, $0316/$0396 level,
-- $0400/$0500 fields (16 rows x 8, $FF empty, $Dx virus), $04 TE VS-CPU arm flag.

local OUT = assert(os.getenv("QA_OUT"), "set QA_OUT")
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local SCEN = os.getenv("QA_SCEN") or "twop"
local SEED = tonumber(os.getenv("QA_SEED") or "1")
local SOAK_FRAMES = tonumber(os.getenv("QA_SOAK_FRAMES") or "40000")
local TAKE_PAUSE = (os.getenv("QA_PAUSE") or "1") == "1"
local FULL = {}                                   -- QA_FULL="lo-hi,lo-hi": full RAM rows for those frames
for lo, hi in (os.getenv("QA_FULL") or ""):gmatch("(%d+)-(%d+)") do FULL[#FULL + 1] = { tonumber(lo), tonumber(hi) } end

local NES, OAM, PPU = emu.memType.nesMemory, emu.memType.nesSpriteRam, emu.memType.nesPpuMemory
local function rd(a) return emu.read(a, NES, false) end

local lf = io.open(OUT .. "qa.log", "w")
local hf = io.open(OUT .. "frames.txt", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end

local function shot(name)
  local ok, p = pcall(emu.takeScreenshot)
  if ok and p then
    local f = io.open(OUT .. name .. ".png", "wb"); f:write(p); f:close()
    logf("SHOT " .. name)
  else
    logf("SHOT_FAIL " .. name .. " " .. tostring(p))
  end
end

local function hexrow(base, n, mt)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02X", emu.read(base + i, mt or NES, false)) end
  return table.concat(t)
end
local function field(p) return hexrow(p == 1 and 0x0400 or 0x0500, 128) end

local function dump(tag)
  local f = io.open(OUT .. "dump_" .. tag .. ".txt", "w")
  for r = 0, 15 do f:write(string.format("P1 r%02d %s   P2 r%02d %s\n", r, hexrow(0x0400 + r * 8, 8), r, hexrow(0x0500 + r * 8, 8))) end
  for s = 0, 63 do
    local b = s * 4
    f:write(string.format("OAM %02d Y=%3d tile=%02X attr=%02X X=%3d\n", s, emu.read(b, OAM, false),
      emu.read(b + 1, OAM, false), emu.read(b + 2, OAM, false), emu.read(b + 3, OAM, false)))
  end
  for r = 0, 29 do f:write(string.format("NT r%02d %s\n", r, hexrow(0x2000 + r * 32, 32, PPU))) end
  f:write("RAM " .. hexrow(0, 0x800) .. "\n")
  f:close()
end

-- deterministic LCG for the input policies
local rng = (SEED * 2654435761) % 4294967296
local function rand(n) rng = (rng * 1103515245 + 12345) % 2147483648; return (rng // 65536) % n end

-------------------------------------------------------------------------- input
local pad = { [0] = {}, [1] = {} }
local BUTTONS = { "a", "b", "select", "start", "up", "down", "left", "right" }
local function full(t)                    -- explicit false for every button: setInput only writes the
  local r = {}                            -- keys present, so a sparse table would leave stale bits set
  for _, k in ipairs(BUTTONS) do r[k] = t[k] and true or false end
  return r
end
local PORTARGS = os.getenv("QA_PORTARGS") or "third"
emu.addEventCallback(function()
  -- Mesen2 LuaApi::SetInput pads the stack to 4 (lua_settop) after ForceParamCount(3), so the PORT is
  -- read from the THIRD argument and the second is ignored: emu.setInput(t, 1) silently drives
  -- controller 1. Pass the port as the 3rd argument (measured: tools/te_release_qa p2debug).
  if PORTARGS == "third" then
    emu.setInput(full(pad[0]), 0, 0)
    emu.setInput(full(pad[1]), 0, 1)
  else
    emu.setInput(full(pad[0]), 0)
    emu.setInput(full(pad[1]), 1)
  end
end, emu.eventType.inputPolled)

-------------------------------------------------------------------------- freeze detectors
local ramExec, ramExecFirst = 0, nil
local frame = 0
emu.addMemoryCallback(function()
  ramExec = ramExec + 1
  if not ramExecFirst then ramExecFirst = frame end
end, emu.callbackType.exec, 0x0000, 0x07FF, emu.cpuType.nes, emu.memType.nesMemory)
-- first frame the end-screen START-wait loop ($9607, stock: shared by the 1P game over and the 2P match
-- final) runs after a reset of startLoopFrame: "START is accepted from here on"
local startLoopFrame = nil
emu.addMemoryCallback(function()
  if not startLoopFrame then startLoopFrame = frame end
end, emu.callbackType.exec, 0x9607, 0x9607, emu.cpuType.nes, emu.memType.nesMemory)

local stats = { maxClockStall = 0, modes = {}, roundEnds = 0, finals = 0, games1p = 0, pauses = 0,
                matches = 0, nextClean = 0, nextDirty = 0, signSprites = 0, wipes = 0, gameOverFills = 0,
                over1p = 0, over1pKept = 0, over1pWiped = 0, over1pBox = 0, over1pToOptions = 0,
                next1pClean = 0, next1pDirty = 0, clears1p = 0 }
local lastClock, clockStall, lastMode, modeSince = -1, 0, -1, 0
-- the final board of a round: both fields as of the last frame in mode 4/5 (mode 5 = the one-frame
-- round-end check; the stock wipe runs on the NEXT frame). Tracked in the frame callback, not in the
-- scenario coroutine, so it is right even when the round ends while the script is busy (e.g. resuming
-- from a STUDY pause).
local snapF1, snapF2 = nil, nil
local lastPills, pillsSince = -1, 0

local function finish(code, why)
  logf(string.format("STATS frames=%d ramExec=%d maxClockStall=%d roundEnds=%d finals=%d games1p=%d pauses=%d " ..
    "matches=%d nextClean=%d nextDirty=%d signSpritesSeen=%d lowerWipes=%d gameOverFills=%d clearWins=%d " ..
    "over1p=%d over1pKept=%d over1pWiped=%d over1pBox=%d over1pToOptions=%d next1pClean=%d next1pDirty=%d clears1p=%d",
    frame, ramExec, stats.maxClockStall, stats.roundEnds, stats.finals, stats.games1p, stats.pauses,
    stats.matches, stats.nextClean, stats.nextDirty, stats.signSprites, stats.wipes, stats.gameOverFills, stats.clearWins or 0,
    stats.over1p, stats.over1pKept, stats.over1pWiped, stats.over1pBox, stats.over1pToOptions, stats.next1pClean,
    stats.next1pDirty, stats.clears1p))
  logf("DONE " .. code .. " " .. (why or ""))
  lf:close(); hf:close()
  emu.stop(code)
end

-------------------------------------------------------------------------- scenario helpers (coroutine)
local function step() coroutine.yield() end
local function wait(n) for _ = 1, n do step() end end
local function press(p, btns, holdf, gap)
  pad[p] = btns; wait(holdf or 6); pad[p] = {}; wait(gap or 12)
end
local function mode() return rd(0x46) end
local function wait_mode(m, timeout, what)
  local t = 0
  while mode() ~= m do
    step(); t = t + 1
    if t > (timeout or 3000) then logf(string.format("WAIT_TIMEOUT for mode %d (%s) at f%d, mode=%d", m, what or "", frame, mode())); return false end
  end
  return true
end

local function vars(tag)
  logf(string.format("  [%s] f=%d mode=%d players=%d armed$04=%d $54=%d won$55=%d failed$61=%d wins=%d/%d virus=%02X/%02X lvl=%d/%d",
    tag, frame, mode(), rd(0x0727), rd(0x04), rd(0x54), rd(0x55), rd(0x61), rd(0x031E), rd(0x039E), rd(0x0324), rd(0x03A4),
    rd(0x0316), rd(0x0396)))
end

-- visible sprites in OAM slots 8..34 inside a bottle (the X-sign + red virus live there in stock)
local function bottle_sprites(p)
  local n = 0
  local xlo, xhi = 16, 96
  if p == 2 then xlo, xhi = 144, 232 end
  for s = 8, 34 do
    local y, x = emu.read(s * 4, OAM, false), emu.read(s * 4 + 3, OAM, false)
    if y < 0xEF and y >= 140 and y <= 205 and x >= xlo and x <= xhi then n = n + 1 end
  end
  return n
end

local function lower_all_ff(p)
  local base = (p == 1) and 0x0440 or 0x0540
  for a = base, base + 63 do if rd(a) ~= 0xFF then return false end end
  return true
end

local function only_viruses_or_empty(p)
  local base = (p == 1) and 0x0400 or 0x0500
  local nv = 0
  for a = base, base + 127 do
    local v = rd(a)
    if v ~= 0xFF then
      if (v & 0xF0) ~= 0xD0 then return false, nv end
      nv = nv + 1
    end
  end
  return true, nv
end

-- the bottle as DRAWN: NT rows 10..25, cols 4..11 (P1) / 20..27 (P2) must equal field RAM
local function nt_matches_field(p)
  local col = (p == 1) and 4 or 20
  local fb = (p == 1) and 0x0400 or 0x0500
  for r = 0, 15 do
    for c = 0, 7 do
      if emu.read(0x2000 + (10 + r) * 32 + col + c, PPU, false) ~= rd(fb + r * 8 + c) then return false end
    end
  end
  return true
end

-- STUDY pause check: STUDY letters in OAM slots 32-36, board frozen, START resumes
local function study_pause(tag, players)
  press(0, { start = true }, 6, 4)
  -- reference taken once the pause is in effect (the START edge is latched a frame or two after the
  -- press, and the capsule may lock in that window), then the board must not change for 70 frames
  local before1, before2 = field(1), field(2)
  wait(40)
  local ys = {}
  for s = 32, 36 do ys[#ys + 1] = emu.read(s * 4, OAM, false) end
  local px = {}
  for s = 37, 40 do px[#px + 1] = string.format("%d:%d", emu.read(s * 4, OAM, false), emu.read(s * 4 + 3, OAM, false)) end
  local tiles = {}
  for s = 32, 36 do tiles[#tiles + 1] = string.format("%02X", emu.read(s * 4 + 1, OAM, false)) end
  local frozen1, frozen2 = (field(1) == before1), (field(2) == before2)
  local clk0 = rd(0x43)
  wait(30)
  local frozen1b, frozen2b = (field(1) == before1), (field(2) == before2)
  shot(tag)
  dump(tag)
  logf(string.format("STUDY %s players=%d letterY=%s tiles=%s previews(Y:X)=%s frozenP1=%s frozenP2=%s clockRuns=%s",
    tag, players, table.concat(ys, ","), table.concat(tiles, ","), table.concat(px, ","), tostring(frozen1 and frozen1b),
    tostring(frozen2 and frozen2b), tostring(rd(0x43) ~= clk0)))
  stats.pauses = stats.pauses + 1
  press(0, { start = true }, 6, 4)
  -- resumed: the falling pill / fields must move again within 240 frames
  local moved, t = false, 0
  local f1, f2, y1 = field(1), field(2), rd(0x0306)
  while t < 240 and not moved do
    step(); t = t + 1
    if field(1) ~= f1 or field(2) ~= f2 or rd(0x0306) ~= y1 or mode() ~= 4 then moved = true end
  end
  logf(string.format("RESUME %s moved=%s after %d frames", tag, tostring(moved), t))
  return moved
end

-- "solver": a deliberately simple virus-clearing policy, so rounds can also end the way most real 2P
-- rounds do -- by clearing every virus (the STAGE CLEAR / clear-win path). Single-colour capsules go
-- vertically onto a virus column whose top cell has that colour (2 of them clear a virus); every other
-- capsule is dumped vertically in a virus-free column. Good enough at virus level 0 (4 viruses).
-- Player struct (P1 $0300 / P2 $0380): +$01/+$02 capsule colours, +$05 column, +$25 rotation,
-- +$27 capsule counter; field $0400/$0500 (row 0 = top, $FF empty, $Dx virus, colour = low 2 bits).
local sol = { [0] = { n = -1 }, [1] = { n = -1 } }
local DUMP_PREF = { 0, 7, 1, 6, 2, 5, 3, 4 }
local function solver_plan(p)
  local S, F = (p == 0) and 0x0300 or 0x0380, (p == 0) and 0x0400 or 0x0500
  local c0, c1 = rd(S + 1), rd(S + 2)
  local top, tcol, run, hasv = {}, {}, {}, {}
  for c = 0, 7 do
    top[c], hasv[c] = 16, false
    for r = 0, 15 do
      local v = rd(F + r * 8 + c)
      if v ~= 0xFF and top[c] == 16 then top[c] = r end
      if (v & 0xF0) == 0xD0 then hasv[c] = true end
    end
    if top[c] < 16 then
      tcol[c] = rd(F + top[c] * 8 + c) & 3
      local n, r = 0, top[c]
      while r < 16 and rd(F + r * 8 + c) ~= 0xFF and (rd(F + r * 8 + c) & 3) == tcol[c] do n = n + 1; r = r + 1 end
      run[c] = n
    end
  end
  if c0 == c1 then
    local best, bestRun = nil, -1
    for c = 0, 7 do
      if hasv[c] and top[c] >= 3 and tcol[c] == c0 and run[c] > bestRun then best, bestRun = c, run[c] end
    end
    if best then return best end
  end
  local best, room = nil, -1
  for _, c in ipairs(DUMP_PREF) do
    if not hasv[c] and top[c] > room then best, room = c, top[c] end
  end
  if not best or room < 3 then
    for _, c in ipairs(DUMP_PREF) do if top[c] > room then best, room = c, top[c] end end
  end
  return best
end
local function solver(p)
  local S = (p == 0) and 0x0300 or 0x0380
  local st = sol[p]
  local n = rd(S + 0x27)
  if n ~= st.n then
    st.n, st.phase, st.t, st.target = n, "rot", 0, solver_plan(p)
    if os.getenv("QA_SOLVERLOG") then
      logf(string.format("SOLVER p%d n=%d colors=%d/%d target=%s virus=%02X", p + 1, n, rd(S + 1), rd(S + 2), tostring(st.target), rd(S + 0x24)))
    end
  end
  st.t = st.t + 1
  if st.phase == "rot" then
    if rd(S + 0x25) ~= 0 then st.phase = "move"; pad[p] = {}
    else pad[p] = (st.t % 4 == 1) and { a = true } or {} end
  end
  if st.phase == "move" then
    local col = rd(S + 5)
    if col == st.target or st.t > 90 then st.phase = "drop"
    elseif st.t % 2 == 0 then pad[p] = (col < st.target) and { right = true } or { left = true }
    else pad[p] = {} end
  end
  if st.phase == "drop" then pad[p] = { down = true } end
end

-- per-player play policies, applied every frame while mode==4
local policy = { [0] = "idle", [1] = "idle" }
local function drive()
  for p = 0, 1 do
    local pol = policy[p]
    if pol == "solver" then
      solver(p)
    elseif pol == "sides" then              -- slow loser: pushes each capsule (horizontal, no DOWN) to the
      local S = (p == 0) and 0x0300 or 0x0380   -- left / right wall alternately, keeping the spawn clear
      local n = rd(S + 0x27)
      if n ~= sol[p].n then sol[p].n = n end
      if frame % 2 == 0 then pad[p] = (n % 2 == 0) and { left = true } or { right = true } else pad[p] = {} end
    elseif pol == "drop" then
      pad[p] = (frame % 4 < 3) and { down = true } or {}
    elseif pol == "random" then
      if frame % 6 == 0 then
        local r = rand(10)
        if r == 0 then pad[p] = { left = true }
        elseif r == 1 then pad[p] = { right = true }
        elseif r == 2 then pad[p] = { a = true }
        elseif r == 3 then pad[p] = { b = true }
        elseif r == 4 then pad[p] = { down = true }
        else pad[p] = {} end
      elseif frame % 6 == 3 then
        pad[p] = {}
      end
    else
      pad[p] = {}
    end
  end
end

-- get from wherever we are to a live game with `players` (1/2), `armCpu` (VS CPU) and P1 level
local function goto_play(players, armCpu, level, level2, speed)
  pad[0], pad[1] = {}, {}
  local t = 0
  while mode() ~= 4 do
    t = t + 1
    if t > 8000 then logf("NAV_TIMEOUT mode=" .. mode()); return false end
    local m = mode()
    local armed = rd(0x04) ~= 0
    local ok_setup = (rd(0x0727) == players) and (armed == (armCpu and true or false))
    if m == 0 then
      if ok_setup then
        press(0, { start = true }, 6, 30)
      elseif armCpu or armed then
        press(0, { select = true }, 6, 20)          -- SELECT walks 1P -> 2P -> 2P+CPU (TE arming)
      else
        press(0, players == 2 and { down = true } or { up = true }, 6, 20)
      end
    elseif m == 1 and not ok_setup then
      press(0, { b = true }, 6, 30)                 -- options screen: B returns to the title
    elseif m == 1 then
      -- virus level is absolute: walk P1 ($0316) and P2 ($0396) to the requested level.
      -- Optional P1 speed ($030B: 0 LOW, 1 MED, 2 HI) only when asked, so the older scenarios keep their
      -- exact input sequence: first the section cursor $65 (0 level, 1 speed, 2 music) back to the top
      local k = 0
      while speed and rd(0x65) ~= 0 and k < 6 do press(0, { up = true }, 4, 8); k = k + 1 end
      k = 0
      while rd(0x0316) ~= (level or 0) and k < 40 do
        press(0, (rd(0x0316) < (level or 0)) and { right = true } or { left = true }, 4, 8); k = k + 1
      end
      k = 0
      while players == 2 and rd(0x0396) ~= (level2 or 0) and k < 40 do
        press(1, (rd(0x0396) < (level2 or 0)) and { right = true } or { left = true }, 4, 8); k = k + 1
      end
      if speed then
        k = 0
        while rd(0x65) ~= 1 and k < 6 do press(0, { down = true }, 4, 8); k = k + 1 end
        k = 0
        while rd(0x030B) ~= speed and k < 8 do
          press(0, (rd(0x030B) < speed) and { right = true } or { left = true }, 4, 8); k = k + 1
        end
      end
      press(0, { start = true }, 6, 30)
      local u = 0
      while mode() == 1 and u < 120 do step(); u = u + 1 end
    elseif m == 7 then
      press(0, { start = true }, 6, 30)
    else
      step()
    end
  end
  return true
end

-- play until the round/game ends (mode leaves 4 for good) -- returns the last in-play fields
local function play_until_end(maxf, pause_at, players, switch_at, after)
  local t = 0
  while true do
    if mode() == 4 and players == 2 and (rd(0x0324) == 0 or rd(0x03A4) == 0) then
      -- a virus-clear win: non-final ones stay in top state 4 (STAGE CLEAR box, wait for START); the
      -- third win goes straight to the end screen (state 7) -- give it a moment to tell them apart
      local s1, s2 = snapF1, snapF2
      pad[0], pad[1] = {}, {}
      local u = 0
      while mode() == 4 and u < 180 do step(); u = u + 1 end
      if mode() == 7 then return s1, s2, "ended" end
      return s1, s2, "clear"
    end
    if mode() == 4 then
      if switch_at and t == switch_at then policy[0], policy[1] = after[1], after[2] end
      drive()
      if pause_at and t == pause_at then
        pad[0], pad[1] = {}, {}
        study_pause("study_" .. players .. "p_f" .. frame, players)
      end
    elseif mode() == 7 then
      break
    end
    step(); t = t + 1
    if maxf and t >= maxf then return nil, nil, "timeout" end
  end
  pad[0], pad[1] = {}, {}
  return snapF1, snapF2, "ended"
end

-- inspect a 2P end screen: boards kept? sign drawn? Returns loser (1/2)
local function check_end_screen(tag, last1, last2, isFinal, shots)
  local loser = rd(0x61)
  local clearWin = (loser == 0)                     -- round won by clearing every virus (STAGE CLEAR)
  if clearWin then                                  -- $55 is not set yet on the final; use the counts
    if rd(0x0324) == 0 or rd(0x031E) >= 3 then loser = 2 else loser = 1 end
  end
  local wonBy = (loser == 1) and 2 or 1
  vars(tag .. "+0")
  local checks = isFinal and { 30, 150, 260, 390, 420, 450 } or { 30, 150 }
  local res = {}
  local t0 = frame
  local lp = (loser == 2) and 2 or 1
  local wp = 3 - lp
  local winnerRef = (wp == 1) and last1 or last2
  for _, d in ipairs(checks) do
    while frame - t0 < d do step() end
    -- a clear-win final starts while the winner's last clear is still animating in RAM: the winner's
    -- reference is then its board at +30; the loser's reference is always the final in-play board
    if clearWin and d == 30 then winnerRef = field(wp) end
    local cur, ref = field(lp), (lp == 1) and last1 or last2
    local kept = (cur == ref)
    local ndiff = 0
    for i = 1, #cur, 2 do if cur:sub(i, i + 1) ~= ref:sub(i, i + 1) then ndiff = ndiff + 1 end end
    local other = (field(wp) == winnerRef)
    local sign = bottle_sprites(lp)
    local wiped = lower_all_ff(lp)
    res[#res + 1] = string.format("+%d loser=P%d keptLoser=%s(%d cells differ) keptWinner=%s signSprites=%d loserLowerFF=%s ntLoser=%s ntWinner=%s",
      d, lp, tostring(kept), ndiff, tostring(other), sign, tostring(wiped), tostring(nt_matches_field(lp)), tostring(nt_matches_field(wp)))
    if sign > 0 then stats.signSprites = stats.signSprites + 1 end
    if wiped then stats.wipes = stats.wipes + 1 end
    if isFinal and d == 390 and not (kept and other) then stats.gameOverFills = stats.gameOverFills + 1 end
    if shots then shot(tag .. "_" .. d); dump(tag .. "_" .. d) end
  end
  logf(string.format("ENDSCREEN %s final=%s winner=P%d clearWin=%s %s", tag, tostring(isFinal), wonBy, tostring(clearWin),
    table.concat(res, " | ")))
  return loser
end

-- a non-final virus-clear round end (state 4): the loser's board must be untouched (stock and v10 alike)
local function check_clear_screen(tag, last1, last2, shots)
  local winner = (rd(0x0324) == 0) and 1 or 2
  local lp = 3 - winner
  vars(tag .. "+0")
  local res, t0 = {}, frame
  for _, d in ipairs({ 30, 150 }) do
    while frame - t0 < d do step() end
    local cur, ref = (lp == 1) and field(1) or field(2), (lp == 1) and last1 or last2
    res[#res + 1] = string.format("+%d loser=P%d keptLoser=%s signSprites=%d loserLowerFF=%s ntLoser=%s", d, lp, tostring(cur == ref),
      bottle_sprites(lp), tostring(lower_all_ff(lp)), tostring(nt_matches_field(lp)))
    if shots then shot(tag .. "_" .. d); dump(tag .. "_" .. d) end
  end
  logf(string.format("CLEARSCREEN %s winner=P%d %s", tag, winner, table.concat(res, " | ")))
  -- continue: START (P1; the winner's pad as a fallback)
  for _, p in ipairs({ 0, winner - 1, 1 }) do
    press(p, { start = true }, 6, 10)
    local u = 0
    while (rd(0x0324) == 0 or rd(0x03A4) == 0) and u < 120 do step(); u = u + 1 end
    if rd(0x0324) ~= 0 and rd(0x03A4) ~= 0 then break end
  end
  if not wait_mode(4, 3000, "after clear") then return false end
  while rd(0x0324) == 0 or rd(0x03A4) == 0 do step() end
  return true
end

-- one 2P match: loserPlan[k] = which player drops in round k (the other plays random)
local function play_match(tag, armCpu, loserPlan, shotsRounds, pauseRound, opts)
  opts = opts or {}
  stats.matches = stats.matches + 1
  if not goto_play(2, armCpu, opts.level1 or 0, opts.level2 or 0) then return false end
  local round = 1
  while true do
    -- first frame of a round
    vars(string.format("%s r%d start", tag, round))
    if round == 1 and stats.matches > 1 then
      local c1, n1 = only_viruses_or_empty(1)
      local c2, n2 = only_viruses_or_empty(2)
      local clean = c1 and c2 and rd(0x031E) == 0 and rd(0x039E) == 0 and bottle_sprites(1) == 0 and bottle_sprites(2) == 0
      logf(string.format("NEXTMATCH %s clean=%s fieldsOnlyViruses=%s/%s viruses=%d/%d wins=%d/%d",
        tag, tostring(clean), tostring(c1), tostring(c2), n1, n2, rd(0x031E), rd(0x039E)))
      if clean then stats.nextClean = stats.nextClean + 1 else stats.nextDirty = stats.nextDirty + 1 end
    end
    if shotsRounds and round == 1 then wait(2); shot(tag .. "_r1_start") end
    local lp = loserPlan[((round - 1) % #loserPlan) + 1]
    local after = { "random", "random" }
    after[lp] = "drop"
    if armCpu then after[2] = "idle" end              -- the CPU drives P2 itself
    local warm = opts.warmup or 0
    if warm > 0 then policy[0], policy[1] = "random", armCpu and "idle" or "random"
    else policy[0], policy[1] = after[1], after[2] end
    local last1, last2, why = play_until_end(12000, (round == pauseRound) and (opts.pauseAt or 100) or nil, 2,
                                             warm > 0 and warm or nil, after)
    policy[0], policy[1] = "idle", "idle"
    if why ~= "ended" then logf("ROUND_TIMEOUT " .. tag .. " r" .. round); return false end
    stats.roundEnds = stats.roundEnds + 1
    local wins1, wins2 = rd(0x031E), rd(0x039E)
    local isFinal = (wins1 >= 3 or wins2 >= 3)
    local loser = check_end_screen(string.format("%s_r%d", tag, round), last1, last2, isFinal,
                                   shotsRounds and (round <= 2 or isFinal))
    if isFinal then
      stats.finals = stats.finals + 1
      wait(30)
      press(0, { start = true }, 6, 30)
      local u = 0
      while mode() == 7 and u < 300 do step(); u = u + 1 end
      vars(tag .. " after-final-START")
      if shotsRounds then wait(30); shot(tag .. "_after_final") end
      return true
    end
    wait(250)
    press(0, { start = true }, 6, 10)
    if not wait_mode(4, 3000, "next round") then return false end
    round = round + 1
  end
end

-------------------------------------------------------------------------- 1P game over
-- stock 1P game over (top state 7, playerLoses_endScreen): 64-frame wait, 128-frame wait, then the
-- $0400-$05FF $FF fill + the GAME OVER box written into field rows 2-8 (redrawn row by row by the NMI),
-- then the START-wait loop at $9607; START -> $FE fill, top state 1 (options), high-score check.
local GO_BOX = "8B8C8C8C8C8C8C8D8EFEFEFEFEFEFE8F8EFE100A160EFE8F8EFEFEFEFEFEFE8F8EFE181F0E1BFE8F8EFEFEFEFEFEFE8F" ..
               "EDEEEEEEEEEEEEEF"
-- the 1P bottle as DRAWN: NT rows 10..25, cols 12..19 (fieldRow_PPUADDR_1P $A717: row 0 = $214C)
local function nt_bottle_1p()
  local t = {}
  for r = 0, 15 do t[#t + 1] = hexrow(0x2000 + (10 + r) * 32 + 12, 8, PPU) end
  return table.concat(t)
end
-- visible sprites overlapping the 1P bottle interior (pixels X 96..159, Y 80..207; OAM Y = line - 1)
local function sprites_1p_bottle()
  local n, list = 0, {}
  for s = 0, 63 do
    local y, x = emu.read(s * 4, OAM, false), emu.read(s * 4 + 3, OAM, false)
    if y < 0xEF and y + 8 >= 80 and y + 1 <= 207 and x + 7 >= 96 and x <= 159 then
      n = n + 1
      list[#list + 1] = string.format("%02X@%d,%d", emu.read(s * 4 + 1, OAM, false), x, y)
    end
  end
  return n, table.concat(list, " ")
end

-- watch a 1P game over from its first top-state-7 frame for `hold` frames, then press START and check
-- the stock continuation. `snap` = the P1 field on the last in-play frame (incl. the capsule that could
-- not spawn: action_sendPill's fail path writes it into the field with confirmPlacement).
local function check_go1p(tag, snap, hold, shots, earlyStart)
  local t0 = frame
  local ntSnap = nt_bottle_1p()
  local firstField, firstNt, boxSeen, maxSpr, sprTiles = nil, nil, false, 0, {}
  local cps = { [1] = true, [30] = true, [64] = true, [100] = true, [150] = true, [190] = true, [194] = true,
                [200] = true, [215] = true, [230] = true, [300] = true, [hold] = true }
  startLoopFrame = nil
  stats.over1p = stats.over1p + 1
  vars(tag .. " gameover+0")
  for d = 1, hold do
    -- an early START (while the stock waits run) must be ignored, exactly as in stock
    if earlyStart and d == 100 then pad[0] = { start = true } elseif earlyStart and d == 106 then pad[0] = {} end
    step()
    local f1, nt = field(1), nt_bottle_1p()
    if not firstField and f1 ~= snap then firstField = d end
    if not firstNt and nt ~= ntSnap then firstNt = d end
    if f1:sub(33, 144) == GO_BOX then boxSeen = true end
    local n, desc = sprites_1p_bottle()
    if n > maxSpr then maxSpr = n end
    for tile in desc:gmatch("(%x%x)@") do sprTiles[tile] = true end
    if cps[d] then
      local nd = 0
      for i = 1, #f1, 2 do if f1:sub(i, i + 1) ~= snap:sub(i, i + 1) then nd = nd + 1 end end
      logf(string.format("GO1P_T %s +%d mode=%d fieldKept=%s(%d cells differ) box=%s ntEqSnap=%s ntEqField=%s " ..
        "bottleSprites=%d [%s] st0300=%02X st0380=%02X st80=%02X won55=%02X failed61=%02X fp57=%02X cur58=%02X z5D=%02X startLoop=%s",
        tag, d, mode(), tostring(f1 == snap), nd, tostring(f1:sub(33, 144) == GO_BOX), tostring(nt == ntSnap),
        tostring(nt == f1), n, desc, rd(0x0300), rd(0x0380), rd(0x80), rd(0x55), rd(0x61), rd(0x57), rd(0x58), rd(0x5D),
        startLoopFrame and ("+" .. (startLoopFrame - t0)) or "no"))
    end
    if shots and (d == 150 or d == hold) then shot(tag .. "_gameover_" .. d); dump(tag .. "_gameover_" .. d) end
  end
  local tiles = {}
  for k in pairs(sprTiles) do tiles[#tiles + 1] = k end
  table.sort(tiles)
  if shots then
    -- a frame with the START prompt drawn (the loop blinks it while frameCounter $43 & 8 ~= 0); the wait
    -- depends only on $43, so every ROM given this script still sees the same inputs on the same frames
    local w2 = 0
    while (rd(0x43) & 8) == 0 and w2 < 16 do step(); w2 = w2 + 1 end
    wait(2); shot(tag .. "_gameover_prompt"); dump(tag .. "_gameover_prompt")
  end
  local kept = (firstField == nil) and (field(1) == snap) and (nt_bottle_1p() == ntSnap) and mode() == 7
  if kept then stats.over1pKept = stats.over1pKept + 1 end
  if firstField then stats.over1pWiped = stats.over1pWiped + 1 end
  if boxSeen then stats.over1pBox = stats.over1pBox + 1 end
  -- START (P1): stock fills both fields with $FE and goes to the options screen (top state 1)
  local pressAt = frame - t0
  pad[0] = { start = true }
  local u = 0
  while mode() == 7 and u < 120 do
    step(); u = u + 1
    if u == 6 then pad[0] = {} end
  end
  local fe = (field(1) == string.rep("FE", 128)) and (field(2) == string.rep("FE", 128))
  local m1 = mode()
  while u < 6 do step(); u = u + 1 end
  pad[0] = {}
  local w = 0
  while mode() ~= 1 and w < 600 do step(); w = w + 1 end
  if mode() == 1 and fe then stats.over1pToOptions = stats.over1pToOptions + 1 end
  logf(string.format("GO1P %s lvl=%d spd=%d keptToHold=%s firstFieldChange=%s firstNtChange=%s boxSeen=%s startLoopFrom=%s " ..
    "maxBottleSprites=%d bottleSpriteTiles=%s earlyStart=%s holdFrames=%d startPressedAt=+%d left7after=%d modeAfterStart=%d fieldsFE=%s optionsReached=%s",
    tag, rd(0x0316), rd(0x030B), tostring(kept), firstField and ("+" .. firstField) or "never",
    firstNt and ("+" .. firstNt) or "never", tostring(boxSeen), startLoopFrame and ("+" .. (startLoopFrame - t0)) or "never",
    maxSpr, table.concat(tiles, ","), tostring(earlyStart and true or false), hold, pressAt, u, m1, tostring(fe),
    tostring(mode() == 1)))
  if shots then wait(30); shot(tag .. "_after_start") end
  return kept
end

local function play_1p(tag, level, pauseAt, maxPlay, shots, opts)
  opts = opts or {}
  if not goto_play(1, false, level, nil, opts.speed) then return false end
  stats.games1p = stats.games1p + 1
  -- every 1P game must start clean: P1 field = this level's viruses only
  local c1, n1 = only_viruses_or_empty(1)
  if c1 and n1 > 0 then stats.next1pClean = stats.next1pClean + 1 else stats.next1pDirty = stats.next1pDirty + 1 end
  logf(string.format("NEXT1P %s clean=%s viruses=%d lvl=%d spd=%d", tag, tostring(c1 and n1 > 0), n1, rd(0x0316), rd(0x030B)))
  vars(tag .. " start")
  if shots then wait(2); shot(tag .. "_start") end
  policy[0] = "random"
  local t = 0
  while mode() == 4 and t < maxPlay do
    drive()
    if pauseAt and t == pauseAt then pad[0] = {}; study_pause("study_1p_" .. tag, 1) end
    step(); t = t + 1
  end
  -- now force the top-out
  policy[0] = "drop"
  local snap, _, why = play_until_end(20000, nil, 1)
  policy[0] = "idle"
  pad[0] = {}
  vars(tag .. " end(" .. why .. ")")
  if why ~= "ended" then logf("ROUND_TIMEOUT " .. tag); return false end
  return check_go1p(tag, snap, opts.hold or 400, shots, opts.earlyStart)
end

-------------------------------------------------------------------------- scenarios
local scenarios = {}

function scenarios.title()
  wait(240); shot("title"); dump("title")
  -- level select (1P) for the screenshot set
  press(0, { start = true }, 6, 60); shot("level_select_1p")
end

function scenarios.onep()
  wait(240); shot("title")
  play_1p("g1", 0, TAKE_PAUSE and 300 or nil, 900, true)
  play_1p("g2", 5, TAKE_PAUSE and 120 or nil, 600, true)
end

-- 1P game overs at several levels / speeds: the end screen is watched frame by frame for 600 frames
-- (stock wipes at ~+192), an early START during the stock waits must be ignored, START then continues
-- the stock way (fields $FE, options screen) and every following game starts clean
function scenarios.go1p()
  wait(240); shot("title")
  local cfg = { { 0, 0, 600 }, { 5, 1, 900 }, { 12, 2, 400 }, { 20, 1, 300 }, { 9, 2, 1500 } }
  for i, c in ipairs(cfg) do
    play_1p("go" .. i, c[1], nil, c[3], i == 1 or i == 3, { speed = c[2], hold = 600, earlyStart = (i % 2 == 1) })
  end
  -- one more game after the last START: it must start clean too
  if goto_play(1, false, 3, nil, 0) then
    local c1, n1 = only_viruses_or_empty(1)
    if c1 and n1 > 0 then stats.next1pClean = stats.next1pClean + 1 else stats.next1pDirty = stats.next1pDirty + 1 end
    logf(string.format("NEXT1P final clean=%s viruses=%d lvl=%d spd=%d", tostring(c1 and n1 > 0), n1, rd(0x0316), rd(0x030B)))
    wait(120)
  end
end

-- 1P stage clears (STAGE CLEAR box, START, next level) must be untouched: the solver clears level 0
-- and level 1, then the game is topped out and its game over checked like go1p
function scenarios.clear1p()
  wait(240); shot("title")
  if not goto_play(1, false, 0, nil, 0) then return end
  stats.games1p = stats.games1p + 1
  for k = 1, 2 do
    vars("clr" .. k .. " start")
    policy[0] = "solver"; sol[0].n = -1
    local t = 0
    while mode() == 4 and rd(0x0324) ~= 0 and t < 30000 do drive(); step(); t = t + 1 end
    policy[0] = "idle"; pad[0] = {}
    if mode() ~= 4 or rd(0x0324) ~= 0 then logf("CLEAR1P clr" .. k .. " not cleared, mode=" .. mode()); break end
    stats.clears1p = stats.clears1p + 1
    local f0 = frame
    wait(60)
    local c1, n1 = only_viruses_or_empty(1)
    logf(string.format("CLEAR1P clr%d cleared at f%d lvl=%d +60 mode=%d fieldViruses=%d bottleSprites=%d", k, f0, rd(0x0316),
      mode(), n1, (sprites_1p_bottle())))
    if k == 1 then shot("clr1_stage_clear"); dump("clr1_stage_clear") end
    wait(200)
    press(0, { start = true }, 6, 10)
    local u = 0
    while (mode() ~= 4 or rd(0x0324) == 0) and u < 3000 do step(); u = u + 1 end
    local cc, nn = only_viruses_or_empty(1)
    logf(string.format("CLEAR1P clr%d next level lvl=%d clean=%s viruses=%d after %d frames", k, rd(0x0316), tostring(cc), nn, u))
  end
  -- top out on the level after the clears
  policy[0] = "drop"
  local snap, _, why = play_until_end(20000, nil, 1)
  policy[0] = "idle"; pad[0] = {}
  if why ~= "ended" then logf("ROUND_TIMEOUT clear1p"); return end
  check_go1p("clr_go", snap, 600, true, false)
  if goto_play(1, false, 0, nil, 0) then
    local c1, n1 = only_viruses_or_empty(1)
    if c1 and n1 > 0 then stats.next1pClean = stats.next1pClean + 1 else stats.next1pDirty = stats.next1pDirty + 1 end
    logf(string.format("NEXT1P clr_next clean=%s viruses=%d", tostring(c1 and n1 > 0), n1))
    wait(60)
  end
end

function scenarios.twop()
  wait(240); shot("title")
  -- human vs human: P1, P2, P1, P2, P1 lose -> P2 wins the match 3-2 in round 5 (both loser sides exercised)
  play_match("m1", false, { 1, 2, 1, 2, 1 }, true, 1)
  -- the next match must start clean (wins 0/0, fields = fresh viruses only); play it to the final too
  play_match("m2", false, { 2, 2, 2 }, true, 2)
end

-- the romhacking.net screenshot set: a realistic 2P board (level 10 vs 10, both players active
-- for a while before one tops out), STUDY pause mid-round, round end, match final
function scenarios.shots()
  wait(240); shot("title")
  press(0, { start = true }, 6, 60); shot("level_select_1p")
  play_match("sh", false, { 2, 1, 2, 2 }, true, 1, { level1 = 10, level2 = 10, warmup = 1500, pauseAt = 200 })
  -- 1P: level 10 MED, STUDY pause at 500, random play until it tops out by itself (or 20000 frames)
  play_1p("sh1p", 10, 500, 20000, true, { speed = 1 })
end

-- VS CPU (SELECT x2) at level 0 with P1 idle: rounds end without any scripted top-out on either side.
-- It was meant to reach a virus-clear (STAGE CLEAR) win; the in-cart CPU did not clear 4 viruses in
-- the measured runs, so ENDSCREEN reports clearWin=false -- STAGE CLEAR stays unexercised here.
function scenarios.cpuidle()
  wait(240)
  if not goto_play(2, true, 0, 0) then return end
  for round = 1, 3 do
    policy[0], policy[1] = "idle", "idle"
    local last1, last2, why = play_until_end(20000, nil, 2)
    if why ~= "ended" then logf("ROUND_TIMEOUT cpuidle r" .. round); return end
    stats.roundEnds = stats.roundEnds + 1
    local isFinal = rd(0x031E) >= 3 or rd(0x039E) >= 3
    check_end_screen("cw_r" .. round, last1, last2, isFinal, true)
    if isFinal then return end
    wait(250); press(0, { start = true }, 6, 10)
    if not wait_mode(4, 3000, "next round") then return end
  end
end

-- rounds won by CLEARING all viruses (the common way real 2P rounds end), incl. a match final decided
-- by a clear: P1 wins r1, P2 wins r2, ... (the winner runs the solver, the other player "spread")
-- one 2P match decided by virus clears (the way most real 2P rounds end), incl. a match final decided by a
-- clear: P1 clears round 1, P2 round 2, ... (the round's winner runs the solver, the other "sides")
local function clear_match(tag, shots)
  stats.matches = stats.matches + 1
  if not goto_play(2, false, 0, 0) then return end
  if stats.matches > 1 then
    local c1, n1 = only_viruses_or_empty(1)
    local c2, n2 = only_viruses_or_empty(2)
    local clean = c1 and c2 and rd(0x031E) == 0 and rd(0x039E) == 0 and bottle_sprites(1) == 0 and bottle_sprites(2) == 0
    logf(string.format("NEXTMATCH %s clean=%s fieldsOnlyViruses=%s/%s viruses=%d/%d wins=%d/%d",
      tag, tostring(clean), tostring(c1), tostring(c2), n1, n2, rd(0x031E), rd(0x039E)))
    if clean then stats.nextClean = stats.nextClean + 1 else stats.nextDirty = stats.nextDirty + 1 end
    if shots then wait(2); shot(tag .. "_start") end
  end
  local round = 1
  while round <= 7 do
    local w = (round % 2 == 1) and 0 or 1
    policy[w], policy[1 - w] = "solver", "sides"
    sol[0].n, sol[1].n = -1, -1
    local last1, last2, why = play_until_end(30000, nil, 2)
    policy[0], policy[1] = "idle", "idle"
    stats.roundEnds = stats.roundEnds + 1
    if why == "clear" then
      stats.clearWins = (stats.clearWins or 0) + 1
      if not check_clear_screen(tag .. "_r" .. round, last1, last2, shots) then return end
      round = round + 1
      goto continue
    end
    if why ~= "ended" then logf("ROUND_TIMEOUT " .. tag .. " r" .. round); return end
    do
      local isFinal = rd(0x031E) >= 3 or rd(0x039E) >= 3
      check_end_screen(tag .. "_r" .. round, last1, last2, isFinal, shots)
      if isFinal then
        stats.finals = stats.finals + 1
        wait(30); press(0, { start = true }, 6, 30)
        local u = 0
        while mode() == 7 and u < 300 do step(); u = u + 1 end
        vars(tag .. " after-final-START")
        return
      end
    end
    wait(250); press(0, { start = true }, 6, 10)
    if not wait_mode(4, 3000, "next round") then return end
    round = round + 1
    ::continue::
  end
end

function scenarios.clearwin()
  wait(240); shot("title")
  clear_match("cw", true)
  clear_match("cw2", true)                        -- the match after a clear-win final starts clean
end

function scenarios.soak()
  wait(200)
  local k = 0
  while frame < SOAK_FRAMES do
    k = k + 1
    local pick = k % 5
    if pick == 1 then
      play_1p("s1p_" .. k, rand(11), rand(2) == 0 and (60 + rand(400)) or nil, 600 + rand(2400), false)
    elseif pick == 2 or pick == 3 then
      local plan = {}
      for i = 1, 5 do plan[i] = 1 + rand(2) end
      play_match("s2p_" .. k, false, plan, false, 1 + rand(3), { level1 = rand(15), level2 = rand(15) })
    elseif pick == 4 then
      clear_match("sclr_" .. k, false)
    else
      play_match("scpu_" .. k, true, { 1 }, false, 1)
      -- disarm for the next human match: power through the title cursor logic (SELECT toggles)
    end
  end
end

function scenarios.pilldebug()
  wait(240)
  goto_play(1, false, 0)
  local lastN = -1
  for i = 1, 600 do
    local a = (i % 120 == 10) and { a = true } or ((i % 120 == 30) and { left = true } or ((i % 120 > 60) and { down = true } or {}))
    pad[0] = a
    step()
    if i % 5 == 0 or rd(0x0327) ~= lastN then
      logf(string.format("PILL i=%d n=%d c0=%d c1=%d col=%d row=%d dir=%d | zp81=%d zp82=%d zp85=%d zp86=%d zpA5=%d",
        i, rd(0x0327), rd(0x0301), rd(0x0302), rd(0x0305), rd(0x0306), rd(0x0325), rd(0x81), rd(0x82), rd(0x85), rd(0x86), rd(0xA5)))
      lastN = rd(0x0327)
    end
  end
  dump("pilldebug")
end

function scenarios.p2debug()
  wait(240)
  goto_play(2, false, 0)
  wait(60)
  for k, btn in ipairs({ { left = true }, { right = true }, { down = true } }) do
    local c0, r0 = rd(0x0385), rd(0x0386)
    for i = 1, 40 do pad[1] = (i % 4 < 2) and btn or {}; step() end
    pad[1] = {}
    logf(string.format("P2DEBUG btn%d col %d->%d row %d->%d  P1 col=%d row=%d  $F6=%02X $F8=%02X",
      k, c0, rd(0x0385), r0, rd(0x0386), rd(0x0305), rd(0x0306), rd(0xF6), rd(0xF8)))
  end
end

-------------------------------------------------------------------------- frame loop
local co = coroutine.create(function()
  local f = scenarios[SCEN]
  if not f then logf("unknown scenario " .. SCEN); return end
  f()
end)

emu.addEventCallback(function()
  frame = frame + 1
  local m = rd(0x46)
  if m ~= lastMode then
    logf(string.format("MODE f=%d %d->%d", frame, lastMode, m))
    stats.modes[m] = (stats.modes[m] or 0) + 1
    lastMode, modeSince = m, frame
  end
  local clk = rd(0x43)
  if clk == lastClock then clockStall = clockStall + 1 else clockStall = 0 end
  lastClock = clk
  if clockStall > stats.maxClockStall then stats.maxClockStall = clockStall end
  -- per-frame RAM hash (full $0000-$07FF, and minus the stack page = CPU-phase noise), plus a third
  -- one that also leaves out both fields ($0400-$05FF), the $00/$01 fill pointer and the OAM-shadow Y
  -- bytes of the 5 START-prompt letters ($0200/4/8/C/$0210): "everything but the boards and the prompt
  -- position" -- measured, the v11 1P game-over hold differs from v10 in exactly those bytes
  if m == 4 or m == 5 then snapF1, snapF2 = field(1), field(2) end
  local h, hm, hx = 0, 0, 0
  for a = 0, 0x7FF do
    local v = rd(a); h = (h * 31 + v) % 2147483647
    if a < 0x100 or a >= 0x200 then
      hm = (hm * 31 + v) % 2147483647
      if a >= 2 and (a < 0x400 or a >= 0x600) and not (a >= 0x200 and a <= 0x210 and a % 4 == 0) then
        hx = (hx * 31 + v) % 2147483647
      end
    end
  end
  hf:write(string.format("%d %d %d %d %d\n", frame, m, h, hm, hx))
  for _, r in ipairs(FULL) do
    if frame >= r[1] and frame <= r[2] then hf:write("R " .. frame .. " " .. hexrow(0, 0x800) .. "\n") end
  end

  if ramExec > 0 then
    local st = emu.getState()
    logf(string.format("FREEZE ram-exec first at f%d pc=%04X", ramExecFirst or -1, st["cpu.pc"] or -1))
    shot("FREEZE"); dump("FREEZE"); finish(3, "ram-exec"); return
  end
  if clockStall > 120 then
    local st = emu.getState()
    logf(string.format("FREEZE clock-stall %d frames at f%d mode=%d pc=%04X", clockStall, frame, m, st["cpu.pc"] or -1))
    shot("FREEZE"); dump("FREEZE"); finish(3, "clock-stall"); return
  end
  -- no progress: outside the title / START-wait screens, neither capsule counter nor the top state
  -- has changed for 3000 frames (a long round is fine as long as capsules keep coming)
  local pills = rd(0x0327) * 256 + rd(0x03A7)
  if pills ~= lastPills or m ~= 4 then lastPills, pillsSince = pills, frame end
  if (m == 4 and frame - pillsSince > 3000) or (m ~= 7 and m ~= 0 and m ~= 4 and frame - modeSince > 3000) then
    logf(string.format("FREEZE no-progress: mode %d, capsules unchanged for %d frames", m, frame - pillsSince))
    shot("FREEZE"); dump("FREEZE"); finish(3, "no-progress"); return
  end

  if coroutine.status(co) == "suspended" then
    local ok, err = coroutine.resume(co)
    if not ok then logf("SCRIPT_ERROR " .. tostring(err)); finish(4, "script error"); return end
  end
  if coroutine.status(co) == "dead" then finish(0, "scenario complete") end
end, emu.eventType.endFrame)

logf(string.format("QA start scen=%s seed=%d", SCEN, SEED))
