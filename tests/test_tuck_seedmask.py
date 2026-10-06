#!/usr/bin/env python3
"""DRCOPRO_TUCKV3_SEEDMASK defect gate (silicon-fidelity lane, 2026-10-06): do the tie-break SEED nibbles reach the
tuck extension's placed cells?

DEFECT. The cart rides the per-match seed on the colour uploads' HIGH nibbles (S_CA = colour | seed_lo << 4, S_CB =
colour | seed_hi & $F0). tuck_v3.emit_tuck_cell_prep loads S_CA/S_CB RAW into LA_CA/LA_CB and emit_land_place_at
stores `LA | $40` into CUR, so on a seeded upload the tuck's two cells become (nibble | 4) << 4 | colour -- e.g. seed
$99 writes $D2 (a VIRUS) where the capsule half should be $42.

THE CHECK (py65, the REAL emitted routines): assemble tuck_cell_prep + land_place_at exactly as the firmware builder
emits them, plant one CANDLIST entry (horizontal and vertical, both colour orders), set S_CA/S_CB, run tuck_cell_prep
then land_place_at, and read the two CUR cells. A cell is CLEAN iff its high nibble is $4 and its low nibble is the
capsule colour.
Arms (two-sided):
  MUST SHOW THE DEFECT : SEEDMASK=0 (the shipped image) with seed nibbles != 0: dirty cells > 0.
  MUST PASS            : SEEDMASK=1 with the same seeds: dirty cells == 0; and seed 0 is clean on both arms.
  test_tuck_seedmask.py
"""
import importlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, ROOT)
from py65.devices.mpu6502 import MPU  # noqa: E402

S_CA, S_CB = 0x6124, 0x6125
ORG = 0x8000


def build(mask):
    os.environ["DRCOPRO_TUCKV3_SEEDMASK"] = "1" if mask else "0"
    sys.modules.pop("tuck_v3", None)
    TV = importlib.import_module("tuck_v3")
    from patch_vs_cpu import Asm6502
    a = Asm6502(ORG)
    a.label("entry"); a.jsr("tuck_cell_prep"); a.jsr("land_place_at"); a.label("halt"); a.jmp("halt")
    TV.emit_land_place_at(a, board=TV.CUR)
    TV.emit_tuck_cell_prep(a, s_ca=S_CA, s_cb=S_CB)
    return TV, a.assemble(), a.labels


def run(TV, code, labels, orient, seed, ca=2, cb=1):
    mem = [0] * 0x10000
    mem[ORG:ORG + len(code)] = list(code)
    for i in range(128):
        mem[TV.CUR + i] = 0xFF
    # one candidate: target col 3, approach 3, trigger row 5, rest row 9, orient (bit0 = vertical, bit1 = swap order)
    mem[TV.CANDLIST:TV.CANDLIST + 5] = [3, 3, 5, 9, orient]
    mem[TV.TP_IDX] = 0
    mem[S_CA] = (ca & 0x0F) | ((seed & 0x0F) << 4)
    mem[S_CB] = (cb & 0x0F) | (seed & 0xF0)
    mpu = MPU(); mpu.memory = mem; mpu.pc = ORG + labels["entry"]; mpu.sp = 0xFD
    halt = ORG + labels["halt"]
    for _ in range(5000):
        if mpu.pc == halt:
            break
        mpu.step()
    else:
        raise RuntimeError("routine did not return")
    cells = [mem[TV.CUR + mem[TV.Z_OFFA]], mem[TV.CUR + mem[TV.Z_OFFB]]]
    dirty = sum(1 for c in cells if (c >> 4) != 0x4 or (c & 0x0F) not in (ca, cb))
    return cells, dirty


def main():
    ok = True
    for mask in (False, True):
        TV, code, labels = build(mask)
        tot_dirty = 0; seed0_dirty = 0; ex = None
        for seed in (0x00, 0x13, 0x99, 0xD9, 0xFF, 0x5D):
            for orient in (0, 1, 2, 3):
                cells, dirty = run(TV, code, labels, orient, seed)
                if seed == 0:
                    seed0_dirty += dirty
                else:
                    tot_dirty += dirty
                    if dirty and ex is None:
                        ex = dict(seed=f"{seed:02X}", orient=orient, cells=[f"{c:02X}" for c in cells])
        arm = "SEEDMASK=1" if mask else "SEEDMASK=0 (shipped)"
        if mask:
            good = tot_dirty == 0 and seed0_dirty == 0
            verdict = "PASS" if good else f"FAIL ({tot_dirty} dirty cells)"
        else:
            good = tot_dirty > 0 and seed0_dirty == 0
            verdict = (f"DEFECT REPRODUCED ({tot_dirty}/40 seeded cells dirty)" if tot_dirty
                       else "SURVIVED -- the gate cannot see the defect")
        ok &= good
        print(f"{arm:22s} {verdict:44s} seed-0 dirty {seed0_dirty}" + (f" | e.g. {ex}" if ex else ""))
    print("TUCK SEEDMASK GATE: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
