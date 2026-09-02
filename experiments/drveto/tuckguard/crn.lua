-- CRN CONTROL + measurement harness for the DRTUCKGUARD A/B.
-- ⚠ THE WHOLE PAIRED DESIGN RESTS ON CRN WORKING, AND THAT IS WHAT THIS FILE PROVES FIRST.
-- Established from the emitter (not a banked note): DRSEED=1's tie-break jitter is SEED-DERIVED
-- -- it mixes SEED1/SEED2 nibbles into the copro request ($6167/$6168, emitter L2558-2562,
-- L2993-2999) -- NOT frame- or hook-derived. So forcing the seeds forces the jitter too.
local CFG = dofile("/home/struktured/projects/dr-mario-rl/tmp/tuckguard/cfg.lua")
local lf = io.open(CFG.out, "w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local function wr(a,v) emu.write(a, v, NES, false) end
local EMU = dofile("/mnt/data/drmario/pocket-copro/mesen_copro_qa/copro_emu.lua")
local s = EMU.attach{ window=0x5200, board_src=0x0500, colA=0x0381, colB=0x0382, latency=24 }
local SEED1,SEED2 = 0x6167,0x6168
local TUCK_C2,TUCK_R2,TGT_C2 = 0x6179,0x617A,0x6152
local VC2, PILLY2 = 0x03A4, 0x0386

local frame,seeded,prevMode = 0,false,-1
local layout_fp, plies, pills = nil, {}, 0
local lastY, engaged, stranded = 255, 0, 0

local function board_fp(base)   -- fingerprint of the dealt layout
  local h = 0
  for i=0,127 do h = (h*31 + rd(base+i)) % 4294967291 end
  return h
end

emu.addEventCallback(function()
  frame = frame + 1
  local mode = rd(0x46)
  if mode == 4 then
    if not seeded then
      -- FORCE THE SEED: overwrite immediately after the cart's own first-play-frame write.
      wr(SEED1, CFG.seed % 256); wr(SEED2, (CFG.seed ~ 0xA4) % 256)
      seeded = true
      layout_fp = board_fp(0x0500)
      logf(string.format("SEEDED seed=%d s1=%02X s2=%02X layout_fp=%d", CFG.seed, rd(SEED1), rd(SEED2), layout_fp))
    end
    -- placement record: on each pill lock (Y resets upward), log the descriptor + final column
    local y = rd(PILLY2)
    if y > lastY + 4 then            -- new pill spawned (Y counts up from floor)
      local tc, tg = rd(TUCK_C2), rd(TGT_C2)
      pills = pills + 1
      plies[#plies+1] = string.format("%d:%02X:%02X", pills, tc, tg)
      if tc ~= 0xFF then
        engaged = engaged + 1
        if tg ~= 0xFF and tc == tg then stranded = stranded + 1 end
      end
    end
    lastY = y
  end
  if prevMode == 4 and mode ~= 4 then
    logf(string.format("MATCHEND frame=%d pills=%d vc2=%02X engaged=%d stranded=%d", frame, pills, rd(VC2), engaged, stranded))
  end
  prevMode = mode
  if frame >= CFG.maxframes then
    logf("PLIES "..table.concat(plies, ","))
    logf(string.format("SUMMARY seed=%d layout_fp=%s pills=%d engaged=%d stranded=%d",
      CFG.seed, tostring(layout_fp), pills, engaged, stranded))
    logf("DONE"); if lf then lf:close(); lf=nil end; pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
