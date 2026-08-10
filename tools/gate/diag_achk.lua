-- diag_achk.lua -- WHY did the A-integrity killed mutant not fail?
--
-- CONTEXT. Phase 2b ran the A-check on the DEFECTIVE cart (087ff959, whose NMI shield begins
-- `LDA $A02E` with no PHA, destroying the accumulator on every NMI) and on the fix (v6e
-- c0082cb3, `PHA ... PLA`). Both reported verdict=PASS, MISMATCH=0, tried=2996, ok=2996,
-- akey=cpu.a. The pre-registered rule fired correctly and the soak disabled the check rather
-- than shipping a detector nobody had seen fail -- but "the mutant did not fail" is a fact about
-- the INSTRUMENT, and it needs a cause, not a shrug.
--
-- WHAT IS ALREADY RULED OUT, so this probe does not re-litigate it:
--  * NOT a wrong register key. akey resolved to cpu.a and ok==tried==2996, so A was read every
--    time. diag_state.lua dumped cpu.a=255 directly.
--  * NOT a value-to-constant comparison. The test is `a ~= AK.apre`, value-to-value, so it is
--    bank-independent and fires whether the clobber writes $00 or $40.
--  * NOT bad event timing IN THE DIRECTION FEARED. NesCpu.cpp:197-207 fires EventType::Nmi
--    AFTER Push(PC), Push(PS) and SetPC(NMIVector) but BEFORE the handler's first instruction
--    executes, and none of that sequence touches A. So A at the nmi event genuinely is A at the
--    interrupt point.
--  * NOT a busy-wait that leaves A pre-loaded with the clobber value: `ad 2e a0` (LDA $A02E)
--    occurs EXACTLY TWICE in the whole ROM, and both are the shield's own mirrors at file
--    0x4EFC and 0xCEFC. Nothing else in the driver reads $A02E, so there is no polling loop
--    that would coincidentally hold [$A02E] in A at interrupt time.
--
-- THE TWO SURVIVING CANDIDATES, which this probe separates in one run:
--  (a) COINCIDENCE OF WORKLOAD. [$A02E] is $00 for banks 0 and 5 at $8000 (it is $40 only for
--      bank 2, and that is the RTI path, which we know is not taken since gameNmi ~= nmi). If
--      the interrupted code essentially always holds A=$00 at NMI time, then clobbering A to
--      $00 is invisible -- the check is CORRECT but BLIND on this workload, and its power is
--      set by how often A is non-zero at interrupt.
--  (b) A BROKEN SAMPLE. One of the two getState() reads is not returning the value at the point
--      I believe it is.
--
-- HOW IT SEPARATES THEM. It records THREE reads per NMI instead of two:
--      A@nmi   -- the event callback, believed to be A at the interrupt point
--      A@CEEC  -- exec callback on the shield's FIRST byte, before `LDA $A02E` has run
--      A@8005  -- exec callback where the shield hands off to the driver
-- A@nmi and A@CEEC MUST be identical: nothing executes between them. That equality is a
-- self-test of the instrument, so this probe validates its own sensor instead of trusting it.
--   * A@nmi != A@CEEC            => candidate (b): the nmi-event sample is the broken one.
--   * A@nmi == A@CEEC == A@8005, and the values are overwhelmingly $00
--                                => candidate (a): blind, not broken. The histogram gives the
--                                   exact power the check would have had.
--   * A@CEEC != A@8005 on the held cart with A@nmi == A@CEEC
--                                => the check should have fired and the fault is in the
--                                   pairing/consumption logic, not in the reads.
-- Run it on the HELD cart FIRST: that is the one where a working instrument must show
-- A@8005 == [$A02E] and A@CEEC == whatever the interrupted code held.
--
-- Env: DA_OUT (dir), DA_MAXF (frames, default 1200), DA_TAG, DA_N (pairs to dump, default 120).
local OUT  = os.getenv("DA_OUT") or "."
local MAXF = tonumber(os.getenv("DA_MAXF") or "1200")
local TAG  = os.getenv("DA_TAG") or "diag_achk"
local NDMP = tonumber(os.getenv("DA_N") or "120")

local logf = io.open(OUT .. "/diag_achk.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local function readA()
  local ok, st = pcall(emu.getState)
  if not ok or type(st) ~= "table" then return nil end
  local v = rawget(st, "cpu.a")
  if type(v) == "number" then return v end
  return nil
end

local D = { nmi = 0, ceec = 0, hit = 0, dumped = 0,
            aNmi = nil, aCeec = nil,
            selfFail = 0,          -- A@nmi ~= A@CEEC : the instrument is lying
            neq = 0,               -- A@CEEC ~= A@8005 : the clobber IS observable
            eq = 0,
            histPre = {}, histPost = {} }

local function bump(h, v) h[v] = (h[v] or 0) + 1 end

emu.addEventCallback(function()
  D.nmi = D.nmi + 1
  D.aNmi = readA()
  D.aCeec = nil
end, emu.eventType.nmi)

-- first byte of the shield, BEFORE `LDA $A02E` (held) / `PHA` (v6e) has executed
emu.addMemoryCallback(function()
  D.ceec = D.ceec + 1
  D.aCeec = readA()
  if D.aNmi ~= nil and D.aCeec ~= nil then
    if D.aNmi ~= D.aCeec then D.selfFail = D.selfFail + 1 end
    bump(D.histPre, D.aCeec)
  end
end, emu.callbackType.exec, 0xCEEC)

emu.addMemoryCallback(function()
  D.hit = D.hit + 1
  local a8 = readA()
  if a8 ~= nil then bump(D.histPost, a8) end
  if D.aCeec ~= nil and a8 ~= nil then
    if D.aCeec ~= a8 then D.neq = D.neq + 1 else D.eq = D.eq + 1 end
    if D.dumped < NDMP then
      D.dumped = D.dumped + 1
      log(string.format("PAIR n=%d A_nmi=%s A_ceec=%d A_8005=%d %s",
          D.nmi, tostring(D.aNmi), D.aCeec, a8,
          (D.aCeec ~= a8) and "CLOBBER_VISIBLE" or "same"))
    end
  end
  D.aCeec = nil
end, emu.callbackType.exec, 0x8005)

local frame = 0
emu.addEventCallback(function()
  frame = frame + 1
  if frame >= MAXF then
    local function top(h, n)
      local ks = {}
      for k in pairs(h) do ks[#ks + 1] = k end
      table.sort(ks, function(x, y) return h[x] > h[y] end)
      local out = {}
      for i = 1, math.min(n, #ks) do out[#out + 1] = string.format("$%02X=%d", ks[i], h[ks[i]]) end
      return table.concat(out, " ")
    end
    log(string.format("A02E_byte_now=%s", tostring(emu.read(0xA02E, emu.memType.nesMemory, false))))
    log(string.format("HIST_PRE(A at CEEC entry)  %s", top(D.histPre, 12)))
    log(string.format("HIST_POST(A at 8005 entry) %s", top(D.histPost, 12)))
    log(string.format("SUMMARY tag=%s frames=%d nmi=%d ceec=%d hit8005=%d " ..
        "SELFTEST_FAIL(Anmi~=Aceec)=%d CLOBBER_VISIBLE(Aceec~=A8005)=%d same=%d",
        TAG, frame, D.nmi, D.ceec, D.hit, D.selfFail, D.neq, D.eq))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("diag_achk start tag=%s maxf=%d", TAG, MAXF))
