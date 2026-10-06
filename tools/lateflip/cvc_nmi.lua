-- cvc_nmi.lua -- long CvC-cart run: nmi_witness.lua + a CHURNING P2 copro mailbox ($5200 window) so the DRLATEGUARD
-- gate does real work: after each GO the running best changes every 2-9 frames (random col 0-7, orient 0-3, first
-- publish 1-6 frames after GO, $FF before it), DONE 15-70 frames after GO with a final that differs from the last
-- live publish half the time -- the late-flip shape of experiments/lateflip. No case injection, no field wipes: the
-- cart plays itself (P1 = native AI). LN_HUMAN=1 (couch/DRHUMAN carts): navigate the menus like lateflip_probe.lua
-- (DOWN/START every 40 frames until play, START out of any non-play mode) and wipe P1's field every frame so the
-- idle human seat never tops out. Env: LN_DIR, LN_MAXF, LN_SEED, LN_HUMAN + nmi_witness.lua's.
local D = os.getenv("LN_DIR") or error("LN_DIR")
dofile(D .. "/nmi_witness.lua")
local MAXF = tonumber(os.getenv("LN_MAXF") or "60000")
math.randomseed(tonumber(os.getenv("LN_SEED") or "1"))
local W = 0x5200
local f = 0
local S = { go_f = -1000, done_f = -1, pubs = {}, final = { 3, 1 }, goes = 0, dones = 0 }
emu.addMemoryCallback(function()
  S.goes = S.goes + 1; S.go_f = f
  local t, pubs = math.random(1, 6), {}
  S.done_f = f + math.random(15, 70)
  while f + t < S.done_f do pubs[#pubs + 1] = { f + t, math.random(0, 7), math.random(0, 3) }; t = t + math.random(2, 9) end
  S.pubs = pubs
  if #pubs > 0 and math.random() < 0.5 then S.final = { pubs[#pubs][2], pubs[#pubs][3] }
  else S.final = { math.random(0, 7), math.random(0, 3) } end
end, emu.callbackType.write, W + 0x84)
local function view()
  if f >= S.done_f then return S.final[1], S.final[2], 1 end
  local c, o = 0, 0xFF
  for i = 1, #S.pubs do if S.pubs[i][1] <= f then c, o = S.pubs[i][2], S.pubs[i][3] else break end end
  return c, o, 0
end
emu.addMemoryCallback(function() local _, _, d = view(); return d end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() local c = view(); return c end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() local _, o = view(); return o end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return 0xFF end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return 0 end, emu.callbackType.read, W + 0x88)
local HUMAN = (os.getenv("LN_HUMAN") or "0") == "1"
local cur_in, untl, navN = nil, -1, 0
emu.addEventCallback(function() if cur_in and f < untl then emu.setInput(cur_in, 0) end end, emu.eventType.inputPolled)
local modes = {}
emu.addEventCallback(function()
  f = f + 1
  local m = emu.read(0x46, emu.memType.nesMemory, false)
  modes[m] = (modes[m] or 0) + 1
  if HUMAN then
    if m ~= 4 and f % 40 == 0 then
      navN = navN + 1
      if emu.read(0x0727, emu.memType.nesMemory, false) ~= 2 and navN % 2 == 1 then cur_in = { down = true }
      else cur_in = { start = true } end
      untl = f + 4
    end
    if m == 4 then
      for i = 0, 127 do pcall(function() emu.write(0x0400 + i, 0xFF, emu.memType.nesMemory) end) end
      cur_in = { down = true }; untl = f + 2   -- P1 drops fast: P2 waits at nextAction 1 until P1's capsule locks
    end
  end
  if f >= MAXF then
    local t = {}
    for k, v in pairs(modes) do t[#t + 1] = string.format("%02X:%d", k, v) end
    table.sort(t)
    NMIW_summary("SUMMARY")
    local wf = io.open((os.getenv("LN_OUT") or ".") .. "/nmi_" .. (os.getenv("LN_TAG") or "nmi") .. ".log", "a")
    wf:write(string.format("CVC goes=%d modes=%s\nDONE\n", S.goes, table.concat(t, ","))); wf:close()
    emu.stop(0)
  end
end, emu.eventType.endFrame)
