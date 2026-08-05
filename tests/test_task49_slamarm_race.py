#!/usr/bin/env python3
"""Task #49 follow-on: does the pair-latch fix, AS ACTUALLY SHIPPED to the human's Pocket
(v4 fast+coldinit, md5 24dcd9dca5db8b7a21c93b2bb30f124b, roms/manifests/pocket-human-v4-coldinit.json),
survive the REVIEW's SLAM_ARM pre-gate hole (PAIR_LATCH_AUDIT.md #6.1) and the m3 topout signature
(film_review_20260804/recon/VERDICT.md)?

House rule: simulate the DEFECT, assert the OUTCOME (not "a flag is set").

FINGERPRINT CONTEXT (see driver-nav/CART_FIX_REPORT.md):
  The shipping v4-coldinit cart reproduces byte-exact from HEAD via `tools/romgen.py rebuild`
  using its recorded manifest flags. Those flags do NOT override DRROTFIX/DRCOLGATE/DRRECOMMIT/
  DRSLAM -- all sit at their code defaults (all ON) -- and explicitly add DRRECOMMIT_NOFREEZE=1
  BECAUSE this profile also sets DRNOFREEZE=1.

  That DRNOFREEZE=1 turns out to matter a lot for what "the fix" even means on THIS cart:
  dn_p2's confidence gate is guarded by `if NO_FREEZE or COLGATE:` (patch_cartridge_copro.py:1621).
  Every Pocket-tagged manifest on driver-nav (classictempo, latchfix, studycounts, v4-coldinit)
  sets DRNOFREEZE=1, which satisfies that OR unconditionally -- so DRCOLGATE is a NO-OP on every
  Pocket cart driver-nav has ever built; the column confidence gate has ALWAYS been active for
  Pocket via the NO_FREEZE branch, not because of COLGATE. The fix that actually mattered for
  Pocket is RECOMMIT (the orient re-latch), extended onto NO_FREEZE=1 carts via
  DRRECOMMIT_NOFREEZE=1 -- first shipped in commit 9e47618 "manifest for the cart now ON THE
  POCKET (pocket-human-latchfix)".

WHAT THIS FILE TESTS:
  A. SLAM_ARM branch, on the REAL shipping V4_PROFILE (not a hypothetical build): does
     SLAM_ARM==0 really skip the K_CROSS feasibility-crossover branch, as REVIEW #6.1 claims?
  B. RECOMMIT two-sided, on the REAL shipping V4_PROFILE: is the Pocket-relevant fix (not
     COLGATE, which is moot here) actually doing something on THIS exact flag set?
  D. COLGATE two-sided, on the freeze-class (DRNOFREEZE=0) cart family it was actually written
     for -- extending the existing test_pocket_placement.py scenario 1 with the SLAM_ARM=0 axis
     REVIEW #6.1 says it's missing. This is NOT the shipping Pocket cart (see A/B) but it is the
     class of cart where DRCOLGATE has a real effect, so it's the right place to two-sided-test it.
  E. Multi-hook lateral-DAS-vs-gravity race (REVIEW #6.2), on the REAL shipping V4_PROFILE, under
     SLAM_ARM=0 (the state Test A proves makes an early forced slam IMPOSSIBLE): characterizes
     whether WEAVE steering (mv_p2, active on every build regardless of DRCOLGATE/DRRECOMMIT) can
     out-run natural gravity to the search's converged column, for a 1-column (feasible) and a
     3-column (commit-6-shaped) lateral distance. This is NOT a DRCOLGATE/DRRECOMMIT-gated
     mechanism at all, which is itself the finding: no flag in this fix family touches it.

Conclusion this file is building evidence for (stated up front, verified below): under SLAM_ARM==0
(REVIEW's flagged pessimal case, expected near a topout), a premature ACCELERATED slam at a stale
column is structurally IMPOSSIBLE on the shipping cart (dn_hold is the only reachable branch before
DONE) -- so REVIEW #6.1's code-path finding is correct, but its consequence is milder than "the
defect still reproduces": SLAM_ARM==0 does not re-open the ORIGINAL premature-slam failure mode.
The residual risk in that regime is REVIEW #6.2's lateral-distance/fall-time race, which no
DRCOLGATE/DRRECOMMIT/DRSLAM flag combination changes -- Test E shows the fix is inert there, not
that the fix fails there.
"""
import os, sys, importlib.util, hashlib
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
W_DONE, W_COL, W_OR = 0x5084, 0x5085, 0x5086       # DRPOCKET single window at $5000
_rom = open(os.path.join(REPO, "drmario_v28cs.nes"), "rb").read(); _prg = _rom[4] * 16384
TOG = _rom[16 + (_prg - 0x4000) + (0xFF30 - 0xC000):][:28]
GAMEMAP = {0: 3, 1: 1, 2: 0, 3: 2}

# the ACTUAL shipping flag profile, from roms/manifests/pocket-human-v4-coldinit.json
V4_PROFILE = dict(DRBUSYESC="1", DRCOLDINIT="1", DRHUMAN="1", DRMINTHINK="12", DRNAVDWELL="0",
                   DRNOFREEZE="1", DRPENDBOUND="1", DRPOCKET="1", DRRECOMMIT_NOFREEZE="1",
                   DRSLAM_KOPEN="32", DRSTALLWD="1", DRSTUDYCOUNTS="1", DRWRETRY="1")

_ALL_DR_KEYS = ("DRNOFREEZE", "DRROTFIX", "DRHUMAN", "DRPOCKET", "DRSLAM", "DRNAVFIX", "DRTRACE",
                "DRPROBE", "DRNAV_V4", "DRNAV_HOLD", "DRCOLGATE", "DRRECOMMIT", "DRBUSYESC",
                "DRCOLDINIT", "DRMINTHINK", "DRNAVDWELL", "DRPENDBOUND", "DRRECOMMIT_NOFREEZE",
                "DRSLAM_KOPEN", "DRSTALLWD", "DRSTUDYCOUNTS", "DRWRETRY", "DRSLAM_KCROSS",
                "DRSLAM_KEND", "DRSLAM_VCEND", "DRSLAM_LOWY", "DRSLAM_MATURE", "DRTUCK")


def build(env):
    for k in _ALL_DR_KEYS:
        os.environ.pop(k, None)
    os.environ.update(env)
    if REPO not in sys.path: sys.path.insert(0, REPO)
    sys.modules.pop("pp_fs49", None)
    spec = importlib.util.spec_from_file_location("pp_fs49", os.path.join(REPO, "patch_cartridge_copro.py"))
    mod = importlib.util.module_from_spec(spec); sys.modules["pp_fs49"] = mod; spec.loader.exec_module(mod)
    code, lab = mod.build_main(11, 1)
    return code, lab, mod


def run_hook(code, lab, setup):
    """Run ONE driver hook over a mock state; return (mem, F6-button)."""
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


results = []  # (name, ok, detail)


def check(name, ok, detail):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")


print("=" * 78)
print("TEST A -- SLAM_ARM branch, on the REAL shipping V4_PROFILE (REVIEW #6.1)")
print("=" * 78)
cA, lA, mA = build(V4_PROFILE)
LOWY = mA.CROSS_LOWY
K_CROSS = mA.K_CROSS


def slamarm_setup(slam_arm_val):
    def s(mem):
        col = 5
        mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_COL] = col; mem[W_OR] = 2   # still searching
        mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]; mem[TGT_O2] = GAMEMAP[2]
        mem[PX2] = col; mem[TGT_C2] = col; mem[STKX2] = col
        mem[STKY2] = LOWY - 2; mem[PY2] = LOWY - 2; mem[LASTY2] = LOWY - 2   # PAST crossover (physically low)
        mem[STABLE_CT2] = K_CROSS   # argmax has been stable long enough to satisfy K_CROSS
        mem[LAST_COL2] = col; mem[LAST_ORI2] = GAMEMAP[2]
        mem[STK2] = 0; mem[VCOUNT_P2] = 48
        mem[SLAM_ARM] = slam_arm_val
    return s


_, f6_armed1 = run_hook(cA, lA, slamarm_setup(1))
_, f6_armed0 = run_hook(cA, lA, slamarm_setup(0))
a1 = bool(f6_armed1 & DOWN)   # SLAM_ARM=1 past crossover + stable -> the K_CROSS branch should fire
a2 = not bool(f6_armed0 & DOWN)  # SLAM_ARM=0 -> REVIEW claims K_CROSS is skipped -> no DOWN, ever
check("A1 SLAM_ARM=1 reaches K_CROSS and slams", a1,
      f"Y={LOWY-2} (<{LOWY}=CROSS_LOWY), STABLE_CT2={K_CROSS}(>=K_CROSS) -> DOWN pressed={bool(f6_armed1 & DOWN)}")
check("A2 SLAM_ARM=0 skips K_CROSS -> dn_hold (REVIEW #6.1 confirmed)", a2,
      f"identical Y/stability, only SLAM_ARM differs -> DOWN pressed={bool(f6_armed0 & DOWN)} (want False)")
print(f"  MIN_THINK={mA.MIN_THINK} CROSS_LOWY={LOWY} K_CROSS={K_CROSS} K_OPEN={mA.K_OPEN}")
print("  -> REVIEW #6.1's code-path claim VERIFIED on the actual shipping build: SLAM_ARM=0 makes")
print("     a forced/accelerated slam at ANY Y structurally unreachable pre-DONE. This means the")
print("     ORIGINAL 'premature slam at a stale column' failure mode CANNOT occur when SLAM_ARM=0")
print("     -- REVIEW #6.1 is right about the branch, but SLAM_ARM=0 is safer than 'same defect',")
print("     not worse: dn_hold never presses DOWN, so gravity alone decides the lock, never an")
print("     accelerated commit to a shallow argmax. See Test E for what dn_hold DOES leave exposed.")

print()
print("=" * 78)
print("TEST B -- RECOMMIT two-sided, on the REAL shipping V4_PROFILE (Pocket's actual fix)")
print("=" * 78)
cB_on, lB_on, mB_on = build(V4_PROFILE)
cB_off, lB_off, mB_off = build({**V4_PROFILE, "DRRECOMMIT": "0"})
assert mB_on.RECOMMIT and not mB_off.RECOMMIT, "harness bug: RECOMMIT toggle didn't take"


def recommit_setup(y):
    def s(mem):
        mem[ARMED2] = 1; mem[W_DONE] = 1; mem[W_COL] = 6; mem[W_OR] = 2   # DONE; converged orient 2->game 0
        mem[ROT_DONE2] = 1
        mem[ORI2] = GAMEMAP[1]        # capsule physically SHALLOW (game 1) != converged (game 0)
        mem[TGT_O2] = GAMEMAP[1]; mem[TGT_C2] = 6
        mem[PX2] = 6; mem[STKX2] = 6; mem[STKY2] = y; mem[PY2] = y; mem[LASTY2] = y
    return s


mem_hi_on, _ = run_hook(cB_on, lB_on, recommit_setup(LOWY + 4))
mem_hi_off, _ = run_hook(cB_off, lB_off, recommit_setup(LOWY + 4))
b1 = mem_hi_on[ROT_DONE2] == 0
b2 = mem_hi_off[ROT_DONE2] == 1
check("B1 RECOMMIT(on V4_PROFILE) re-opens latch, capsule HIGH", b1,
      f"ROT_DONE2 after DONE = {mem_hi_on[ROT_DONE2]} (want 0 = re-opened)")
check("B2 pre-fix (DRRECOMMIT=0 on same V4_PROFILE) never re-opens", b2,
      f"ROT_DONE2 after DONE = {mem_hi_off[ROT_DONE2]} (want 1 = stuck shallow)")

print()
print("=" * 78)
print("TEST D -- COLGATE two-sided, freeze-class family (where DRCOLGATE has a real effect),")
print("          extended with the SLAM_ARM=0 axis REVIEW #6.1 says test_pocket_placement.py lacks")
print("=" * 78)
FREEZE_BASE = dict(DRHUMAN="1", DRPOCKET="1", DRSLAM="1")   # NOT DRNOFREEZE -- ROTFIX-only class.
# DRPOCKET is kept (matches test_pocket_placement.py's own build() baseline, and this harness's
# mailbox addresses -- W_DONE/W_COL/W_OR at $5084-$5086 -- are DRPOCKET's single-window layout);
# only DRNOFREEZE is left at its "0" default, which is what actually selects the freeze-class path.
cD_on, lD_on, mD_on = build(FREEZE_BASE)
cD_off, lD_off, mD_off = build({**FREEZE_BASE, "DRCOLGATE": "0"})
LOWY_D = mD_on.CROSS_LOWY


def colgate_setup(slam_arm_val):
    def s(mem):
        mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_OR] = 2; mem[W_COL] = 5    # searching, running argmax col5
        mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]; mem[TGT_O2] = GAMEMAP[2]
        mem[PX2] = 5; mem[TGT_C2] = 5; mem[STKX2] = 5; mem[STKY2] = LOWY_D + 4; mem[PY2] = LOWY_D + 4
        mem[LASTY2] = LOWY_D + 4
        mem[STABLE_CT2] = 0; mem[LAST_COL2] = 0xFE; mem[LAST_ORI2] = 0xFE  # argmax JUST changed -> unstable
        mem[SLAM_ARM] = slam_arm_val
    return s


_, d_on_armed1 = run_hook(cD_on, lD_on, colgate_setup(1))
_, d_off_armed1 = run_hook(cD_off, lD_off, colgate_setup(1))
_, d_on_armed0 = run_hook(cD_on, lD_on, colgate_setup(0))
_, d_off_armed0 = run_hook(cD_off, lD_off, colgate_setup(0))
d1 = (not bool(d_on_armed1 & DOWN)) and bool(d_off_armed1 & DOWN)
d2 = (not bool(d_on_armed0 & DOWN)) and bool(d_off_armed0 & DOWN)
check("D1 SLAM_ARM=1: COLGATE holds unstable argmax, pre-fix soft-drops it (original defect, two-sided)",
      d1, f"fixed DOWN={bool(d_on_armed1 & DOWN)} pre-fix DOWN={bool(d_off_armed1 & DOWN)}")
check("D2 SLAM_ARM=0: COLGATE STILL holds; pre-fix STILL slams (protection is SLAM_ARM-independent)",
      d2, f"fixed DOWN={bool(d_on_armed0 & DOWN)} pre-fix DOWN={bool(d_off_armed0 & DOWN)}")
print("  -> D2 corrects an assumption made while designing this test: pre-fix (DRCOLGATE=0, non-")
print("     NO_FREEZE) doesn't degrade to a SLAM_ARM-gated wait at all -- with the whole")
print("     `if NO_FREEZE or COLGATE:` block false, it never evaluates SLAM_ARM in the first place")
print("     and falls straight to the unconditional `LDY #4` (the canonical 'drop()' in the")
print("     mechanism sketch). So COLGATE's protection is SLAM_ARM-independent on the class of cart")
print("     it actually gates: it holds an unstable argmax whether the previous search was fast or")
print("     slow. REVIEW #6.1's gap is real (Test A), but it lives ENTIRELY inside the")
print("     already-gated region (K_CROSS vs dn_hold) -- it is not a case where COLGATE regresses")
print("     toward pre-fix behavior.")

print()
print("=" * 78)
print("TEST E -- lateral DAS-vs-gravity race under SLAM_ARM=0, REAL shipping V4_PROFILE")
print("          (REVIEW #6.2; characterization, not a flag-gated pass/fail -- DRCOLGATE/DRRECOMMIT")
print("           do not touch this path at all, which is itself the finding)")
print("=" * 78)
# Grounded constants (NOT invented): DAS ~= 32 hook-cycles/column-edge (patch_cartridge_copro.py
# comment at mv_p2, lines ~1554-1556: "32-hook cycles = 6.4 frames per edge"); gravity ~= 26
# hook-cycles/row (L11 fall 13f/row x 2 hooks/frame, per project memory dr-mario-tempo-chew /
# the AUDITED 2026-08-01 hook-rate note in this same file).
DAS_HOOKS_PER_EDGE = 32
GRAV_HOOKS_PER_ROW = 26
cE, lE, mE = build(V4_PROFILE)


def simulate_race(spawn_col, true_col, flip_hook, start_y, total_hooks):
    """Step the driver hook-by-hook for EXACTLY total_hooks (= 2 * the tape's observed
    spawn_to_lock_frames -- the piece locks when the critically-stacked board's own geometry
    stops it, not when some modeled 'floor' is reached, so we don't try to model the floor: we
    report wherever PX2 is when the observed hook budget runs out, matching the tape's ground
    truth methodology). Mailbox column = spawn_col until flip_hook, then true_col (a
    late-converging search, matching VERDICT.md's commit 6 shape). `y` is $0386-space (a ROW
    index, counts UP from the floor, project convention) and decreases toward CROSS_LOWY as
    natural gravity falls one row every GRAV_HOOKS_PER_ROW hooks (SLAM_ARM=0, so this is the
    ONLY thing moving Y -- Test A proved dn_p2 cannot accelerate it). PX2 moves 1 column per
    DAS_HOOKS_PER_EDGE hooks of a held LEFT/RIGHT, mirroring the driver's own comment."""
    y = start_y; px = spawn_col; tgt = spawn_col
    das_progress = 0; forced_down_before_convergence = False
    for h in range(total_hooks):
        tgt = true_col if h >= flip_hook else spawn_col

        def setup(mem, tgt=tgt, y=y, px=px):
            mem[ARMED2] = 1; mem[W_DONE] = 0; mem[W_COL] = tgt; mem[W_OR] = 2
            mem[ROT_DONE2] = 1; mem[ORI2] = GAMEMAP[2]
            mem[PX2] = px; mem[STKX2] = px
            mem[STKY2] = y; mem[PY2] = y; mem[LASTY2] = y
            mem[SLAM_ARM] = 0; mem[STK2] = 0; mem[VCOUNT_P2] = 48
            # TGT_C2/TGT_O2/STABLE_CT2/LAST_COL2/LAST_ORI2 are refreshed by nf2 every hook from
            # the mailbox in the real driver; this harness runs act_p2 directly (post-nf2) so
            # seed them consistently with "the mailbox was just read this hook":
            mem[TGT_C2] = tgt; mem[TGT_O2] = GAMEMAP[2]

        mem, f6 = run_hook(cE, lE, setup)
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
            y -= 1   # one row of natural fall completes every GRAV_HOOKS_PER_ROW-th hook
    return px, forced_down_before_convergence, total_hooks


# start_y: a critically-stacked board leaves only a few rows of clearance above the stack, so Y
# starts just above CROSS_LOWY (still "searching, not yet at the crossover") rather than at the
# spawn-row max -- matching VERDICT.md's board-state cross-check (row 0 already locked at commit
# 1 onward). LOWY+2 gives 2 rows of natural fall (~2*26=52 hooks worth) before crossover, then the
# capsule is in dn_hold's floor-approach regime for the remainder of the window.
START_Y = LOWY + 2

# E1: 1-column distance (feasible per REVIEW #6.2's own arithmetic), short window like commit 6
# (~20 frames = ~40 hooks), flip at hook 8 (search converges early-ish within the window).
lock1, forced1, hooks1 = simulate_race(spawn_col=4, true_col=5, flip_hook=8,
                                        start_y=START_Y, total_hooks=40)
e1 = (lock1 == 5) and not forced1
check("E1 1-column distance, 40-hook window -> WEAVE reaches the converged column, no forced slam",
      e1, f"locked_col={lock1} (want 5) forced_down={forced1} hooks_used={hooks1}")

# E2: commit-6-shaped -- 3-column distance, 40-hook (~20f) window, late flip (hook 20, matching
# the observed non-monotonic timing where the shortest window was worst). REVIEW #6.2's own
# arithmetic: 3 edges * 32 hooks = 96 hooks needed, ~2.4x the available window.
lock2, forced2, hooks2 = simulate_race(spawn_col=4, true_col=7, flip_hook=20,
                                        start_y=START_Y, total_hooks=40)
e2_reaches_target = (lock2 == 7)
check("E2 3-column distance (commit-6-shaped), 40-hook window -> reaches col7?", e2_reaches_target,
      f"locked_col={lock2} (col7=target, col4=spawn) forced_down={forced2} hooks_used={hooks2} "
      f"-- {'REACHED' if e2_reaches_target else 'DID NOT REACH'} target; needed ~"
      f"{3*DAS_HOOKS_PER_EDGE} hooks of DAS travel in a {hooks2}-hook window")
print("  -> E2 is reported, not asserted as a required PASS: REVIEW #6.2 already showed this")
print("     distance/window combination is infeasible for ANY commit-timing policy (DAS alone")
print("     costs ~96 hooks against a ~40-hook budget). The finding is that E2 landing short of")
print("     col7 is a PHYSICAL constraint, not a bug in COLGATE/RECOMMIT/SLAM -- and critically,")
print(f"     forced_down_before_convergence={forced2} confirms it does NOT fail via an accelerated")
print("     wrong-column slam either (SLAM_ARM=0 rules that out per Test A) -- whatever column it")
print("     ends up in is entirely a WEAVE/DAS-speed outcome, never an accelerated commit.")

# E3: commit-3-shaped counter-case (REVIEW #6.3) -- no column change at all, short window, the
# tape and eval already agree. Assert this is NOT made worse: capsule reaches/holds the (single,
# unchanging) target with no spurious forced drop before natural lock.
lock3, forced3, hooks3 = simulate_race(spawn_col=3, true_col=3, flip_hook=0,
                                        start_y=START_Y, total_hooks=33)
e3 = (lock3 == 3) and not forced3
check("E3 commit-3 counter-case (no column change, 33-hook window) -> no regression",
      e3, f"locked_col={lock3} (want 3) forced_down={forced3} hooks_used={hooks3}")

print()
print("=" * 78)
n_ok = sum(1 for _, ok, _ in results if ok)
print(f"==== {n_ok}/{len(results)} checks passed (E2 is informational; see script output above) ====")
# E2 is intentionally excluded from the pass/fail gate -- it documents a known, physically-bounded
# residual (REVIEW #6.2), not a regression this change is responsible for fixing.
gate = [ok for name, ok, _ in results if not name.startswith("E2")]
sys.exit(0 if all(gate) else 1)
