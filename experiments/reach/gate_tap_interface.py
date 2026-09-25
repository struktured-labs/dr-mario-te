#!/usr/bin/env python3
"""INTERFACE-COMPLIANCE GATE for DRTAPP (owner ruling 2026-09-25: superhuman up to, never beyond, the controller).

Runs the REAL emitted P2 driver (the cart's unit-1 `main`, bytes from tools/nmi126/capture_ir.py = ground-truth
gated against the emitter) under py65, closed-loop, for thousands of frames:
  * each game frame: $43 = frame; hook pass 1 and pass 2 (the ROM's two controller reads) with the physical pad
    idle; the ROM's own getInputs semantics then apply: R = pass1 & pass2 ($F6), pressed = R & (R ^ held),
    held := R ($F8). R is the ONLY pad state the game ever sees for that frame.
  * a small ROM-rule world moves the P2 capsule from `pressed`/`held` exactly like fallingPill_checkYMove /
    checkXMove (DAS 16/6, blocked -> 15) / checkRotate, locks, clears 4-runs, spawns (x=3, row 0), speeds up every
    10 pills, and resets to fresh random boards (incl. tall-throat PROPH ledge boards and wells).
  * an emulated copro answers every GO on the P2 mailbox window: invalid ($FF) for a random delay, then a random
    target (sometimes flipping once mid-search), then DONE.
Checks on every in-game frame (the controller-interface definition: one pad state per frame, and the game's
edges are exactly the edges of that state sequence):
  C1 NO MANUFACTURED EDGE : pressed(t) == R(t) & ~R(t-1)  (for every bit)
  C2 RELEASED FRAME BETWEEN: no button has press edges on two consecutive frames
  C3 DIAL                  : successive press edges of A/B/L/R are >= P frames apart (P = DRTAPP)
Informational: hook-pass disagreements (harmless: the ROM ANDs them), frames with > 1 bit changing, press timing
(first answer-driven press after the answer is published, lateral spacing) for aligning the steering sim.
Usage: gate_tap_interface.py --cart couch|cvc --tap P [--mut everyframe] [--frames N] [--seed S]
Exit 0 iff C1-C3 hold with zero violations (and, with --mut, iff the mutant is caught: exit 0 = KILLED).
"""
import argparse, json, os, random, subprocess, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory

A_, B_, UP_, DOWN_, LEFT_, RIGHT_ = 0x80, 0x40, 0x08, 0x04, 0x02, 0x01
INTENT = A_ | B_ | LEFT_ | RIGHT_
SPEED_TABLE = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27, 0x25, 0x23,
               0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D, 0x0C, 0x0B, 0x0A, 0x09,
               0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
               0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03, 0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01,
               0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00]
SPEED_BASE = [0x0F, 0x19, 0x1F]
MAGIC, MODE, Z04, MATCH = 0x6149, 0x46, 0x04, 0x6164
P2 = dict(x=0x0385, y=0x0386, rot=0x03A5, ca=0x0381, cb=0x0382, na=0x039A, nb=0x039B, su=0x038A, sp=0x038B,
          scnt=0x0392, hv=0x0393, vc=0x03A4, pc=0x03A7, lvl=0x0396)


def capture(cart, env_extra, out):
    """Build the cart's flag snapshot (from the recorded build logs) + overlays, capture the IR in a subprocess."""
    logs = {"couch": os.path.join(ROOT, "tmp", "carts", "couch_tap2.log"),
            "cvc": os.path.join(ROOT, "tmp", "carts", "cvc_tap2.log")}
    import re
    snap = json.loads(re.search(r"##DRFLAGSNAPSHOT## (\{.*\})", open(logs[cart]).read()).group(1))
    snap.update(env_extra)
    man = out + ".manifest.json"
    json.dump({"flag_snapshot": snap}, open(man, "w"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nmi126", "capture_ir.py"), man, out],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.load(open(out)), snap


class Copro:
    def __init__(self, wbase, rng, mem_subject):
        self.w, self.rng, self.m = wbase, rng, mem_subject
        self.state = "idle"; self.done = 1; self.col = 0; self.o4 = 0xFF; self.events = []
        self.frame = 0

    def on_go(self, addr, value):
        self.state = "search"; self.done = 0; self.o4 = 0xFF; self.col = 0
        self.t_pub = self.frame + self.rng.randint(1, 16)
        self.t_flip = self.t_pub + self.rng.randint(2, 14) if self.rng.random() < 0.3 else None
        self.t_done = self.t_pub + self.rng.randint(0, 30)
        self.events.append(("go", self.frame))
        return 0

    def target(self):
        o4 = self.rng.randrange(4)
        col = self.rng.choice([0, 0, 1, 2, 5, 6, 7, 7, 3, 4])
        if o4 & 2 and col > 6:                    # copro o4 bit1 = horizontal
            col = 6
        return col, o4

    def tick(self, frame):
        self.frame = frame
        if self.state != "search":
            return
        if frame >= self.t_pub and self.o4 == 0xFF:
            self.col, self.o4 = self.target(); self.events.append(("pub", frame, self.col, self.o4))
        if self.t_flip is not None and frame >= self.t_flip:
            self.col, self.o4 = self.target(); self.t_flip = None; self.events.append(("flip", frame, self.col, self.o4))
        if frame >= self.t_done:
            if self.o4 == 0xFF:
                self.col, self.o4 = self.target()
            self.done = 1; self.state = "idle"; self.events.append(("done", frame))

    def read(self, addr):
        off = addr - self.w
        if off == 0x84:
            return self.done
        if off == 0x85:
            return self.col
        if off == 0x86:
            return self.o4
        return None


class World:
    def __init__(self, rng, mem):
        self.rng, self.m = rng, mem
        self.board = [[0] * 8 for _ in range(16)]
        self.active = False; self.spawn_in = 5; self.pills = 0; self.speed = 1; self.su = 0; self.hv = 0; self.scnt = 0
        self.x = 3; self.row = 0; self.rot = 0; self.ca = 0; self.cb = 1
        self.new_board()

    def new_board(self):
        r = self.rng; kind = r.randrange(5)
        self.board = [[0] * 8 for _ in range(16)]
        for c in range(8):
            h = r.choice([0, 1, 2, 4, 6, 8, 10, 12, 13])
            if kind == 1 and c in (3, 4):
                h = r.choice([13, 14, 15])                 # tall throat -> PROPH ledge regime
            if kind == 2 and c % 2 == 0:
                h = r.choice([10, 12, 14])                 # wells
            for row in range(16 - min(h, 15), 16):
                self.board[row][c] = 0xD0 | r.randrange(3) if row > 9 and r.random() < 0.3 else 0x60 | r.randrange(3)
        for c in (3, 4):
            self.board[0][c] = 0                            # spawn cells free
        self.speed = r.randrange(3); self.su = r.randrange(0, 30); self.pills_on_board = 0

    def thr(self):
        return SPEED_TABLE[min(80, SPEED_BASE[self.speed] + self.su)]

    def empty(self, row, c):
        return 0 <= c < 8 and 0 <= row < 16 and self.board[row][c] == 0

    def fits(self, x, row, rot):
        if row >= 16:
            return False
        if rot % 2 == 0:
            return 0 <= x <= 6 and self.empty(row, x) and self.empty(row, x + 1)
        return 0 <= x <= 7 and self.empty(row, x) and (row == 0 or self.empty(row - 1, x))

    def publish(self):
        m = self.m
        for r in range(16):
            for c in range(8):
                m[0x0500 + r * 8 + c] = 0xFF if self.board[r][c] == 0 else self.board[r][c]
        m[P2["x"]] = self.x; m[P2["y"]] = 15 - self.row; m[P2["rot"]] = self.rot
        m[P2["ca"]] = self.ca; m[P2["cb"]] = self.cb; m[P2["su"]] = self.su; m[P2["sp"]] = self.speed
        m[P2["scnt"]] = self.scnt; m[P2["hv"]] = self.hv; m[P2["pc"]] = self.pills & 0x7F

    def lock(self):
        if self.rot % 2 == 0:
            cells = [(self.row, self.x, self.ca), (self.row, self.x + 1, self.cb)]
        else:
            cells = [(self.row - 1, self.x, self.ca), (self.row, self.x, self.cb)]
        for r, c, k in cells:
            if 0 <= r < 16:
                self.board[r][c] = 0x60 | k
        # clear 4-runs (no gravity pass: enough for exercising the driver)
        kill = set()
        for r in range(16):
            for c in range(8):
                v = self.board[r][c]
                if not v:
                    continue
                for dr, dc in ((0, 1), (1, 0)):
                    run = [(r + i * dr, c + i * dc) for i in range(4)]
                    if all(0 <= rr < 16 and 0 <= cc < 8 and self.board[rr][cc] and (self.board[rr][cc] & 3) == (v & 3)
                           for rr, cc in run):
                        kill.update(run)
        for r, c in kill:
            self.board[r][c] = 0
        self.active = False; self.spawn_in = self.rng.randint(8, 28); self.pills += 1; self.pills_on_board += 1
        if self.pills % 10 == 0:
            self.su = min(49, self.su + 1)

    def step(self, frame, pressed, held):
        if not self.active:
            self.spawn_in -= 1
            if self.spawn_in <= 0:
                if not (self.empty(0, 3) and self.empty(0, 4)) or self.pills_on_board >= 30:
                    self.new_board()
                self.x, self.row, self.rot = 3, 0, 0
                self.ca, self.cb = self.m[P2["na"]] % 3, self.m[P2["nb"]] % 3
                self.m[P2["na"]], self.m[P2["nb"]] = self.rng.randrange(3), self.rng.randrange(3)
                self.active = True; self.scnt = 0; self.age = 0
            return
        self.age += 1
        # --- checkYMove
        lower = False
        if (frame & 1) and (held & 0x0F) == DOWN_:
            lower = True
        else:
            self.scnt += 1
            if self.scnt > self.thr():
                lower = True
        if lower:
            self.scnt = 0
            if self.fits(self.x, self.row + 1, self.rot):
                self.row += 1
            else:
                self.lock(); return
        # --- checkXMove
        move = False
        if pressed & (LEFT_ | RIGHT_):
            self.hv = 0; move = True
        elif held & (LEFT_ | RIGHT_):
            self.hv += 1
            if self.hv >= 16:
                self.hv = 10; move = True
        if move:
            if held & RIGHT_:
                if self.fits(self.x + 1, self.row, self.rot):
                    self.x += 1
                else:
                    self.hv = 15
            if held & LEFT_:
                if self.fits(self.x - 1, self.row, self.rot):
                    self.x -= 1
                else:
                    self.hv = 15
        # --- checkRotate
        for btn, d in ((A_, -1), (B_, 1)):
            if pressed & btn:
                nr = (self.rot + d) & 3
                if self.fits(self.x, self.row, nr):
                    self.rot = nr
                elif nr % 2 == 0 and self.fits(self.x - 1, self.row, nr):
                    self.x -= 1; self.rot = nr


def run(cart, tap, mut, frames, seed):
    tmpd = os.path.join(ROOT, "tmp", "tapgate"); os.makedirs(tmpd, exist_ok=True)
    extra = {"DRTAPP": str(tap)}
    if mut != "none":
        extra["DRTAPP_MUT"] = mut
    ir, snap = capture(cart, extra, os.path.join(tmpd, f"{cart}_p{tap}_{mut}_ir.json"))
    wbase = 0x5000 if snap.get("DRPOCKET") == "1" else 0x5200     # DRPOCKET single-window, else P2 = $5200
    rng = random.Random(seed)
    base = [0] * 0x10000
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"])
        base[u["base"]:u["base"] + len(b)] = list(b)
    mem = ObservableMemory(subject=base)
    copro = Copro(wbase, rng, base)
    mem.subscribe_to_write([wbase + 0x84], copro.on_go)
    mem.subscribe_to_read(range(wbase + 0x84, wbase + 0x87), copro.read)
    mpu = MPU(memory=mem)
    entry = ir["units"]["main"]["base"] + ir["units"]["main"]["labels"]["main"]
    # driver / game init (the task49 harness's warm state)
    base[MAGIC] = 0xA5; base[MODE] = 4; base[Z04] = 1; base[MATCH] = 1
    base[0x0324] = 20; base[P2["vc"]] = 20; base[P2["lvl"]] = 11
    for i in range(128):
        base[0x0400 + i] = 0xFF; base[0x0780 + i] = rng.randrange(9)
    world = World(rng, base)
    world.publish()

    def hook():
        SENT = 0x0400 - 0x100          # a return address inside RAM that never executes
        mpu.sp = 0xFD
        r = (0x3000 - 1)
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry
        base[0x3000] = 0xEA
        k = 0
        while mpu.pc != 0x3000:
            mpu.step(); k += 1
            if k > 400000:
                raise RuntimeError(f"hook runaway pc=${mpu.pc:04X}")

    viol = collections.Counter(); ex = {}
    prevR = 0; last_edge = {b: -99 for b in (A_, B_, LEFT_, RIGHT_)}; last_any = -99
    passdis = multibit = presses = 0
    spacing = collections.Counter()
    timing = []           # (answer-publish frame, first answer-driven press frame)
    pend_pub = None
    edges_log = []
    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        outs = []
        for p in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0            # physical pads idle (P1 human absent, P2 unplugged)
            hook(); outs.append(base[0xF6])
        R = outs[0] & outs[1]
        held_used = base[0xF8]
        pressed = R & (R ^ held_used)
        base[0xF6] = pressed; base[0xF8] = R          # the ROM's _pressedVsHeld
        passdis += int(outs[0] != outs[1])
        multibit += int(bin(R ^ prevR).count("1") > 1)
        phys = R & ~prevR & 0xFF
        if pressed != phys:
            viol["C1_manufactured_edge"] += 1; ex.setdefault("C1", (f, hex(prevR), hex(R), hex(held_used), hex(pressed)))
        for b in (A_, B_, LEFT_, RIGHT_):
            if pressed & b:
                if f - last_edge[b] == 1:
                    viol["C2_consecutive_press"] += 1; ex.setdefault("C2", (f, hex(b)))
                last_edge[b] = f
        if pressed & INTENT:
            presses += 1
            gap = f - last_any
            if gap < tap:
                viol["C3_dial_spacing"] += 1; ex.setdefault("C3", (f, gap))
            spacing[min(gap, 40)] += 1
            last_any = f
            if pend_pub is not None:
                timing.append(f - pend_pub); pend_pub = None
        if copro.events and copro.events[-1][0] == "pub" and copro.events[-1][1] == f:
            pend_pub = f
        prevR = R
        world.step(f, pressed, R)
        world.publish()
    tot = sum(viol.values())
    tl = sorted(timing)
    return {"cart": cart, "tap": tap, "mut": mut, "frames": frames, "pills": world.pills, "presses": presses,
            "violations": dict(viol), "examples": ex, "pass_disagree": passdis, "multibit_frames": multibit,
            "spacing_hist": dict(sorted(spacing.items())),
            "pub_to_first_press": {"n": len(tl), "min": tl[0] if tl else None, "median": tl[len(tl) // 2] if tl else None,
                                   "max": tl[-1] if tl else None},
            "gos": sum(1 for e in copro.events if e[0] == "go"), "ok": tot == 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cart", default="couch"); ap.add_argument("--tap", type=int, default=2)
    ap.add_argument("--mut", default="none"); ap.add_argument("--frames", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    res = run(a.cart, a.tap, a.mut, a.frames, a.seed)
    print(json.dumps(res))
    if a.mut != "none":
        print("GATE_TAP_INTERFACE mutant", a.mut, "KILLED" if not res["ok"] else "SURVIVED")
        sys.exit(0 if not res["ok"] else 1)
    print("GATE_TAP_INTERFACE", a.cart, f"P={a.tap}", "PASS" if res["ok"] else "FAIL")
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
