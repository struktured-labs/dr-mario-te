-- ============================================================================
-- copro_emu.lua — emulate the Dr. Mario FPGA coprocessor mailbox inside Mesen.
-- Reusable module: `local EMU = dofile(".../copro_emu.lua"); local s = EMU.attach{...}`.
--
-- WHY: the shipped cart is mapper 100 (MMC1 + a memory-mapped copro window at $5000).
-- Remap its iNES header to mapper 1 (the banking IS MMC1) so Mesen boots it; then this
-- module ANSWERS like the FPGA so the cart's driver runs and its AI places pills.
--
-- Mailbox contract (patch_cartridge_copro.py), per window base W:
--   W+$00..W+$7F  board upload (128 cells)          [driver writes; open-bus under MMC1]
--   W+$80..W+$83  colors cA,cB,previewA,previewB     [driver writes]
--   W+$84         GO on WRITE / DONE on READ (0=searching)
--   W+$85         result column 0..7   (driver reads after DONE)
--   W+$86         result orient4 0..3  (0xFF = "no result yet" sentinel for the anytime path)
--
-- MESEN QUIRKS worked around (verified empirically in this build — see README):
--   * A Lua READ callback that returns an integer OVERRIDES the byte the CPU reads — this is
--     how we answer DONE/col/orient (confirmed: the driver adopts our col+orient).
--   * !!! No emu.* API may be called INSIDE a memory callback (read/write/exec) — doing so
--     (emu.read, emu.framecount, ...) silently kills that callback so it never fires again.
--     So the callbacks touch ONLY plain Lua state: a frame counter kept in an upvalue (bumped
--     from an endFrame event handler) stands in for emu.framecount(), and the board is
--     snapshotted (emu.read) from the endFrame handler, not the GO callback. The board
--     ($0400/$0500) is stable while the searching pill is airborne, so a 1-frame-later snapshot
--     is the same board the copro saw.
--   * A RANGE write callback covering the window disables an overlapping single-address write
--     callback, and EXEC-based GO detection is unreliable (hot bank-0 address). So GO detection
--     is a single-address write callback at W+$84, and the board comes from source RAM — not from
--     shadowing the open-bus window writes.
--
-- attach{ window=0x5000, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24, brain=fn }
--   brain(board, colA, colB) -> col(0..7), orient(0..3)   [orient in copro space; driver maps it]
--   board: Lua array [0..127], row-major 8x16, 0x00/0xFF = empty (0x00 normalized to empty).
-- Returns a state handle with .goes/.dones/.board/.latency for logging.
-- ============================================================================
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end

local M = {}

-- default brain: emptiest column (fewest occupied cells), vertical (orient 0 = V, A-top)
function M.default_brain(board, colA, colB)
  local bestCol, bestFill = 0, 99
  for c = 0, 7 do
    local fill = 0
    for r = 0, 15 do local v = board[r * 8 + c]; if v ~= 0xFF and v ~= 0x00 then fill = fill + 1 end end
    if fill < bestFill then bestFill = fill; bestCol = c end
  end
  return bestCol, 0
end

function M.attach(cfg)
  local w        = cfg.window    or 0x5000
  local bsrc     = cfg.board_src or 0x0500
  local caAddr   = cfg.colA      or 0x0381
  local cbAddr   = cfg.colB      or 0x0382
  local latency  = cfg.latency   or 24
  local brain    = cfg.brain     or M.default_brain

  local s = { board = {}, done = false, go_frame = -1, rcol = 0, ror = 0xFF, pending = false,
              need_snap = false, goes = 0, dones = 0, colA = 0, colB = 0, latency = latency }
  for i = 0, 127 do s.board[i] = 0xFF end

  local curFrame = 0   -- plain-Lua stand-in for emu.framecount() (memory callbacks can't call emu.*)

  -- GO strobe: single-address write callback (reliable). Touches ONLY plain Lua state.
  emu.addMemoryCallback(function(addr, value)
    s.go_frame = curFrame; s.done = false; s.pending = true; s.need_snap = true
    s.ror = 0xFF; s.goes = s.goes + 1
  end, emu.callbackType.write, w + 0x84)

  -- DONE read: 0 while searching; 1 once latency elapses. Compute the move at that instant
  -- (pure Lua — brain touches no emu.*), before flipping DONE, so col/orient read back first.
  emu.addMemoryCallback(function(addr, value)
    if s.done then return 1 end
    if s.pending and not s.need_snap and (curFrame - s.go_frame) >= latency then
      local c, o = brain(s.board, s.colA, s.colB)
      s.rcol = c % 8; s.ror = o % 4
      s.done = true; s.pending = false; s.dones = s.dones + 1
      return 1
    end
    return 0
  end, emu.callbackType.read, w + 0x84)

  emu.addMemoryCallback(function(addr, value) return s.rcol end, emu.callbackType.read, w + 0x85)
  emu.addMemoryCallback(function(addr, value) return s.ror  end, emu.callbackType.read, w + 0x86)

  -- frame bump + board snapshot (emu.read/framecount ARE allowed in an event callback)
  emu.addEventCallback(function()
    curFrame = curFrame + 1
    if s.need_snap then
      for i = 0, 127 do local v = rd(bsrc + i); if v == 0x00 then v = 0xFF end; s.board[i] = v end
      s.colA = rd(caAddr) % 16; s.colB = rd(cbAddr) % 16
      s.need_snap = false
    end
  end, emu.eventType.endFrame)

  return s
end

return M
