#!/usr/bin/env python3
"""KILLED MUTANT for the DRRTIVEC A-clobber (v6e).

THE DEFECT: the shipped shield probed the mapped bank with `LDA $A02E` and then fell through to
`JMP $8005`. The game's NMI handler opens PHA and closes PLA, so it faithfully saved and restored
the value the shield had ALREADY destroyed -- the interrupted main-loop code resumed with a wrong
accumulator on every NMI the shield handled. It only bites when DRMMC1RST is also on, because PRG
mode 3 hard-fixes $C000-$FFFF to index 3, whose NMI vector IS the shield. That is the shipping
combination.

WHY THIS TEST AND NOT THE GATE: the 18,000-frame multi-match gate passed the defective cart with
numbers identical to the unhardened build. Match counts, round transitions and abort counts are
structurally insensitive to a corrupted register. A check that cannot fail on the defect is not a
check -- so this one reads A directly, and is required to FAIL on the shipped cart and PASS on v6e.

It executes the shield bytes lifted out of the REAL ROM images (not a transcription), on a real
6502, for both bank cases, and asserts on the accumulator.

    python3 tests/test_rtivec_aclobber.py roms/c-v8ship.nes roms/v6e.nes
"""
import sys

from py65.devices.mpu6502 import MPU

SHIELD_CPU = 0xCEEC
PROBE = 0xA02E          # RTIVEC_PROBE
MAGIC = 0x40            # RTIVEC_MAGIC -- driver bank marker
GAME_NMI = 0x8005
SENTINEL = 0x5A         # the accumulator the interrupted code owns


def shield_bytes(path, idx=3):
    """Lift the shield straight out of the cart image (16 KB bank `idx`, CPU $C000 base)."""
    rom = open(path, "rb").read()
    prg = rom[16:16 + 0x10000]
    off = idx * 0x4000 + (SHIELD_CPU - 0xC000)
    return prg[off:off + 17]


def run_shield(code, low_bank_probe_value):
    """Execute the shield with A=SENTINEL and a pushed NMI frame; return (A_at_exit, exit_kind).

    Models the hardware state at an NMI vector fetch: P and the return PC are on the stack, A is
    whatever the interrupted code held. exit_kind is 'game' if it reached the game's NMI entry,
    'absorbed' if it executed RTI.
    """
    mpu = MPU()
    for i, b in enumerate(code):
        mpu.memory[SHIELD_CPU + i] = b
    mpu.memory[PROBE] = low_bank_probe_value
    mpu.memory[GAME_NMI] = 0xEA                      # NOP: a landing pad we can detect
    mpu.a = SENTINEL
    mpu.sp = 0xFD
    # what NMI hardware pushes: PCH, PCL, P
    mpu.memory[0x0100 + 0xFD] = 0x80
    mpu.memory[0x0100 + 0xFC] = 0x00
    mpu.memory[0x0100 + 0xFB] = 0x24
    mpu.sp = 0xFA
    mpu.pc = SHIELD_CPU
    for _ in range(40):
        if mpu.pc == GAME_NMI:
            return mpu.a, "game"
        before = mpu.pc
        mpu.step()
        # RTI pulls P + PC; detect it by the stack pointer unwinding past the pushed frame
        if mpu.sp >= 0xFD and before != mpu.pc and mpu.pc != GAME_NMI:
            return mpu.a, "absorbed"
    return mpu.a, "ranaway"


def check(path, expect_preserved):
    code = shield_bytes(path)
    print(f"\n{path}\n  shield bytes: {code[:15].hex(' ')}")
    ok = True
    # case 1: BASE bank mapped (probe != MAGIC) -> shield must hand off to the game's NMI
    a, kind = run_shield(code, 0x00)
    preserved = (a == SENTINEL)
    print(f"  base-bank case : exit={kind:9s} A=${a:02X} (entered with ${SENTINEL:02X}) "
          f"-> {'PRESERVED' if preserved else 'CLOBBERED'}")
    if kind != "game":
        print(f"    !! expected to reach the game NMI entry ${GAME_NMI:04X}"); ok = False
    if preserved != expect_preserved:
        print(f"    !! expected {'PRESERVED' if expect_preserved else 'CLOBBERED'}"); ok = False
    # case 2: DRIVER bank mapped (probe == MAGIC) -> shield must absorb the NMI
    a2, kind2 = run_shield(code, MAGIC)
    preserved2 = (a2 == SENTINEL)
    print(f"  driver-bank    : exit={kind2:9s} A=${a2:02X} "
          f"-> {'PRESERVED' if preserved2 else 'CLOBBERED'}")
    if kind2 != "absorbed":
        print(f"    !! expected the overrun NMI to be absorbed by RTI"); ok = False
    if preserved2 != expect_preserved:
        print(f"    !! expected {'PRESERVED' if expect_preserved else 'CLOBBERED'}"); ok = False
    return ok


def main():
    defective, fixed = sys.argv[1], sys.argv[2]
    print("=" * 78)
    print("KILLED MUTANT: the check must FAIL on the shipped cart and PASS on v6e")
    print("=" * 78)
    print("\n--- MUTANT (shipped cart): A must be CLOBBERED, proving the check can fail ---")
    m_ok = check(defective, expect_preserved=False)
    print("\n--- FIX (v6e): A must be PRESERVED ---")
    f_ok = check(fixed, expect_preserved=True)
    print("\n" + "=" * 78)
    if m_ok and f_ok:
        print("PASS: defect reproduced on the shipped cart AND absent on v6e (both directions)")
        return 0
    print("FAIL: " + ("mutant did not show the defect; " if not m_ok else "")
          + ("v6e does not preserve A" if not f_ok else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
