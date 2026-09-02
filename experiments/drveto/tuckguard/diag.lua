-- DIAGNOSTIC: what do $03A7 and TUCK_C2 actually DO? Dump raw values, draw no conclusions.
local out=io.open("/home/struktured/projects/dr-mario-rl/tmp/tuckguard/diag.log","w")
local NES=emu.memType.nesMemory
local function rd(a) return emu.read(a,NES,false) end
local EMU=dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
EMU.attach{window=0x5200,board_src=0x0500,colA=0x0381,colB=0x0382,latency=24}
local f,n=0,0
emu.addEventCallback(function()
  f=f+1
  if rd(0x46)==4 then
    n=n+1
    if n%15==0 and n<=1500 then
      out:write(string.format("f=%-6d pill$03A7=%-4d pillP1$0327=%-4d TUCK_C2=%02X TUCK_R2=%02X TGT_C2=%02X pillY=%-4d vc2=%02X\n",
        f, rd(0x03A7), rd(0x0327), rd(0x6179), rd(0x617A), rd(0x6152), rd(0x0386), rd(0x03A4)))
      out:flush()
    end
  end
  if f>=9000 then out:write("DONE\n"); out:close(); pcall(function() emu.stop(0) end) end
end, emu.eventType.endFrame)
