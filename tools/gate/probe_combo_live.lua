-- #140 COMBINED-CART dual liveness + interlock witness (forced-release rig).
--
-- Extends probe_prespipe_force.lua: same one-byte $0318 poke driving the ROM's
-- own release path, PLUS the DRP1SLICE machine's liveness (SL_PH starts /
-- completes, SL_COL tick steps) and the #140 PP_RAN interlock witness: at
-- every slice tick step (SL_COL write, v != 0), PP_PH and PP_RAN must both
-- read 0 -- a nonzero read means a tick ran on a pipeline-work hook, the
-- exact pairing the census certificate forbids. The NOGUARD mutant arm is the
-- positive control: with the guard byte-patched out, viol MUST go nonzero
-- (a witness that cannot fire proves nothing).
--
-- Arms and their expected last lines:
--   control (prespipe-hardened-q3): pp live, sl_* == 0, viol == 0
--   combo   (pp3sl):                pp live, sl live, viol == 0
--   noguard (byte-patched combo):   pp live, sl live, viol  > 0  (witness fires)
local PP_PH, PP_SWAL, PP_RAN = 0x61C2, 0x61C3, 0x61C5
local SL_PH, SL_COL = 0x61BB, 0x61BC
local PRE_LAST2, PRE_ATK2 = 0x6199, 0x0318
local ARMED2 = 0x6161
local W2 = tonumber(os.getenv("PS_W") or "0x5200")
local GO = W2 + 0x84
local OUT  = os.getenv("PS_OUT") or "."
local TAG  = os.getenv("PS_TAG") or "combo"
local MAXF = tonumber(os.getenv("PS_MAXF") or "12000")
local FIRST = tonumber(os.getenv("PS_FIRST") or "1800")
local EVERY = tonumber(os.getenv("PS_EVERY") or "600")
local SIZE  = tonumber(os.getenv("PS_SIZE") or "4")

local f = assert(io.open(OUT .. "/force.log", "w"))
local function log(s) f:write(s .. "\n"); f:flush() end
local function rd(a) return emu.read(a, emu.memType.nesMemory, false) end

local starts, advances, completes, aborts, swal = 0, 0, 0, 0, 0
local ctl_hooks, edges, pokes, gos_after_edge = 0, 0, 0, 0
local maxph, prev = 0, 0
local frame, atk_prev, lastEdgeF, armed_prev = 0, 0, -999, 0
local lastPokeF = -99999
local diag, werr = 0, 0
local fc_prev, fc_stuck, mode_hist = -1, 0, {}
-- slice machine + interlock
local sl_starts, sl_completes, sl_aborts, sl_maxph, sl_prev = 0, 0, 0, 0, 0
local sl_ticks, viol, ppran_sets, ppran_clears = 0, 0, 0, 0

emu.addMemoryCallback(function(addr, value)
  if value == prev then return end
  if prev == 0 and value == 1 then starts = starts + 1
  elseif value == 0 and prev ~= 0 then
    if prev >= maxph and maxph > 0 then completes = completes + 1 else aborts = aborts + 1 end
  elseif value > prev then
    advances = advances + 1
    if value > maxph then maxph = value end
  end
  prev = value
end, emu.callbackType.write, PP_PH, PP_PH)

emu.addMemoryCallback(function(addr, value)
  if value == sl_prev then return end
  if sl_prev == 0 and value == 1 then sl_starts = sl_starts + 1
  elseif value == 0 and sl_prev ~= 0 then
    if sl_prev == 3 then sl_completes = sl_completes + 1 else sl_aborts = sl_aborts + 1 end
  end
  if value > sl_maxph then sl_maxph = value end
  sl_prev = value
end, emu.callbackType.write, SL_PH, SL_PH)

emu.addMemoryCallback(function(addr, value)
  -- v==0 is ambiguous (the arm block zeroes SL_COL); a tick's resume-column
  -- write is nonzero on 7 of 8 steps, so a systematic interlock breach cannot
  -- hide behind the ambiguity. The NOGUARD arm proves the witness can fire.
  if value ~= 0 then
    sl_ticks = sl_ticks + 1
    if rd(PP_PH) ~= 0 or rd(PP_RAN) ~= 0 then viol = viol + 1 end
  end
end, emu.callbackType.write, SL_COL, SL_COL)

emu.addMemoryCallback(function(a, v)
  if v ~= 0 then ppran_sets = ppran_sets + 1 else ppran_clears = ppran_clears + 1 end
end, emu.callbackType.write, PP_RAN, PP_RAN)

emu.addMemoryCallback(function() ctl_hooks = ctl_hooks + 1 end,
                      emu.callbackType.write, PRE_LAST2, PRE_LAST2)
emu.addMemoryCallback(function(a, v) if v ~= 0 then swal = swal + 1 end end,
                      emu.callbackType.write, PP_SWAL, PP_SWAL)
emu.addMemoryCallback(function(addr, value)
  if value == 0 and atk_prev ~= 0 then edges = edges + 1; lastEdgeF = frame end
  atk_prev = value
end, emu.callbackType.write, PRE_ATK2, PRE_ATK2)

local gos_total, gos_near = 0, 0
emu.addMemoryCallback(function()
  gos_total = gos_total + 1
  if (frame - lastEdgeF) <= 4 then gos_near = gos_near + 1 end
end, emu.callbackType.write, GO, GO)

emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  mode_hist[mode] = (mode_hist[mode] or 0) + 1
  local fc = rd(0x43)
  if fc == fc_prev then fc_stuck = fc_stuck + 1 else fc_stuck = 0 end
  fc_prev = fc
  local armed = rd(ARMED2)
  if armed ~= 0 and armed_prev == 0 and (frame - lastEdgeF) <= 8 then
    gos_after_edge = gos_after_edge + 1
  end
  armed_prev = armed

  if mode == 4 and frame >= FIRST and diag < 6 then
    diag = diag + 1
    log(string.format("DIAG f=%d mode=%d atk=%d sinceLast=%d",
        frame, mode, rd(PRE_ATK2), frame - lastPokeF))
  end
  if mode == 4 and frame >= FIRST and (frame - lastPokeF) >= EVERY
     and rd(PRE_ATK2) == 0 then
    local ok, err = pcall(function()
      for k = 0, 3 do
        emu.write(0x0329 + k, (pokes + k) % 3, emu.memType.nesMemory)
      end
      emu.write(PRE_ATK2, SIZE, emu.memType.nesMemory)
    end)
    if not ok then
      if werr < 3 then werr = werr + 1; log("WRITE_ERR " .. tostring(err)) end
    else
      pokes = pokes + 1; lastPokeF = frame
      log(string.format("POKE f=%d readback=%d", frame, rd(PRE_ATK2)))
    end
  end

  if frame >= MAXF then
    local mh = {}
    for k, v in pairs(mode_hist) do mh[#mh + 1] = string.format("%d:%d", k, v) end
    table.sort(mh)
    log(string.format("SUMMARY tag=%s frames=%d pokes=%d release_edges=%d "
      .. "starts=%d advances=%d completes=%d aborts=%d maxphase=%d swallows=%d "
      .. "armedgos=%d GO_total=%d GO_near_edge=%d CTL_hookwrites=%d fc_stuck=%d "
      .. "sl_starts=%d sl_completes=%d sl_aborts=%d sl_maxph=%d sl_ticks=%d "
      .. "ppran_sets=%d ppran_clears=%d viol=%d modes=%s",
      TAG, frame, pokes, edges, starts, advances, completes, aborts, maxph,
      swal, gos_after_edge, gos_total, gos_near, ctl_hooks, fc_stuck,
      sl_starts, sl_completes, sl_aborts, sl_maxph, sl_ticks,
      ppran_sets, ppran_clears, viol,
      table.concat(mh, ",")))
    emu.stop(0)
  end
end, emu.eventType.nmi)

log(string.format("start tag=%s maxf=%d first=%d every=%d size=%d",
                  TAG, MAXF, FIRST, EVERY, SIZE))
