-- Why does DRNAVDWELL hang autonav at the title?
-- The dwell (patch_cartridge_copro.py, an_title) counts elapsed frames like this:
--     LDA $43 ; CMP DWELL_LAST ; BEQ chk      -- same frame -> don't count
--     STA DWELL_LAST
--     LDA DWELL_CNT ; CMP #180 ; BCS chk      -- saturate
--     INC DWELL_CNT
--   chk: LDA DWELL_CNT ; CMP #180 ; BCS done  -- elapsed -> navigate
--     RTS                                     -- else keep holding
-- So it navigates ONLY once DWELL_CNT reaches 180. If $43 never changes, DWELL_CNT never
-- increments and the title holds forever -- which is the observed symptom (110+ s, not the
-- ~3 s the code comments promise).
local OUT=(os and os.getenv and os.getenv("DRQA_OUT")) or "/tmp/"
if OUT:sub(-1)~="/" then OUT=OUT.."/" end
local lf=io.open(OUT.."dwell_probe.log","w")
local function logf(s) if lf then lf:write(s.."\n"); lf:flush() end end
local NES=emu.memType.nesMemory
local function rd(a) return emu.read(a,NES,false) end
local DWELL_CNT, DWELL_LAST = 0x6177, 0x6178
local f=0
local seen43={}
emu.addEventCallback(function()
  f=f+1
  seen43[rd(0x43)]=true
  if f%60==0 and f<=900 then
    local n=0; for _ in pairs(seen43) do n=n+1 end
    logf(string.format("f%-4d $43=%02X CNT=%02X mode=%02X $0727=%d $04=%d NAV_STABLE=%02X $51=%02X",
      f, rd(0x43), rd(DWELL_CNT), rd(0x0046), rd(0x0727), rd(0x04), rd(0x6176), rd(0x51)))
  end
  if f==900 then
    local n=0; for _ in pairs(seen43) do n=n+1 end
    logf("")
    logf("VERDICT:")
    logf(string.format("  $43 took %d distinct values over 900 frames -> %s",
      n, n>1 and "IT DOES ADVANCE" or "IT NEVER CHANGES (dwell can never count)"))
    logf(string.format("  DWELL_CNT reached %d of the 180 needed -> %s",
      rd(DWELL_CNT), rd(DWELL_CNT)>=180 and "would have navigated" or "STUCK BELOW THRESHOLD"))
    if lf then lf:close() end
    emu.stop(0)
  end
end, emu.eventType.endFrame)
logf("dwell_probe started")
