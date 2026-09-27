#!/usr/bin/env python3
"""DRRELATCH -- RE-LATCH-ON-CHANGE, the classes-b/c/d fix from the execution-fidelity
census (wf_5583bec4-ed9, 2026-08-09). The census flip arm showed the driver adopts a
mid-pill commit flip's COLUMN 922/922 but keeps the PRE-flip ORIENTATION 112/922 (true
backward horizontals at the correct column + real nonsensical verticals), because the
nf2_* live-publish path refreshes TGT_C2 every hook while ROT_DONE2 keeps TGT_O2
feasibility-locked; RECOMMIT only re-opens the latch once, at DONE, in handle().

House rule (test the DEFECT, not the fix -- [[test-defect-not-fix]]): every scenario is
run TWO-SIDED where meaningful.

  A. DEFECT REPRODUCES with DRRELATCH=0: mid-pill flip -> post-flip column adopted,
     PRE-flip orientation kept, latch never re-opens (the census's stale adoption).
  B. FIX with DRRELATCH=1 (high capsule): same flip -> post-flip MAPPED orientation
     adopted, ROT_DONE2 re-opened, act_p2 presses A to rotate this very hook.
  C. CROSS_LOWY NO-BACKWARDS-LOCK INVARIANT with the fix ON: same flip but the capsule
     is BELOW the line -> committed orientation kept, latch intact, no rotation press.
     Also the exact-boundary case (Y == CROSS_LOWY -> re-latch allowed, matching
     RECOMMIT's own BCC semantics).
  D. NO-CHANGE GUARD with the fix ON: published orient maps to the latched value ->
     latch stays closed (no spurious re-open / rotation churn).
  E. RE-LATCH COMPLETES: after the re-open, once the game orient reaches the new
     target, p2_commit latches ROT_DONE2 again (on-change, not permanently open).
  F. BYTE-NEUTRAL: DRRELATCH unset == DRRELATCH=0, byte-identical build_main output.
     (The stronger proof -- the v6b manifest study2p-fix-v6-boardhold.json replays to
     49e10ce9 byte-exact with the flag off -- is run at romgen level, not here.)
"""
import os, sys, importlib.util
from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F6, F8 = 0xF6, 0xF8
A_BTN = 0x80
MODE, Z04, MATCH, VC1, VC2 = 0x46, 0x04, 0x6164, 0x0324, 0x03A4
ARMED2, PEND2, DELAY2, LASTY2, WDOG2, WDOGH2, MAGIC = 0x6161, 0x614F, 0x615F, 0x6155, 0x6162, 0x6166, 0x6149
PY2, PX2, STKX2, STKY2, ORI2 = 0x0386, 0x0385, 0x6159, 0x615A, 0x03A5
TGT_C2, TGT_O2, ROT_DONE2, STABLE_CT2, SLAM_ARM = 0x6152, 0x6153, 0x616E, 0x6171, 0x6172
LAST_COL2, LAST_ORI2, STK2 = 0x616F, 0x6170, 0x615B
W_DONE, W_COL, W_OR = 0x5084, 0x5085, 0x5086   # DRPOCKET=1 -> W2_BASE=$5000
_rom = open(os.path.join(REPO, "drmario_v28cs.nes"), "rb").read(); _prg = _rom[4] * 16384
TOG = _rom[16 + (_prg - 0x4000) + (0xFF30 - 0xC000):][:28]
GAMEMAP = {0: 3, 1: 1, 2: 0, 3: 2}   # copro orient -> game orient, as handle()/nf2 map

# the v6b cart's own profile (RECIPE_v6b_boardhold_fixfl.json), minus the build-id stamp
V6B_PROFILE = dict(DRBUSYESC="1", DRCOLDINIT="1", DRHUMAN="1", DRMINTHINK="12", DRNAVDWELL="0",
                   DRNOFREEZE="1", DRPENDBOUND="1", DRPOCKET="1", DRRECOMMIT_NOFREEZE="1",
                   DRSLAM_KOPEN="32", DRSTALLWD="1", DRSTUDYCOUNTS="1", DRWRETRY="1",
                   DRBUILDID="0")

_ALL_DR_KEYS = ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRNAVFIX", "DRTRACE",
                "DRPROBE", "DRNAV_V4", "DRNAV_HOLD", "DRCOLGATE", "DRRECOMMIT", "DRBUSYESC",
                "DRCOLDINIT", "DRMINTHINK", "DRNAVDWELL", "DRPENDBOUND", "DRRECOMMIT_NOFREEZE",
                "DRSLAM_KOPEN", "DRSTALLWD", "DRSTUDYCOUNTS", "DRWRETRY", "DRSLAM_KCROSS",
                "DRSLAM_KEND", "DRSLAM_VCEND", "DRSLAM_LOWY", "DRSLAM_MATURE", "DRTUCK",
                "DRDISTGATE", "DRDIST_DASEDGE", "DRDIST_GRAVROW", "DRRELATCH", "DRBUILDID")


def build(env):
    for k in _ALL_DR_KEYS:
        os.environ.pop(k, None)
    os.environ.update(env)
    if REPO not in sys.path: sys.path.insert(0, REPO)
    sys.modules.pop("pp_relatch", None)
    spec = importlib.util.spec_from_file_location("pp_relatch", os.path.join(REPO, "patch_cartridge_copro.py"))
    mod = importlib.util.module_from_spec(spec); sys.modules["pp_relatch"] = mod; spec.loader.exec_module(mod)
    code, lab = mod.build_main(11, 1)
    return code, lab, mod


def run_hook(code, lab, mem=None, setup=None):
    """One driver hook (a full `main`). Pass mem back in to run consecutive hooks."""
    mpu = MPU()
    if mem is None:
        mem = [0] * 0x10000
        mem[MAGIC] = 0xA5; mem[MODE] = 4; mem[Z04] = 1; mem[MATCH] = 1; mem[VC1] = 48; mem[VC2] = 48
        mem[PEND2] = 0; mem[DELAY2] = 0; mem[WDOG2] = 0; mem[WDOGH2] = 1
    mpu.memory = mem
    for i, b in enumerate(code): mem[0x8000 + i] = b
    for i, b in enumerate(TOG): mem[0xFF30 + i] = b
    if setup: setup(mem)
    SENT = 0x400; mc = 0x8000 + lab["main"]
    mpu.sp = 0xFD; r = SENT - 1
    mem[0x100 + mpu.sp] = (r >> 8) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
    mem[0x100 + mpu.sp] = r & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
    mem[F6] = 0; mem[F8] = 0; mpu.pc = mc; k = 0
    while mpu.pc != SENT and k < 20000: mpu.step(); k += 1
    assert k < 20000, "hook did not return"
    return mem


# The census flip shape (class b, backward horizontal): capsule already rotated+latched to
# the PRE-flip target, copro's running best then flips to a NEW column with the 180-degree
# horizontal phase. Copro-space: pre 2 (game 0), post 0 (game 3).
PRE_OR_C, POST_OR_C = 2, 0
PRE_OR_G, POST_OR_G = GAMEMAP[PRE_OR_C], GAMEMAP[POST_OR_C]
OLD_COL, NEW_COL, SPAWN_COL = 6, 2, 3


def flip_setup(board_y):
    def s(mem):
        mem[ARMED2] = 1                    # mid-search: the flip is a LIVE-publish change
        mem[W_DONE] = 0                    # (same byte as W_GO on this cart; 0 = not DONE)
        mem[W_COL] = NEW_COL; mem[W_OR] = POST_OR_C
        mem[ROT_DONE2] = 1                 # orient latched to the PRE-flip target ...
        mem[TGT_O2] = PRE_OR_G; mem[ORI2] = PRE_OR_G   # ... and already reached
        mem[TGT_C2] = OLD_COL
        mem[PX2] = SPAWN_COL; mem[PY2] = board_y
        mem[STKX2] = SPAWN_COL; mem[STKY2] = board_y; mem[LASTY2] = board_y
        mem[STABLE_CT2] = 5; mem[LAST_COL2] = OLD_COL; mem[LAST_ORI2] = PRE_OR_G
        mem[STK2] = 0; mem[VC2] = 48; mem[SLAM_ARM] = 1
        mem[WDOG2] = 40; mem[WDOGH2] = 0   # well past MIN_THINK, not past the 256-hook escape
    return s


results = []


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


print("=" * 78)
print("TEST A -- DEFECT REPRODUCES (DRRELATCH off): flip adopts column, keeps stale orient")
print("=" * 78)
cOFF, lOFF, mOFF = build(dict(V6B_PROFILE))
assert not mOFF.RELATCH, "harness bug: RELATCH should be off by default"
HI_Y = 12
mem = run_hook(cOFF, lOFF, setup=flip_setup(HI_Y))
check("A1 column adopted (the 922/922 half)", mem[TGT_C2] == NEW_COL,
      f"TGT_C2={mem[TGT_C2]} want {NEW_COL}")
check("A2 orientation STALE (the 112/922 half)", mem[TGT_O2] == PRE_OR_G,
      f"TGT_O2={mem[TGT_O2]} stays pre-flip {PRE_OR_G}")
check("A3 latch never re-opens", mem[ROT_DONE2] == 1, f"ROT_DONE2={mem[ROT_DONE2]}")

print("=" * 78)
print("TEST B -- FIX (DRRELATCH=1, high capsule): flip adopts column AND orientation")
print("=" * 78)
cON, lON, mON = build(dict(V6B_PROFILE, DRRELATCH="1"))
assert mON.RELATCH, "harness bug: DRRELATCH=1 didn't take"
assert mON.CROSS_LOWY == 8, f"profile drift: CROSS_LOWY={mON.CROSS_LOWY}"
mem = run_hook(cON, lON, setup=flip_setup(HI_Y))
check("B1 column adopted", mem[TGT_C2] == NEW_COL, f"TGT_C2={mem[TGT_C2]}")
check("B2 post-flip MAPPED orient adopted", mem[TGT_O2] == POST_OR_G,
      f"TGT_O2={mem[TGT_O2]} want {POST_OR_G} (game space)")
check("B3 latch re-opened", mem[ROT_DONE2] == 0, f"ROT_DONE2={mem[ROT_DONE2]}")
check("B4 act_p2 rotates toward it this hook", mem[F6] & A_BTN == A_BTN and mem[F8] == 0,
      f"F6={mem[F6]:#04x} F8={mem[F8]:#04x} (want A edge-press)")

print("=" * 78)
print("TEST C -- CROSS_LOWY invariant (fix ON, capsule LOW): committed orient is kept")
print("=" * 78)
LO_Y = mON.CROSS_LOWY - 1
mem = run_hook(cON, lON, setup=flip_setup(LO_Y))
check("C1 orientation kept below the line", mem[TGT_O2] == PRE_OR_G, f"TGT_O2={mem[TGT_O2]}")
check("C2 latch intact", mem[ROT_DONE2] == 1, f"ROT_DONE2={mem[ROT_DONE2]}")
check("C3 no rotation press", mem[F6] & A_BTN == 0, f"F6={mem[F6]:#04x}")
check("C4 column still refined (column-only mode)", mem[TGT_C2] == NEW_COL,
      f"TGT_C2={mem[TGT_C2]}")
mem = run_hook(cON, lON, setup=flip_setup(mON.CROSS_LOWY))
check("C5 boundary Y==CROSS_LOWY re-latches (BCS, matches RECOMMIT's BCC low->keep)",
      mem[ROT_DONE2] == 0 and mem[TGT_O2] == POST_OR_G,
      f"ROT_DONE2={mem[ROT_DONE2]} TGT_O2={mem[TGT_O2]}")

print("=" * 78)
print("TEST D -- no-change guard (fix ON): same published orient does not re-open")
print("=" * 78)


def nochange_setup(mem):
    flip_setup(HI_Y)(mem)
    mem[W_OR] = PRE_OR_C          # publishes the SAME orient the latch already holds
mem = run_hook(cON, lON, setup=nochange_setup)
check("D1 latch stays closed", mem[ROT_DONE2] == 1, f"ROT_DONE2={mem[ROT_DONE2]}")
check("D2 orient unchanged", mem[TGT_O2] == PRE_OR_G, f"TGT_O2={mem[TGT_O2]}")
check("D3 no rotation press", mem[F6] & A_BTN == 0, f"F6={mem[F6]:#04x}")

print("=" * 78)
print("TEST E -- re-latch completes: orient reached -> p2_commit closes the latch again")
print("=" * 78)
mem = run_hook(cON, lON, setup=flip_setup(HI_Y))
assert mem[ROT_DONE2] == 0 and mem[TGT_O2] == POST_OR_G, "precondition (Test B) failed"
mem[ORI2] = POST_OR_G             # the game has now performed the rotation
mem[F6] = 0; mem[F8] = 0
mem = run_hook(cON, lON, mem=mem)
check("E1 latch closed again with the new orient",
      mem[ROT_DONE2] == 1 and mem[TGT_O2] == POST_OR_G,
      f"ROT_DONE2={mem[ROT_DONE2]} TGT_O2={mem[TGT_O2]}")

print("=" * 78)
print("TEST F -- byte-neutral: DRRELATCH unset == DRRELATCH=0 (build_main identical)")
print("=" * 78)
cDEF, _, mDEF = build(dict(V6B_PROFILE))
cZERO, _, _ = build(dict(V6B_PROFILE, DRRELATCH="0"))
check("F1 unset == 0, byte-identical", bytes(cDEF) == bytes(cZERO),
      f"{len(cDEF)} vs {len(cZERO)} bytes")
check("F2 fix build actually differs (not a no-op flag)", bytes(cDEF) != bytes(cON),
      f"{len(cDEF)} vs {len(cON)} bytes")

print()
fails = [r for r in results if not r[1]]
print(f"{len(results) - len(fails)}/{len(results)} checks passed")
if fails:
    for name, _, detail in fails:
        print(f"  FAILED: {name}: {detail}")
    sys.exit(1)
print("ALL PASS")
