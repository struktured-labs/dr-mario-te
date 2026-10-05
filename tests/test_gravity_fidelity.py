#!/usr/bin/env python3
"""GRAVITY-FIDELITY GATE (settle lane, 2026-10-03): the P2 driver may change the game ONLY through the controller.

Owner rule (memory owner-ruling-superhuman-input-rate): faster than a human is fair, cheating is not -- and pinning
gravity is cheating. The 2026-07-19 fidelity audit (tests/test_driver_fidelity.py) asserted the freeze_pending SETTLE
pin as "the one deployed in-window pin, ~3 frames inside the ~20 f spawn window": its mock reloads the drop timer every
frame, so a pin "inside the window" looked free. The ROM's speed counter is CUMULATIVE (fallingPill_checkYMove: inc,
drop when > speedCounterTable[...]), so every pinned frame delays the drop; Mesen measured G0 = 6 on the stock couch cart
vs G0 = 1 on the unmodified game (5 frames per pill). That test is also not in tools/gate/run_cart_gates.sh, and
experiments/reach/gate_tap_interface.py's world rewrites $0392 from its own copy every frame, so it cannot see the pin.

THIS GATE. The REAL emitted driver (unit-1 `main` + the P1 native AI units, IR captured from the emitter under a cart's
flag snapshot by tools/nmi126/capture_ir.py, ground-truth gated) runs under py65 against a ROM-rule P2 world whose
state LIVES IN THE GAME'S OWN RAM: each frame the world reads p2 RAM ($0385 X, $0386 Y, $0392 speed counter, $0393
horVelocity, $0397 nextAction, $03A5 rotation, $03A7 pill counter, the board $0500-$057F ...), steps it with the ROM
rules, and writes it back -- exactly what the ROM's p2RAM_toCurrentP / nextAction / currentP_toP2 do, so a driver store
to any of those bytes IS seen by the game, as on silicon.
  Run A: closed loop, the driver hooked twice per frame inside the "NMI" (the ROM's two-pass controller read: the pad
         the game consumes is R = pass1 & pass2, pressed = R & ~held). The (pressed, held) pair is recorded per frame.
  Run B: the SAME world (same seed), NO driver at all, the recorded pads replayed = the unmodified game under the same
         inputs.
  FAIL iff A and B differ on any frame (P2 nextAction, Y, X, rotation, speed counter, horVelocity, pill counter, board
  hash) -- i.e. some P2 pill's gravity / lock / position timing differs from the unmodified game's under the same
  inputs. The first divergence is printed with the driver stores into world RAM that caused it.
World coverage (each counted; a zero count is a FAILURE, never a vacuous pass -- rule 26):
  round starts (level init: Y=$0F with p2_nextAction = sendPill, the throw 1-2 frames later), mid-round spawns after
  clear windows, P1 garbage releases into P2 (the $0318 release edge + a fall window: DRPRESTART pipelines run),
  STALE-DONE edges (the copro has not DONE when the capsule locks -> the next pill's edge finds ARMED2 still set, the
  DRPENDBOUND bound path), throat-ledge boards (DRPROPH), speeds LOW/MED/HI with speedUps 0-49.
Arms (the gate is two-sided, killed-mutant standard):
  MUST PASS : couch + CvC with DRSETTLE=3 DRSETTLEPIN=0 (the fair build), and DRSETTLE=3 with the pin kept.
  MUST FAIL : couch 464a4b75 / CvC 387bb7bd flag sets (the shipped 15-hook settle + pin) -- proves the check can see it.
  test_gravity_fidelity.py [--frames N] [--seed S] [--arm NAME] [--json]
"""
import argparse, json, os, random, subprocess, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

A_, B_, DOWN_, LEFT_, RIGHT_ = 0x80, 0x40, 0x04, 0x02, 0x01
SPEED_TABLE = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27, 0x25, 0x23,
               0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D, 0x0C, 0x0B, 0x0A, 0x09,
               0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
               0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03, 0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01,
               0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00]
SPEED_BASE = [0x0F, 0x19, 0x1F]
MAGIC, MODE, Z04, MATCH = 0x6149, 0x46, 0x04, 0x6164
X2, Y2, CA, CB, SU, SP, SCNT, HV, NA, NA_A, NA_B, ROT, PC, VC, LVL = (0x0385, 0x0386, 0x0381, 0x0382, 0x038A, 0x038B,
    0x0392, 0x0393, 0x0397, 0x039A, 0x039B, 0x03A5, 0x03A7, 0x03A4, 0x0396)
ATK1 = 0x0318                          # p1_attackSize: P2's checkReleaseAttack consumes it (the release edge)
BOARD = 0x0500
WORLD_RAM = [X2, Y2, CA, CB, SU, SP, SCNT, HV, NA, NA_A, NA_B, ROT, PC, ATK1] + list(range(BOARD, BOARD + 128))
NAMES = {X2: "X $0385", Y2: "Y $0386", SCNT: "SPEED COUNTER $0392", HV: "horVelocity $0393", NA: "nextAction $0397",
         ROT: "rotation $03A5", PC: "pillsCounter $03A7", SU: "speedUps $038A", SP: "speed $038B", CA: "colour $0381",
         CB: "colour $0382", NA_A: "preview $039A", NA_B: "preview $039B", ATK1: "p1 attackSize $0318"}
ARMED2, PEND2, DELAY2, PRE_ACT2 = 0x6161, 0x614F, 0x615F, 0x619A

ARMS = {   # name: (flags json, overlays, expectation)
    "couch_fair":     ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0"}, "pass"),
    "cvc_fair":       ("experiments/lateflip/cvc_3b8737a9_flags.json",
                       {"DRLATEGUARD": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0"}, "pass"),
    "couch_settle3_pinkept": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3"}, "pass"),
    # the fair couch CANDIDATE: + DRPROPHFIRST (PROPH's ledge escape before the rotation pre-phase); the other fair
    # ledge-fix flags (DRPROPHHOLD / DRDISTROW / DRLEDGECOMMIT) were measured too: experiments/settle/RESULT_SETTLE.md
    "couch_fair_D":   ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1"},
                       "pass"),
    # DRABORTSTALE (abort-stale lane): the fair candidate + the stale-search abort at the new-pill edge, couch and CvC.
    # Must PASS, and additionally upload NO dead pill (see dead_pill_uploads below; the flag-off arms are only counted).
    "couch_fair_D_abort": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1",
                        "DRABORTSTALE": "1"}, "pass"),
    "cvc_fair_abort": ("experiments/lateflip/cvc_3b8737a9_flags.json",
                       {"DRLATEGUARD": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRABORTSTALE": "1"}, "pass"),
    # execfid lane (2026-10-04): DRLGPRESTART (prestart answers bypass DRLATEGUARD) and DRDISTROW on the fair carts.
    "couch_fair_D_lgp": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1",
                        "DRLGPRESTART": "1"}, "pass"),
    "couch_fair_A_lgp": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1",
                        "DRABORTSTALE": "1", "DRLGPRESTART": "1"}, "pass"),
    "couch_fair_A_row": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1",
                        "DRABORTSTALE": "1", "DRDISTROW": "1"}, "pass"),
    "couch_fair_D_lgp_row": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1",
                        "DRLGPRESTART": "1", "DRDISTROW": "1"}, "pass"),
    "couch_fair_A_lgp_row": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1",
                        "DRABORTSTALE": "1", "DRLGPRESTART": "1", "DRDISTROW": "1"}, "pass"),
    "couch_464a4b75": ("experiments/lateflip/couch_c960dd49_flags.json", {"DRLATEGUARD": "1", "DRSTUDYEND": "1"}, "fail"),
    "couch_settle3_noguard": ("experiments/lateflip/couch_c960dd49_flags.json",
                       {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0",
                        "DRSETTLE_MUT": "noguard"}, "fail_upload"),
    "cvc_387bb7bd":   ("experiments/lateflip/cvc_3b8737a9_flags.json", {"DRLATEGUARD": "1"}, "fail"),
}


def capture(flags, overlays, tag):
    snap = json.load(open(os.path.join(ROOT, flags)))["flag_snapshot"]
    snap.update(overlays)
    d = os.path.join(ROOT, "tmp", "gravity_gate"); os.makedirs(d, exist_ok=True)
    man = os.path.join(d, f"{tag}_{os.getpid()}.manifest.json"); out = os.path.join(d, f"{tag}_{os.getpid()}_ir.json")
    json.dump({"flag_snapshot": snap}, open(man, "w"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nmi126", "capture_ir.py"), man, out], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-2500:]
    ir = json.load(open(out))
    os.remove(man); os.remove(out)
    return ir, snap


class Copro:
    """P2 mailbox ($5284 GO/DONE, $5285 col, $5286 orient4, $5287/8 no tuck). Anytime: invalid, then a target,
    sometimes a flip, then DONE -- or, STALE: DONE only after a very long delay, so the capsule locks while ARMED."""
    def __init__(self, rng, w=0x5200):
        self.rng, self.w = rng, w
        self.state, self.done, self.col, self.o4, self.frame = "idle", 1, 3, 2, 0
        self.goes = self.stale = 0

    def on_go(self, addr, value):
        r = self.rng
        self.goes += 1
        self.state, self.done, self.o4, self.col = "search", 0, 0xFF, 0
        self.t_pub = self.frame + r.randint(1, 8)
        self.t_flip = self.t_pub + r.randint(2, 12) if r.random() < 0.25 else None
        if r.random() < 0.15:
            self.t_done = self.frame + r.randint(250, 700); self.stale += 1
        else:
            self.t_done = self.t_pub + r.randint(0, 30)

    def target(self):
        o4 = self.rng.randrange(4); col = self.rng.choice([0, 1, 2, 3, 3, 4, 4, 5, 6, 7])
        if o4 & 2 and col > 6:
            col = 6
        return col, o4

    def tick(self, frame):
        self.frame = frame
        if self.state != "search":
            return
        if frame >= self.t_pub and self.o4 == 0xFF:
            self.col, self.o4 = self.target()
        if self.t_flip is not None and frame >= self.t_flip:
            self.col, self.o4 = self.target(); self.t_flip = None
        if frame >= self.t_done:
            if self.o4 == 0xFF:
                self.col, self.o4 = self.target()
            self.done, self.state = 1, "idle"

    def read(self, addr):
        off = addr - self.w
        return {0x84: self.done, 0x85: self.col, 0x86: self.o4, 0x87: 0xFF, 0x88: 0x00}.get(off)


class World:
    """ROM-rule P2 seat; ALL state that the ROM keeps in RAM is read from / written to RAM every frame."""
    def __init__(self, rng, m):
        self.r, self.m = rng, m
        self.mode_wait = 0; self.throw_in = 0; self.win = 0; self.garbage_pending = False
        self.pills = 0; self.round_pills = 0; self.f = 0
        self.locks = []
        self.starts = []                                   # frame each pill's lifecycle starts (its new-pill edge)
        self.in_round_start = False
        self.cnt = collections.Counter()
        self.round_start()

    # ---- RAM-backed state
    def rd(self):
        m = self.m
        return dict(x=m[X2], y=m[Y2], rot=m[ROT], scnt=m[SCNT], hv=m[HV], na=m[NA], pc=m[PC], su=m[SU], sp=m[SP])

    def cell(self, row, c):
        return self.m[BOARD + row * 8 + c]

    def empty(self, row, c):
        return 0 <= c < 8 and 0 <= row < 16 and self.cell(row, c) in (0x00, 0xFF)

    def fits(self, x, row, rot):
        if row >= 16:
            return False
        if rot % 2 == 0:
            return 0 <= x <= 6 and self.empty(row, x) and self.empty(row, x + 1)
        return 0 <= x <= 7 and self.empty(row, x) and (row == 0 or self.empty(row - 1, x))

    def thr(self):
        return SPEED_TABLE[min(80, SPEED_BASE[self.m[SP] % 3] + self.m[SU])]

    # ---- round / board
    def new_board(self):
        r, m = self.r, self.m
        kind = r.randrange(5)
        for i in range(128):
            m[BOARD + i] = 0xFF
        for c in range(8):
            h = r.choice([0, 1, 2, 4, 6, 8, 10, 12])
            if kind == 1 and c in (3, 4):
                h = r.choice([13, 14])                     # tall throat -> DRPROPH ledge regime
            if kind == 2 and c % 2 == 0:
                h = r.choice([10, 12, 14])                 # wells
            for row in range(16 - min(h, 15), 16):
                m[BOARD + row * 8 + c] = (0xD0 | r.randrange(3)) if (row > 9 and r.random() < 0.3) else (0x60 | r.randrange(3))
        m[BOARD + 3] = m[BOARD + 4] = 0xFF                # spawn cells free

    def round_start(self):
        r, m = self.r, self.m
        self.new_board()
        m[SP] = r.randrange(3); m[SU] = r.choice([0, 0, 5, 12, 20, 30, 40, 49])
        # level init: pillsCounter := 0, generateNextPill twice -> Y=$0F, counter 2, nextAction = sendPill; the THROW
        # (a third generateNextPill) comes 1-3 frames later. Colours come from the shared reserve $0780 like the ROM's.
        for i in range(128):
            m[0x0780 + i] = r.randrange(9)
        m[PC] = 0
        self.gen_next(); self.gen_next()
        m[X2], m[Y2], m[ROT], m[SCNT] = 3, 15, 0, 0
        m[NA] = 6
        self.starts.append(self.f); self.in_round_start = True    # level init: the stock Y test fires its edge here
        self.throw_in = r.randint(1, 3); self.round_pills = 0
        self.cnt["round_starts"] += 1

    def gen_next(self):
        """generateNextPill's colour half: capsule <- preview, preview <- colorCombination[pillsReserve[counter]]
        (left = v/3, right = v%3), counter++ (mod 128)."""
        m = self.m
        m[CA], m[CB] = m[NA_A], m[NA_B]
        v = m[0x0780 + (m[PC] & 0x7F)] % 9
        m[NA_A], m[NA_B] = v // 3, v % 3
        m[PC] = (m[PC] + 1) & 0x7F

    def spawn(self):
        """generateNextPill (+ sendPill's toField): colours via gen_next, X/Y/rot reset."""
        r, m = self.r, self.m
        self.gen_next()
        if not self.in_round_start:
            self.starts.append(self.f)                     # mid-round spawn = this pill's edge
        self.in_round_start = False
        m[X2], m[Y2], m[ROT] = 3, 15, 0
        self.pills += 1; self.round_pills += 1
        if self.pills % 10 == 0:
            m[SU] = min(49, m[SU] + 1)
        m[NA] = 3                                          # sendPillFinished next frame
        if not self.fits(3, 0, 0):                         # spawn blocked -> top-out -> round over
            self.cnt["topouts"] += 1
            self.end_round()

    def end_round(self):
        self.m[MODE] = 7; self.mode_wait = self.r.randint(20, 60); self.m[NA] = 4

    def lock(self, x, row, rot):
        m, r = self.m, self.r
        ca, cb = m[CA], m[CB]
        self.locks.append((self.f, ca & 3, cb & 3, m[NA_A] & 3, m[NA_B] & 3))
        cells = [(row, x, ca), (row, x + 1, cb)] if rot % 2 == 0 else [(row - 1, x, ca), (row, x, cb)]
        for rr, cc, k in cells:
            if 0 <= rr < 16:
                m[BOARD + rr * 8 + cc] = 0x60 | k
        kill = set()
        for rr in range(16):
            for cc in range(8):
                v = self.cell(rr, cc)
                if v in (0, 0xFF):
                    continue
                for dr, dc in ((0, 1), (1, 0)):
                    run = [(rr + i * dr, cc + i * dc) for i in range(4)]
                    if all(0 <= a < 16 and 0 <= b < 8 and self.cell(a, b) not in (0, 0xFF)
                           and (self.cell(a, b) & 3) == (v & 3) for a, b in run):
                        kill.update(run)
        for a, b in kill:
            m[BOARD + a * 8 + b] = 0xFF
        if kill:
            self.cnt["clears"] += 1
        m[NA] = 1                                          # pillPlaced: clear / cascade animation window
        self.win = r.randint(2, 40) if kill else r.randint(1, 3)

    # ---- one main-loop frame
    def step(self, frame, pressed, held):
        m, r = self.m, self.r
        self.f = frame
        if m[MODE] != 4:
            self.mode_wait -= 1
            if self.mode_wait <= 0:
                m[MODE] = 4; self.round_start()
            return
        # P1 sends garbage now and then while P2 falls (released at P2's next checkAttack)
        if m[NA] == 0 and m[ATK1] == 0 and r.random() < 0.004:
            m[ATK1] = r.randint(2, 4)
        na = m[NA]
        if na == 6:                                        # sendPill: the round-start throw (2P: immediate)
            if self.throw_in > 0:
                self.throw_in -= 1
                if self.throw_in > 0:
                    return
            self.spawn(); return
        if na == 3:                                        # sendPillFinished
            m[NA] = 0; return
        if na == 1:                                        # pillPlaced window (clears / cascades / garbage fall)
            self.win -= 1
            if self.win <= 0:
                m[NA] = 2
            return
        if na == 2:                                        # checkAttack
            if m[ATK1] >= 2:
                k = m[ATK1]; m[ATK1] = 0                   # the RELEASE EDGE the DRPRESTART pipeline keys on
                cols = r.sample(range(8), k)
                for c in cols:
                    if self.empty(0, c):
                        m[BOARD + c] = 0x80 | r.randrange(3)
                for c in cols:                             # land the garbage at the end of its fall window
                    row = 0
                    while row + 1 < 16 and self.empty(row + 1, c):
                        row += 1
                    if row > 0 and self.cell(0, c) not in (0, 0xFF):
                        m[BOARD + row * 8 + c] = m[BOARD + c]; m[BOARD + c] = 0xFF
                m[NA] = 1; self.win = r.randint(15, 40); self.cnt["garbage"] += 1
            else:
                m[NA] = 5
            return
        if na == 5:                                        # incNextAction
            if self.round_pills >= 14:
                self.end_round(); return
            m[NA] = 6; self.throw_in = 0; return
        if na != 0:
            return
        # ---- action_pillFalling: checkYMove, checkXMove, checkRotate (fallingPill_*) on RAM state
        x, row, rot = m[X2], 15 - m[Y2], m[ROT]
        lower = False
        if (frame & 1) and (held & 0x0F) == DOWN_:
            lower = True
        else:
            m[SCNT] = (m[SCNT] + 1) & 0xFF
            if m[SCNT] > self.thr():
                lower = True
        if lower:
            m[SCNT] = 0
            if self.fits(x, row + 1, rot):
                row += 1; m[Y2] = 15 - row
            else:
                self.lock(x, row, rot); return
        move = False
        if pressed & (LEFT_ | RIGHT_):
            m[HV] = 0; move = True
        elif held & (LEFT_ | RIGHT_):
            m[HV] = (m[HV] + 1) & 0xFF
            if m[HV] >= 16:
                m[HV] = 10; move = True
        if move:
            if held & RIGHT_:
                if self.fits(x + 1, row, rot):
                    x += 1
                else:
                    m[HV] = 15
            if held & LEFT_:
                if self.fits(x - 1, row, rot):
                    x -= 1
                else:
                    m[HV] = 15
            m[X2] = x
        for btn, d in ((A_, -1), (B_, 1)):
            if pressed & btn:
                nr = (rot + d) & 3
                if self.fits(x, row, nr):
                    rot = nr
                elif nr % 2 == 0 and self.fits(x - 1, row, nr):
                    x -= 1; rot = nr
                m[X2], m[ROT] = x, rot

    def state(self):
        m = self.m
        return (m[MODE], m[NA], m[Y2], m[X2], m[ROT], m[SCNT], m[HV], m[PC], m[SU], hash(bytes(m[BOARD:BOARD + 128])))


FIELDS = ("mode", "nextAction", "Y", "X", "rotation", "speedCounter", "horVelocity", "pillsCounter", "speedUps", "board")


def fresh_mem(rng_seed):
    base = [0] * 0x10000
    rng = random.Random(rng_seed)
    base[MAGIC] = 0xA5; base[MODE] = 4; base[Z04] = 1; base[MATCH] = 1
    base[0x0324] = 20; base[VC] = 20; base[LVL] = 11
    for i in range(128):
        base[0x0400 + i] = 0xFF; base[0x0780 + i] = rng.randrange(9)
    base[0x0306] = 15                                      # P1 static (human seat / native AI idle): no P1 edges
    return base


def run_arm(name, frames, seed):
    flags, overlays, expect = ARMS[name]
    ir, snap = capture(flags, overlays, name)
    # ---------------- run A: driver closed loop
    base = fresh_mem(seed)
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    mem = ObservableMemory(subject=base)
    copro = Copro(random.Random(seed * 7919 + 1))
    upbuf = [0] * 132
    gos = []                                               # (frame, uploaded bytes) per GO

    def on_up(addr, value):
        upbuf[addr - 0x5200] = value

    def on_go(addr, value):
        gos.append((cur_f[0], list(upbuf)))
        return copro.on_go(addr, value)
    mem.subscribe_to_write(range(0x5200, 0x5284), on_up)
    mem.subscribe_to_write([0x5284], on_go)
    mem.subscribe_to_read(range(0x5284, 0x5289), copro.read)
    stores = []                                            # driver stores into world RAM (attribution)
    in_hook = [False]; cur_f = [0]

    def on_world_write(addr, value):
        if in_hook[0]:
            stores.append((cur_f[0], addr, value, base[addr]))
    mem.subscribe_to_write(WORLD_RAM, on_world_write)
    mpu = MPU(memory=mem)
    entry = ir["units"]["main"]["base"] + ir["units"]["main"]["labels"]["main"]
    world = World(random.Random(seed), base)

    def hook():
        mpu.sp = 0xFD
        r = 0x3000 - 1
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry; base[0x3000] = 0xEA
        k = 0
        while mpu.pc != 0x3000:
            mpu.step(); k += 1
            if k > 400000:
                raise RuntimeError(f"hook runaway pc=${mpu.pc:04X}")

    pads, statesA = [], []
    act = collections.Counter()
    prev_y = 15; prev_pc = None
    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        cur_f[0] = f
        outs = []
        armed_before = base[ARMED2]; pend_before = base[PEND2]
        for _ in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0
            in_hook[0] = True
            hook()
            in_hook[0] = False
            outs.append(base[0xF6])
        R = outs[0] & outs[1]
        held_used = base[0xF8]
        pressed = R & (R ^ held_used)
        base[0xF6] = pressed; base[0xF8] = R
        if base[PEND2] and not pend_before and armed_before:
            act["stale_armed_edges"] += 1                  # new-pill edge while the previous search is still ARMED
        pads.append((pressed, R))
        world.step(f, pressed, R)
        statesA.append(world.state())
    act.update(world.cnt)
    # ---- UPLOAD CORRECTNESS (the settle's own job): the FIRST upload after a pill's new-pill edge (level init for a
    # round-start pill, the spawn otherwise) must carry THAT pill: the capsule (cA/cB) and preview (nA/nB) colours it
    # actually had at its lock (low 2 bits; the high bits carry the seed / DRREACHTX nibbles). No upload between the
    # edge and the lock = a prestart-owned pill (GO in the garbage window, before the spawn) or a lock-while-armed pill
    # (the previous search still running) -> counted, not checked. GOs between a lock and the next edge (a stale search
    # DONE-ing in the clear window re-uploads the DEAD pill -- a pre-existing driver path, not the settle's) are counted.
    bad_up = []
    for (lf, ca, cb, na_, nb_) in world.locks:
        st = max([s_ for s_ in world.starts if s_ <= lf], default=None)
        mine = [g for g in gos if st is not None and st < g[0] <= lf]   # hooks of frame f run BEFORE its world step
        if mine:
            gf, up = mine[0]
            got = (up[128] & 3, up[129] & 3, up[130] & 3, up[131] & 3)
            if got != (ca, cb, na_, nb_):
                bad_up.append({"go_f": gf, "edge_f": st, "lock_f": lf, "uploaded": got, "pill": (ca, cb, na_, nb_)})
            act["uploads_checked"] += 1
        else:
            act["pills_without_settle_upload"] += 1
    prev = -1
    for lf, ca, cb, na_, nb_ in world.locks:
        st = min([s_ for s_ in world.starts if s_ > lf], default=10 ** 9)
        between = [g for g in gos if lf < g[0] < st]
        act["gos_between_lock_and_next_edge"] += len(between)
        # DEAD-PILL UPLOAD: a GO after this pill locked (before the next edge) that carries THIS pill's capsule and
        # preview -- the stale-DONE path re-searching a capsule that no longer exists (a DRPRESTART GO in the same
        # window carries the NEXT capsule = this pill's preview, so it is not counted unless all four colours collide).
        act["dead_pill_uploads"] += sum(1 for g in between
                                        if (g[1][128] & 3, g[1][129] & 3, g[1][130] & 3, g[1][131] & 3) == (ca, cb, na_, nb_))
    act["pills"] = world.pills; act["goes"] = copro.goes; act["stale_searches"] = copro.stale
    # ---------------- run B: the unmodified game, same world seed, the recorded pads replayed, no driver
    baseB = fresh_mem(seed)
    worldB = World(random.Random(seed), baseB)
    div = None
    for f in range(frames):
        baseB[0x43] = f & 0xFF
        pressed, R = pads[f]
        baseB[0xF6] = pressed; baseB[0xF8] = R
        worldB.step(f, pressed, R)
        sB = worldB.state()
        if sB != statesA[f]:
            diff = [(FIELDS[i], statesA[f][i], sB[i]) for i in range(len(sB)) if sB[i] != statesA[f][i]]
            near = [s for s in stores if f - 3 <= s[0] <= f]
            div = {"frame": f, "diff": diff,
                   "driver_stores_near": [(s[0], NAMES.get(s[1], f"${s[1]:04X}"), s[2], s[3]) for s in near[-6:]]}
            break
    tally = collections.Counter(NAMES.get(a, f"${a:04X}") for _, a, v, old in stores if v != old)
    return {"arm": name, "expect": expect, "frames": frames, "seed": seed, "diverged": div is not None,
            "upload_mismatches": len(bad_up), "upload_mismatch_examples": bad_up[:3],
            "first_divergence": div, "activity": dict(act),
            "driver_stores_changing_world_ram": dict(tally)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=2500)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--arm", action="append")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    arms = a.arm or list(ARMS)
    ok = True
    for name in arms:
        res = run_arm(name, a.frames, a.seed)
        act = res["activity"]
        need = ["round_starts", "garbage", "stale_armed_edges", "pills"]
        if name.startswith("couch"):
            need.append("goes")
        missing = [k for k in need if act.get(k, 0) == 0]
        nbad = res["upload_mismatches"]
        dead = act.get("dead_pill_uploads", 0)
        abort_arm = ARMS[name][1].get("DRABORTSTALE") == "1"
        if res["expect"] == "pass":
            good = (not res["diverged"]) and nbad == 0 and not missing and not (abort_arm and dead)
            verdict = ("PASS" if good else "FAIL (diverged)" if res["diverged"] else
                       f"FAIL ({nbad} wrong uploads)" if nbad else
                       f"FAIL ({dead} dead-pill uploads with DRABORTSTALE)" if (abort_arm and dead) else
                       f"FAIL (unexercised: {missing})")
        elif res["expect"] == "fail_upload":
            good = nbad > 0 and not res["diverged"]
            verdict = (f"KILLED ({nbad} wrong-pill uploads)" if good else
                       "SURVIVED -- the round-start defect is not reproduced" if not nbad else "FAIL (also diverged)")
        else:
            good = res["diverged"] and nbad == 0
            verdict = "KILLED (pin detected)" if good else (f"FAIL ({nbad} wrong uploads)" if nbad else
                                                            "SURVIVED -- the gate cannot see the shipped pin")
        ok &= good
        if a.json:
            print(json.dumps(res))
        d = res["first_divergence"]
        print(f"{name:24s} expect={res['expect']:11s} {verdict:34s} pills={act.get('pills', 0)} uploads_ok={act.get('uploads_checked', 0) - nbad} rounds={act.get('round_starts', 0)} "
              f"garbage={act.get('garbage', 0)} stale_edges={act.get('stale_armed_edges', 0)} goes={act.get('goes', 0)} "
              f"dead_pill_uploads={dead} no_settle_upload={act.get('pills_without_settle_upload', 0)} "
              f"stores_changing_world={res['driver_stores_changing_world_ram']}"
              + (f" | first divergence f={d['frame']} {d['diff'][:3]} driver stores {d['driver_stores_near']}" if d else ""))
        if res["upload_mismatch_examples"]:
            print(f"    wrong-pill uploads e.g. {res['upload_mismatch_examples'][:2]}")
    print("GRAVITY-FIDELITY GATE: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
