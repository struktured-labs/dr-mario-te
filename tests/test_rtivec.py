#!/usr/bin/env python3
"""DRRTIVEC -- HAZARD 1: the overrun NMI re-enters driver main with the BUSY guard BYPASSED.

Trace-proven 2026-08-09 by the prestart-autotest Mesen gate. An invocation that overruns the
whole frame is still running when the next vblank NMI fires; the 6502 loads PC straight from
$FFFA, and with the DRIVER unit mapped $C000-$FFFF is PRG index 3 -- expand_prg.py's verbatim
copy of the base game's vectors ($8005/$8035). $8005 in the DRIVER bank is not the game's NMI
handler, it is main's DRDISTGATE dist_table: seven 2-byte non-branching zero-page ALU ops that
fall through into main at $8013 with no control flow to escape. The BUSY guard lives in the
$FF54 trampoline and the vector executes not one byte of it, so main re-enters unguarded and
act_done's terminal RTS pops the NMI frame as an address (probe7.log: ... 8B26 -> 0BA6 = RAM).

House rule (test the DEFECT, not the fix -- [[test-defect-not-fix]]): every scenario is
two-sided. The walker EXECUTES the real emitted bytes in py65 over a flat memory assembled
from the chosen (low bank, high bank) MMC1 mapping, so it is testing the artifact.

  A. DEFECT REPRODUCES with DRRTIVEC=0: overrun NMI -> lands in the driver bank at $8005 ->
     falls through into the driver body with no RTI anywhere on the path.
  B. FIX with DRRTIVEC=1: the same overrun NMI reaches an RTI without ever entering the
     driver bank's low half.
  C. NON-OVERRUN FRAMES ARE UNTOUCHED: unit-0's vectors are byte-identical, so an ordinary
     game NMI (PRG bank 0, high half = index 1) still lands on $8005 = the base handler.
  D. CO-DEPENDENCE WITH DRMMC1RST -- the one that kills the obvious design. DRMMC1RST's $80
     write forces MMC1 PRG mode 3 (MMC1.sv:110 `control <= control | 5'b0_11_00`), which
     HARD-FIXES $C000-$FFFF to index 3 for the BASE GAME too. The shield must therefore give
     the right answer with the BASE bank mapped low, not just ours.
  E. IRQ is shielded too, and stays semantics-preserving (base $8035 is a bare RTI).
  F. BYTE-INERTNESS: DRRTIVEC unset == DRRTIVEC=0.

KILLED MUTANTS (a check that cannot fail is not a check). Each is a realistic half-applied
build of this very fix; every one must make a scenario FAIL:
  M1 probe byte forgotten   -> shield mis-reads the bank, sends the overrun NMI into main.
  M2 vectors not repointed  -> shield emitted but never reached.
  M3 "just point $FFFA at an in-bank RTI" (the literal recon design) -> D fails: under mode 3
     the base game vectors to driver-bank $A02E, which is $00 = BRK in base bank 0, and the
     BRK's own IRQ vector is the same stub. Unbreakable BRK loop on the first NMI after the
     first hook.
"""
import hashlib
import json
import os
import subprocess
import sys

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(REPO, "tmp", "hazfix")
BANK = 0x4000
IDX = {i: 0x10 + i * BANK for i in range(4)}        # PRG index -> file offset
PROBE = 0xA02E                                       # driver-bank probe byte
MAGIC = 0x40
SHIELD = 0xCEEC
RTI_AT = SHIELD + 7
V_NMI, V_RST, V_IRQ = 0x3FFA, 0x3FFC, 0x3FFE          # offsets within a 16K bank image

_KIL = {0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72, 0x92, 0xB2, 0xD2, 0xF2}


# ---------------------------------------------------------------- build helpers
def build(name, **over):
    """Build the v6c ship profile with `over` applied; cached on disk. Returns (bytes, info)."""
    snap = json.load(open(os.path.join(REPO, "roms", "manifests", "v6c-distlatch.json")))
    flags = dict(snap["flag_snapshot"])
    flags.update({k: str(v) for k, v in over.items()})
    flags["DRBUILDID"] = "0"          # default-ON stamp: hashes the FINAL image, defeats compares
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"t_rtivec_{name}.nes")
    env = {k: v for k, v in os.environ.items() if not k.startswith("DR")}
    env.update(flags)
    r = subprocess.run([sys.executable, "patch_cartridge_copro.py"], cwd=REPO, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, f"emitter failed for {name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}"
    os.replace(os.path.join(REPO, "drmario_copro.nes"), path)
    info = {}
    for line in r.stdout.splitlines():
        if line.startswith("unit-1 main:"):
            info["body_len"] = int(line.split()[2])
    return bytearray(open(path, "rb").read()), info


def flat(rom, low_idx, high_idx):
    """Flat 64K as the CPU sees it for a given MMC1 (low bank, high bank) mapping."""
    mem = [0] * 0x10000
    mem[0x8000:0xC000] = list(rom[IDX[low_idx]:IDX[low_idx] + BANK])
    mem[0xC000:0x10000] = list(rom[IDX[high_idx]:IDX[high_idx] + BANK])
    return mem


def take_interrupt(rom, low_idx, high_idx, vec=V_NMI, steps=40):
    """Execute from the vector the CPU would fetch, and report where control ends up.

    Returns (verdict, pc, trace). verdict is one of:
      LOW  -- PC entered $8000-$BFFF (the switchable half). With the DRIVER bank mapped that
              IS hazard 1; with the BASE bank mapped it is the game's own NMI.
      RTI  -- an RTI was reached first (shielded; also stack-neutral).
      BRK / KIL -- the failure shapes the half-applied mutants produce.
    """
    mem = flat(rom, low_idx, high_idx)
    target = mem[0xC000 + vec] | (mem[0xC000 + vec + 1] << 8)
    mpu = MPU()
    mpu.memory = mem
    mpu.pc = target
    mpu.sp = 0xFD                       # a plausible mid-frame stack
    trace = []
    for _ in range(steps):
        pc = mpu.pc
        trace.append(pc)
        if 0x8000 <= pc < 0xC000:
            return "LOW", pc, trace
        op = mem[pc]
        if op == 0x40:
            return "RTI", pc, trace
        if op == 0x00:
            return "BRK", pc, trace
        if op in _KIL:
            return "KIL", pc, trace
        mpu.step()
    return "RUN", mpu.pc, trace


def walk_low(rom, low_idx, start, steps=24):
    """Straight-line execution INSIDE the switchable half -- used to show the fall-through."""
    mem = flat(rom, low_idx, 3)
    mpu = MPU()
    mpu.memory = mem
    mpu.pc = start
    mpu.sp = 0xFD
    trace, saw_rti = [], False
    for _ in range(steps):
        trace.append(mpu.pc)
        op = mem[mpu.pc]
        if op == 0x40:
            saw_rti = True
            break
        if op == 0x60 or op in _KIL:
            break
        mpu.step()
    return trace, saw_rti


def vec_of(rom, idx, which):
    o = IDX[idx] + which
    return rom[o] | (rom[o + 1] << 8)


# ---------------------------------------------------------------- scenarios
def scen_A_defect(rom, info):
    """DEFECT: unshielded overrun NMI lands in the driver bank and falls into main."""
    assert vec_of(rom, 3, V_NMI) == 0x8005, "unshielded cart should carry the base NMI vector"
    verdict, pc, _ = take_interrupt(rom, low_idx=2, high_idx=3)
    assert verdict == "LOW" and pc == 0x8005, f"expected the unguarded entry, got {verdict} ${pc:04X}"
    trace, saw_rti = walk_low(rom, 2, 0x8005)
    body_end = 0x8000 + info["body_len"]
    assert not saw_rti, "an unshielded cart must NOT have an RTI on the vector path"
    assert any(0x8013 <= p < body_end for p in trace), (
        f"expected fall-through into the driver body (>=$8013, body ends ${body_end:04X}); "
        f"trace {[hex(p) for p in trace]}")
    return f"DEFECT reproduced: $8005 -> ${trace[-1]:04X} inside the driver body, no RTI"


def scen_B_shield(rom, info):
    """FIX: the overrun NMI is absorbed without entering the driver bank's low half."""
    verdict, pc, trace = take_interrupt(rom, low_idx=2, high_idx=3)
    assert verdict == "RTI", f"overrun NMI not shielded: {verdict} at ${pc:04X} trace {[hex(p) for p in trace]}"
    assert pc == RTI_AT, f"RTI at ${pc:04X}, expected ${RTI_AT:04X}"
    assert all(p >= 0xC000 for p in trace), (
        f"shield path entered the switchable half: {[hex(p) for p in trace]}")
    return f"overrun NMI -> RTI at ${pc:04X} in {len(trace)} steps, never entered $8000-$BFFF"


def scen_C_normal(rom, info):
    """NON-OVERRUN: unit-0's vectors are untouched, so the game NMI is bit-for-bit unchanged."""
    assert vec_of(rom, 1, V_NMI) == 0x8005, "unit-0 NMI vector moved -- ordinary frames changed"
    assert vec_of(rom, 1, V_IRQ) == 0x8035, "unit-0 IRQ vector moved"
    verdict, pc, _ = take_interrupt(rom, low_idx=0, high_idx=1)
    assert verdict == "LOW" and pc == 0x8005, f"game NMI perturbed: {verdict} ${pc:04X}"
    base = bytes(flat(rom, 0, 1)[0x8005:0x800A])
    assert base == bytes([0x48, 0x8A, 0x48, 0x98, 0x48]), (
        f"$8005 is not the base NMI prologue: {base.hex()}")
    return "unit-0 vectors untouched; game NMI still enters the base handler at $8005"


def scen_D_mode3(rom, info):
    """CO-DEPENDENCE: with DRMMC1RST forcing PRG mode 3, the BASE game runs with index 3 at
    $C000. The shield must route it to the game's own NMI, not into our stub."""
    verdict, pc, trace = take_interrupt(rom, low_idx=0, high_idx=3)
    assert verdict == "LOW", (
        f"mode-3 game NMI did not reach the game handler: {verdict} at ${pc:04X} "
        f"trace {[hex(p) for p in trace]}")
    op = flat(rom, 0, 3)[pc]
    fate = ("BRK -> re-vectors through the SAME stub = unbreakable BRK loop" if op == 0x00
            else f"opcode {op:#04x}")
    assert pc == 0x8005, (
        f"mode-3 game NMI landed at ${pc:04X} in BASE bank 0, expected $8005 -- {fate}")
    return f"mode-3 game NMI: $FFFA -> ${trace[0]:04X} (shield) -> $8005, {len(trace)} steps"


def scen_E_irq(rom, info):
    """IRQ is shielded, and the base IRQ handler was a bare RTI so semantics are preserved."""
    assert flat(rom, 0, 1)[0x8035] == 0x40, "base IRQ handler is not a bare RTI"
    v, pc, _ = take_interrupt(rom, low_idx=2, high_idx=3, vec=V_IRQ)
    assert v == "RTI" and pc == RTI_AT, f"driver-unit IRQ not shielded: {v} ${pc:04X}"
    v, pc, _ = take_interrupt(rom, low_idx=0, high_idx=3, vec=V_IRQ)
    assert v == "RTI", f"mode-3 game IRQ became {v} at ${pc:04X} (base behaviour is RTI)"
    assert vec_of(rom, 3, V_RST) == 0xFF00, "RESET vector must stay $FF00 -- MMC1 boots in mode 3"
    return "IRQ shielded in unit 1 and still an RTI for the base game; RESET untouched"


# ---------------------------------------------------------------- mutants
def mut_no_probe(rom):
    """M1: vectors repointed, driver-bank probe byte never written."""
    rom[IDX[2] + (PROBE - 0x8000)] = 0x00
    return rom


def mut_no_vectors(rom):
    """M2: shield emitted, index-3 vectors left at the base values."""
    o = IDX[3] + V_NMI
    rom[o], rom[o + 1] = 0x05, 0x80
    o = IDX[3] + V_IRQ
    rom[o], rom[o + 1] = 0x35, 0x80
    return rom


def mut_literal_rti(rom):
    """M3: the LITERAL recon design -- point $FFFA straight at an in-bank RTI, no discriminator."""
    o = IDX[3] + V_NMI
    rom[o], rom[o + 1] = PROBE & 0xFF, PROBE >> 8
    o = IDX[3] + V_IRQ
    rom[o], rom[o + 1] = PROBE & 0xFF, PROBE >> 8
    return rom


def main():
    fails = []
    print("=" * 78)
    print("DRRTIVEC -- hazard 1: unguarded vector re-entry into driver main")
    print("=" * 78)

    off, info_off = build("off", DRRTIVEC=0, DRMMC1RST=0)
    on, info_on = build("on", DRRTIVEC=1, DRMMC1RST=0)
    both, info_both = build("both", DRRTIVEC=1, DRMMC1RST=1)

    print("\n-- A. the DEFECT, on a DRRTIVEC=0 cart --")
    print("   " + scen_A_defect(off, info_off))

    print("\n-- B/C/D/E. the FIX, on a DRRTIVEC=1 cart --")
    for fn in (scen_B_shield, scen_C_normal, scen_D_mode3, scen_E_irq):
        print(f"   {fn.__name__[5:]:8s} {fn(on, info_on)}")

    print("\n-- B/C/D/E again with DRMMC1RST=1 as well (the shipping combination) --")
    for fn in (scen_B_shield, scen_C_normal, scen_D_mode3, scen_E_irq):
        print(f"   {fn.__name__[5:]:8s} {fn(both, info_both)}")

    print("\n-- F. byte-inertness: unset == 0 --")
    unset, _ = build("unset")
    assert hashlib.md5(bytes(unset)).hexdigest() == hashlib.md5(bytes(off)).hexdigest(), \
        "DRRTIVEC unset differs from DRRTIVEC=0"
    print(f"   md5 {hashlib.md5(bytes(off)).hexdigest()} for both")

    print("\n-- KILLED MUTANTS (each MUST make a scenario fail) --")
    mutants = [
        ("M1 probe byte forgotten", mut_no_probe, [scen_B_shield, scen_D_mode3]),
        ("M2 vectors not repointed", mut_no_vectors, [scen_B_shield]),
        ("M3 literal in-bank RTI vector (no discriminator)", mut_literal_rti,
         [scen_D_mode3, scen_C_normal]),
    ]
    for label, mut, scens in mutants:
        m = mut(bytearray(both))
        killed = False
        for fn in scens:
            try:
                fn(m, info_both)
            except AssertionError as e:
                killed = True
                print(f"   KILLED  {label}")
                print(f"           {fn.__name__} -> AssertionError: {e}")
                break
        if not killed:
            fails.append(f"MUTANT SURVIVED: {label}")
            print(f"   SURVIVED  {label}  <-- the gate is vacuous")

    print()
    if fails:
        for f in fails:
            print("FAIL:", f)
        sys.exit(1)
    print("test_rtivec: ALL PASS (defect reproduced, fix holds, 3/3 mutants killed)")


if __name__ == "__main__":
    main()
