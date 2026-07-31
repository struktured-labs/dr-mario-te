-- ============================================================================
-- study_viruscount_probe.lua — WHY do the VIRUS counts vanish when STUDY pauses?
--
-- User report 2026-07-28: "when I press pause for study the virus counts disappear —
-- ideally stays too."
--
-- Our STUDY hack keeps the playfield visible during pause by disabling the vanilla OAM
-- clear in three places (STUDY_EDITS) and then drawing "STUDY" into OAM slots 32-36 plus
-- the previews into 37-40. If the virus counter is drawn by a routine that vanilla skips
-- while paused — or if it lives in sprites our hack overwrites/stops refreshing — it
-- disappears. This probe finds out WHICH, by diffing full OAM + the counter RAM across
-- the play->pause transition instead of guessing.
--
-- Dumps, for PLAY and then for STUDY:
--   * all 64 OAM slots (Y/tile/attr/X), so we can see exactly which sprites stop being drawn
--   * the virus-count RAM ($0324 P1 / $03A4 P2) — proves whether the VALUE is lost or just
--     the DISPLAY
-- Then prints the slots that changed, which is the answer.
--
-- Launch: DRQA_OUT=<dir> Mesen <cart.nes> study_viruscount_probe.lua --donotsavesettings
-- ============================================================================
local OUT = (os and os.getenv and os.getenv("DRQA_OUT")) or "/tmp/"
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local lf = io.open(OUT .. "study_viruscount.log", "w")
local function logf(s) if lf then lf:write(s .. "\n"); lf:flush() end end

local NES = emu.memType.nesMemory
local OAM = emu.memType.nesSpriteRam
local function rd(a) return emu.read(a, NES, false) end
local function oam(i, k) return emu.read(i * 4 + k, OAM, false) end

local VCOUNT_P1, VCOUNT_P2 = 0x0324, 0x03A4

local frame, phase, pause_at = 0, "nav", nil
local cur_input = {}
local snap_play, snap_study = nil, nil

-- title picks 1P/2P VERTICALLY -> DOWN before the first START (see standalone_study_qa.lua)
local function nav_input(f)
  if f >= 120 and f < 150 then return { down = true }
  elseif f >= 180 and f < 210 then return { start = true }
  elseif f >= 240 and f < 330 then if (f % 10) < 5 then return { up = true } end
  elseif f >= 380 and f < 410 then return { start = true }
  end
  return {}
end

local function snapshot()
  local s = { oam = {}, sh = {}, vp1 = rd(VCOUNT_P1), vp2 = rd(VCOUNT_P2) }
  -- SHADOW OAM ($0200-$02FF) for slots 8..15: tells us whether the game BLANKS the tiles
  -- or merely hides the sprite by moving Y offscreen. If tiles survive, the fix is a
  -- 4-byte-per-sprite Y rewrite; if not, we must rebuild the digits from the count.
  for i = 8, 15 do
    s.sh[i] = { rd(0x0200 + i*4), rd(0x0201 + i*4), rd(0x0202 + i*4), rd(0x0203 + i*4) }
  end
  for i = 0, 63 do
    s.oam[i] = { oam(i, 0), oam(i, 1), oam(i, 2), oam(i, 3) }
  end
  return s
end

local function dump(tag, s)
  logf(string.format("%s: virus P1=%d P2=%d", tag, s.vp1, s.vp2))
  local live = {}
  for i = 0, 63 do
    local o = s.oam[i]
    if o[1] ~= 0xFF and o[1] ~= 0x00 then
      live[#live + 1] = string.format("s%02d(Y%02X,T%02X,X%02X)", i, o[1], o[2], o[4])
    end
  end
  logf("  live sprites (" .. #live .. "): " .. table.concat(live, " "))
  local sh = {}
  for i = 8, 15 do
    local o = s.sh[i]
    sh[#sh+1] = string.format("s%02d[Y%02X T%02X A%02X X%02X]", i, o[1], o[2], o[3], o[4])
  end
  logf("  SHADOW $0200 slots 8-15: " .. table.concat(sh, " "))
end

local function tick()
  frame = frame + 1
  if phase == "nav" then
    cur_input = nav_input(frame)
    if rd(0x0046) == 0x04 and frame > 410 then
      pause_at = frame + 150          -- let a few capsules land so counts are interesting
      phase = "play"
    elseif frame > 900 then
      logf("NAV FAILED"); if lf then lf:close() end; emu.stop(1)
    end

  elseif phase == "play" then
    if frame == pause_at - 1 then
      snap_play = snapshot(); dump("PLAY ", snap_play)
    elseif frame >= pause_at and frame < pause_at + 30 then
      cur_input = { start = true }    -- pause -> STUDY
    elseif frame >= pause_at + 30 then
      cur_input = {}
      if frame >= pause_at + 120 then
        snap_study = snapshot(); dump("STUDY", snap_study)
        logf("\n=== WHAT CHANGED play -> STUDY ===")
        local gone, appeared, moved = {}, {}, {}
        for i = 0, 63 do
          local a, b = snap_play.oam[i], snap_study.oam[i]
          local a_live = a[1] ~= 0xFF and a[1] ~= 0x00
          local b_live = b[1] ~= 0xFF and b[1] ~= 0x00
          if a_live and not b_live then
            gone[#gone + 1] = string.format("s%02d(was Y%02X T%02X X%02X)", i, a[1], a[2], a[4])
          elseif b_live and not a_live then
            appeared[#appeared + 1] = string.format("s%02d(Y%02X T%02X X%02X)", i, b[1], b[2], b[4])
          elseif a_live and b_live and (a[1] ~= b[1] or a[2] ~= b[2] or a[4] ~= b[4]) then
            moved[#moved + 1] = string.format("s%02d(%02X/%02X/%02X -> %02X/%02X/%02X)",
              i, a[1], a[2], a[4], b[1], b[2], b[4])
          end
        end
        logf("  DISAPPEARED (" .. #gone .. "): " .. table.concat(gone, " "))
        logf("  APPEARED    (" .. #appeared .. "): " .. table.concat(appeared, " "))
        logf("  MOVED       (" .. #moved .. "): " .. table.concat(moved, " "))
        logf(string.format("\n  virus RAM preserved across pause? P1 %d->%d  P2 %d->%d  => %s",
          snap_play.vp1, snap_study.vp1, snap_play.vp2, snap_study.vp2,
          (snap_play.vp1 == snap_study.vp1 and snap_play.vp2 == snap_study.vp2)
            and "YES (value intact — it is a DISPLAY problem, redrawable)"
            or "NO (value itself changed — investigate before redrawing)"))
        pcall(function() emu.takeScreenshot() end)
        if lf then lf:close() end
        emu.stop(0)
      end
    end
  end
end

emu.addEventCallback(function()
  pcall(function() emu.setInput(cur_input, 0) end)
end, emu.eventType.inputPolled)

local died = false
emu.addEventCallback(function()
  if died then return end
  local ok, err = pcall(tick)
  if not ok then
    died = true; logf("LUA ERROR f" .. frame .. ": " .. tostring(err))
    if lf then lf:close() end; emu.stop(1)
  end
end, emu.eventType.endFrame)

logf("study_viruscount_probe started")
