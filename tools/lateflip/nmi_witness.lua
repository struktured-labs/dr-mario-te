-- nmi_witness.lua -- NMI cycle census on a REAL cart run + driver-path witnesses per hook (PR #30 census review).
--
-- Per NMI (game NMI handler $8005 .. its RTI $8035, both in the BASE bank; Dr. Mario's NMI = PHA/TXA/PHA/TYA/PHA,
-- JSRs, PLA/TAY/PLA/TAX/PLA, RTI -- disassembled from the cart, bank 0):
--   total = cycles(exec RTI) - cycles(exec $8005) + 6 (RTI) + 7 (interrupt entry)   <- vs the 29,780-cycle frame
--   h1/h2 = wrapper entry $FF54 .. wrapper RTS $FFC3 (or the BUSY-bail RTS $FF7C), hook 1 and hook 2
--   game share = total - h1 - h2 (pre / mid / post+13 maxima too): what census.py charges as GAME_HEAD 2040 + eps 300
-- NESTED: an NMI entry while the previous one has not reached its RTI = a real overrun, counted directly.
-- Witnesses (exec callbacks, BANK-QUALIFIED: the driver bank reads $40 at $A02E, the base bank $00 -- exec callbacks
-- are bank-blind): lg_gate / lg_live / lg_done / every DRPRESPIPE phase entry / pp_disp / pt_edge / pt_commit / h2_cp.
-- A hook that dispatched a NON-committing phase AND ran lg_gate/lg_live/lg_done is a direct refutation of the
-- census's lg cut and is logged as REFUTE.
-- Optional garbage pokes (LN_POKE_EVERY > 0): write attackColors $0329-$032C + p1_attackSize $0318 during play (the
-- probe_prespipe_force.lua method) so the ROM's own checkReleaseAttack drops a volley on P2 and the DRPRESTART
-- pipeline actually runs -- without it a lateflip replay has NO release edges and no phase ever executes.
-- Env: LN_ADDRS (lua table from tools/lateflip/nmi_addrs.py), LN_OUT (dir/), LN_TAG, LN_POKE_EVERY, LN_POKE_SIZE,
--      LN_THRESH (log every NMI above this many cycles, default 24000).
local OUTD = os.getenv("LN_OUT") or error("LN_OUT"); if OUTD:sub(-1) ~= "/" then OUTD = OUTD .. "/" end
local TAGN = os.getenv("LN_TAG") or "nmi"
local A = dofile(os.getenv("LN_ADDRS") or error("LN_ADDRS"))
local POKE_EVERY = tonumber(os.getenv("LN_POKE_EVERY") or "0")
local POKE_SIZE = tonumber(os.getenv("LN_POKE_SIZE") or "4")
local THRESH = tonumber(os.getenv("LN_THRESH") or "24000")
local BUDGET = 29780
local NMI_ENTRY, NMI_RTI = 0x8005, 0x8035
local WRAP_ENTRY, WRAP_BAIL, WRAP_RTS = 0xFF54, 0xFF7C, 0xFFC3
local MEM = emu.memType.nesMemory
local function rd(a) return emu.read(a, MEM, false) end
local function drv() return rd(0xA02E) == 0x40 end
local function cyc() local ok, st = pcall(emu.getState); if ok and st then return st["cpu.cycleCount"] end end
local wf = io.open(OUTD .. "nmi_" .. TAGN .. ".log", "w")
local function wlog(s) wf:write(s .. "\n"); wf:flush() end

-- witness bits
local BIT = { lg_gate = 1, lg_live = 2, lg_done = 4, pp_disp = 8, pt_edge = 16, pt_commit = 32, h2_cp = 64,
              ph_nc = 128, ph_c = 256 }
local nph = #A.phases
local phase_of = {}
for i, p in ipairs(A.phases) do phase_of[A.addr[p]] = i end

local frame = 0
local in_nmi, c_entry, hook_i, c_hook = false, nil, 0, nil
local hk = { 0, 0, 0 }              -- witness bits per hook of the current NMI (index 3 = >2 hooks, should not happen)
local hcyc = { 0, 0 }
local st = { nmis = 0, max = 0, max_f = -1, max_h1 = 0, max_h2 = 0, over = 0, nested = 0, hooks_gt2 = 0,
             maxh = 0, maxh_bits = 0, refute = 0, phase_hooks = 0, nc_hooks = 0, lg_hooks = 0, abort_hooks = 0,
             frame_ph_lg = 0, frame_nc_lg = 0, pair_max = {}, hist = { 0, 0, 0, 0, 0, 0 }, pokes = 0, edges = 0,
             commits = 0, absorbed = 0, maxsum_ph = 0, max_pre = 0, max_mid = 0, max_post = 0, max_head = 0, max_head_f = -1, max_head_play = 0,
             max_head_play_f = -1, max_total_play = 0 }
local c_end = { 0, 0 }              -- cycle at each hook's RTS (for the game's own share of the NMI)

local function bits_str(b)
  local t = {}
  for k, v in pairs(BIT) do if b & v ~= 0 then t[#t + 1] = k end end
  table.sort(t); return table.concat(t, "+")
end

local function finish(c_rti)
  local total = c_rti - c_entry + 13
  st.nmis = st.nmis + 1
  local b1, b2 = hk[1], hk[2]
  if total > st.max then
    st.max, st.max_f, st.max_h1, st.max_h2 = total, frame, hcyc[1], hcyc[2]
    wlog(string.format("NMIMAX f=%d total=%d h1=%d h2=%d bits1=%s bits2=%s mode=%02X", frame, total, hcyc[1],
      hcyc[2], bits_str(b1), bits_str(b2), rd(0x46)))
  end
  local hb = total < 12000 and 1 or total < 16000 and 2 or total < 20000 and 3 or total < 24000 and 4
             or total < BUDGET and 5 or 6
  st.hist[hb] = st.hist[hb] + 1
  if total >= BUDGET then st.over = st.over + 1 end
  if total >= THRESH then
    wlog(string.format("BIGNMI f=%d total=%d h1=%d h2=%d bits1=%s bits2=%s", frame, total, hcyc[1], hcyc[2],
      bits_str(b1), bits_str(b2)))
  end
  local anyph = ((b1 | b2) & (BIT.ph_nc | BIT.ph_c)) ~= 0
  local anylg = ((b1 | b2) & (BIT.lg_gate | BIT.lg_live | BIT.lg_done)) ~= 0
  if anyph and anylg then st.frame_ph_lg = st.frame_ph_lg + 1 end
  if ((b1 | b2) & BIT.ph_nc) ~= 0 and anylg then
    st.frame_nc_lg = st.frame_nc_lg + 1
    wlog(string.format("NC_LG_FRAME f=%d total=%d bits1=%s bits2=%s", frame, total, bits_str(b1), bits_str(b2)))
  end
  if anyph and total > st.maxsum_ph then st.maxsum_ph = total end
  if hook_i == 2 then               -- the game's own share: everything but the two hook bodies (census GAME_HEAD+eps)
    local head = total - hcyc[1] - hcyc[2]
    if head > st.max_head then st.max_head, st.max_head_f = head, frame end
    if rd(0x46) == 4 then
      if head > st.max_head_play then st.max_head_play, st.max_head_play_f = head, frame end
      if total > st.max_total_play then st.max_total_play = total end
    end
    local post = c_rti - c_end[2] + 13
    if post > st.max_post then st.max_post = post end
  end
  for i = 1, 3 do hk[i] = 0 end
  hcyc[1], hcyc[2] = 0, 0
  hook_i = 0
end

emu.addMemoryCallback(function()
  if drv() then return end
  local c = cyc(); if not c then return end
  if in_nmi then
    st.nested = st.nested + 1
    wlog(string.format("NESTED f=%d (NMI entered before the previous NMI's RTI; %d cycles in)", frame, c - c_entry))
  end
  in_nmi, c_entry, hook_i = true, c, 0
end, emu.callbackType.exec, NMI_ENTRY)

emu.addMemoryCallback(function()
  if drv() or not in_nmi then return end
  local c = cyc(); if not c then return end
  finish(c); in_nmi = false
end, emu.callbackType.exec, NMI_RTI)

-- DRRTIVEC shield: the DRIVER bank's NMI vector is $CEEC, which RTIs an NMI that lands while a hook has the driver
-- bank mapped (an overrun the game then never sees as a frame). Count those directly (probe_nmi126's witness).
emu.addMemoryCallback(function()
  if not drv() then return end
  st.absorbed = st.absorbed + 1
  if st.absorbed <= 20 then wlog(string.format("ABSORB f=%d hook=%d (NMI landed inside a hook: overrun)", frame, hook_i)) end
end, emu.callbackType.exec, 0xCEEC)

emu.addMemoryCallback(function()
  hook_i = hook_i + 1
  if hook_i > 2 then st.hooks_gt2 = st.hooks_gt2 + 1 end
  c_hook = cyc()
  if c_hook and in_nmi then
    if hook_i == 1 and c_hook - c_entry > st.max_pre then st.max_pre = c_hook - c_entry end
    if hook_i == 2 and c_hook - c_end[1] > st.max_mid then st.max_mid = c_hook - c_end[1] end
  end
end, emu.callbackType.exec, WRAP_ENTRY)

local function hook_end()
  local c = cyc(); if not c or not c_hook then return end
  local i = math.min(hook_i, 3)
  local d = c - c_hook
  if i <= 2 then hcyc[i] = d; c_end[i] = c end
  local b = hk[i]
  if d > st.maxh then st.maxh, st.maxh_bits = d, b end
  local isph = (b & (BIT.ph_nc | BIT.ph_c)) ~= 0
  local islg = (b & (BIT.lg_gate | BIT.lg_live | BIT.lg_done)) ~= 0
  if isph then st.phase_hooks = st.phase_hooks + 1 end
  if (b & BIT.ph_nc) ~= 0 then st.nc_hooks = st.nc_hooks + 1 end
  if islg then st.lg_hooks = st.lg_hooks + 1 end
  if (b & BIT.pp_disp) ~= 0 and not isph then st.abort_hooks = st.abort_hooks + 1 end
  if (b & BIT.pt_commit) ~= 0 then st.commits = st.commits + 1 end
  if (b & BIT.ph_nc) ~= 0 and (b & (BIT.lg_gate | BIT.lg_live | BIT.lg_done)) ~= 0 then
    st.refute = st.refute + 1
    wlog(string.format("REFUTE f=%d hook=%d cycles=%d bits=%s  (non-committing phase + lateguard in ONE hook)",
      frame, i, d, bits_str(b)))
  end
end
emu.addMemoryCallback(hook_end, emu.callbackType.exec, WRAP_RTS)
emu.addMemoryCallback(hook_end, emu.callbackType.exec, WRAP_BAIL)

local function mark(bit)
  return function()
    if not drv() then return end
    local i = math.min(math.max(hook_i, 1), 3)
    hk[i] = hk[i] | bit
  end
end
for name, bit in pairs(BIT) do
  if A.addr[name] then emu.addMemoryCallback(mark(bit), emu.callbackType.exec, A.addr[name]) end
end
for i, p in ipairs(A.phases) do
  emu.addMemoryCallback(mark(i < nph and BIT.ph_nc or BIT.ph_c), emu.callbackType.exec, A.addr[p])
end

-- release-edge counter (the pipeline only runs after one) + optional pokes
local atk_prev = 0
emu.addMemoryCallback(function(addr, value)
  if value == 0 and atk_prev ~= 0 then st.edges = st.edges + 1 end
  atk_prev = value
end, emu.callbackType.write, 0x0318, 0x0318)
local last_poke = -100000
local play_f = 0
emu.addEventCallback(function()
  frame = frame + 1
  if rd(0x46) == 4 then play_f = play_f + 1 else play_f = 0 end
  -- poke only while P2's capsule is FALLING ($0397 == 0) and 120+ frames into a match: the ROM then releases the
  -- volley at P2's next lock, its natural point (a poke at the first play frame wedged P2 in nextAction 1)
  if POKE_EVERY > 0 and play_f >= 120 and rd(0x0397) == 0 and rd(0x0318) == 0 and frame - last_poke >= POKE_EVERY then
    local ok = pcall(function()
      for k = 0, 3 do emu.write(0x0329 + k, (st.pokes + k) % 3, MEM) end
      emu.write(0x0318, POKE_SIZE, MEM)
    end)
    if ok then st.pokes = st.pokes + 1; last_poke = frame end
  end
  if frame % 3000 == 0 then NMIW_summary("TICK") end
end, emu.eventType.endFrame)

function NMIW_summary(kind)
  wlog(string.format(
    "%s tag=%s frames=%d nmis=%d max=%d@f%d (h1=%d h2=%d) over29780=%d nested=%d shield_absorbed=%d hooks_gt2=%d maxhook=%d[%s] "
    .. "hist(<12k,<16k,<20k,<24k,<29780,>=)=%d,%d,%d,%d,%d,%d phase_hooks=%d nc_phase_hooks=%d lg_hooks=%d "
    .. "abort_hooks=%d commits=%d frames_phase&lg=%d frames_ncphase&lg=%d REFUTE_same_hook=%d max_nmi_with_phase=%d "
    .. "release_edges=%d pokes=%d game_share(max pre=%d mid=%d post+13=%d head=total-h1-h2=%d@f%d; in play: head=%d@f%d total=%d)", kind, TAGN, frame, st.nmis, st.max, st.max_f, st.max_h1, st.max_h2, st.over,
    st.nested, st.absorbed, st.hooks_gt2, st.maxh, bits_str(st.maxh_bits), st.hist[1], st.hist[2], st.hist[3], st.hist[4],
    st.hist[5], st.hist[6], st.phase_hooks, st.nc_hooks, st.lg_hooks, st.abort_hooks, st.commits, st.frame_ph_lg,
    st.frame_nc_lg, st.refute, st.maxsum_ph, st.edges, st.pokes, st.max_pre, st.max_mid, st.max_post, st.max_head,
    st.max_head_f, st.max_head_play, st.max_head_play_f, st.max_total_play))
end

wlog(string.format("nmi_witness loaded tag=%s phases=%d poke_every=%d size=%d", TAGN, nph, POKE_EVERY, POKE_SIZE))
