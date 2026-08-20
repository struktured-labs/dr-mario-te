-- #126 enforcement 2 LIVENESS WITNESS.
-- The probe6 A/B shows the pipelined cart does no harm; it does NOT show the
-- pipelined path ever RAN. A "no harm" result on a path that never executed is
-- the vacuous-gate failure mode, so this counts the machine's own transitions.
--
-- PP_PH ($61C2) is PRG-RAM, so a write callback on it is unambiguous -- the
-- bank-qualification hazard (dr-mario-mesen-exec-callbacks-bank-blind) applies
-- to EXEC callbacks on the switched $8000-$BFFF window, not to a RAM address.
local PP_PH, PP_SWAL = 0x61C2, 0x61C3
local OUT  = os.getenv("PS_OUT") or "."
local TAG  = os.getenv("PS_TAG") or "prespipe"
local MAXF = tonumber(os.getenv("PS_MAXF") or "9000")

local f = assert(io.open(OUT .. "/prespipe.log", "w"))
local function log(s) f:write(s .. "\n"); f:flush() end

local starts, advances, completes, aborts, swal = 0, 0, 0, 0, 0
local maxph, prev, frame = 0, 0, 0
local phase_hist = {}

emu.addMemoryCallback(function(addr, value)
  if value == prev then return end
  if prev == 0 and value == 1 then
    starts = starts + 1
  elseif value == 0 and prev ~= 0 then
    -- phase 0 from the LAST phase is a completion (commit or a late bail);
    -- from any earlier phase it is an abort or an early bail.
    if prev >= maxph and maxph > 0 then completes = completes + 1
    else aborts = aborts + 1 end
  elseif value > prev then
    advances = advances + 1
    if value > maxph then maxph = value end
  end
  phase_hist[value] = (phase_hist[value] or 0) + 1
  prev = value
end, emu.callbackType.write, PP_PH, PP_PH)

emu.addMemoryCallback(function(addr, value)
  if value ~= 0 then swal = swal + 1 end
end, emu.callbackType.write, PP_SWAL, PP_SWAL)

emu.addEventCallback(function()
  frame = frame + 1
  if frame >= MAXF then
    local hs = {}
    for k, v in pairs(phase_hist) do hs[#hs + 1] = string.format("%d:%d", k, v) end
    table.sort(hs)
    log(string.format("SUMMARY tag=%s frames=%d starts=%d advances=%d completes=%d "
      .. "aborts=%d maxphase=%d swallows=%d hist=%s",
      TAG, frame, starts, advances, completes, aborts, maxph, swal,
      table.concat(hs, ",")))
    emu.stop(0)
  end
end, emu.eventType.nmi)

log(string.format("start tag=%s maxf=%d", TAG, MAXF))
