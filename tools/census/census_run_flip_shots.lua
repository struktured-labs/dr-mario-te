-- ============================================================================
-- census_run.lua — per-pill INTENDED-vs-LANDED logger for the v4 Pocket human cart
-- (pocket_human_v4_coldinit.nes, on-card md5 24dcd9dc; run the MMC1 remap v4_mmc1.nes).
--
-- Question (owner field report 2026-08-08): for every P2 (copro-driven) pill, does the
-- LANDED placement (board delta at lock) match the copro's COMMITTED placement (mailbox)?
--
-- Design: single-window DRPOCKET cart — window $5000 serves P2 (board $0500, colors
-- $0381/$0382). This script IS the copro (Lua mailbox emulator, per copro_emu.lua
-- contract), so the committed placement is known EXACTLY (we serve it). The landed
-- placement is recovered from the P2 board delta at lock. RAW facts only are logged;
-- all decoding/classification happens offline in decode_census.py (gate-able + mutant-
-- killable there).
--
-- Mesen quirk compliance (dr-mario-mesen-copro-harness / -qa memories):
--   * NO emu.* inside memory callbacks (pure-Lua state only; brain runs on a board
--     snapshot taken in endFrame).
--   * GO = single-address write callback on $5084; board from SOURCE RAM $0500.
--   * read-callback integer return overrides the CPU read (serves DONE/col/orient).
--   * emu.write takes THREE args (addr, value, type).
--
-- Instruments (deviations from pure cart behavior, all disclosed):
--   * P1 KEEP-ALIVE: every frame, P1 board ($0400) non-virus cells are erased so the
--     un-driven P1 never tops out / never clears -> P2 plays full games. P1 never
--     attacks (it can never match), so P2's board delta stays pill-only.
--   * SEED VARIATION: at each level-select visit, $0017/$0018 are poked with per-round
--     LCG values (the play_rom_live.py instrument) -> distinct virus layouts + capsule
--     streams per round. Values logged.
--   * MENU DRIVE: START/SELECT injected only when mode ~= 4 (autonav may or may not be
--     active on the DRHUMAN cart; injection is guarded and idempotent).
--
-- Env: CEN_OUT (dir, must exist), CEN_MAXF, CEN_RLAT (frames until mailbox result is
-- readable; models running-best publish), CEN_DLAT (frames until DONE flips), CEN_SHOTS
-- (screenshots of the first N locks), CEN_SEED (LCG init).
-- NOTE: this is a STABLE-TARGET census — the served result never changes mid-pill, so
-- mailbox running-best FLIPS are not modeled; measured mismatches are pure driver-
-- execution errors (a lower bound on the field rate).
-- ============================================================================

local OUT   = os.getenv("CEN_OUT") or "."
local MAXF  = tonumber(os.getenv("CEN_MAXF")  or "36000")
local RLAT  = tonumber(os.getenv("CEN_RLAT")  or "2")
local DLAT  = tonumber(os.getenv("CEN_DLAT")  or "12")
local SHOTS = tonumber(os.getenv("CEN_SHOTS") or "0")
local SEED  = tonumber(os.getenv("CEN_SEED")  or "1")
local FLIPF = tonumber(os.getenv("CEN_FLIPF") or "20")  -- frames after GO when running-best flips alt->best

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end

local logf = io.open(OUT .. "/run.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end
local csv = io.open(OUT .. "/census.csv", "w")
csv:write("seq,round,go_f,go_count,res_f,done_f,lock_f,cA,cB,ccol,co4,tgtC,tgtO,rotdone," ..
          "capx_prev,capy_prev,capor_prev,capx_lock,capy_lock,capor_lock," ..
          "h_go,vc_go,seed17,seed18,newcells,flag,acol,ao4,flipf\n")
local function shot(name)
  local p = emu.takeScreenshot()
  local f = io.open(OUT .. "/" .. name, "wb"); f:write(p); f:close()
end

-- ---------- tiny LCG for seed pokes (deterministic, logged) ----------
local lcg = SEED
local function nextrand()
  lcg = (lcg * 1103515245 + 12345) % 2147483648
  return math.floor(lcg / 65536) % 256
end

-- ---------- d1 greedy color-matching brain (pure Lua; runs on the GO snapshot) ------
local function occupied(bd, r, c)
  if r < 0 or r > 15 or c < 0 or c > 7 then return true end
  local v = bd[r * 8 + c]; return v ~= 0xFF and v ~= 0x00
end
local function toprow(bd, c)
  for r = 0, 15 do if occupied(bd, r, c) then return r end end
  return 16
end
local function cellinfo(bd, r, c, vcells)  -- returns color (0..2) or nil, isvirus
  if r < 0 or r > 15 or c < 0 or c > 7 then return nil, false end
  for _, vc in ipairs(vcells) do
    if vc[1] == r and vc[2] == c then return vc[3], false end
  end
  local v = bd[r * 8 + c]
  if v == 0xFF or v == 0x00 then return nil, false end
  return v % 16, (math.floor(v / 16) == 0x0D)
end
local function runlen(bd, r, c, dr, dc, col, vcells)
  local n, nv = 0, 0
  local rr, cc = r + dr, c + dc
  while true do
    local ccol, isv = cellinfo(bd, rr, cc, vcells)
    if ccol ~= col then break end
    n = n + 1; if isv then nv = nv + 1 end
    rr = rr + dr; cc = cc + dc
  end
  return n, nv
end
local function score_place(bd, cells)  -- cells = { {r,c,color}, {r,c,color} }
  local sc = 0
  for _, cl in ipairs(cells) do
    local r, c, col = cl[1], cl[2], cl[3]
    local hl, hlv = runlen(bd, r, c, 0, -1, col, cells)
    local hr, hrv = runlen(bd, r, c, 0, 1, col, cells)
    local vu, vuv = runlen(bd, r, c, -1, 0, col, cells)
    local vd, vdv = runlen(bd, r, c, 1, 0, col, cells)
    local hrun, hvir = 1 + hl + hr, hlv + hrv
    local vrun, vvir = 1 + vu + vd, vuv + vdv
    if hrun >= 4 then sc = sc + 800 + 400 * hvir end
    if vrun >= 4 then sc = sc + 800 + 400 * vvir end
    sc = sc + 12 * math.max(hrun, vrun) + 6 * r
    local bcol, bvir = cellinfo(bd, r + 1, c, cells)
    if bvir then
      if bcol == col then sc = sc + 60 else sc = sc - 40 end
    end
  end
  return sc
end
-- copro-space enumeration (decide_ship_d3 convention):
-- o4: 0 = V A-top, 1 = V B-top, 2 = H A-left, 3 = H B-left; col = left/only column.
local function brain(bd, cA, cB)   -- returns best AND runner-up (distinct placement)
  local bestc, besto, bestsc = 3, 0, -1e9
  local altc, alto, altsc = 3, 0, -1e9
  for o4 = 0, 3 do
    local maxc = (o4 >= 2) and 6 or 7
    for c = 0, maxc do
      local cells = nil
      if o4 < 2 then
        local t = toprow(bd, c)
        if t >= 2 then
          local topcol = (o4 == 0) and cA or cB
          local botcol = (o4 == 0) and cB or cA
          cells = { { t - 2, c, topcol }, { t - 1, c, botcol } }
        end
      else
        local t = math.min(toprow(bd, c), toprow(bd, c + 1))
        if t >= 1 then
          local lcol = (o4 == 2) and cA or cB
          local rcol = (o4 == 2) and cB or cA
          cells = { { t - 1, c, lcol }, { t - 1, c + 1, rcol } }
        end
      end
      if cells then
        local sc = score_place(bd, cells)
        if sc > bestsc then
          if bestsc > -1e9 then altsc = bestsc; altc = bestc; alto = besto end
          bestsc = sc; bestc = c; besto = o4
        elseif sc > altsc then
          altsc = sc; altc = c; alto = o4
        end
      end
    end
  end
  if altsc <= -1e9 then altc, alto = bestc, besto end
  return bestc, besto, altc, alto
end

-- ---------- mailbox emulator state (per copro_emu.lua, + RLAT running-best) ----------
local W = 0x5000
local S = { board = {}, go_pulse = false, pending = false, need_snap = false,
            go_frame = -1, res_frame = -1, done_frame = -1,
            rcol = 0xFF, ror = 0xFF, acol = 0xFF, aor = 0xFF,
            done = false, cA = 0, cB = 0, goes = 0, dones = 0 }
for i = 0, 127 do S.board[i] = 0xFF end
local curFrame = 0

local function compute_if_due()
  -- pure Lua; callable from read callbacks. Result becomes readable at RLAT.
  if S.pending and not S.need_snap and S.ror == 0xFF
     and (curFrame - S.go_frame) >= RLAT then
    local c, o, ac, ao = brain(S.board, S.cA, S.cB)
    S.rcol = c % 8; S.ror = o % 4          -- FINAL (post-flip) result
    S.acol = ac % 8; S.aor = ao % 4        -- provisional running-best served before FLIPF
    S.res_frame = curFrame
  end
end
local function serving()                    -- what the mailbox currently publishes
  if S.ror == 0xFF then return 0xFF, 0xFF end
  if (curFrame - S.go_frame) < FLIPF then return S.acol, S.aor end
  return S.rcol, S.ror
end

emu.addMemoryCallback(function(addr, value)  -- GO strobe (write $5084): pure Lua only
  S.go_pulse = true; S.pending = true; S.need_snap = true
  S.done = false; S.rcol = 0xFF; S.ror = 0xFF; S.acol = 0xFF; S.aor = 0xFF
  S.go_frame = curFrame; S.goes = S.goes + 1
end, emu.callbackType.write, W + 0x84)

emu.addMemoryCallback(function(addr, value)  -- DONE read
  if S.done then return 1 end
  compute_if_due()
  if S.pending and S.ror ~= 0xFF and (curFrame - S.go_frame) >= DLAT
     and (curFrame - S.go_frame) >= FLIPF then
    S.done = true; S.pending = false
    S.done_frame = curFrame; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)

emu.addMemoryCallback(function(addr, value)
  compute_if_due()
  local c, _ = serving()
  if c == 0xFF then return 0 end
  return c
end, emu.callbackType.read, W + 0x85)

emu.addMemoryCallback(function(addr, value)
  compute_if_due()
  local _, o = serving()
  return o
end, emu.callbackType.read, W + 0x86)

-- ---------- input injection ----------
local frame = 0
local modeCache = -1
local inCur, inUntil = nil, -1
local forceUntil = -1     -- honored even in mode 4 (unpause watchdog)
emu.addEventCallback(function()
  if inCur and frame < inUntil and (modeCache ~= 4 or frame < forceUntil) then
    emu.setInput(inCur, 0)
  end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

-- ---------- per-pill record keeping ----------
local rec = nil            -- open pill record
local seq, round = 0, 0
local shotN = 0
local mmShots = 0
local lastActivity = 0
local seed17, seed18 = -1, -1
local prevCap = { x = -1, y = -1, o = -1 }
local curCap  = { x = -1, y = -1, o = -1 }
local lvlPoked, seedPokedRound = false, -1
local dwell = 0

local function snap_board(dst, base)
  for i = 0, 127 do
    local v = rd(base + i); if v == 0x00 then v = 0xFF end
    dst[i] = v
  end
end
local function board_stats(bd)
  local h, vc = 0, 0
  for c = 0, 7 do local t = toprow(bd, c); if 16 - t > h then h = 16 - t end end
  for i = 0, 127 do
    local v = bd[i]
    if v ~= 0xFF and v ~= 0x00 and math.floor(v / 16) == 0x0D then vc = vc + 1 end
  end
  return h, vc
end
local function diff_new_cells(bd)  -- vs rec.snap; returns list of {r,c,byte}
  local out = {}
  for i = 0, 127 do
    local v = rd(0x0500 + i)
    local was = bd[i]
    local isEmpty = (v == 0xFF or v == 0x00)
    local wasEmpty = (was == 0xFF or was == 0x00)
    if wasEmpty and not isEmpty then
      out[#out + 1] = { math.floor(i / 8), i % 8, v }
    end
  end
  return out
end
local function cells_str(cl)
  local t = {}
  for _, c in ipairs(cl) do t[#t + 1] = string.format("%d:%d:%02X", c[1], c[2], c[3]) end
  return table.concat(t, ";")
end
local function close_rec(lockf, cells, flag)
  seq = seq + 1
  csv:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s,%d,%d,%d\n",
    seq, round, rec.go_f, rec.go_count, rec.res_f, rec.done_f, lockf,
    rec.cA, rec.cB, rec.ccol, rec.co4,
    rd(0x6152), rd(0x6153), rd(0x616E),
    rec.px, rec.py, rec.po, curCap.x, curCap.y, curCap.o,
    rec.h_go, rec.vc_go, seed17, seed18, cells_str(cells), flag,
    rec.acol or -1, rec.ao4 or -1, FLIPF))
  csv:flush()
  if flag == "ok" and shotN < SHOTS then
    shotN = shotN + 1
    shot(string.format("lock_%03d_f%d.png", seq, lockf))
  end
  -- targeted mismatch screenshots at lock time (offline decode remains authoritative):
  -- trigger on orientation-class flip OR wrong column vs the FINAL committed placement.
  if flag == "ok" and rec.ccol >= 0 and #cells == 2 and mmShots < 30 then
    local a, b = cells[1], cells[2]
    if a[1] > b[1] or (a[1] == b[1] and a[2] > b[2]) then a, b = b, a end
    local kind = (a[2] == b[2]) and "V" or "H"
    local ckind = (rec.co4 < 2) and "V" or "H"
    -- color-order flip check (same class, same col): committed first-cell color
    local want1
    if rec.co4 == 0 or rec.co4 == 2 then want1 = rec.cA else want1 = rec.cB end
    local flipped = (kind == ckind) and (a[2] == rec.ccol or (kind == "V" and a[2] == rec.ccol))
                    and (rec.cA ~= rec.cB) and ((a[3] % 16) ~= want1)
    if kind ~= ckind or a[2] ~= rec.ccol or flipped then
      mmShots = mmShots + 1
      local tag = (kind ~= ckind) and "orient" or (flipped and "colflip" or "col")
      shot(string.format("mm_%s_seq%03d_c%d_o%d_land%s%d.png", tag, seq, rec.ccol, rec.co4, kind, a[2]))
    end
  end
  rec = nil
  lastActivity = frame
end

-- ---------- main endFrame loop ----------
emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    local mode = rd(0x46); modeCache = mode

    -- mailbox board snapshot for the brain (same as copro upload source)
    if S.need_snap then
      snap_board(S.board, 0x0500)
      S.cA = rd(0x0381) % 16; S.cB = rd(0x0382) % 16
      S.need_snap = false
    end

    -- ---- menu / round driving (mode ~= 4) ----
    -- v4 DRHUMAN cart: autonav HOLDS coherent VS-CPU ($0727=2/$04=1) every menu hook but
    -- an_st_go is a bare RTS (P0.4: never press the human's buttons) -> WE are the human:
    -- press START at the title and at every menu screen. Level-select can be mode 1 or 2
    -- depending on flow; poke levels/speed/seed in modes 1..3 (idempotent).
    if mode ~= 4 then
      if rec then close_rec(frame, {}, "nolock_modeexit") end
      if mode >= 1 and mode <= 3 then
        if not lvlPoked then
          if rd(0x0316) ~= 11 then wr(0x0316, 11) end
          if rd(0x0396) ~= 11 then wr(0x0396, 11) end
          wr(0x96, 11); wr(0x45, 1)          -- live cursor + MED speed (CvC autonav parity)
          lvlPoked = true
        end
        if seedPokedRound ~= round then
          local s1, s2 = nextrand(), nextrand()
          if s1 == 0 and s2 == 0 then s1 = 0x89 end
          wr(0x17, s1); wr(0x18, s2)
          seedPokedRound = round
          dwell = 20 + (nextrand() % 60)
          log(string.format("SEEDPOKE f=%d round=%d s17=%02X s18=%02X dwell=%d", frame, round + 1, s1, s2, dwell))
        end
        if dwell > 0 then dwell = dwell - 1 else
          if frame % 12 == 0 then press({ start = true }, 4) end
        end
      else                                    -- title (0), post-match (7), intro (8), ...
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      lastActivity = frame
      return
    end

    -- ---- play (mode == 4) ----
    if lvlPoked then lvlPoked = false end

    -- round edge: mode entered 4 since last frame
    if prevMode ~= 4 then
      round = round + 1
      seed17, seed18 = rd(0x17), rd(0x18)
      local bd = {}; snap_board(bd, 0x0500)
      local h, vc = board_stats(bd)
      log(string.format("ROUND %d start f=%d seed=%02X%02X h=%d vc=%d p727=%d z04=%d",
        round, frame, seed17, seed18, h, vc, rd(0x0727), rd(0x04)))
      lastActivity = frame
    end

    -- P1 keep-alive: erase non-virus cells on P1 board
    for i = 0, 127 do
      local v = rd(0x0400 + i)
      if v ~= 0xFF and v ~= 0x00 and math.floor(v / 16) ~= 0x0D then
        wr(0x0400 + i, 0xFF)
      end
    end

    -- capsule tracking (P2)
    prevCap.x, prevCap.y, prevCap.o = curCap.x, curCap.y, curCap.o
    curCap.x, curCap.y, curCap.o = rd(0x0385), rd(0x0386), rd(0x03A5)

    -- GO pulse -> open/refresh record
    if S.go_pulse then
      S.go_pulse = false
      if rec then
        -- late-lock catch: did the previous pill lock without us noticing?
        local cl = diff_new_cells(rec.snap)
        if #cl >= 2 then
          close_rec(frame, cl, "latecatch")
        end
      end
      if rec and rec.cA == (rd(0x0381) % 16) and rec.cB == (rd(0x0382) % 16) then
        -- same pill re-GO (retry): refresh commit info when it arrives
        rec.go_count = rec.go_count + 1
        rec.go_f = S.go_frame
        rec.ccol, rec.co4, rec.res_f, rec.done_f = -1, -1, -1, -1
        rec.acol, rec.ao4 = -1, -1
      else
        if rec then close_rec(frame, {}, "superseded") end
        rec = { go_f = S.go_frame, go_count = 1, snap = {}, ccol = -1, co4 = -1,
                acol = -1, ao4 = -1,
                res_f = -1, done_f = -1, cA = rd(0x0381) % 16, cB = rd(0x0382) % 16,
                px = -1, py = -1, po = -1 }
        snap_board(rec.snap, 0x0500)
        rec.h_go, rec.vc_go = board_stats(rec.snap)
      end
      lastActivity = frame
    end

    if rec then
      -- adopt commit values once computed
      if rec.ccol == -1 and S.ror ~= 0xFF then
        rec.ccol, rec.co4, rec.res_f = S.rcol, S.ror, S.res_frame   -- FINAL result
        rec.acol, rec.ao4 = S.acol, S.aor                            -- provisional alt
      end
      if rec.done_f == -1 and S.done then rec.done_f = S.done_frame end
      rec.px, rec.py, rec.po = prevCap.x, prevCap.y, prevCap.o
      -- lock detection: board delta vs GO snapshot
      local cl = diff_new_cells(rec.snap)
      if #cl >= 2 then
        close_rec(frame, cl, "ok")
      end
    end

    -- stall watchdog: paused (STUDY) or wedged -> unpause / log
    if frame - lastActivity > 900 then
      log(string.format("STALL f=%d mode=%d goes=%d dones=%d capy=%d -> START", frame, mode, S.goes, S.dones, curCap.y))
      press({ start = true }, 4)
      forceUntil = frame + 4
      lastActivity = frame - 600   -- retry every ~5s if still stuck
    end
  end)
  if not ok then log("LUA_ERROR f=" .. frame .. " " .. tostring(err)) end
  prevMode = modeCache

  if frame >= MAXF and not stopped then
    stopped = true
    log(string.format("SUMMARY frames=%d rounds=%d pills=%d goes=%d dones=%d shots=%d", frame, round, seq, S.goes, S.dones, shotN))
    csv:close(); logf:close()
    pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)

log(string.format("census_run_flip loaded RLAT=%d DLAT=%d FLIPF=%d MAXF=%d SHOTS=%d SEED=%d out=%s", RLAT, DLAT, FLIPF, MAXF, SHOTS, SEED, OUT))
