-- ============================================================================
-- release_shots.lua -- capture the screenshots a romhacking.net submission needs.
--
-- ★ DOES NOT USE emu.takeScreenshot(). That call returns success in this build and writes
-- NOTHING, anywhere -- verified by searching the whole filesystem for new PNGs after a run
-- in which all four shots reported "taken". (An earlier guess that --donotsavesettings
-- caused it was wrong; the flag is irrelevant.) Instead we pull the framebuffer with
-- emu.getScreenBuffer() and write raw pixels, which the caller converts to PNG. Nothing
-- depends on Mesen's own file I/O.
--
-- Nav is REUSED from standalone_study_qa.lua, which is the proven sequence:
--   * the title picks 1PLAYER/2PLAYER VERTICALLY, so DOWN must land BEFORE the first START
--     (pressing START first silently plays 1P);
--   * ★ level select moves with LEFT/RIGHT, not UP/DOWN -- the old UP presses left every
--     run sitting at level 0, which is a near-empty bottle and a poor release shot.
--   * inputs go on `inputPolled`; at endFrame the ROM has already latched the pad.
-- ============================================================================
local OUT = (os and os.getenv and os.getenv("DRQA_OUT")) or "/tmp/"
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local lf = io.open(OUT .. "release_shots.log", "w")
local function logf(s) if lf then lf:write(s .. "\n"); lf:flush() end end

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end

local frame, shots, paused_at = 0, 0, nil
local cur_input = {}

local function nav_input(f)
  if f >= 120 and f < 150 then return { down = true }        -- title: 1PLAYER -> 2PLAYER
  elseif f >= 180 and f < 210 then return { start = true }
  elseif f >= 240 and f < 400 then
    if (f % 12) < 4 then return { right = true } end          -- level select: RIGHT raises it
  elseif f >= 430 and f < 460 then return { start = true }
  end
  return {}
end

local function snap(name)
  local buf = emu.getScreenBuffer()
  local w, h = 256, 240
  local ok, sz = pcall(function() return emu.getScreenSize() end)
  if ok and type(sz) == "table" and sz.width then w, h = sz.width, sz.height end
  local f = io.open(OUT .. name .. ".raw", "wb")
  local t = {}
  for i = 1, #buf do
    local p = buf[i]
    t[#t + 1] = string.char((p >> 16) & 0xFF, (p >> 8) & 0xFF, p & 0xFF)  -- ARGB -> RGB
    if #t >= 4096 then f:write(table.concat(t)); t = {} end
  end
  f:write(table.concat(t)); f:close()
  shots = shots + 1
  logf(string.format("shot %d %-12s frame %5d  %dx%d  px=%d", shots, name, frame, w, h, #buf))
end

emu.addEventCallback(function() emu.setInput(cur_input, 0) end, emu.eventType.inputPolled)

emu.addEventCallback(function()
  frame = frame + 1
  local mode, np = rd(0x0046), rd(0x0727)
  if frame == 90 then snap("01_title") end
  cur_input = nav_input(frame)
  if frame == 415 then snap("02_level_select") end
  if mode == 0x04 and np == 2 and frame == 900 then snap("03_midgame_2p") end
  if mode == 0x04 and np == 2 and frame >= 960 and frame < 990 then
    cur_input = { start = true }
    paused_at = paused_at or frame
  end
  if paused_at and frame == paused_at + 70 then snap("04_study_2p") end
  if frame == 1120 then
    logf(string.format("done: mode=%d players=%d level=%d virus=%d shots=%d",
                       mode, np, rd(0x0316), rd(0x0324), shots))
    emu.stop(0)
  end
end, emu.eventType.endFrame)

logf("release_shots started")
