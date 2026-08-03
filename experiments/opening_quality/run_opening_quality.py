#!/usr/bin/env python3
"""Task #43 instrument: does the Pocket cart's DRIVER (real 6502 assembly, executed
instruction-by-instruction via py65) place the opening 8 P2 pills sanely, and which
mechanism explains "nonsensical vertical drops" -- tempo miscalibration (A), stale
driver state across a rematch (B), or a slam that fires mid-lateral-transit (A')?

INSTRUMENT NOTE (see message to team-lead, 2026-08-02): the Verilator "co-sim"
(fpga/copro/sim_mister.cpp) is copro-RTL-only -- no NES CPU, no driver code, cannot
answer this question at all. This harness instead drives the REAL assembled driver
bytes (patch_cartridge_copro.py's build_main output) through py65, continuously
across 8 simulated pill-locks per game, with a mocked copro mailbox (search latency
+ published column/orient are scripted per scenario, deterministic per seed). This
is decision-accurate for the driver's OWN state machine (the thing in question --
lateral movement, commit gating, slam timing, cold/warm state) but NOT a claim about
copro search QUALITY (which is out of scope here; the copro's answer is mocked).

Hook cadence: patch_cartridge_copro.py:95-112 measured (2026-08-01, static analysis
of the NMI call graph) that the driver hook runs EXACTLY 2x per frame, both inside
the NMI, and that this is baked into the getInputs/addExpansionCTRL call structure
of the BASE game ROM -- DRPOCKET does not touch it (confirmed by rider-3 static
check, message to team-lead 2026-08-02: DRPOCKET's only effect is the single-vs-dual
mailbox window). This harness uses HOOKS_PER_FRAME=2 accordingly. A prior scratch
harness (driver-nav/tmp/p0lib.py, gitignored, predates the corrected measurement)
used hooks=5/frame ("calibration prose, not measured" per the same comment) -- not
reused here for that reason.

Warm-state (P0.2/P0.3) stale signature, cited from patch_cartridge_copro.py:1008-1030
and :1060-1064 (the DRCOLDINIT block and its menu-entry gate): without DRCOLDINIT,
MATCH_ACTIVE never resets across a rematch (menus only clear it `if COLDINIT:`), so
none of PEND1/2, DELAY1/2, LASTY1/2, ARMED2, WDOG2, WDOGH2, WRETRY2 get cleared at
the start of a new match. We inject exactly that signature: MATCH_ACTIVE=1 (already
true, left alone), ARMED2=1, WDOG2/WDOGH2 mid-search values, LASTY2 stuck near the
spawn row (post-topout symptom named in the :313-318 comment), TGT_C2/TGT_O2 holding
the PREVIOUS match's final target, PEND2=1/DELAY2 mid-settle. This is the documented
P0.2/P0.3 signature, not an invented one.
"""
import os, sys, json, random, importlib.util, argparse
from pathlib import Path

DRV = "/home/struktured/projects/dr-mario-mods-wt/driver-nav"
sys.path.insert(0, DRV)
from py65.devices.mpu6502 import MPU  # noqa: E402

BASE = 0x8000
SENT = 0x4FF2
HOOKS_PER_FRAME = 2          # measured (patch_cartridge_copro.py:102), NOT the old tmp/p0lib.py "5"
GRAV_TH = 40                 # frames/row of natural gravity (mid-level pace; soft-drop overrides via $F6&4)

ARM_SPECS = {
    "v2-form": dict(DRHUMAN="1", DRNAVDWELL="0", DRNOFREEZE="1", DRPOCKET="1",
                     DRRECOMMIT_NOFREEZE="1", DRSTUDYCOUNTS="1", DRMINTHINK="12",
                     DRSLAM_KOPEN="32", DRWRETRY="1", DRPENDBOUND="1", DRSTALLWD="1",
                     DRBUSYESC="1"),
    "v3-form": dict(DRHUMAN="1", DRNAVDWELL="0", DRNOFREEZE="1", DRPOCKET="1",
                     DRRECOMMIT_NOFREEZE="1", DRSTUDYCOUNTS="1",
                     DRWRETRY="1", DRPENDBOUND="1", DRSTALLWD="1", DRBUSYESC="1"),
    "v4-form": dict(DRHUMAN="1", DRNAVDWELL="0", DRNOFREEZE="1", DRPOCKET="1",
                     DRRECOMMIT_NOFREEZE="1", DRSTUDYCOUNTS="1", DRMINTHINK="12",
                     DRSLAM_KOPEN="32", DRWRETRY="1", DRPENDBOUND="1", DRSTALLWD="1",
                     DRBUSYESC="1", DRCOLDINIT="1"),
}

# B2 (2026-08-02): the "v2/v3/v4-form" arms above are all DRHUMAN=1 (Pocket carts). fc_clear's
# START injection is compiled out entirely `if not HUMAN_P1` (patch_cartridge_copro.py:984-988)
# -- a human is expected to press their own START -- so those arms cannot exercise the
# auto-injection path the MiSTer field report is actually about. The live "Stomper" probe cart
# is a CvC duel (DRP1NATIVE=1, no DRHUMAN/DRPOCKET); flags below are copied EXACTLY from
# driver-nav/roms/manifests/latch-converged-native-probe.json (git commit ee32402e, the deployed
# build), which already carries DRCOLDINIT=1 -- matching the cart the user actually observed.
MISTER_PROBE_SPEC = dict(DRBUSYESC="1", DRCOLDINIT="1", DRMINTHINK="12", DRNAVDWELL="0",
                          DRNAVESC="1", DRNOFREEZE="1", DRP1NATIVE="1", DRPENDBOUND="1",
                          DRRECOMMIT_NOFREEZE="1", DRSLAM_KOPEN="32", DRSTALLWD="1", DRWRETRY="1")
MISTER_ARM_SPECS = {
    "mister-probe": dict(MISTER_PROBE_SPEC),
    "mister-probe-nocoldinit": {k: v for k, v in MISTER_PROBE_SPEC.items() if k != "DRCOLDINIT"},
}

ALL_FLAGS = sorted({k for spec in list(ARM_SPECS.values()) + list(MISTER_ARM_SPECS.values())
                     for k in spec} | {"DRCOLDINIT"})


def build(flags):
    for k in ALL_FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    name = "pc_oq_" + "_".join(f"{k}={v}" for k, v in sorted(flags.items()))
    for m in list(sys.modules):
        if m.startswith("patch_cartridge_copro"):
            del sys.modules[m]
    path = os.path.join(DRV, "patch_cartridge_copro.py")
    spec = importlib.util.spec_from_file_location(name, path)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


class Game:
    """Continuous multi-pill P2 driver run. Board is a placeholder (bottom-row viruses,
    no clear physics) -- opening-quality is about the DRIVER's pill-to-pill state
    machine, not clear correctness, which is out of scope here."""

    def __init__(self, P, unit1, labels, rng, grav_th=GRAV_TH, stress=False):
        self.P, self.labels, self.rng = P, labels, rng
        self.grav_th = grav_th
        self.stress = stress   # hyp A' stress mode: force far-column + rotation + late-revise plans
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        for i in range(128):
            self.m.memory[0x0500 + i] = 0xFF
        for c in (0, 2, 5, 7):
            self.m.memory[0x0500 + 15 * 8 + c] = 0xD0 | (c % 3)
        for a, v in ((0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.y, self.x, self.orient = 15, 3, 0
        self.frame = 0
        self.hook_n = 0
        self.WB = P.W2_BASE
        self.mbox_done = 0
        self.pub = (0xFF, 0xFF)
        self.search_hooks = 0
        self.armed_live = False
        self.cur_plan = None       # (latency_hooks, col, orient, revise_at, revise_col, revise_orient)
        self.spawn_hook = 0
        self.lateral_seen = False
        self.records = []          # per-pill dict, appended on lock
        self.force_stuck = False   # True during play_through_rematch's pre-menu window: the
                                    # in-flight search never DONEs, matching the documented
                                    # P2.2 "soft-relaunch mid-search" stale-ARMED2 scenario
                                    # (driver-nav/tmp/sim_p22_relaunch.py, gitignored prior art)
        self._sync_mbox()

    def _sync_mbox(self):
        self.m.memory[self.WB + 0x84] = self.mbox_done
        self.m.memory[self.WB + 0x85], self.m.memory[self.WB + 0x86] = self.pub

    def new_plan(self):
        if self.force_stuck:
            return dict(latency=10**9, col=self.rng.randint(0, 7), orient=self.rng.choice([0, 1, 2, 3]),
                        revise_at=None, revise_col=None, revise_orient=None)
        if self.stress:
            # hyp A' stress: far column (max lateral distance from spawn=3) + a rotation, and
            # ALWAYS revise late (near the search's own latency) -- the adversarial case for
            # "slam fires before steering finishes": maximum distance to cover after commit.
            latency = self.rng.choice([6, 10, 12, 16])   # deliberately near/below MIN_THINK=12 (v2/v4-form)
            col = self.rng.choice([0, 7])
            orient = self.rng.choice([1, 2, 3])
            revise_at = max(1, latency - 2)
            revise_col = 7 if col == 0 else 0             # revise flips to the OPPOSITE wall
            revise_orient = self.rng.choice([0, 1, 2, 3])
            return dict(latency=latency, col=col, orient=orient,
                        revise_at=revise_at, revise_col=revise_col, revise_orient=revise_orient)
        # scripted "copro": latency + published (col, orient), optional mid-flight revision.
        latency = self.rng.choice([6, 10, 20, 40, 80])
        col = self.rng.randint(0, 7)
        orient = self.rng.choice([0, 1, 2, 3])
        revise = self.rng.random() < 0.25
        revise_at = latency // 2 if revise else None
        revise_col = self.rng.randint(0, 7) if revise else None
        revise_orient = self.rng.choice([0, 1, 2, 3]) if revise else None
        return dict(latency=latency, col=col, orient=orient,
                    revise_at=revise_at, revise_col=revise_col, revise_orient=revise_orient)

    def hook(self, mode):
        m = self.m
        m.memory[0x0046] = mode
        m.memory[0x0385], m.memory[0x0386] = self.x, self.y
        m.memory[0x03A5] = self.orient
        m.memory[0xF6] = 0
        m.memory[0xF5] = 0    # P1 raw pad latch: no physical controller -> reads 0 unless the
                               # driver itself injects a button this hook (autonav/fc_clear START)
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        if m.memory[0xF5] != 0 and hasattr(self, "injected_starts"):
            # checked HERE, not after frame_step(): frame_step() calls hook() twice
            # (HOOKS_PER_FRAME=2) and the second hook's $F5=0 clear-at-entry would erase
            # any injection the first hook made before an external caller could observe it.
            self.injected_starts += 1
        if m.memory[self.WB + 0x84] != self.mbox_done:   # driver wrote GO (mailbox +0x84 changed)
            self.armed_live = True
            self.search_hooks = 0
            self.mbox_done = 0
            self.pub = (0xFF, 0xFF)
            self.cur_plan = self.new_plan()
        if self.armed_live and self.cur_plan is not None:
            self.search_hooks += 1
            plan = self.cur_plan
            if self.search_hooks == max(1, plan["latency"] // 3):
                self.pub = (plan["col"], plan["orient"])          # first live argmax appears
            if plan["revise_at"] and self.search_hooks == plan["revise_at"]:
                self.pub = (plan["revise_col"], plan["revise_orient"])
            if self.search_hooks >= plan["latency"]:
                col, orient = (plan["revise_col"], plan["revise_orient"]) if plan["revise_at"] else (plan["col"], plan["orient"])
                self.pub = (col, orient)
                self.mbox_done = 1
                self.armed_live = False
        self._sync_mbox()
        f6 = m.memory[0xF6]
        if f6 & 0x03:
            self.lateral_seen = True
        self.hook_n += 1
        return f6

    def frame_step(self, mode):
        press = 0
        for _ in range(HOOKS_PER_FRAME):
            press |= self.hook(mode)
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1
        if mode != 4:
            return press
        last = self.m.memory[0xF6]
        if last & 0x80:
            self.orient = (self.orient + 1) & 3
        if last & 0x01 and self.x < 7:
            self.x += 1
        if last & 0x02 and self.x > 0:
            self.x -= 1
        drop = False
        if last & 0x04:
            drop = True
        else:
            g = self.m.memory[0x0392] + 1
            self.m.memory[0x0392] = g
            if g >= self.grav_th:
                self.m.memory[0x0392] = 0
                drop = True
        if drop:
            floor = 2 if self.m.memory[0x0500 + 15 * 8 + self.x] != 0xFF else 1
            if self.y - 1 <= floor:
                self.lock()
            else:
                self.y -= 1
        return press

    def lock(self):
        m = self.m
        tgt_c = m.memory[0x6152]  # TGT_C2: published target column at the moment of lock
        spawn_x = self._spawn_x
        rec = dict(pill=len(self.records) + 1,
                   spawn_x=spawn_x, locked_x=self.x, locked_orient=self.orient,
                   tgt_c_at_lock=tgt_c,
                   think_hooks=self.hook_n - self.spawn_hook,
                   lateral_seen=self.lateral_seen,
                   zero_lateral=(self.x == spawn_x and not self.lateral_seen),
                   wrong_column=(self.x != tgt_c))
        self.records.append(rec)
        self.y, self.x, self.orient = 15, 3, 0
        self._spawn_x = 3
        self.spawn_hook = self.hook_n
        self.lateral_seen = False

    def boot_cold(self):
        self._spawn_x = 3
        for _ in range(10):
            self.frame_step(8)     # intro-ish hooks to let power-on init run

    def play_through_rematch(self, search_hooks=20, menu_hooks=20, menu_mode=2):
        """Drive the ACTUAL P0.2/P0.3 code paths (not a raw-memory injection): play mode-4
        hooks so a search goes ARMED (ARMED2=1, WDOG2/WDOGH2/LASTY2 accrue real driver state
        from a genuinely in-flight search near the spawn row -- the topout symptom named in
        patch_cartridge_copro.py:313-318), then cut to a non-4/non-8 mode (any value reaches
        the "menus" label at :1060, which is the ONLY place that clears MATCH_ACTIVE
        `if COLDINIT:` -- :1061-1064), then resume play mode. For non-COLDINIT arms
        MATCH_ACTIVE survives the menu untouched -> the go_ai per-match reset block at
        :1008-1030 (gated on MATCH_ACTIVE==0) never fires for the "rematch" -> ARMED2/WDOG2/
        LASTY2/PEND2/DELAY2 all carry the stale prior-search values into pill 1 of the new
        match. For COLDINIT arms the menu step zeros MATCH_ACTIVE -> the reset block fires on
        the first rematch play-hook -> clean state. This reproduces the mechanism through the
        REAL code, not an assumed address list. The pre-menu search is forced never-DONE
        (force_stuck) so it is genuinely in-flight -- not coincidentally resolved -- when the
        match ends, matching the P2.2 soft-relaunch mechanism (stale ARMED2 from an abandoned
        search) rather than relying on timing luck."""
        self.force_stuck = True
        for _ in range(search_hooks):
            self.frame_step(4)
        self.force_stuck = False
        for _ in range(menu_hooks):
            self.frame_step(menu_mode)
        # observation window starts fresh at the rematch's pill 1 -- discard any pre-transition
        # lock record and reset the per-pill trackers so recorded pills are strictly post-rematch.
        self.records = []
        self.y, self.x, self.orient = 15, 3, 0
        self._spawn_x = 3
        self.spawn_hook = self.hook_n
        self.lateral_seen = False

    def play_through_autorematch(self, search_hooks=20, transit_hooks=20, transit_modes=(7, 3, 8)):
        """B2 (team-lead sub-hypothesis, 2026-08-02): does an auto-rematch (no human hand on a
        menu) ever reach the "menus"/mode-8 MATCH_ACTIVE clear at all? The MiSTer CvC probe ring
        showed the real transition is modes 7->3->8->4, never touching 0/1 (a human-driven
        menu). This drives the REAL compiled fc_clear ("full-clear auto-advance",
        patch_cartridge_copro.py:963-989) through that exact scenario rather than asserting
        what it does: set VCOUNT_P2 nonzero for a few real play hooks so the driver's own code
        naturally latches VSEEN2=1 (:1039), then zero VCOUNT_P2 (a player "cleared their
        board" -- the STAGE CLEAR trigger, :977-981) while MATCH_ACTIVE stays 1, then drive
        hooks through transit_modes in order with VCOUNT_P2 still 0 throughout (matching the
        realistic case where the base game does not repopulate viruses until the new match's
        play-mode actually begins) before restoring VCOUNT_P2 and resuming mode 4. fc_clear's
        gate (:976, MATCH_ACTIVE!=0) never reads $0046, so if it keeps firing across every
        transit mode, the driver never reaches EITHER the "menus" COLDINIT clear or the mode-8
        unconditional clear, regardless of the DRCOLDINIT flag -- this method measures whether
        that is what actually happens, not just what a static trace implies.

        transit_modes default (7,3,8) matches the measured MiSTer CvC probe-ring sequence, where
        mode 3 (<4) is structurally exempt from fc_clear via the NAV_V4 floor at :975 (default
        ON) and lets DRCOLDINIT's fix through. Pass transit_modes=(7,) to test the team-lead's
        2026-08-02 scope-check hypothesis instead: a HUMAN cart's real rematch flow may go
        straight from the results screen (mode 7, presumed) to play (mode 4) via the player's
        own physical START press, with NO intervening mode<4 menu screen -- in which case the
        NAV_V4 escape this write-up found for the CvC case never applies, and DRCOLDINIT alone
        would NOT be enough even though fc_clear's own injection is compiled out for DRHUMAN
        (:984-988) and so isn't what's making the human's real button work in the first place
        (that flows through the base game's own controller read, independent of this driver
        hook's dispatch decisions -- fc_clear's early-RTS only gates the DRIVER's OWN downstream
        state-reset code, not the human's ability to press START).

        force_stuck matches play_through_rematch: an abandoned in-flight search, not a
        coincidentally-resolved one."""
        VCOUNT_P2 = 0x03A4
        self.force_stuck = True
        self.m.memory[VCOUNT_P2] = 40           # let the driver's own code see a live count
        for _ in range(search_hooks):
            self.frame_step(4)                   # real play hooks -> VSEEN2 latches (:1037-1040)
        self.force_stuck = False
        self.injected_starts = 0                 # diagnostic: did fc_clear actually fire?
        armed_before = self.m.memory[0x6161]     # ARMED2, for the "did dispatch ever resume" check
        self.m.memory[VCOUNT_P2] = 0             # "P2 cleared the board" -> STAGE CLEAR trigger
        for mode in transit_modes:
            for _ in range(transit_hooks):
                self.frame_step(mode)             # injected_starts counted inside hook() itself
        self.armed_frozen_through_transit = (self.m.memory[0x6161] == armed_before)
        self.m.memory[VCOUNT_P2] = 40            # new match's board populated -> fc_clear gate clears
        self.records = []
        self.y, self.x, self.orient = 15, 3, 0
        self._spawn_x = 3
        self.spawn_hook = self.hook_n
        self.lateral_seen = False

    def run_n_pills(self, n, max_frames=10000):
        for _ in range(max_frames):
            self.frame_step(4)
            if len(self.records) >= n:
                break
        return self.records[:n]


def run_arm_condition(arm, condition, seed, n_pills=8, stress=False, grav_th=GRAV_TH):
    P, unit1, labels = build(ARM_SPECS[arm])
    rng = random.Random(seed)
    g = Game(P, unit1, labels, rng, grav_th=grav_th, stress=stress)
    g.boot_cold()
    if condition == "warm":
        g.play_through_rematch()
    recs = g.run_n_pills(n_pills)
    return recs


def run_autorematch_sweep(seeds=50, pills=8, arm_specs=None, transit_modes=(7, 3, 8), label="AUTOREMATCH"):
    """B2: the third, empirically-driven arm x condition -- auto-rematch (fc_clear-owned
    transit, no human menu hand) vs the "menu-flow warm" condition already covered by
    run_arm_condition's "warm". Becomes the permanent regression gate for the fc_clear-bypass
    mechanism once a fix lands. Defaults to MISTER_ARM_SPECS/(7,3,8) (the measured CvC probe-ring
    sequence); pass transit_modes=(7,) for the human-direct-START scope check (team-lead
    2026-08-02) -- DRHUMAN arms compile out fc_clear's START injection (:984-988) but that's
    irrelevant to this specific check (see play_through_autorematch's docstring)."""
    arm_specs = MISTER_ARM_SPECS if arm_specs is None else arm_specs
    out = {}
    for arm in arm_specs:
        all_recs = []
        starts_total = 0
        frozen_count = 0
        for seed in range(seeds):
            P, unit1, labels = build(arm_specs[arm])
            rng = random.Random(seed)
            g = Game(P, unit1, labels, rng)
            g.boot_cold()
            g.play_through_autorematch(transit_modes=transit_modes)
            starts_total += g.injected_starts
            frozen_count += int(g.armed_frozen_through_transit)
            recs = g.run_n_pills(pills)
            for r in recs:
                r["seed"] = seed
            all_recs.extend(recs)
        out[arm] = all_recs
        n = len(all_recs)
        zl = sum(r["zero_lateral"] for r in all_recs) / n if n else 0
        wc = sum(r["wrong_column"] for r in all_recs) / n if n else 0
        mean_hooks = sum(r["think_hooks"] for r in all_recs) / n if n else 0
        print(f"{label} {arm:10s} n={n:4d}  zero_lateral={zl:5.1%}  wrong_column={wc:5.1%}  "
              f"mean_think_hooks={mean_hooks:6.1f}  mean_starts_injected/seed={starts_total/seeds:5.1f}  "
              f"armed_frozen_through_transit={frozen_count}/{seeds}")
    return out


def run_stress_sweep(seeds=50, pills=8, grav_th=10):
    """Hypothesis A' stress test: far-column + rotation + late mid-flight revision, under FAST
    gravity (grav_th frames/row, vs the 40-frame baseline) so the slam/commit gates are under
    real time pressure. Cold boot only (isolates A' from the already-characterized B mechanism).
    """
    out = {}
    for arm in ARM_SPECS:
        all_recs = []
        for seed in range(seeds):
            recs = run_arm_condition(arm, "cold", seed, pills, stress=True, grav_th=grav_th)
            for r in recs:
                r["seed"] = seed
            all_recs.extend(recs)
        out[arm] = all_recs
        n = len(all_recs)
        wc = sum(r["wrong_column"] for r in all_recs) / n if n else 0
        zl = sum(r["zero_lateral"] for r in all_recs) / n if n else 0
        mean_hooks = sum(r["think_hooks"] for r in all_recs) / n if n else 0
        print(f"STRESS {arm:10s} n={n:4d}  wrong_column={wc:5.1%}  zero_lateral={zl:5.1%}  mean_think_hooks={mean_hooks:6.1f}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8, help="number of independent scenario seeds")
    ap.add_argument("--pills", type=int, default=8)
    ap.add_argument("--out", default=str(Path(__file__).parent / "results.json"))
    ap.add_argument("--stress", action="store_true", help="also run the hyp-A' fast-gravity stress sweep")
    ap.add_argument("--stress-gravth", type=int, default=10)
    ap.add_argument("--autorematch", action="store_true", help="also run the B2 CvC auto-rematch sweep")
    args = ap.parse_args()

    out = {}
    for arm in ARM_SPECS:
        for condition in ("cold", "warm"):
            key = f"{arm}/{condition}"
            all_recs = []
            for seed in range(args.seeds):
                recs = run_arm_condition(arm, condition, seed, args.pills)
                for r in recs:
                    r["seed"] = seed
                all_recs.extend(recs)
            out[key] = all_recs
            n = len(all_recs)
            zl = sum(r["zero_lateral"] for r in all_recs) / n if n else 0
            wc = sum(r["wrong_column"] for r in all_recs) / n if n else 0
            mean_hooks = sum(r["think_hooks"] for r in all_recs) / n if n else 0
            print(f"{key:16s} n={n:3d}  zero_lateral={zl:5.1%}  wrong_column={wc:5.1%}  mean_think_hooks={mean_hooks:6.1f}")
    if args.stress:
        print()
        stress_out = run_stress_sweep(seeds=args.seeds, pills=args.pills, grav_th=args.stress_gravth)
        out["_stress"] = stress_out
    if args.autorematch:
        print()
        autorematch_out = run_autorematch_sweep(seeds=args.seeds, pills=args.pills)
        out["_autorematch"] = autorematch_out
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
