local CFG = dofile(CFGPATH)
local lf = io.open(CFG.out, "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a,v) emu.write(a, v, NES) end
local EMU = dofile(EMUPATH)
local s = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
local SEED1,SEED2 = 0x6167,0x6168
local PX2,VC2,PILLY2 = 0x0385,0x03A4,0x0386
local TUCK_C2,TGT_C2 = 0x6179,0x6152
local frame,seeded,lastY = 0,false,255
local pills,strand,reached = 0,0,0
local prevX,prevTgt = 255,255
emu.addEventCallback(function()
  frame=frame+1
  if rd(0x46)==4 then
    if not seeded then wr(SEED1,CFG.seed%256); wr(SEED2,(CFG.seed~0xA4)%256); seeded=true end
    local y=rd(PILLY2)
    if y > lastY + 4 then          -- new pill; the PREVIOUS one locked -> prevX/prevTgt are its lock state
      if prevTgt ~= 255 and prevTgt < 8 then
        pills=pills+1
        if prevX == prevTgt then reached=reached+1 else strand=strand+1 end
      end
    end
    prevX=rd(PX2); prevTgt=rd(TGT_C2)   -- keep last-active values (become lock state next spawn)
    lastY=y
  end
  if frame>=CFG.maxframes then
    logf(string.format("SUMMARY seed=%d pills=%d reached_target=%d STRANDED=%d strand_rate=%.3f",
      CFG.seed,pills,reached,strand, pills>0 and strand/pills or 0))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
