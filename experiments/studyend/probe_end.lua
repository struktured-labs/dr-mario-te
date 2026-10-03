-- probe_end.lua: measure the 2P round-end screen (X-sign virus + lower-field blank) and the
-- mid-game STUDY pause on a DRHUMAN couch cart (remapped to MMC1), P2 seat served by copro_emu.
-- Run via experiments/studyend/run_probe.sh (remaps the cart to MMC1, private Mesen home, TestRunner).
-- env: SE_OUT=<dir/> (required)  SE_TAG=<tag>  SE_EMU=<path to tools/copro_emu.lua>  SE_HOLD=<frames>
-- P1 is idle during play (tops out); START is pressed only for nav, the study pause/resume,
-- and to leave each end screen. Exits via emu.stop(0) after the 3rd (final) round's end screen.
local OUT = assert(os.getenv("SE_OUT"), "set SE_OUT")
local TAG = os.getenv("SE_TAG") or "x"
local HOLD = tonumber(os.getenv("SE_HOLD") or "1500")      -- frames to sit on the round-1 end screen
local NES, OAM = emu.memType.nesMemory, emu.memType.nesSpriteRam
local PPU, PRG = emu.memType.nesPpuMemory, emu.memType.nesPrgRom
local lf = io.open(OUT .. TAG .. "_probe.log", "w")
local hf = io.open(OUT .. TAG .. "_ramhash.txt", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end
local function rd(a) return emu.read(a, NES, false) end
local function shot(n)
  local ok, p = pcall(emu.takeScreenshot)
  if ok then local f = io.open(OUT .. TAG .. "_" .. n .. ".png", "wb"); f:write(p); f:close() end
  logf("SHOT " .. n .. " ok=" .. tostring(ok))
end
local EMU = dofile(assert(os.getenv("SE_EMU"), "set SE_EMU"))
local cs = EMU.attach{ window = 0x5200, board_src = 0x0500, colA = 0x0381, colB = 0x0382, latency = 24 }

-- exec counters keyed on unit-0 PRG-ROM offsets (cpu - $8000), so the driver bank cannot alias them
local EX = {
  anyPlayerLoses = 0x1532, jsrEmpty_P1 = 0x154F, jsrEmpty_P2 = 0x1579, emptyLower = 0x16C0,
  emptyLowerTail = 0x16CF, whoFailedChk = 0x088C, redVirusBody = 0x0890, endNonFinal = 0x1646,
  finalWipe = 0x15CE, pauseLoop = 0x17C7, studyHB_u0 = 0x52CC, studyHB_u1 = 0xD2CC,
}
local cnt = {}
for k, off in pairs(EX) do
  cnt[k] = 0
  emu.addMemoryCallback(function() cnt[k] = cnt[k] + 1 end, emu.callbackType.exec, off, off, emu.cpuType.nes, PRG)
end
-- writes of $FF into the LOWER half (rows 8-15) of each field, by game phase (plain-Lua only)
local phase = "nav"
local ffw = {}
local function bump(key) ffw[key] = (ffw[key] or 0) + 1 end
emu.addMemoryCallback(function(a, v) if v == 0xFF then bump("P1lower@" .. phase) end end, emu.callbackType.write, 0x0440, 0x047F)
emu.addMemoryCallback(function(a, v) if v == 0xFF then bump("P2lower@" .. phase) end end, emu.callbackType.write, 0x0540, 0x057F)

local function counters(tag)
  local ks = {}
  for k in pairs(cnt) do ks[#ks + 1] = k end
  table.sort(ks)
  local parts = {}
  for _, k in ipairs(ks) do parts[#parts + 1] = k .. "=" .. cnt[k] end
  logf("  [" .. tag .. "] EXEC " .. table.concat(parts, " "))
  local fk = {}
  for k in pairs(ffw) do fk[#fk + 1] = k end
  table.sort(fk)
  local fp = {}
  for _, k in ipairs(fk) do fp[#fp + 1] = k .. "=" .. ffw[k] end
  logf("  [" .. tag .. "] FFWRITES " .. table.concat(fp, " "))
end
local function vars(tag)
  logf(string.format("  [%s] mode=%d enablePause$54=%d whoWon$55=%d whoFailed$61=%d vict P1/P2=%d/%d virus P1/P2=%02X/%02X pills P1/P2=%d/%d pillY P1/P2=%d/%d f$43=%d copro goes=%d dones=%d",
    tag, rd(0x46), rd(0x54), rd(0x55), rd(0x61), rd(0x031E), rd(0x039E), rd(0x0324), rd(0x03A4),
    rd(0x0327), rd(0x03A7), rd(0x0306), rd(0x0386), rd(0x43), cs.goes, cs.dones))
end
local function hexrow(base, n, mt)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02X", emu.read(base + i, mt, false)) end
  return table.concat(t)
end
local function dump(tag)
  local f = io.open(OUT .. TAG .. "_" .. tag .. "_dump.txt", "w")
  for r = 0, 15 do f:write(string.format("P1field r%02d %s\n", r, hexrow(0x0400 + r * 8, 8, NES))) end
  for r = 0, 15 do f:write(string.format("P2field r%02d %s\n", r, hexrow(0x0500 + r * 8, 8, NES))) end
  for s = 0, 63 do
    local b = s * 4
    f:write(string.format("OAM %02d Y=%3d tile=%02X attr=%02X X=%3d\n", s,
      emu.read(b, OAM, false), emu.read(b + 1, OAM, false), emu.read(b + 2, OAM, false), emu.read(b + 3, OAM, false)))
  end
  for r = 0, 29 do f:write(string.format("NT r%02d %s\n", r, hexrow(0x2000 + r * 32, 32, PPU))) end
  f:close()
  logf("DUMP " .. tag)
end
local function ramhash()
  local h = 0
  for a = 0x0000, 0x07FF do h = (h * 31 + rd(a)) % 2147483647 end
  local g = 0
  for a = 0x6100, 0x61FF do g = (g * 31 + rd(a)) % 2147483647 end
  return h, g
end

local frame, cur, untl = 0, nil, -1
emu.addEventCallback(function() if cur and frame < untl then emu.setInput(cur, 0) end end, emu.eventType.inputPolled)
local function press(i, d) cur = i; untl = frame + (d or 4) end

local st = "nav"; local navN = 0; local t0 = 0; local round = 0; local lastMode = -1
local pauseY1, pauseY2, pausePills
emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  if mode ~= lastMode then logf(string.format("MODE f=%d %d->%d (st=%s)", frame, lastMode, mode, st)); lastMode = mode end
  if round <= 1 then local h, g = ramhash(); hf:write(string.format("%d %d %d %d\n", frame, mode, h, g)) end
  -- P1 is never driven during play: any P1 input seen in mode 4 outside our presses is phantom
  if mode == 4 and not (cur and frame < untl + 2) and (rd(0xF5) ~= 0 or rd(0xF7) ~= 0) then
    logf(string.format("PHANTOM f=%d round=%d st=%s F5=%02X F7=%02X", frame, round, st, rd(0xF5), rd(0xF7)))
  end
  if st == "nav" then
    if mode ~= 4 and frame % 40 == 0 then
      navN = navN + 1
      if rd(0x0727) ~= 2 and navN % 2 == 1 then press({ down = true }, 4) else press({ start = true }, 4) end
    end
    if mode == 4 then st = "play1"; t0 = frame; round = 1; phase = "play"; logf("PLAY round1 at " .. frame); vars("play-start") end
  elseif st == "play1" then
    if frame == t0 + 300 then
      vars("mid-prepause"); counters("mid-prepause"); dump("mid_prepause"); shot("mid_prepause")
      press({ start = true }, 4); logf("START (study pause) at " .. frame); st = "paused"; t0 = frame; phase = "pause"
    end
  elseif st == "paused" then
    if frame == t0 + 60 then
      vars("mid-study"); counters("mid-study"); dump("mid_study"); shot("mid_study")
      pauseY1, pauseY2, pausePills = rd(0x0306), rd(0x0386), rd(0x0327) + rd(0x03A7)
      press({ start = true }, 4); logf("START (unpause) at " .. frame); st = "resumed"; t0 = frame; phase = "play"
    end
  elseif st == "resumed" then
    if frame == t0 + 120 then
      vars("mid-resumed+120"); counters("mid-resumed+120"); shot("mid_resumed")
      logf(string.format("RESUME_CHECK mode=%d pillY P1 %d->%d P2 %d->%d pills %d->%d", rd(0x46), pauseY1, rd(0x0306),
        pauseY2, rd(0x0386), pausePills, rd(0x0327) + rd(0x03A7)))
      st = "toend"
    end
  elseif st == "toend" then
    if mode == 7 or mode == 5 then st = "end"; t0 = frame; phase = "end" .. round; logf("ROUNDEND round " .. round .. " at " .. frame); vars("end+0") end
    if frame > 60000 then logf("TIMEOUT waiting for round end"); lf:close(); emu.stop(2) end
  elseif st == "end" then
    local d = frame - t0
    if d == 30 then vars("end+30"); counters("end+30"); dump("r" .. round .. "_end30"); shot("r" .. round .. "_end30") end
    if d == 150 then vars("end+150"); counters("end+150"); dump("r" .. round .. "_end150"); shot("r" .. round .. "_end150") end
    if d == 260 then vars("end+260"); counters("end+260"); dump("r" .. round .. "_end260"); shot("r" .. round .. "_end260") end
    local leave = (round == 1) and HOLD or 400
    if d == leave then
      vars("end+" .. d); counters("end+" .. d); shot("r" .. round .. "_endhold")
      if round == 3 or rd(0x031E) == 3 or rd(0x039E) == 3 then
        logf("FINAL screen reached; done"); counters("final"); lf:close(); hf:close(); emu.stop(0); return
      end
      press({ start = true }, 4); logf("START (leave end screen) at " .. frame); st = "next"; t0 = frame; phase = "next"
    end
  elseif st == "next" then
    if mode == 4 and frame > t0 + 10 then
      round = round + 1; st = "playN"; t0 = frame; phase = "play"; logf("PLAY round" .. round .. " at " .. frame); vars("round" .. round .. "-start")
    end
    if frame > t0 + 2000 then logf("TIMEOUT leaving end screen; mode=" .. mode); lf:close(); emu.stop(3) end
  elseif st == "playN" then
    if frame == t0 + 200 then vars("round" .. round .. "+200"); dump("r" .. round .. "_play200"); shot("r" .. round .. "_play200") end
    if mode == 7 or mode == 5 then st = "end"; t0 = frame; phase = "end" .. round; logf("ROUNDEND round " .. round .. " at " .. frame); vars("end+0") end
  end
  if frame > 90000 then logf("TIMEOUT global st=" .. st); lf:close(); emu.stop(4) end
end, emu.eventType.endFrame)
