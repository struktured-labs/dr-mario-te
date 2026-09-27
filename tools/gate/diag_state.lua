-- ============================================================================
-- diag_state.lua -- capability probe, NOT a gate. Answers three questions that decide whether a
-- per-NMI A-INTEGRITY assertion is buildable in THIS Mesen build, before any five-hour run is
-- designed around one:
--
--   Q1. Does emu.getState() expose the 6502 accumulator, and under what key path?
--       README_GATE says `emu.getState().cpu` is nil. That may mean "no registers" or merely
--       "different key". Those have opposite consequences, so it is dumped rather than assumed.
--   Q2. May emu.getState() be called INSIDE a memory callback? README_GATE says no emu.* call
--       may run there and that the failure is SILENT (the callback stops firing). So this probe
--       calls it under pcall AND keeps counting hits afterwards: if the count freezes, the
--       callback died and the answer is no, which is itself detected rather than assumed.
--   Q3. Is the DRRTIVEC shield at $CEEC actually EXECUTED during play? The whole A-clobber
--       concern is conditional on that path being live. Counting is register-free, so this
--       answer is available regardless of Q1/Q2.
--
-- Env: DG_OUT DG_MAXF DG_TAG
-- ============================================================================
local OUT  = os.getenv("DG_OUT") or "."
local MAXF = tonumber(os.getenv("DG_MAXF") or "600")
local TAG  = os.getenv("DG_TAG") or "diag"

local NES = emu.memType.nesMemory
local logf = io.open(OUT .. "/diag_state.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local frame = 0
local pend = {}     -- lines produced inside callbacks, flushed from endFrame

-- ---- Q3: shield / game-NMI execution counts (no emu.* inside, so always valid) ----
local nShield, nGameNmi, nNmiEvent = 0, 0, 0
emu.addMemoryCallback(function() nShield = nShield + 1 end, emu.callbackType.exec, 0xCEEC)

-- ---- Q2: does getState survive inside a memory callback? ----
local cbTried, cbOk, cbErr, cbAfter = 0, 0, 0, 0
local cbA = {}
emu.addMemoryCallback(function()
  nGameNmi = nGameNmi + 1
  cbAfter = nGameNmi              -- if this stops advancing after the pcall, the callback died
  if cbTried < 5 then
    cbTried = cbTried + 1
    local ok, st = pcall(emu.getState)
    if ok and type(st) == "table" then cbOk = cbOk + 1; cbA[#cbA + 1] = st else cbErr = cbErr + 1 end
  end
end, emu.callbackType.exec, 0x8005)

-- ---- Q1: NMI event callback + full state dump ----
local dumped = false
local function dump(t, prefix, depth)
  if depth > 2 then return end
  local keys = {}
  for k, _ in pairs(t) do keys[#keys + 1] = tostring(k) end
  table.sort(keys)
  for _, k in ipairs(keys) do
    local v = t[k]
    local tv = type(v)
    if tv == "table" then
      log(string.format("STATE %s%s = <table>", prefix, k))
      dump(v, prefix .. k .. ".", depth + 1)
    else
      log(string.format("STATE %s%s = %s (%s)", prefix, k, tostring(v), tv))
    end
  end
end

emu.addEventCallback(function()
  nNmiEvent = nNmiEvent + 1
end, emu.eventType.nmi)

emu.addEventCallback(function()
  frame = frame + 1
  for _, s in ipairs(pend) do log(s) end; pend = {}

  if frame == 3 then
    local ok, st = pcall(emu.getState)
    log("Q1 getState from endFrame: ok=" .. tostring(ok) .. " type=" .. type(st))
    if ok and type(st) == "table" then dump(st, "", 0) end
    dumped = true
  end

  if frame == MAXF then
    log(string.format("Q2 inside-memory-callback getState: tried=%d ok=%d err=%d", cbTried, cbOk, cbErr))
    log(string.format("Q2 callback ALIVE after the pcall? gameNmi_hits_now=%d (frozen == callback died)", nGameNmi))
    if #cbA > 0 and type(cbA[1]) == "table" then
      log("Q2 state captured INSIDE a memory callback -- dumping first:")
      dump(cbA[1], "CB.", 1)
    end
    log(string.format("SUMMARY tag=%s frames=%d shield_CEEC=%d gameNmi_8005=%d nmi_events=%d dumped=%s",
        TAG, frame, nShield, nGameNmi, nNmiEvent, tostring(dumped)))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("diag_state start tag=%s maxf=%d", TAG, MAXF))
