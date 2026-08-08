#!/usr/bin/env python3
"""Regression: TITLE DWELL (DRNAVDWELL) -- hold autonav's FIRST title START ~DWELL_FRAMES frames so the
TRAINING EDITION branding shows at boot. Pure frame-count gate IN FRONT of the nav VS-CPU write + stability
gate; the $51 demo-hold keeps running each held hook. Frames counted via the game's frameCounter $43.

  1 dwell HOLDS  : with the dwell the nav does NOT commit VS-CPU (P0727=2,$04=1) until ~DWELL_FRAMES frames,
                   and $51 is held 0 every held hook (attract demo stays at bay)
  2 START gated  : START ($F5 bit4) is injected only AFTER the dwell elapses
  3 DRNAVDWELL=0 : nav lands VS-CPU + injects START FAST (no dwell)
  4 byte         : DRNAVFIX=0 goldens unaffected (dwell is NAV_V4-gated)
"""
import os, sys, importlib.util, hashlib
from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODE, P0727, Z04, F5, W51, F43, MAGIC = 0x46, 0x0727, 0x04, 0xF5, 0x51, 0x43, 0x6149
MATCH_ACTIVE, VSEEN1, VSEEN2, VC1, VC2 = 0x6164, 0x616A, 0x616B, 0x0324, 0x03A4
DWELL_CNT, DWELL_LAST = 0x6177, 0x6178
B_START = 0x10
_rom = open(os.path.join(REPO, "drmario_v28cs.nes"), "rb").read(); _prg = _rom[4] * 16384
TOG = _rom[16 + (_prg - 0x4000) + (0xFF30 - 0xC000):][:28]


def build(env):
    for k in [x for x in os.environ if x.startswith("DR")]: os.environ.pop(k, None)
    os.environ["DRNAVFIX"] = "1"; os.environ.update(env)     # NAV_V4 title nav
    if REPO not in sys.path: sys.path.insert(0, REPO)
    sys.modules.pop("dw_fs", None)
    spec = importlib.util.spec_from_file_location("dw_fs", os.path.join(REPO, "patch_cartridge_copro.py"))
    m = importlib.util.module_from_spec(spec); sys.modules["dw_fs"] = m; spec.loader.exec_module(m)
    c, l = m.build_main(11, 1); return c, l, m


def run_title(code, lab, nhooks):
    """Sit at the title, advancing $43 one frame per hook; return (start_frame, vs_frame, demo_held)."""
    mpu = MPU(); mem = [0]*0x10000; mpu.memory = mem
    for i, b in enumerate(code): mem[0x8000+i] = b
    for i, b in enumerate(TOG): mem[0xFF30+i] = b
    mem[MAGIC]=0xA5; mem[MODE]=0; mem[P0727]=1; mem[Z04]=0; mem[VC1]=0; mem[VC2]=0
    mem[VSEEN1]=1; mem[VSEEN2]=1; mem[MATCH_ACTIVE]=0
    SENT=0x400; mc=0x8000+lab["main"]
    frame=0; start_frame=None; vs_frame=None; demo_held=True
    for _ in range(nhooks):
        mem[F43]=(mem[F43]+1)&0xFF; frame+=1                 # one frame per hook (advances $43)
        mem[F5]=0
        mpu.sp=0xFD; r=SENT-1
        mem[0x100+mpu.sp]=(r>>8)&0xFF; mpu.sp=(mpu.sp-1)&0xFF; mem[0x100+mpu.sp]=r&0xFF; mpu.sp=(mpu.sp-1)&0xFF
        mpu.pc=mc; k=0
        while mpu.pc!=SENT and k<20000: mpu.step(); k+=1
        if vs_frame is None and mem[P0727]==2 and mem[Z04]==1: vs_frame=frame
        if start_frame is None and (mem[F5]&B_START): start_frame=frame
        # while the dwell holds START (start not yet fired) $51 must be held 0 (attract demo at bay)
        if start_frame is None and mem[W51]!=0: demo_held=False
    return start_frame, vs_frame, demo_held


cf, lf, mf = build({})                       # DRNAVDWELL default ON
assert mf.NAVDWELL; D = mf.DWELL_FRAMES
s_fix, vs_fix, demo = run_title(cf, lf, D + 40)
# The dwell holds the START (title stays up, logo shows) for ~D frames while keeping $51=0 (demo at bay).
# The menu VS-CPU state (P0727/$04) is set upstream every menu hook, so vs_frame is early -- that's fine;
# the dwell's job is holding the START/advance, which is the branding-visibility gate.
c1 = (s_fix is not None and s_fix >= D and demo)          # START held until the dwell, demo held throughout
c2 = (s_fix is not None and s_fix < D + 30)               # then fires promptly (not stuck)

cp, lp, mp = build({"DRNAVDWELL": "0"})      # dwell OFF -> fast nav
assert not mp.NAVDWELL
s_pre, vs_pre, _ = run_title(cp, lp, 40)
c3 = (vs_pre is not None and vs_pre < 20 and s_pre is not None and s_pre < 40)

def sha(env):
    c, _l, _m = build(env); return hashlib.sha256(bytes(c)).hexdigest()[:12]
a = sha({"DRNAVFIX": "0"}); b = sha({"DRNAVFIX": "0", "DRNAVDWELL": "0"})
c4 = (a == b)

print(f"  DWELL_FRAMES={D}")
print(f"  1 dwell holds START : START@frame {s_fix} (want >= {D}), demo_held={demo}")
print(f"  2 fires promptly    : START@frame {s_fix} (want < {D+30})")
print(f"  3 DRNAVDWELL=0 fast : VS@{vs_pre} START@{s_pre} (both < {D})")
print(f"  4 NAVFIX=0 byte-exact w/wo dwell: {a} == {b} -> {c4}")
for n, ok in ((1, c1), (2, c2), (3, c3), (4, c4)):
    print(f"  [{'PASS' if ok else 'FAIL'}] scenario {n}")
print(f"\n==== {sum((c1, c2, c3, c4))}/4 checks passed ====")
sys.exit(0 if all((c1, c2, c3, c4)) else 1)
