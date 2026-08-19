-- ============================================================================
-- probe_framedense.lua -- PREREG_FRAMEDENSE.md, the DRIVER-PATH test.
--
-- QUESTION (pre-registered): given a publish stream that is CANONICAL BY
-- CONSTRUCTION, can the CART DRIVER ever store a non-canonical TGT_O2 ($6153)
-- on a double capsule?
--
-- WHY THIS SHAPE. Mesen serves the copro mailbox from THIS Lua file -- it never
-- executes copro_rom.hex (gate-standard rule 10). So the firmware cannot be
-- A/B'd here; instead the Lua copro is made the SOURCE of the invariant and the
-- component Mesen DOES execute -- the 6502 cart driver -- is what gets measured.
--
-- THE INVARIANT, derived from source, not from data:
--   * DRDBLCANON (tests/test_search_d3.py `canon_o4` / `_e_dblcanon`) is
--     literally `AND #$FE` on the copro orient o4 when cA == cB.  Canonical
--     copro orients on a double are therefore the EVEN ones, {0, 2}.
--   * The driver's copro->game orient map (patch_cartridge_copro.py, handle()
--     DONE branch; the DRROTFIX anytime weave; the DRRELATCH re-latch) is
--     {0xFF:3, 0:3, 1:1, 2:0, 3:2}.  Even copro -> game {3, 0}; odd -> {1, 2}.
--   => publish EVEN, and a correct driver can only ever store TGT_O2 in {0,3}.
--
-- ARMS (FD_ARM):
--   A  CANON   : on doubles publish only copro orient in {0,2}; non-doubles free;
--                NO tuck descriptors.        expectation: TGT_O2 never in {1,2}
--   B  MUTANT  : on doubles publish only copro orient in {1,3}.  POSITIVE CONTROL
--                -- must fire >= 20% or the whole run is VOID.
--   C  TUCK    : arm A's publisher, PLUS tuck descriptors with ODD orients
--                (mimics tuck_v3.py:745-748, which overwrites S_BEST_O with the
--                tuck's uncanonicalised orient).  TGT_O2 in {1,2} EXPECTED here;
--                confirms the precedence/exclusion rule holds driver-side.
--
-- LOGGING: one CSV row PER HOOK (per frame), carrying the PUBLISHED value next
-- to the STORED value.  Separating "firmware emitted it" from "driver corrupted
-- it" is the entire point and is what save-state sampling could never give.
-- Plus a write-callback census on $6153 itself: every store, with its PC, and
-- the value the mailbox was serving at that instant = the map's truth table.
--
-- Env (ALL REQUIRED except where noted; see the ORPHAN LOG incident in
-- dr-mario-mesen-launch-verification -- no defaulted OUT, no defaulted TAG):
--   FD_OUT FD_TAG FD_ARM FD_W        (FD_W: $5200 on DRPOCKET=0 MiSTer carts,
--   FD_MAXF FD_DLAT FD_SEED FD_TFIND  $5000 on DRPOCKET=1 -- serving the wrong
--                                     base is SILENT: the cart reads open bus.)
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then
    error("\n*** " .. name .. " IS REQUIRED. Refusing to run: an unattributable log\n"
       .. "*** is worse than no log. Launch via run_framedense.sh.\n", 0)
  end
  return v
end
local OUT = need("FD_OUT")
local TAG = need("FD_TAG")
local ARM = need("FD_ARM")
local W   = tonumber(need("FD_W"))
if ARM ~= "A" and ARM ~= "B" and ARM ~= "C" then
  error("\n*** FD_ARM must be exactly A, B or C (got '" .. tostring(ARM) .. "')\n", 0)
end
local MAXF  = tonumber(os.getenv("FD_MAXF") or "60000")
local DLAT  = tonumber(os.getenv("FD_DLAT") or "34")
local SEED  = tonumber(os.getenv("FD_SEED") or "114")
local TFIND = os.getenv("FD_TFIND") or "synth"     -- arm C descriptor source
-- FD_ORIENT: diagnostic override -- publish this COPRO orient on every search instead of
-- drawing from the arm's allowed set.  -1 = normal arm behaviour.
--
-- ⚠ CORRECTED (#132, refuted; #135 adoption pass).  The original note here read: "exists
-- because a per-search RANDOM orient made P2 livelock at the spawn row (13 pills/8000 f vs
-- probe6's 76)", and FD_STALLF's note below claimed "MEASURED: a sustained TGT_O2==2 pins P2
-- at the spawn row indefinitely".  BOTH ARE WRONG, and the second one asserted a CART PROPERTY
-- that does not exist.  #132 root-caused those freezes as the #131 match-restart wedge -- the
-- harness's OWN START press surviving the 8->4 transit into the stock pause routine, which on
-- a P1-native cart is unexitable (#133).  Rotation to game orient 2 works perfectly: 108 pills
-- at 80.5 f/pill once the wedge is removed.  The orient knob only changed how long match 1 ran,
-- which changed the RESTART PHASE, which changed whether a frame%30 press landed on the transit
-- frame.  It was a phase artifact, not orientation.  The knob is still useful for holding orient
-- constant across arms; it is NOT a livelock workaround, and nothing here should be read as
-- evidence about how the cart handles orient 2.
local ORIENT = tonumber(os.getenv("FD_ORIENT") or "-1")
-- FD_STALLF: frames of a completely frozen P2 capsule (X, Y and both colours unchanged) before
-- the harness power-cycles.  Kept as a GENERIC stall backstop -- a denominator made of thousands
-- of copies of one frozen ply is the [[dr-mario-soak-loops-every-2h]] failure, where a big N is
-- a big n_eff of 1, and that hazard is real whatever the cause.  Its original justification (the
-- refuted TGT_O2==2 claim above) is withdrawn; with the #135 guard in place the wedge this
-- actually fired on should no longer occur, so a run that trips STALLF now wants investigating
-- rather than absorbing.
local STALLF = tonumber(os.getenv("FD_STALLF") or "400")
-- FD_ANYTIME: serve a RUNNING BEST during the search instead of $FF-until-DONE.
-- REQUIRED to exercise the DRROTFIX anytime weave and the DRRELATCH re-latch -- the two
-- store sites the prereg names as the surviving surface.  MEASURED without it: those two
-- sites ($858F, $85D0) executed ZERO times in 200,000 frames, because the weave's very
-- first test is `LDA $5286 / CMP #$FF / BEQ nf2_hold`, so an $FF-until-DONE mailbox sends
-- it straight out every hook.  Real firmware live-publishes S_BEST_O throughout the root
-- search, so on silicon that path runs constantly.  A k=0 measured without this would be
-- clearing a path that never ran.
local ANYTIME = tonumber(os.getenv("FD_ANYTIME") or "0")
local ATSTART = tonumber(os.getenv("FD_ATSTART") or "6")    -- first running best, frames after GO
local ATSTEP  = tonumber(os.getenv("FD_ATSTEP") or "30")    -- refresh interval, frames

local CART, CARTID = "?", "?"
pcall(function()
  local ri = emu.getRomInfo()
  CART   = tostring(ri.name or ri.path or "?"):gsub("%s", "_")
  CARTID = tostring(ri.fileSha1 or ri.sha1 or "?"):sub(1, 8)
end)
-- process-unique nonce (math.random unseeded repeats across processes -- measured)
local NONCE = string.format("%x", os.time() % 0x1000000) .. "-" .. tostring({}):sub(-6)

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/framedense.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end
local csvf = io.open(OUT .. "/hooks.csv", "w")
csvf:write("frame,mode,tgt_o2,tgt_c2,tuck_c2,tuck_r2,stable_ct2,last_ori2,rot_done2,armed2," ..
           "c0381,c0382,px0385,py0386,b0387,ori03a5,pub_or,pub_dbl,pub_frame,store_pc,store_n," ..
           "served_or,elig,anom\n")
local csvn = 0

-- ---- driver symbols (patch_cartridge_copro.py) ----
local TGT_C2, TGT_O2       = 0x6152, 0x6153
local ARMED2               = 0x6161
local ROT_DONE2            = 0x616E
local LAST_ORI2, STABLE_CT2 = 0x6170, 0x6171
local TUCK_C2, TUCK_R2     = 0x6179, 0x617A
local PX2, PY2             = 0x0385, 0x0386

local frame, curFrame = 0, 0
local events = {}
local function ev(s) events[#events + 1] = s end

-- ================= Lua copro (the SOURCE of the invariant) =================
local S = { board = {}, done = false, go_f = -1, rcol = 0, ror = 0xFF,
            tcol = 0xFF, trow = 0xFF, pending = false, need_snap = false,
            goes = 0, dones = 0, anypub = 0, pub_f = -1, pub_dbl = 0, upA = -1, upB = -1,
            goA = -1, goB = -1, godbl = 0, tuckpub = 0, dblsearch = 0 }
for i = 0, 127 do S.board[i] = 0xFF end

local lcg = SEED
local function nextrand() lcg = (lcg * 1103515245 + 12345) % 2147483648; return math.floor(lcg / 65536) % 256 end

local function filled(bd, r, c) local v = bd[r * 8 + c]; return v ~= 0xFF and v ~= 0x00 end
local function topfill(bd, c)
  for r = 0, 15 do if filled(bd, r, c) then return r end end
  return 16
end

-- probe6's geometric, executor-shaped tuck finder (realistic descriptor stream)
local function find_tuck(bd)
  for f = 0, 7 do
    local seenFill = false
    for r = 0, 13 do
      if filled(bd, r, f) then
        seenFill = true
      elseif seenFill and not filled(bd, r + 1, f) and not filled(bd, r + 2, f) then
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

-- probe6's synthetic descriptor: fires on nearly every hook, so arm C cannot be
-- vacuous through board luck.  Placement quality is meaningless here and no play
-- metric is read from arm C.
local SLACK, MINROW = 2, 5
local function synth_tuck(bd)
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

local function brain_col(bd)
  local bestCol, bestFill = 0, 99
  for c = 0, 7 do
    local fill = 0
    for r = 0, 15 do if filled(bd, r, c) then fill = fill + 1 end end
    if fill < bestFill then bestFill = fill; bestCol = c end
  end
  return bestCol
end

-- THE PUBLISHER. `dbl` is computed exactly as the firmware computes it
-- (_e_dblcanon: LDA S_CA / EOR S_CB / AND #$0F), from the colour bytes the
-- driver itself uploaded at GO -- not from a Lua-side guess.
local EVEN, ODD, ALL = { 0, 2 }, { 1, 3 }, { 0, 1, 2, 3 }
local function pick(set) return set[1 + (nextrand() % #set)] end
local function choose_orient(dbl)
  if ORIENT >= 0 then return ORIENT end
  if dbl == 1 then
    if ARM == "B" then return pick(ODD) else return pick(EVEN) end
  end
  return pick(ALL)                       -- non-doubles unconstrained in every arm
end

emu.addMemoryCallback(function(addr, value) S.upA = value end, emu.callbackType.write, W + 0x80)
emu.addMemoryCallback(function(addr, value) S.upB = value end, emu.callbackType.write, W + 0x81)

emu.addMemoryCallback(function()
  S.go_f = curFrame; S.done = false; S.pending = true; S.need_snap = true
  S.ror = 0xFF; S.goes = S.goes + 1
  S.goA, S.goB = S.upA, S.upB
  S.godbl = (S.goA >= 0 and S.goB >= 0 and (S.goA % 16) == (S.goB % 16)) and 1 or 0
  if S.godbl == 1 then S.dblsearch = S.dblsearch + 1 end
end, emu.callbackType.write, W + 0x84)

emu.addMemoryCallback(function()
  if S.done then return 1 end
  if S.pending and not S.need_snap and (curFrame - S.go_f) >= DLAT then
    local bc = brain_col(S.board)
    local f, a, rt
    if ARM == "C" then
      if TFIND == "geom" then f, a, rt = find_tuck(S.board) else f, a, rt = synth_tuck(S.board) end
    end
    if f then
      -- tuck commit: column := final, orient := the tuck's own (ODD, uncanonicalised)
      S.rcol = f % 8; S.ror = pick(ODD); S.tcol = a; S.trow = rt
      S.tuckpub = S.tuckpub + 1
    else
      S.rcol = bc % 8; S.ror = choose_orient(S.godbl); S.tcol = 0xFF; S.trow = 0xFF
    end
    S.pub_f = curFrame; S.pub_dbl = S.godbl
    S.done = true; S.pending = false; S.dones = S.dones + 1
    if S.dones <= 20 then
      ev(string.format("SEARCH #%d f=%d cA=%02X cB=%02X dbl=%d pub_col=%d pub_or=%d tcol=%d trow=%d",
         S.dones, curFrame, S.goA % 256, S.goB % 256, S.godbl, S.rcol, S.ror, S.tcol, S.trow))
    end
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return S.tcol end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return S.trow end, emu.callbackType.read, W + 0x88)

-- ================= the TGT_O2 store census (published -> stored, by PC) ======
-- getState IS safe inside a memory callback (probe10.lua:383).  The key map is
-- FLAT with dotted keys -- st.cpu.pc is nil and would silently log -1 forever
-- (the DRSTUDYCOUNTS SC_PC no-op).  Proven live by pc_ok below.
local store_n, store_pc, store_pub, store_pub_dbl = 0, -1, -1, -1
local pc_ok, pc_fail = 0, 0
local xtab = {}          -- xtab[pub_or][stored] = count      (the truth table)
local pctab = {}         -- pctab[pc] = {n=, odd=}            (localisation)
local storeLog = {}
emu.addMemoryCallback(function(addr, value)
  local pc = -1
  local ok, st = pcall(function() return emu.getState() end)
  if ok and type(st) == "table" then pc = st["cpu.pc"] or -1 end
  if pc >= 0 then pc_ok = pc_ok + 1 else pc_fail = pc_fail + 1 end
  store_n = store_n + 1; store_pc = pc; store_pub = S.ror; store_pub_dbl = S.pub_dbl
  local k = S.ror
  xtab[k] = xtab[k] or {}
  xtab[k][value] = (xtab[k][value] or 0) + 1
  pctab[pc] = pctab[pc] or { n = 0, odd = 0 }
  pctab[pc].n = pctab[pc].n + 1
  if value == 1 or value == 2 then pctab[pc].odd = pctab[pc].odd + 1 end
  if #storeLog < 60 then
    storeLog[#storeLog + 1] = string.format("STORE #%d f=%d pc=$%04X pub_or=%d stored=%d dbl=%d",
      store_n, curFrame, pc, S.ror, value, S.pub_dbl)
  end
end, emu.callbackType.write, TGT_O2)

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

-- ================= counters =================
local N_elig, k_naive, k_strict, k_pubodd = 0, 0, 0, 0
local N_dblrows, N_settled, N_mode4 = 0, 0, 0
local N_elig_tuckrow, k_tuckrow = 0, 0        -- rows WITH a live descriptor (arm C)
local anomLog = {}
local nPills = 0
-- ply-level de-duplication: a ply is (match, pill).  Hook-rows within one ply are NOT
-- independent samples, so both denominator and numerator are reported at BOTH levels.
local plyElig, plyAnom = {}, {}
local nStall, resets, resetOK = 0, 0, "?"
local frozenFor, lastSig = 0, ""
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

    -- ---- ANYTIME running-best publish (see FD_ANYTIME) ----
    if ANYTIME == 1 and S.pending and not S.need_snap and not S.done then
      local age = curFrame - S.go_f
      if age >= ATSTART and ((age - ATSTART) % ATSTEP) == 0 then
        S.rcol = brain_col(S.board) % 8
        S.ror = choose_orient(S.godbl)     -- SAME allowed set as the arm's final publish:
        S.pub_f = curFrame                 -- the stream stays canonical by construction
        S.pub_dbl = S.godbl
        S.anypub = S.anypub + 1
      end
    end

    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d goes=%d dones=%d stores=%d N=%d k=%d",
          frame, prevMode, mode, S.goes, S.dones, store_n, N_elig, k_naive))
      if mode == 4 and prevMode ~= 4 then matchesStarted = matchesStarted + 1 end
      if prevMode == 4 and mode ~= 4 then
        matchesEnded = matchesEnded + 1
        if mode == 0 then
          aborts = aborts + 1
          log(string.format("!!! CATASTROPHIC 4->0 f=%d (#%d) !!!", frame, aborts))
        else
          cleanEnds = cleanEnds + 1
        end
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

    local py, px = rd(PY2), rd(PX2)
    if prevPy >= 0 and py > prevPy then nPills = nPills + 1 end
    prevPy = py

    -- ---- THE PRE-REGISTERED PREDICATE, evaluated per hook ----
    local o2, c2 = rd(TGT_O2), rd(TGT_C2)
    local tc, tr = rd(TUCK_C2), rd(TUCK_R2)
    local st, lo, rdn, am = rd(STABLE_CT2), rd(LAST_ORI2), rd(ROT_DONE2), rd(ARMED2)
    local cA, cB = rd(0x0381), rd(0x0382)
    local b87, o3a5 = rd(0x0387), rd(0x03A5)

    N_mode4 = N_mode4 + 1
    local dbl     = (cA % 16) == (cB % 16)                 -- condition 1
    local settled = st >= 8                                -- condition 2
    local odd     = (o2 == 1 or o2 == 2)                   -- condition 3
    local notuck  = (tc == 0xFF and tr == 16)              -- condition 4 (FIXED in the prereg)
    if dbl then N_dblrows = N_dblrows + 1 end
    if settled then N_settled = N_settled + 1 end

    local ply = string.format("%d:%d", matchesStarted, nPills)
    local elig, anom = 0, 0
    if dbl and settled and notuck then
      elig = 1; N_elig = N_elig + 1; plyElig[ply] = true
      if odd then
        anom = 1; k_naive = k_naive + 1; plyAnom[ply] = true
        -- condition 5: was the publish that produced this stored value canonical?
        if store_pub == 0 or store_pub == 2 or store_pub == 0xFF then
          k_strict = k_strict + 1
        else
          k_pubodd = k_pubodd + 1
        end
        if #anomLog < 80 then
          anomLog[#anomLog + 1] = string.format(
            "ANOMALY f=%d TGT_O2=%d TGT_C2=%d STABLE=%d TUCK_C2=$%02X TUCK_R2=%d cA=%d cB=%d " ..
            "pub_or=%d pub_dbl=%d store_pc=$%04X store_n=%d rot_done=%d armed=%d",
            frame, o2, c2, st, tc, tr, cA % 16, cB % 16, store_pub, store_pub_dbl,
            store_pc, store_n, rdn, am)
        end
      end
    elseif dbl and settled and not notuck then
      N_elig_tuckrow = N_elig_tuckrow + 1
      if odd then k_tuckrow = k_tuckrow + 1 end
    end

    csvn = csvn + 1
    csvf:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
      frame, mode, o2, c2, tc, tr, st, lo, rdn, am, cA, cB, px, py, b87, o3a5,
      store_pub, store_pub_dbl, S.pub_f, store_pc, store_n, S.ror, elig, anom))
    if csvn % 2000 == 0 then csvf:flush() end

    -- ---- stall watchdog: power-cycle a frozen P2 rather than bank duplicate rows ----
    local sig = string.format("%d/%d/%d/%d", px, py, cA, cB)
    if sig == lastSig then frozenFor = frozenFor + 1 else frozenFor = 0; lastSig = sig end
    if frozenFor >= STALLF then
      nStall = nStall + 1
      log(string.format("STALL f=%d frozen=%d px=%d py=%d cA=%d cB=%d TGT_O2=%d TGT_C2=%d " ..
          "ori03a5=%d rot_done=%d armed=%d served_or=%d -> RESET",
          frame, frozenFor, px, py, cA, cB, o2, c2, o3a5, rdn, am, S.ror))
      local ok1 = pcall(function() emu.reset() end)
      if ok1 then resets = resets + 1; resetOK = "reset"
      else
        local ok2 = pcall(function() emu.power() end)
        if ok2 then resets = resets + 1; resetOK = "power" else resetOK = "NONE" end
      end
      frozenFor = 0; lastSig = ""
      prevMode = -1; lvlPoked = false; round = round + 1; prevPy = -1
      S.pending = false; S.done = false; S.need_snap = false
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF then
    for _, s in ipairs(storeLog) do log(s) end
    for _, s in ipairs(anomLog) do log(s) end
    for p = 0, 255 do
      if xtab[p] then
        for v = 0, 255 do
          if xtab[p][v] then log(string.format("XTAB pub_or=%d stored=%d n=%d", p, v, xtab[p][v])) end
        end
      end
    end
    local nply, nplyk = 0, 0
    for _ in pairs(plyElig) do nply = nply + 1 end
    for _ in pairs(plyAnom) do nplyk = nplyk + 1 end
    for pc, t in pairs(pctab) do
      log(string.format("PCTAB pc=$%04X n=%d odd_stores=%d", pc, t.n, t.odd))
    end
    log(string.format("SUMMARY tag=%s arm=%s cart=%s cartid=%s nonce=%s w=$%04X tfind=%s " ..
        "frames=%d mode4=%d pills=%d goes=%d dones=%d dblsearch=%d tuckpub=%d anypub=%d " ..
        "stores=%d pc_ok=%d pc_fail=%d matches_started=%d matches_ended=%d clean_ends=%d ABORT_4to0=%d " ..
        "dblrows=%d settledrows=%d N=%d k_naive=%d k_strict=%d k_pubodd=%d " ..
        "N_tuckrow=%d k_tuckrow=%d csvrows=%d stalls=%d resets=%d resetmode=%s " ..
        "N_ply=%d k_ply=%d orientknob=%d",
        TAG, ARM, CART, CARTID, NONCE, W, TFIND,
        frame, N_mode4, nPills, S.goes, S.dones, S.dblsearch, S.tuckpub, S.anypub,
        store_n, pc_ok, pc_fail, matchesStarted, matchesEnded, cleanEnds, aborts,
        N_dblrows, N_settled, N_elig, k_naive, k_strict, k_pubodd,
        N_elig_tuckrow, k_tuckrow, csvn, nStall, resets, resetOK,
        nply, nplyk, ORIENT))
    csvf:flush(); csvf:close(); logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("framedense start tag=%s arm=%s cart=%s cartid=%s nonce=%s out=%s w=$%04X " ..
    "maxf=%d dlat=%d seed=%d tfind=%s", TAG, ARM, CART, CARTID, NONCE, OUT, W, MAXF, DLAT, SEED, TFIND))
