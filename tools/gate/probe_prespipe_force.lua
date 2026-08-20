-- #126 enforcement 2 FORCED-RELEASE LIVENESS.
--
-- WHY: the 18k probe6 A/B is VACUOUS for this code path. Measured on the same
-- carts, 12,000 frames: atk_release_edges = 0 -- P2 never receives a garbage
-- volley in a CvC run, so DRPRESTART (and therefore DRPRESPIPE) never fires.
-- The battery shows the cart is healthy; it cannot show the pipeline works.
--
-- WHAT THIS DOES: pokes p1_attackSize ($0318) during play, which is exactly
-- what the ROM writes when P1 lands a multi-virus clear. The ROM's own
-- checkReleaseAttack then drops the garbage and clears the byte -- and THAT
-- clear is the release edge the prestart triggers on. One byte, at an NMI
-- boundary, driving the real ROM path: far less invasive than probe9's
-- whole-RAM restore, and the release itself is the ROM's, not the probe's.
--
-- The CONTROL cart (no DRPRESPIPE) is the discriminator: it must show release
-- edges and ZERO PP_PH transitions. Equal edge counts with zero phases on one
-- arm and nonzero on the other is the pair that means anything.
local PP_PH, PP_SWAL = 0x61C2, 0x61C3
local PRE_LAST2, PRE_ATK2 = 0x6199, 0x0318
local ARMED2 = 0x6161
local OUT  = os.getenv("PS_OUT") or "."
local TAG  = os.getenv("PS_TAG") or "force"
local MAXF = tonumber(os.getenv("PS_MAXF") or "12000")
local FIRST = tonumber(os.getenv("PS_FIRST") or "1800")   -- well into play
local EVERY = tonumber(os.getenv("PS_EVERY") or "600")
local SIZE  = tonumber(os.getenv("PS_SIZE") or "4")

local f = assert(io.open(OUT .. "/force.log", "w"))
local function log(s) f:write(s .. "\n"); f:flush() end
local function rd(a) return emu.read(a, emu.memType.nesMemory, false) end

local starts, advances, completes, aborts, swal = 0, 0, 0, 0, 0
local ctl_hooks, edges, pokes, gos_after_edge = 0, 0, 0, 0
local maxph, prev = 0, 0
local frame, atk_prev, lastEdgeF, armed_prev = 0, 0, -999, 0
-- wedge canaries: the driver freezing is the failure this whole family is about
local fc_prev, fc_stuck, mode_hist = -1, 0, {}

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

emu.addMemoryCallback(function() ctl_hooks = ctl_hooks + 1 end,
                      emu.callbackType.write, PRE_LAST2, PRE_LAST2)
emu.addMemoryCallback(function(a, v) if v ~= 0 then swal = swal + 1 end end,
                      emu.callbackType.write, PP_SWAL, PP_SWAL)
emu.addMemoryCallback(function(addr, value)
  if value == 0 and atk_prev ~= 0 then edges = edges + 1; lastEdgeF = frame end
  atk_prev = value
end, emu.callbackType.write, PRE_ATK2, PRE_ATK2)

emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  mode_hist[mode] = (mode_hist[mode] or 0) + 1
  local fc = rd(0x43)
  if fc == fc_prev then fc_stuck = fc_stuck + 1 else fc_stuck = 0 end
  fc_prev = fc
  -- a GO issued within 8 frames of a release edge is a PRESTART go, not a
  -- spawn-edge go: the spawn is >= 24 frames away by the window formula.
  local armed = rd(ARMED2)
  if armed ~= 0 and armed_prev == 0 and (frame - lastEdgeF) <= 8 then
    gos_after_edge = gos_after_edge + 1
  end
  armed_prev = armed

  if mode == 4 and frame >= FIRST and (frame - FIRST) % EVERY == 0
     and rd(PRE_ATK2) == 0 then
    -- attackColors alongside the size: checkReleaseAttack reads both, and a
    -- size with stale colours would drop a malformed volley. 0-based colours
    -- (dr-mario-copro-0based-colors), varied per poke so the volley is not
    -- always one colour (a single-colour volley is the 4-run bail case and
    -- would make every release bail -- a liveness run that proves nothing).
    for k = 0, 3 do
      emu.write(0x0329 + k, (pokes + k) % 3, emu.memType.nesMemory, false)
    end
    emu.write(PRE_ATK2, SIZE, emu.memType.nesMemory, false)
    pokes = pokes + 1
  end

  if frame >= MAXF then
    local mh = {}
    for k, v in pairs(mode_hist) do mh[#mh + 1] = string.format("%d:%d", k, v) end
    table.sort(mh)
    log(string.format("SUMMARY tag=%s frames=%d pokes=%d release_edges=%d "
      .. "starts=%d advances=%d completes=%d aborts=%d maxphase=%d swallows=%d "
      .. "prestart_gos=%d CTL_hookwrites=%d fc_stuck=%d modes=%s",
      TAG, frame, pokes, edges, starts, advances, completes, aborts, maxph,
      swal, gos_after_edge, ctl_hooks, fc_stuck, table.concat(mh, ",")))
    emu.stop(0)
  end
end, emu.eventType.nmi)

log(string.format("start tag=%s maxf=%d first=%d every=%d size=%d",
                  TAG, MAXF, FIRST, EVERY, SIZE))
