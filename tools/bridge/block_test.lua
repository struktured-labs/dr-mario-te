-- block_test.lua — de-risk the py65 bridge: confirm Mesen tolerates a MULTI-SECOND block inside
-- a copro_emu brain (memory-callback path) and still places pills. The bridge needs to freeze game
-- time during the ~4s python compute so the falling pill doesn't land before the answer; this proves
-- a blocking brain works before we wire the real (slow) planner.
--   brain busy-waits ~1.5s (os.clock, plain Lua — no emu.*) then returns the dumb default move.
local DIR = "/mnt/data/drmario/pocket-copro/mesen_copro_qa/"
local OUT = DIR.."shots/"
local lf = io.open(OUT.."block_test.log", "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function fill(base) local n=0; for i=0,127 do local c=rd(base+i); if c~=0xFF and c~=0x00 then n=n+1 end end; return n end

local EMU = dofile(DIR.."copro_emu.lua")

local BLOCK_S = 1.5
local blocked = 0
local function slow_brain(board, cA, cB)
  local t0 = os.clock()
  while os.clock() - t0 < BLOCK_S do end   -- busy block (plain Lua only)
  blocked = blocked + 1
  return EMU.default_brain(board, cA, cB)   -- dumb move after the block
end

-- drive P1 of the AB cart with the slow (blocking) brain, small latency so the pill barely falls
local p1 = EMU.attach{ window=0x5000, board_src=0x0400, colA=0x0301, colB=0x0302, latency=2, brain=slow_brain }
-- P2 dumb/fast to keep the match alive (no idle-topout ending the match)
local p2 = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
logf(string.format("block_test: P1 blocking brain (%.1fs/pill), P2 dumb; latency P1=2", BLOCK_S))

local frame=0; local firstPlay=nil
emu.addEventCallback(function()
  frame=frame+1
  local mode=rd(0x46)
  if mode==4 and not firstPlay then firstPlay=frame; logf("PLAY at "..frame) end
  if mode==4 and firstPlay and (frame-firstPlay)%120==0 then
    logf(string.format("t=%d(+%d) P1: GO=%d DONE=%d tgtC=%d px=%d fill=%d blocked=%d | P2 GO=%d",
      frame, frame-firstPlay, p1.goes, p1.dones, rd(0x6150), rd(0x0305), fill(0x0400), blocked, p2.goes))
  end
  if firstPlay and (frame-firstPlay)==300 then local p=emu.takeScreenshot(); local f=io.open(OUT.."block_test.png","wb"); f:write(p); f:close() end
  if (firstPlay and frame>=firstPlay+420) or frame>=3000 then
    logf(string.format("SUMMARY P1 GO=%d DONE=%d blocked=%d (blocking brain OK if GO>2 && DONE tracks GO && pills placed)", p1.goes, p1.dones, blocked))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
logf("block_test loaded")
