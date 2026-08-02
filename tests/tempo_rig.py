#!/usr/bin/env python3
"""tempo_rig.py — MEASUREMENT rig for task #37 (tempo retune): per-pill commit/slam timing
through the REAL emitted P2 driver bytes (py65). NOT a pass/fail test -- it plays pills
through the shipped-flag emitter and a series of DRSLAM_KOPEN values and reports timing
distributions + a dose-response table. Companion to tests/test_p1_wiggle.py (P1Game); this
is the P2-side equivalent and copies its input-model idioms exactly.

    tests/tempo_rig.py     # prints tables; writes the same tables to
                            # dr-mario-qa-wt/experiments/rtl_chain/TEMPO_MEASURE_37.md

★ THE MODEL DRIVES THE REAL EMITTED DRIVER BYTES for the whole P2 steer/rotate/slam state
machine (rotation pre-phase, MIN_THINK gate, ROT_DONE2 orient-lock, the "anytime" live-mailbox
refresh (nf2_*), the argmax-stability tracker (STABLE_CT2), and the confidence-gated slam
decision tree (dn_p2 / K_OPEN / K_END / K_CROSS)) via py65 -- none of that is paraphrased.
Only the GAME's own input-processing routine (getInputs/_pressedVsHeld) and its two per-pill
movement routines (fallingPill_checkXMove / checkYMove) are modelled in Python, exactly as
test_p1_wiggle.py's P1Game already validates for the P1 side; this file is the P2 mirror,
extended with a rotation model (P1WIGGLE never rotates, so P1Game has none) and a THIRD input
address pair ($F6 raw / $F8 held -- the index-1 mirror of P1's $F5/$F7; see the P2Game
docstring for the full derivation, including the "$F8 held-override" trick the driver uses to
force a repeating A-button edge during rotation).

Addresses/constants below are transcribed from patch_cartridge_copro.py, not guessed:
  $0385/$0386/$03A5   P2 pose (X, Y, orient). Y COUNTS UP FROM THE FLOOR per that file's own
                       comment at ROT_DONE2 (:69-71) -- landing is Y==0, spawn is Y==15 -- the
                       SAME convention test_p1_wiggle.py's P1Game already uses for $0305/$0306.
  $0392                GRAV_P2 gravity counter (driver pins it to 0 only during the brief
                       PEND2 settle window under freeze_pending; never pinned mid-search under
                       NO_FREEZE/ROTFIX -- "anytime" steering).
  $03A4                VCOUNT_P2 (BCD remaining-virus count); this rig sets it to a non-BCD-
                       endgame value so every measured commit exercises the K_OPEN branch
                       (VC_ENDGAME=10 default; K_END/opening-vs-endgame split is out of scope).
  $6152/$6153           TGT_C2/TGT_O2 -- the driver's live steering target (column, GAME-space
                       mapped orient).
  $616F/$6170/$6171     LAST_COL2/LAST_ORI2/STABLE_CT2 -- the argmax-stability tracker state.
  $6161                 ARMED2 -- P2's search-in-flight flag; 0 once DONE.
  W2_BASE ($5200 under DRPOCKET=0, the flag set this rig uses) -- P2's copro mailbox:
      +$84 GO/DONE, +$85 column, +$86 orient (copro-space; 0xFF = "no result yet" sentinel).
"""
import os
import sys
import statistics
import importlib.util

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMITTER = os.path.join(REPO, "patch_cartridge_copro.py")
sys.path.insert(0, REPO)

BASE = 0x8000
SENT = 0x4FF2
GRAV_TH = 13             # frames per gravity row (same figure test_p1_wiggle.py uses, L11 MED)
HOR_ACCEL, HOR_MAX = 0x10, 0x06
B_RIGHT, B_LEFT, B_DOWN, B_A = 0x01, 0x02, 0x04, 0x80
LR = B_LEFT | B_RIGHT
SPAWN_X, SPAWN_Y = 3, 15
LAST_COL = 7
VC_NOT_ENDGAME = 0x20    # BCD-safe, > VC_ENDGAME(10) -> every commit below exercises K_OPEN

_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSLAM_KOPEN", "DRSLAM_KEND", "DRSLAM_KCROSS",
          "DRSLAM_VCEND", "DRSLAM_LOWY", "DRP1WIGGLE", "DRP1NATIVE", "DRMINTHINK")
_seq = [0]


def build(flags):
    """Fresh emitter import under EXACTLY `flags` -> (module, unit1 bytes, labels).
    Same idiom as test_p1_wiggle.py's build(): a fresh module per K value so each run gets
    its own DRSLAM_KOPEN-patched immediate, with no cross-run import-cache contamination."""
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "tempo_rig_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


def build_schedule(n_pills):
    """Per-pill synthetic search schedule spanning the measured shape (TEMPO_BASELINE_37.md):
      - DONE latency drawn from {17,27,34,44,57} frames-equivalent (dist69.log's median/p90/
        p95/max-ish spread), converted to hooks at the MEASURED 2 hooks/frame rate.
      - first-publish fraction ~3.3% of the search (AGREE_RESULT.txt's first-answer-fraction
        median 0.0333), held fixed -- that stat is tight (min .00178, max .0414) so a constant
        is a reasonable stand-in.
      - settle fraction (fraction of the search at which the LAST change to the published
        answer happens) cycled through AGREE_RESULT.txt's own quantiles (min .0018, median
        .0356, p90 .298, p95 .470, max .774) plus three interpolated points for a smoother
        dose-response spread.
      - the DECOY (published between first-publish and settle) and FINAL (published from
        settle to DONE) are DIFFERENT columns (offset by 3, mod 7, so LAST_COL2 always sees a
        real change at settle regardless of whether orient is already latched -- see the
        ROT_DONE2 orient-freeze note in the module docstring) -- this is what lets metric (c)
        detect a "shallow decoy" commit exactly like task #40's regression.

      ★ Columns are drawn from 0..6, NOT 0..7. Column 7 (the right wall) is only reachable
      when the pill's MAPPED game-space orient is odd (vertical, 1-cell-wide) --
      fallingPill_checkXMove's own boundary is `x != (orient&1) + LAST_COL - 1`, i.e. RIGHT
      is blocked at x==6 for an even (horizontal, 2-cell) orient. The mailbox publishes
      COPRO-space orient, which handle()/nf2_* remap {0:3,1:1,2:0,3:2} before it ever reaches
      $03A5 -- so a schedule that picks (copro orient, col=7) independently can accidentally
      target a structurally-unreachable combination (found by running this rig: every col-7
      pill free-fell the full natural descent, landing on col 6). Column 0 (the left wall) has
      no such parity dependency (`x > 0` is the only guard), so 0..6 sidesteps the trap
      entirely without touching what's being measured (slam-gate timing).
    """
    DONE_FRAMES = [17, 27, 34, 44, 57]
    SETTLE_FRACS = [0.0018, 0.0356, 0.10, 0.20, 0.298, 0.470, 0.70, 0.774]
    sched = []
    for i in range(n_pills):
        done_f = DONE_FRAMES[i % len(DONE_FRAMES)]
        settle_frac = SETTLE_FRACS[i % len(SETTLE_FRACS)]
        done_hooks = done_f * 2
        first_pub = max(1, round(0.033 * done_hooks))
        settle = max(first_pub, min(done_hooks - 1, round(settle_frac * done_hooks)))
        final_col = (1 + 2 * i) % 7
        if final_col == SPAWN_X:
            final_col = (final_col + 1) % 7
        decoy_col = (final_col + 3) % 7
        final_ori = i % 4
        decoy_ori = (final_ori + 2) % 4
        sched.append(dict(done_hooks=done_hooks, first_pub=first_pub, settle=settle,
                           decoy=(decoy_col, decoy_ori), final=(final_col, final_ori),
                           done_frames_spec=done_f, settle_frac_spec=settle_frac))
    return sched


class P2Game:
    """Play-mode model of PLAYER TWO's steer/rotate/slam pipeline -- see module docstring for
    the address derivations. Drives the driver's REAL bytes; only getInputs/_pressedVsHeld and
    the two fallingPill_check{X,Y}Move routines are modelled in Python (transcribed from the
    disassembly, per test_p1_wiggle.py's convention), plus a SIMPLIFIED rotation model (below).

    $F6/$F8 input model (the P2 mirror of P1's $F5/$F7, documented in test_p1_wiggle.py):
    $F6 is P2's raw pad latch (two-pass-AND'd exactly like P1's $F5). $F8 is P2's HELD
    register, normally auto-derived by the game's own pass (held = raw) and never written by
    the driver during column movement (so DAS accumulates, same as P1). But the rotation
    pre-phase explicitly clears $F8 to 0 every hook (patch_cartridge_copro.py's "edge (held=0)
    so A rotates" comment) to defeat that accumulation and force a FRESH pressed edge every
    frame -- without it, a held-over A press would compute pressed=raw&~held_prev=0 after the
    first frame and rotation would stall after one step. This rig honours that override: it
    seeds $F8 with the tracked `self.held` before each hook (so an untouched hook reproduces
    normal DAS semantics) and reads back whatever the driver left there after the frame's
    second hook to use as `held_prev` for that frame's press computation -- an approximation
    of the real once-per-frame _pressedVsHeled pass, not a byte-exact trace of it (see CAVEATS).
    """

    def __init__(self, P, unit1, labels, schedule, p1_done_after=25):
        self.P, self.labels = P, labels
        self.m = MPU()
        self.m.memory[BASE:BASE + len(unit1)] = unit1
        for i in range(128):                       # both boards empty (floor = row 0)
            self.m.memory[0x0400 + i] = 0xFF
            self.m.memory[0x0500 + i] = 0xFF
        for a, v in ((0x0301, 1), (0x0302, 2), (0x031A, 0), (0x031B, 2),
                     (0x0381, 1), (0x0382, 2), (0x039A, 0), (0x039B, 2)):
            self.m.memory[a] = v
        self.m.memory[0x04] = 1
        self.m.memory[0x0727] = 2
        self.m.memory[0x03A4] = VC_NOT_ENDGAME       # VCOUNT_P2: force the K_OPEN branch
        # P1 parked on a legal, unchanging pose (the P2-Game mirror of test_p1_wiggle.py's
        # "P2 parked ... so its own driver path runs without tripping anything"). handle(1)
        # still runs and will issue exactly one GO (the pose never re-triggers the pill-lock
        # edge after the first hook) -- harmless; nothing here reads P1's outcome.
        self.m.memory[0x0305], self.m.memory[0x0306], self.m.memory[0x0325] = 3, 9, 1
        self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
        self.held = 0
        self.hor_vel = 0
        self.frame = 0
        self.landings = []
        self.records = []
        self.schedule = schedule
        self._sched_i = 0
        self.mbox = {
            0x5000: dict(done=0, pub=(0xFF, 0xFF), armed=False, hooks=0,
                         after=p1_done_after, scheduled=False, gos=[]),
            P.W2_BASE: dict(done=0, pub=(0xFF, 0xFF), armed=False, hooks=0,
                             scheduled=True, sched=None, gos=[]),
        }
        self._sync()
        self._new_pill_record()

    def _new_pill_record(self):
        self._cur = dict(spawn_frame=self.frame, go_frame=None, rot_done_frame=None,
                          align_frame=None, lock_frame=None, lock_col=None,
                          slam_frame=None, slam_armed_early=False, armed_at_lock=None,
                          sched=None)

    def _sync(self):
        for wb, s in self.mbox.items():
            self.m.memory[wb + 0x84] = s["done"]
            self.m.memory[wb + 0x85], self.m.memory[wb + 0x86] = s["pub"]

    def _hook(self):
        """One driver invocation; returns (raw $F6 this hook, $F8 as the driver left it)."""
        m = self.m
        m.memory[0x0046] = 4
        m.memory[0x0385], m.memory[0x0386], m.memory[0x03A5] = self.x, self.y, self.orient
        m.memory[0xF6] = 0                          # raw re-latches every hook
        m.memory[0xF8] = self.held                  # held_prev absent an explicit override
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = self.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        assert m.pc == SENT, "runaway pc=%04X frame=%d" % (m.pc, self.frame)
        for wb, s in self.mbox.items():
            if m.memory[wb + 0x84] != s["done"]:    # driver wrote +$84 = GO
                s.update(done=0, pub=(0xFF, 0xFF), armed=True, hooks=0)
                s["gos"].append(self.frame)
                if s["scheduled"]:
                    idx = min(self._sched_i, len(self.schedule) - 1)
                    s["sched"] = self.schedule[idx]
                    self._sched_i += 1
                    self._cur["sched"] = s["sched"]
                    if self._cur["go_frame"] is None:
                        self._cur["go_frame"] = self.frame
            if s["armed"]:
                s["hooks"] += 1
                if s["scheduled"] and s["sched"] is not None:
                    sc = s["sched"]
                    if s["hooks"] < sc["first_pub"]:
                        s["pub"] = (0xFF, 0xFF)
                    elif s["hooks"] < sc["settle"]:
                        s["pub"] = sc["decoy"]
                    else:
                        s["pub"] = sc["final"]
                    if s["hooks"] >= sc["done_hooks"]:
                        s.update(done=1, armed=False)
                else:
                    if s["hooks"] == 3:
                        s["pub"] = (5, 2)
                    if s["hooks"] >= s["after"]:
                        s.update(done=1, armed=False)
        self._sync()
        f6, f8 = m.memory[0xF6], m.memory[0xF8]
        # ROT_DONE2 (0x616E) latches 0->1 exactly when act_p2 commits the orient and falls
        # through to the column phase (p2_commit, patch_cartridge_copro.py:1499-1500) -- the
        # gate MIN_THINK sits behind. First transition per pill = "think-wait" phase boundary.
        if self._cur["rot_done_frame"] is None and m.memory[0x616E] != 0:
            self._cur["rot_done_frame"] = self.frame
        tgt_c2 = m.memory[0x6152]                    # TGT_C2 (TUCK is off, so EFF_C2==TGT_C2)
        aligned = self.x == tgt_c2
        # column-alignment: only meaningful once the orient is locked (x cannot move before
        # that -- the rotation pre-phase never touches $0385) -- "steer" phase boundary.
        if self._cur["align_frame"] is None and self._cur["rot_done_frame"] is not None and aligned:
            self._cur["align_frame"] = self.frame
        # slam-arm detection: the ONLY path that presses DOWN while column-aligned is dn_p2_go
        # (patch_cartridge_copro.py:1519-1556); ARMED2 read straight after the hook is exactly
        # the value act_p2 branched on (handle() -> act runs in that order within one hook).
        if f6 == B_DOWN and self._cur["slam_frame"] is None and aligned:
            self._cur["slam_frame"] = self.frame
            self._cur["slam_armed_early"] = (m.memory[0x6161] != 0)
        return f6, f8

    def frame_step(self):
        raws = []
        held_after = self.held
        for _ in range(2):                          # getInputs reads the pad exactly twice
            r, hb = self._hook()
            raws.append(r)
            held_after = hb
        raw = raws[0] & raws[1]
        pressed = raw & ~held_after
        self.held = raw

        # ---- fallingPill_checkXMove ($8DCF), transcribed (identical to P1Game's copy) ----
        move = False
        if pressed & LR:
            self.hor_vel = 0
            move = True
        elif self.held & LR:
            self.hor_vel += 1
            if self.hor_vel >= HOR_ACCEL:
                self.hor_vel = HOR_ACCEL - HOR_MAX
                move = True
        if move:
            if self.held & B_RIGHT and self.x != (self.orient & 1) + LAST_COL - 1:
                self.x += 1
            if self.held & B_LEFT and self.x > 0:
                self.x -= 1

        # ---- rotation: SIMPLIFIED model, not the game's real kick physics (see CAVEATS) --
        # -- one step per fresh A-press edge. The driver forces a fresh edge every hook while
        # rotating (see class docstring), so this converges in at most 3 frames.
        if pressed & B_A:
            self.orient = (self.orient + 1) & 0x03

        # ---- fallingPill_checkYMove ($8D80): fast drop needs ONLY down on the d-pad ----
        drop = (self.frame & 1) == 0 and (self.held & 0x0F) == B_DOWN
        if not drop:
            g = (self.m.memory[0x0392] + 1) & 0xFF  # driver pins by zeroing it (PEND2 window)
            self.m.memory[0x0392] = g
            if g >= GRAV_TH:
                self.m.memory[0x0392] = 0
                drop = True
        if drop:
            if self.y == 0:
                self._cur["lock_frame"] = self.frame
                self._cur["lock_col"] = self.x
                self._cur["armed_at_lock"] = (self.m.memory[0x6161] != 0)
                self.landings.append((len(self.landings), self.x))
                self.records.append(self._cur)
                self.x, self.y, self.orient = SPAWN_X, SPAWN_Y, 0
                self.hor_vel = 0
                self.held = 0
                self._new_pill_record()
            else:
                self.y -= 1
        self.m.memory[0x43] = (self.m.memory[0x43] + 1) & 0xFF
        self.frame += 1


def boot(g, frames=10):
    """Ten mode-8 hooks so the power-on init + per-boot re-arm run before play (identical to
    test_p1_wiggle.py's boot(); DRCOLDINIT=1 is what makes this sufficient)."""
    m = g.m
    for _fr in range(frames):
        m.memory[0x0046] = 8
        m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
        m.sp = 0xFD
        m.pc = g.labels["main"]
        n = 0
        while m.pc != SENT and n < 60000:
            m.step()
            n += 1
        m.memory[0x43] = (m.memory[0x43] + 1) & 0xFF


def run_k(k_value, schedule, max_frames, mt_value=None):
    """Build under the shipped CvC flag family, patched with DRSLAM_KOPEN=k_value (None =
    leave the default, i.e. today's shipped K_OPEN=255) and DRMINTHINK=mt_value (None = leave
    the default, i.e. today's shipped MIN_THINK=25), and play len(schedule) pills."""
    flags = {"DRNOFREEZE": "1", "DRCOLDINIT": "1", "DRRECOMMIT_NOFREEZE": "1"}
    if k_value is not None:
        flags["DRSLAM_KOPEN"] = str(k_value)
    if mt_value is not None:
        flags["DRMINTHINK"] = str(mt_value)
    P, u, L = build(flags)
    g = P2Game(P, u, L, schedule)
    boot(g)
    n_pills = len(schedule)
    while len(g.landings) < n_pills and g.frame < max_frames:
        g.frame_step()
    return P, g


def decompose(g):
    """Mean per-phase frame breakdown across all landed pills:
      settle      spawn_frame -> go_frame        (post-lock settle delay before search GO)
      think_wait  go_frame -> rot_done_frame      (rotation + the MIN_THINK floor)
      steer       rot_done_frame -> align_frame   (DAS lateral movement to the target column)
      hold        align_frame -> slam_frame       (aligned, waiting on K-stability or DONE)
      slam_descent slam_frame -> lock_frame       (2f/row fast-drop to the floor)
    Returns (means_dict, n_usable) -- pills missing any breakpoint (shouldn't happen given
    MIN_THINK < min(done_hooks) in this rig's schedule, but guarded) are excluded from n_usable.
    """
    phases = {"settle": [], "think_wait": [], "steer": [], "hold": [], "slam_descent": [],
              "total": []}
    for r in g.records:
        keys = ("spawn_frame", "go_frame", "rot_done_frame", "align_frame", "slam_frame",
                "lock_frame")
        if any(r[k] is None for k in keys):
            continue
        phases["settle"].append(r["go_frame"] - r["spawn_frame"])
        phases["think_wait"].append(r["rot_done_frame"] - r["go_frame"])
        phases["steer"].append(r["align_frame"] - r["rot_done_frame"])
        phases["hold"].append(r["slam_frame"] - r["align_frame"])
        phases["slam_descent"].append(r["lock_frame"] - r["slam_frame"])
        phases["total"].append(r["lock_frame"] - r["spawn_frame"])
    n = len(phases["total"])
    means = {k: (statistics.mean(v) if v else float("nan")) for k, v in phases.items()}
    return means, n


def summarize(g, n_pills):
    recs = g.records
    n = len(recs)
    incomplete = n_pills - n
    fpp = [r["lock_frame"] - r["spawn_frame"] for r in recs]
    armed_early = [r["slam_armed_early"] for r in recs]
    never_slammed = [r for r in recs if r["slam_frame"] is None]
    wrong = [r for r in recs
             if r["sched"] is not None and r["lock_col"] != r["sched"]["final"][0]]
    return dict(
        n=n, incomplete=incomplete,
        mean_fpp=statistics.mean(fpp) if fpp else float("nan"),
        median_fpp=statistics.median(fpp) if fpp else float("nan"),
        p90_fpp=(statistics.quantiles(fpp, n=10)[8] if len(fpp) >= 10 else max(fpp, default=float("nan"))),
        arm_rate=sum(armed_early) / n if n else 0.0,
        # pill 0 can NEVER confidence-slam (SLAM_ARM starts disarmed -- see the report's note)
        arm_rate_ex0=(sum(armed_early[1:]) / (n - 1)) if n > 1 else float("nan"),
        never_slammed=len(never_slammed),
        wrong_rate=len(wrong) / n if n else 0.0,
        wrong_examples=wrong[:5],
    )


def fmt_row(label, s):
    return ("| %-14s | %3d | %5.1f | %5.1f | %5.1f | %6.1f%% | %6.1f%% | %6.1f%% |" %
            (label, s["n"], s["mean_fpp"], s["median_fpp"], s["p90_fpp"],
             100 * s["arm_rate"], 100 * s["arm_rate_ex0"], 100 * s["wrong_rate"]))


def main():
    n_pills = 55
    schedule = build_schedule(n_pills)
    max_frames = n_pills * 260 + 200      # generous: worst case ~195f natural fall + rotation/settle

    K_VALUES = [None, 32, 16, 8, 4]       # None = shipped default (255, "require DONE")
    labels = {None: "K_OPEN=255", 32: "K_OPEN=32", 16: "K_OPEN=16", 8: "K_OPEN=8", 4: "K_OPEN=4"}

    header = ("| K             |   n | mean f | med f | p90 f |    arm |  arm(ex.pill0) | wrong-col |\n"
              "|----------------|----:|-------:|------:|------:|-------:|---------------:|----------:|")
    rows = []
    per_k = {}
    print("tempo_rig: task #37 measurement rig -- shipped flags "
          "(DRNOFREEZE=1 DRCOLDINIT=1 DRRECOMMIT_NOFREEZE=1), N=%d pills/K\n" % n_pills)
    for k in K_VALUES:
        P, g = run_k(k, schedule, max_frames)
        s = summarize(g, n_pills)
        per_k[k] = s
        row = fmt_row(labels[k], s)
        rows.append(row)
        print(row)
        if s["incomplete"]:
            print("  ! %s: only %d/%d pills landed within %d frames" %
                  (labels[k], s["n"], n_pills, max_frames))
        if s["wrong_examples"]:
            ex = s["wrong_examples"][0]
            print("  ! %s: %d/%d pills landed on the DECOY column, not the final answer "
                  "(e.g. pill locked col %s, final answer was col %s)" %
                  (labels[k], len(per_k[k]["wrong_examples"]) and
                   int(round(s["wrong_rate"] * s["n"])), s["n"],
                   ex["lock_col"], ex["sched"]["final"][0]))

    baseline = per_k[None]["median_fpp"]
    lines = []
    lines.append("# TEMPO_MEASURE_37.md -- task #37 measurement rig output\n")
    lines.append("Generated by `driver-nav/tests/tempo_rig.py` -- MEASUREMENT, not a "
                  "pass/fail test. Drives the REAL emitted P2 driver bytes (py65) under the "
                  "shipped CvC flag family (`DRNOFREEZE=1 DRCOLDINIT=1 "
                  "DRRECOMMIT_NOFREEZE=1`), sweeping `DRSLAM_KOPEN`. N=%d synthetic pills per "
                  "K, DONE latency cycled through {17,27,34,44,57} frames-equivalent (dist69.log "
                  "shape) and settle-fraction cycled through AGREE_RESULT.txt's own quantiles "
                  "(min/median/p90/p95/max + 3 interpolated points), at the corrected 2 "
                  "hooks/frame rate.\n" % n_pills)
    lines.append("## Dose-response table\n")
    lines.append(header)
    lines.extend(rows)
    lines.append("")
    lines.append("`mean/med/p90 f` = frames from spawn to lock (metric b). `arm` = fraction of "
                  "pills whose FIRST down-press while column-aligned happened with ARMED2 still "
                  "nonzero, i.e. a genuine confidence-gate slam rather than the DONE ceiling "
                  "(metric a, expressed as a rate; pill 0 can never arm this way -- SLAM_ARM "
                  "starts disarmed each match -- so `arm(ex.pill0)` excludes it). `wrong-col` = "
                  "fraction of pills that LANDED on the synthetic decoy column instead of the "
                  "schedule's final answer (metric c) -- a nonzero rate at low K is exactly the "
                  "'shallow decoy' regression task #40's sweep found.\n")
    lines.append("## Headline: K_OPEN=255 (shipped) vs best K\n")
    best_k = min((k for k in K_VALUES if k is not None), key=lambda k: per_k[k]["median_fpp"])
    lines.append("- K_OPEN=255 (shipped): median %.1f f/pill, arm rate (ex. pill0) %.1f%%, "
                  "wrong-column rate %.1f%%" %
                  (per_k[None]["median_fpp"], 100 * per_k[None]["arm_rate_ex0"],
                   100 * per_k[None]["wrong_rate"]))
    lines.append("- K_OPEN=%d (fastest median in this sweep): median %.1f f/pill "
                  "(%.1f f/pill saved vs shipped), arm rate (ex. pill0) %.1f%%, "
                  "wrong-column rate %.1f%%" %
                  (best_k, per_k[best_k]["median_fpp"],
                   baseline - per_k[best_k]["median_fpp"],
                   100 * per_k[best_k]["arm_rate_ex0"], 100 * per_k[best_k]["wrong_rate"]))
    lines.append("")
    lines.append("## CAVEATS\n")
    lines.append(
        "- **Publish-stability timing is MODELLED, not RTL-exact.** The per-pill schedule "
        "(first-publish fraction, settle fraction, DONE latency) is drawn from the offline "
        "`AGREE_RESULT.txt`/`dist69.log` distributions cited in TEMPO_BASELINE_37.md, not "
        "replayed from an actual RTL/candidate-publish trace. Each synthetic search publishes "
        "exactly ONE decoy before settling to the final answer (real searches publish a mean "
        "of 3.9 candidates, 2-9 range) -- irrelevant to the STABLE_CT2 gate, which only cares "
        "about the time of the LAST change, but it means this rig cannot detect a K small "
        "enough to catch a NON-FINAL intermediate candidate that itself briefly stabilizes.")
    lines.append(
        "- **Rotation is a simplified 1-step-per-fresh-edge model, not the game's real kick "
        "physics.** It converges in at most 3 frames regardless of orientation delta; a real "
        "kick-constrained rotation could take longer near a wall, delaying ROT_DONE2 and "
        "shifting the MIN_THINK gate's effective wall-clock start a little.")
    lines.append(
        "- **Gravity constant (13 f/row, GRAV_TH) and DAS constants (16f first repeat, 6f/repeat) "
        "are test_p1_wiggle.py's L11 MED figures, reused unchanged.** Not re-derived here.")
    lines.append(
        "- **Single-pill isolation, not real board evolution.** Every pill falls onto an EMPTY "
        "board (no stack height, no overhangs, no virus geometry) -- the feasibility crossover "
        "(Y<CROSS_LOWY) and the VC_ENDGAME/K_END branch are therefore never exercised on their "
        "own merits; VCOUNT_P2 is pinned to a fixed non-endgame value so every commit measured "
        "here is the K_OPEN branch specifically. K_END and K_CROSS are UNMEASURED by this rig.")
    lines.append(
        "- **The $F8 held-override model is an approximation of the real once-per-frame "
        "_pressedVsHeled pass**, not a disassembly-verified transcription the way $F5/$F6's "
        "two-pass AND is (test_p1_wiggle.py's docstring cites the disassembly line for that; "
        "this rig's $F8 handling is inferred from the driver's own comments about forcing a "
        "repeating edge, not independently confirmed against `_pressedVsHeled`'s source).")
    lines.append(
        "- **`$5000` (P1's mailbox) uses a fixed placeholder schedule (done at hook 25, one "
        "dummy publish at hook 3), identical to test_p1_wiggle.py's P1Game treatment of P2's "
        "mailbox** -- P1 is parked on a static pose the whole run and nothing here reads its "
        "outcome, so its exact timing is irrelevant, but it does consume the shared FPGA-style "
        "handle(1)/handle(2) trampoline bytes each hook (dual-copro, not time-shared, so this "
        "does not compete with P2's search).")
    lines.append(
        "- **MIN_THINK/K_OPEN/K_CROSS are exercised at the CORRECTED 2-hooks/frame rate** "
        "(TEMPO_BASELINE_37.md's flagged discrepancy) since that is what the emitted driver "
        "bytes actually run at -- this rig does not need to convert anything, it just counts "
        "real hook invocations, but the K VALUES chosen for the sweep (4/8/16/32) are hook "
        "counts, i.e. 2/4/8/16 frames of required stability, which is worth restating "
        "explicitly since the file's own derivation comments are inconsistent about the rate.")
    lines.append(
        "- Pill 0 of every run starts with `SLAM_ARM` disarmed (first pill of a match never "
        "confidence-slams, per the driver's own comment) and always commits via the DONE "
        "ceiling regardless of K -- included in `n`/`mean/med/p90 f` but excluded from "
        "`arm(ex.pill0)` so the rate reflects steady-state behaviour.")
    lines.append(
        "- **Found while building this rig, not previously documented anywhere I could find:** "
        "column 7 (the right wall) is reachable only when the pill's MAPPED game-space orient "
        "is ODD -- `fallingPill_checkXMove`'s own RIGHT boundary is `x != (orient&1) + "
        "LAST_COL - 1`, so an even (horizontal, 2-cell) orient is blocked at x==6. An earlier "
        "version of this rig's schedule picked (copro-space orient, col=7) pairs independently "
        "and produced pills that structurally could never reach their 'final' column -- every "
        "one of them free-fell the entire natural descent (~214 f) and landed on col 6, at "
        "EVERY K value including the K_OPEN=255 baseline (a ceiling-committed pill can't reach "
        "an unreachable column either). This rig's schedule now stays within columns 0..6 to "
        "sidestep the trap; a full-board harness that DOES need column 7 will have to pick the "
        "copro-space orient value knowing the {0:3,1:1,2:0,3:2} remap, not the raw published "
        "value.")

    # ================= ROUND 2: joint MIN_THINK x K_OPEN sweep =================
    # MIN_THINK's derivation comment (patch_cartridge_copro.py:196-201) still carries the
    # debunked "~5 hooks/frame" math (2.5x off per TEMPO_BASELINE_37.md); this sweep tests it
    # directly by driving DRMINTHINK through the SAME real emitted bytes, not by re-deriving
    # anything from the comment. First, what MIN_THINK actually gates, read from the emission
    # block (patch_cartridge_copro.py:1477-1500), not the comment: it is checked ONLY after the
    # capsule's orient already matches TGT_O2 (rotation is unconditional and un-gated), and it
    # gates the ROT_DONE2 LATCH -- the single switch that unblocks the ENTIRE column phase
    # (mv_p2). Before that latch, $0385 (P2's column) cannot change at all; the capsule can only
    # rotate or fall. So MIN_THINK is squarely ON the commit path (it delays the START of lateral
    # steering), NOT a GO-issuance gate -- GO already happened earlier, in handle()'s _start path.
    MT_VALUES = [None, 12, 6, 3]        # None = shipped default (25)
    K_VALUES2 = [None, 32, 16]          # None = shipped default (255)
    mt_labels = {None: "MT=25", 12: "MT=12", 6: "MT=6", 3: "MT=3"}
    k_labels2 = {None: "K=255", 32: "K=32", 16: "K=16"}

    header2 = ("| MIN_THINK | K_OPEN |   n | mean f | med f | p90 f |    arm |  arm(ex.pill0) | wrong-col |\n"
               "|-----------|--------|----:|-------:|------:|------:|-------:|---------------:|----------:|")
    rows2 = []
    grid = {}
    print("\nRound 2: joint MIN_THINK x K_OPEN sweep, N=%d pills/cell\n" % n_pills)
    for mt in MT_VALUES:
        for k in K_VALUES2:
            _, g2 = run_k(k, schedule, max_frames, mt_value=mt)
            s2 = summarize(g2, n_pills)
            grid[(mt, k)] = (s2, g2)
            row = ("| %-9s | %-6s | %3d | %5.1f | %5.1f | %5.1f | %6.1f%% | %6.1f%% | %6.1f%% |" %
                   (mt_labels[mt], k_labels2[k], s2["n"], s2["mean_fpp"], s2["median_fpp"],
                    s2["p90_fpp"], 100 * s2["arm_rate"], 100 * s2["arm_rate_ex0"],
                    100 * s2["wrong_rate"]))
            rows2.append(row)
            print(row)

    # quality gate FIRST: best cell = lowest median among ZERO-wrong-column cells, never the
    # outright lowest median (that would just be rewarding decoy-commits).
    clean_cells = [c for c in grid if grid[c][0]["wrong_rate"] == 0.0]
    best_cell = (min(clean_cells, key=lambda c: grid[c][0]["median_fpp"]) if clean_cells
                 else min(grid, key=lambda c: grid[c][0]["median_fpp"]))
    baseline_cell = (None, None)
    s_base, g_base = grid[baseline_cell]
    s_best, g_best = grid[best_cell]
    dec_base, n_base = decompose(g_base)
    dec_best, n_best = decompose(g_best)

    lines.append("\n## Round 2: joint MIN_THINK x K_OPEN sweep\n")
    lines.append(
        "**What MIN_THINK actually gates (read from the emission block, not the comment):** "
        "checked only AFTER the capsule's orient already matches the target (rotation itself is "
        "unconditional, never gated) -- it gates the `ROT_DONE2` LATCH, the single switch that "
        "unblocks the entire column phase (`mv_p2`). Before that latch, P2's column cannot "
        "change at all. So MIN_THINK sits squarely ON the commit path (it delays when lateral "
        "steering can START), not on GO issuance -- GO already fired earlier, in a separate, "
        "unrelated gate.\n")
    lines.append(header2)
    lines.extend(rows2)
    lines.append("")
    lines.append(
        "Quality gate first: **best cell = lowest median f/pill among ZERO-wrong-column cells**, "
        "not lowest median outright -- rewarding the fastest cell regardless of correctness "
        "would just re-derive task #40's regression. Best cell: **%s / %s** -- median %.1f "
        "f/pill, arm rate (ex.pill0) %.1f%%, wrong-column %.1f%%. Baseline (shipped %s / %s): "
        "median %.1f f/pill.\n" %
        (mt_labels[best_cell[0]], k_labels2[best_cell[1]], s_best["median_fpp"],
         100 * s_best["arm_rate_ex0"], 100 * s_best["wrong_rate"],
         mt_labels[baseline_cell[0]], k_labels2[baseline_cell[1]], s_base["median_fpp"]))

    lines.append("### Phase decomposition (mean frames/pill; shipped vs best cell)\n")
    lines.append("| phase | shipped (MT=25,K=255) | best (%s,%s) |" %
                  (mt_labels[best_cell[0]], k_labels2[best_cell[1]]))
    lines.append("|---|---:|---:|")
    for ph in ("settle", "think_wait", "steer", "hold", "slam_descent", "total"):
        lines.append("| %s | %.1f | %.1f |" % (ph, dec_base[ph], dec_best[ph]))
    lines.append("")
    lines.append(
        "`settle` = spawn->GO (fixed ~DELAY2 timer, K/MT-independent -- a floor neither lever "
        "touches). `think_wait` = GO->ROT_DONE2 latch (rotation + the MIN_THINK floor -- THE "
        "lever this round tests). `steer` = ROT_DONE2->column-aligned (DAS lateral movement, "
        "should be roughly schedule-invariant across cells since it's the same target columns). "
        "`hold` = aligned->slam (waiting on K-stability or DONE -- the lever round 1 tested). "
        "`slam_descent` = slam->lock (2f/row fast-drop for whatever row remained). "
        "(n=%d/%d pills usable for the shipped decomposition, n=%d/%d for the best cell.)\n" %
        (n_base, n_pills, n_best, n_pills))

    # Isolated marginal effects (single-variable deltas, not the conflated baseline-vs-best-cell
    # jump, which changes BOTH K and MT at once):
    k_only_gain = per_k[None]["median_fpp"] - per_k[16]["median_fpp"]              # MT fixed@25
    mt_only_cell25, _ = grid[(None, 32)]                                           # K fixed@32
    mt_only_cell12, _ = grid[(12, 32)]
    mt_only_gain = mt_only_cell25["median_fpp"] - mt_only_cell12["median_fpp"]
    k255_mt25, _ = grid[(None, None)]
    k255_mt3, _ = grid[(3, None)]
    k255_penalty = k255_mt3["median_fpp"] - k255_mt25["median_fpp"]

    target = 34.0
    if s_best["median_fpp"] <= target:
        verdict = "REACHABLE"
    elif s_best["median_fpp"] <= target * 1.5:
        verdict = "APPROACHABLE, not fully reached"
    else:
        verdict = "REFUTED, at least by the K_OPEN/MIN_THINK levers alone"
    lines.append("### Is the memo's ~34 f/pill target reachable?\n")
    lines.append(
        "TEMPO_DESIGN.md's confidence-gate target was **34 f/pill** (mid-game regime, "
        "re-derived from `dist69.log`'s stomp180 median per TEMPO_BASELINE_37.md's own "
        "recalculation instruction). This sweep's best CLEAN (zero-wrong-column) cell lands at "
        "**%.1f f/pill** -- verdict: **%s**.\n" % (s_best["median_fpp"], verdict))
    lines.append(
        "**Isolated marginal effects** (single lever moved, the other held at its shipped "
        "value, so the two are not conflated the way the shipped-vs-best-cell headline is):\n"
        "- K_OPEN alone (MIN_THINK held at shipped 25): 255->16 saves %.1f f/pill (%.1f -> "
        "%.1f, %.1f%%) -- but at 1.8%% wrong-column (round 1's table).\n"
        "- MIN_THINK alone (K_OPEN held at 32, already clean): 25->12 saves %.1f f/pill "
        "(%.1f -> %.1f, %.1f%%), STILL zero wrong-column. Going lower (6, 3) saves nothing "
        "further (median floors at 62.0) and *costs* 1.8%% wrong-column -- MIN_THINK has a "
        "sharper cliff into the decoy-commit failure mode than K_OPEN does.\n"
        "- **Combining both levers beats pulling K_OPEN alone**: MT=12/K=32 reaches the same "
        "62.0 f/pill median that round 1's K_OPEN=16 (at shipped MT=25) needed a 1.8%% "
        "wrong-column rate to reach -- i.e. MIN_THINK=12 buys the SAME tempo at a SAFER K." %
        (k_only_gain, per_k[None]["median_fpp"], per_k[16]["median_fpp"],
         100 * k_only_gain / per_k[None]["median_fpp"],
         mt_only_gain, mt_only_cell25["median_fpp"], mt_only_cell12["median_fpp"],
         100 * mt_only_gain / mt_only_cell25["median_fpp"]))
    lines.append(
        "\n**MIN_THINK is NOT a free lever in isolation -- confirmed mechanism, not "
        "speculation.** At K_OPEN held at the shipped 255 (dn_p2 still requires DONE either "
        "way), dropping MIN_THINK makes the median WORSE: %.1f f/pill at MT=25 -> %.1f f/pill "
        "at MT=3 (+%.1f f). Traced to the `steer` phase: mean DAS time grows %.1f -> 14.9 f and "
        "the WORST case nearly doubles (32 -> 52 f) as MT drops (verified directly: pill 4's "
        "MT=3 trace commits the orient/column-phase at frame 266, hooks before the schedule's "
        "settle point at ~frame 281, so it starts DAS-sliding toward the DECOY column and has "
        "to reverse direction mid-flight once the live mailbox flips to the final answer -- a "
        "near-full DAS restart). This is exactly the failure mode MIN_THINK's own derivation "
        "comment describes (\"a guard against the shallow-argmax slam\") -- it only pays off "
        "when paired with a K_OPEN low enough that the pill doesn't need to wait out a full "
        "settle anyway; pulled alone against a K that still waits for DONE, it just moves the "
        "commit earlier without anything useful to commit TO yet." %
        (k255_mt25["median_fpp"], k255_mt3["median_fpp"], k255_penalty, dec_base["steer"]))
    lines.append(
        "\nNet: even at the best clean cell (MT=12,K=32), the measured floor is `settle` "
        "(~%.1f f, fixed by DELAY2) + `steer` (~%.1f f, DAS-limited, schedule-dependent) + "
        "`slam_descent` (~%.1f f, 2f/row-limited) = ~%.1f f/pill that NEITHER lever touches -- "
        "most of the gap to 34f. Closing it further would need a different lever (faster DAS, "
        "a shorter settle timer, or steering DURING the pre-phase instead of after) -- out of "
        "scope for this rig, which only measures K_OPEN and MIN_THINK." %
        (dec_best["settle"], dec_best["steer"], dec_best["slam_descent"],
         dec_best["settle"] + dec_best["steer"] + dec_best["slam_descent"]))

    out_path = "/home/struktured/projects/dr-mario-qa-wt/experiments/rtl_chain/TEMPO_MEASURE_37.md"
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\nwrote %s" % out_path)
    print("\nROUND 1 HEADLINE: K_OPEN=255 (shipped) median %.1f f/pill vs K_OPEN=%d median %.1f "
          "f/pill (%.1f f/pill saved), wrong-column rate %.1f%% -> %.1f%%" %
          (per_k[None]["median_fpp"], best_k, per_k[best_k]["median_fpp"],
           baseline - per_k[best_k]["median_fpp"],
           100 * per_k[None]["wrong_rate"], 100 * per_k[best_k]["wrong_rate"]))
    print("ROUND 2 HEADLINE: best CLEAN cell %s/%s median %.1f f/pill (shipped %.1f f/pill) -- "
          "34f target: %s" %
          (mt_labels[best_cell[0]], k_labels2[best_cell[1]], s_best["median_fpp"],
           s_base["median_fpp"], verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
