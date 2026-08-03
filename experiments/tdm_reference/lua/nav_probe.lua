-- T&DM navigation probe v10: isolate the effect of directional input on
-- Game Select, WITHOUT ever pressing Start again, so we can see raw cursor
-- movement (if any) uncontaminated by a confirm action. Try Right held long,
-- screenshotting every 15 frames; then try Down held long, same cadence.
local OUT = "/tmp/claude-1000/-home-struktured-projects-dr-mario-rl/02493363-c6af-4da9-9c47-58ceef8174b6/scratchpad/tdm/"
local frame = 0

local logf = io.open(OUT .. "nav_log.txt", "w")
logf:write("v10 script loaded\n")
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

local PRESS_EVERY = 300
local PRESS_HOLD = 8
local NUM_PRESSES = 11
local PHASE1_END = (NUM_PRESSES - 1) * PRESS_EVERY + PRESS_HOLD  -- 3008

local RIGHT_HOLD_START = PHASE1_END + 10   -- 3018
local RIGHT_HOLD_END = RIGHT_HOLD_START + 90  -- 3108
local DOWN_HOLD_START = RIGHT_HOLD_END + 40   -- 3148
local DOWN_HOLD_END = DOWN_HOLD_START + 90    -- 3238

emu.addEventCallback(function()
	frame = frame + 1

	if frame <= PHASE1_END and frame % PRESS_EVERY < PRESS_HOLD then
		pcall(emu.setInput, { start = true }, 0)
	elseif frame >= RIGHT_HOLD_START and frame < RIGHT_HOLD_END then
		pcall(emu.setInput, { right = true }, 0)
		local rel = frame - RIGHT_HOLD_START
		if rel % 15 == 0 then
			save_shot(string.format("right_hold_%03d", rel))
		end
	elseif frame >= DOWN_HOLD_START and frame < DOWN_HOLD_END then
		pcall(emu.setInput, { down = true }, 0)
		local rel = frame - DOWN_HOLD_START
		if rel % 15 == 0 then
			save_shot(string.format("down_hold_%03d", rel))
		end
	else
		pcall(emu.setInput, {}, 0)
	end
end, emu.eventType.startFrame)
