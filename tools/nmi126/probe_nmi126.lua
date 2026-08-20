-- probe_nmi126.lua -- measure the NMI's cycle anatomy on a real cart run.
--
-- Per NMI, using cpu.cycleCount (proven exposed in this build, tmp/soak/s-diag):
--   pre  = NMI entry -> wrapper entry #1   (game render/logic head)
--   h1   = wrapper entry #1 -> wrapper RTS (hook 1, driver work)
--   mid  = between the two hooks           (rest of controller read pass 1)
--   h2   = hook 2
--   total ~= pre+h1+mid+h2 (+ a small post-hook tail: register restore + RTI,
--           bounded by the getInputs remainder; reported as +eps, not hidden)
-- OVERRUN WITNESSES (direct, not inferred):
--   shield  = exec at $CEEC where rd($A02E)==$40 (DRRTIVEC absorbing an NMI
--             that fired while the driver bank was mapped = a real overrun)
--   bail    = exec at the wrapper's BUSY-bail RTS (re-entry blocked = a real
--             overrun on a cart whose vectors kept the game path)
-- VOID GUARD: if the wrapper-entry callback stops advancing while frames do,
-- the instrument is dead and the run is VOID, never a thin pass.
--
-- Env: PN_OUT PN_MAXF PN_TAG PN_DLAT PN_W (mailbox base, e.g. 0x5000)
local OUT  = os.getenv("PN_OUT")  or "."
local MAXF = tonumber(os.getenv("PN_MAXF") or "6000")
local DLAT = tonumber(os.getenv("PN_DLAT") or "34")
local TAG  = os.getenv("PN_TAG") or "nmi126"
local W    = tonumber(os.getenv("PN_W") or "0x5000")

local WRAP_ENTRY, WRAP_BAIL, WRAP_RTS = 0xFF54, 0xFF7C, 0xFFC3
local SHIELD = 0xCEEC

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local logf = io.open(OUT .. "/probe_nmi126.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local frame = 0
local function cyc()
  local ok, st = pcall(emu.getState)
  if ok and st then return st["cpu.cycleCount"] end
  return nil
end

-- ---------------- per-NMI anatomy ----------------
local nmi_n, c0 = 0, nil
local hook_i = 0            -- 0/1/2 within the current NMI
local cw, parts = nil, {}
local h1_end = nil
local worst = {}            -- top records {sum,pre,h1,mid,h2,frame,mode}
local mx = {pre=0, h1=0, mid=0, h2=0, sum=0}
local hist = {0,0,0,0,0,0}  -- sum buckets: <8k,<12k,<16k,<20k,<29780,>=29780
local over_sum = 0
local entryHits, exitHits = 0, 0

local function finish_nmi()
  if parts.pre and parts.h1 and parts.h2 then
    local sum = parts.pre + parts.h1 + (parts.mid or 0) + parts.h2
    for _, k in ipairs({"pre", "h1", "mid", "h2"}) do
      local v = parts[k]
      if v and v > mx[k] then mx[k] = v end
    end
    if sum > mx.sum then mx.sum = sum end
    local b = sum < 8000 and 1 or sum < 12000 and 2 or sum < 16000 and 3
              or sum < 20000 and 4 or sum < 29780 and 5 or 6
    hist[b] = hist[b] + 1
    if b == 6 then over_sum = over_sum + 1 end
    if sum > 11000 then
      worst[#worst + 1] = string.format(
        "WORSTNMI f=%d sum=%d pre=%d h1=%d mid=%d h2=%d mode=%02x",
        frame, sum, parts.pre, parts.h1, parts.mid or -1, parts.h2, rd(0x0046))
    end
  end
  parts = {}
  hook_i = 0
  h1_end = nil
end

-- eventType.nmi fired only ONCE per run in this build (measured f=1200 nmi=1),
-- so NMI entry is taken from exec at the game's NMI handler $8005 instead,
-- BANK-QUALIFIED: $8005 is in the switched window and the driver bank holds
-- different bytes there (dr-mario-mesen-exec-callbacks-bank-blind) -- accept
-- only when the base bank is mapped ($A02E reads $00; driver bank reads $40).
emu.addMemoryCallback(function()
  if rd(0xA02E) == 0x40 then return end
  finish_nmi()
  nmi_n = nmi_n + 1
  c0 = cyc()
end, emu.callbackType.exec, 0x8005)

emu.addMemoryCallback(function()
  entryHits = entryHits + 1
  local c = cyc()
  if not c or not c0 then return end
  hook_i = hook_i + 1
  if hook_i == 1 then parts.pre = c - c0
  elseif hook_i == 2 and h1_end then parts.mid = c - h1_end end
  cw = c
end, emu.callbackType.exec, WRAP_ENTRY)

local function hook_exit()
  exitHits = exitHits + 1
  local c = cyc()
  if not c or not cw then return end
  if hook_i == 1 then parts.h1 = c - cw; h1_end = c
  elseif hook_i == 2 then parts.h2 = c - cw end
end
emu.addMemoryCallback(hook_exit, emu.callbackType.exec, WRAP_RTS)

local bail_n = 0
emu.addMemoryCallback(function()
  bail_n = bail_n + 1
  hook_exit()
end, emu.callbackType.exec, WRAP_BAIL)

-- ---------------- overrun witnesses ----------------
local shield_all, shield_absorb = 0, 0
emu.addMemoryCallback(function()
  shield_all = shield_all + 1
  if rd(0xA02E) == 0x40 then shield_absorb = shield_absorb + 1 end
end, emu.callbackType.exec, SHIELD)

-- ---------------- minimal copro mailbox (probe3 pattern) ----------------
local S = {pending=false, go_f=-1, done=0, rcol=3, ror=0}
emu.addMemoryCallback(function()
  S.pending = true; S.go_f = frame; S.done = 0
  -- vary the column a little so the driver actually steers
  S.rcol = (S.rcol + 3) % 8
  S.ror = (S.ror + 1) % 4
end, emu.callbackType.write, W + 0x84)
emu.addMemoryCallback(function()
  if S.pending and (frame - S.go_f) >= DLAT then S.done = 1; S.pending = false end
  return S.done
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return (S.done == 1) and S.ror or 0xFF end,
                      emu.callbackType.read, W + 0x86)

-- ---------------- frame pump + void guard ----------------
local lastEntryHits, stale = 0, 0
local summary_done = false
emu.addEventCallback(function()
  frame = frame + 1
  if frame % 600 == 0 then
    if entryHits == lastEntryHits then stale = stale + 1 else stale = 0 end
    lastEntryHits = entryHits
    if stale >= 2 then
      log(string.format("VOID tag=%s instrument dead: entryHits frozen at %d f=%d",
          TAG, entryHits, frame))
      emu.stop(2)
    end
    log(string.format("TICK f=%d nmi=%d hooks=%d mode=%02x mxsum=%d",
        frame, nmi_n, entryHits, rd(0x0046), mx.sum))
  end
  if frame >= MAXF and not summary_done then
    summary_done = true
    finish_nmi()
    for _, s in ipairs(worst) do log(s) end
    log(string.format("HIST <8k=%d <12k=%d <16k=%d <20k=%d <29780=%d OVER=%d",
        hist[1], hist[2], hist[3], hist[4], hist[5], hist[6]))
    log(string.format(
      "SUMMARY tag=%s frames=%d nmi=%d entry=%d exit=%d bail=%d shield=%d absorb=%d "
      .. "mxpre=%d mxh1=%d mxmid=%d mxh2=%d mxsum=%d over=%d",
      TAG, frame, nmi_n, entryHits, exitHits, bail_n, shield_all, shield_absorb,
      mx.pre, mx.h1, mx.mid, mx.h2, mx.sum, over_sum))
    emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe_nmi126 loaded tag=%s W=%04x maxf=%d dlat=%d", TAG, W, MAXF, DLAT))
