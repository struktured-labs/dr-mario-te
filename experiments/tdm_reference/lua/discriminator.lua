-- Decisive discriminator (team-lead directive): compare cold-boot timing
-- with ZERO input vs Start HELD from frame 0. Identical screen-transition
-- frames across both runs => no emulated input has ever reached the game
-- (the wall is input plumbing, not navigation timing).
--
-- Mode is picked via a marker file written by the launcher shell script,
-- since Mesen2's Lua environment doesn't expose OS env vars directly
-- without I/O access (which we do have, so os.getenv should work -- but
-- using a file keeps this robust either way).
local OUT = "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tdm/"
local frame = 0

local modeFile = io.open(OUT .. "discriminator_mode.txt", "r")
local mode = "zero"
if modeFile then
	mode = modeFile:read("*l") or "zero"
	modeFile:close()
end

local logf = io.open(OUT .. "discriminator_log_" .. mode .. ".txt", "w")
logf:write("discriminator mode=" .. mode .. " loaded\n")
logf:flush()

local function save_shot(tag)
	local ok, png = pcall(emu.takeScreenshot)
	if ok then
		local f = io.open(OUT .. "disc_" .. mode .. "_" .. tag .. ".png", "wb")
		f:write(png)
		f:close()
		logf:write("shot " .. tag .. " saved at frame " .. frame .. " (" .. #png .. " bytes)\n")
	else
		logf:write("shot " .. tag .. " FAILED: " .. tostring(png) .. "\n")
	end
	logf:flush()
end

-- Shared checkpoint schedule for both runs -- identical frames so results
-- are directly comparable.
local checkpoints = {30, 100, 300, 600, 900, 1200, 1500, 1800, 2100, 2400,
	2700, 3000, 3100, 3200, 3300, 3600, 3900}
local checkSet = {}
for _, f in ipairs(checkpoints) do checkSet[f] = true end

emu.addEventCallback(function()
	frame = frame + 1

	if mode == "start_held" then
		pcall(emu.setInput, { start = true }, 0)
	else
		pcall(emu.setInput, {}, 0)
	end

	if checkSet[frame] then
		save_shot(string.format("f%05d", frame))
	end
end, emu.eventType.startFrame)
