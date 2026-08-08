#!/usr/bin/env python3
"""DRNAVFIX byte-exactness pins + two anti-premature-START smoke checks.

DRNAVFIX is now v4: it directly WRITES coherent VS-CPU ($0727=2,$04=1) each menu hook and gates the
mode-independent full-clear auto-advance to play/post (mode>=4). The real ~1-in-3 mis-land was the
full-clear FALSE-firing at the title on inherited MATCH_ACTIVE (injecting START, skipping the autonav
-> 1P) -- see tests/test_nav_fullclear.py for the reproduce-then-fix, test_nav_parity.py for the
inherited-state sweep, and test_nav_demo_hold.py for the secondary attract-demo guard.

This file retains: (NAV-1/NAV-2) smoke checks that v4 does NOT premature-START on a cold-boot menu
transient and DOES eventually fire START on a stable VS-CPU state (driving the REAL main() at mode 0
in py65 with a stubbed $FF30 and counting START injections at $614B); and the BYTE-EXACTNESS golden
pins for DRNAVFIX=0 (== the b92ec32 base) and DRSLAM=0 DRNAVFIX=0 (== the c300acb canonical).
"""
import os, sys, importlib.util, hashlib
from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WT = os.path.join(REPO, "patch_cartridge_copro.py")

MODE, Z04, P0727 = 0x0046, 0x04, 0x0727
Z_F5 = 0xF5
NAV_T, NAV_MAGIC, MATCH_ACTIVE = 0x6147, 0x6149, 0x6164
NAV_STABLE = 0x6174
INJ_CNT = 0x614B                 # DBG: START-inject counter (inject() does INC $614B)
VCOUNT_P1, VCOUNT_P2 = 0x0324, 0x03A4
SENTINEL = 0x0400


def load_build(navfix, slam="0", patcher=WT):
    for k in ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRNAVFIX", "DRNAV_M", "DRNAVDWELL"):
        os.environ.pop(k, None)
    os.environ["DRNOFREEZE"] = "1"                 # AB cart context
    os.environ["DRSLAM"] = slam
    os.environ["DRNAVFIX"] = "1" if navfix else "0"
    os.environ["DRNAVDWELL"] = "0"                 # title dwell is orthogonal to the nav-gate logic under test
    d = os.path.dirname(patcher)
    for p in (d, os.path.join(d, "tests")):
        if p not in sys.path:
            sys.path.insert(0, p)
    key = f"pc_nav_{navfix}_{slam}_{abs(hash(patcher)):x}"
    spec = importlib.util.spec_from_file_location(key, patcher)
    m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m.build_main(11, 1), getattr(m, "NAV_M", 48)


class NavSim:
    """Drive main() at the title (mode 0). $FF30 (the menu toggle) is stubbed RTS; the menu state
    ($04/$0727) is scripted per hook, so we observe only the driver's START-injection decision."""
    def __init__(self, navfix):
        (self.code, self.lab), self.NAV_M = load_build(navfix)
        self.mpu = MPU(); self.mem = [0] * 0x10000; self.mpu.memory = self.mem
        for i, b in enumerate(self.code):
            self.mem[0x8000 + i] = b
        self.main_cpu = 0x8000 + self.lab["main"]
        self.mem[0xFF30] = 0x60                    # RTS stub for JSR $FF30 (toggle)
        self.mem[NAV_MAGIC] = 0xA5                 # skip power-on init (we set state explicitly)
        self.mem[MODE] = 0x00                      # title screen
        self.mem[MATCH_ACTIVE] = 0                 # not in a match -> full-clear detect stays off
        self.mem[VCOUNT_P1] = 48; self.mem[VCOUNT_P2] = 48
        self.mem[NAV_T] = 0                         # intro just zeroed it -> START window open
        self.mem[NAV_STABLE] = 0

    def hook(self, p04, p0727):
        """Set the scripted menu state, run one main() hook, return True if it injected START."""
        self.mem[Z04] = p04; self.mem[P0727] = p0727
        before = self.mem[INJ_CNT]
        mpu = self.mpu; mpu.sp = 0xFD
        r = SENTINEL - 1
        mpu.memory[0x0100 + mpu.sp] = (r >> 8) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.memory[0x0100 + mpu.sp] = r & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = self.main_cpu; n = 0
        while mpu.pc != SENTINEL and n < 20000:
            mpu.step(); n += 1
        assert n < 20000, "main did not return"
        return self.mem[INJ_CNT] != before

    def run(self, timeline):
        """timeline: list of (p04, p0727) per hook. Returns the hook indices that injected START."""
        return [i for i, (a, b) in enumerate(timeline) if self.hook(a, b)]


results = []
def check(name, cond, detail=""):
    results.append(cond); print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


# ---------------------------------------------------------------- NAV-1: cold-boot garbage transient
# The title fade-in: $04 reads garbage-nonzero ($01) with $0727 garbage-2 for the first 10 hooks,
# then the menu inits the 1P default ($04=0,$0727=1). NAV_T starts at 0 so the START window is open.
print("NAV-1: cold-boot transient -- garbage $04!=0 for 10 hooks, then the menu inits 1P")
GARBAGE = [(0x01, 0x02)] * 10          # transient: nonzero $04, $0727 not the settled VS-CPU value
INIT_1P = [(0x00, 0x01)] * 20          # menu settles to the 1P default
tl = GARBAGE + INIT_1P
canon_inj = NavSim(navfix=False).run(tl)
fix_inj = NavSim(navfix=True).run(tl)
# injections that occurred DURING the transient (hooks < 10) are premature 1P-mis-land STARTs
canon_premature = [i for i in canon_inj if i < 10]
fix_premature = [i for i in fix_inj if i < 10]
check("NAV-1: canonical nav fires a PREMATURE START during the garbage transient (the 1P mis-land)",
      len(canon_premature) > 0, f"canonical injected at hooks {canon_premature}")
check("NAV-1: DRNAVFIX withholds START through the entire transient (no 1P mis-land)",
      len(fix_premature) == 0, f"DRNAVFIX injects at {fix_inj} (none < 10)")

# ---------------------------------------------------------------- NAV-2: genuine VS-CPU still starts
# The legitimate case: the toggles have reached VS-CPU ($04=1,$0727=2), held stable. DRNAVFIX must
# still fire START (once NAV_M armed hooks accrue and a START window opens) -- it must not hang.
print("NAV-2: genuine VS-CPU ($04=1,$0727=2) held stable -- DRNAVFIX still fires START")
s = NavSim(navfix=True)
vs_inj = s.run([(0x01, 0x02)] * (s.NAV_M + 40))
check("NAV-2: DRNAVFIX DOES fire START on a stable VS-CPU state (does not hang)",
      len(vs_inj) > 0, f"first START at hook {vs_inj[0] if vs_inj else None} (NAV_M={s.NAV_M})")
check("NAV-2: and it waits out the stability floor first (first START only after >= NAV_M hooks)",
      bool(vs_inj) and vs_inj[0] >= s.NAV_M, f"first START hook={vs_inj[0] if vs_inj else None} NAV_M={s.NAV_M}")

# NAV-3/NAV-4 (the v3 stability-gate "conjunction-rejects-garbage" and "delayed-VS-phase-START"
# assertions) were REMOVED when DRNAVFIX became v4: v4 does not respond to a scripted menu timeline --
# it directly WRITES coherent VS-CPU ($0727=2,$04=1) each menu hook and gates the full-clear
# auto-advance to mode>=4. v4's decision logic + the real mis-land root cause are covered by
# tests/test_nav_fullclear.py (full-clear false-fire), test_nav_parity.py (inherited-state sweep),
# and test_nav_demo_hold.py (attract-demo guard). NAV-1/NAV-2 above still hold for v4 (it does not
# premature-START on a cold-boot transient, and it does eventually fire START on a stable VS-CPU).

# ---------------------------------------------------------------- byte-exactness
print("BYTE-EXACT: DRNAVFIX=0 == the b92ec32 base; DRSLAM=0 DRNAVFIX=0 == c300acb canonical")
def sha(code):
    return hashlib.sha256(bytes(code)).hexdigest()[:16]
BASE = "3fe9515d3872cf1a"       # build_main(11,1) at b92ec32 (DRSLAM=1 maturity, no navfix), ab variant
CANON = "855ca99a2cc3c8aa"      # build_main(11,1) at c300acb (full canonical), ab variant
(navoff, _lab), _ = load_build(navfix=False, slam="1")
check("BYTE-EXACT: DRNAVFIX=0 (slam on) == b92ec32 base golden", sha(navoff) == BASE,
      f"got {sha(navoff)} want {BASE}")
(full_canon, _lab), _ = load_build(navfix=False, slam="0")
check("BYTE-EXACT: DRSLAM=0 DRNAVFIX=0 == c300acb canonical golden", sha(full_canon) == CANON,
      f"got {sha(full_canon)} want {CANON}")

print()
npass = sum(1 for c in results if c)
print(f"==== {npass}/{len(results)} checks passed ====")
sys.exit(0 if npass == len(results) else 1)
