-- ============================================================================
-- probe5.lua -- ONE instrument for the v8+DRTUCK decision. Three halves in one run:
--
--   (A) MECHANISM  : probe3's MMC1 shift-register MODEL + bank0 / RAM-wipe / BRK canaries.
--                    Counts MIXED loads into the PRG register -- the catastrophic case.
--   (B) FUNCTIONAL : fieldplay's match cycle. P1 is the idle human on a DRHUMAN cart, so
--                    matches END and the whole end-of-match -> title -> next-match loop runs.
--                    `4->0` (mid-match abort to title) is the kill condition.
--   (C) EXECUTION  : does the cart actually PERFORM a tuck? The Lua copro is extended to
--                    publish a tuck descriptor at $5087/$5088 (W_TCOL/W_TROW), which the
--                    stock probe3/fieldplay brains do NOT serve -- on those, a DRTUCK cart
--                    reads OPEN BUS ($50) there and the executor is inert.
--
-- ---- WHY (C) IS A CHECK THAT CAN FAIL --------------------------------------------------
-- Two independent detectors, run on EVERY arm including a DRTUCK=0 control served the
-- SAME descriptors:
--
--   D1 (cart-state): EFF_C2 ($617B) is written ONLY inside `if TUCK:` in the emitter. A
--       DRTUCK=0 cart never writes it, so "EFF_C2 == approach while high, then == final
--       once at/below the trigger row" is structurally impossible there. D1 therefore
--       cannot pass on the plain cart -- and the control run proves that empirically, it
--       is not an argument from source.
--   D2 (trajectory, cart-agnostic): the capsule's own X ($0385) DWELLED on the approach
--       column for >= DWELL frames while high, then LANDED on a different column ==
--       final. This reads nothing tuck-specific -- it is the manoeuvre itself. A driver
--       that steers monotonically to one target cannot produce it.
--
-- D2 is deliberately NOT keyed to the shape of the fix (hazard: probe2 keyed on "a run of
-- writes not a multiple of 5" and would have scored DRMMC1RST as the defect). D2 would
-- score ANY implementation that moves the capsule this way, and would score none that
-- doesn't.
--
-- ---- the descriptor source -------------------------------------------------------------
-- The real copro's tuck_v3 firmware decides tucks with a theta gate (theta*=400). That is
-- FIRMWARE, not cart. This probe substitutes a geometric finder so the CART side can be
-- exercised: it looks for a cell under an overhang that a neighbouring, clear column can
-- deliver the capsule to. Rates from this finder measure the PROBE, not the firmware;
-- what measures the CART is executed/published (the conversion ratio).
--
-- Env: P5_OUT P5_MAXF P5_DLAT P5_SEED P5_TAG P5_TUCK (1=publish descriptors, 0=never)
-- ============================================================================
-- ---- REQUIRED IDENTITY (added after an ORPHAN LOG incident; see probe8.lua) ------------
-- OUT and TAG used to default to "." and "probe5". A launch with no P5_* environment then
-- wrote a complete, healthy-looking SUMMARY into Mesen's own Release directory, attributable
-- to no cart, no flag set and no lane. Reproduced byte-for-byte from this very file. Both are
-- now REQUIRED and every run stamps cart identity + a per-run nonce.
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then
    error("\n*** " .. name .. " IS REQUIRED. Refusing to run: an unattributable log is worse\n"
       .. "*** than no log. Launch via the run_one*.sh runner, never by handing this file\n"
       .. "*** straight to run_mesen.sh.\n", 0)
  end
  return v
end
local OUT   = need("P5_OUT")
local TAG   = need("P5_TAG")
local CART, CARTID = "?", "?"
pcall(function()
  local ri = emu.getRomInfo()
  CART   = tostring(ri.name or ri.path or "?"):gsub("%s", "_")   -- coerce: a non-string here must not crash the header
  CARTID = tostring(ri.fileSha1 or ri.sha1 or "?"):sub(1, 8)
end)
-- nonce must be UNIQUE PER PROCESS: math.random unseeded returns the same sequence every
-- run, so four probes started in the same second produced the SAME "nonce" (observed).
-- A table address is process-unique and costs nothing.
local NONCE = string.format("%x", os.time() % 0x1000000) .. "-" .. tostring({}):sub(-6)
local MAXF  = tonumber(os.getenv("P5_MAXF") or "18000")
local DLAT  = tonumber(os.getenv("P5_DLAT") or "34")
local SEED  = tonumber(os.getenv("P5_SEED") or "114")
local PUBT  = tonumber(os.getenv("P5_TUCK") or "1")     -- 0 => always publish 0xFF (no tuck)
local BOOTF = tonumber(os.getenv("P5_BOOTF") or "10")
local DWELL = tonumber(os.getenv("P5_DWELL") or "2")    -- D2: frames on the approach column

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/probe5.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local frame, curFrame = 0, 0
local events = {}
local function ev(s) events[#events + 1] = s end

-- ================= (A) MMC1 shift-register model =================
local REGNAME = { [0] = "CTRL", [1] = "CHR0", [2] = "CHR1", [3] = "PRG" }
local sr_count, sr_srcs = 0, {}
local loads, mixed_total, mixed_prg, mixed_boot, resets = 0, 0, 0, 0, 0
local mixedLog = {}

emu.addMemoryCallback(function(addr, value)
  if value >= 0x80 then
    resets = resets + 1; sr_count = 0; sr_srcs = {}
    return
  end
  sr_count = sr_count + 1
  sr_srcs[sr_count] = addr
  if sr_count == 5 then
    loads = loads + 1
    local reg = math.floor(addr / 8192) % 4
    local mixed = false
    for i = 2, 5 do if sr_srcs[i] ~= sr_srcs[1] then mixed = true end end
    if mixed then
      mixed_total = mixed_total + 1
      if frame <= BOOTF then mixed_boot = mixed_boot + 1 end
      local tag = ""
      if reg == 3 then
        if frame > BOOTF then mixed_prg = mixed_prg + 1 end
        tag = "  <<< MIXED LOAD INTO PRG -- THE CATASTROPHIC CASE"
      end
      if #mixedLog < 60 then
        local srcs = ""
        for i = 1, 5 do srcs = srcs .. string.format("$%04X ", sr_srcs[i]) end
        mixedLog[#mixedLog + 1] = string.format("MIXEDLOAD f=%d reg=%s(%d) srcs=[ %s]%s%s",
          frame, REGNAME[reg], reg, srcs, (frame <= BOOTF and "  (power-on)" or ""), tag)
      end
    end
    sr_count = 0; sr_srcs = {}
  end
end, emu.callbackType.write, 0x8000, 0xFFFF)

local soft8036 = 0
emu.addMemoryCallback(function()
  soft8036 = soft8036 + 1
  ev(string.format("*** BANK0 SOFT-ENTRY exec $8036 f=%d (#%d) ***", frame, soft8036))
end, emu.callbackType.exec, 0x8036)

local wipes, lastVC = 0, -1
emu.addMemoryCallback(function(addr, value)
  if value ~= lastVC then
    if lastVC > 0 and value == 0 then
      wipes = wipes + 1
      ev(string.format("!!! VC1 WIPE f=%d  %d -> 0 (#%d) !!!", frame, lastVC, wipes))
    end
    lastVC = value
  end
end, emu.callbackType.write, 0x0324)

local brkhits = 0
emu.addMemoryCallback(function()
  brkhits = brkhits + 1
  if brkhits <= 5 then ev(string.format("### exec $A02E f=%d (#%d) BRK-loop watch ###", frame, brkhits)) end
end, emu.callbackType.exec, 0xA02E)

-- ================= copro mailbox, tuck-aware =================
local W = 0x5000            -- DRPOCKET=1 => P2 rides the $5000 window (W2_BASE=0x5000)
local S = { board = {}, done = false, go_f = -1, rcol = 0, ror = 0xFF,
            tcol = 0xFF, trow = 0xFF, pending = false, need_snap = false,
            goes = 0, dones = 0, pub = 0, opp = 0 }
for i = 0, 127 do S.board[i] = 0xFF end

local function filled(bd, r, c) local v = bd[r * 8 + c]; return v ~= 0xFF and v ~= 0x00 end

-- Geometric, EXECUTOR-SHAPED tuck finder.
--   final column f has a lip: some cell (rt,f) is EMPTY with a FILLED cell above it.
--   approach column a (|a-f|==1) is CLEAR from the top down to rt, so the capsule can fall
--   to rt in a and then slide one column into the pocket.
-- Returns final, approach, rt  (rt = BOARD row, 0 = top -- the executor converts to 15-rt).
local function find_tuck(bd)
  for f = 0, 7 do
    local seenFill = false
    for r = 0, 13 do
      if filled(bd, r, f) then
        seenFill = true
      elseif seenFill and not filled(bd, r + 1, f) and not filled(bd, r + 2, f) then
        -- (r,f) is under a lip and the pocket is >= 2 deep, so a VERTICAL capsule fits.
        for _, a in ipairs({ f - 1, f + 1 }) do
          if a >= 0 and a <= 7 then
            local clear = true
            for rr = 0, r + 2 do if filled(bd, rr, a) then clear = false; break end end
            if clear and r >= 2 then return f, a, r + 1 end
          end
        end
      end
    end
  end
  return nil
end

-- topmost filled row of a column (16 = column empty)
local function topfill(bd, c)
  for r = 0, 15 do if filled(bd, r, c) then return r end end
  return 16
end

-- SYNTHETIC EXECUTOR PROBE (P5_TUCK=2). Isolates the CART's capability from board luck: it
-- asks for a late lateral switch between two columns that are BOTH open, with >= SLACK rows
-- of fall left after the switch. A working executor lands on `final`; a driver that ignores
-- the descriptor never visits `approach`; a driver that switches too late lands on
-- `approach`. All three outcomes are distinguishable, on every pill, so this is the
-- high-n instrument. It is NOT a play-quality measurement and is not reported as one.
local SLACK = 3
local function synth_tuck(bd, final)
  for _, a in ipairs({ final - 1, final + 1 }) do
    if a >= 0 and a <= 7 then
      local ta, tf = topfill(bd, a), topfill(bd, final)
      local lo = math.min(ta, tf)
      if lo >= SLACK + 2 then
        local rt = lo - SLACK
        if rt >= 2 and rt <= 13 then return a, rt end
      end
    end
  end
  return nil
end

local function brain(bd)
  local bestCol, bestFill = 0, 99
  for c = 0, 7 do
    local fill = 0
    for r = 0, 15 do if filled(bd, r, c) then fill = fill + 1 end end
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
    local bc, bo = brain(S.board)
    local f, a, rt
    if PUBT == 1 then
      f, a, rt = find_tuck(S.board)                       -- geometric (realistic) tucks
    elseif PUBT == 2 then
      f = bc; a, rt = synth_tuck(S.board, bc)             -- synthetic executor stress
      if not a then f = nil end
    end
    if f then S.opp = S.opp + 1 end
    if S.dones < 30 then
      local nf = 0
      for i = 0, 127 do if S.board[i] ~= 0xFF and S.board[i] ~= 0x00 then nf = nf + 1 end end
      ev(string.format("SEARCH #%d f=%d fill=%d tuck=%s", S.dones + 1, curFrame, nf,
         f and string.format("final=%d appr=%d row=%d", f, a, rt) or "none"))
    end
    if f then
      S.rcol = f % 8; S.ror = 0; S.tcol = a; S.trow = rt; S.pub = S.pub + 1
    else
      S.rcol = bc % 8; S.ror = bo % 4; S.tcol = 0xFF; S.trow = 0xFF
    end
    S.done = true; S.pending = false; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return S.tcol end, emu.callbackType.read, W + 0x87)  -- W_TCOL
emu.addMemoryCallback(function() return S.trow end, emu.callbackType.read, W + 0x88)  -- W_TROW

-- ================= input =================
local modeCache = -1
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
  if inCur and frame < inUntil and modeCache ~= 4 and not d135_block(inCur) then
    emu.setInput(inCur, 0)
  end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

-- ================= (C) tuck-execution detection =================
local TUCK_C2, TUCK_R2, EFF_C2, TGT_C2, EFF_DIST2 = 0x6179, 0x617A, 0x617B, 0x6152, 0x6194
local PX2, PY2 = 0x0385, 0x0386

local P = nil            -- per-pill state
local nPills, nDesc, nExec, nD2, nChanged = 0, 0, 0, 0, 0
local fHi, fLo, fReach, fLand = 0, 0, 0, 0    -- which condition failed (first failing one)
local execLog = {}

local function close_pill()
  if not P or not P.desc then P = nil; return end
  -- ⚠ DRPRESTART can publish the NEXT pill's result while this one is still falling, which
  -- rewrites TUCK_C2/TGT_C2 mid-flight. Attributing that descriptor to THIS pill would score
  -- a guaranteed failure that the executor never had a chance at, so those pills are
  -- EXCLUDED and counted separately rather than folded into the failure buckets.
  if P.changed then nChanged = nChanged + 1; P = nil; return end
  nDesc = nDesc + 1
  local land = P.lastPx
  local d1 = P.sawHi and P.sawLo and P.pxAppr and (land == P.final)
  local d2 = (P.dwellAppr >= DWELL) and (land == P.final) and (P.apprCol ~= P.final)
  if d1 then nExec = nExec + 1 end
  if d2 then nD2 = nD2 + 1 end
  if not P.sawHi then fHi = fHi + 1
  elseif not P.sawLo then fLo = fLo + 1
  elseif not P.pxAppr then fReach = fReach + 1
  elseif land ~= P.final then fLand = fLand + 1 end
  if #execLog < 40 then
    execLog[#execLog + 1] = string.format(
      "TUCKPILL f=%d appr=%d final=%d trigY=%d hi=%s lo=%s pxAppr=%s dwell=%d land=%d D1=%s D2=%s",
      frame, P.apprCol, P.final, P.trigY, tostring(P.sawHi), tostring(P.sawLo),
      tostring(P.pxAppr), P.dwellAppr, land, tostring(d1), tostring(d2))
  end
  P = nil
end

-- ================= main loop =================
local lcg = SEED
local function nextrand() lcg = (lcg * 1103515245 + 12345) % 2147483648; return math.floor(lcg / 65536) % 256 end
local prevMode, lvlPoked, seedPokedRound, round = -1, false, -1, 0
local matchesStarted, matchesEnded, aborts, cleanEnds = 0, 0, 0, 0
local prevPy = -1

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    if #events > 0 then for _, s in ipairs(events) do log(s) end; events = {} end

    local mode = rd(0x46); modeCache = mode
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end

    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d match=%d vc1=%d vc2=%d mixed=%d mixedPRG=%d soft=%d " ..
          "goes=%d dones=%d pub=%d exec=%d", frame, prevMode, mode, rd(0x6164), rd(0x0324),
          rd(0x03A4), mixed_total, mixed_prg, soft8036, S.goes, S.dones, S.pub, nExec))
      if mode == 4 and prevMode ~= 4 then matchesStarted = matchesStarted + 1 end
      if prevMode == 4 and mode ~= 4 then
        matchesEnded = matchesEnded + 1
        if mode == 0 then
          aborts = aborts + 1
          log(string.format("!!! CATASTROPHIC 4->0 f=%d (#%d) !!!", frame, aborts))
        else
          cleanEnds = cleanEnds + 1
        end
        close_pill()
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
        if seedPokedRound ~= round then
          local s1, s2 = nextrand(), nextrand()
          if s1 == 0 and s2 == 0 then s1 = 0x89 end
          wr(0x17, s1); wr(0x18, s2); seedPokedRound = round
        end
        if frame % 12 == 0 then press({ start = true }, 4) end
      else
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      prevPy = -1
      return
    end
    if lvlPoked then lvlPoked = false; round = round + 1 end

    -- ---- per-pill tuck tracking (mode 4 only) ----
    local py, px = rd(PY2), rd(PX2)
    if prevPy >= 0 and py > prevPy then          -- $0386 counts UP from the floor: a RISE = new pill
      close_pill(); nPills = nPills + 1
    end
    if not P then
      P = { desc = false, changed = false, apprCol = -1, final = -1, trigY = -1,
            sawHi = false, sawLo = false, pxAppr = false, dwellAppr = 0, lastPx = px }
    end
    local tc, tr, ec, gc = rd(TUCK_C2), rd(TUCK_R2), rd(EFF_C2), rd(TGT_C2)
    if (not P.desc) and tc ~= 0xFF and tc < 8 and gc < 8 and tc ~= gc then
      P.desc = true; P.apprCol = tc; P.trigY = tr; P.final = gc
    elseif P.desc and tc < 8 and (tc ~= P.apprCol or gc ~= P.final) then
      P.changed = true
    end
    if P.desc then
      if py > P.trigY then
        if ec == P.apprCol then P.sawHi = true end
        if px == P.apprCol then P.pxAppr = true end
        -- D2: cart-agnostic dwell on the approach column while still high
        if px == P.apprCol then P.dwellAppr = P.dwellAppr + 1 end
      else
        if ec == P.final then P.sawLo = true end
      end
    end
    P.lastPx = px
    prevPy = py
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF then
    close_pill()
    for _, s in ipairs(mixedLog) do log(s) end
    for _, s in ipairs(execLog) do log(s) end
    log(string.format("SUMMARY tag=%s cart=%s cartid=%s nonce=%s frames=%d goes=%d dones=%d sr_loads=%d sr_resets=%d " ..
        "MIXED_total=%d MIXED_boot=%d MIXED_PRG_nonboot=%d soft8036=%d wipes=%d brk_a02e=%d " ..
        "matches_started=%d matches_ended=%d clean_ends=%d ABORT_4to0=%d " ..
        "pills=%d tuck_opp=%d tuck_pub=%d tuck_desc=%d desc_changed=%d " ..
        "TUCK_EXEC_D1=%d TUCK_EXEC_D2=%d fail_hi=%d fail_lo=%d fail_reach=%d fail_land=%d",
        TAG, CART, CARTID, NONCE, frame, S.goes, S.dones, loads, resets, mixed_total, mixed_boot, mixed_prg,
        soft8036, wipes, brkhits, matchesStarted, matchesEnded, cleanEnds, aborts,
        nPills, S.opp, S.pub, nDesc, nChanged, nExec, nD2, fHi, fLo, fReach, fLand))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe5 start cart=%s cartid=%s nonce=%s out=%s tag=%s maxf=%d dlat=%d seed=%d pubtuck=%d dwell=%d",
    CART, CARTID, NONCE, OUT, TAG, MAXF, DLAT, SEED, PUBT, DWELL))
