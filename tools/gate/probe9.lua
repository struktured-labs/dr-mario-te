-- ============================================================================
-- probe9.lua -- REPRODUCTION GATE for task #129 (the 2026-08-18 soak wedge).
--
-- CLAIM UNDER TEST: the wedge is a NON-TERMINATING LOOP IN STOCK GAME LOGIC
-- (checkVerMatch's vertical colour scan), not in the driver / copro / tuck path.
-- The vertical scan steps fieldPos_tmp by +8 and only stops when the index
-- wraps into 0..7 (`and #$F8 / beq`) -- it has NO field-boundary check. So a
-- colour chain reaching the bottom row runs on through the 128 bytes AFTER the
-- field (P2: fireworksData_RAM $0580-$05FF). If those bytes all share the
-- chain's colour nibble the index wraps to 0..7, that value is written back to
-- fieldPos, and the whole scan restarts from the top of a column, forever.
--
-- METHOD: restore the RAM captured from the wedged MiSTer, then let the real
-- ROM run. The ONLY difference between the two arms is 128 bytes:
--
--   ARM  (P9_MODE=arm)  $0580-$05FF = as captured ($BF)   -> predict WEDGE
--   CTRL (P9_MODE=ctrl) $0580-$05FF = $00                 -> predict NO WEDGE
--   BASE (P9_MODE=base) no injection at all               -> harness plays
--
-- CTRL is what makes this a gate rather than a demonstration: if the injected
-- state hangs the ROM for ANY reason (a bad restore, a confused action state),
-- CTRL hangs too and the arm is void. Only ARM-hangs-and-CTRL-recovers isolates
-- the 128 bytes as the cause.
--
-- WEDGE detector (all three must hold, so a merely slow frame cannot trip it):
--   * frameCounter $0043 is still advancing   (the NMI is alive)
--   * p2_pillPlacedStep $0387 stays 6         (parked in checkVerMatch)
--   * P2 field $0500-$057F byte-identical for the whole observation window
--
-- Env: P9_OUT P9_TAG P9_MODE [P9_MAXF P9_INJF P9_OBSF P9_RAM P9_W P9_DLAT]
-- ============================================================================
local function need(name)
  local v = os.getenv(name)
  if v == nil or v == "" then
    error("\n*** " .. name .. " IS REQUIRED. Refusing to run: an unattributable log\n"
       .. "*** is worse than no log. Launch via run_probe9.sh, never by hand.\n", 0)
  end
  return v
end
local OUT  = need("P9_OUT")
local TAG  = need("P9_TAG")
local MODE = need("P9_MODE")            -- arm | ctrl | base
if MODE ~= "arm" and MODE ~= "ctrl" and MODE ~= "base" then
  error("\n*** P9_MODE must be exactly arm|ctrl|base (got '" .. MODE .. "')\n", 0)
end
local RAMFILE = os.getenv("P9_RAM") or ""
if MODE ~= "base" and RAMFILE == "" then error("\n*** P9_RAM required for arm/ctrl\n", 0) end

local MAXF = tonumber(os.getenv("P9_MAXF") or "9000")
local INJF = tonumber(os.getenv("P9_INJF") or "3000")   -- inject once we are well into play
local OBSF = tonumber(os.getenv("P9_OBSF") or "1800")   -- observation window after injection
local DLAT = tonumber(os.getenv("P9_DLAT") or "34")
local W    = tonumber(os.getenv("P9_W") or "0x5200")

local CART, CARTID = "?", "?"
pcall(function()
  local ri = emu.getRomInfo()
  CART   = tostring(ri.name or ri.path or "?"):gsub("%s", "_")
  CARTID = tostring(ri.fileSha1 or ri.sha1 or "?"):sub(1, 8)
end)
local NONCE = string.format("%x", os.time() % 0x1000000) .. "-" .. tostring({}):sub(-6)

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a, v) emu.write(a, v, NES) end
local logf = io.open(OUT .. "/probe9.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

-- ---- captured RAM ----------------------------------------------------------
local RAM = nil
if MODE ~= "base" then
  local fh = io.open(RAMFILE, "r")
  if not fh then error("\n*** cannot open P9_RAM " .. RAMFILE .. "\n", 0) end
  local hex = fh:read("*a"):gsub("%s", ""); fh:close()
  if #hex ~= 2048 * 2 then
    error(string.format("\n*** P9_RAM must be 2048 bytes of hex (got %d chars)\n", #hex), 0)
  end
  RAM = {}
  for i = 0, 2047 do RAM[i] = tonumber(hex:sub(i * 2 + 1, i * 2 + 2), 16) end
end

-- ================= copro mailbox (probe6's emulator, no tuck) ===============
local S = { board = {}, done = false, go_f = -1, rcol = 0, ror = 0xFF,
            pending = false, need_snap = false, goes = 0, dones = 0 }
for i = 0, 127 do S.board[i] = 0xFF end
local frame, curFrame = 0, 0
local function filled(bd, r, c) local v = bd[r * 8 + c]; return v ~= 0xFF and v ~= 0x00 end
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
    S.rcol = bc % 8; S.ror = bo % 4
    S.done = true; S.pending = false; S.dones = S.dones + 1
    return 1
  end
  return 0
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return 0xFF   end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return 0xFF   end, emu.callbackType.read, W + 0x88)

-- ================= input (nav to a VS-CPU match) ============================
local modeCache = -1
local inCur, inUntil = nil, -1
emu.addEventCallback(function()
  if inCur and frame < inUntil and modeCache ~= 4 then emu.setInput(inCur, 0) end
end, emu.eventType.inputPolled)
local function press(i, d) inCur = i; inUntil = frame + (d or 4) end

-- ================= state ====================================================
local injected, injF = false, -1
local verdict, verdictF = "NONE", -1
local baseField, fcAtInj, stepAtInj = nil, -1, -1
local fcSeen, fieldChangedF, stepLeftF, modeLeftF = {}, -1, -1, -1
local lvlPoked, prevMode = false, -1

local function snapField()
  local t = {}
  for i = 0, 127 do t[i] = rd(0x0500 + i) end
  return t
end

-- ⚠ RESTORE A WHITELIST, NOT ALL 2 KB. The first version of this probe wrote the whole
-- $0000-$07FF image back, which includes the STACK PAGE -- so the main loop returned into
-- the captured (foreign) return addresses and the game fell out of mode 4 into mode $FF one
-- frame later. That is a broken restore, not a wedge, and it would have read as "no repro".
-- Restoring only the two player blocks and the two fields leaves the live call chain and the
-- zero-page working pointers alone, so the ROM keeps executing its own code on captured data.
local RESTORE = { { 0x0300, 0x03AF }, { 0x0400, 0x05FF } }

local function do_inject()
  for _, rg in ipairs(RESTORE) do
    for a = rg[1], rg[2] do wr(a, RAM[a]) end
  end
  if MODE == "ctrl" then
    for i = 0, 127 do wr(0x0580 + i, 0x00) end
  end
  injected = true; injF = frame
  baseField = snapField()
  fcAtInj = rd(0x43); stepAtInj = rd(0x0387)
  log(string.format("INJECT f=%d mode=%s step=%d fc=%d fw0=%02X field0=%02X",
      frame, MODE, rd(0x0387), rd(0x43), rd(0x0580), rd(0x0500)))
end

emu.addEventCallback(function()
  local ok, err = pcall(function()
    frame = frame + 1; curFrame = frame
    local mode = rd(0x46); modeCache = mode
    if S.need_snap then
      for i = 0, 127 do local v = rd(0x0500 + i); if v == 0x00 then v = 0xFF end; S.board[i] = v end
      S.need_snap = false
    end
    if mode ~= prevMode then
      log(string.format("MODE f=%d %d->%d goes=%d dones=%d", frame, prevMode, mode, S.goes, S.dones))
      prevMode = mode
    end

    -- Once injected we must KEEP OBSERVING even if the game leaves mode 4 -- escaping play is
    -- itself the strongest possible evidence of NO wedge, and bailing out here would have
    -- silently scored a healthy recovery as "verdict=NONE".
    if mode ~= 4 and not injected then
      if mode >= 1 and mode <= 3 then
        if not lvlPoked then
          if rd(0x0316) ~= 11 then wr(0x0316, 11) end
          if rd(0x0396) ~= 11 then wr(0x0396, 11) end
          wr(0x96, 11); wr(0x45, 1); lvlPoked = true
        end
        if frame % 12 == 0 then press({ start = true }, 4) end
      else
        if frame % 30 == 0 then press({ start = true }, 4) end
      end
      return
    end
    lvlPoked = false

    if (not injected) and MODE ~= "base" and frame >= INJF then do_inject(); return end
    if not injected then return end

    -- ---- observation ----
    fcSeen[rd(0x43)] = true
    if mode ~= 4 and modeLeftF < 0 then modeLeftF = frame end
    if rd(0x0387) ~= 6 and stepLeftF < 0 then stepLeftF = frame end
    if fieldChangedF < 0 then
      for i = 0, 127 do
        if rd(0x0500 + i) ~= baseField[i] then fieldChangedF = frame; break end
      end
    end
    if verdict == "NONE" and frame >= injF + OBSF then
      local nfc = 0
      for _ in pairs(fcSeen) do nfc = nfc + 1 end
      local nmiAlive   = nfc >= 8
      local stepParked = (stepLeftF < 0) and (modeLeftF < 0)
      local fieldFrozen= (fieldChangedF < 0)
      if nmiAlive and stepParked and fieldFrozen then verdict = "WEDGE"
      else verdict = "NO_WEDGE" end
      verdictF = frame
      log(string.format("VERDICT %s f=%d nmi_frameCounter_values=%d step_left_at=%d field_changed_at=%d mode_left_at=%d",
          verdict, frame, nfc, stepLeftF, fieldChangedF, modeLeftF))
    end
  end)
  if not ok then log("ERR " .. tostring(err)) end

  if frame >= MAXF or (verdict ~= "NONE" and frame >= verdictF + 60) then
    local nfc = 0
    for _ in pairs(fcSeen) do nfc = nfc + 1 end
    log(string.format(
      "SUMMARY tag=%s mode=%s cart=%s cartid=%s nonce=%s frames=%d inj_f=%d verdict=%s " ..
      "fc_values=%d step_left_at=%d field_changed_at=%d mode_left_at=%d goes=%d dones=%d",
      TAG, MODE, CART, CARTID, NONCE, frame, injF, verdict,
      nfc, stepLeftF, fieldChangedF, modeLeftF, S.goes, S.dones))
    logf:close(); emu.stop(0)
  end
end, emu.eventType.endFrame)

log(string.format("probe9 start tag=%s mode=%s cart=%s cartid=%s nonce=%s maxf=%d injf=%d obsf=%d W=%04X",
    TAG, MODE, CART, CARTID, NONCE, MAXF, INJF, OBSF, W))
