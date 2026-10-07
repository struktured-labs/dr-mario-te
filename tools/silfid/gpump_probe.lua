-- gpump_probe.lua (silfid lane 2026-10-07): FREE-RUNNING mechanics check of the PUBLOG capture #2 cart
-- (DRP1HOLD + DRGPUMP + DRPUBLOG on the cvcp2 seat) in Mesen. No cases: the cart autonavigates into VS and plays.
-- The P2 copro ($5200 window) is a STAND-IN brain (this run checks the cart's mechanics, not the copro): at GO it
-- takes the uploaded board, publishes the LOWEST column, vertical (orient4 1), PUB_F frames after GO, and DONE at DONE_F.
-- Measured, one line per event + a STAT line every 600 frames + SUMMARY:
--   P1 HOLD   P1's capsule Y ($0306), X ($0305) and pill counter ($0327): any change during play is a HOLD violation
--             (after the round-start throw settles).
--   PUMP      $0318 0 -> n deliveries (size n, colours $0329-$032C), n -> 0 releases, the cart's GP_N / GP_C telemetry,
--             play frames -> volleys per play-minute.
--   ROUNDS    mode $46 leaving 4: P2 virus count at the end (0 = P2 cleared, > 0 = P2 topped out; P1 cannot win).
--   P2 BOARD  max column height + virus count at every P2 GO (the capture's CELL definition).
--   RING      PRG-RAM $6600-$7FFF dumped at the end (decode with tools/silfid/publog.py).
-- Env: LF_OUT LF_TAG LF_MAXF (run_probe.sh's names; LF_CASES is ignored), GP_PUB_F (2), GP_DONE_F (24).
local OUT = os.getenv("LF_OUT") or error("LF_OUT"); if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local TAG = os.getenv("LF_TAG") or "gpump"
local MAXF = tonumber(os.getenv("LF_MAXF") or "36000")
local PUB_F = tonumber(os.getenv("GP_PUB_F") or "2")
local DONE_F = tonumber(os.getenv("GP_DONE_F") or "24")
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local lf = io.open(OUT .. "lateflip_" .. TAG .. ".log", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end

local W = 0x5200
local fcount = 0
local up = {}
local sh = { go_f = -1000, col = 3, goes = 0, dones = 0, searching = false }
emu.addMemoryCallback(function(addr, value) up[addr - W] = value end, emu.callbackType.write, W, W + 0x83)
local golog = {}
emu.addMemoryCallback(function(addr, value)
  -- stand-in brain: the lowest column (ties -> leftmost), vertical
  local best, bh = 0, 99
  for c = 0, 7 do
    local h = 0
    for r = 0, 15 do
      local v = up[r * 8 + c] or 0xFF
      if v ~= 0xFF and v ~= 0x00 then h = 16 - r; break end
    end
    if h < bh then best, bh = c, h end
  end
  sh.col = best; sh.go_f = fcount; sh.goes = sh.goes + 1; sh.searching = true
  golog[#golog + 1] = string.format("GO n=%d f=%d col=%d h=%d", sh.goes, fcount, best, bh)
end, emu.callbackType.write, W + 0x84)
emu.addMemoryCallback(function()
  local k = fcount - sh.go_f
  if sh.searching and k >= DONE_F then sh.searching = false; sh.dones = sh.dones + 1 end
  return sh.searching and 0 or 1
end, emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(function()
  if fcount - sh.go_f >= PUB_F then return sh.col end; return 0
end, emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(function()
  if fcount - sh.go_f >= PUB_F then return 1 end; return 0xFF
end, emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(function() return 0xFF end, emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(function() return 0 end, emu.callbackType.read, W + 0x88)

local function bcd(b) return math.floor(b / 16) * 10 + b % 16 end
local function p2maxh()
  local h = 0
  for c = 0, 7 do
    for r = 0, 15 do
      local v = rd(0x0500 + r * 8 + c)
      if v ~= 0xFF and v ~= 0x00 then if 16 - r > h then h = 16 - r end; break end
    end
  end
  return h
end

local st = { p2atk_max = 0, p2atk_nz = 0, esc_inj_live = 0, play_f = 0, rounds = 0, p2_clear = 0, p2_top = 0, deliv = 0, deliv_cells = 0, rel = 0, hold_viol = 0,
             spawns = 0, cell = 0, le20 = 0, maxh_hist = {} }
local last_mode, last_atk, p1 = -1, 0, nil
local last_inj, last_live = nil, false
local in_round_f = 0
logf(string.format("gpump probe %s maxf=%d pub_f=%d done_f=%d", TAG, MAXF, PUB_F, DONE_F))
emu.addEventCallback(function()
  fcount = fcount + 1
  if #golog > 0 then for i = 1, #golog do logf(golog[i]) end; golog = {} end
  local mode = rd(0x46)
  if mode == 4 and rd(0x04) ~= 0 then
    st.play_f = st.play_f + 1; in_round_f = in_round_f + 1
    -- P1 hold: after the round-start throw (60 frames), P1's capsule must not move or lock
    local cur = { y = rd(0x0306), x = rd(0x0305), pc = rd(0x0327) }
    if in_round_f > 60 and p1 ~= nil and (cur.y ~= p1.y or cur.x ~= p1.x or cur.pc ~= p1.pc) then
      st.hold_viol = st.hold_viol + 1
      if st.hold_viol <= 5 then
        logf(string.format("HOLD_VIOLATION f=%d y %d->%d x %d->%d pc %d->%d", fcount, p1.y, cur.y, p1.x, cur.x, p1.pc, cur.pc))
      end
    end
    p1 = cur
    -- DRP1DRAIN: P2's outgoing attack $0398; DRNAVESC_NOPLAY: no escape START ($614B count) inside a live round
    local pa = rd(0x0398)
    if pa > st.p2atk_max then st.p2atk_max = pa end
    if pa ~= 0 then st.p2atk_nz = st.p2atk_nz + 1 end
    -- the pump: deliveries into an empty slot, releases by P2's checkReleaseAttack
    local atk = rd(0x0318)
    if atk ~= 0 and last_atk == 0 then
      st.deliv = st.deliv + 1; st.deliv_cells = st.deliv_cells + atk
      logf(string.format("DELIVER f=%d size=%d colours=%d,%d,%d,%d p2vir=%d", fcount, atk, rd(0x0329), rd(0x032A),
        rd(0x032B), rd(0x032C), bcd(rd(0x03A4))))
    elseif atk == 0 and last_atk ~= 0 then
      st.rel = st.rel + 1
    end
    last_atk = atk
  end
  -- DRNAVESC_NOPLAY: the inject counter $614B (shared with the menu autonav) must not move between two consecutive
  -- LIVE-round frames (mode 4, $04 != 0, P2 viruses != 0); menu / round-end presses happen outside such pairs
  local inj, live_now = rd(0x614B), (mode == 4 and rd(0x04) ~= 0 and rd(0x03A4) ~= 0)
  if live_now and last_live and last_inj ~= nil and inj ~= last_inj then
    st.esc_inj_live = st.esc_inj_live + 1
    logf(string.format("INJECT_IN_LIVE_ROUND f=%d count %d->%d", fcount, last_inj, inj))
  end
  last_inj, last_live = inj, live_now
  if last_mode == 4 and mode ~= 4 then
    local v = bcd(rd(0x03A4))
    st.rounds = st.rounds + 1
    if v == 0 then st.p2_clear = st.p2_clear + 1 else st.p2_top = st.p2_top + 1 end
    logf(string.format("ROUND_END n=%d f=%d p2vir=%d round_frames=%d", st.rounds, fcount, v, in_round_f))
    in_round_f = 0; p1 = nil
  end
  last_mode = mode
  if fcount % 600 == 0 then
    logf(string.format("STAT f=%d play_f=%d rounds=%d deliveries=%d releases=%d GP_N=%d GP_C=%d hold_viol=%d goes=%d",
      fcount, st.play_f, st.rounds, st.deliv, st.rel, rd(0x6633) + 256 * rd(0x6634), rd(0x6635) + 256 * rd(0x6636),
      st.hold_viol, sh.goes))
  end
  if fcount >= MAXF then
    local fh = io.open(OUT .. "ring.bin", "wb")
    local t = {}
    for a2 = 0x6000, 0x7FFF do t[#t + 1] = string.char(rd(a2)) end
    fh:write(table.concat(t)); fh:close()
    local gn, gc = rd(0x6633) + 256 * rd(0x6634), rd(0x6635) + 256 * rd(0x6636)
    local rate = st.play_f > 0 and st.deliv / (st.play_f / 60.0988 / 60) or 0
    logf(string.format("SUMMARY tag=%s frames=%d play_f=%d rounds=%d p2_clear=%d p2_topout=%d deliveries=%d cells=%d releases=%d GP_N=%d GP_C=%d rate_per_play_min=%.2f hold_violations=%d goes=%d dones=%d p2atk_max=%d p2atk_nonzero_frames=%d esc_inject_live=%d",
      TAG, fcount, st.play_f, st.rounds, st.p2_clear, st.p2_top, st.deliv, st.deliv_cells, st.rel, gn, gc, rate,
      st.hold_viol, sh.goes, sh.dones, st.p2atk_max, st.p2atk_nz, st.esc_inj_live))
    logf("DONE"); lf:close(); pcall(function() emu.stop(0) end)
  end
end, emu.eventType.endFrame)
