-- publog_probe.lua (silfid lane 2026-10-06: + GO upload bytes, periodic RAM dumps for the DRPUBLOG ring)
-- execfid_probe.lua (execfid lane 2026-10-04: lateflip_probe.lua + T-line fields sa=SLAM_ARM $6172 st=STABLE_CT2 $6171
-- pa=PRE_ACT2 $619A hv=P2 horVelocity $0393 f8=pad held $F8 lpc=$6155, and a SPAWN line per spawn)
-- lateflip_probe.lua -- reproduce couch LATE-FLIPs on the REAL couch cart in Mesen (2026-10-03).
--
-- Cart: a DRHUMAN couch cart (P1 = human seat, P2 = copro AI on the $5200 window), header remapped 100 -> 1 (MMC1).
-- The P2 copro is served from a PUBLISH TIMELINE measured on the REAL copro (Verilator co-sim of the shipped RTL +
-- firmware, tmp/pubtrace/sim_pubtrace2.cpp): every change of the live mailbox (col, orient) with its time since GO,
-- then DONE + final (col, orient) + tuck descriptor. So the cart sees exactly what silicon's copro would publish, and
-- WHEN, frame-quantised (the driver polls the mailbox 2x per frame, both inside the NMI).
--
-- Per case: at the P2 spawn (endFrame where $0386 becomes $0F) the case board is written into $0500-$057F with the
-- capsule colours ($0381/$0382), the preview ($039A/$039B), speedUps ($038A), the P2 virus count ($03A4, BCD) and
-- SEED2 ($6168) = 0, BEFORE the driver's next hook sees the new-pill edge. The cart's own upload at GO is captured
-- (pure-Lua write callbacks on $5200-$5283) and compared byte-for-byte with the timeline's upload line.
--
-- Env: LF_CASES (lua data file, see gen_cases_lua.py), LF_OUT (dir/), LF_TAG, LF_MAXF, LF_STALE (1 = the GO hook's own
-- mailbox read returns the PREVIOUS search's final answer, as the copro RAM does for ~72 CPU cycles after GO).
-- Mesen traps honoured: no emu.* inside memory callbacks; emu.write takes three args (pcall-logged).
local OUT = os.getenv("LF_OUT") or error("LF_OUT"); if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local TAG = os.getenv("LF_TAG") or "run"
local MAXF = tonumber(os.getenv("LF_MAXF") or "60000")
local STALE = (os.getenv("LF_STALE") or "0") == "1"
local DUMP_EVERY = tonumber(os.getenv("LF_DUMP_EVERY") or "0")
local DUMP_MAX = tonumber(os.getenv("LF_DUMP_MAX") or "150")
local ndump = 0
local CASES = dofile(os.getenv("LF_CASES") or error("LF_CASES"))
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local lf = io.open(OUT .. "lateflip_" .. TAG .. ".log", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end
local function wr(a, v)
  local ok, err = pcall(function() emu.write(a, v, NES) end)
  if not ok then logf("WRITE_ERR " .. string.format("%04X", a) .. " " .. tostring(err)) end
end

-- ---------------------------------------------------------------- mailbox shim (P2 window $5200)
local W = 0x5200
local fcount = 0                       -- endFrame counter (plain-Lua clock for the memory callbacks)
local sh = { mode = "idle", go_f = -1, sched = nil, prev_col = 0, prev_or = 0, goes = 0, dones = 0,
             served_col = -1, served_or = -1, served_done = 0, go_hook = false, case = nil, golog = {} }
local up = {}                          -- captured upload bytes (offsets 0..131)
emu.addMemoryCallback(function(addr, value) up[addr - W] = value end, emu.callbackType.write, W, W + 0x83)
emu.addMemoryCallback(function(addr, value)
  local prev_mode, prev_go = sh.mode, sh.go_f
  sh.goes = sh.goes + 1; sh.go_f = fcount; sh.go_hook = true; sh.mode = "search"; sh.served_done = 0
  local kind = "case"
  sh.sched = sh.pending_sched; sh.pending_sched = nil
  if sh.sched == nil and sh.prefetch ~= nil then sh.sched = sh.prefetch; sh.prefetch = nil; sh.prefetch_used = true; kind = "prefetch" end
  if sh.sched == nil then sh.sched = { filler = true, pubs = {}, done_f = 3, final = { 3, 0 }, tuck = { 255, 0 } }; kind = "FILLER" end
  local hx = {}
  for i = 0, 131 do hx[#hx + 1] = string.format("%02x", up[i] or 0) end
  sh.golog[#sh.golog + 1] = string.format("GO n=%d f=%d kind=%s preempt=%s prev_k=%d up=%s", sh.goes, fcount, kind,
    tostring(prev_mode == "search"), (prev_mode == "search") and (fcount - prev_go) or -1, table.concat(hx))
end, emu.callbackType.write, W + 0x84)

-- current published (col, orient) at elapsed frames k (sched.pubs sorted by time; t in frames since GO)
local function pub_at(k)
  local s = sh.sched
  if k >= s.done_f then return s.final[1], s.final[2], 1 end
  local c, o = nil, 0xFF
  for i = 1, #s.pubs do
    local p = s.pubs[i]
    if p[1] <= k then c, o = p[2], p[3] else break end
  end
  return (c or 0), o, 0
end
local function cur_view()
  if sh.mode ~= "search" then return sh.prev_col, sh.prev_or, 1 end
  local k = fcount - sh.go_f
  if sh.go_hook then                    -- the GO hook itself: copro RAM not yet re-initialised
    if STALE then return sh.prev_col, sh.prev_or, 0 end
    return 0, 0xFF, 0
  end
  return pub_at(k)
end
emu.addMemoryCallback(function()
  local c, o, d = cur_view()
  if d == 1 and sh.mode == "search" then
    sh.mode = "idle"; sh.dones = sh.dones + 1; sh.prev_col, sh.prev_or = sh.sched.final[1], sh.sched.final[2]
    sh.served_done = 1
  end
  return d
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function() local c, o = cur_view(); sh.served_col = c; return c end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function() local c, o = cur_view(); sh.served_or = o; return o end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function()
  if sh.sched and sh.mode == "idle" then return sh.sched.tuck[1] end; return 0xFF
end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function()
  if sh.sched and sh.mode == "idle" then return sh.sched.tuck[2] end; return 0
end, emu.callbackType.read, W + 0x88)
-- the hook that GOes is over once the driver writes LASTY2 in the NEXT hook (dispatch writes it every play hook)
emu.addMemoryCallback(function() sh.go_hook = false end, emu.callbackType.write, 0x6155)

-- ---------------------------------------------------------------- P1 menu navigation (human seat)
local cur_in, untl = nil, -1
emu.addEventCallback(function() if cur_in and fcount < untl then emu.setInput(cur_in, 0) end end, emu.eventType.inputPolled)
local function press(i, d) cur_in = i; untl = fcount + (d or 4) end

-- ---------------------------------------------------------------- case driver
local st, ci, navN = "nav", 1, 0
local win = nil                       -- p of a garbage case whose post-lock window is being traced
local last = {}
local spawn_f, case_log, lastF6 = -1, nil, 0
local pills_in_play = 0
local function bcd(n) return math.floor(n / 10) * 16 + n % 10 end
local function inject(c)
  for i = 0, 127 do wr(0x0500 + i, c.board[i + 1]) end
  wr(0x0381, c.cur[1]); wr(0x0382, c.cur[2]); wr(0x039A, c.nxt[1]); wr(0x039B, c.nxt[2])
  wr(0x038A, c.spu); wr(0x03A4, bcd(c.vc)); wr(0x6168, 0)
  if sh.prefetch_used then sh.prefetch_used = false else sh.pending_sched = c.sched end
  sh.prefetch = nil
  for i = 0, 131 do up[i] = nil end
end
local function upload_check(c)
  local bad, first = 0, -1
  for i = 0, 131 do
    if up[i] ~= c.upload[i + 1] then bad = bad + 1; if first < 0 then first = i end end
  end
  logf(string.format("UPLOAD p%d %s bad=%d first=%d got=%s want=%s", c.p, bad == 0 and "MATCH" or "MISMATCH", bad, first,
    tostring(up[first]), tostring(c.upload[first + 1])))
end

logf(string.format("probe %s: %d cases stale=%s maxf=%d", TAG, #CASES, tostring(STALE), MAXF))
emu.addEventCallback(function()
  fcount = fcount + 1
  if #sh.golog > 0 then for i = 1, #sh.golog do logf(sh.golog[i]) end; sh.golog = {} end
  local mode = rd(0x46)
  if st == "nav" then
    if mode ~= 4 and fcount % 40 == 0 then
      navN = navN + 1
      if rd(0x0727) ~= 2 and navN % 2 == 1 then press({ down = true }, 4) else press({ start = true }, 4) end
    end
    if mode == 4 then st = "warm"; logf("PLAY at " .. fcount) end
    return
  end
  if mode ~= 4 then
    if fcount % 600 == 0 then logf("NOTPLAY f=" .. fcount .. " mode=" .. mode .. " st=" .. st) end
    if mode ~= 4 and fcount % 40 == 0 then press({ start = true }, 4) end
  end
  -- keep the idle human seat alive: P1's field is wiped every frame, so it can never top out
  for i = 0, 127 do wr(0x0400 + i, 0xFF) end
  local y, x, rot, na = rd(0x0386), rd(0x0385), rd(0x03A5), rd(0x0397)
  local spawned = (y == 15 and last.y ~= nil and last.y ~= 15)
  if spawned then pills_in_play = pills_in_play + 1
    logf(string.format("SPAWN n=%d f=%d x=%d hv=%d f8=%02X sa=%d armed=%d", pills_in_play, fcount, x, rd(0x0393), rd(0xF8), rd(0x6172), rd(0x6161)))
  end
  -- silfid: RAM dumps for the save-state co-sim validation (CPU RAM $0000-$07FF + PRG-RAM $6000-$7FFF)
  if st ~= "nav" and DUMP_EVERY > 0 and fcount % DUMP_EVERY == 0 and ndump < DUMP_MAX then
    ndump = ndump + 1
    local fh = io.open(string.format("%sdump_%06d.bin", OUT, fcount), "wb")
    local t = {}
    for a2 = 0, 0x7FF do t[#t + 1] = string.char(emu.read(a2, NES, false)) end
    for a2 = 0x6000, 0x7FFF do t[#t + 1] = string.char(emu.read(a2, NES, false)) end
    fh:write(table.concat(t)); fh:close()
  end
  -- per-frame trace while a case pill is live
  if case_log then
    local f6 = rd(0xF6)
    if y <= 15 and x <= 7 and (fcount - spawn_f) == 20 then        -- is the FALLING capsule in the field RAM?
      logf(string.format("CELL p%d f=20 y=%d x=%d rot=%d own=%02X right=%02X above=%02X", case_log.p, y, x, rot,
        rd(0x0500 + (15 - y) * 8 + x), rd(0x0500 + (15 - y) * 8 + math.min(x + 1, 7)),
        (y < 15) and rd(0x0500 + (14 - y) * 8 + x) or 0xEE))
    end
    logf(string.format("T p%d f=%d y=%d x=%d rot=%d na=%d grav=%d | tgt=%d,%d rd2=%d arm=%d pend=%d dly=%d eff=%d bud=%d fall=%d proph=%02X lg=%d,%d | pad=%02X held=%02X | mb=%d,%d,%d k=%d",
      case_log.p, fcount - spawn_f, y, x, rot, na, rd(0x0392), rd(0x6152), rd(0x6153), rd(0x616E), rd(0x6161), rd(0x614F),
      rd(0x615F), rd(0x6194), rd(0x6193), rd(0x61B2), rd(0x61C6), rd(0x61D7), rd(0x61D6), f6, rd(0xF8), sh.served_col, sh.served_or, sh.served_done,
      (sh.mode == "search") and (fcount - sh.go_f) or -1) ..
      string.format(" sa=%d st=%d pa=%d hv=%d f8=%02X lpc=%d", rd(0x6172), rd(0x6171), rd(0x619A), rd(0x0393), rd(0xF8), rd(0x6155)))
    if sh.goes > 0 and case_log.upchk == nil and sh.go_f >= spawn_f and sh.sched == case_log.sched then
      case_log.upchk = true; upload_check(case_log)
    end
    if na ~= 0 and last.na == 0 then                    -- locked this frame: the pose of the last falling frame
      local o2v = { [0] = 0, [2] = 1, [3] = 2, [1] = 3 }
      local v = o2v[last.rot]
      logf(string.format("LAND p%d f=%d x=%d y=%d rot=%d action=%d | sil=%d sim=%d cosim_final=%d",
        case_log.p, fcount - spawn_f, last.x, last.y, last.rot, v * 8 + last.x, case_log.actual, case_log.sim, case_log.fin))
      local rows = {}
      for r = 0, 15 do
        local t = {}
        for cc = 0, 7 do t[#t + 1] = string.format("%02X", rd(0x0500 + r * 8 + cc)) end
        rows[#rows + 1] = table.concat(t)
      end
      logf("BOARD p" .. case_log.p .. " " .. table.concat(rows, " "))
      case_log.landed = true
    end
    if case_log.garb and (fcount - spawn_f) == 2 then          -- P2's INCOMING volley (ROM p1_attackSize/$0329 colours)
      wr(0x0318, case_log.garb[1])
      for i = 2, #case_log.garb do wr(0x0329 + i - 2, case_log.garb[i]) end
      logf(string.format("GARB p%d f=2 size=%d", case_log.p, case_log.garb[1]))
    end
    if case_log.landed and case_log.garb and not case_log.pf and CASES[ci] then
      sh.prefetch = CASES[ci].sched; case_log.pf = true; win = case_log.p
    end
    if case_log.landed and (sh.mode == "idle" or (CASES[ci] and CASES[ci].chain)) then case_log = nil end
  end
  if win ~= nil and case_log == nil then
    if spawned then win = nil else
      logf(string.format("W after=p%d f=%d y=%d x=%d na=%d | tgt=%d,%d arm=%d pend=%d pa=%d lgc=%d lgl=%d atk=%d | mb=%d,%d,%d k=%d pre=%s",
        win, fcount, y, x, na, rd(0x6152), rd(0x6153), rd(0x6161), rd(0x614F), rd(0x619A), rd(0x61D7), rd(0x61D6), rd(0x0318),
        sh.served_col, sh.served_or, sh.served_done, (sh.mode == "search") and (fcount - sh.go_f) or -1, tostring(sh.prefetch_used)))
    end
  end
  if spawned and case_log == nil and pills_in_play >= 3 then
    local c = CASES[ci]
    if c == nil then
      logf(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d cases=%d", TAG, fcount, sh.goes, sh.dones, #CASES))
      logf("DONE"); lf:close(); pcall(function() emu.stop(0) end); return
    end
    if c.chain or sh.mode == "idle" then
      inject(c); spawn_f = fcount; case_log = c; ci = ci + 1
      logf(string.format("INJECT p%d at f=%d (y=%d x=%d rot=%d) spu=%d vc=%d sched_pubs=%d done_f=%.2f final=%d,%d",
        c.p, fcount, y, x, rot, c.spu, c.vc, #c.sched.pubs, c.sched.done_f, c.sched.final[1], c.sched.final[2]))
    end
  end
  last = { y = y, x = x, rot = rot, na = na }
  if fcount >= MAXF then
    logf(string.format("SUMMARY tag=%s frames=%d goes=%d dones=%d cases_done=%d TIMEOUT", TAG, fcount, sh.goes, sh.dones, ci - 1))
    logf("DONE"); lf:close(); pcall(function() emu.stop(1) end)
  end
end, emu.eventType.endFrame)
