-- Final decisive nav test: no Start presses at all (auto-advance handles
-- legal/logo/title -> Game Select on its own, confirmed by exp0v2). Hold
-- Right STARTING BEFORE Game Select even renders (frame 2900, well ahead
-- of the ~3008 arrival we've measured), continuing through and past it,
-- then a Start pulse. Tests whether the auto-advance timer only respects
-- input that's already asserted when the screen initializes.
local OUT = "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tdm/"
local frame = 0

local logf = io.open(OUT .. "nav_log.txt", "w")
logf:write("final decisive test loaded\n")
logf:flush()

local function save_shot(tag)
	local ok, png = pcall(emu.takeScreenshot)
	if ok then
		local f = io.open(OUT .. "shot_" .. tag .. ".png", "wb")
		f:write(png)
		f:close()
		logf:write("shot " .. tag .. " saved at frame " .. frame .. "\n")
	else
		logf:write("shot " .. tag .. " FAILED: " .. tostring(png) .. "\n")
	end
	logf:flush()
end

local RIGHT_START = 2900
local RIGHT_END = 3100
local START2_START = 3105
local START2_END = 3115

emu.addEventCallback(function()
	frame = frame + 1

	-- keep the PAR-code target forced too, in case it matters combined
	-- with actual navigation into Dr. Mario's own submenu this time.
	pcall(emu.write, 0x1E72, 0x03, emu.memType.snesWorkRam)

	if frame >= RIGHT_START and frame < RIGHT_END then
		pcall(emu.setInput, { right = true }, 0)
	elseif frame >= START2_START and frame < START2_END then
		pcall(emu.setInput, { start = true }, 0)
	else
		pcall(emu.setInput, {}, 0)
	end

	if frame == 2850 or frame == 2950 or frame == 3050 or frame == 3090
		or frame == 3130 or frame == 3200 or frame == 3400 or frame == 3700 then
		save_shot(string.format("f%05d", frame))
	end
end, emu.eventType.startFrame)
