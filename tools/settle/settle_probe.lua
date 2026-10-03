-- settle_probe.lua -- what does the P2 post-spawn SETTLE (DELAY2, 15 hooks) protect? (2026-10-03, claude/settle)
--
-- Runs a REAL copro cart (couch DRHUMAN or CvC, header remapped 100 -> 1) with a Lua copro on the P2 window ($5200):
-- a 1-ply colour-greedy brain (plus a fraction of random placements, to grow tall boards) that answers from the
-- cart's OWN upload bytes. Per driver hook (exec $FF54 = the trampoline entry, i.e. exactly the RAM the driver
-- sees: the hook runs inside the NMI, the main loop cannot run between the two hooks of a frame) it snapshots the
-- bytes the P2 upload is built from: $0500-$057F, $0381/$0382 (capsule), $039A/$039B (preview), $038A/$038B
-- (speedUps/speed: DRREACHTX nibbles), SEED2 $6168. Per pill:
--   EDGE  = the driver's own new-pill block writing DELAY2 <- SETTLE ($615F; RMW dummy write filtered)
--   GO    = the driver's write to $5284; the 132 upload bytes $5200-$5283 are captured by a write callback
--   for every hook k from the edge to the GO: does enc(snapshot_k) == the bytes actually uploaded?  -> the earliest
--   hook after the edge from which the upload is already final ("stable_from"), per pill, with the context.
--   LOCK  = $0397 0 -> !0; the upload is compared with the last pre-lock snapshot: did the AI plan on the board the
--           capsule actually landed in?
-- Gravity (the fairness / pricing question), per pill at FRAME level (endFrame, same method as base_gravity_probe):
--   spawn = the endFrame where p2_pillsCounter $03A7 moved; the P2 gravity counter $0392 per frame until the first
--   drop; G0 = k - counter at the last frame k before the first drop (= frames of gravity NOT counted since spawn).
-- Interrupted main-loop PC per NMI (stack at the game NMI entry $8005) -> was the game mid-write when the hook ran?
-- Env: ST_OUT (dir/), ST_TAG, ST_MAXF, ST_SETTLE (the cart's DELAY2 immediate, 15 stock), ST_HUMAN (1 = couch seat:
-- menu nav + P1 field wipe), ST_POKE_EVERY / ST_POKE_SIZE (garbage pokes, nmi_witness.lua method), ST_PRAND
-- (fraction of random placements), ST_SEED, ST_TAPP (2), ST_REACHTX (1), ST_TRACE (pills to trace hook-by-hook).
-- Mesen traps: emu.write has 3 args (pcall-logged); single instance (runner waits for the seat); memory callbacks
-- that answer the mailbox are pure Lua; exec callbacks read RAM (as tools/lateflip/nmi_witness.lua does).
local OUT = os.getenv("ST_OUT") or error("ST_OUT"); if OUT:sub(-1) ~= "/" then OUT = OUT .. "/" end
local TAG = os.getenv("ST_TAG") or "run"
local MAXF = tonumber(os.getenv("ST_MAXF") or "60000")
local SETTLE = tonumber(os.getenv("ST_SETTLE") or "15")
local HUMAN = (os.getenv("ST_HUMAN") or "0") == "1"
local POKE_EVERY = tonumber(os.getenv("ST_POKE_EVERY") or "0")
local POKE_SIZE = tonumber(os.getenv("ST_POKE_SIZE") or "0")      -- 0 = random 2..4
local PRAND = tonumber(os.getenv("ST_PRAND") or "0.15")
local TAPP = tonumber(os.getenv("ST_TAPP") or "2")
local REACHTX = (os.getenv("ST_REACHTX") or "1") == "1"
local NTRACE = tonumber(os.getenv("ST_TRACE") or "12")
math.randomseed(tonumber(os.getenv("ST_SEED") or "1"))

local NES = emu.memType.nesMemory
local function rd(a) return emu.read(a, NES, false) end
local lf = io.open(OUT .. "settle_" .. TAG .. ".log", "w")
local function logf(s) lf:write(s .. "\n"); lf:flush() end
local cb_err = 0
local function guard(fn)               -- a raising callback is silently dropped by Mesen: count + log instead
  return function(...)
    local ok, r = pcall(fn, ...)
    if not ok then cb_err = cb_err + 1; if cb_err <= 20 then logf("CBERR " .. tostring(r)) end; return nil end
    return r
  end
end
local function wr(a, v)
  local ok, err = pcall(function() emu.write(a, v, NES) end)
  if not ok then logf(string.format("WRITE_ERR %04X %s", a, tostring(err))) end
end

-- ------------------------------------------------------------------ counters / clocks
local frame, hook, nmi, hpos = 0, 0, 0, 0
local W = 0x5200
local A_DELAY2, A_PEND2, A_ARMED2, A_ROTDONE2, A_SEED2 = 0x615F, 0x614F, 0x6161, 0x616E, 0x6168

-- ------------------------------------------------------------------ upload encoding (patch_cartridge_copro handle(2))
local function enc_from(b, c1, c2, n1, n2, spu, spd, seed)
  local t = {}
  for i = 1, 128 do local v = b[i]; if v == 0 then v = 0xFF end; t[i] = v end
  t[129] = (c1 & 0x0F) | ((seed << 4) & 0xF0)
  t[130] = (c2 & 0x0F) | (seed & 0xF0)
  if REACHTX then
    local na = ((spu & 0x0F) << 4) | ((TAPP & 3) << 2)
    local nb = ((((spu >> 4) & 3) | ((spd + 1) << 2)) << 4) & 0xFF
    nb = nb | (((TAPP >> 2) & 3) << 2)
    local m = (TAPP ~= 0) and 0x03 or 0x0F
    t[131] = (n1 & m) | (na & 0xFF)
    t[132] = (n2 & m) | nb
  else
    t[131] = n1 & 0x0F; t[132] = n2 & 0x0F
  end
  local s = {}
  for i = 1, 132 do s[i] = string.char(t[i] & 0xFF) end
  return table.concat(s), t
end

-- ------------------------------------------------------------------ per-hook snapshots
local snaps = {}                      -- hook id -> snapshot
local function snapshot()
  local b = {}
  for i = 0, 127 do b[i + 1] = rd(0x0500 + i) end
  local s = { b = b, c1 = rd(0x0381), c2 = rd(0x0382), n1 = rd(0x039A), n2 = rd(0x039B), spu = rd(0x038A),
              spd = rd(0x038B), seed = rd(A_SEED2), y = rd(0x0386), x = rd(0x0385), rot = rd(0x03A5),
              na = rd(0x0397), cnt = rd(0x03A7), grav = rd(0x0392), combo = rd(0x038F), chain = rd(0x03A1),
              mode = rd(0x46), pad = rd(0xF8), pend = rd(A_PEND2), dly = rd(A_DELAY2), arm = rd(A_ARMED2), rd2 = rd(A_ROTDONE2),
              nmi = nmi, pos = hpos, frame = frame }
  s.enc, s.encT = enc_from(b, s.c1, s.c2, s.n1, s.n2, s.spu, s.spd, s.seed)
  return s
end

-- ------------------------------------------------------------------ copro brain (1-ply colour greedy)
-- copro orient o4 = var ^ 2; var 0 = H (a,b), 1 = H (b,a), 2 = V a top, 3 = V b top (steer_model / bitexact map)
local function brain(up)
  local occ, col = {}, {}
  for r = 0, 15 do for c = 0, 7 do
    local v = up[r * 8 + c] or 0xFF
    occ[r * 8 + c] = (v ~= 0xFF and v ~= 0x00); col[r * 8 + c] = v & 0x0F
  end end
  local a, bcol = (up[128] or 0) & 0x03, (up[129] or 0) & 0x03
  local cands = {}
  for var = 0, 3 do
    local horiz = var < 2
    local ca, cb = a, bcol
    if var == 1 or var == 3 then ca, cb = bcol, a end
    for c = 0, horiz and 6 or 7 do
      -- straight drop from the top: the deepest row r such that every row 0..r is free for the pose
      local r, ok = -1, true
      while ok do
        local nr = r + 1
        if nr > 15 then break end
        if horiz then ok = (not occ[nr * 8 + c]) and (not occ[nr * 8 + c + 1])
        else ok = (not occ[nr * 8 + c]) and (nr == 0 or not occ[(nr - 1) * 8 + c]) end
        if ok then r = nr end
      end
      if r >= 0 then
        local cells
        if horiz then cells = { { r, c, ca }, { r, c + 1, cb } }
        else cells = { { r - 1, c, ca }, { r, c, cb } } end
        -- score: cells/viruses in >=4 runs through the placed cells, plus same-colour neighbours, minus height
        local function at(rr, cc)
          if rr < 0 or rr > 15 or cc < 0 or cc > 7 then return nil end
          for _, p in ipairs(cells) do if p[1] == rr and p[2] == cc then return p[3] end end
          if occ[rr * 8 + cc] then return col[rr * 8 + cc] end
          return nil
        end
        local clear, vir, nb = 0, 0, 0
        for _, p in ipairs(cells) do
          if p[1] >= 0 then
            for _, d in ipairs({ { 0, 1 }, { 1, 0 } }) do
              local n, rr, cc = 1, p[1], p[2]
              local run = { { rr, cc } }
              while at(rr - d[1] * n, cc - d[2] * n) == p[3] do run[#run + 1] = { rr - d[1] * n, cc - d[2] * n }; n = n + 1 end
              local m = 1
              while at(rr + d[1] * m, cc + d[2] * m) == p[3] do run[#run + 1] = { rr + d[1] * m, cc + d[2] * m }; m = m + 1 end
              if #run >= 4 then
                clear = clear + #run
                for _, q in ipairs(run) do
                  local v = up[q[1] * 8 + q[2]]
                  if v and (v & 0xF0) == 0xD0 then vir = vir + 1 end
                end
              elseif #run >= 2 then nb = nb + (#run - 1) end
            end
          end
        end
        local sc = 1000 * vir + 60 * clear + 9 * nb + 4 * r + math.random() * 3
        cands[#cands + 1] = { sc = sc, o4 = var ~ 2, c = c }
      end
    end
  end
  if #cands == 0 then return 3, 2 end
  if math.random() < PRAND then local k = cands[math.random(1, #cands)]; return k.c, k.o4 end
  local best = cands[1]
  for _, k in ipairs(cands) do if k.sc > best.sc then best = k end end
  return best.c, best.o4
end

-- ------------------------------------------------------------------ mailbox (P2 window)
local up = {}
local mb = { mode = "idle", go_hook = -1, first = 2, done_at = 30, col = 3, ori = 2, prev_col = 3, prev_ori = 2,
             goes = 0, dones = 0 }
local gos = {}                        -- pending GO records for the per-hook processor
emu.addMemoryCallback(guard(function(addr, value) up[addr - W] = value end), emu.callbackType.write, W, W + 0x83)
emu.addMemoryCallback(guard(function()
  mb.goes = mb.goes + 1
  local copy = {}
  for i = 0, 131 do copy[i] = up[i] end
  local s = {}
  for i = 0, 131 do s[i + 1] = string.char((copy[i] or 0) & 0xFF) end
  gos[#gos + 1] = { hook = hook, up = table.concat(s), upT = copy }
  local c, o = brain(copy)
  mb.mode = "search"; mb.go_hook = hook; mb.col, mb.ori = c, o
  mb.first = math.random(2, 4)                    -- hooks after GO until the first live publish
  mb.done_at = math.random(20, 80)                -- hooks after GO until DONE (10-40 frames)
end), emu.callbackType.write, W + 0x84)
local function view()
  if mb.mode ~= "search" then return mb.prev_col, mb.prev_ori, 1 end
  local k = hook - mb.go_hook
  if k >= mb.done_at then return mb.col, mb.ori, 1 end
  if k >= mb.first then return mb.col, mb.ori, 0 end
  return 0, 0xFF, 0
end
emu.addMemoryCallback(guard(function()
  local c, o, d = view()
  if d == 1 and mb.mode == "search" then mb.mode = "idle"; mb.dones = mb.dones + 1; mb.prev_col, mb.prev_ori = mb.col, mb.ori end
  return d
end), emu.callbackType.read, W + 0x84)
emu.addMemoryCallback(guard(function() local c = view(); return c end), emu.callbackType.read, W + 0x85)
emu.addMemoryCallback(guard(function() local _, o = view(); return o end), emu.callbackType.read, W + 0x86)
emu.addMemoryCallback(guard(function() return 0xFF end), emu.callbackType.read, W + 0x87)
emu.addMemoryCallback(guard(function() return 0x00 end), emu.callbackType.read, W + 0x88)

-- ------------------------------------------------------------------ driver edge (DELAY2 <- SETTLE)
local edges = {}
local lastw = -1
emu.addMemoryCallback(guard(function(addr, value)
  if value == SETTLE and lastw ~= SETTLE then edges[#edges + 1] = hook end
  lastw = value
end), emu.callbackType.write, A_DELAY2)

-- garbage release (P2's checkReleaseAttack zeroes P1's attackSize $0318)
local atk_prev, releases = 0, {}
emu.addMemoryCallback(guard(function(addr, value)
  if value == 0 and atk_prev ~= 0 then releases[#releases + 1] = hook end
  atk_prev = value
end), emu.callbackType.write, 0x0318)

-- ------------------------------------------------------------------ NMI entry: interrupted main-loop PC
local pc_hist = {}
local nmi_pc = {}
local state_keys_logged = false
emu.addMemoryCallback(guard(function()
  if rd(0xA02E) == 0x40 then return end           -- driver bank mapped: not the game NMI entry
  nmi = nmi + 1; hpos = 0
  local st = emu.getState()
  if not state_keys_logged then
    state_keys_logged = true
    local ks = {}
    for k, _ in pairs(st) do if tostring(k):sub(1, 4) == "cpu." then ks[#ks + 1] = tostring(k) end end
    table.sort(ks); logf("STATEKEYS " .. table.concat(ks, ","))
  end
  local sp = st["cpu.sp"]
  if sp then
    local pcl = rd(0x0100 + ((sp + 2) & 0xFF)); local pch = rd(0x0100 + ((sp + 3) & 0xFF))
    local pc = pch * 256 + pcl
    nmi_pc[nmi] = pc
    pc_hist[pc] = (pc_hist[pc] or 0) + 1
  end
end), emu.callbackType.exec, 0x8005)
local absorbed = 0
emu.addMemoryCallback(guard(function() if rd(0xA02E) == 0x40 then absorbed = absorbed + 1 end end),
  emu.callbackType.exec, 0xCEEC)

-- ------------------------------------------------------------------ pill tracking
local late_checks = {}
local late = { eq = 0, ne = 0, locked = 0 }
local stats = { pills = 0, selfcheck_bad = 0, noedge_go = 0, lock_bad = 0, stable = {}, firsteq_bad = 0,
                kinds = {}, worst = -1, traced = 0, multi_edge = 0 }
local cur = nil                       -- the pill being tracked (from its GO)
local last_lock_hook = -1
local last_go_hook = -1
local prev_s = nil
local function field_diff(a, b)
  local nb = 0
  for i = 1, 128 do if a.b[i] ~= b.b[i] and not ((a.b[i] == 0 or a.b[i] == 0xFF) and (b.b[i] == 0 or b.b[i] == 0xFF)) then nb = nb + 1 end end
  local t = {}
  if nb > 0 then t[#t + 1] = "board" .. nb end
  if a.c1 ~= b.c1 or a.c2 ~= b.c2 then t[#t + 1] = "cur" end
  if a.n1 ~= b.n1 or a.n2 ~= b.n2 then t[#t + 1] = "next" end
  if a.spu ~= b.spu or a.spd ~= b.spd then t[#t + 1] = "speed" end
  if a.seed ~= b.seed then t[#t + 1] = "seed" end
  return (#t == 0) and "-" or table.concat(t, "+")
end
local function height(s)
  for r = 0, 15 do for c = 0, 7 do local v = s.b[r * 8 + c + 1]; if v ~= 0 and v ~= 0xFF then return 16 - r end end end
  return 0
end

local function process_go(g)
  -- which edge does this GO belong to? the latest edge in (last_go_hook, g.hook]
  local e = nil
  local ne = 0
  for i = #edges, 1, -1 do
    if edges[i] <= g.hook and edges[i] > last_go_hook then ne = ne + 1; if e == nil then e = edges[i] end end
  end
  if ne > 1 then stats.multi_edge = stats.multi_edge + 1 end
  last_go_hook = g.hook
  local sg = snaps[g.hook]
  local rec = { go = g.hook, edge = e, up = g.up, upT = g.upT }
  stats.pills = stats.pills + 1
  if sg == nil then logf("NOSNAP go=" .. g.hook); return rec end
  rec.self_ok = (sg.enc == g.up)
  if not rec.self_ok then
    stats.selfcheck_bad = stats.selfcheck_bad + 1
    local first = -1
    for i = 1, 132 do if sg.enc:byte(i) ~= g.up:byte(i) then first = i - 1; break end end
    logf(string.format("SELFCHECK_BAD go=%d first=%d enc=%02X up=%02X", g.hook, first, sg.enc:byte(first + 1) or 0, g.up:byte(first + 1) or 0))
  end
  if e == nil then
    stats.noedge_go = stats.noedge_go + 1
    rec.kind = "noedge"
    logf(string.format("GO_NOEDGE go=%d f=%d na=%d y=%d cnt=%d mode=%d", g.hook, sg.frame, sg.na, sg.y, sg.cnt, sg.mode))
    return rec
  end
  local se = snaps[e]
  -- stable_from: earliest hook h in [e, go] such that enc(snap_h) == upload for every h' in [h, go]
  local stable = g.hook
  for h = g.hook, e, -1 do
    local sh = snaps[h]
    if sh and sh.enc == g.up then stable = h else break end
  end
  rec.stable = stable - e
  -- flag-on carts: also compare with what a 15-hook settle would have uploaded (the snapshot at edge + 14), if the
  -- capsule is still in the air then (checked when that hook arrives)
  if g.hook - e < 14 then late_checks[#late_checks + 1] = { at = e + 14, up = g.up, e = e } end
  rec.first_eq = (se ~= nil and se.enc == g.up)
  -- context
  local kind = "mid"
  if se then
    if se.na == 6 then kind = "prethrow" end
    if se.cnt ~= sg.cnt then kind = kind .. "+cntmoved" end
  end
  local rel = false
  for i = #releases, 1, -1 do if releases[i] > last_lock_hook and releases[i] <= e then rel = true; break end end
  rec.garbage = rel
  rec.kind = kind
  stats.kinds[kind] = (stats.kinds[kind] or 0) + 1
  local key = string.format("%s%s", kind, rel and "+garbage" or "")
  stats.stable[key] = stats.stable[key] or {}
  stats.stable[key][rec.stable] = (stats.stable[key][rec.stable] or 0) + 1
  if rec.stable > stats.worst then stats.worst = rec.stable end
  if not rec.first_eq then stats.firsteq_bad = stats.firsteq_bad + 1 end
  -- per-hook diff vs the GO snapshot, for every hook before stable
  local diffs = {}
  for h = e, stable - 1 do
    local sh = snaps[h]
    diffs[#diffs + 1] = sh and string.format("%d:%s", h - e, field_diff(sh, sg)) or string.format("%d:nosnap", h - e)
  end
  local pce = se and nmi_pc[se.nmi] or -1
  local pc1 = -1
  if se then pc1 = nmi_pc[se.nmi + 1] or -1 end
  logf(string.format("PILL n=%d edge=%d go=%d dgo=%d stable=%d first_eq=%s self=%s kind=%s garbage=%s chain=%d " ..
    "h=%d na_e=%d cnt_e=%d cnt_go=%d spu=%d pc_e=%04X pc_e1=%04X pos_e=%d diffs=%s",
    stats.pills, e, g.hook, g.hook - e, rec.stable, tostring(rec.first_eq), tostring(rec.self_ok), kind, tostring(rel),
    se and se.chain or -1, se and height(se) or -1, se and se.na or -1, se and se.cnt or -1, sg.cnt, sg.spu, pce, pc1,
    se and se.pos or -1, (#diffs > 0) and table.concat(diffs, ",") or "-"))
  -- hook-by-hook trace for the first NTRACE pills and any pill whose edge-hook upload was not final
  if stats.traced < NTRACE or (not rec.first_eq and stats.traced < NTRACE + 60) then
    stats.traced = stats.traced + 1
    for h = e - 2, g.hook do
      local sh = snaps[h]
      if sh then
        logf(string.format("TR n=%d h=%+d nmi=%d pos=%d f=%d mode=%d y=%d x=%d rot=%d na=%d cnt=%d grav=%d c=%d,%d n=%d,%d spu=%d pend=%d dly=%d arm=%d rd2=%d pc=%04X eq=%s",
          stats.pills, h - e, sh.nmi, sh.pos, sh.frame, sh.mode, sh.y, sh.x, sh.rot, sh.na, sh.cnt, sh.grav, sh.c1, sh.c2,
          sh.n1, sh.n2, sh.spu, sh.pend, sh.dly, sh.arm, sh.rd2, nmi_pc[sh.nmi] or -1, tostring(sh.enc == g.up)))
      end
    end
  end
  return rec
end

local function finish_lock(h)
  -- the capsule locked: compare the upload with the last pre-lock snapshots
  if cur == nil then return end
  local s1, s2 = snaps[h - 1], snaps[h - 2]
  local ok1 = s1 and s1.enc == cur.up
  local ok2 = s2 and s2.enc == cur.up
  if not ok1 then
    stats.lock_bad = stats.lock_bad + 1
    local sg = snaps[cur.go]
    logf(string.format("LOCK_MISMATCH go=%d lock=%d kind=%s ok_h-1=%s ok_h-2=%s go_vs_prelock=%s", cur.go, h,
      tostring(cur.kind), tostring(ok1), tostring(ok2), (s1 and sg) and field_diff(s1, sg) or "nosnap"))
  end
  stats.locks = (stats.locks or 0) + 1
  -- per-pill tempo: edge (or prestart GO) -> lock, and whether the driver soft-dropped (DOWN held) on the way
  local t0 = cur.edge or cur.go
  local slam = false
  for k = t0, h - 1 do local sk = snaps[k]; if sk and (sk.pad & 0x04) ~= 0 then slam = true; break end end
  local se = snaps[t0]
  logf(string.format("LOCKT kind=%s t0=%d lock=%d dt_hooks=%d slam=%s y_lock=%d spu=%d", tostring(cur.kind), t0, h,
    h - t0, tostring(slam), snaps[h - 1] and snaps[h - 1].y or -1, se and se.spu or -1))
  last_lock_hook = h
  cur = nil
end

emu.addMemoryCallback(guard(function()
  hook = hook + 1; hpos = hpos + 1
  local s = snapshot()
  snaps[hook] = s
  snaps[hook - 400] = nil
  -- GOs issued during the previous hook(s)
  while #gos > 0 and gos[1].hook < hook do
    local g = table.remove(gos, 1)
    if cur ~= nil and cur.go ~= nil then stats.go_without_lock = (stats.go_without_lock or 0) + 1 end
    cur = process_go(g)
  end
  if prev_s and cur and prev_s.na == 0 and s.na ~= 0 and s.mode == 4 then finish_lock(hook) end
  while #late_checks > 0 and late_checks[1].at <= hook do
    local lc = table.remove(late_checks, 1)
    if lc.at == hook then
      if s.na ~= 0 and s.na ~= 3 then late.locked = late.locked + 1
      elseif s.enc == lc.up then late.eq = late.eq + 1
      else
        late.ne = late.ne + 1
        local sg = snaps[lc.e]
        logf(string.format("LATE_NE edge=%d at=%d na=%d diff_vs_edge=%s", lc.e, hook, s.na, sg and field_diff(s, sg) or "?"))
      end
    end
  end
  prev_s = s
end), emu.callbackType.exec, 0xFF54)

-- ------------------------------------------------------------------ frame-level gravity trace (fairness probe)
local gv = { cur = nil, n = 0, g0 = {}, natural = {}, softfirst = 0, recs = 0 }
local SPEED_TABLE = { [0] = 0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
  0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
  0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
  0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
  0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00 }
local SPEED_BASE = { [0] = 0x0F, 0x19, 0x1F }
local last_f = {}
local function gravity_frame(mode, y, cnt, na, grav, spu, spd)
  if mode ~= 4 then gv.cur = nil; last_f = {}; return end
  if last_f.cnt ~= nil and cnt ~= last_f.cnt then
    -- a new pill was generated in this frame's main loop
    local thr = SPEED_TABLE[math.min(80, (SPEED_BASE[spd] or 0x19) + spu)]
    gv.cur = { s = frame, y0 = y, thr = thr, trace = { grav }, na = { na }, spu = spu, spd = spd }
  elseif gv.cur then
    local k = frame - gv.cur.s
    if y < gv.cur.y0 or (na ~= 0 and na ~= 3 and na ~= 6) or k > 300 then
      -- first drop (or lock/timeout): classify with the counter of the previous frame
      local c = gv.cur
      local lastc = c.trace[#c.trace]
      local natural = (y < c.y0) and (lastc == c.thr)
      local g0 = (k - 1) - lastc
      gv.recs = gv.recs + 1
      if natural then gv.natural[k] = (gv.natural[k] or 0) + 1 else gv.softfirst = gv.softfirst + 1 end
      local key = string.format("thr%d", c.thr)
      gv.g0[g0] = (gv.g0[g0] or 0) + 1
      if gv.recs <= 400 then
        logf(string.format("GRAV n=%d s=%d k_drop=%d thr=%d spu=%d spd=%d natural=%s G0=%d trace=%s na=%s",
          gv.recs, c.s, k, c.thr, c.spu, c.spd, tostring(natural), g0, table.concat(c.trace, ","), table.concat(c.na, ",")))
      end
      gv.cur = nil
    else
      gv.cur.trace[#gv.cur.trace + 1] = grav
      gv.cur.na[#gv.cur.na + 1] = na
    end
  end
  last_f = { cnt = cnt }
end

-- ------------------------------------------------------------------ frame loop: nav, P1 seat, pokes, gravity, end
local cur_in, untl, navN = nil, -1, 0
emu.addEventCallback(guard(function() if cur_in and frame < untl then emu.setInput(cur_in, 0) end end), emu.eventType.inputPolled)
local function press(i, d) cur_in = i; untl = frame + (d or 4) end
local play_f, last_poke, pokes = 0, -100000, 0
local modes = {}
logf(string.format("settle_probe %s settle=%d human=%s poke_every=%d prand=%.2f tapp=%d reachtx=%s maxf=%d",
  TAG, SETTLE, tostring(HUMAN), POKE_EVERY, PRAND, TAPP, tostring(REACHTX), MAXF))

emu.addEventCallback(guard(function()
  frame = frame + 1
  local mode = rd(0x46)
  modes[mode] = (modes[mode] or 0) + 1
  if HUMAN then
    if mode ~= 4 and frame % 40 == 0 then
      navN = navN + 1
      if rd(0x0727) ~= 2 and navN % 2 == 1 then press({ down = true }, 4) else press({ start = true }, 4) end
    end
    if mode == 4 then for i = 0, 127 do wr(0x0400 + i, 0xFF) end end    -- the idle human seat never tops out
  end
  if mode == 4 then play_f = play_f + 1 else play_f = 0 end
  if POKE_EVERY > 0 and play_f >= 120 and rd(0x0397) == 0 and rd(0x0318) == 0 and frame - last_poke >= POKE_EVERY then
    local size = POKE_SIZE > 0 and POKE_SIZE or math.random(2, 4)
    local ok = pcall(function()
      for k = 0, 3 do emu.write(0x0329 + k, math.random(0, 2), NES) end
      emu.write(0x0318, size, NES)
    end)
    if ok then pokes = pokes + 1; last_poke = frame end
  end
  gravity_frame(mode, rd(0x0386), rd(0x03A7), rd(0x0397), rd(0x0392), rd(0x038A), rd(0x038B))
  if frame % 6000 == 0 then
    logf(string.format("TICK f=%d hooks=%d nmis=%d pills=%d goes=%d dones=%d edges=%d locks=%d pokes=%d releases=%d cberr=%d",
      frame, hook, nmi, stats.pills, mb.goes, mb.dones, #edges, stats.locks or 0, pokes, #releases, cb_err))
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
    for key, h in pairs(stats.stable) do logf("STABLE_HIST " .. key .. " " .. hist(h)) end
    logf("KINDS " .. hist(stats.kinds))
    logf("G0_HIST " .. hist(gv.g0))
    logf("NATURAL_KDROP_HIST " .. hist(gv.natural) .. " softfirst=" .. gv.softfirst)
    local top = {}
    for pc, n in pairs(pc_hist) do top[#top + 1] = { pc, n } end
    table.sort(top, function(p, q) return p[2] > q[2] end)
    local o = {}
    for i = 1, math.min(25, #top) do o[#o + 1] = string.format("%04X:%d", top[i][1], top[i][2]) end
    logf("NMI_PC_TOP " .. table.concat(o, " "))
    logf("MODES " .. hist(modes))
    logf(string.format("SUMMARY tag=%s frames=%d hooks=%d nmis=%d pills=%d goes=%d dones=%d edges=%d locks=%d " ..
      "selfcheck_bad=%d noedge_go=%d first_eq_bad=%d worst_stable=%d lock_bad=%d multi_edge=%d go_without_lock=%d " ..
      "pokes=%d releases=%d grav_recs=%d absorbed=%d late_eq=%d late_ne=%d late_locked=%d cberr=%d",
      TAG, frame, hook, nmi, stats.pills, mb.goes, mb.dones, #edges, stats.locks or 0, stats.selfcheck_bad, stats.noedge_go,
      stats.firsteq_bad, stats.worst, stats.lock_bad, stats.multi_edge, stats.go_without_lock or 0, pokes, #releases,
      gv.recs, absorbed, late.eq, late.ne, late.locked, cb_err))
    logf("DONE"); lf:close()
    pcall(function() emu.stop(0) end)
  end
end), emu.eventType.endFrame)
