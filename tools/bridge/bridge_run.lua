-- bridge_run.lua — END-TO-END integration test: drive the AB cart's P1 with the REAL py65 depth-3
-- planner (nes_d3_golden.decide_d3, DEPLOY config) served by planner_bridge.py over a file bridge.
-- P2 uses the dumb default brain (keeps the match alive so P1 isn't ended by an idle-topout).
--
-- The brain BLOCKS the emulation thread during the ~4s python compute (busy-wait on resp.txt, plain
-- Lua only — no emu.* in the callback). Blocking FREEZES game time, so the slow planner doesn't cost
-- the falling pill any distance (a real copro answers in ~15-50f precisely because the pill falls).
--
-- PREREQ: planner_bridge.py must be running (background) on the same --dir.
--   watch P1's virus count (D-nibble cells in $0400) DROP = the real brain clearing viruses in Mesen.
local DIR = "/mnt/data/drmario/pocket-copro/mesen_copro_qa/"
local BR  = DIR.."bridge/"
local OUT = DIR.."shots/"
local lf = io.open(OUT.."bridge_run.log", "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function shot(n) local p=emu.takeScreenshot(); local f=io.open(OUT..n,"wb"); f:write(p); f:close() end
local function viruses(base) local n=0; for i=0,127 do if (rd(base+i) & 0xF0)==0xD0 then n=n+1 end end; return n end
local function fill(base) local n=0; for i=0,127 do local c=rd(base+i); if c~=0xFF and c~=0x00 then n=n+1 end end; return n end

local EMU = dofile(DIR.."copro_emu.lua")

-- P1 next-pill preview colors, captured each frame (brain can't call emu.*)
local nA, nB = 0, 1
-- bridge stats
local seq = 0
local misses, lastms = 0, 0

local function atomic_write(path, text)
  local tmp = path..".tmp"; local f = io.open(tmp,"w"); f:write(text); f:close(); os.rename(tmp, path)
end
local function read_resp(want)
  local f = io.open(BR.."resp.txt","r"); if not f then return nil end
  local s = f:read("*a"); f:close()
  local nums = {}; for d in s:gmatch("%-?%d+") do nums[#nums+1] = tonumber(d) end
  if #nums >= 3 and nums[1] == want then return nums[2], nums[3], nums[4] or 0 end
  return nil
end

local function planner_brain(board, cA, cB)
  seq = seq + 1
  -- serialize request: seq / pA pB nA nB / 128 board bytes
  local parts = {}; for i=0,127 do parts[#parts+1] = tostring(board[i] or 0xFF) end
  atomic_write(BR.."req.txt", string.format("%d\n%d %d %d %d\n%s\n", seq, cA, cB, nA, nB, table.concat(parts," ")))
  -- block (freeze game time) until the daemon answers this seq, up to ~12s
  local t0 = os.clock()
  while os.clock() - t0 < 12.0 do
    local col, o4, ms = read_resp(seq)
    if col ~= nil then lastms = ms; return col, o4 end
  end
  misses = misses + 1                                   -- daemon slow/absent -> dumb fallback
  return EMU.default_brain(board, cA, cB)
end

local p1 = EMU.attach{ window=0x5000, board_src=0x0400, colA=0x0301, colB=0x0302, latency=2, brain=planner_brain }
local p2 = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
logf("bridge_run: P1 = py65 decide_d3 (blocking file bridge), P2 = dumb; watching P1 virus count $0400")

local frame=0; local firstPlay=nil; local v0=nil; local shotN=0
emu.addEventCallback(function()
  frame=frame+1
  nA = rd(0x031A) & 0x0F; nB = rd(0x031B) & 0x0F      -- capture P1 preview colors for the brain
  local mode=rd(0x46)
  if mode==4 and not firstPlay then firstPlay=frame; logf("PLAY at "..frame) end
  if mode==4 and firstPlay and (frame-firstPlay)%60==0 then
    local v=viruses(0x0400); if v0==nil then v0=v end
    logf(string.format("t=%d(+%d) P1: GO=%d DONE=%d moves=%d lastCompute=%dms miss=%d | P1 virus=%d(start %d) fill=%d tgtC=%d px=%d",
      frame, frame-firstPlay, p1.goes, p1.dones, seq, lastms, misses, v, v0, fill(0x0400), rd(0x6150), rd(0x0305)))
  end
  if mode==4 and firstPlay and shotN<4 and (frame-firstPlay)==(shotN+1)*120 then shotN=shotN+1; shot(string.format("bridge_%02d.png",shotN)) end
  -- run until P1 has placed ~20 pills, cleared some viruses, or a wall budget
  local enough = (p1.dones >= 20) or (v0 and viruses(0x0400) <= v0-4)
  if (firstPlay and enough and frame>firstPlay+120) or frame>=6000 then
    local vend = firstPlay and viruses(0x0400) or -1
    logf(string.format("SUMMARY P1 moves=%d GO=%d DONE=%d miss=%d virus %s->%d (real-brain placement proven if moves>3 && miss==0; clearing proven if virus dropped)",
      seq, p1.goes, p1.dones, misses, tostring(v0), vend))
    shot("bridge_final.png")
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
logf("bridge_run loaded")
