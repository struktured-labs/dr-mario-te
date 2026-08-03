-- One remaining "fix attempt" (team-lead budget): hold Right CONTINUOUSLY
-- from frame 1 (mirroring the Start-held discriminator that just proved a
-- continuous hold measurably perturbs the state machine, unlike our
-- earlier Right attempts which only started the hold near Game Select).
-- Also holds Start together with Right from frame 3200 onward, in case the
-- combination (not Right alone) is what's needed to confirm Dr. Mario.
local OUT = "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tdm/"
local frame = 0

local logf = io.open(OUT .. "right_from_boot_log.txt", "w")
logf:write("right_from_boot script loaded\n")
logf:flush()

local function save_shot(tag)
	local ok, png = pcall(emu.takeScreenshot)
	if ok then
		local f = io.open(OUT .. "rfb_" .. tag .. ".png", "wb")
		f:write(png)
		f:close()
		logf:write("shot " .. tag .. " saved at frame " .. frame .. " (" .. #png .. " bytes)\n")
	else
		logf:write("shot " .. tag .. " FAILED: " .. tostring(png) .. "\n")
	end
	logf:flush()
end

local checkpoints = {30, 100, 300, 600, 900, 1200, 1500, 1800, 2100, 2400,
	2700, 3000, 3100, 3200, 3300, 3600, 3900, 4200, 4500}
local checkSet = {}
for _, f in ipairs(checkpoints) do checkSet[f] = true end

emu.addEventCallback(function()
	frame = frame + 1

	if frame >= 3200 then
		pcall(emu.setInput, { right = true, start = true }, 0)
	else
		pcall(emu.setInput, { right = true }, 0)
	end

	if checkSet[frame] then
		save_shot(string.format("f%05d", frame))
	end
end, emu.eventType.startFrame)
