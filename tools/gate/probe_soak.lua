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
-- ==================== probe_soak.lua = probe7 + LONG-SOAK INSTRUMENTATION =================
-- probe_soak is probe7 with the mechanism detectors (section A), the copro mailbox and the tuck
-- execution detectors left BYTE-IDENTICAL, so the killed-mutant evidence earned for them in the
-- tuck phase (hardening OFF -> MIXED_PRG 21 / wipes 21 / bank0 23 / 4->0 1) transfers unchanged.
-- What is ADDED is everything a multi-hour soak needs that a 5-minute gate did not:
--
--   (S1) CHECKPOINT every CKPT frames: every canary total + wall clock, flushed. A crash of the
--        box or of the driving session still leaves a usable frame count and therefore a BOUND.
--   (S2) Per-MATCH records: start/end frame, duration, exit mode, and the DELTA of every canary
--        over that match. A failure is then locatable in time, which a run-total cannot do.
--   (S3) STUCK-BUSY canary. BUSY ($6176) is the driver's re-entrancy latch and the documented
--        soft-brick surface (sticky PRG-RAM -> every later hook bails). Counts the longest run of
--        consecutive frames with BUSY != 0 and flags runs >= BUSYRUN. Companion: BUSYSKP ($6192),
--        the DRBUSYESC consecutive-bail counter, whose MAX tells you whether a stale-BUSY episode
--        happened at all even if the escape recovered it.
--   (S4) PROGRESS canaries, three of them, because "it kept running" has three distinct failures:
--          mode_stall   : the same mode for >= STALL frames        (a hard hang)
--          gap_stall    : match end -> next match start > GAPMAX   (the v6c 0->1->2->3->8->0 loop)
--          search_stall : in mode 4 with no new GO for > SRCHSTALL (driver alive, AI dead)
--   (S5) TITLE-RETURN canary: ANY entry into mode 0 after boot. On a healthy cart mode 0 is
--        visited exactly once, at power-on. 4->0 (already counted as ABORT) is the catastrophic
--        subclass; this is the superset.
--   (S6) TUCK-WRITE identity assertion. The emitter writes TUCK_C2/EFF_C2 ($6179/$617B) ONLY
--        inside `if TUCK:`. On a DRTUCK=0 cart this counter MUST read 0 -- so it is simultaneously
--        a canary and a proof that the bytes actually under test are the plain ship cart. It is
--        falsifiable by construction: the same probe on roms/v8tuck.nes drives it positive.
--   (S7) QUARTILE breakdown, so degradation-over-time is visible rather than averaged away.
--
-- ---- PS_INJECT: the detectors added here are NEW, so they get their own killed-mutant test ----
--   1 = force BUSY=1 for [INJ_A, INJ_B]     -> S3 must fire
--   2 = force mode $46=0 for [INJ_A, INJ_B] -> S5 and S4/gap must fire
-- A soak arm runs with INJECT=0; the validation arms exist to prove these checks CAN fail.
--
-- Env: PS_OUT PS_MAXF PS_DLAT PS_SEED PS_TAG PS_TUCK PS_CKPT PS_INJECT PS_INJA PS_INJB
-- ============================================================================
local OUT   = os.getenv("PS_OUT")  or "."
local MAXF  = tonumber(os.getenv("PS_MAXF") or "18000")
local DLAT  = tonumber(os.getenv("PS_DLAT") or "34")
local SEED  = tonumber(os.getenv("PS_SEED") or "114")
local TAG   = os.getenv("PS_TAG") or "probe_soak"
local PUBT  = tonumber(os.getenv("PS_TUCK") or "4")     -- 4 = tuck v1 = what the POCKET core publishes
local BOOTF = tonumber(os.getenv("PS_BOOTF") or "10")
local DWELL = tonumber(os.getenv("PS_DWELL") or "2")    -- D2: frames on the approach column
-- ⚠ ALL soak config AND soak state lives in ONE table K. Not style: Lua caps a function at 60
-- upvalues and the main endFrame closure was already near it in probe7 -- holding these as loose
-- locals overflows the limit and the script will not compile. Keep new state inside K.
local K = {
  CKPT = tonumber(os.getenv("PS_CKPT") or "30000"),
  INJ  = tonumber(os.getenv("PS_INJECT") or "0"),
  INJA = tonumber(os.getenv("PS_INJA") or "1500"),
  INJB = tonumber(os.getenv("PS_INJB") or "2100"),
  -- thresholds: each is set well above the observed healthy maximum, and the observed maximum is
  -- itself reported, so the margin is auditable instead of asserted.
  BUSYRUN   = tonumber(os.getenv("PS_BUSYRUN")   or "120"),   -- 2 s of latched BUSY
  STALL     = tonumber(os.getenv("PS_STALL")     or "7200"),  -- 2 min in one mode
  GAPMAX    = tonumber(os.getenv("PS_GAPMAX")    or "3600"),  -- 60 s between matches (healthy ~300)
  SRCHSTALL = tonumber(os.getenv("PS_SRCHSTALL") or "1800"),  -- 30 s with no GO while in mode 4
  BUSY_A = 0x6176, BUSYSKP_A = 0x6192,
  busyRun = 0, busyRunMax = 0, busyEpisodes = 0, busyskpMax = 0,
  modeRun = 0, modeRunMax = 0, modeStalls = 0,
  lastEndF = -1, gapMax = 0, gapStalls = 0,
  lastGoF = 0, srchGapMax = 0, srchStalls = 0, prevGoes = 0,
  -- frames spent in LIVE PLAY (mode 4). The rig's matches are short because the idle-human P1
  -- tops out fast, so TOTAL frames overstate how much live play a soak contains. Every driver
  -- hook -- and therefore every MMC1 bank switch, which is the hazard's actual exposure --
  -- happens during mode 4, so the bound is quoted against this as well as against wall frames.
  play4 = 0,
  titleReturns = 0,
  mStartF = -1, mSnap = nil,
  durMin = 1e9, durMax = 0, durSum = 0,
  wallStart = os.time(), nextCkpt = 0,
  QN = 4, qMix = {}, qWipe = {}, qSoft = {}, qAbort = {}, qMatch = {},
  pMix = 0, pWipe = 0, pSoft = 0, pAbort = 0,
}
K.nextCkpt = K.CKPT
for i = 1, K.QN do K.qMix[i], K.qWipe[i], K.qSoft[i], K.qAbort[i], K.qMatch[i] = 0, 0, 0, 0, 0 end

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/probe_soak.log", "w")
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

-- (S6) TUCK-WRITE IDENTITY ASSERTION -------------------------------------------------------
-- $6179 TUCK_C2, $617A TUCK_R2, $617B EFF_C2. The emitter emits every store to these three
-- addresses inside `if TUCK:` and nowhere else. So on the DRTUCK=0 ship cart this MUST be 0,
-- and a non-zero value means the cart under test is NOT the plain ship cart. This is a check
-- that can fail: run the same probe on roms/v8tuck.nes and it goes positive on the first hook.
local tuckwrites = 0
emu.addMemoryCallback(function()
  tuckwrites = tuckwrites + 1
end, emu.callbackType.write, 0x6179, 0x617B)

-- (S8) DRRTIVEC NMI SHIELD: is it live, and does it preserve the ACCUMULATOR? ---------------
-- The held v8 candidate 087ff959 clobbers A on every NMI the shield handles: `LDA $A02E` then
-- fall into the game's NMI handler, whose PHA/PLA faithfully restores the ALREADY-corrupted
-- value, so interrupted main-loop code resumes with a wrong A. v6e prepends PHA and pops before
-- both exits. A gate that counts matches is blind to this -- which is precisely why an
-- 18,000-frame multi-match gate passed the defective cart with numbers identical to the
-- unhardened build. A soak that repeats that blindness for five hours is worse than no soak.
--
-- Three counters, in increasing order of what they assume:
--   shieldHits ($CEEC exec) -- is the shield path even TAKEN? register-free, always valid.
--   gameNmi    ($8005 exec) -- game NMI handler entry; also the LIVENESS WITNESS below.
--   nmiEvents  (eventType.nmi) -- NMIs actually taken, from an event callback.
--
-- ⚠ SILENT-FAILURE GUARD. README_GATE: no emu.* call may run inside a memory callback, and the
-- failure mode is that the callback STOPS FIRING, with no error. An A-check built naively that
-- way would report "0 mismatches" forever = a check that cannot fail. So gameNmi is incremented
-- BEFORE anything risky, and is compared at the end against nmiEvents: if gameNmi stalls while
-- nmiEvents climbs, the callback died and the A verdict is reported VOID, never PASS.
-- The killed mutant for this check is the held cart itself: it MUST report mismatches.
local AK = { shieldHits = 0, gameNmi = 0, nmiEvents = 0, gameNmiAtLastNmi = 0, frozen = 0,
             on = (tonumber(os.getenv("PS_ACHK") or "0") == 1),
             apre = -1, pend = false, tried = 0, ok = 0, err = 0, mism = 0,
             dead = false, log = {} }

-- Resolve the accumulator out of emu.getState() without assuming a key path: the serializer
-- names are console-specific and README_GATE reports `.cpu` is nil here. Searched once, cached.
function AK.finda(st, depth)
  if type(st) ~= "table" or depth > 3 then return nil end
  for _, k in ipairs({ "a", "A" }) do
    local v = rawget(st, k)
    if type(v) == "number" and v >= 0 and v <= 255 then return v end
  end
  for k, v in pairs(st) do
    local ks = tostring(k):lower()
    if type(v) == "table" and (ks:find("cpu") or ks:find("nes") or depth < 2) then
      local r = AK.finda(v, depth + 1)
      if r then return r end
    end
  end
  return nil
end

emu.addMemoryCallback(function() AK.shieldHits = AK.shieldHits + 1 end, emu.callbackType.exec, 0xCEEC)

emu.addEventCallback(function()
  -- liveness bookkeeping: did the $8005 callback advance since the previous NMI?
  if AK.nmiEvents > 0 and AK.gameNmi == AK.gameNmiAtLastNmi then AK.frozen = AK.frozen + 1 end
  AK.gameNmiAtLastNmi = AK.gameNmi
  AK.nmiEvents = AK.nmiEvents + 1
  if AK.on and not AK.dead then
    local ok, st = pcall(emu.getState)
    if ok then
      local a = AK.finda(st, 0)
      if a then AK.apre = a; AK.pend = true else AK.dead = true end
    else
      AK.dead = true
    end
  end
end, emu.eventType.nmi)

emu.addMemoryCallback(function()
  AK.gameNmi = AK.gameNmi + 1          -- witness FIRST, unconditionally
  if AK.on and AK.pend and not AK.dead then
    AK.tried = AK.tried + 1
    local ok, st = pcall(emu.getState)
    if ok then
      local a = AK.finda(st, 0)
      if a then
        AK.ok = AK.ok + 1
        if a ~= AK.apre then
          AK.mism = AK.mism + 1
          if #AK.log < 25 then
            AK.log[#AK.log + 1] = string.format("AMISM f=%d A_at_interrupt=%d A_at_gameNMI=%d",
              curFrame, AK.apre, a)
          end
        end
      else AK.err = AK.err + 1 end
    else AK.err = AK.err + 1 end
    AK.pend = false
  end
end, emu.callbackType.exec, 0x8005)

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

-- SYNTHETIC EXECUTOR PROBE (P7_TUCK=2). Isolates the CART's capability from board luck: it
-- asks for a late lateral switch between two columns that are BOTH open, with >= SLACK rows
-- of fall left after the switch. A working executor lands on `final`; a driver that ignores
-- the descriptor never visits `approach`; a driver that switches too late lands on
-- `approach`. All three outcomes are distinguishable, on every pill, so this is the
-- high-n instrument. It is NOT a play-quality measurement and is not reported as one.
--
-- ⚠ REVISION (probe6 vs probe5). probe5 anchored the trigger row to the argmax column's own
-- depth, which on an L11 board (viruses from ~row 5) put it at board row 2-3. The copro answer
-- arrives DLAT=34 frames after GO and the capsule falls ~1 row/13 frames, so by the time the
-- descriptor existed the capsule was ALREADY below the trigger and the switch window had
-- closed -- probe5 scored those as fail_hi, which is the INSTRUMENT's latency, not the cart's
-- executor. probe6 instead picks the ADJACENT PAIR with the deepest shared clearance and puts
-- the trigger 2 rows above it, so the window is open when the answer lands.
local SLACK = 2
local MINROW = 5              -- trigger must be deep enough that the descriptor beats the fall
local function synth_tuck(bd, argcol)
  local bestF, bestA, bestLo = nil, nil, -1
  for f = 0, 7 do
    for _, a in ipairs({ f - 1, f + 1 }) do
      if a >= 0 and a <= 7 then
        local lo = math.min(topfill(bd, a), topfill(bd, f))
        if lo > bestLo then bestLo = lo; bestF = f; bestA = a end
      end
    end
  end
  if not bestF then return nil end
  local rt = bestLo - SLACK
  if rt > 13 then rt = 13 end
  if rt < MINROW then return nil end
  return bestF, bestA, rt
end

-- ============================ TUCK v1 -- WHAT THE POCKET CORE ACTUALLY PUBLISHES ===========
-- The Analogue Pocket core (`Cores/agg23.NES/nes.rev` a0d5190f = strand180_20, firmware
-- e970e9ab) is built `DRSTRAND=20 DRCOPRO_TUCK=1 DRCOPRO_ARM=1 DRFIX=1 DRCHAIN=180`
-- (experiments/rtl_chain/ship/stomper180s20-seed2/REBUILD.md, hash verified). DRCOPRO_TUCK=1
-- is tuck **v1** = fpga/copro/tuck_scan.py. DRCOPRO_TUCKV3 is unset, so theta -- which is a
-- tuck_v3 constant -- DOES NOT EXIST in that core at any dose.
--
-- v1 has NO value gate. Transcribed from its own docstring:
--     for the target column c (= best_col):
--         fc = first_occ(c);  sd = fc - 1        -- deepest row a STRAIGHT drop reaches
--         for approach a in {c-1, c+1}:
--             ra = first_occ(a) - 1
--             for r = fc .. ra:
--                 if board[r][c] occupied: skip  -- cannot enter c at this row
--                 rf = fall from r in c
--                 if rf > sd: candidate(approach=a, trigger=r, rest=rf)
--     select DEEPEST rest, ties -> first found
-- Depth is the entire criterion. So this mode measures the descriptor stream a DRTUCK=1 cart
-- would actually consume on the rematch platform TODAY.
--
-- ⚠ ONE FAITHFULNESS LIMIT, stated rather than hidden: `bc` here is this probe's emptiest-
-- column brain, not the copro's depth-3 argmax. v1 anchors on best_col, so the descriptor
-- STREAM is anchored differently than on silicon. Fire and misland RATES from this arm are
-- indicative of the mechanism, not a silicon prediction.
local function tuck_v1(bd, c)
  local fc = topfill(bd, c)
  local sd = fc - 1
  local bestA, bestR, bestRest = nil, nil, -1
  for _, a in ipairs({ c - 1, c + 1 }) do
    if a >= 0 and a <= 7 then
      local ra = topfill(bd, a) - 1
      for r = fc, ra do
        if r >= 0 and r <= 15 and not filled(bd, r, c) then
          local rf = r
          while rf + 1 < 16 and not filled(bd, rf + 1, c) do rf = rf + 1 end
          if rf > sd and rf > bestRest then bestRest = rf; bestA = a; bestR = r end
        end
      end
    end
  end
  if not bestA then return nil end
  return c, bestA, bestR
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
      f, a, rt = synth_tuck(S.board, bc)                  -- synthetic executor stress
    elseif PUBT == 3 then
      -- ⚠ BOARD-INDEPENDENT descriptor, for the MECHANISM arms ONLY.
      -- MEASURED: with DRHOLDBOARD=1 (the interleave trigger) the driver's restore loop
      -- stamps HOLD_BUF over the LIVE playfield $0500 every hook, so any board-derived
      -- descriptor evaluates on garbage and never fires -- t-mech-on published 0 tucks in
      -- 12 searches. That makes a board-derived probe STRUCTURALLY unable to test the one
      -- composition this gate exists for (long hook + tuck path). Mode 3 publishes a valid
      -- descriptor unconditionally, so the tuck branch runs on EVERY hook while the trigger
      -- is present. The PLACEMENTS are meaningless here and no play metric is read from
      -- these arms -- only MMC1 / canary counts, which do not depend on placement quality.
      f = bc % 8
      a = (f < 7) and (f + 1) or (f - 1)
      rt = 8
    elseif PUBT == 4 then
      f, a, rt = tuck_v1(S.board, bc)                     -- what the POCKET core publishes
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
emu.addEventCallback(function()
  if inCur and frame < inUntil and modeCache ~= 4 then emu.setInput(inCur, 0) end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

-- ================= (C) tuck-execution detection =================
local TUCK_C2, TUCK_R2, EFF_C2, TGT_C2, EFF_DIST2 = 0x6179, 0x617A, 0x617B, 0x6152, 0x6194
local PX2, PY2 = 0x0385, 0x0386

local P = nil            -- per-pill state
local nPills, nDesc, nExec, nD2, nChanged = 0, 0, 0, 0, 0
local nMis, nMisAppr = 0, 0
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
  -- MISLAND = the documented "strictly worse than no tuck" outcome: a descriptor was live for
  -- this pill and the capsule did NOT come to rest on the column the search scored. Counted
  -- over ALL attributable descriptor pills, not just the ones that got as far as switching.
  if land ~= P.final then nMis = nMis + 1
    if land == P.apprCol then nMisAppr = nMisAppr + 1 end
  end
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

-- ================= (S1..S7) soak helpers (state itself lives in K, see the upvalue note) ====
function K.qidx() local i = math.floor(frame * K.QN / MAXF) + 1; if i > K.QN then i = K.QN end; return i end

-- snapshot of every canary, for per-match deltas
function K.snap()
  return { mx = mixed_prg, wp = wipes, sf = soft8036, bk = brkhits, tw = tuckwrites,
           go = S.goes, dn = S.dones, pl = nPills, mt = mixed_total }
end

function K.statline()
  return string.format("mixedPRG=%d mixedTot=%d wipes=%d soft8036=%d brk=%d tuckwr=%d " ..
    "busyMax=%d busyEp=%d busyskpMax=%d modeRunMax=%d modeStall=%d gapMax=%d gapStall=%d " ..
    "srchGapMax=%d srchStall=%d title0=%d abort=%d shield=%d gameNmi=%d nmi=%d amism=%d",
    mixed_prg, mixed_total, wipes, soft8036, brkhits, tuckwrites,
    K.busyRunMax, K.busyEpisodes, K.busyskpMax, K.modeRunMax, K.modeStalls, K.gapMax,
    K.gapStalls, K.srchGapMax, K.srchStalls, K.titleReturns, aborts,
    AK.shieldHits, AK.gameNmi, AK.nmiEvents, AK.mism)
end

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    if #events > 0 then for _, s in ipairs(events) do log(s) end; events = {} end

    -- ---- PS_INJECT: drive the NEW detectors with the fault they are supposed to catch ----
    if K.INJ > 0 and frame >= K.INJA and frame <= K.INJB then
      if K.INJ == 1 then wr(K.BUSY_A, 1)             -- S3 must fire
      elseif K.INJ == 2 then wr(0x46, 0) end         -- S5 + S4/gap must fire
    end

    local mode = rd(0x46); modeCache = mode
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end

    -- ---- (S3) stuck-BUSY ----
    local bz = rd(K.BUSY_A)
    if bz ~= 0 then
      K.busyRun = K.busyRun + 1
      if K.busyRun > K.busyRunMax then K.busyRunMax = K.busyRun end
      if K.busyRun == K.BUSYRUN then
        K.busyEpisodes = K.busyEpisodes + 1
        log(string.format("!!! STUCK-BUSY f=%d BUSY=$%02X held %d frames (#%d) mode=%d !!!",
            frame, bz, K.busyRun, K.busyEpisodes, mode))
      end
    else
      K.busyRun = 0
    end
    local bs = rd(K.BUSYSKP_A)
    if bs > K.busyskpMax then
      K.busyskpMax = bs
      if bs >= 200 then log(string.format("!!! BUSYSKP HIGH f=%d val=%d (DRBUSYESC escape near) !!!", frame, bs)) end
    end

    -- ---- (S4a) mode stall ----
    if mode == prevMode then
      K.modeRun = K.modeRun + 1
      if K.modeRun > K.modeRunMax then K.modeRunMax = K.modeRun end
      if K.modeRun == K.STALL then
        K.modeStalls = K.modeStalls + 1
        log(string.format("!!! MODE-STALL f=%d mode=%d held %d frames (#%d) !!!", frame, mode, K.modeRun, K.modeStalls))
      end
    else
      K.modeRun = 0
    end

    -- ---- (S4b) match-boundary gap: end of a match -> start of the next ----
    if K.lastEndF >= 0 and (frame - K.lastEndF) == K.GAPMAX then
      K.gapStalls = K.gapStalls + 1
      log(string.format("!!! GAP-STALL f=%d no new match %d frames after end f=%d mode=%d (#%d) !!!",
          frame, K.GAPMAX, K.lastEndF, mode, K.gapStalls))
    end

    -- ---- (S4c) search stall: mode 4 but the AI has stopped asking ----
    if S.goes ~= K.prevGoes then K.prevGoes = S.goes; K.lastGoF = frame end
    if mode == 4 then
      K.play4 = K.play4 + 1
      local sg = frame - K.lastGoF
      if sg > K.srchGapMax then K.srchGapMax = sg end
      if sg == K.SRCHSTALL then
        K.srchStalls = K.srchStalls + 1
        log(string.format("!!! SEARCH-STALL f=%d no GO for %d frames in mode 4 (#%d) !!!",
            frame, sg, K.srchStalls))
      end
    else
      K.lastGoF = frame
    end

    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d match=%d vc1=%d vc2=%d mixed=%d mixedPRG=%d soft=%d " ..
          "goes=%d dones=%d pub=%d exec=%d", frame, prevMode, mode, rd(0x6164), rd(0x0324),
          rd(0x03A4), mixed_total, mixed_prg, soft8036, S.goes, S.dones, S.pub, nExec))
      -- (S5) any entry into mode 0 after boot is an unrequested return to title
      if mode == 0 and frame > 60 then
        K.titleReturns = K.titleReturns + 1
        log(string.format("!!! TITLE-RETURN f=%d from mode %d (#%d) !!!", frame, prevMode, K.titleReturns))
      end
      if mode == 4 and prevMode ~= 4 then
        matchesStarted = matchesStarted + 1
        K.mStartF = frame; K.mSnap = K.snap()
        local gap = (K.lastEndF >= 0) and (frame - K.lastEndF) or 0
        if gap > K.gapMax then K.gapMax = gap end
      end
      if prevMode == 4 and mode ~= 4 then
        matchesEnded = matchesEnded + 1
        if mode == 0 then
          aborts = aborts + 1
          log(string.format("!!! CATASTROPHIC 4->0 f=%d (#%d) !!!", frame, aborts))
        else
          cleanEnds = cleanEnds + 1
        end
        close_pill()
        -- (S2) per-match record with per-canary deltas
        local d = K.snap()
        local ms = K.mSnap or d
        local dur = (K.mStartF >= 0) and (frame - K.mStartF) or -1
        if dur >= 0 then
          if dur < K.durMin then K.durMin = dur end
          if dur > K.durMax then K.durMax = dur end
          K.durSum = K.durSum + dur
        end
        local qi = K.qidx(); K.qMatch[qi] = K.qMatch[qi] + 1
        log(string.format("MATCH #%d start=%d end=%d dur=%d exit=%d " ..
            "d_mixedPRG=%d d_mixedTot=%d d_wipes=%d d_soft=%d d_brk=%d d_tuckwr=%d " ..
            "d_goes=%d d_dones=%d d_pills=%d busyMax=%d busyskpMax=%d",
            matchesEnded, K.mStartF, frame, dur, mode,
            d.mx - ms.mx, d.mt - ms.mt, d.wp - ms.wp, d.sf - ms.sf,
            d.bk - ms.bk, d.tw - ms.tw, d.go - ms.go, d.dn - ms.dn,
            d.pl - ms.pl, K.busyRunMax, K.busyskpMax))
        K.lastEndF = frame; K.mStartF = -1
      end
      prevMode = mode
    end

    -- ---- (S7) quartile attribution of the four headline canaries ----
    if mixed_prg ~= K.pMix   then local q = K.qidx(); K.qMix[q]   = K.qMix[q]   + (mixed_prg - K.pMix);   K.pMix   = mixed_prg end
    if wipes     ~= K.pWipe  then local q = K.qidx(); K.qWipe[q]  = K.qWipe[q]  + (wipes     - K.pWipe);  K.pWipe  = wipes end
    if soft8036  ~= K.pSoft  then local q = K.qidx(); K.qSoft[q]  = K.qSoft[q]  + (soft8036  - K.pSoft);  K.pSoft  = soft8036 end
    if aborts    ~= K.pAbort then local q = K.qidx(); K.qAbort[q] = K.qAbort[q] + (aborts    - K.pAbort); K.pAbort = aborts end

    -- ---- (S1) checkpoint: a crash after this point still yields a usable bound ----
    if frame >= K.nextCkpt then
      local el = os.time() - K.wallStart
      log(string.format("CKPT f=%d wall=%ds fps=%.1f matches_started=%d ended=%d clean=%d %s",
          frame, el, (el > 0) and (frame / el) or 0,
          matchesStarted, matchesEnded, cleanEnds, K.statline()))
      K.nextCkpt = K.nextCkpt + K.CKPT
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
    log(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d sr_loads=%d sr_resets=%d " ..
        "MIXED_total=%d MIXED_boot=%d MIXED_PRG_nonboot=%d soft8036=%d wipes=%d brk_a02e=%d " ..
        "matches_started=%d matches_ended=%d clean_ends=%d ABORT_4to0=%d " ..
        "pills=%d tuck_opp=%d tuck_pub=%d tuck_desc=%d desc_changed=%d " ..
        "TUCK_EXEC_D1=%d TUCK_EXEC_D2=%d MISLAND=%d MISLAND_APPR=%d " ..
        "fail_hi=%d fail_lo=%d fail_reach=%d fail_land=%d",
        TAG, frame, S.goes, S.dones, loads, resets, mixed_total, mixed_boot, mixed_prg,
        soft8036, wipes, brkhits, matchesStarted, matchesEnded, cleanEnds, aborts,
        nPills, S.opp, S.pub, nDesc, nChanged, nExec, nD2, nMis, nMisAppr,
        fHi, fLo, fReach, fLand))
    local el = os.time() - K.wallStart
    log(string.format("SOAK tag=%s frames=%d play4_frames=%d sr_loads=%d wall=%ds fps=%.1f %s",
        TAG, frame, K.play4, loads, el, (el > 0) and (frame / el) or 0, K.statline()))
    log(string.format("SOAK2 tag=%s match_dur_min=%d match_dur_max=%d match_dur_mean=%.1f " ..
        "BUSYRUN_thr=%d STALL_thr=%d GAPMAX_thr=%d SRCHSTALL_thr=%d",
        TAG, (matchesEnded > 0) and K.durMin or -1, K.durMax,
        (matchesEnded > 0) and (K.durSum / matchesEnded) or 0,
        K.BUSYRUN, K.STALL, K.GAPMAX, K.SRCHSTALL))
    for i = 1, K.QN do
      log(string.format("QUART tag=%s q=%d matches=%d mixedPRG=%d wipes=%d soft8036=%d abort=%d",
          TAG, i, K.qMatch[i], K.qMix[i], K.qWipe[i], K.qSoft[i], K.qAbort[i]))
    end
    -- (S8) A-integrity verdict. VOID is a distinct outcome from PASS and is reported as such:
    -- a dead callback or an unreadable accumulator means the check did not run, NOT that the
    -- cart is clean. Only ACHK=PASS with tried>0 and ok==tried is evidence of anything.
    for _, s in ipairs(AK.log) do log(s) end
    local verdict
    if not AK.on then verdict = "OFF"
    elseif AK.dead or AK.err > 0 then verdict = "VOID_callback_or_register_unavailable"
    elseif AK.tried == 0 then verdict = "VOID_never_ran"
    elseif AK.mism > 0 then verdict = "FAIL_A_CORRUPTED"
    else verdict = "PASS" end
    log(string.format("ACHK tag=%s verdict=%s on=%s shield_CEEC=%d gameNmi_8005=%d nmi_events=%d " ..
        "frozen_witness=%d tried=%d ok=%d err=%d MISMATCH=%d dead=%s",
        TAG, verdict, tostring(AK.on), AK.shieldHits, AK.gameNmi, AK.nmiEvents,
        AK.frozen, AK.tried, AK.ok, AK.err, AK.mism, tostring(AK.dead)))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe_soak start tag=%s maxf=%d dlat=%d seed=%d pubtuck=%d dwell=%d ckpt=%d " ..
    "inject=%d[%d,%d] thr(busy=%d mode=%d gap=%d srch=%d)",
    TAG, MAXF, DLAT, SEED, PUBT, DWELL, K.CKPT, K.INJ, K.INJA, K.INJB,
    K.BUSYRUN, K.STALL, K.GAPMAX, K.SRCHSTALL))
