-- probe_final.lua: DRSTUDYEND match-final + next-match-start probe (couch DRHUMAN cart remapped to MMC1,
-- P2 seat served by tools/copro_emu.lua, P1 idle so it tops out). Run via experiments/studyend/run_final.sh.
-- env: SE_OUT=<dir/> SE_TAG=<tag> SE_EMU=<tools/copro_emu.lua> SE_SCEN=final2p|final3|oneplayer
--      SE_FHOLD=<frames on the match-final screen before START, default 400>
--   final2p   : on the first play frame write P2 victories $039E=2 (same frame, both carts), so round 1's
--               end IS the match final -> an exact pair with matched START timing.
--   final3    : a genuine 3-round match (no writes); rounds 1-2 end screens held 400 frames.
--   oneplayer : 1 PLAYER game, P1 tops out -> 1P game over (shares $95C9.. with the 2P final in stock).
-- Every scenario: hold the final screen SE_FHOLD frames, press START, walk the menus with START every 40
-- frames into the next match, run 300 frames of it, stop. Per frame: mode + RAM/PRG-RAM hash (whole run) and
-- the full $0000-$07FF hex from the final end screen to the end (for exact address-level diffs).
local OUT = assert(os.getenv("SE_OUT"), "set SE_OUT")
local TAG = os.getenv("SE_TAG") or "x"
local SCEN = os.getenv("SE_SCEN") or "final2p"
local FHOLD = tonumber(os.getenv("SE_FHOLD") or "400")
local FULLLO, FULLHI = tonumber(os.getenv("SE_FULLLO") or "-1"), tonumber(os.getenv("SE_FULLHI") or "-1")  -- extra full-RAM window
local NES, OAM, PPU = emu.memType.nesMemory, emu.memType.nesSpriteRam, emu.memType.nesPpuMemory
local lf = io.open(OUT .. TAG .. "_final.log", "w")
local hf = io.open(OUT .. TAG .. "_frames.txt", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end
local function rd(a) return emu.read(a, NES, false) end
local function shot(n)
  local ok, p = pcall(emu.takeScreenshot)
  if ok then local f = io.open(OUT .. TAG .. "_" .. n .. ".png", "wb"); f:write(p); f:close() end
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
    f:write(string.format("OAM %02d Y=%3d tile=%02X attr=%02X X=%3d\n", s, emu.read(b, OAM, false),
      emu.read(b + 1, OAM, false), emu.read(b + 2, OAM, false), emu.read(b + 3, OAM, false)))
  end
  for r = 0, 29 do f:write(string.format("NT r%02d %s\n", r, hexrow(0x2000 + r * 32, 32, PPU))) end
  f:close()
end
local function vars(tag)
  logf(string.format("  [%s] mode=%d players=%d $54=%d whoWon$55=%d whoFailed$61=%d vict P1/P2=%d/%d music$06F5=%02X status=%02X/%02X",
    tag, rd(0x46), rd(0x0727), rd(0x54), rd(0x55), rd(0x61), rd(0x031E), rd(0x039E), rd(0x06F5), rd(0x0300), rd(0x0380)))
end
-- h: $0000-$07FF  g: PRG-RAM  m: $0000-$07FF minus $BF/$C7 (DRNMITMP pad-read scratch) and minus the stack page
-- (what lies around SP at end-of-frame is the NMI's pushed return address/flags = which instruction the main loop
-- was on when the NMI landed: CPU phase, not game state)
local function ramhash()
  local h, g, m = 0, 0, 0
  for a = 0x0000, 0x07FF do
    local v = rd(a); h = (h * 31 + v) % 2147483647
    if a ~= 0xBF and a ~= 0xC7 and (a < 0x100 or a >= 0x200) then m = (m * 31 + v) % 2147483647 end
  end
  for a = 0x6000, 0x7FFF do g = (g * 31 + rd(a)) % 2147483647 end
  return h, g, m
end

local EMU = dofile(assert(os.getenv("SE_EMU"), "set SE_EMU"))
local cs = EMU.attach{ window = 0x5200, board_src = 0x0500, colA = 0x0381, colB = 0x0382, latency = 24 }
-- exec counters (unit-0 PRG offsets): the stock final fill / GAME OVER calls and the START loop
local EX = { finalFill = 0x15CE, gameOverP1 = 0x15DB, gameOverP2 = 0x15E7, startLoop = 0x1607,
             newBlock = 0x15BD, onePlayerEntry = 0x15C9, levelInit = 0x0206 }
local cnt = {}
for k, off in pairs(EX) do
  cnt[k] = 0
  emu.addMemoryCallback(function() cnt[k] = cnt[k] + 1 end, emu.callbackType.exec, off, off, emu.cpuType.nes, emu.memType.nesPrgRom)
end
local function counters(tag)
  local ks = {}
  for k in pairs(cnt) do ks[#ks + 1] = k end
  table.sort(ks)
  local p = {}
  for _, k in ipairs(ks) do p[#p + 1] = k .. "=" .. cnt[k] end
  logf("  [" .. tag .. "] EXEC " .. table.concat(p, " "))
end

local frame, cur, untl = 0, nil, -1
emu.addEventCallback(function() if cur and frame < untl then emu.setInput(cur, 0) end end, emu.eventType.inputPolled)
local function press(i, d) cur = i; untl = frame + (d or 4) end

local want = (SCEN == "oneplayer") and 1 or 2
local st, t0, round, navN, lastMode, fullFrom = "nav", 0, 0, 0, -1, nil
local function finished(code) logf("DONE " .. code); lf:close(); hf:close(); emu.stop(code) end
emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  if mode ~= lastMode then logf(string.format("MODE f=%d %d->%d (st=%s)", frame, lastMode, mode, st)); lastMode = mode end
  local h, g, mh = ramhash()
  hf:write(string.format("%d %d %d %d %d\n", frame, mode, h, g, mh))
  if (fullFrom and frame >= fullFrom) or (frame >= FULLLO and frame <= FULLHI) then
    hf:write("R " .. frame .. " " .. hexrow(0, 0x800, NES) .. "\n")
  end
  if mode == 4 and not (cur and frame < untl + 2) and (rd(0xF5) ~= 0 or rd(0xF7) ~= 0) then
    logf(string.format("PHANTOM f=%d st=%s F5=%02X F7=%02X", frame, st, rd(0xF5), rd(0xF7)))
  end
  if st == "nav" and mode == 0 and frame > 2000 and rd(0x0727) ~= want then
    logf("PLAYER COUNT FORCED: $0727=" .. rd(0x0727) .. " after 2000 title frames, want " .. want ..
         " (couch DRNAV_V4 nav rewrites $0727=2 every menu hook) -- scenario unreachable on this cart")
    finished(5); return
  end
  if st == "nav" or st == "nav2" then
    if mode ~= 4 and frame % 40 == 0 then
      navN = navN + 1
      if mode == 0 and rd(0x0727) ~= want then           -- never START the title on the wrong player count
        press(navN % 2 == 1 and { select = true } or (want == 1 and { up = true } or { down = true }), 4)
      else
        press({ start = true }, 4)
      end
    end
    if mode == 4 then
      if st == "nav" then
        st = "play"; round = 1; logf("PLAY round1 at " .. frame); vars("round1-start")
        if rd(0x0727) ~= want then logf("WRONG PLAYER COUNT " .. rd(0x0727) .. " want " .. want); finished(5); return end
        if SCEN == "final2p" then
          local ok, err = pcall(function() emu.write(0x039E, 2, NES) end)
          logf("POKE $039E=2 ok=" .. tostring(ok) .. " " .. tostring(err)); vars("after-poke")
        end
      else
        st = "next"; t0 = frame; logf("NEXT MATCH play at " .. frame); vars("next+0"); dump("next0"); shot("next0"); counters("next+0")
      end
    end
  elseif st == "play" then
    if mode == 7 then
      local final = (SCEN ~= "final3") or round == 3
      st = final and "final" or "roundend"; t0 = frame
      logf("ROUNDEND round " .. round .. " at " .. frame .. (final and " (FINAL)" or "")); vars("end+0")
      if final then fullFrom = frame end
    end
  elseif st == "roundend" then
    if frame == t0 + 400 then press({ start = true }, 4); st = "between"; t0 = frame end
  elseif st == "between" then
    if mode == 4 and frame > t0 + 10 then round = round + 1; st = "play"; logf("PLAY round" .. round .. " at " .. frame) end
  elseif st == "final" then
    local d = frame - t0
    for _, k in ipairs({ 30, 150, 260, FHOLD - 10 }) do
      if d == k then vars("final+" .. d); counters("final+" .. d); dump("final" .. d); shot("final" .. d) end
    end
    if d == FHOLD then
      press({ start = true }, 4); logf("START (leave match-final screen) at " .. frame); st = "poststart"; t0 = frame
    end
  elseif st == "poststart" then
    if frame == t0 + 30 then vars("poststart+30"); counters("poststart+30"); shot("poststart30") end
    if mode ~= 7 and frame > t0 + 30 then st = "nav2"; logf("menus from " .. frame) end
  elseif st == "next" then
    local d = frame - t0
    if d == 200 then vars("next+200"); dump("next200"); shot("next200") end
    if d == 300 then counters("end"); finished(0) end
  end
  if frame > 60000 then logf("TIMEOUT st=" .. st .. " mode=" .. mode); finished(2) end
end, emu.eventType.endFrame)
