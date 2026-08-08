#!/usr/bin/env python3
"""RECOMMIT verification for the cart ON THE USER'S POCKET (md5 9b2eedc...).

1. Rebuild unit1 in-process with the manifest's exact flags; assert byte-identity
   against the cart's unit-1 bank -> the label map applies to shipped silicon bytes.
2. Disassemble the RECOMMIT block + audit every branch target in handle(2).
3. Execute the REAL cart bytes on a py65 MPU across the full state matrix:
   handle(2) DONE-publish path, then act_p2, asserting latch/press behavior.
"""
import os, sys

os.environ.update({"DRHUMAN": "1", "DRNAVDWELL": "0", "DRNOFREEZE": "1",
                   "DRPOCKET": "1", "DRRECOMMIT_NOFREEZE": "1"})
sys.path.insert(0, "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
import patch_cartridge_copro as P

CART = "/home/struktured/projects/dr-mario-mods-wt/driver-nav/tmp/verify_user_cart.nes"
BANK_OFF = 16 + 2 * 16384          # unit-1 bank in the 4-bank expanded file
BASE = 0x8000

unit1, labels = P.build_main(11, 1)
rom = open(CART, "rb").read()
bank = rom[BANK_OFF:BANK_OFF + 16384]
assert bank[:len(unit1)] == unit1, "in-process build != cart bank bytes"
print("unit1 (%d B) == cart unit-1 bank: byte-identical -> labels apply to the shipped cart"
      % len(unit1))
assert not P.TUCK and P.RECOMMIT and P.MATURE and P.SLAM and P.ROTFIX and P.NO_FREEZE and P.HUMAN_P1
print("flags: RECOMMIT=%s MATURE=%s SLAM=%s ROTFIX=%s NO_FREEZE=%s HUMAN_P1=%s TUCK=%s COLGATE=%s"
      % (P.RECOMMIT, P.MATURE, P.SLAM, P.ROTFIX, P.NO_FREEZE, P.HUMAN_P1, P.TUCK, P.COLGATE))
print("consts: CROSS_LOWY=%d MIN_THINK=%d K_OPEN=%d K_END=%d K_CROSS=%d FAST_HI=%d W2_BASE=$%04X"
      % (P.CROSS_LOWY, P.MIN_THINK, P.K_OPEN, P.K_END, P.K_CROSS, P.FAST_HI, P.W2_BASE))

L = {k: BASE + v for k, v in labels.items()}
rev = {}
for k, v in L.items():
    rev.setdefault(v, []).append(k)

# ---- disassembler (subset used by the emitter) ------------------------------
OPS = {
    0xAD: ("LDA", "abs"), 0x8D: ("STA", "abs"), 0xCD: ("CMP", "abs"),
    0xEE: ("INC", "abs"), 0xBD: ("LDA", "absX"), 0x9D: ("STA", "absX"),
    0xA9: ("LDA", "imm"), 0xC9: ("CMP", "imm"), 0xA0: ("LDY", "imm"),
    0xA2: ("LDX", "imm"), 0xE0: ("CPX", "imm"),
    0x85: ("STA", "zp"), 0x84: ("STY", "zp"), 0xA5: ("LDA", "zp"),
    0xF0: ("BEQ", "rel"), 0xD0: ("BNE", "rel"), 0x90: ("BCC", "rel"), 0xB0: ("BCS", "rel"),
    0x4C: ("JMP", "abs"), 0x60: ("RTS", "impl"), 0xE8: ("INX", "impl"),
    0x0A: ("ASL", "impl"), 0x4A: ("LSR", "impl"), 0x18: ("CLC", "impl"),
    0x29: ("AND", "imm"), 0x0D: ("ORA", "abs"), 0x6D: ("ADC", "abs"),
}
def dis(lo, hi):
    pc = lo
    while pc < hi:
        for nm in rev.get(pc, []):
            print("            %s:" % nm)
        op = bank[pc - BASE]
        if op not in OPS:
            print("  $%04X: .db $%02X ???" % (pc, op)); pc += 1; continue
        mn, mode = OPS[op]
        if mode == "impl":
            print("  $%04X: %s" % (pc, mn)); pc += 1
        elif mode == "imm":
            print("  $%04X: %s #$%02X" % (pc, mn, bank[pc - BASE + 1])); pc += 2
        elif mode == "zp":
            print("  $%04X: %s $%02X" % (pc, mn, bank[pc - BASE + 1])); pc += 2
        elif mode == "rel":
            off = bank[pc - BASE + 1]; off = off - 256 if off >= 128 else off
            tgt = pc + 2 + off
            print("  $%04X: %s $%04X  %s" % (pc, mn, tgt,
                  "<" + ",".join(rev.get(tgt, ["?NO-LABEL?"])) + ">"))
            pc += 2
        else:
            a16 = bank[pc - BASE + 1] | (bank[pc - BASE + 2] << 8)
            lbl = ("  <" + ",".join(rev.get(a16, [])) + ">") if mn == "JMP" else ""
            print("  $%04X: %s $%04X%s%s" % (pc, mn, a16,
                  "" if mode == "abs" else ",X", lbl)); pc += 3

# ---- branch-target audit over handle(2) -------------------------------------
h2_lo, h2_hi = L["h2_dz"] - 8, L["h2_done"] + 1
bad = 0
pc = h2_lo
while pc < h2_hi:
    op = bank[pc - BASE]
    if op not in OPS:
        pc += 1; continue
    mn, mode = OPS[op]
    n = 1 if mode == "impl" else 2 if mode in ("imm", "zp", "rel") else 3
    if mode == "rel":
        off = bank[pc - BASE + 1]; off = off - 256 if off >= 128 else off
        tgt = pc + 2 + off
        if tgt not in rev:
            print("BRANCH-AUDIT FAIL: $%04X %s -> $%04X lands on NO label" % (pc, mn, tgt)); bad += 1
    if mn == "JMP":
        a16 = bank[pc - BASE + 1] | (bank[pc - BASE + 2] << 8)
        if a16 >= BASE and a16 not in rev:
            print("BRANCH-AUDIT FAIL: $%04X JMP -> $%04X lands on NO label" % (pc, a16)); bad += 1
    pc += n
print("branch audit over handle(2) [$%04X..$%04X]: %s" % (h2_lo, h2_hi,
      "ALL branches/JMPs land ON labels" if bad == 0 else "%d BAD" % bad))

print("\n---- RECOMMIT block disassembly (publish -> mat gate) ----")
dis(L["h2_pst"], L["mat_done"] + 9)

# ---- dynamic execution on the REAL cart bytes -------------------------------
from py65.devices.mpu6502 import MPU

W = P.W2_BASE
WDONE, WCOL, WOR = W + 0x84, W + 0x85, W + 0x86
ROT2, TGO, TGC = P.ROT_DONE2, P.TGT_O2, P.TGT_C2
STOP = 0x4FF0   # unmapped sentinel return

def run(entry, stop_at, ram, max_steps=3000):
    m = MPU()
    m.memory[BASE:BASE + len(bank)] = bank                        # map bank at $8000
    for k, v in ram.items():
        m.memory[k] = v
    m.pc = entry
    steps = 0
    trace = []
    while m.pc not in stop_at and steps < max_steps:
        trace.append(m.pc)
        m.step(); steps += 1
    assert m.pc in stop_at, "did not reach a stop label; last pcs %s" % [hex(x) for x in trace[-6:]]
    return m

# ---------- A. handle(2) DONE path: RECOMMIT truth table ----------
print("\n---- A. handle(2) DONE-publish path on cart bytes ----")
# entry h2_armed (armed!=0), wdone=1 -> publish col/orient -> RECOMMIT -> MATURE -> clear
CASES = []
for rot in (0, 1):
    for y in (0, 7, 8, 9, 15):
        for cur_o in (0, 3):          # live orient $03A5
            CASES.append((rot, y, cur_o))
ok = 0
for rot, y, cur_o in CASES:
    ram = {ROT2: rot, 0x0386: y, 0x03A5: cur_o,
           WDONE: 1, WCOL: 4, WOR: 0xFF,   # copro answer col=4, orient 0xFF -> game orient 3
           P.WDOGH2: 0, P.ARMED2: 1}
    m = run(L["h2_armed"], {L["h2_done"]}, ram)
    pub_o = m.memory[TGO]
    exp_reopen = (rot == 1 and y >= P.CROSS_LOWY and pub_o != cur_o)
    exp_rot2 = 0 if exp_reopen else rot
    assert m.memory[TGC] == 4 and pub_o == 3, "publish wrong (col=%d o=%d)" % (m.memory[TGC], pub_o)
    assert m.memory[ROT2] == exp_rot2, \
        "RECOMMIT wrong: rot=%d y=%d cur_o=%d pub_o=%d -> ROT_DONE2=%d expected %d" \
        % (rot, y, cur_o, pub_o, m.memory[ROT2], exp_rot2)
    assert m.memory[P.ARMED2] == 0 and m.memory[P.WDOG2] == 0 and m.memory[P.WDOGH2] == 0
    assert m.memory[P.SLAM_ARM] == 1        # WDOGH2=0 < FAST_HI -> fast -> armed
    ok += 1
print("A: %d/%d state-matrix cases exact (reopen iff latched AND Y>=%d AND orient differs)"
      % (ok, len(CASES), P.CROSS_LOWY))

# boundary + orient-map cross-check: every copro orient value, at the Y boundary
omap = {0xFF: 3, 0: 3, 1: 1, 2: 0, 3: 2}
ok = 0
for wor, game_o in omap.items():
    for y in (P.CROSS_LOWY - 1, P.CROSS_LOWY):
        ram = {ROT2: 1, 0x0386: y, 0x03A5: (game_o + 1) & 3,
               WDONE: 1, WCOL: 2, WOR: wor, P.WDOGH2: 0, P.ARMED2: 1}
        m = run(L["h2_armed"], {L["h2_done"]}, ram)
        assert m.memory[TGO] == game_o, "orient map broke: %02X -> %d" % (wor, m.memory[TGO])
        exp = 1 if y < P.CROSS_LOWY else 0
        assert m.memory[ROT2] == exp, "boundary wrong at y=%d" % y
        ok += 1
print("A2: %d/%d orient-map x Y-boundary cases exact (Y=%d keeps latch, Y=%d reopens)"
      % (ok, len(omap) * 2, P.CROSS_LOWY - 1, P.CROSS_LOWY))

# slow-search disarm variant
ram = {ROT2: 1, 0x0386: 15, 0x03A5: 0, WDONE: 1, WCOL: 4, WOR: 0xFF,
       P.WDOGH2: P.FAST_HI, P.ARMED2: 1}
m = run(L["h2_armed"], {L["h2_done"]}, ram)
assert m.memory[P.SLAM_ARM] == 0 and m.memory[ROT2] == 0
print("A3: slow search (WDOGH2=%d) -> SLAM_ARM disarmed; RECOMMIT still evaluated" % P.FAST_HI)

# ---------- B. act_p2 after a recommit: rotate, no slam, relatch ----------
print("\n---- B. act_p2 on cart bytes (post-RECOMMIT states) ----")
stops = {L["act_p1"]}
base_ram = {P.STK2: 0, P.ARMED2: 0, P.WDOG2: 0, P.WDOGH2: 0, P.SLAM_ARM: 1,
            P.STABLE_CT2: 0, TGC: 4, TGO: 3, 0x0385: 4, 0x0386: 9,
            ROT2: 0, 0x03A5: 1, 0xF6: 0xEE, 0xF8: 0xEE, P.VCOUNT_P2: 20}
# B1: reopened latch, orient differs -> exactly a rotate press, latch stays open, NO down-press
m = run(L["act_p2_n"], stops, dict(base_ram))
assert m.memory[0xF6] == 0x80 and m.memory[0xF8] == 0x00 and m.memory[ROT2] == 0
print("B1: reopened+differs -> presses A (rotate), $F8=0 edge, latch stays open, no slam reachable")
# B2: orient now matches, DONE (ARMED2=0) -> immediate relatch + column phase -> slam (DONE ceiling)
ram = dict(base_ram); ram[0x03A5] = 3
m = run(L["act_p2_n"], stops, ram)
assert m.memory[ROT2] == 1, "no relatch"
assert m.memory[0xF6] == 0x04, "expected down-press (DONE slam ceiling), got %02X" % m.memory[0xF6]
print("B2: orient reached + DONE -> relatch ROT_DONE2=1, column aligned -> slam (DONE ceiling)")
# B3: orient matches, DONE, but column NOT aligned -> relatch + steer, no down
ram = dict(base_ram); ram[0x03A5] = 3; ram[0x0385] = 1
m = run(L["act_p2_n"], stops, ram)
assert m.memory[ROT2] == 1 and m.memory[0xF6] in (0x01, 0x02)
print("B3: orient reached, column off -> relatch + lateral steer (press $%02X)" % m.memory[0xF6])
# B4: latched (no recommit) -> pre-phase skipped even though orient differs
ram = dict(base_ram); ram[ROT2] = 1; ram[0x03A5] = 1
m = run(L["act_p2_n"], stops, ram)
assert m.memory[0xF6] != 0x80, "latched capsule must not rotate"
print("B4: latched + orient differs -> NO rotate (feasibility lock holds); press $%02X" % m.memory[0xF6])
# B5: reopened latch + capsule now LOW + orient differs (post-recommit fall) -> still rotates
ram = dict(base_ram); ram[0x0386] = 2
m = run(L["act_p2_n"], stops, ram)
assert m.memory[0xF6] == 0x80 and m.memory[ROT2] == 0
print("B5: NOTE reopened latch keeps rotating even once low (Y=2): press A, latch open")

print("\nALL DYNAMIC CHECKS PASSED on the shipped cart's bytes")
