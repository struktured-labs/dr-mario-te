-- probe_nav.lua: why does the v4 cart not reach mode 4 in Mesen?
-- Logs mode/$0727/$04/NAV debug vars once per 30 frames. Serves the $5000 mailbox
-- trivially (DONE=1, col=3, orient=0) so play can proceed if reached.
local OUT = os.getenv("CEN_OUT") or "."
local MAXF = tonumber(os.getenv("CEN_MAXF") or "2400")
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local logf = io.open(OUT .. "/probe.log", "w")
local function log(s) logf:write(s .. "\n"); logf:flush() end

local goes = 0
emu.addMemoryCallback(function() goes = goes + 1 end, emu.callbackType.write, 0x5084)
emu.addMemoryCallback(function() return 1 end, emu.callbackType.read, 0x5084)
emu.addMemoryCallback(function() return 3 end, emu.callbackType.read, 0x5085)
emu.addMemoryCallback(function() return 0 end, emu.callbackType.read, 0x5086)

local frame = 0
emu.addEventCallback(function()
  frame = frame + 1
  if frame % 30 == 0 then
    log(string.format(
      "f=%d m46=%d p727=%d z04=%d navT=%d inj=%02X injN=%d magic=%02X%02X wait51=%d fc43=%d goes=%d vc2=%d capy2=%d",
      frame, rd(0x46), rd(0x0727), rd(0x04), rd(0x6147), rd(0x6148), rd(0x614B),
      rd(0x6149), rd(0x614A), rd(0x51), rd(0x43), goes, rd(0x03A4), rd(0x0386)))
  end
  if frame >= MAXF then
    log("PROBE DONE")
    logf:close()
    pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
log("probe_nav loaded")
