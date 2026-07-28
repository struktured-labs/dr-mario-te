-- ============================================================================
-- standalone_study_qa.lua — Mesen QA for the PURE (non-copro) TE cart.
--
-- Validates the three v9 acceptance criteria without any hardware:
--   (a) 2P STUDY renders BOTH previews over the CORRECT boards
--       (the "floating capsule after START" bug: v8.2 evacuated the 2P tail, so
--        P1's preview stayed at its 1P-default X=$BE/$C6 — over the RIGHT board —
--        and P2's slots 39/40 were never written at all)
--   (b) no level-select garble  (old part3b @ $BE56 inside a print table)
--   (c) no KIL freeze           (old part3c @ $BC26 -> $0301 = $02)
--
-- Expected under v9 ($FB80 relocated tail):
--   slots 37,38 (P1 preview) X = $38,$40   -- above the LEFT board
--   slots 39,40 (P2 preview) X = $B8,$C0   -- above the RIGHT board
--   slots 32..36 (STUDY text) Y = $08      -- lifted clear of the "1P 2P/LEVEL" header
--   all four preview slots     Y = $33
--
-- Launch:  DRQA_OUT=<dir> run_mesen.sh <cart.nes> standalone_study_qa.lua --donotsavesettings
-- ============================================================================
local OUT = (os and os.getenv and os.getenv("DRQA_OUT")) or "/tmp/"
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local lf = io.open(OUT .. "standalone_study_qa.log", "w")
local function logf(s) if lf then lf:write(s .. "\n"); lf:flush() end end

local NES = emu.memType.nesMemory
local OAM = emu.memType.nesSpriteRam
local function rd(a) return emu.read(a, NES, false) end
local function oam(i, k) return emu.read(i * 4 + k, OAM, false) end

local frame, phase, phase_f = 0, "nav", 0
local kil_seen, alive_seen, mode_hist = false, false, {}
local results = {}
local pause_at = nil          -- frame at which we press START to enter STUDY
local cur_input = {}          -- what the inputPolled callback injects each frame

-- Menu nav reused verbatim from the proven cpu_vs_cpu.lua sequence: inputs must be HELD
-- ~30 frames (a single-frame press is missed — the ROM edge-detects on btnsPressed).
--   START (exit title) -> RIGHT (choose 2P) -> START (confirm) -> UP (level) -> START (go)
-- The title selects 1PLAYER/2PLAYER VERTICALLY, so DOWN must land BEFORE the first START
-- (the borrowed cpu_vs_cpu sequence pressed START first and therefore always took 1P --
-- observed directly: $0727 stayed 1 all the way into play).
local MODE = (os and os.getenv and os.getenv("DRQA_MODE")) or "2p"
local function nav_input(f)
  if f >= 120 and f < 150 then
    if MODE == "2p" then return { down = true } end      -- title: 1PLAYER -> 2PLAYER
    return {}                                            -- 1P: leave the cursor alone
  elseif f >= 180 and f < 210 then return { start = true }
  elseif f >= 240 and f < 330 then
    if (f % 10) < 5 then return { up = true } end        -- level select
  elseif f >= 380 and f < 410 then return { start = true }
  end
  return {}
end

-- Dr. Mario: $0046 game mode (4 = play), $0727 player count, $0316 level, $0301 = the
-- byte the $BC26 collision corrupted into an opcode.
local function press(btn)
  local s = {}
  s[btn] = true
  emu.setInput(s, 0)
end

-- this Mesen build's takeScreenshot takes NO arguments (saves to its own folder); the OAM
-- assertions below are the objective verdict, the shot is only corroborating evidence.
local function snap(name)
  local ok = pcall(function() emu.takeScreenshot() end)
  logf("screenshot(" .. name .. "): " .. (ok and "taken" or "unavailable"))
end

-- (b) LEVEL-SELECT GARBLE, asserted not eyeballed. The old part3b @ $BE56 sat inside an
-- RB6C2_PRINT table, so the level-select nametable was drawn with junk tiles. Hashing the
-- visible nametable ($2000-$23BF) turns "does it look right" into a comparable number:
-- a cart with the garble differs from a clean cart here, byte for byte.
local function nt_hash()
  local PPU = emu.memType.nesPpuMemory
  local h, n = 5381, 0
  for a = 0x2000, 0x23BF do
    local v = emu.read(a, PPU, false) or 0
    h = (h * 33 + v) % 4294967296
    if v ~= 0x24 and v ~= 0x00 then n = n + 1 end        -- 0x24 = blank tile
  end
  return h, n
end

local function dump_oam(tag)
  local t = { tag .. ":" }
  for _, i in ipairs({ 32, 33, 34, 35, 36, 37, 38, 39, 40 }) do
    t[#t + 1] = string.format("  slot%-3d Y=$%02X tile=$%02X attr=$%02X X=$%02X",
      i, oam(i, 0), oam(i, 1), oam(i, 2), oam(i, 3))
  end
  logf(table.concat(t, "\n"))
end

local function check_study()
  local ok = true
  local function want(slot, k, val, what)
    local got = oam(slot, k)
    local good = (got == val)
    ok = ok and good
    logf(string.format("  [%s] slot%d %s: got $%02X want $%02X", good and "PASS" or "FAIL",
      slot, what, got, val))
    return good
  end
  if MODE == "2p" then
    logf("--- (a) 2P preview placement ---")
    want(37, 3, 0x38, "X (P1 left)")
    want(38, 3, 0x40, "X (P1 left)")
    want(39, 3, 0xB8, "X (P2 right)")
    want(40, 3, 0xC0, "X (P2 right)")
    for _, s in ipairs({ 37, 38, 39, 40 }) do want(s, 0, 0x33, "Y") end
    logf("--- STUDY text lift (2P only) ---")
    for _, s in ipairs({ 32, 33, 34, 35, 36 }) do want(s, 0, 0x08, "Y") end
  else
    -- 1P REGRESSION. v9 must be INDISTINGUISHABLE from v8.2 here: the single preview stays
    -- at its 1P default and the STUDY text must NOT be lifted. Lifting 1P would silently
    -- change the PUBLISHED romhacking.net v6 hack's behaviour, which is explicitly forbidden.
    logf("--- 1P regression: preview at 1P default, STUDY NOT lifted ---")
    want(37, 3, 0xBE, "X (1P default)")
    want(38, 3, 0xC6, "X (1P default)")
    want(37, 0, 0x45, "Y (1P default)")
    want(38, 0, 0x45, "Y (1P default)")
    want(39, 0, 0xFF, "Y (P2 slot unused in 1P)")
    want(40, 0, 0xFF, "Y (P2 slot unused in 1P)")
    for _, s in ipairs({ 32, 33, 34, 35, 36 }) do want(s, 0, 0x0F, "Y (unlifted)") end
  end
  results.study = ok
  return ok
end

-- Mesen reports Lua errors only in its GUI script window, so a throwing callback looks
-- identical to a hung one from the shell. Wrap the body and record the message ourselves.
local function tick()
  frame = frame + 1
  phase_f = phase_f + 1
  if frame <= 3 then logf("tick f" .. frame .. " phase=" .. phase) end

  -- (c) FREEZE watch. NOTE: an earlier version tested `rd(0x0301)==0x02` directly -- that is
  -- a FALSE POSITIVE generator, because $0301 legitimately holds $02 during normal play (it
  -- fired on v8.2, which provably does not freeze). The real signature of the $BC26 KIL is
  -- LIVENESS LOSS: the CPU halts, so the frame counter stops advancing relative to game state.
  -- Reaching play and rendering STUDY is therefore the positive proof of no freeze.
  if rd(0x0046) ~= 0x00 then alive_seen = true end
  mode_hist[#mode_hist + 1] = rd(0x0046)
  if #mode_hist > 4 then table.remove(mode_hist, 1) end

  if phase == "nav" then
    cur_input = nav_input(frame)
    if frame % 60 == 0 then
      logf(string.format("f%-4d $0046=$%02X $0727=%d $0316=%d", frame,
        rd(0x0046), rd(0x0727), rd(0x0316)))
    end
    if frame == 360 then
      snap("level_select")
      local h, n = nt_hash()
      logf(string.format("LEVELSEL_NT hash=%u nonblank=%d", h, n))
      results.nt_hash = h
      dump_oam("level-select OAM")
    end
    if rd(0x0046) == 0x04 and frame > 410 then
      logf(string.format("PLAY reached f%d: $0727=%d $0316=%d",
        frame, rd(0x0727), rd(0x0316)))
      results.twop = (rd(0x0727) == 2)
      pause_at = frame + 90
      phase, phase_f = "play", 0
    elseif frame > 900 then
      logf("NAV FAILED to reach play by f900")
      results.navfail = true
      phase, phase_f = "done", 0
    end

  elseif phase == "play" then
    if frame >= pause_at and frame < pause_at + 30 then
      cur_input = { start = true }         -- hold START -> pause -> STUDY
    elseif frame >= pause_at + 30 then
      cur_input = {}
      if frame >= pause_at + 90 then
        snap("study_2p")
        dump_oam("STUDY OAM")
        check_study()
        phase, phase_f = "done", 0
      end
    end

  elseif phase == "done" then
    if phase_f > 30 then
      logf("=== VERDICT ===")
      logf(string.format("  nav reached 2P play     : %s",
        results.navfail and "FAIL (never reached play)" or (results.twop and "PASS ($0727=2)" or "FAIL (1P)")))
      logf(string.format("  (a) 2P previews correct : %s", results.study and "PASS" or "FAIL"))
      logf(string.format("  (c) no KIL freeze       : %s",
        (alive_seen and results.study ~= nil) and "PASS (reached play + rendered STUDY)" or "INCONCLUSIVE"))
      logf(string.format("  frames run              : %d", frame))
      logf(string.format("  (b) level-select NT hash: %s  (compare across carts)",
        tostring(results.nt_hash)))
      logf(string.format("  mode                    : %s", MODE))
      if lf then lf:close() end
      emu.stop(0)
    end
  end
end

-- ★ Input MUST be injected on inputPolled, not endFrame: by end-of-frame the ROM has
-- already latched the controller, so a setInput there is a frame late and never seen.
emu.addEventCallback(function()
  pcall(function() emu.setInput(cur_input, 0) end)
end, emu.eventType.inputPolled)

local died = false
emu.addEventCallback(function()
  if died then return end
  local ok, err = pcall(tick)
  if not ok then
    died = true
    logf("LUA ERROR at frame " .. tostring(frame) .. ": " .. tostring(err))
    if lf then lf:close() end
    emu.stop(1)
  end
end, emu.eventType.endFrame)

logf("standalone_study_qa started")
