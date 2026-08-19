-- ============================================================================
-- stomp_census.lua — hunt the REMATCH-TRANSIT RAM stomp on the v2 Pocket tuck cart
-- (v6e-tuck-pocket.nes, md5 d33dfa2b; run the MMC1 remap tuckv2_mmc1.nes).
--
-- Task #46. Field evidence (Pocket, theta400 core): across ~3 match transits the
-- OPTIONS screen accumulates corruption -- music silently OFF, music row rendering
-- hex-like garbage glyphs, cursor scrolling outside the 3 music options, eventually
-- a full bork that SURVIVES RESET.
--
-- Instrument design (raw facts only; all verdicts offline):
--   1. STATE SNAPSHOT at every options-screen visit: zero page $00-$FF, the options
--      page $0700-$07FF, and PRG-RAM $6000-$61FF (persists across reset -- the
--      "survives reset" signature). Visit 1 is the pre-match baseline; every later
--      visit is a rematch transit. Offline diff = the victim map.
--   2. NAMETABLE dump per visit (tile garbage is a PPU fact, not a RAM fact).
--   3. WRITE CENSUS with PC on a watchlist of victim addresses. Mesen forbids emu.*
--      inside a memory callback, so PC capture is opt-in (SC_PC=1): the callback may
--      die after firing, which is fine -- we want the FIRST stomp's PC.
--   4. Per-frame WRITE TRIPWIRE (pure Lua, no emu.*) on the watchlist: records
--      (addr, value, frame, mode-at-last-endFrame) for every write, always on.
--
-- We are the human (P1): the cart is DRHUMAN=1, so autonav never presses START.
-- SC_KEEPALIVE=1 erases P1's non-virus cells so P1 never tops out (bot wins by race);
-- SC_KEEPALIVE=0 lets P1 stack and TOP OUT (the field condition -- owner topped out).
--
-- Env: SC_OUT (dir), SC_MAXF, SC_RLAT, SC_DLAT, SC_SEED, SC_KEEPALIVE, SC_PC, SC_SHOTS
-- ============================================================================

local OUT   = os.getenv("SC_OUT") or "."
local MAXF  = tonumber(os.getenv("SC_MAXF")  or "120000")
local RLAT  = tonumber(os.getenv("SC_RLAT")  or "2")
local DLAT  = tonumber(os.getenv("SC_DLAT")  or "12")
local SEED  = tonumber(os.getenv("SC_SEED")  or "1")
local KEEP  = tonumber(os.getenv("SC_KEEPALIVE") or "0")
local WANTPC= tonumber(os.getenv("SC_PC")    or "0")
local SHOTS = tonumber(os.getenv("SC_SHOTS") or "1")
-- SELF-TEST (killed-mutant control for the GARBLE detector): synthesise the exact OAM
-- signature STUDYCOUNTS would leave on a menu screen. A detector that does not fire here is
-- not measuring anything, so no clean run may be reported without this control passing.
local SELFTEST = tonumber(os.getenv("SC_SELFTEST") or "0")

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end

local logf = io.open(OUT .. "/run.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end
local wcsv = io.open(OUT .. "/writes.csv", "w")
wcsv:write("frame,mode,addr,value,pc\n")
local scsv = io.open(OUT .. "/snapshots.csv", "w")
scsv:write("visit,frame,mode,region,addr,value\n")
-- per-frame trace of the options screen: the victim bytes plus the 8 STUDYCOUNTS digit
-- sprites (OAM slots 8-15). Slot Y=$FF means "blanked off-screen" (the v8.2 garble fix);
-- any other Y on a menu screen IS the leak the field reported as garbage glyphs.
local tcsv = io.open(OUT .. "/optrace.csv", "w")
tcsv:write("frame,mode,visit,cur65,music0731,speed45,lvl96,p727,z04,s4y,s4t,s4x,s5y,s5t,s5x,s6y,s6t,s6x,s7y,s7t,s7x,s8y,s8t,s8x,s9y,s9t,s9x,s10y,s10t,s10x,s11y,s11t,s11x,s12y,s12t,s12x,s13y,s13t,s13x,s14y,s14t,s14x,s15y,s15t,s15x\n")

local function shot(name)
  local ok, p = pcall(function() return emu.takeScreenshot() end)
  if ok and p then local f = io.open(OUT .. "/" .. name, "wb"); f:write(p); f:close() end
end

-- ---------- deterministic LCG for per-round seed pokes ----------
local lcg = SEED
local function nextrand()
  lcg = (lcg * 1103515245 + 12345) % 2147483648
  return math.floor(lcg / 65536) % 256
end

-- ============================ copro mailbox ============================
-- Single-window DRPOCKET build: W=$5000 serves P2 (board $0500, colors $0381/$0382).
local W = 0x5000
local S = { board = {}, done = false, go_frame = -1, res_frame = -1, done_frame = -1,
            rcol = 0, ror = 0xFF, pending = false, need_snap = false,
            goes = 0, dones = 0, cA = 0, cB = 0, go_pulse = false }
for i = 0, 127 do S.board[i] = 0xFF end
local curFrame = 0

local function occupied(bd, r, c)
  if r < 0 or r > 15 or c < 0 or c > 7 then return true end
  local v = bd[r * 8 + c]; return v ~= 0xFF and v ~= 0x00
end
-- emptiest-column vertical brain: enough to keep the bot playing full games.
local function brain(bd)
  local bestCol, bestFill = 0, 99
  for c = 0, 7 do
    local fill = 0
    for r = 0, 15 do if occupied(bd, r, c) then fill = fill + 1 end end
    if fill < bestFill then bestFill = fill; bestCol = c end
  end
  return bestCol, 0
end

local function compute_if_due()
  if S.ror ~= 0xFF then return end
  if S.pending and not S.need_snap and (curFrame - S.go_frame) >= RLAT then
    local c, o = brain(S.board)
    S.rcol = c % 8; S.ror = o % 4; S.res_frame = curFrame
  end
end

emu.addMemoryCallback(function(addr, value)
  S.go_frame = curFrame; S.done = false; S.pending = true; S.need_snap = true
  S.ror = 0xFF; S.res_frame = -1; S.done_frame = -1
  S.goes = S.goes + 1; S.go_pulse = true
end, emu.callbackType.write, W + 0x84)

emu.addMemoryCallback(function(addr, value)
  if S.done then return 1 end
  compute_if_due()
  if S.pending and not S.need_snap and (curFrame - S.go_frame) >= DLAT and S.ror ~= 0xFF then
    S.done = true; S.pending = false; S.dones = S.dones + 1; S.done_frame = curFrame
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)

emu.addMemoryCallback(function(addr, value)
  compute_if_due()
  if S.ror == 0xFF then return 0 end
  return S.rcol
end, emu.callbackType.read, W + 0x85)

emu.addMemoryCallback(function(addr, value)
  compute_if_due()
  return S.ror
end, emu.callbackType.read, W + 0x86)

-- ======================= victim write tripwire =======================
-- Watchlist: the options-screen state the field report implicates, plus the driver's
-- own known menu writes (so a stomp can be told apart from intended maintenance).
--   $0731 music type      $0727 nbPlayers      $65 game-option cursor
--   $04 VS flag           $51 waitFrames       $46 mode
--   $0740 anti-piracy     $45 speed            $96 level cursor
local WATCH = { 0x0731, 0x0727, 0x0065, 0x0004, 0x0051, 0x0046, 0x0740, 0x0045, 0x0096 }
local frame, modeCache = 0, -1
local wrote = {}          -- pure-Lua ring; drained in endFrame (no emu.* in callbacks)
local wn = 0
local WMAX = 40000

for _, a in ipairs(WATCH) do
  if WANTPC == 1 then
    -- PC capture: emu.getState() inside a write callback is FORBIDDEN by the harness
    -- rules and may kill the callback. That is acceptable here -- we want the FIRST
    -- offending write's PC, and a dead callback is itself logged (count stops rising).
    emu.addMemoryCallback(function(addr, value)
      local pc = -1
      local ok, st = pcall(function() return emu.getState() end)
      if ok and st and st.cpu then pc = st.cpu.pc end
      if wn < WMAX then wn = wn + 1; wrote[wn] = { frame, modeCache, addr, value, pc } end
    end, emu.callbackType.write, a)
  else
    emu.addMemoryCallback(function(addr, value)
      if wn < WMAX then wn = wn + 1; wrote[wn] = { frame, modeCache, addr, value, -1 } end
    end, emu.callbackType.write, a)
  end
end

-- ================= OAM WRITE ATTRIBUTION (task #46 decisive test) =================
-- The pixel-watch detector (check_garble) cannot attribute a menu sprite to a writer:
-- the driver's digit X/Y constants were MEASURED FROM the game's own layout, so a
-- driver-drawn and a game-drawn digit are positionally identical. Watch the WRITE
-- instead and record WHO wrote it.
--
-- ⚠ emu.getState() returns a FLAT DOTTED-KEY map: st["cpu.pc"] is the PC and st.cpu is
-- nil (README_GATE.md line 61). stomp_census3.lua's SC_PC path reads st.cpu.pc, so it
-- records pc=-1 for every write -- a silent no-op. That bug is why this file exists.
local oamLastPC = {}      -- slot -> PC of the last write to any of its 4 bytes
local oamPCHist = {}      -- PC -> number of OAM writes from it
local staleHits = {}      -- PC -> menu-frame sightings of a sprite it wrote last
local staleTotal = 0
local pcProbeOk, pcProbeFail = 0, 0

for _slot = 0, 15 do
  local slot = _slot
  for b = 0, 3 do
    emu.addMemoryCallback(function(addr, value)
      local pc = -1
      local ok, st = pcall(emu.getState)
      if ok and type(st) == "table" then
        pc = st["cpu.pc"] or (st.cpu and st.cpu.pc) or -1
      end
      if pc >= 0 then pcProbeOk = pcProbeOk + 1 else pcProbeFail = pcProbeFail + 1 end
      oamLastPC[slot] = pc
      oamPCHist[pc] = (oamPCHist[pc] or 0) + 1
    end, emu.callbackType.write, 0x0200 + slot * 4 + b)
  end
end

-- On a NON-PLAY screen every sprite still visible (Y ~= $FF) is charged to whoever wrote
-- it last. This is the number that must read ZERO on a cart with the feature compiled
-- out -- and it is MEASURED, not defined-to-be-zero.
local function attribute_stale(mode)
  if mode == 4 then return end
  for slot = 0, 15 do
    if rd(0x0200 + slot * 4) ~= 0xFF then
      local pc = oamLastPC[slot] or -1
      staleHits[pc] = (staleHits[pc] or 0) + 1
      staleTotal = staleTotal + 1
    end
  end
end

local function report_attribution()
  log(string.format("PCPROBE ok=%d fail=%d", pcProbeOk, pcProbeFail))
  local rows = {}
  for pc, n in pairs(oamPCHist) do rows[#rows + 1] = { pc, n, staleHits[pc] or 0 } end
  table.sort(rows, function(x, y) return x[2] > y[2] end)
  for i = 1, #rows do
    log(string.format("OAMPC pc=%04X writes=%d stale_menu_sightings=%d",
                      rows[i][1], rows[i][2], rows[i][3]))
  end
  log(string.format("STALE_TOTAL %d distinct_pcs=%d", staleTotal, #rows))
end

local function drain_writes()
  for i = 1, wn do
    local r = wrote[i]
    wcsv:write(string.format("%d,%d,%04X,%02X,%s\n", r[1], r[2], r[3], r[4],
      r[5] >= 0 and string.format("%04X", r[5]) or ""))
  end
  if wn > 0 then wcsv:flush() end
  wn = 0
end

-- ======================= options-screen snapshots =======================
local visit = 0
local snapArm = 0
local snappedVisit = -1

local function dump_region(v, tag, base, n)
  for i = 0, n - 1 do
    scsv:write(string.format("%d,%d,%d,%s,%04X,%02X\n", v, frame, modeCache, tag, base + i, rd(base + i)))
  end
end

local function dump_nametable(v)
  local mt = emu.memType.nesPpuMemory or emu.memType.ppuMemory
  if not mt then log("NT_DUMP unavailable: no ppu memType"); return end
  local ok, err = pcall(function()
    local f = io.open(OUT .. string.format("/nt_visit%02d.hex", v), "w")
    for row = 0, 29 do
      local t = {}
      for col = 0, 31 do
        t[#t + 1] = string.format("%02X", emu.read(0x2000 + row * 32 + col, mt, false))
      end
      f:write(table.concat(t, " ") .. "\n")
    end
    f:close()
  end)
  if not ok then log("NT_DUMP failed: " .. tostring(err)) end
end

local function snapshot_options()
  visit = visit + 1
  log(string.format("SNAPSHOT %d f=%d mode=%d p727=%02X z04=%02X music0731=%02X cur65=%02X",
    visit, frame, modeCache, rd(0x0727), rd(0x04), rd(0x0731), rd(0x65)))
  dump_region(visit, "zp",    0x0000, 256)
  dump_region(visit, "oam",   0x0200, 256)
  dump_region(visit, "page7", 0x0700, 256)
  dump_region(visit, "prgram",0x6000, 512)
  dump_nametable(visit)
  if visit <= SHOTS + 8 then shot(string.format("options_visit%02d.png", visit)) end
  scsv:flush()
end

-- ---------- input injection (we are the human P1) ----------
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
  if not (live == 8) then return false end
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

-- ---------- main loop ----------
local prevMode = -1
local round = 0
local seedPokedRound = -1
local dwell = 0
local optionsDwell = 0
local stopped = false
local lastActivity = 0

local optT = 0
local pauseT = 0
-- STUDYCOUNTS draws its 8 digit sprites at these two Y rows (emitter: ytop 0xBF for the
-- virus counters, 0x2B for the level counters). Seeing either on a NON-PLAY screen means a
-- play-path digit write survived onto a menu -- on the options screen y=0xBF is pixel row
-- 191, i.e. exactly the FEVER/CHILL/OFF row, which is where the field saw garbage glyphs.
-- SPECIFICITY (a first cut fired on the settings screen's OWN box sprites, which happen to
-- sit at y=$BF too): a STUDYCOUNTS digit is identified by the CONJUNCTION of its Y row, one
-- of the eight X columns the emitter hard-codes, and a tile index <= $0F (the digit tiles are
-- raw nibble/decimal values). The screen's box sprites use tiles $2E/$2F/$3F/$5F, so the tile
-- test alone already rejects them; all three are required so the detector cannot fire on any
-- sprite the base game draws.
local DIGIT_Y = { [0xBF] = true, [0x2B] = true }
local DIGIT_X = { [0x6D]=true,[0x6E]=true,[0x75]=true,[0x76]=true,
                  [0x83]=true,[0x84]=true,[0x8B]=true,[0x8C]=true }
local garbleHits = 0
local function check_garble(mode)
  if mode == 4 then return end
  for slot = 0, 15 do
    local y = rd(0x0200 + slot * 4)
    local t = rd(0x0200 + slot * 4 + 1)
    local x = rd(0x0200 + slot * 4 + 3)
    if DIGIT_Y[y] and DIGIT_X[x] and t <= 0x0F then
      garbleHits = garbleHits + 1
      if garbleHits <= 200 then
        local ys, ts = {}, {}
        for k = 8, 15 do
          ys[#ys + 1] = string.format("%02X", rd(0x0200 + k * 4))
          ts[#ts + 1] = string.format("%02X", rd(0x0200 + k * 4 + 1))
        end
        log(string.format("GARBLE f=%d mode=%d slot=%d y=%02X x=%02X t=%02X Y=[%s] T=[%s]",
          frame, mode, slot, y, x, t, table.concat(ys, " "), table.concat(ts, " ")))
      end
      return
    end
  end
end

local function trace_options()
  local t = { frame, modeCache, visit, rd(0x65), rd(0x0731), rd(0x45), rd(0x96), rd(0x0727), rd(0x04) }
  for slot = 4, 15 do
    t[#t + 1] = rd(0x0200 + slot * 4)       -- Y ($FF = blanked by the v8.2 garble fix)
    t[#t + 1] = rd(0x0200 + slot * 4 + 1)   -- tile index
    t[#t + 1] = rd(0x0200 + slot * 4 + 3)   -- X (identifies WHICH digit sprite)
  end
  tcsv:write(table.concat(t, ",") .. "\n")
end

local function finish_if_due()
  if frame >= MAXF and not stopped then
    stopped = true
    report_attribution()
    log(string.format("SUMMARY frames=%d rounds=%d visits=%d goes=%d dones=%d keepalive=%d pc=%d",
      frame, round, visit, S.goes, S.dones, KEEP, WANTPC))
    drain_writes()
    tcsv:flush(); tcsv:close(); wcsv:close(); scsv:close(); logf:close()
    pcall(function() emu.stop(0) end)
  end
end

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    local mode = rd(0x46); modeCache = mode
    drain_writes()
    if SELFTEST == 1 and mode ~= 4 and frame >= 200 and frame <= 203 then
      -- inject a virus-counter digit pair into slots 14/15 exactly as the emitter would
      wr(0x0200 + 14 * 4, 0xBF); wr(0x0200 + 14 * 4 + 1, 0x04); wr(0x0200 + 14 * 4 + 3, 0x83)
      wr(0x0200 + 15 * 4, 0xBF); wr(0x0200 + 15 * 4 + 1, 0x08); wr(0x0200 + 15 * 4 + 3, 0x8B)
      if frame == 200 then log("SELFTEST inject f=200 (expect GARBLE on f200-203)") end
    end
    check_garble(mode)
    attribute_stale(mode)
    if mode ~= 4 then trace_options() end

    if S.need_snap then
      for i = 0, 127 do
        local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v
      end
      S.cA = rd(0x0381) % 16; S.cB = rd(0x0382) % 16
      S.need_snap = false
    end

    -- MODE MACHINE: log every transition. The rematch flow's mode sequence is NOT
    -- assumed -- the field screen may not be modes 1..3, so we record the machine and
    -- snapshot every non-play screen we land on.
    if mode ~= prevMode then
      log(string.format("MODE %d -> %d f=%d round=%d p727=%02X z04=%02X music=%02X cur65=%02X",
        prevMode, mode, frame, round, rd(0x0727), rd(0x04), rd(0x0731), rd(0x65)))
      snapArm = (mode ~= 4) and 30 or 0
    end

    if mode ~= 4 then
      -- Snapshot ONCE per screen visit, after a settle dwell so the screen's own init
      -- has finished writing.
      if snapArm > 0 then
        snapArm = snapArm - 1
        if snapArm == 0 then snapshot_options() end
      end
      if mode >= 1 and mode <= 3 then
        -- ===== BE THE HUMAN ON THE OPTIONS SCREEN =====
        -- The field corruption was seen by an owner who SITS on this screen and works the
        -- cursor. The earlier pass pressed START within ~85 frames and never touched the
        -- cursor, so it could not have exercised the music option at all. Here we dwell,
        -- walk the cursor with DOWN, and change the music setting with LEFT/RIGHT before
        -- starting the next match.
        optT = optT + 1
        if optT == 1 then
          log(string.format("OPTNAV begin f=%d mode=%d cur65=%02X music=%02X", frame, mode, rd(0x65), rd(0x0731)))
        end
        -- seed variation per round so rounds are not identical
        if seedPokedRound ~= round then
          local s1, s2 = nextrand(), nextrand()
          if s1 == 0 and s2 == 0 then s1 = 0x89 end
          wr(0x17, s1); wr(0x18, s2)
          seedPokedRound = round
          log(string.format("SEEDPOKE f=%d round=%d s17=%02X s18=%02X", frame, round + 1, s1, s2))
        end
        -- scripted navigation, 16 frames per step (press 4, release 12)
        local step = math.floor(optT / 16)
        if optT % 16 == 1 then
          if     step < 6  then press({ down  = true }, 4)
          elseif step < 10 then press({ right = true }, 4)
          elseif step < 12 then press({ left  = true }, 4)
          elseif step < 16 then press({ down  = true }, 4)
          elseif step == 16 then
            snapshot_options()   -- post-navigation state: the screen the owner is looking at
            log(string.format("OPTNAV end f=%d cur65=%02X music=%02X", frame, rd(0x65), rd(0x0731)))
          elseif step >= 18 then press({ start = true }, 4) end
        end
      else
        optT = 0
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      lastActivity = frame
      finish_if_due()
      return
    end

    if prevMode ~= 4 then
      round = round + 1; pauseT = 0
      log(string.format("ROUND %d start f=%d seed=%02X%02X p727=%d z04=%d music=%02X",
        round, frame, rd(0x17), rd(0x18), rd(0x0727), rd(0x04), rd(0x0731)))
    end

    -- ===== PAUSE INTO THE STUDY SCREEN =====
    -- DRSTUDY/DRSTUDY2P/DRSTUDYCOUNTS only render on the PAUSE screen, and STUDYCOUNTS is what
    -- writes the digit sprites into OAM slots 8-15 at y=$BF/$2B. A harness that never pauses
    -- never exercises the blob the field report implicates, so pause periodically like a player
    -- reviewing the board, then unpause and let the match run on.
    pauseT = pauseT + 1
    if pauseT == 300 then
      press({ start = true }, 4)
      log(string.format("PAUSE f=%d round=%d", frame, round))
    elseif pauseT == 480 then
      press({ start = true }, 4)
      log(string.format("UNPAUSE f=%d round=%d", frame, round))
    elseif pauseT >= 640 then
      pauseT = 0
    end

    if KEEP == 1 then
      for i = 0, 127 do
        local v = rd(0x0400 + i)
        if v ~= 0xFF and v ~= 0x00 and math.floor(v / 16) ~= 0x0D then wr(0x0400 + i, 0xFF) end
      end
    end
    -- KEEP == 0: P1 (us) does nothing -> stacks in the spawn column -> TOPS OUT.
    -- That is the field condition; we deliberately do not play.

    S.go_pulse = false
    lastActivity = frame
    finish_if_due()
  end)
  if not ok then log("LUA_ERROR f=" .. frame .. " " .. tostring(err)) end
  prevMode = modeCache
end, emu.eventType.endFrame)

log(string.format("stomp_census loaded RLAT=%d DLAT=%d MAXF=%d SEED=%d KEEP=%d PC=%d out=%s",
  RLAT, DLAT, MAXF, SEED, KEEP, WANTPC, OUT))
