#!/usr/bin/env python3
"""FIRMWARE TARGET GATE for DRDIST (py65): the emitted dist_6502 routine, run on the real image, writes to the LeafEval
target register $70F5 EXACTLY what the sim's rule chooses (cascade_leaf6_x.Leaf6Decider mode dist_target, vk 4, cap
16, kdig 0, via the gate reference proven equal to _vdist by dist_equiv.py): 0 with no virus or > 4 viruses, else
$80 | the smallest-D virus (ties: lowest index). Boards: every real gate-(b) game board (L11 + L15) and the couch
regression boards (9/27 lulu G1 stall, 9/27 match-1 G3, whole games), plus synthetic endgame boards (1..6 viruses,
cavities, floating viruses, walls). Each TEST-ONLY mutant must be KILLED. Also reports the routine's cycle cost.
Usage: gate_dist_fw.py [--synth N]"""
import argparse, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro")); sys.path.insert(0, os.path.join(HERE, "gate"))
from py65.devices.mpu6502 import MPU
from py65.memory import ObservableMemory
import dist_6502 as DT
from patch_vs_cpu import Asm6502
import gate as G
G.DIST_ON = True
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"


def expected(board):
    vir = [i for i in range(128) if board[i] != 0xFF and (board[i] & 0xF0) == 0xD0]
    if not vir or len(vir) > DT.VK:
        return 0
    return 0x80 | min(vir, key=lambda i: (G.dist_D(board, i), i))


class Runner:
    def __init__(self, mut="none"):
        DT._MUT = mut
        a = Asm6502(DT.DIST_ROM); DT.emit_dist(a); code = a.assemble()
        DT._MUT = "none"
        self.base = [0] * 0x10000
        self.base[DT.DIST_ROM:DT.DIST_ROM + len(code)] = list(code)
        stub = 0x0300                                   # JSR DIST_ROM ; then spin
        self.base[stub:stub + 3] = [0x20, DT.DIST_ROM & 0xFF, DT.DIST_ROM >> 8]
        self.ret = stub + 3
        self.base[self.ret] = 0xEA
        self.stub = stub
        self.mem = ObservableMemory(subject=self.base)
        self.w = []
        self.mem.subscribe_to_write([DT.LEV_TGT], lambda addr, v: self.w.append(v))
        self.mpu = MPU(memory=self.mem)

    def run(self, board):
        for i in range(128):
            self.base[DT.LIVE + i] = board[i]
        self.w.clear()
        m = self.mpu; m.pc = self.stub; m.sp = 0xFF
        start = m.processorCycles
        n = 0
        while m.pc != self.ret:
            m.step(); n += 1
            assert n < 400000, "runaway"
        return (self.w[-1] if self.w else None), len(self.w), m.processorCycles - start


def boards_real():
    out = []
    for f in ("game_l11.jsonl", "game_l15.jsonl"):
        for l in open(os.path.join(ROOT, "experiments", "reach", "corpus", f)):
            out.append(("game", json.loads(l)["nes"]))
    for f, lab in (("cases_lulu_20260927.jsonl", "lulu"), ("cases_hsv_20260927.jsonl", "hsv27"),
                   ("cases_hsv_control_20260926.jsonl", "ctl26")):
        p = os.path.join(CF, f)
        if not os.path.exists(p):
            continue
        for l in open(p):
            r = json.loads(l); S = r["S"]
            nes = []
            for i in range(128):
                c = int(S["color"][i]); v = S["virus"][i] == "1"
                nes.append(0xFF if c == 0 else ((0xD0 if v else 0x60) | (c - 1)))
            out.append(("couch_" + lab + ("_" + r.get("game_label", "").replace(" ", "") if lab == "lulu" else ""), nes))
    return out


def synth(n, rng):
    out = []
    for _ in range(n):
        b = [0xFF] * 128
        for c in range(8):
            h = rng.choice([0, 1, 3, 5, 8, 11, 13, 15])
            for r in range(16 - h, 16):
                b[r * 8 + c] = rng.choice([0x40, 0x50, 0x60, 0x70, 0x80]) | rng.randrange(3)
            if rng.random() < 0.35:
                for r in range(16):
                    if rng.random() < 0.25:
                        b[r * 8 + c] = 0xFF
        for _k in range(rng.randint(1, 6)):
            b[rng.randrange(128)] = 0xD0 | rng.randrange(3)
        out.append(("synth", b))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--synth", type=int, default=20000)
    a = ap.parse_args()
    boards = boards_real() + synth(a.synth, random.Random(20260928))
    R = Runner()
    bad = 0; nwrite_bad = 0; active = 0; cyc = {"off": [], "on": []}; kinds = {}
    for kind, b in boards:
        got, nw, c = R.run(b); exp = expected(b)
        k = kind.split("_")[0]
        kinds.setdefault(k, [0, 0, 0]); kinds[k][0] += 1
        if got != exp:
            bad += 1
            if bad <= 5:
                print("MISMATCH", kind, "got", got, "exp", exp)
        else:
            kinds[k][1] += 1
        if nw != 1:
            nwrite_bad += 1
        if exp:
            active += 1; kinds[k][2] += 1; cyc["on"].append(c)
        else:
            cyc["off"].append(c)
    for k, (n, ok, act) in kinds.items():
        print(f"{k:6s}: {ok}/{n} target == Leaf6Decider rule ({act} with a target, i.e. 1..4 viruses)")
    for t in ("off", "on"):
        v = sorted(cyc[t])
        if v:
            print(f"cycles ({t}): median {v[len(v) // 2]}  max {v[-1]}  (once per decision; 85.9 MHz -> max "
                  f"{v[-1] / 85.9e3:.3f} ms)")
    ok = bad == 0 and nwrite_bad == 0 and active > 0
    # mutants
    sample = [b for _, b in boards if 0 < sum(1 for x in b if x != 0xFF and (x & 0xF0) == 0xD0) <= 4]
    for m in ("vk5", "tie_le", "hwin", "gap", "cavity", "vbelow", "cap15"):
        Rm = Runner(m)
        diff = sum(Rm.run(b)[0] != expected(b) for _, b in boards[:3000]) + \
            sum(Rm.run(b)[0] != expected(b) for b in sample)
        print(f"mutant {m:7s}: {'KILLED' if diff else 'SURVIVED'} ({diff} boards differ)")
        ok &= diff > 0
    print(f"boards {len(boards)}, target mismatches {bad}, write-count violations {nwrite_bad}")
    print("GATE_DIST_FW", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
