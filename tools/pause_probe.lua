-- pause_probe.lua — task #39 permanent regression check: the Pocket "floating pill" pause bug.
--
-- DEFECT SIGNATURE this guards against (byte-exact, from the original repro on
-- pocket_human_studycounts.nes md5 01ee0fc6, and the DRSTUDY2P partial-fix run on md5 7eeee398):
--   * P1 preview (OAM slots 37,38) frozen at Y=$45 X=$BE,$C6 -- the 1P-DEFAULT position, which
--     visually reads as "floating" over the wrong side of a 2P board -- instead of the correct
--     2P layout Y=$33 X=$38,$40 (above P1's own board, left side).
--   * P2 preview (OAM slots 39,40) never written at all (Y=$FF) instead of Y=$33 X=$B8,$C0.
--   * STUDY text (OAM slots 32-36) stuck at Y=$0F (overlaps the "1P 2P/LEVEL" header box)
--     instead of the 2P-lifted Y=$08.
--   * Root cause (confirmed 2026-08-02): the copro build ships apply_study_pause(evac=True) --
--     the base-game trampoline's 2P tail parts (part2-5 at $9FF8/$A371/$BE56/$BC26) were never
--     present in ANY copro binary; only part1 ($D2CC, "STUDY" text + P1's 1P-default preview)
--     survives. DRSTUDY2P (driver-side redraw, commit 7f6429a) fixes P2 correctly but a FIRST
--     version left P1's slots (37,38) and the STUDY Y-lift (32-36) still wrong: part1 re-executes
--     EVERY paused frame (not "once at entry" as first assumed) and stomps those specific fields
--     back to its own stale values right after the driver's per-hook write -- the tell is that
--     P2 (which part1 never touches) comes out right while P1/STUDY-Y (which part1 DOES actively
--     write) come out wrong. Fix = shrink part1 to stop writing anything the driver now owns.
--
-- Cart under test is a DRPOCKET+DRHUMAN(+DRSTUDYCOUNTS)(+DRSTUDY2P) build: P1 = human passthrough,
-- P2 = copro AI riding the single $5000 mailbox window (board_src $0500, colors $0381/$0382) --
-- same family as v89_copro_run.lua. Header must be pre-remapped mapper 100->1 (MMC1) via
-- remap_mapper100_mmc1.py so Mesen can boot it; the copro window is emulated by copro_emu.lua.
--
-- ALSO checks the "invisible during play" claim: slots 32-40 must show NO stray sprites a few
-- seconds into normal (unpaused) play -- if a future driver-side fix leaks sprites into live
-- gameplay, this catches it immediately (PRE-PAUSE play block below).
--
-- CFG.dir / CFG.out are passed via DRQA_DIR / DRQA_OUT env vars (falls back to hardcoded
-- paths below if unset). Prints a final VERDICT line per check plus an overall PASS/FAIL.

local DIR = (os and os.getenv and os.getenv("DRQA_DIR")) or "/home/struktured/projects/dr-mario-qa-wt/tools/"
local OUT = (os and os.getenv and os.getenv("DRQA_OUT")) or "/home/struktured/projects/dr-mario-qa-wt/experiments/freeze_20260801/pause_probe/"
if DIR:sub(-1) ~= "/" then DIR = DIR .. "/" end
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end

local lf = io.open(OUT .. "pause_probe.log", "w")
local function logf(s) if lf then lf:write(s .. "\n"); lf:flush() end end

local NES = emu.memType.nesMemory
local OAM = emu.memType.nesSpriteRam
local function rd(a) return emu.read(a, NES, false) end
local function oam(slot, k) return emu.read(slot * 4 + k, OAM, false) end
local function bcd(b) return ((b >> 4) & 0x0F) * 10 + (b & 0x0F) end

local results = {}   -- name -> true/false, filled in by the check_* functions

local function snap(name)
  local ok, err = pcall(function() emu.takeScreenshot() end)
  logf("screenshot(" .. name .. "): " .. (ok and "taken (Mesen default folder)" or ("FAILED: " .. tostring(err))))
end

local EMU = dofile(DIR .. "copro_emu.lua")
if not EMU then logf("FATAL: copro_emu.lua nil (DRQA_DIR=" .. DIR .. ")"); pcall(function() emu.stop(1) end); return end
local s = EMU.attach{ window = 0x5000, board_src = 0x0500, colA = 0x0381, colB = 0x0382, latency = 24 }
logf("copro_emu attached window=$5000 board_src=$0500 (DRPOCKET single-window; P1=human, P2=copro)")

local frame = 0
local cur = nil
local untl = -1
-- IMPORTANT: only call emu.setInput when we are actively injecting a press (matches the
-- proven v89_copro_run.lua pattern). The cart's own autonav writes fake P1 presses directly
-- into $F5 each frame to self-navigate the menu; calling emu.setInput({},0) UNCONDITIONALLY
-- every frame races that and stomps it back to "nothing pressed" (confirmed: caused a hang,
-- never reached PLAY in 2600 frames on the first version of this script).
emu.addEventCallback(function() if cur and frame < untl then emu.setInput(cur, 0) end end, emu.eventType.inputPolled)
local function press(i, d) cur = i; untl = frame + (d or 4) end

local function dump_oam(tag, lo, hi)
  local t = { tag .. ":" }
  for slot = lo, hi do
    t[#t + 1] = string.format("  slot%-3d Y=$%02X(%3d) tile=$%02X attr=$%02X X=$%02X(%3d)",
      slot, oam(slot, 0), oam(slot, 0), oam(slot, 1), oam(slot, 2), oam(slot, 3), oam(slot, 3))
  end
  logf(table.concat(t, "\n"))
end

local function check_counts(tag)
  local vc1, vc2 = rd(0x0324), rd(0x03A4)
  local shownV1 = oam(12, 1) * 10 + oam(13, 1)
  local shownV2 = oam(14, 1) * 10 + oam(15, 1)
  local blankV = (oam(12,0)==0xFF and oam(13,0)==0xFF and oam(14,0)==0xFF and oam(15,0)==0xFF)
  logf(string.format("[%s] virus counts: raw $0324=$%02X(BCD %d) $03A4=$%02X(BCD %d)  rendered P1=%d P2=%d  slots8-15 blank=%s",
    tag, vc1, bcd(vc1), vc2, bcd(vc2), shownV1, shownV2, tostring(blankV)))
  dump_oam(tag .. " slots 8-15 (counts)", 8, 15)
  if tag == "PAUSED" then
    local ok = not blankV and shownV1 == bcd(vc1) and shownV2 == bcd(vc2)
    results["PAUSED: virus counts present+correct"] = ok
    logf("VERDICT [" .. (ok and "PASS" or "FAIL") .. "] PAUSED virus counts present+correct")
  end
end

local function check_previews(tag)
  local np = rd(0x0727)
  local p1y1, p1y2 = oam(37,0), oam(38,0)
  local p1x1, p1x2 = oam(37,3), oam(38,3)
  local p2y1, p2y2 = oam(39,0), oam(40,0)
  local p2x1, p2x2 = oam(39,3), oam(40,3)
  local p2_present = not (p2y1 == 0xFF and p2y2 == 0xFF)
  local p1_is_2p_pos = (p1y1 == 0x33 and p1y2 == 0x33 and p1x1 == 0x38 and p1x2 == 0x40)
  local p1_is_1p_pos = (p1x1 == 0xBE and p1x2 == 0xC6)
  local p2_is_2p_pos = (p2y1 == 0x33 and p2y2 == 0x33 and p2x1 == 0xB8 and p2x2 == 0xC0)
  local studyY = { oam(32,0), oam(33,0), oam(34,0), oam(35,0), oam(36,0) }
  local studyLifted = (studyY[1]==0x08 and studyY[2]==0x08 and studyY[3]==0x08 and studyY[4]==0x08 and studyY[5]==0x08)
  logf(string.format("[%s] $0727=%d $04=%d $0046=%d", tag, np, rd(0x04), rd(0x46)))
  logf(string.format("[%s] P1 preview (37,38): Y=$%02X,$%02X X=$%02X,$%02X  -> %s",
    tag, p1y1, p1y2, p1x1, p1x2,
    p1_is_2p_pos and "2P-CORRECT (above P1/left board)" or (p1_is_1p_pos and "*** 1P-DEFAULT POSITION (floating bug signature) ***" or "UNKNOWN position")))
  logf(string.format("[%s] P2 preview (39,40): Y=$%02X,$%02X X=$%02X,$%02X  -> %s",
    tag, p2y1, p2y2, p2x1, p2x2, p2_present and (p2_is_2p_pos and "2P-CORRECT" or "present but wrong position") or "*** ABSENT (Y=$FF, never written) ***"))
  logf(string.format("[%s] STUDY text Y (32-36) = %02X %02X %02X %02X %02X  (want $08 in 2P/VS, $0F in 1P)",
    tag, studyY[1], studyY[2], studyY[3], studyY[4], studyY[5]))
  dump_oam(tag .. " slots 32-40 (STUDY+previews)", 32, 40)
  dump_oam(tag .. " slots 0-3 (capsules)", 0, 3)
  if tag == "PAUSED" then
    results["PAUSED: P1 preview 2P-correct"] = p1_is_2p_pos
    results["PAUSED: P2 preview 2P-correct"] = p2_is_2p_pos
    results["PAUSED: STUDY text Y-lifted to $08"] = studyLifted
    logf("VERDICT [" .. (p1_is_2p_pos and "PASS" or "FAIL") .. "] PAUSED P1 preview 2P-correct")
    logf("VERDICT [" .. (p2_is_2p_pos and "PASS" or "FAIL") .. "] PAUSED P2 preview 2P-correct")
    logf("VERDICT [" .. (studyLifted and "PASS" or "FAIL") .. "] PAUSED STUDY text Y-lifted to $08")
  elseif tag == "PRE-PAUSE play" then
    local allBlank = true
    for slot = 32, 40 do if oam(slot, 0) ~= 0xFF then allBlank = false end end
    results["PRE-PAUSE play: slots 32-40 invisible (no leak into gameplay)"] = allBlank
    logf("VERDICT [" .. (allBlank and "PASS" or "FAIL") .. "] PRE-PAUSE play slots 32-40 invisible (no leak into gameplay)")
  end
end

-- ATTEMPT 1 (no injected input) hung at mode=$00 forever with $0727=2 $04=1 armed within
-- ~60 frames -- the autonav on a DRHUMAN cart only sets the 2P/VS-CPU TOGGLE state, it does
-- NOT self-press START (that is deliberately left to the real human/player on a "human
-- challenge" cart). So we must drive START ourselves, like a human would, through title +
-- any level-select screens, until PLAY (mode==4) is reached.
local lastMode = -1
local nextNavPress = 60
local firstPlay, pauseFrame, resumedFrame, done = nil, nil, nil, false
emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  if mode ~= lastMode then
    logf(string.format("MODE CHANGE f%-4d: $%02X -> $%02X  $0727=%d $04=%d $0316=%d",
      frame, lastMode, mode, rd(0x0727), rd(0x04), rd(0x0316)))
    lastMode = mode
  end
  if not firstPlay and frame % 60 == 0 then
    logf(string.format("heartbeat f%-4d mode=$%02X $0727=%d $04=%d $0316=%d", frame, mode, rd(0x0727), rd(0x04), rd(0x0316)))
  end
  -- nav: press START every ~40 frames (held 6f) until PLAY, since DRHUMAN leaves START to us
  if not firstPlay and frame >= nextNavPress and (not cur or frame >= untl) then
    press({ start = true }, 6)
    nextNavPress = frame + 40
  end
  if mode == 4 and not firstPlay then
    firstPlay = frame
    logf(string.format("PLAY reached at f%d  $0727=%d $04=%d", frame, rd(0x0727), rd(0x04)))
  end
  if firstPlay and frame == firstPlay + 60 then
    check_counts("PRE-PAUSE play")
    check_previews("PRE-PAUSE play")
  end
  if firstPlay and frame == firstPlay + 300 and not pauseFrame then
    snap("before_pause")
    press({ start = true }, 6)
    pauseFrame = frame
    logf("injected START (enter STUDY pause) at f" .. frame)
  end
  if pauseFrame and frame == pauseFrame + 50 and not done then
    done = true
    snap("at_pause")
    logf("=== PAUSED STATE (f" .. frame .. ") ===")
    check_counts("PAUSED")
    check_previews("PAUSED")
    press({ start = true }, 6)
    resumedFrame = frame
    logf("injected START (resume) at f" .. frame)
  end
  if resumedFrame and frame == resumedFrame + 30 then
    snap("after_resume")
    local resumedClean = (rd(0x46) == 4)
    results["resume returns to PLAY (mode=4)"] = resumedClean
    logf(string.format("resume check: mode=%d (want 4=play) GO=%d DONE=%d", rd(0x46), s.goes, s.dones))
    logf("VERDICT [" .. (resumedClean and "PASS" or "FAIL") .. "] resume returns to PLAY (mode=4)")
    local overall = true
    local order = {
      "PRE-PAUSE play: slots 32-40 invisible (no leak into gameplay)",
      "PAUSED: virus counts present+correct",
      "PAUSED: P1 preview 2P-correct",
      "PAUSED: P2 preview 2P-correct",
      "PAUSED: STUDY text Y-lifted to $08",
      "resume returns to PLAY (mode=4)",
    }
    logf("=== SUMMARY ===")
    for _, k in ipairs(order) do
      local v = results[k]
      if v == nil then overall = false; logf("  [MISSING] " .. k)
      else
        if not v then overall = false end
        logf("  [" .. (v and "PASS" or "FAIL") .. "] " .. k)
      end
    end
    logf("OVERALL: " .. (overall and "PASS" or "FAIL"))
    logf("DONE")
    if lf then lf:close(); lf = nil end
    pcall(function() emu.stop(0) end)
  end
  if frame >= 4200 then
    logf("TIMEOUT: no play/pause reached (firstPlay=" .. tostring(firstPlay) .. " pauseFrame=" .. tostring(pauseFrame) .. ")")
    logf("OVERALL: FAIL (timeout)")
    if lf then lf:close(); lf = nil end
    pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
logf("pause_probe loaded; DIR=" .. DIR .. " OUT=" .. OUT)
