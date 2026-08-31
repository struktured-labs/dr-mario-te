#!/usr/bin/env python3
"""GATE 5 (DRPROPH): mode-guard -- the trigger must not fire outside active play.

Method: run ONE driver hook (main @$8000, past the trampoline exactly like the
trampoline would) of the DRPROPH=1 cart and the DRPROPH=0 cart from IDENTICAL
machine state, with a board that WOULD trigger (fo(c4)=1 ledge, Y-rise armed),
across every non-play mode + the two mode-4 non-AI states. DRPROPH=1 must be
BEHAVIORALLY INERT there: full state diff (zp, RAM $0000-$07FF, PRG-RAM
$6000-$7FFF) identical to DRPROPH=0, and PROPH_DIR ($61C6) still 0.

Positive control (the check that proves the instrument can fail): mode 4 +
$04!=0 + the same board -> PROPH_DIR latches LEFT ($02) and the pulse presses
$F6=$02 with $F8=0 on both hooks of frame 0, releases on frame 1 (the $43-parity
phase), while the DRPROPH=0 cart writes the plain no-button state.
"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)
from py65_harness import Cpu

PROPH_DIR = 0x61C6
MODE, P2SEL = 0x0046, 0x04

def load_cart(path):
    d = open(path, "rb").read()
    assert d[:4] == b"NES\x1a"
    prg = d[16:16 + 4 * 16384]
    cpu = Cpu()
    cpu.load(0x8000, prg[2 * 16384:3 * 16384])   # driver unit low half (bank 2)
    cpu.load(0xC000, prg[3 * 16384:4 * 16384])   # shared high half (bank 3)
    return cpu

def setup(cpu, mode, p2sel, vc2=5, nbp=2):
    m = cpu.mem
    m[MODE] = mode
    m[P2SEL] = p2sel
    m[0x0727] = nbp
    m[0x43] = 0
    m[0x6149] = 0xA5                  # NAV_MAGIC warm: a live cart mid-session (a cold boot
                                      # would run the power-on init, clearing MATCH_ACTIVE and
                                      # degenerating the fc_clear case to a first-play frame)
    m[0x0324] = 5                     # VCOUNT_P1
    m[0x03A4] = vc2                   # VCOUNT_P2
    m[0x6164] = 1                     # MATCH_ACTIVE
    m[0x616B] = 1 if vc2 == 0 else 0  # VSEEN2 (armed for the fc_clear case)
    m[0x6155] = 2                     # LASTY2 low -> $0386=15 reads as a NEW PILL
    m[0x0386] = 15; m[0x0385] = 3; m[0x03A5] = 0
    m[0x0306] = 15; m[0x6154] = 15    # P1: no edge
    for i in range(128):
        m[0x0500 + i] = 0xFF
    for r in range(1, 16):
        m[0x0500 + r * 8 + 4] = 0x41  # col4 fo=1: the trigger ledge
    m[0x5286] = 0xFF                  # mailbox invalid (no candidate)

def state(cpu):
    # $0100-$01FF excluded: stack RESIDUE below SP differs because the DRPROPH build's code
    # addresses differ (JSR return bytes), which is layout, not behavior.
    return (tuple(cpu.mem[0:0x100]), tuple(cpu.mem[0x200:0x800]),
            tuple(cpu.mem[0x6000:0x8000]))

# G3_DIR: cart directory. tmp/proph = the human-cart arms, tmp/proph_cvc = the CvC soak arms.
G3_DIR = os.environ.get("G3_DIR", os.path.join(ROOT, "tmp", "proph"))
CARTS = {f: os.path.join(G3_DIR, f + ".nes") for f in ("proph0", "proph1")}
fails = []
neg_cases = ([("mode%d" % md, md, 1, 5) for md in (0, 1, 2, 3, 7, 8)]
             + [("mode4_p04_0", 4, 0, 5), ("mode4_fcclear", 4, 1, 0)])
for name, md, p2, vc2 in neg_cases:
    st = {}
    for cart, path in CARTS.items():
        cpu = load_cart(path)
        setup(cpu, md, p2, vc2=vc2)
        cpu.call(0x8000)
        st[cart] = state(cpu)
        if cart == "proph1" and cpu.mem[PROPH_DIR] != 0:
            fails.append(f"{name}: PROPH_DIR fired = {cpu.mem[PROPH_DIR]:#x}")
    if st["proph0"] != st["proph1"]:
        d = [i for i, (a, b) in enumerate(zip(st["proph0"][0], st["proph1"][0])) if a != b] \
            + [0x6000 + i for i, (a, b) in enumerate(zip(st["proph0"][1], st["proph1"][1])) if a != b]
        fails.append(f"{name}: state diverges at {[hex(x) for x in d[:8]]}")
    print(f"  NEG {name:14s}: PROPH_DIR=0 and proph1==proph0 "
          f"{'OK' if not any(name in f for f in fails) else 'FAIL'}")

# positive control: mode 4 + $04=1, four hooks (frames 0,0,1,1)
cpu = load_cart(CARTS["proph1"])
setup(cpu, 4, 1)
seen = []
for hook in range(4):
    cpu.mem[0x43] = hook // 2
    cpu.mem[0xF6] = 0; cpu.mem[0xF8] = 0x02   # stale held dir: the edge-force must clear it
    cpu.call(0x8000)
    seen.append((cpu.mem[PROPH_DIR], cpu.mem[0xF6], cpu.mem[0xF8]))
ok_pos = (seen[0][0] == 0x02 and                       # LEFT latched, parity 0
          [s[1] for s in seen] == [2, 2, 0, 0] and     # press,press,release,release
          seen[0][2] == 0 and seen[1][2] == 0)         # held forced 0 on press hooks
print(f"  POS mode4_ai: PROPH_DIR={seen[0][0]:#04x} F6/hook={[s[1] for s in seen]} "
      f"F8/press={[s[2] for s in seen[:2]]} {'OK' if ok_pos else 'FAIL'}")
if not ok_pos:
    fails.append(f"positive control: {seen}")
# proph0 same state writes plain no-button (proves the instrument sees the delta)
cpu0 = load_cart(CARTS["proph0"]); setup(cpu0, 4, 1)
cpu0.mem[0xF6] = 0x99; cpu0.mem[0xF8] = 0x99
cpu0.call(0x8000)
ok_ctl = cpu0.mem[0xF6] == 0 and cpu0.mem[0xF8] == 0 and cpu0.mem[PROPH_DIR] == 0
print(f"  CTL proph0 mode4: no-button state, PROPH_DIR untouched {'OK' if ok_ctl else 'FAIL'}")
if not ok_ctl:
    fails.append("proph0 control")

print("\nGATE5:", "PASS" if not fails else "FAIL")
for f in fails:
    print("  ", f)
sys.exit(1 if fails else 0)
