-- PER-DESCRIPTOR CORRECTNESS TEST, v2, built on the PROVEN copro_emu.lua.
-- ⚠ v1 silently produced nothing because its memory callbacks called emu.getState() --
-- the banked Mesen quirk is "NO emu.* inside memory callbacks" (dr-mario-mesen-copro-harness).
-- Here EVERY emu.* call lives in the endFrame event callback; memory callbacks only return
-- values precomputed there.
--
-- NOT a rate test: the guard is a DETERMINISTIC PREDICATE over (board, descriptor), so each
-- published descriptor is one EXACT evaluation. n cases = n tests, never vacuous.
local OUT = os.getenv("PT_OUT") or "./pred2.log"
local lf = io.open(OUT, "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local EMU = dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
local W = 0x5200
local TUCK_C2, TUCK_R2, TGT_C2 = 0x6179, 0x617A, 0x6152

-- descriptor published to the cart; recomputed ONLY in the frame callback
local pubA, pubR = 0xFF, 0xFF
emu.addMemoryCallback(function() return pubA end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return pubR end, emu.callbackType.read, W + 0x88)
local s = EMU.attach{ window=W, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }

local function filled(b,r,c) local v=b[r*8+c]; return v~=0xFF and v~=0x00 end
local function readboard() local b={} for i=0,127 do b[i]=rd(0x0500+i) end return b end
local function find_tuck(b)
  for f=0,7 do
    local seen=false
    for r=0,13 do
      if filled(b,r,f) then seen=true
      elseif seen and not filled(b,r+1,f) and not filled(b,r+2,f) then
        for _,a in ipairs({f-1,f+1}) do
          if a>=0 and a<=7 then
            local clear=true
            for rr=0,r do if filled(b,rr,a) then clear=false; break end end
            if clear then return f,a,r end
          end
        end
      end
    end
  end
end

local frame, cases, armed, pend, discarded = 0, 0, nil, 0, 0
emu.addEventCallback(function()
  frame = frame + 1
  if rd(0x46) ~= 4 then return end
  -- republish a descriptor every 30 frames so the guard is exercised repeatedly
  if frame % 10 == 0 and not armed then
    local b = readboard()
    local f,a,rt = find_tuck(b)
    if f then
      pubA, pubR = a, 15-rt
      local hex={} for i=0,127 do hex[#hex+1]=string.format("%02X",b[i]) end
      armed = {a=a, f=f, rt=rt, board=table.concat(hex)}
      pend = frame
    end
  end
  -- 8 frames later the driver has adopted and the guard has run: record the DECISION
  if armed and frame - pend >= 6 then
    -- ⚠ STALE-BOARD GUARD: the board the GUARD evaluated must be the board we LOG. v2 logged
    -- at publication and read the decision 6-8 frames later, during which the capsule falls and
    -- can lock -- so a boundary case (have == need) could flip for reasons that are not the
    -- cart's. Re-read here and DISCARD any case whose board moved.
    local b2 = readboard()
    local hex2 = {}
    for i = 0, 127 do hex2[#hex2+1] = string.format("%02X", b2[i]) end
    local now = table.concat(hex2)
    local c2 = rd(TUCK_C2)
    if now ~= armed.board then
      discarded = discarded + 1
      logf(string.format("DISCARD approach=%d final=%d trow=%d -- board changed between publish and decision",
        armed.a, armed.f, armed.rt))
    else
      cases = cases + 1
      logf(string.format("CASE %03d approach=%d final=%d trow_board=%d cart_TUCK_C2=%02X verdict=%s board=%s",
        cases, armed.a, armed.f, armed.rt, c2, (c2==0xFF) and "VETOED" or "ALLOWED", armed.board))
    end
    armed = nil; pubA, pubR = 0xFF, 0xFF
  end
  if frame >= tonumber(os.getenv("PT_MAXF") or "12000") then
    logf(string.format("SUMMARY cases=%d discarded=%d", cases, discarded)); logf("DONE")
    if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
