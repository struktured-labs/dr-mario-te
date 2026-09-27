-- Reachability check: does DRTUCKGUARD's precondition (a tuck descriptor engaged) actually
-- FIRE in this substrate? If tucks are rare the divergence rate collapses and the A/B is dead
-- before it starts. Counts engaged placements per game from RAM.
-- ⚠ HARD ERROR if play is never reached -- a well-formed zero is the quiet failure mode that
-- cost a run when the human cart (which does NOT autonav) returned pills=0 instead of refusing.
local CFG = dofile("/home/struktured/projects/dr-mario-rl/tmp/tuckguard/cfge.lua")
local lf = io.open(CFG.out, "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local EMU = dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
local s = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
-- ⚠ PILL COUNT COMES FROM THE ROM'S OWN AUTHORITATIVE COUNTER ($0327 P1 / $03A7 P2), not
-- inferred from the pill Y register. The Y-delta heuristic undercounted badly (3 pills in
-- 3308 play frames, where ~20-25 was expected) -- a well-formed wrong number, not a crash.
local TUCK_C2, TGT_C2, PILLCNT2 = 0x6179, 0x6152, 0x03A7
local frame, playFrames, pills, engaged, stranded, lastY = 0,0,0,0,0,-1
emu.addEventCallback(function()
  frame = frame + 1
  if rd(0x46) == 4 then
    playFrames = playFrames + 1
    local pc = rd(PILLCNT2)
    if pc ~= lastY then
      pills = pills + 1
      local tc, tg = rd(TUCK_C2), rd(TGT_C2)
      if tc ~= 0xFF then
        engaged = engaged + 1
        if tg ~= 0xFF and tc == tg then stranded = stranded + 1 end
      end
    end
    lastY = pc
  end
  if frame >= CFG.maxframes then
    if playFrames < 60 then
      logf("HARD ERROR: play was NEVER reached (playFrames="..playFrames..") -- refusing to report a zero")
    else
      logf(string.format("ENGAGE playFrames=%d pills=%d engaged=%d stranded=%d engage_rate=%.3f",
        playFrames, pills, engaged, stranded, pills>0 and engaged/pills or 0))
    end
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
