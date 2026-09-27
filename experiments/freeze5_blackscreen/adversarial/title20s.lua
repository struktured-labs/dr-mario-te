-- Idle TITLE sampled at EXACTLY the watchdog cadence: 1200 frames = 20.0 s NTSC
emu.speedmode("maximum")
local OUT = "/home/struktured/projects/dr-mario-qa-wt/tmp/adversary_framewd/emu20/"
for i = 1, 420 do emu.frameadvance() end
for k = 1, 6 do
  gui.savescreenshotas(OUT .. string.format("t20_%d", k) .. ".png")
  for i = 1, 1200 do emu.frameadvance() end
end
emu.exit()
