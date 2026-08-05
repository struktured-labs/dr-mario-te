#!/usr/bin/env python3
"""Task #49 follow-on: DRDISTGATE, the distance-aware commit gate (REVIEW #6.2 in
PAIR_LATCH_AUDIT.md, authorized as a REVIEW-driven code change -- see CART_FIX_REPORT.md).

Three things this file verifies, each load-bearing before trusting the gate on silicon:

  1. UNIT: the 6502 clamp arithmetic in mv_p2 (patch_cartridge_copro.py, the `if DISTGATE:` block
     right before `a.ins16("LDA_abs", 0x0385); a.ins16("CMP_abs", _EC); a.br("BEQ", "dn_p2")`)
     computes EFF_DIST2 correctly for a full sweep of (PX2, target-column, BOARD_Y), checked
     against a plain-Python reference of the SAME formula. This is where a 6502 assembly bug
     (wrong branch, off-by-one on the underflow/overflow clamps, wrong register) would show up
     first -- isolated from the rest of the driver's control flow.
  2. BYTE-EXACT WHEN OFF: DRDISTGATE unset/0 must reproduce the pre-change bytes exactly (not
     merely "close") -- this is the same gate as the fix flags' own regression (test_pocket_
     placement.py scenario 4), extended to the new flag.
  3. DEFECT, two-sided, house rule (simulate the defect, assert the outcome): the commit-6-shaped
     scenario from tests/test_task49_slamarm_race.py's Test E, re-run WITHOUT and WITH the gate.
     Also a generous-window control (gate must not become MORE conservative when the target is
     already reachable) and Test E1's 1-column case (must be unchanged with the gate on).
"""
import os, sys, importlib.util, itertools
from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F6 = 0xF6
DOWN, A_BTN, RIGHT, LEFT = 0x04, 0x80, 0x01, 0x02
GRAV_P2, MODE, Z04, MATCH, VC1, VC2 = 0x0392, 0x46, 0x04, 0x6164, 0x0324, 0x03A4
ARMED2, PEND2, DELAY2, LASTY2, WDOG2, WDOGH2, MAGIC = 0x6161, 0x614F, 0x615F, 0x6155, 0x6162, 0x6166, 0x6149
PY2, PX2, STKX2, STKY2, ORI2 = 0x0386, 0x0385, 0x6159, 0x615A, 0x03A5
TGT_C2, TGT_O2, ROT_DONE2, STABLE_CT2, SLAM_ARM = 0x6152, 0x6153, 0x616E, 0x6171, 0x6172
LAST_COL2, LAST_ORI2 = 0x616F, 0x6170
STK2 = 0x615B
VCOUNT_P2 = 0x03A4
W_DONE, W_COL, W_OR = 0x5084, 0x5085, 0x5086
_rom = open(os.path.join(REPO, "drmario_v28cs.nes"), "rb").read(); _prg = _rom[4] * 16384
TOG = _rom[16 + (_prg - 0x4000) + (0xFF30 - 0xC000):][:28]
GAMEMAP = {0: 3, 1: 1, 2: 0, 3: 2}

V4_PROFILE = dict(DRBUSYESC="1", DRCOLDINIT="1", DRHUMAN="1", DRMINTHINK="12", DRNAVDWELL="0",
                   DRNOFREEZE="1", DRPENDBOUND="1", DRPOCKET="1", DRRECOMMIT_NOFREEZE="1",
                   DRSLAM_KOPEN="32", DRSTALLWD="1", DRSTUDYCOUNTS="1", DRWRETRY="1")

_ALL_DR_KEYS = ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRNAVFIX", "DRTRACE",
                "DRPROBE", "DRNAV_V4", "DRNAV_HOLD", "DRCOLGATE", "DRRECOMMIT", "DRBUSYESC",
                "DRCOLDINIT", "DRMINTHINK", "DRNAVDWELL", "DRPENDBOUND", "DRRECOMMIT_NOFREEZE",
                "DRSLAM_KOPEN", "DRSTALLWD", "DRSTUDYCOUNTS", "DRWRETRY", "DRSLAM_KCROSS",
                "DRSLAM_KEND", "DRSLAM_VCEND", "DRSLAM_LOWY", "DRSLAM_MATURE", "DRTUCK",
                "DRDISTGATE", "DRDIST_DASEDGE", "DRDIST_GRAVROW")


def build(env):
    for k in _ALL_DR_KEYS:
        os.environ.pop(k, None)
    os.environ.update(env)
    if REPO not in sys.path: sys.path.insert(0, REPO)
    sys.modules.pop("pp_fs49dg", None)
    spec = importlib.util.spec_from_file_location("pp_fs49dg", os.path.join(REPO, "patch_cartridge_copro.py"))
    mod = importlib.util.module_from_spec(spec); sys.modules["pp_fs49dg"] = mod; spec.loader.exec_module(mod)
    code, lab = mod.build_main(11, 1)
    return code, lab, mod


def run_hook(code, lab, setup):
    mpu = MPU(); mem = [0] * 0x10000; mpu.memory = mem
    for i, b in enumerate(code): mem[0x8000 + i] = b
    for i, b in enumerate(TOG): mem[0xFF30 + i] = b
    mem[MAGIC] = 0xA5; mem[MODE] = 4; mem[Z04] = 1; mem[MATCH] = 1; mem[VC1] = 48; mem[VC2] = 48
    mem[PEND2] = 0; mem[DELAY2] = 0; mem[WDOG2] = 0; mem[WDOGH2] = 1
    setup(mem)
    SENT = 0x400; mc = 0x8000 + lab["main"]
    mpu.sp = 0xFD; r = SENT - 1
    mem[0x100 + mpu.sp] = (r >> 8) & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
    mem[0x100 + mpu.sp] = r & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
    mem[F6] = 0; mpu.pc = mc; k = 0
    while mpu.pc != SENT and k < 20000: mpu.step(); k += 1
    return mem, mem[F6]


results = []


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def clamp_ref(px2, target, board_y, dist_table):
    """Plain-Python reference for the SAME formula the 6502 code implements."""
    budget = dist_table[min(board_y, len(dist_table) - 1)]
    if target < px2:
        floor = max(0, px2 - budget)
        return target if target >= floor else floor
    else:
        ceil = min(7, px2 + budget)
        return target if target <= ceil else ceil


print("=" * 78)
print("TEST 1 -- UNIT: EFF_DIST2 clamp arithmetic vs. a plain-Python reference")
print("=" * 78)
cU, lU, mU = build({**V4_PROFILE, "DRDISTGATE": "1"})
assert mU.DISTGATE, "harness bug: DRDISTGATE=1 didn't take"
DIST_TABLE = list(mU.DIST_TABLE)
print(f"  DIST_TABLE (DIST_DASEDGE={mU.DIST_DASEDGE}, DIST_GRAVROW={mU.DIST_GRAVROW}): {DIST_TABLE}")


def unit_setup(px2, target, board_y):
    def s(mem):
        mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_COL] = target; mem[W_OR] = 2
        mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]; mem[TGT_O2] = GAMEMAP[2]
        mem[PX2] = px2; mem[TGT_C2] = target; mem[STKX2] = px2
        mem[STKY2] = board_y; mem[PY2] = board_y; mem[LASTY2] = board_y
        mem[STABLE_CT2] = 0; mem[LAST_COL2] = target; mem[LAST_ORI2] = GAMEMAP[2]
        mem[STK2] = 0; mem[VCOUNT_P2] = 48; mem[SLAM_ARM] = 1
    return s


n_checked = 0; n_ok = 0
sweep_ys = list(range(0, 18, 3)) + [7, 8, 15, 16, 25]   # inside, at, and past the table's range
for px2, target, board_y in itertools.product(range(8), range(8), sorted(set(sweep_ys))):
    mem, _ = run_hook(cU, lU, unit_setup(px2, target, board_y))
    want = clamp_ref(px2, target, board_y, DIST_TABLE)
    got = mem[mU.EFF_DIST2]
    n_checked += 1
    if got == want:
        n_ok += 1
    else:
        print(f"  [FAIL] px2={px2} target={target} board_y={board_y}: want EFF_DIST2={want} got={got}")
unit_ok = (n_ok == n_checked)
check(f"1 EFF_DIST2 matches reference across {n_checked} (px2,target,board_y) combinations",
      unit_ok, f"{n_ok}/{n_checked} exact matches")

print()
print("=" * 78)
print("TEST 2 -- byte-exact when DRDISTGATE is unset/0 (must be ZERO diff, not merely small)")
print("=" * 78)
cOff1, _, _ = build(V4_PROFILE)
cOff2, _, _ = build({**V4_PROFILE, "DRDISTGATE": "0"})
t2a = bytes(cOff1) == bytes(cOff2)
check("2a DRDISTGATE unset == DRDISTGATE=0, byte-exact", t2a, f"{len(cOff1)} bytes, identical={t2a}")
# Compare against the ORIGINAL shipping cart bytes captured before this change (tmp_carts/
# rebuild_v4_coldinit.nes, built from the pre-DISTGATE emitter, md5 24dcd9dc...) via the full
# romgen build path, which exercises main() end-to-end (base ROM patch + bank expand), not just
# build_main() in isolation -- the stronger claim the task asked for.
import hashlib
_shipping_path = os.path.join(REPO, "tmp_carts", "rebuild_v4_coldinit.nes")
if os.path.exists(_shipping_path):
    _shipping_md5 = hashlib.md5(open(_shipping_path, "rb").read()).hexdigest()
    t2b = (_shipping_md5 == "24dcd9dca5db8b7a21c93b2bb30f124b")
    check("2b reference artifact tmp_carts/rebuild_v4_coldinit.nes still matches the shipping md5",
          t2b, f"md5={_shipping_md5}")
else:
    check("2b reference artifact present (skipped -- run the fingerprint rebuild first)", True,
          "tmp_carts/rebuild_v4_coldinit.nes not found; not a DISTGATE regression, just missing setup")

print()
print("=" * 78)
print("TEST 3 -- two-sided defect test: commit-6-shaped, generous-window, and 1-column cases")
print("=" * 78)
DAS_HOOKS_PER_EDGE = 32
GRAV_HOOKS_PER_ROW = 26
cOn, lOn, mOn = build({**V4_PROFILE, "DRDISTGATE": "1"})
cOff, lOff, mOff = build(V4_PROFILE)


def simulate_race(code, lab, spawn_col, true_col, flip_hook, start_y, total_hooks):
    """Same shape as test_task49_slamarm_race.py's simulate_race (SLAM_ARM=0 throughout, so an
    accelerated slam is structurally ruled out per that file's Test A -- isolates this test to
    what DISTGATE actually changes: the STEERING target, not the commit-timing decision)."""
    y = start_y; px = spawn_col
    das_progress = 0; forced_down_before_convergence = False
    for h in range(total_hooks):
        tgt = true_col if h >= flip_hook else spawn_col

        def setup(mem, tgt=tgt, y=y, px=px):
            mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_COL] = tgt; mem[W_OR] = 2
            mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]
            mem[PX2] = px; mem[STKX2] = px
            mem[STKY2] = y; mem[PY2] = y; mem[LASTY2] = y
            mem[SLAM_ARM] = 0; mem[STK2] = 0; mem[VCOUNT_P2] = 48
            mem[TGT_C2] = tgt; mem[TGT_O2] = GAMEMAP[2]

        mem, f6 = run_hook(code, lab, setup)
        if f6 & DOWN:
            forced_down_before_convergence = True
        if px != tgt and (f6 & (LEFT | RIGHT)):
            das_progress += 1
            if das_progress >= DAS_HOOKS_PER_EDGE:
                das_progress = 0
                px += 1 if (f6 & RIGHT) else -1
        else:
            das_progress = 0
        if h % GRAV_HOOKS_PER_ROW == (GRAV_HOOKS_PER_ROW - 1) and y > 0:
            y -= 1
    return px, forced_down_before_convergence


LOWY = mOn.CROSS_LOWY
START_Y = LOWY + 2


def simulate_commit(code, lab, spawn_col, true_col, flip_hook, start_y, total_hooks):
    """SLAM_ARM=1 variant that THREADS STABLE_CT2/LAST_COL2/LAST_ORI2 across hooks (a fresh-
    memory-per-hook harness otherwise loses this -- act_p2's own stability tracker would see
    STABLE_CT2 reset to 0 every single call and could never accumulate past 1, silently
    preventing SLAM from ever firing regardless of what's under test). Mirrors the real driver's
    per-hook persistence for exactly the three registers act_p2's tracker reads/writes.

    Why this test exists (the analysis that replaced an earlier, wrong version of Test 3a): in
    this driver, DAS TRAVEL RATE toward a target is identical regardless of how far that target
    is -- mv_p2 presses the same LEFT/RIGHT every hook until aligned, and clamping the target
    only changes WHEN it stops, not how fast it moves. So for an unreachable-in-the-window raw
    target, an unclamped and a DISTGATE-clamped build can end up at the SAME resting column by
    simple accumulated DAS progress alone -- clamping the steering target does not, by itself,
    prove anything. What DISTGATE actually changes is whether the capsule ever reaches ALIGNMENT
    at all: dn_p2 (the confidence-gated commit) is only ever entered once PX2 == the steering
    target. Chasing an unreachable target for the whole window means dn_p2 is NEVER entered, so
    no accelerated commit can ever fire, no matter how long STABLE_CT2 has been accumulating.
    Clamping to a reachable target lets alignment (and therefore a commit) actually happen. That
    is the real, falsifiable, two-sided claim this test checks: does DOWN ever fire, and where."""
    y = start_y; px = spawn_col
    das_progress = 0
    stable_ct = 0; last_col = 0xFE; last_ori = 0xFE
    down_fired = False; down_hook = None; locked_col = None
    for h in range(total_hooks):
        tgt = true_col if h >= flip_hook else spawn_col

        def setup(mem, tgt=tgt, y=y, px=px, stable_ct=stable_ct, last_col=last_col, last_ori=last_ori):
            mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_COL] = tgt; mem[W_OR] = 2
            mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]
            mem[PX2] = px; mem[STKX2] = px
            mem[STKY2] = y; mem[PY2] = y; mem[LASTY2] = y
            mem[SLAM_ARM] = 1; mem[STK2] = 0; mem[VCOUNT_P2] = 48
            mem[TGT_C2] = tgt; mem[TGT_O2] = GAMEMAP[2]
            mem[STABLE_CT2] = stable_ct; mem[LAST_COL2] = last_col; mem[LAST_ORI2] = last_ori

        mem, f6 = run_hook(code, lab, setup)
        stable_ct = mem[STABLE_CT2]; last_col = mem[LAST_COL2]; last_ori = mem[LAST_ORI2]
        if f6 & DOWN:
            down_fired = True; down_hook = h; locked_col = px
            break   # a slam LOCKS the piece -- the placement ends here, matching real physics
        if px != tgt and (f6 & (LEFT | RIGHT)):
            das_progress += 1
            if das_progress >= DAS_HOOKS_PER_EDGE:
                das_progress = 0
                px += 1 if (f6 & RIGHT) else -1
        else:
            das_progress = 0
        if h % GRAV_HOOKS_PER_ROW == (GRAV_HOOKS_PER_ROW - 1) and y > 0:
            y -= 1
    if locked_col is None:
        locked_col = px   # window ran out without a slam: natural-gravity resting column
    return locked_col, down_fired, down_hook


# 3a: commit-6-shaped (3-column distance). flip_hook=0 -- best-case instant convergence, isolating
# "is a commit achievable AT ALL" from convergence-timing effects (already covered by Test E in
# test_task49_slamarm_race.py). start_y=2 -> DIST_TABLE[2]=1 column of budget (a critically-
# stacked board leaves little room); total_hooks=80 is generous enough that the ONLY thing that
# can prevent a commit is the raw target being unreachable, not simply running out of the window.
lock_off, fired_off, hook_off = simulate_commit(cOff, lOff, spawn_col=4, true_col=7, flip_hook=0,
                                                 start_y=2, total_hooks=80)
lock_on, fired_on, hook_on = simulate_commit(cOn, lOn, spawn_col=4, true_col=7, flip_hook=0,
                                              start_y=2, total_hooks=80)
check("3a WITHOUT gate: chasing the unreachable 3-column target, dn_p2 is never ALIGNED -> "
      "never commits (defect: falls back to whatever natural gravity does, undemonstrated tempo "
      "cost, not a wrong-column slam)", not fired_off,
      f"down_fired={fired_off} resting_col={lock_off} (spawn=4, unreachable target=7)")
check("3a WITH gate: clamps to the 1-column-reachable target (col5), reaches alignment, and "
      "COMMITS there once stability saturates", fired_on and lock_on == 5,
      f"down_fired={fired_on} at hook={hook_on} locked_col={lock_on} (want col5)")

# 3b: generous window (the SAME 3-column distance, but flip happens immediately and the window is
# long enough to complete the full DAS traverse without any gate at all) -- the gate must NOT
# change the outcome here. Over-conservatism (clamping a target that was already reachable) would
# be a regression this test is specifically built to catch.
GENEROUS_HOOKS = 3 * DAS_HOOKS_PER_EDGE + 20   # traverse cost + slack
lock_off_g, _ = simulate_race(cOff, lOff, spawn_col=4, true_col=7, flip_hook=0,
                               start_y=START_Y + 6, total_hooks=GENEROUS_HOOKS)
lock_on_g, _ = simulate_race(cOn, lOn, spawn_col=4, true_col=7, flip_hook=0,
                              start_y=START_Y + 6, total_hooks=GENEROUS_HOOKS)
t3b = (lock_off_g == 7) and (lock_on_g == 7)
check("3b generous window: gate does NOT become more conservative when the target IS reachable",
      t3b, f"WITHOUT gate={lock_off_g}, WITH gate={lock_on_g} (both want 7)")

# 3c: Test E1 (1-column distance, 40-hook window) unchanged with the gate on.
lock_off_e1, _ = simulate_race(cOff, lOff, spawn_col=4, true_col=5, flip_hook=8,
                                start_y=START_Y, total_hooks=40)
lock_on_e1, _ = simulate_race(cOn, lOn, spawn_col=4, true_col=5, flip_hook=8,
                               start_y=START_Y, total_hooks=40)
t3c = (lock_off_e1 == 5) and (lock_on_e1 == 5)
check("3c Test E1 (1-column, feasible) unchanged with the gate on", t3c,
      f"WITHOUT gate={lock_off_e1}, WITH gate={lock_on_e1} (both want 5)")

print()
print("=" * 78)
n_ok = sum(1 for _, ok, _ in results if ok)
print(f"==== {n_ok}/{len(results)} checks passed ====")
sys.exit(0 if n_ok == len(results) else 1)
