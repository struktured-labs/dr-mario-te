-- base_gravity_probe.lua -- condition (c) of the settle-pin fairness check: what does the UNMODIFIED game do with a
-- capsule's gravity in the frames after it spawns? (2026-10-03, claude/settle)
--
-- ROM: the stock Dr. Mario base ROM (no driver, no AI). 2-player VS, both seats driven by this script:
--   * from the spawn until the capsule's FIRST drop: NO buttons at all for that seat (pure game gravity);
--   * after that first drop: steer to a per-pill target column (press edges) and hold DOWN, so boards stay low
--     and rounds last. None of this touches the NEXT pill's spawn-to-first-drop window, which is what is measured.
-- Measured per pill and seat at FRAME level (endFrame), the same method as settle_probe.lua's gravity trace:
--   spawn = the endFrame where pillsCounter ($0327 / $03A7) moved; speedCounter ($0312 / $0392) per frame until the
--   first drop; natural = the drop came with the counter at thr (speedCounterTable[base(speed)+speedUps]);
--   G0 = k - counter at the last frame k before the drop (frames of gravity the game did NOT count since spawn).
-- Speed/level: poked to MED / L11 on the options screen (BS_SPEED / BS_LEVEL) like a player choosing them.
-- Env: BS_OUT (dir/), BS_TAG, BS_MAXF, BS_SPEED (0/1/2), BS_LEVEL.
local OUT = os.getenv("BS_OUT") or error("BS_OUT"); if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local TAG = os.getenv("BS_TAG") or "base"
local MAXF = tonumber(os.getenv("BS_MAXF") or "60000")
local SPEED = tonumber(os.getenv("BS_SPEED") or "1")
local LEVEL = tonumber(os.getenv("BS_LEVEL") or "11")
local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local lf = io.open(OUT .. "base_" .. TAG .. ".log", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end
local cb_err = 0
local function guard(fn)
  return function(...)
    local ok, r = pcall(fn, ...)
    if not ok then cb_err = cb_err + 1; if cb_err <= 20 then logf("CBERR " .. tostring(r)) end end
    return nil
  end
end
local function wr(a, v)
  local ok, err = pcall(function() emu.write(a, v, NES) end)
  if not ok then logf(string.format("WRITE_ERR %04X %s", a, tostring(err))) end
end

local SPEED_TABLE = { [0] = 0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
  0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
  0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
  0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
  0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00 }
local SPEED_BASE = { [0] = 0x0F, 0x19, 0x1F }

local frame = 0
-- per seat: RAM base ($0300 P1 / $0380 P2), controller port
local SEATS = { { name = "P1", base = 0x0300, port = 0 }, { name = "P2", base = 0x0380, port = 1 } }
for _, s in ipairs(SEATS) do
  s.cur = nil; s.last_cnt = nil; s.dropped = true; s.target = 0; s.npill = 0
  s.g0 = {}; s.nat = {}; s.recs = 0; s.soft = 0; s.g0_by_thr = {}
end
local ORDER = { 0, 7, 1, 6, 2, 5, 3, 4, 0, 6, 1, 7, 2, 4, 3, 5 }

local function seat_frame(s, mode)
  local b = s.base
  local y, cnt, na, grav, spu, spd, x = rd(b + 0x06), rd(b + 0x27), rd(b + 0x17), rd(b + 0x12), rd(b + 0x0A), rd(b + 0x0B), rd(b + 0x05)
  if mode ~= 4 then s.cur = nil; s.last_cnt = nil; s.dropped = true; return end
  if s.last_cnt ~= nil and cnt ~= s.last_cnt then
    local thr = SPEED_TABLE[math.min(80, (SPEED_BASE[spd] or 0x19) + spu)]
    s.cur = { s = frame, y0 = y, thr = thr, trace = { grav }, na = { na }, spu = spu, spd = spd }
    s.dropped = false
    s.npill = s.npill + 1
    s.target = ORDER[(s.npill % #ORDER) + 1]
  elseif s.cur then
    local k = frame - s.cur.s
    if y < s.cur.y0 or (na ~= 0 and na ~= 3 and na ~= 6) or k > 400 then
      local c = s.cur
      local lastc = c.trace[#c.trace]
      local natural = (y < c.y0) and (lastc == c.thr)
      local g0 = (k - 1) - lastc
      s.recs = s.recs + 1
      if natural then
        s.nat[k] = (s.nat[k] or 0) + 1
        s.g0[g0] = (s.g0[g0] or 0) + 1
        local key = c.thr
        s.g0_by_thr[key] = s.g0_by_thr[key] or {}
        s.g0_by_thr[key][g0] = (s.g0_by_thr[key][g0] or 0) + 1
      else s.soft = s.soft + 1 end
      if s.recs <= 150 then
        logf(string.format("GRAV %s n=%d s=%d k_drop=%d thr=%d spu=%d spd=%d natural=%s G0=%d trace=%s na=%s", s.name,
          s.recs, c.s, k, c.thr, c.spu, c.spd, tostring(natural), g0, table.concat(c.trace, ","), table.concat(c.na, ",")))
      end
      s.cur = nil
      s.dropped = true
    else
      local c = s.cur; c.trace[#c.trace + 1] = grav; c.na[#c.na + 1] = na
    end
  end
  s.last_cnt = cnt
  s.x = x
end

-- input: nav on port 0 outside play; in play each seat idle until its pill's first drop, then steer + DOWN
local nav_in, nav_until, navN = nil, -1, 0
local function blank() return { a = false, b = false, select = false, start = false, up = false, down = false, left = false, right = false } end
emu.addEventCallback(guard(function()
  local mode = rd(0x46)
  for _, s in ipairs(SEATS) do
    local t = blank()
    if mode ~= 4 then
      if s.port == 0 and nav_in and frame < nav_until then for k, v in pairs(nav_in) do t[k] = v end end
    elseif s.dropped and s.cur == nil then
      local x = s.x or 3
      if x < s.target then t.right = (frame % 2 == 0)
      elseif x > s.target then t.left = (frame % 2 == 0)
      else t.down = true end
    end
    emu.setInput(t, 0, s.port)
  end
end), emu.eventType.inputPolled)

local modes = {}
logf(string.format("base_gravity_probe %s speed=%d level=%d maxf=%d", TAG, SPEED, LEVEL, MAXF))
emu.addEventCallback(guard(function()
  frame = frame + 1
  local mode = rd(0x46)
  modes[mode] = (modes[mode] or 0) + 1
  if mode ~= 4 then
    -- options: a player choosing L LEVEL / speed SPEED (both seats)
    if rd(0x0727) == 2 then
      wr(0x0316, LEVEL); wr(0x0396, LEVEL)
      wr(0x030B, SPEED); wr(0x038B, SPEED)
      wr(0x0734, SPEED); wr(0x0735, SPEED); wr(0x0736, SPEED); wr(0x0737, SPEED)
    end
    if frame % 40 == 0 then
      navN = navN + 1
      if rd(0x0727) ~= 2 and navN % 2 == 1 then nav_in = { select = true } else nav_in = { start = true } end
      nav_until = frame + 4
    end
  end
  for _, s in ipairs(SEATS) do seat_frame(s, mode) end
  if frame % 6000 == 0 then
    logf(string.format("TICK f=%d P1recs=%d P2recs=%d spd1=%d spd2=%d lvl=%d,%d cberr=%d", frame, SEATS[1].recs, SEATS[2].recs,
      rd(0x030B), rd(0x038B), rd(0x0316), rd(0x0396), cb_err))
  end
  if frame >= MAXF then
    local function hist(t)
      local ks = {}
      for k, _ in pairs(t) do ks[#ks + 1] = k end
      table.sort(ks)
      local o = {}
      for _, k in ipairs(ks) do o[#o + 1] = string.format("%s:%d", tostring(k), t[k]) end
      return table.concat(o, " ")
    end
    for _, s in ipairs(SEATS) do
      logf(string.format("G0_HIST %s %s", s.name, hist(s.g0)))
      logf(string.format("NATURAL_KDROP_HIST %s %s soft=%d", s.name, hist(s.nat), s.soft))
      for thr, h in pairs(s.g0_by_thr) do logf(string.format("G0_BY_THR %s thr=%d %s", s.name, thr, hist(h))) end
    end
    logf("MODES " .. hist(modes))
    logf(string.format("SUMMARY tag=%s frames=%d P1recs=%d P2recs=%d cberr=%d", TAG, frame, SEATS[1].recs, SEATS[2].recs, cb_err))
    logf("DONE"); lf:close()
    pcall(function() emu.stop(0) end)
  end
end), emu.eventType.endFrame)
