-- PER-DESCRIPTOR CORRECTNESS TEST for DRTUCKGUARD.
-- ⚠ NOT a rate test. probe6's finder is GEOMETRIC and has no reason to publish PAYABLE
-- approaches, so a veto RATE on that stream measures the PROBE, not the guard (probe6's own
-- header: "Rates from this finder measure the PROBE, not the firmware"). A rate cannot show
-- over-veto OR correctness.
-- INSTEAD: the guard is a DETERMINISTIC PREDICATE over (board, descriptor). For every
-- published descriptor we log the BOARD, the DESCRIPTOR, and the cart's DECISION, then compute
-- the predicate INDEPENDENTLY offline. n descriptors = n EXACT evaluations, never vacuous.
local OUT = os.getenv("PT_OUT") or "/home/struktured/projects/dr-mario-rl/tmp/tuckguard/pred.log"
local lf = io.open(OUT, "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local W = 0x5200
local TUCK_C2, TUCK_R2, TGT_C2 = 0x6179, 0x617A, 0x6152
local function filled(bd,r,c) local v=bd[r*8+c]; return v~=0xFF and v~=0x00 end

-- geometric finder, ported from probe6 (same shape, so the descriptor stream is comparable)
local function find_tuck(bd)
  for f=0,7 do
    local seen=false
    for r=0,13 do
      if filled(bd,r,f) then seen=true
      elseif seen and not filled(bd,r+1,f) and not filled(bd,r+2,f) then
        for _,a in ipairs({f-1,f+1}) do
          if a>=0 and a<=7 then
            local clear=true
            for rr=0,r do if filled(bd,rr,a) then clear=false break end end
            if clear then return f,a,r end
          end
        end
      end
    end
  end
  return nil
end

local S={board={},done=false,pending=false,go_f=-1,rcol=0,ror=0xFF,tcol=0xFF,trow=0xFF,goes=0}
local DLAT=34
local function snap() for i=0,127 do S.board[i]=rd(0x0500+i) end end
emu.addMemoryCallback(function() S.pending=true; S.done=false; S.go_f=emu.getState().ppu.frameCount; S.goes=S.goes+1; snap() end,
  emu.callbackType.write, W+0x84)
emu.addMemoryCallback(function()
  if S.done then return 1 end
  local fc=emu.getState().ppu.frameCount
  if S.pending and (fc-S.go_f)>=DLAT then
    -- brain: emptiest column, vertical (same as the QA harness)
    local best,bn=0,999
    for c=0,7 do local n=0; for r=0,15 do if filled(S.board,r,c) then n=n+1 end end; if n<bn then bn=n; best=c end end
    S.rcol=best; S.ror=0
    local f,a,rt=find_tuck(S.board)
    if f then S.tcol=a; S.trow=15-rt else S.tcol=0xFF; S.trow=0xFF end
    S.done=true; S.pending=false
    -- LOG THE CASE: board + descriptor, BEFORE the cart's guard sees it
    local b={} for i=0,127 do b[#b+1]=string.format("%02X",S.board[i]) end
    logf(string.format("CASE f=%d pub_approach=%02X pub_trow=%02X brain_final=%d board=%s",
      fc, S.tcol, S.trow, S.rcol, table.concat(b)))
    return 0
  end
  return S.pending and 0 or 1
end, emu.callbackType.read, W+0x84)
emu.addMemoryCallback(function() return S.rcol end, emu.callbackType.read, W+0x85)
emu.addMemoryCallback(function() return S.ror  end, emu.callbackType.read, W+0x86)
emu.addMemoryCallback(function() return S.tcol end, emu.callbackType.read, W+0x87)
emu.addMemoryCallback(function() return S.trow end, emu.callbackType.read, W+0x88)

local f=0
emu.addEventCallback(function()
  f=f+1
  -- one frame after DONE the driver has adopted (and the guard has run): record the DECISION
  if S.done and S.go_f>0 and f%2==0 then
    local c2=rd(TUCK_C2)
    if S.tcol~=0xFF then
      logf(string.format("DECIDE pub_approach=%02X cart_TUCK_C2=%02X cart_TUCK_R2=%02X TGT_C2=%02X verdict=%s",
        S.tcol, c2, rd(TUCK_R2), rd(TGT_C2), (c2==0xFF) and "VETOED" or "ALLOWED"))
      S.tcol=0xFF
    end
  end
  if f>=tonumber(os.getenv("PT_MAXF") or "9000") then logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end) end
end, emu.eventType.endFrame)
