-- ============================================================================
-- both_counters_2digit.lua -- close the gap format_probe.log itself flagged:
--     "VC_P2: AMBIGUOUS (<10, rerun higher)"
--
-- P1's virus counter was empirically confirmed BCD at 84 (two digits). P2's never was:
-- every observation of $03A4 to date has been < 10, and BELOW 10 BCD AND BINARY AGREE, so
-- those runs structurally cannot tell a BCD-correct render from the 48->"72" failure class.
-- The injected truth table proves the DIGIT ROUTINE over all 0..99; it cannot prove what
-- format the GAME stores, because it supplies its own input.
--
-- So: drive BOTH players to a level with >9 viruses (RIGHT on port 0 AND port 1 at the
-- level select -- each player picks their own), then assert for BOTH counters that the
-- RENDERED digits equal the BCD decode of the RAM byte, in play AND after the STUDY pause.
--
-- Sprite map (measured, study_viruscount_probe): virus P1 tens/ones = OAM slots 12/13,
-- virus P2 = 14/15; the TILE INDEX IS THE DIGIT.
-- ============================================================================
local OUT = (os and os.getenv and os.getenv("DRQA_OUT")) or "/tmp/"
if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local lf = io.open(OUT .. "both_counters_2digit.log", "w")
local function logf(s) if lf then lf:write(s .. "\n"); lf:flush() end end

local NES, OAM = emu.memType.nesMemory, emu.memType.nesSpriteRam
local function rd(a) return emu.read(a, NES, false) end
local function tile(slot) return emu.read(slot * 4 + 1, OAM, false) end

local frame, paused_at, fails, checks = 0, nil, 0, 0
local p0, p1 = {}, {}

local function nav(f)
  if f >= 120 and f < 150 then return { down = true }, {}          -- title -> 2 PLAYER
  elseif f >= 180 and f < 210 then return { start = true }, {}
  elseif f >= 240 and f < 430 then
    if (f % 12) < 4 then
      return { right = true }, { right = true }                     -- BOTH players' levels up
    end
  elseif f >= 450 and f < 490 then return { start = true }, { start = true }
  end
  return {}, {}
end

local function bcd(b) return ((b >> 4) & 0x0F) * 10 + (b & 0x0F) end

local function check(phase)
  local raw = { rd(0x0324), rd(0x03A4) }
  local shown = { tile(12) * 10 + tile(13), tile(14) * 10 + tile(15) }
  for i = 1, 2 do
    local want = bcd(raw[i])
    local two = raw[i] > 0x09
    checks = checks + 1
    local ok = (shown[i] == want)
    if not ok then fails = fails + 1 end
    logf(string.format("  %-6s P%d  byte=$%02X  BCD-decode=%2d  rendered=%2d  %s%s",
        phase, i, raw[i], want, shown[i], ok and "OK" or "*** MISMATCH ***",
        two and "  [TWO-DIGIT -- discriminating]" or "  [<10: BCD==binary, NOT discriminating]"))
    if not two then
      logf(string.format("  %-6s P%d  ^ this observation CANNOT distinguish BCD from binary",
                         phase, i))
    end
  end
  return raw
end

emu.addEventCallback(function()
  local a, b = nav(frame)
  emu.setInput(a, 0); emu.setInput(b, 1)
end, emu.eventType.inputPolled)

emu.addEventCallback(function()
  frame = frame + 1
  local mode, np = rd(0x0046), rd(0x0727)
  if mode == 0x04 and np == 2 and frame == 620 then
    logf(string.format("PLAY reached (level P1=%d P2=%d)", rd(0x0316), rd(0x0396)))
    check("play")
  end
  if mode == 0x04 and np == 2 and frame >= 680 and frame < 710 then
    emu.setInput({ start = true }, 0); paused_at = paused_at or frame
  end
  if paused_at and frame == paused_at + 70 then
    logf("STUDY pause:")
    local raw = check("study")
    local both2 = raw[1] > 0x09 and raw[2] > 0x09
    logf("")
    logf(string.format("VERDICT: %d checks, %d mismatches; BOTH counters two-digit: %s",
                       checks, fails, both2 and "YES" or "NO"))
    logf((fails == 0 and both2) and "PASS -- P2's BCD source format is now confirmed too"
         or (fails > 0 and "FAIL -- a rendered value disagrees with the BCD decode"
             or "INCONCLUSIVE -- did not reach a two-digit count on both sides"))
    emu.stop(0)
  end
  if frame == 1200 then logf("TIMEOUT before pause"); emu.stop(0) end
end, emu.eventType.endFrame)

logf("both_counters_2digit started")
