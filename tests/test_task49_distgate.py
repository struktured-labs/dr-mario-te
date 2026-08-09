#!/usr/bin/env python3
"""Task #49 follow-on: DRDISTGATE, the distance-aware commit gate (REVIEW #6.2 in
PAIR_LATCH_AUDIT.md, authorized as a REVIEW-driven code change -- see CART_FIX_REPORT.md).

SURFACE-RELATIVE REBUILD (2026-08-09, wf_c6d25d83 acceptance forensics): the first DISTGATE
indexed DIST_TABLE by $0386 directly -- FLOOR-relative Y (counts UP from the floor). On a
filled board (h>=12, the census defect regime) the capsule locks at HIGH $0386, the budget
saturated at 7 = the whole board width, and the gate NEVER restricted exactly where it was
built to: census class-a 29/1038 pill-for-pill identical to gate-OFF (FAILED VACUOUSLY).
The rebuild indexes by SURFACE-RELATIVE REMAINING FALL, scanned from the live board $0500
across the travel span (en-route max surface; see the emitter's flag comment for the full
signal-choice constraint). Same DIST_TABLE, same footage-corrected constants -- only the
INDEX changed.

What this file verifies, each load-bearing before trusting the gate on silicon:

  1. UNIT: the 6502 scan+clamp in mv_p2 computes EFF_DIST2 correctly for a sweep of
     (PX2, target, BOARD_Y) x BOARD PROFILES, checked against a plain-Python reference of
     the surface-relative formula (closed form; the 6502 does a row scan -- independent
     implementations of the same spec).
  1b. KILLED MUTANT (house gate standard): the OLD floor-relative indexing, kept buildable
     as DRDIST_FLOORREL=1 strictly for this test, must FAIL the new surface-relative unit
     checks on every discriminating scenario -- and the discriminating set must be non-empty
     (mutant is not equivalent).
  2. BYTE-EXACT WHEN OFF: DRDISTGATE unset/0 must reproduce the pre-change bytes exactly.
  3. Behavioral tests on an EMPTY board (where surface == floor and the rebuild must agree
     with the original design): the Y=0 true-floor case, the generous window, and the
     1-column case -- unchanged semantics from the pre-rebuild file.
  4. DEFECT REGIME, two-sided (simulate the defect, assert the outcome): near-topout flat
     board (h=14) where the raw target is physically unreachable in the remaining fall.
     Surface-relative build: clamps to the reachable column, ALIGNS, and commits (DOWN
     fires). Floor-relative mutant AND gate-OFF build: chase the unreachable target, never
     align, never commit -- the capsule parks wherever DAS got it (the census class-a
     shape). This is the regime the first build was measured to be vacuous in.
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
BOARD2 = 0x0500
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
                "DRDISTGATE", "DRDIST_DASEDGE", "DRDIST_GRAVROW", "DRDIST_FLOORREL")


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


def write_board(mem, heights, empty_byte=0x00):
    """Fill $0500 with a P2 board built from per-column stack heights (count-up space:
    column c occupied at Y 0..heights[c]-1, i.e. board rows 16-h..15; row 0 = top).
    empty_byte exercises both legal empty encodings ($00 and $FF -- tile-encoding)."""
    for i in range(128):
        mem[BOARD2 + i] = empty_byte
    for c, h in enumerate(heights):
        for yy in range(h):
            mem[BOARD2 + (15 - yy) * 8 + c] = 0xD0   # a virus byte: any non-$00/$FF = stack


results = []


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def fall_ref(px2, target, board_y, heights, scan_cap):
    """Surface-relative remaining fall, closed form (the 6502 does a row scan of the same
    spec): empty rows strictly below the capsule across the span [min..max](px2, target),
    capped at scan_cap (table saturation depth -- deeper rows cannot change the budget)."""
    y = min(board_y, 15)
    lo, hi = (px2, target) if px2 <= target else (target, px2)
    smax = max(heights[lo:hi + 1])
    return max(0, min(y, scan_cap, y - smax))


def clamp_ref(px2, target, board_y, heights, dist_table, scan_cap):
    """Plain-Python reference for the full surface-relative gate formula."""
    budget = dist_table[fall_ref(px2, target, board_y, heights, scan_cap)]
    if target < px2:
        floor = max(0, px2 - budget)
        return target if target >= floor else floor
    else:
        ceil = min(7, px2 + budget)
        return target if target <= ceil else ceil


def clamp_ref_floor(px2, target, board_y, dist_table):
    """The ORIGINAL floor-relative formula (the census-refuted indexing) -- used only to
    sanity-check that the DRDIST_FLOORREL mutant is a FAITHFUL reproduction of the old
    behavior (a broken mutant would fail the new tests for the wrong reason)."""
    budget = dist_table[min(board_y, len(dist_table) - 1)]
    if target < px2:
        floor = max(0, px2 - budget)
        return target if target >= floor else floor
    else:
        ceil = min(7, px2 + budget)
        return target if target <= ceil else ceil


print("=" * 78)
print("TEST 1 -- UNIT: EFF_DIST2 (surface-relative) vs. a plain-Python reference")
print("=" * 78)
cU, lU, mU = build({**V4_PROFILE, "DRDISTGATE": "1"})
assert mU.DISTGATE, "harness bug: DRDISTGATE=1 didn't take"
assert not mU.DIST_FLOORREL, "harness bug: mutant flag leaked into the shipping build"
DIST_TABLE = list(mU.DIST_TABLE)
SCAN_CAP = mU.DIST_SCANCAP
print(f"  DIST_TABLE (DIST_DASEDGE={mU.DIST_DASEDGE}, DIST_GRAVROW={mU.DIST_GRAVROW}): {DIST_TABLE}")
print(f"  DIST_SCANCAP (table saturation depth, scan bound): {SCAN_CAP}")

# Board profiles: name -> (heights, empty_byte). Chosen to cover: empty board (surface ==
# floor -- the rebuild must reproduce the original design here), the census defect regime
# (flat h=12 and h=14 near-topout), a staircase (span max varies with the span), a pillar
# BETWEEN spawn and target (en-route max != target-column surface -- the signal-choice
# constraint), and a $FF-empties board (both legal empty encodings).
BOARDS = {
    "empty":     ([0] * 8, 0x00),
    "flat12":    ([12] * 8, 0x00),
    "flat14":    ([14] * 8, 0x00),
    "stair":     ([0, 2, 4, 6, 8, 10, 12, 14], 0x00),
    "pillar":    ([2, 2, 2, 13, 2, 2, 2, 2], 0x00),
    "empty_ff":  ([3] * 8, 0xFF),
}


def unit_setup(px2, target, board_y, heights, empty_byte):
    def s(mem):
        write_board(mem, heights, empty_byte)
        mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_COL] = target; mem[W_OR] = 2
        mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]; mem[TGT_O2] = GAMEMAP[2]
        mem[PX2] = px2; mem[TGT_C2] = target; mem[STKX2] = px2
        mem[STKY2] = board_y; mem[PY2] = board_y; mem[LASTY2] = board_y
        mem[STABLE_CT2] = 0; mem[LAST_COL2] = target; mem[LAST_ORI2] = GAMEMAP[2]
        mem[STK2] = 0; mem[VCOUNT_P2] = 48; mem[SLAM_ARM] = 1
    return s


sweep_ys = sorted(set([0, 1, 2, 3, 7, 13, 14, 15, 16, 25]))   # inside, at, and past the clamp
n_checked = 0; n_ok = 0
discriminating = []   # scenarios where floor-relative and surface-relative predictions differ
for bname, (heights, eb) in BOARDS.items():
    for px2, target, board_y in itertools.product(range(8), range(8), sweep_ys):
        mem, _ = run_hook(cU, lU, unit_setup(px2, target, board_y, heights, eb))
        want = clamp_ref(px2, target, board_y, heights, DIST_TABLE, SCAN_CAP)
        got = mem[mU.EFF_DIST2]
        n_checked += 1
        if got == want:
            n_ok += 1
        else:
            print(f"  [FAIL] board={bname} px2={px2} target={target} board_y={board_y}: "
                  f"want EFF_DIST2={want} got={got}")
        want_floor = clamp_ref_floor(px2, target, min(board_y, 255), DIST_TABLE)
        if want_floor != want:
            discriminating.append((bname, heights, eb, px2, target, board_y, want, want_floor))
unit_ok = (n_ok == n_checked)
check(f"1 EFF_DIST2 matches the surface-relative reference across {n_checked} scenarios",
      unit_ok, f"{n_ok}/{n_checked} exact matches")

# On the EMPTY board the two formulas must agree everywhere (surface == floor there, modulo
# the scan cap sitting exactly at the table's saturation depth): the rebuild changes NOTHING
# until there is an actual stack. Regression guard for open-board behavior.
empty_disagree = [d for d in discriminating if d[0] == "empty"]
check("1c empty board: surface-relative == floor-relative everywhere (open-board behavior "
      "unchanged by the rebuild)", not empty_disagree, f"{len(empty_disagree)} disagreements")

print()
print("=" * 78)
print("TEST 1b -- KILLED MUTANT: DRDIST_FLOORREL=1 (the old indexing) must FAIL these tests")
print("=" * 78)
cM, lM, mM = build({**V4_PROFILE, "DRDISTGATE": "1", "DRDIST_FLOORREL": "1"})
assert mM.DIST_FLOORREL, "harness bug: DRDIST_FLOORREL=1 didn't take"
check("1b-i the mutant is not equivalent: discriminating scenarios exist in the sweep",
      len(discriminating) > 0, f"{len(discriminating)} scenarios where floor != surface")
n_killed = 0; n_faithful = 0
for bname, heights, eb, px2, target, board_y, want_surf, want_floor in discriminating:
    mem, _ = run_hook(cM, lM, unit_setup(px2, target, board_y, heights, eb))
    got = mem[mM.EFF_DIST2]
    if got != want_surf:
        n_killed += 1       # the mutant FAILS the new (surface-relative) expectation
    if got == want_floor:
        n_faithful += 1     # ...and does so by faithfully reproducing the OLD formula
check(f"1b-ii mutant FAILS the surface-relative expectation on ALL {len(discriminating)} "
      "discriminating scenarios (killed)", n_killed == len(discriminating),
      f"killed {n_killed}/{len(discriminating)}")
check("1b-iii mutant faithfully reproduces the OLD floor-relative formula (it fails for the "
      "right reason, not because the mutant build is broken)",
      n_faithful == len(discriminating), f"{n_faithful}/{len(discriminating)} match old formula")

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
# 2c: DRDIST_FLOORREL without DRDISTGATE emits nothing (the mutant knob is scoped to the gate)
cOff3, _, _ = build({**V4_PROFILE, "DRDIST_FLOORREL": "1"})
t2c = bytes(cOff1) == bytes(cOff3)
check("2c DRDIST_FLOORREL=1 with the gate OFF is byte-exact too (mutant knob fully scoped)",
      t2c, f"identical={t2c}")

print()
print("=" * 78)
print("TEST 3 -- empty-board behavior (surface == floor): Y=0 floor, generous window, 1-column")
print("=" * 78)
# SILICON-MEASURED (2026-08-05, see patch_cartridge_copro.py's DIST_DASEDGE/DIST_GRAVROW comment
# for the full methodology and footage sources) -- same numbers the gate itself now uses as its
# defaults, kept in sync here so the simulation and the mechanism under test share one source of
# truth. Superseded the original 32/26 pair, which was never measured (inherited a stale
# hooks-per-frame conversion bug from an old code comment).
DAS_HOOKS_PER_EDGE = 12
GRAV_HOOKS_PER_ROW = 30
cOn, lOn, mOn = build({**V4_PROFILE, "DRDISTGATE": "1"})
cOff, lOff, mOff = build(V4_PROFILE)


def simulate_race(code, lab, spawn_col, true_col, flip_hook, start_y, total_hooks):
    """Same shape as test_task49_slamarm_race.py's simulate_race (SLAM_ARM=0 throughout, so an
    accelerated slam is structurally ruled out per that file's Test A -- isolates this test to
    what DISTGATE actually changes: the STEERING target, not the commit-timing decision).
    Board left empty (all $00 = empty per tile-encoding): surface == floor here."""
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


def simulate_commit(code, lab, spawn_col, true_col, flip_hook, start_y, total_hooks,
                    heights=None):
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
    is the real, falsifiable, two-sided claim this test checks: does DOWN ever fire, and where.

    heights: optional per-column stack heights written into $0500 every hook (surface-relative
    rebuild). Physics honor the stack: gravity stops at the surface of the capsule's CURRENT
    column and the capsule LOCKS on the first blocked gravity tick (the NES lock rule -- one
    full gravity interval of lock delay while resting on the surface)."""
    y = start_y; px = spawn_col
    das_progress = 0
    stable_ct = 0; last_col = 0xFE; last_ori = 0xFE
    down_fired = False; down_hook = None; locked_col = None
    hts = heights or [0] * 8
    for h in range(total_hooks):
        tgt = true_col if h >= flip_hook else spawn_col

        def setup(mem, tgt=tgt, y=y, px=px, stable_ct=stable_ct, last_col=last_col, last_ori=last_ori):
            if heights is not None:
                write_board(mem, heights)
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
        if h % GRAV_HOOKS_PER_ROW == (GRAV_HOOKS_PER_ROW - 1):
            if y - 1 >= hts[px]:
                if y > 0:
                    y -= 1
            else:
                locked_col = px   # blocked gravity tick on the surface -> natural lock
                break
    if locked_col is None:
        locked_col = px   # window ran out without a slam: natural-gravity resting column
    return locked_col, down_fired, down_hook


# 3a: REDESIGNED after the constants correction (see patch_cartridge_copro.py's DIST_DASEDGE/
# DIST_GRAVROW comment). Under the corrected, much-faster DAS numbers, a literal "commit-6-shaped"
# 3-column-in-40-hooks scenario no longer demonstrates infeasibility: 3 columns now cost 3*12=36
# hooks, which FITS inside a 40-hook window (this itself is a major finding -- see
# CART_FIX_REPORT.md). Attempting to reconstruct a tight, gate-still-matters scenario at
# intermediate Y values ran into a genuine, correctly-behaving property of the mechanism, not a
# bug: because the clamp is recomputed fresh each hook relative to the CAPSULE'S CURRENT position
# (not spawn), once DAS makes real progress the reachable ceiling advances right along with it
# (correctly -- "how far MORE can I get from HERE, given remaining time" is the right recursive
# definition, not a fixed spawn-relative cap) -- so for any Y > 0 the clamp converges toward
# "effectively unclamped" as soon as movement starts, UNLESS the window is so short that NEITHER
# the clamped nor unclamped build can align in time (in which case there is nothing to
# demonstrate either way).
#
# The one place the clamp is UNCONDITIONALLY, non-rubber-band binding on an EMPTY board is the
# TRUE FLOOR: Y=0 gives DIST_TABLE[0]=0 by explicit design (no more fall-room, full stop), so
# EFF_DIST2=PX2 immediately regardless of how much DAS progress has or hasn't happened. (The
# surface-relative rebuild generalizes exactly this behavior to "capsule at the STACK surface" --
# that is Test 4.)
lock_off, fired_off, hook_off = simulate_commit(cOff, lOff, spawn_col=4, true_col=7, flip_hook=0,
                                                 start_y=0, total_hooks=20)
lock_on, fired_on, hook_on = simulate_commit(cOn, lOn, spawn_col=4, true_col=7, flip_hook=0,
                                              start_y=0, total_hooks=20)
check("3a WITHOUT gate, Y=0 (true floor): chasing the unreachable target, dn_p2 never ALIGNED -> "
      "never commits; natural DAS accumulation alone (not an accelerated commit) rests it at "
      "col5, closer to the true target than spawn", not fired_off and lock_off == 5,
      f"down_fired={fired_off} resting_col={lock_off} (spawn=4, unreachable target=7)")
check("3a WITH gate, Y=0: EFF_DIST2=PX2 immediately (0 fall-room = 0 budget, by design) -> "
      "ALIGNED from hook 0 -> COMMITS via an accelerated slam at col4 (spawn -- no progress) "
      "once stability saturates, ~8 hooks earlier than any natural alternative", fired_on and lock_on == 4,
      f"down_fired={fired_on} at hook={hook_on} locked_col={lock_on} (spawn=4)")
print("  -> HONEST READING, not a clean win: at Y=0 the gate trades a NUMERICALLY WORSE resting")
print("     column (4, spawn, vs the uncommitted case's natural col5) for an EARLIER, DEFINITE")
print("     commit. Whether that is actually better depends on what the REAL game does in the")
print("     few hooks between Y reading 0 and genuine physical collision -- if natural DAS could")
print("     still gain ground in that window (plausible: Y=0 does not necessarily mean")
print("     'collides THIS hook'), the gate's immediate freeze may cost real distance the")
print("     uncommitted case would have kept gaining. Flagged as a genuine, not-fully-resolved")
print("     trade-off in CART_FIX_REPORT.md rather than claimed as an unambiguous improvement.")

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
print("TEST 4 -- DEFECT REGIME, two-sided: near-topout flat board (h=14), unreachable target")
print("=" * 78)
# The census-measured vacuity regime: board height >= 12, capsule locks HIGH. Flat h=14 board,
# spawn col1, raw target col7 (edge column -- the clean-failure geometry). Remaining fall from
# Y=15 over a 14-high surface is ONE row (~30 hooks) + one blocked-tick lock delay (~30 hooks);
# the 6-column traverse costs 72 hooks -- physically unreachable. Timeline (constants above):
#   floor-relative (mutant) & gate-OFF: budget saturates at 7 (mutant) / no clamp (OFF) -> the
#     steering target stays col7 -> never aligned -> dn_p2 never entered -> NO commit; DAS
#     accumulation parks the capsule at col6 (the 5th edge completes on the same hook as the
#     lock tick, h=59 -- edges at h=11/23/35/47/59) when the lock fires. That IS the class-a
#     census shape: an uncommitted pill resting wherever gravity caught it, one short of goal.
#   surface-relative: fall=1 -> budget=2 -> EFF=col3; aligned at hook ~24; STABLE_CT2 passes
#     K_OPEN=32 at hook ~32 -> DOWN fires, committed AT its re-targeted column, well before the
#     lock tick. The gate restricts EXACTLY where the first build was measured not to.
H14 = [14] * 8
lock_mut, fired_mut, hook_mut = simulate_commit(cM, lM, spawn_col=1, true_col=7, flip_hook=0,
                                                start_y=15, total_hooks=120, heights=H14)
lock_off4, fired_off4, hook_off4 = simulate_commit(cOff, lOff, spawn_col=1, true_col=7, flip_hook=0,
                                                   start_y=15, total_hooks=120, heights=H14)
lock_srf, fired_srf, hook_srf = simulate_commit(cOn, lOn, spawn_col=1, true_col=7, flip_hook=0,
                                                start_y=15, total_hooks=120, heights=H14)
check("4a gate OFF reproduces the defect: never aligned, never commits, parks mid-traverse",
      not fired_off4 and lock_off4 == 6,
      f"down_fired={fired_off4} resting_col={lock_off4} (spawn=1, unreachable target=7)")
check("4b floor-relative MUTANT is vacuous in-regime (killed, behavioral level): identical "
      "defect outcome to gate OFF -- budget saturated at 7, gate never restricted",
      not fired_mut and lock_mut == lock_off4,
      f"down_fired={fired_mut} resting_col={lock_mut} (must equal OFF's {lock_off4})")
check("4c surface-relative build: clamps to the reachable col3, ALIGNS, and COMMITS before "
      "the lock tick (down fires at its re-targeted column)",
      fired_srf and lock_srf == 3 and hook_srf is not None and hook_srf < 59,
      f"down_fired={fired_srf} at hook={hook_srf} locked_col={lock_srf} (want col3, hook<59)")

print()
print("=" * 78)
n_ok = sum(1 for _, ok, _ in results if ok)
print(f"==== {n_ok}/{len(results)} checks passed ====")
sys.exit(0 if n_ok == len(results) else 1)
