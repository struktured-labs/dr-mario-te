#!/usr/bin/env python3
"""Differential test: tuck_cell_prep's 6502 port vs a direct python re-derivation of
cell_offsets() (land_place_at.py) + the _FLIP colour mapping (tuck_scan_v3_ref.py), across
all 4 orientations, several target/rest pairs, and both colour orderings -- confirming
LA_OFFA/LA_OFFB/LA_CA/LA_CB come out right for every combination before this gets wired
into the candidate loop.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.environ.get("DRNAV", "/home/struktured/projects/dr-mario-mods-wt/driver-nav")
sys.path.insert(0, HERE)
sys.path.insert(0, DRIVER)

from py65.devices.mpu6502 import MPU            # noqa: E402
from patch_vs_cpu import Asm6502                 # noqa: E402
import patch_vs_cpu                              # noqa: E402
patch_vs_cpu.OPS.setdefault("CLD", 0xD8)

from land_place_at import cell_offsets, LA_OFFA, LA_OFFB, LA_CA, LA_CB  # noqa: E402
from tuck_cell_prep import (                      # noqa: E402
    emit_tuck_cell_prep, TP_IDX, TP_TARGET, TP_APPROACH, TP_TRIGGER, TP_REST, TP_ORIENT,
    CANDLIST,
)

H, V, RH, RV = 0, 1, 2, 3
_FLIP = {H: 0, V: 1, RH: 1, RV: 0}
S_CA, S_CB = 0x60A0, 0x60A1   # arbitrary absolute scratch standing in for the search's
                              # real current-pill colour bytes -- only the address matters
BASE = 0x8000


def ref_prep(target, rest, orient, ca, cb):
    offa, offb = cell_offsets(target, rest, orient)
    if _FLIP[orient] == 0:
        return offa, offb, ca, cb
    return offa, offb, cb, ca


def build():
    a = Asm6502(BASE)
    emit_tuck_cell_prep(a, s_ca=S_CA, s_cb=S_CB)
    code = a.assemble()
    return code, a.labels


CODE, LABELS = build()


def run(idx, target, approach, trigger, rest, orient, ca, cb):
    mpu = MPU()
    mem = [0] * 0x10000
    mpu.memory = mem
    for i, v in enumerate(CODE):
        mem[BASE + i] = v
    base = CANDLIST + idx * 5
    mem[base + 0] = target
    mem[base + 1] = approach
    mem[base + 2] = trigger
    mem[base + 3] = rest
    mem[base + 4] = orient
    mem[TP_IDX] = idx
    mem[S_CA] = ca
    mem[S_CB] = cb
    SENT = 0x400
    mpu.sp = 0xFD
    mem[0x100 + mpu.sp] = ((SENT - 1) >> 8) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mem[0x100 + mpu.sp] = (SENT - 1) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = BASE + LABELS["tuck_cell_prep"]
    k = 0
    while mpu.pc != SENT and k < 100000:
        mpu.step()
        k += 1
    assert mpu.pc == SENT, f"tuck_cell_prep did not return (pc={mpu.pc:#06x})"
    return mem


def main():
    fails = 0
    n = 0
    cases = []
    for orient in (H, V, RH, RV):
        for target in (0, 3, 6):
            rest = 1 if orient in (V, RV) else 6   # rest must leave room for the pair
            for ca, cb in ((0, 1), (2, 0)):
                cases.append((target, 3, 12, rest, orient, ca, cb))
    for idx, (target, approach, trigger, rest, orient, ca, cb) in enumerate(cases):
        n += 1
        mem = run(idx % 14, target, approach, trigger, rest, orient, ca, cb)
        got = (mem[LA_OFFA], mem[LA_OFFB], mem[LA_CA], mem[LA_CB])
        exp = ref_prep(target, rest, orient, ca, cb)
        # also check the raw fields were reloaded correctly
        fields_ok = (mem[TP_TARGET] == target and mem[TP_APPROACH] == approach
                     and mem[TP_TRIGGER] == trigger and mem[TP_REST] == rest
                     and mem[TP_ORIENT] == orient)
        ok = got == exp and fields_ok
        tag = "H V RH RV".split()[orient]
        print(f"  [{tag} t={target} r={rest} ca={ca} cb={cb}] got={got} exp={exp} "
              f"fields_ok={fields_ok}  {'OK' if ok else 'FAIL'}")
        if not ok:
            fails += 1
    print(f"\n{'ALL PASS' if not fails else f'{fails}/{n} FAILURES'} (code={len(CODE)}B)")
    return fails == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
