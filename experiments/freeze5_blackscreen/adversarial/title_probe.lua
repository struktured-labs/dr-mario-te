-- Capture idle TITLE and idle LEVEL-SELECT screens 1 s apart, to test whether a
-- "legitimately static" Dr. Mario screen actually holds still at the pixel level.
local OUT = "/home/struktured/projects/dr-mario-qa-wt/tmp/adversary_framewd/emu/"
local n = 0

local function shoot(tag)
  gui.savescreenshotas(OUT .. tag .. ".png")
end

-- boot / attract: settle on the title screen
for i = 1, 420 do emu.frameadvance() end

-- TITLE, idle, four captures 60 frames (~1 s) apart
for k = 1, 4 do
  shoot(string.format("title_%d", k))
  for i = 1, 60 do emu.frameadvance() end
end

-- TITLE, idle, four captures 20 frames (~0.33 s) apart -- catches fast blink cycles
for k = 1, 4 do
  shoot(string.format("titlefast_%d", k))
  for i = 1, 20 do emu.frameadvance() end
end

-- press START to reach the level-select / settings screen
for i = 1, 12 do joypad.set(1, {start = true}); emu.frameadvance() end
for i = 1, 90 do emu.frameadvance() end

for k = 1, 4 do
  shoot(string.format("levelsel_%d", k))
  for i = 1, 60 do emu.frameadvance() end
end

emu.exit()
