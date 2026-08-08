#!/usr/bin/env python3
"""Faithful-ish model of the TITLE menu (flicker + timeout + attract cycle) driving the real nav.

Gauntlet failure: DRNAVFIX consecutive-NAV_M=48 never fires START on ~3/5 cold loads -> the title
times out into the attract demo. Hypothesis: $04/$0727 FLICKER during menu redraws reset the
consecutive counter before it reaches 48. My NAV-2 test missed this by modeling a menu that never
flickers.

This models the menu as a state machine that RESPONDS to the nav's own $FF30 toggles (1P->2P->VS-CPU),
plus (a) a cold-boot garbage phase, (b) a periodic redraw flicker at VS-CPU (1 un-armed hook every R),
and (c) a title timeout at T hooks (-> attract demo). It drives the REAL main() and reports whether the
nav fires START before the timeout, across a sweep of flicker intervals R.
"""
import os, sys, importlib.util
from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WT = os.path.join(REPO, "patch_cartridge_copro.py")
MODE, Z04, P0727, Z_F5 = 0x0046, 0x04, 0x0727, 0xF5
NAV_T, NAV_MAGIC, MATCH_ACTIVE = 0x6147, 0x6149, 0x6164
NAV_STABLE, INJ_CNT = 0x6174, 0x614B
TOG_CNT = 0x6180                  # our $FF30 stub increments this (toggle counter)
VCOUNT_P1, VCOUNT_P2 = 0x0324, 0x03A4
SENTINEL = 0x0400


def load(patcher, navfix, navm=None):
    for k in ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRNAVFIX", "DRNAV_M"):
        os.environ.pop(k, None)
    os.environ["DRNOFREEZE"] = "1"; os.environ["DRSLAM"] = "1"
    os.environ["DRNAVFIX"] = "1" if navfix else "0"
    if navm is not None:
        os.environ["DRNAV_M"] = str(navm)
    d = os.path.dirname(patcher)
    for p in (d, os.path.join(d, "tests")):
        if p not in sys.path:
            sys.path.insert(0, p)
    key = f"pc_fm_{navfix}_{navm}_{abs(hash(patcher)):x}"
    spec = importlib.util.spec_from_file_location(key, patcher)
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m.build_main(11, 1), getattr(m, "NAV_M", None)


class MenuModel:
    """state 0=1P,1=2P,2=VS-CPU. $FF30 toggle advances (state+1)%3. Cold-boot garbage for K_garb
    hooks (worst case: reads armed=VS-CPU). Redraw flicker at VS-CPU: 1 un-armed hook every R."""
    def __init__(self, patcher, navfix, navm=None, K_garb=10, R=0, T=3000):
        (self.code, self.lab), self.NAV_M = load(patcher, navfix, navm)
        self.mpu = MPU(); self.mem = [0] * 0x10000; self.mpu.memory = self.mem
        for i, b in enumerate(self.code):
            self.mem[0x8000 + i] = b
        self.main_cpu = 0x8000 + self.lab["main"]
        # $FF30 stub: INC TOG_CNT ; RTS
        self.mem[0xFF30] = 0xEE; self.mem[0xFF31] = TOG_CNT & 0xFF; self.mem[0xFF32] = TOG_CNT >> 8
        self.mem[0xFF33] = 0x60
        self.mem[NAV_MAGIC] = 0xA5; self.mem[MODE] = 0x00; self.mem[MATCH_ACTIVE] = 0
        self.mem[VCOUNT_P1] = 48; self.mem[VCOUNT_P2] = 48; self.mem[NAV_T] = 0; self.mem[NAV_STABLE] = 0
        self.state = 0; self.K_garb = K_garb; self.R = R; self.T = T; self.i = 0

    def observed(self):
        if self.i < self.K_garb:
            return (1, 2)                       # cold-boot garbage that happens to LOOK like VS-CPU
        st = self.state
        p04 = 1 if st == 2 else 0
        p0727 = 2 if st >= 1 else 1
        if st == 2 and self.R and (self.i % self.R == 0):
            p04 = 0                             # periodic redraw flicker: 1 un-armed hook every R
        return (p04, p0727)

    def step(self):
        p04, p0727 = self.observed()
        self.mem[Z04] = p04; self.mem[P0727] = p0727
        tog0 = self.mem[TOG_CNT]; inj0 = self.mem[INJ_CNT]
        mpu = self.mpu; mpu.sp = 0xFD
        r = SENTINEL - 1
        mpu.memory[0x0100 + mpu.sp] = (r >> 8) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.memory[0x0100 + mpu.sp] = r & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = self.main_cpu; n = 0
        while mpu.pc != SENTINEL and n < 20000:
            mpu.step(); n += 1
        toggled = self.mem[TOG_CNT] != tog0
        injected = self.mem[INJ_CNT] != inj0
        if toggled and self.i >= self.K_garb:   # toggles during garbage are lost (menu not ready)
            self.state = (self.state + 1) % 3
        self.i += 1
        return injected

    def run(self):
        """Return the hook index of the first START, or None if the title times out (-> demo)."""
        premature = None
        while self.i < self.T:
            armed_real = (self.i >= self.K_garb and self.state == 2)
            if self.step():
                if not armed_real and premature is None:
                    premature = self.i - 1       # START fired while NOT genuinely at VS-CPU
                return dict(start_hook=self.i - 1, premature=premature, state=self.state)
        return dict(start_hook=None, premature=premature, state=self.state)   # timed out -> attract demo


results = []
def check(name, cond, detail=""):
    results.append(cond); print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


FAB = None   # filled below with the fab7fc7 (consecutive) patcher path
def make_prefix():
    global FAB
    import subprocess
    FAB = os.path.join(REPO, ".navprev.py")
    src = subprocess.check_output(["git", "-C", REPO, "show", "fab7fc7:patch_cartridge_copro.py"])
    open(FAB, "wb").write(src)
make_prefix()

print("FLICKER SWEEP: does the nav fire START before the title timeout, vs redraw-flicker interval R?")
print(f"  (menu: 10-hook garbage, toggles 1P->2P->VS-CPU, timeout at 3000 hooks ~= title ~10 s)")
print(f"  {'R':>4} | {'consecutive (fab7fc7)':>24} | {'leaky (this branch)':>22}")
consec_fail = leaky_ok = 0
for R in (0, 4, 8, 16, 24, 40):
    c = MenuModel(FAB, navfix=True, K_garb=10, R=R).run()          # fab7fc7 = consecutive NAV_M=48
    l = MenuModel(WT, navfix=True, K_garb=10, R=R).run()           # this branch = leaky
    cs = "START@%d" % c["start_hook"] if c["start_hook"] is not None else "TIMEOUT->demo"
    ls = "START@%d" % l["start_hook"] if l["start_hook"] is not None else "TIMEOUT->demo"
    print(f"  {R:>4} | {cs:>24} | {ls:>22}")
    if R and c["start_hook"] is None:
        consec_fail += 1
    if l["start_hook"] is not None and not l["premature"]:
        leaky_ok += 1
check("MODEL reproduces the gauntlet failure: consecutive counter TIMES OUT under flicker (R>0)",
      consec_fail >= 1, f"consecutive timed out for {consec_fail} of the flicker cases")
check("FIX: the leaky counter fires a clean (non-premature) START at EVERY flicker interval",
      leaky_ok == 6, f"leaky clean-start count = {leaky_ok}/6")

# garbage rejection: the leaky counter must NOT fire during the cold-boot garbage window
print("GARBAGE: cold-boot garbage that looks like VS-CPU for K hooks must not fire a premature START")
for K in (5, 10, 15):
    l = MenuModel(WT, navfix=True, K_garb=K, R=8).run()
    check(f"leaky: garbage K={K} hooks -> no premature START (fires only on genuine VS-CPU)",
          l["premature"] is None and l["start_hook"] is not None,
          f"start@{l['start_hook']} premature={l['premature']}")

if FAB and os.path.exists(FAB):
    os.remove(FAB)
print()
npass = sum(1 for c in results if c)
print(f"==== {npass}/{len(results)} model checks passed ====")
sys.exit(0 if npass == len(results) else 1)
