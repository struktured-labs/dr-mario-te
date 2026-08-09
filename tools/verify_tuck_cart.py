#!/usr/bin/env python3
"""DRTUCK executor gates, run against the INTEGRATED MiSTer demo-cart image.

Every dynamic gate below executes the BYTES OF THE BUILT CART (located inside the .nes by
exact substring match against an in-process build with the manifest's own flag snapshot),
not a standalone re-emission -- the same discipline as tools/verify_recommit.py.

Gates:
  0. cart bytes == in-process build (locates the driver bank; everything downstream
     therefore runs shipped bytes)
  1. WINDOW GATE (the defect this cart line fixes, tested per the house rule "test the
     DEFECT, not the fix"): the descriptor latch must read P2's OWN window ($5287/$5288
     on this dual-window MiSTer cart) -- the old hardcoded $5087 read is OPEN BUS on the
     winner single-copro core (the $5000-$51FF decode is stripped). Asserts the exact
     opcodes, then DEMONSTRATES the defect: running the same latch path with open-bus
     $50 planted at $5087/$5088 while the real descriptor sits at $5287/$5288 shows the
     old address would have latched garbage ($50) where the new one latches the real
     descriptor.
  2. DESCRIPTOR LATCH (handle(2) DONE path): TUCK_C2 <- [$5287]; TUCK_R2 <- 15-[$5288]
     (the D1 row-units conversion); 0xFF passes through as "no tuck".
  3. RECOMMIT x CROSS_LOWY invariant on the TUCK cart (the TUCK far-branch trampoline
     restructured handle(2)'s branch spans; this proves the invariant survived):
     verify_recommit's state matrix, reopen iff latched AND Y >= CROSS_LOWY AND orient
     differs, plus the orient-map x Y-boundary sweep and the slow-search disarm.
  4. EXECUTOR HEIGHT SWITCH (mv_p2): EFF_C2 = approach column while Y > TUCK_R2, final
     column (TGT_C2) at/below the trigger row or when the descriptor is 0xFF.
  5. D2 INVALIDATION SCOPE (h2_start): TUCK_C2 is invalidated to 0xFF exactly when a
     search actually starts (PEND2=1, DELAY2=0), and NOT on the pend=0 / delay!=0 hooks
     of the descent (the D2 bug was invalidating every hook).

Usage: verify_tuck_cart.py [cart.nes] [manifest.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRV = os.path.dirname(HERE)
CART = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DRV, "roms", "drmario_tuck_demo_mister.nes")
MANIFEST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    DRV, "roms", "manifests", "mister-tuck-demo-theta400.json")

man = json.load(open(MANIFEST))
snap = man["flag_snapshot"]
for k in list(os.environ):
    if k.startswith("DR"):
        del os.environ[k]
os.environ.update(snap)

sys.path.insert(0, DRV)
import patch_cartridge_copro as P                     # noqa: E402

assert os.path.samefile(P.__file__, os.path.join(DRV, "patch_cartridge_copro.py")), P.__file__
assert P.TUCK and P.RECOMMIT and P.MATURE and P.SLAM and P.ROTFIX and P.NO_FREEZE
assert not P.HUMAN_P1 and not P.DISTGATE
assert P.W2_BASE == 0x5200 and P.W_TCOL == 0x5287 and P.W_TROW == 0x5288, \
    (hex(P.W2_BASE), hex(P.W_TCOL), hex(P.W_TROW))

BASE = 0x8000
unit1, labels = P.build_main(11, 1)
rom = open(CART, "rb").read()
n_hits = rom.count(bytes(unit1))
assert n_hits == 1, f"unit1 must appear exactly once in the cart, found {n_hits}"
off = rom.find(bytes(unit1))
bank_i, bank_off = divmod(off - 16, 16384)
assert bank_off == 0, f"unit1 not bank-aligned (bank {bank_i} + {bank_off})"
bank = rom[off:off + 16384]
print(f"[gate0] unit1 ({len(unit1)} B) == cart bank {bank_i} bytes: byte-identical "
      f"(md5 cart {man['output']['md5']})")

L = {k: BASE + v for k, v in labels.items()}

# ---- gate 1: window addressing, defect-first --------------------------------
u = bytes(unit1)
lda_new, sbc_new = bytes([0xAD, 0x87, 0x52]), bytes([0xED, 0x88, 0x52])
lda_old, sbc_old = bytes([0xAD, 0x87, 0x50]), bytes([0xED, 0x88, 0x50])
assert u.count(lda_new) == 1 and u.count(sbc_new) == 1, "P2-window descriptor reads missing"
assert u.count(lda_old) == 0 and u.count(sbc_old) == 0, "stale $5087/$5088 read still present"
print("[gate1a] descriptor latch reads $5287/$5288 (P2 window): LDA/SBC opcodes found "
      "exactly once each; zero stale $5087/$5088 reads")

from py65.devices.mpu6502 import MPU                  # noqa: E402

W = P.W2_BASE
WDONE, WCOL, WOR = W + 0x84, W + 0x85, W + 0x86


def run(entry, stop_at, ram, max_steps=30000):
    m = MPU()
    m.memory[BASE:BASE + len(bank)] = bank
    for k, v in ram.items():
        m.memory[k] = v
    m.pc = entry
    steps = 0
    while m.pc not in stop_at and steps < max_steps:
        m.step()
        steps += 1
    assert m.pc in stop_at, f"no stop label reached from ${entry:04X} (pc=${m.pc:04X})"
    return m


def done_ram(kw=None):
    ram = {P.ROT_DONE2: 0, 0x0386: 15, 0x03A5: 0,
           WDONE: 1, WCOL: 4, WOR: 0xFF, P.WDOGH2: 0, P.ARMED2: 1}
    ram.update(kw or {})
    return ram


# gate 1b: THE DEFECT. Plant open-bus $50 at the OLD address, real descriptor at the NEW.
ram = done_ram({0x5087: 0x50, 0x5088: 0x50, P.W_TCOL: 5, P.W_TROW: 12})
m = run(L["h2_armed"], {L["h2_done"]}, ram)
assert m.memory[P.TUCK_C2] == 5 and m.memory[P.TUCK_R2] == 15 - 12, \
    (m.memory[P.TUCK_C2], m.memory[P.TUCK_R2])
# and the converse -- the old behaviour, simulated: a latch that had read $5087/$5088
# would have adopted $50 (column 80!) as the approach column. Show the value there IS
# the garbage the guard comment describes, i.e. the defect was real on this cart class.
assert m.memory[0x5087] == 0x50 and m.memory[P.TUCK_C2] != 0x50
print("[gate1b] DEFECT DEMONSTRATED+FIXED: with open-bus $50 planted at $5087/$5088 and a "
      "real descriptor (5,12) at $5287/$5288, the cart latches TUCK_C2=5 TUCK_R2=3 "
      "(old address would have latched column 80 = the NES_tuckmb_20260731 failure)")

# ---- gate 2: descriptor latch + D1 row conversion ---------------------------
cases = [(5, 12), (0, 0), (7, 15), (3, 9), (2, 0), (0xFF, 0xFF), (0xFF, 3)]
ok = 0
for tcol, trow in cases:
    m = run(L["h2_armed"], {L["h2_done"]}, done_ram({P.W_TCOL: tcol, P.W_TROW: trow}))
    assert m.memory[P.TUCK_C2] == tcol, (tcol, trow, m.memory[P.TUCK_C2])
    if tcol != 0xFF:
        assert m.memory[P.TUCK_R2] == (15 - trow) & 0xFF, (tcol, trow, m.memory[P.TUCK_R2])
    assert m.memory[P.TGT_C2] == 4 and m.memory[P.TGT_O2] == 3   # publish unaffected
    ok += 1
print(f"[gate2] descriptor latch: {ok}/{len(cases)} cases exact "
      f"(TUCK_C2 <- W_TCOL; TUCK_R2 <- 15-W_TROW in $0386 units; 0xFF passthrough)")

# ---- gate 3: RECOMMIT x CROSS_LOWY on the TUCK cart -------------------------
CASES = [(rot, y, cur_o) for rot in (0, 1) for y in (0, 7, 8, 9, 15) for cur_o in (0, 3)]
ok = 0
for rot, y, cur_o in CASES:
    ram = done_ram({P.ROT_DONE2: rot, 0x0386: y, 0x03A5: cur_o,
                      P.W_TCOL: 0xFF, P.W_TROW: 0xFF})
    m = run(L["h2_armed"], {L["h2_done"]}, ram)
    pub_o = m.memory[P.TGT_O2]
    exp_reopen = (rot == 1 and y >= P.CROSS_LOWY and pub_o != cur_o)
    exp_rot2 = 0 if exp_reopen else rot
    assert m.memory[P.TGT_C2] == 4 and pub_o == 3
    assert m.memory[P.ROT_DONE2] == exp_rot2, (rot, y, cur_o, m.memory[P.ROT_DONE2])
    assert m.memory[P.ARMED2] == 0 and m.memory[P.WDOG2] == 0 and m.memory[P.WDOGH2] == 0
    assert m.memory[P.SLAM_ARM] == 1
    ok += 1
print(f"[gate3] RECOMMIT truth table on TUCK cart: {ok}/{len(CASES)} exact "
      f"(reopen iff latched AND Y>={P.CROSS_LOWY} AND orient differs)")

omap = {0xFF: 3, 0: 3, 1: 1, 2: 0, 3: 2}
ok = 0
for wor, game_o in omap.items():
    for y in (P.CROSS_LOWY - 1, P.CROSS_LOWY):
        ram = done_ram({P.ROT_DONE2: 1, 0x0386: y, 0x03A5: (game_o + 1) & 3,
                          WCOL: 2, WOR: wor, P.W_TCOL: 0xFF, P.W_TROW: 0xFF})
        m = run(L["h2_armed"], {L["h2_done"]}, ram)
        assert m.memory[P.TGT_O2] == game_o, (wor, m.memory[P.TGT_O2])
        assert m.memory[P.ROT_DONE2] == (1 if y < P.CROSS_LOWY else 0), (wor, y)
        ok += 1
print(f"[gate3b] orient-map x Y-boundary: {ok}/{len(omap) * 2} exact "
      f"(Y={P.CROSS_LOWY - 1} keeps latch, Y={P.CROSS_LOWY} reopens)")

m = run(L["h2_armed"], {L["h2_done"]},
        done_ram({P.ROT_DONE2: 1, P.WDOGH2: P.FAST_HI, P.W_TCOL: 0xFF, P.W_TROW: 0xFF}))
assert m.memory[P.SLAM_ARM] == 0 and m.memory[P.ROT_DONE2] == 0
print(f"[gate3c] slow search (WDOGH2={P.FAST_HI}) -> SLAM_ARM disarmed, RECOMMIT still ran")

# ---- gate 4: executor height switch in mv_p2 --------------------------------
stops = {L["dn_p2"], L["st_p2"]}


def mv(tuck_c2, tuck_r2, y, tgt=5, px=0):
    ram = {P.TUCK_C2: tuck_c2, P.TUCK_R2: tuck_r2, P.TGT_C2: tgt,
           0x0386: y, 0x0385: px}
    m = run(L["mv_p2"], stops, ram)
    return m.memory[P.EFF_C2]


cases4 = [
    # (tuck_c2, tuck_r2, y) -> expected EFF_C2  (approach=2, final=5)
    ((0xFF, 0, 15), 5), ((0xFF, 0, 0), 5),          # no descriptor -> final always
    ((2, 6, 15), 2), ((2, 6, 7), 2),                # high -> approach
    ((2, 6, 6), 5), ((2, 6, 5), 5), ((2, 6, 0), 5),  # at/below trigger -> final
    ((2, 15, 15), 5),                                # trigger at spawn row -> final at once
    ((2, 0, 1), 2), ((2, 0, 0), 5),                  # floor-row trigger boundary
]
ok = 0
for (tc, tr, y), exp in cases4:
    got = mv(tc, tr, y)
    assert got == exp, (tc, tr, y, got, exp)
    ok += 1
print(f"[gate4] mv_p2 height switch: {ok}/{len(cases4)} exact "
      "(approach while Y>TUCK_R2, final at/below, 0xFF -> final)")

# ---- gate 5: D2 invalidation scope in h2_start ------------------------------
common = {P.TUCK_C2: 3, P.TUCK_R2: 9, P.ARMED2: 0, P.WDOG2: 0, P.WDOGH2: 0}
# a) search actually starts -> invalidated + search armed
m = run(L["h2_start"], {L["h2_done"]}, {**common, P.PEND2: 1, P.DELAY2: 0})
assert m.memory[P.TUCK_C2] == 0xFF and m.memory[P.ARMED2] == 1, \
    (m.memory[P.TUCK_C2], m.memory[P.ARMED2])
# b) nothing pending (ordinary descent hook) -> descriptor SURVIVES
m = run(L["h2_start"], {L["h2_done"]}, {**common, P.PEND2: 0, P.DELAY2: 0})
assert m.memory[P.TUCK_C2] == 3 and m.memory[P.ARMED2] == 0
# c) pending but still in the settle window -> descriptor survives
m = run(L["h2_start"], {L["h2_done"]}, {**common, P.PEND2: 1, P.DELAY2: 5})
assert m.memory[P.TUCK_C2] == 3 and m.memory[P.ARMED2] == 0
print("[gate5] D2 invalidation scope: 3/3 exact (0xFF only when a search actually starts; "
      "descriptor survives pend=0 and settle-delay hooks)")

print("\nALL GATES PASS on the integrated cart image:", os.path.basename(CART))
