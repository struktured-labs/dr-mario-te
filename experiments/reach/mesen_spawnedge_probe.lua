-- mesen_spawnedge_probe.lua -- DRSPAWNEDGE round-start + Y=$0F-lock check on the REAL cart in Mesen (2026-09-28).
-- Cart: the CvC TAP cart (P1 native AI, P2 copro AI on the $5200 window), header remapped 100 -> 1 (MMC1). The P2
-- copro is emulated by tools/copro_emu.lua. Zero input: the cart's autonav plays VS rounds and rematches by itself.
-- Logged (to $DRQA_OUT/spawnedge_<tag>.log, one line per change):
--   E <frame>             : one new-pill EDGE = the new-pill block's own `STA DELAY2 <- 15` ($615F)
--   S <frame> mode y pc na x rot : any change of mode $46 / p2 Y $0386 / p2_pillsCounter $03A7 / p2_nextAction $0397
--   F ...                 : the forced top-row lock (see FORCE below)
-- FORCE (at the first spawn after level inits DRQA_FORCE_AT, default 4,9,14): cols 0-1 occupied from row 1 down, the
-- capsule teleported to X=0 at Y=$0F, answer "col 0, horizontal" -- it locks at Y=$0F OFF the spawn cells. The next
-- pill must then get its edge (fix on) / miss it (fix off).
-- Mesen traps honoured: no emu.* inside memory callbacks; emu.write has THREE args (pcall-logged); single instance.
local DIR = os.getenv("DRQA_DIR") or error("DRQA_DIR (folder with copro_emu.lua)")
if DIR:sub(-1) ~= "/" then DIR = DIR .. "/" end
local OUT = os.getenv("DRQA_OUT") or error("DRQA_OUT"); if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local TAG = os.getenv("DRQA_TAG") or "run"
local MAXF = tonumber(os.getenv("DRQA_MAXF") or "90000")
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local lf = io.open(OUT .. "spawnedge_" .. TAG .. ".log", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end
local function wr(a, v)
  local ok, err = pcall(function() emu.write(a, v, NES) end)
  if not ok then logf("WRITE_ERR " .. tostring(err)) end
end

-- ---- emulated copro on P2 ($5200), with a switchable brain ----
local force = { active = false, saved = {} }
local EMU = dofile(DIR .. "copro_emu.lua")
local function brain(board, cA, cB)
  if force.active then return 0, 2 end            -- col 0, copro orient 2 = game 0 = horizontal
  return EMU.default_brain(board, cA, cB)
end
local p2 = EMU.attach{ window = 0x5200, board_src = 0x0500, colA = 0x0381, colB = 0x0382, latency = 6, brain = brain }
-- tuck descriptor: "no tuck" (the real copro serves these; open bus would read $52)
emu.addMemoryCallback(function() return 0xFF end, emu.callbackType.read, 0x5287)
emu.addMemoryCallback(function() return 0x00 end, emu.callbackType.read, 0x5288)

-- ---- edge counter: pure Lua inside the write callback ----
-- The block's `STA DELAY2 <- 15` is followed in the SAME hook by handle()'s `DEC DELAY2`, and a 6502 read-modify-write
-- first writes back the UNMODIFIED byte (a dummy write of 15) -- so count a 15 only when the previous write wasn't 15.
local frame, edges, edge_frames, lastw = 0, 0, {}, -1
emu.addMemoryCallback(function(addr, value)
  if value == 15 and lastw ~= 15 then edges = edges + 1; edge_frames[#edge_frames + 1] = frame end
  lastw = value
end, emu.callbackType.write, 0x615F)

local last = {}; local logged_edges = 0; local inits = 0; local last_pc = nil; local plays = 0
local force_state = "wait"; local force_lock_y = nil
local FORCE_AT, forced_at, nforce = {}, {}, 0
for v in string.gmatch(os.getenv("DRQA_FORCE_AT") or "4,9,14", "%d+") do FORCE_AT[tonumber(v)] = true end
logf(string.format("probe %s loaded: latency=%d force_at=%s maxf=%d", TAG, p2.latency, os.getenv("DRQA_FORCE_AT") or "4,9,14", MAXF))

emu.addEventCallback(function()
  frame = frame + 1
  local mode, y, pc, na, x, rot = rd(0x46), rd(0x0386), rd(0x03A7), rd(0x0397), rd(0x0385), rd(0x03A5)
  while logged_edges < edges do
    logged_edges = logged_edges + 1
    logf(string.format("E %d", edge_frames[logged_edges]))
  end
  if mode ~= last.mode or y ~= last.y or pc ~= last.pc or na ~= last.na then
    logf(string.format("S %d %d %d %d %d %d %d", frame, mode, y, pc, na, x, rot))
    -- level init = the pill counter jumps (reset + generateNextPill x2) instead of the throw's +1, no capsule live
    if last.pc ~= nil and pc ~= last.pc and na ~= 0 and pc ~= (last.pc + 1) % 128 then inits = inits + 1; logf("INIT " .. inits .. " at " .. frame .. " pc " .. last.pc .. "->" .. pc) end
  end
  -- ---- FORCE state machine ----
  -- The driver itself will NOT steer onto a zero-fall landing (DRDISTGATE clamps a target whose span has no empty row
  -- below the capsule), so the Y=$0F off-spawn lock is created directly: at the spawn frame, cols 0-1 are filled from
  -- row 1 down (row 0 free) and the capsule is TELEPORTED to X=0 at Y=$0F (no Y change -> no spurious edge). Its first
  -- gravity tick then locks it at Y=$0F off the spawn cells. The pill AFTER it is the one under test.
  if force_state == "wait" and FORCE_AT[inits] and not forced_at[inits] and mode == 4 and na == 0 and last.na ~= 0 and y == 15 then
    forced_at[inits] = true; force_state = "active"; force.active = true; nforce = nforce + 1
    for r = 0, 15 do for c = 0, 1 do force.saved[r * 8 + c] = rd(0x0500 + r * 8 + c) end end
    wr(0x0500 + 0, 0xFF); wr(0x0500 + 1, 0xFF)
    for r = 1, 15 do wr(0x0500 + r * 8 + 0, 0x60); wr(0x0500 + r * 8 + 1, 0x70) end
    wr(0x0385, 0)
    logf(string.format("F%d start %d x=%d->0 y=%d pc=%d", nforce, frame, x, y, pc))
  end
  if force_state == "active" then
    if na ~= 0 and last.na == 0 then                  -- it locked
      force_lock_y = y; force_state = "locked"; force.active = false
      logf(string.format("F%d locked %d x=%d y=%d rot=%d (Y=$0F off-spawn lock %s)", nforce, frame, last.x or -1, y,
                         last.rot or -1, (y == 15 and (last.x or 9) <= 1) and "OK" or "NOT ACHIEVED"))
      for r = 1, 15 do for c = 0, 1 do wr(0x0500 + r * 8 + c, force.saved[r * 8 + c] or 0xFF) end end
    end
  end
  if force_state == "locked" and na == 0 and last.na ~= 0 then
    force_state = "wait"; logf(string.format("F%d next-pill live %d y=%d pc=%d", nforce, frame, y, pc))
  end
  last = { mode = mode, y = y, pc = pc, na = na, x = x, rot = rot }
  if frame >= MAXF then
    logf(string.format("SUMMARY frames=%d edges=%d inits=%d goes=%d dones=%d forced=%d last_force_lock_y=%s",
                       frame, edges, inits, p2.goes, p2.dones, nforce, tostring(force_lock_y)))
    logf("DONE"); lf:close(); pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
