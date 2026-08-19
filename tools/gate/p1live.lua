-- ============================================================================
-- p1live.lua -- fieldplay plus an IN-PLAY P1 controller exercise, for the #101
-- Pocket session failure ("P1 inputs mostly dead, P2 suicides in seconds").
-- fieldplay only presses START in the menus, so it can show that P1 input reaches
-- the menu code while telling you nothing about P1 during a live match -- which is
-- exactly where the owner saw the fault.  Here P1 is walked left/right through
-- mode 4 and $0305 (P1 capsule X) is watched for a matching response.
--
-- The v6c acceptance harness (census_run_dist.lua) keeps P1 alive on purpose so P2
-- plays unbroken games; that instrument means a match NEVER ENDS, so DRHOLDBOARD --
-- the one flag the ship cart turns on and every acceptance cart left off -- is never
-- exercised.  This harness does the opposite: P1 is left to top out exactly as an
-- idle human would, matches END, and the whole end-of-match -> hold -> title ->
-- next-match cycle runs.
--
-- Emulates the copro mailbox for P2 (window $5000, board $0500) per copro_emu.lua.
-- Mesen quirks obeyed: no emu.* inside memory callbacks; emu.write is 3-arg.
--
-- PATHOLOGY WATCH (the thing under test): HOLD_ACTIVE ($6195) != 0 while $0046 == 4.
-- In that state the driver's restore loop stamps HOLD_BUF1/2 ($6300/$6400) over the
-- LIVE playfields $0400/$0500 every hook and forces a PPU row-redraw drain, i.e. the
-- board on screen is a stale/garbage snapshot instead of the game.
--
-- Env: FP_OUT (dir), FP_MAXF, FP_DLAT, FP_SEED, FP_WARM (1 = simulate warm PRG-RAM:
--      MATCH_ACTIVE preset + HOLD_BUF garbage, the state a soft reset after a prior
--      game leaves behind), FP_TAG.
-- ============================================================================
local OUT   = os.getenv("FP_OUT")  or "."
local MAXF  = tonumber(os.getenv("FP_MAXF")  or "40000")
local DLAT  = tonumber(os.getenv("FP_DLAT")  or "34")
local SEED  = tonumber(os.getenv("FP_SEED")  or "114")
local WARM  = tonumber(os.getenv("FP_WARM")  or "0")
local TAG   = os.getenv("FP_TAG") or "run"
-- FP_P1DRIVE=1 exercises P1's controller DURING live play (mode 4).  0 is the
-- killed-mutant arm: the same cart with the stimulus removed, which must read
-- p1_moves=0, or this probe cannot tell a live P1 from a dead one.
local P1DRIVE = tonumber(os.getenv("FP_P1DRIVE") or "1")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end

local logf = io.open(OUT .. "/run.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end
local csv = io.open(OUT .. "/frames.csv", "w")
csv:write("frame,mode,match_active,hold_active,hold_cnt,vc1,vc2,capy,fill1,fill2,eff_dist2,s2p_ttl\n")

local W = 0x5000
local MATCH_ACTIVE, HOLD_ACTIVE = 0x6164, 0x6195
local HOLD_CNT, HOLD_BUF1, HOLD_BUF2 = 0x6197, 0x6300, 0x6400
local EFF_DIST2, S2P_TTL = 0x6194, 0x61B0

local function shot(name)
  local ok, p = pcall(emu.takeScreenshot)
  if not ok or not p then return end
  local f = io.open(OUT .. "/" .. name, "wb"); f:write(p); f:close()
end

-- ---------------- copro mailbox (pure-Lua state in the callbacks) ----------------
local S = { board = {}, done = false, go_f = -1, rcol = 0, ror = 0xFF,
            pending = false, need_snap = false, goes = 0, dones = 0, cA = 0, cB = 0 }
for i = 0, 127 do S.board[i] = 0xFF end
local curFrame = 0

local function brain(bd)
  local bestCol, bestFill = 0, 99
  for c = 0, 7 do
    local fill = 0
    for r = 0, 15 do local v = bd[r * 8 + c]; if v ~= 0xFF and v ~= 0x00 then fill = fill + 1 end end
    if fill < bestFill then bestFill = fill; bestCol = c end
  end
  return bestCol, 0
end

emu.addMemoryCallback(function()
  S.go_f = curFrame; S.done = false; S.pending = true; S.need_snap = true
  S.ror = 0xFF; S.goes = S.goes + 1
end, emu.callbackType.write, W + 0x84)

emu.addMemoryCallback(function()
  if S.done then return 1 end
  if S.pending and not S.need_snap and (curFrame - S.go_f) >= DLAT then
    local c, o = brain(S.board)
    S.rcol = c % 8; S.ror = o % 4
    S.done = true; S.pending = false; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)

-- ---------------- input ----------------
local frame, modeCache = 0, -1
local inCur, inUntil = nil, -1
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
  if inCur and frame < inUntil and not d135_block(inCur) then
    emu.setInput(inCur, 0)
  end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

-- ---------------- main loop ----------------
local lcg = SEED
local function nextrand() lcg = (lcg * 1103515245 + 12345) % 2147483648; return math.floor(lcg / 65536) % 256 end

local prevMode, prevHold = -1, -1
local lvlPoked, seedPokedRound, round = false, -1, 0
local pathoFrames, pathoFirst = 0, -1
local holdEpisodes, shotN = 0, 0
local warmDone = false
local matchesEnded = 0

-- ---- P1 in-play liveness + P2 survival accounting ----
local P1X, P1Y, P2Y = 0x0305, 0x0306, 0x0386
local p1Windows, p1Moves, p1Agree, p1Disagree = 0, 0, 0, 0
local p1PrevX, p1Dir = -1, 0
local p1XSeen = {}
local playFrames, matchPlayFrames, minMatchPlay = 0, 0, -1
local p2Locks, p2PrevY = 0, -1

local function fill_of(base)
  local n = 0
  for i = 0, 127 do local v = rd(base + i); if v ~= 0x00 and v ~= 0xFF then n = n + 1 end end
  return n
end

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame

    -- WARM arm: at f5 install the PRG-RAM state a soft reset after a prior game leaves.
    if WARM == 1 and not warmDone and frame == 5 then
      wr(MATCH_ACTIVE, 1)
      for i = 0, 255 do wr(HOLD_BUF1 + i, (i * 7 + 0x41) % 256); wr(HOLD_BUF2 + i, (i * 13 + 0x23) % 256) end
      warmDone = true
      log(string.format("WARM f=%d MATCH_ACTIVE<-1, HOLD_BUF1/2 <- garbage pattern", frame))
    end

    local mode = rd(0x46); modeCache = mode
    local ha, ma = rd(HOLD_ACTIVE), rd(MATCH_ACTIVE)
    local hc = rd(HOLD_CNT) + rd(HOLD_CNT + 1) * 256

    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.cA = rd(0x0381) % 16; S.cB = rd(0x0382) % 16
      S.need_snap = false
    end

    -- ---- PATHOLOGY: hold armed during live play ----
    if ha ~= 0 and mode == 4 then
      pathoFrames = pathoFrames + 1
      if pathoFirst < 0 then
        pathoFirst = frame
        log(string.format("*** PATHOLOGY f=%d: HOLD_ACTIVE=%d while mode=4 (live play) ***", frame, ha))
        shot(string.format("%s_patho_f%06d.png", TAG, frame))
      end
    end

    -- ---- hold episode edges ----
    if ha ~= 0 and prevHold == 0 then
      holdEpisodes = holdEpisodes + 1
      log(string.format("HOLD ARM f=%d ep=%d mode=%d match_active=%d vc1=%d vc2=%d",
                        frame, holdEpisodes, mode, ma, rd(0x0324), rd(0x03A4)))
      if shotN < 12 then shotN = shotN + 1; shot(string.format("%s_holdarm%02d_f%06d_m%d.png", TAG, holdEpisodes, frame, mode)) end
    elseif ha == 0 and prevHold ~= 0 and prevHold ~= -1 then
      log(string.format("HOLD REL f=%d mode=%d held=%d", frame, mode, hc))
      if shotN < 12 then shotN = shotN + 1; shot(string.format("%s_holdrel%02d_f%06d_m%d.png", TAG, holdEpisodes, frame, mode)) end
    end

    -- ---- mode transitions ----
    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d hold=%d match=%d vc1=%d vc2=%d fill1=%d fill2=%d goes=%d dones=%d",
                        frame, prevMode, mode, ha, ma, rd(0x0324), rd(0x03A4),
                        fill_of(0x0400), fill_of(0x0500), S.goes, S.dones))
      if prevMode == 4 and mode ~= 4 then
        matchesEnded = matchesEnded + 1
        if minMatchPlay < 0 or matchPlayFrames < minMatchPlay then minMatchPlay = matchPlayFrames end
        log(string.format("MATCHEND f=%d n=%d play_frames=%d (%.1fs) vc1=%d vc2=%d p2_locks=%d",
                          frame, matchesEnded, matchPlayFrames, matchPlayFrames / 60.0,
                          rd(0x0324), rd(0x03A4), p2Locks))
        if shotN < 12 then shotN = shotN + 1; shot(string.format("%s_endmatch%02d_f%06d.png", TAG, matchesEnded, frame)) end
      end
      -- title screen after a match: the OBS "blue bars over (c)1990 Nintendo" check
      if mode == 0 and matchesEnded > 0 then
        shot(string.format("%s_title_after%02d_f%06d.png", TAG, matchesEnded, frame))
      end
      prevMode = mode
    end

    if frame % 4 == 0 then
      csv:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n", frame, mode, ma, ha, hc,
                rd(0x0324), rd(0x03A4), rd(0x0386), fill_of(0x0400), fill_of(0x0500),
                rd(EFF_DIST2), rd(S2P_TTL)))
    end
    prevHold = ha

    -- ---- menu driving: we are the human on a DRHUMAN cart ----
    if mode ~= 4 then
      if mode >= 1 and mode <= 3 then
        if not lvlPoked then
          if rd(0x0316) ~= 11 then wr(0x0316, 11) end
          if rd(0x0396) ~= 11 then wr(0x0396, 11) end
          wr(0x96, 11); wr(0x45, 1)
          lvlPoked = true
        end
        if seedPokedRound ~= round then
          local s1, s2 = nextrand(), nextrand()
          if s1 == 0 and s2 == 0 then s1 = 0x89 end
          wr(0x17, s1); wr(0x18, s2); seedPokedRound = round
          log(string.format("SEEDPOKE f=%d round=%d s17=%02X s18=%02X", frame, round + 1, s1, s2))
        end
        if frame % 12 == 0 then press({ start = true }, 4) end
      else
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      matchPlayFrames = 0
      p1PrevX, p1Dir = -1, 0
      return
    end
    if lvlPoked then lvlPoked = false; round = round + 1 end

    -- ---- live play: walk P1 and score the response ----
    playFrames = playFrames + 1
    matchPlayFrames = matchPlayFrames + 1

    local y2 = rd(P2Y)
    if p2PrevY >= 0 and y2 < p2PrevY - 2 then p2Locks = p2Locks + 1 end
    p2PrevY = y2

    local x1 = rd(P1X)
    p1XSeen[x1] = true
    if p1PrevX >= 0 and x1 ~= p1PrevX then
      p1Moves = p1Moves + 1
      -- Only score direction while a press is actually in flight; a capsule that
      -- moves on its own (respawn, DAS carry-over) must not be credited to us.
      if p1Dir ~= 0 then
        if (x1 - p1PrevX) * p1Dir > 0 then p1Agree = p1Agree + 1 else p1Disagree = p1Disagree + 1 end
      end
    end
    p1PrevX = x1

    if P1DRIVE == 1 then
      local phase = playFrames % 64
      if phase == 0 then
        press({ left = true }, 10); p1Dir = -1; p1Windows = p1Windows + 1
      elseif phase == 32 then
        press({ right = true }, 10); p1Dir = 1; p1Windows = p1Windows + 1
      elseif phase == 14 or phase == 46 then
        p1Dir = 0
      end
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF then
    local nx = 0; for _ in pairs(p1XSeen) do nx = nx + 1 end
    log(string.format("P1LIVE tag=%s p1drive=%d play_frames=%d p1_windows=%d p1_moves=%d " ..
                      "p1_agree=%d p1_disagree=%d p1_distinct_x=%d p2_locks=%d min_match_play=%d",
                      TAG, P1DRIVE, playFrames, p1Windows, p1Moves, p1Agree, p1Disagree,
                      nx, p2Locks, minMatchPlay))
    log(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d matches_ended=%d hold_episodes=%d " ..
                      "patho_frames=%d patho_first=%d", TAG, frame, S.goes, S.dones, matchesEnded,
                      holdEpisodes, pathoFrames, pathoFirst))
    shot(string.format("%s_final_f%06d.png", TAG, frame))
    csv:close(); logf:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("fieldplay start tag=%s maxf=%d dlat=%d seed=%d warm=%d", TAG, MAXF, DLAT, SEED, WARM))
