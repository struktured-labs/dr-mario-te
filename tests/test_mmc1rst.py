#!/usr/bin/env python3
"""DRMMC1RST -- HAZARD 2: the MMC1 shift-register interleave that wipes RAM and latches BUSY.

MMC1 has ONE 5-bit shift register shared by all four registers, and the register a serial
sequence lands in is chosen by A14/A13 of its FIFTH write. The base game clocks a 5-write
$DFFF (CHR bank 1) sequence from the MAIN loop every frame -- $89C9 reads the frame counter,
ANDs #$08, and JSRs the $B8F4 helper (the virus blink). The copro trampoline clocks two
5-write $FFF0 (PRG bank) sequences per hook, 2 hooks per frame, ALL inside the NMI. They are
the two sides of the same frame and they share one register.

An NMI landing after k of the main loop's writes leaves k bits already shifted in, so the
trampoline's PRG sequence completes with mixed bits. In 32KB mode prgsel = {prg_bank[3:1],
A14} and cart.sv masks by ROM size (4 banks -> &3), so EVERY mid-sequence phase resolves to
PRG index 0 at $8000 = the base game. The trampoline's very next instruction is JSR $8000;
base $8000 is `LDX #$00; JMP $8036`; $8036 runs the RAM-clear loop = full wipe of $0000-$06FF.
BUSY lives at $6176 in PRG-RAM, which that loop does not touch, so BUSY stays latched at 1 and
every later hook bails forever. Title screen + dead driver = the 2026-08-09 Pocket field event.
Trace witness: prestart_gate/dbg7/interleave.log f=517 `C01 C00 C00 C00 | NMI | P02 P01 P00
P00 P00`.

This test does NOT re-implement the patch. It EXECUTES the real emitted trampoline in py65 and
feeds every write in $8000-$FFFF into a shift-register model transcribed line-for-line from
pocket-nes-mapper100/rtl/upstream/mappers/MMC1.sv:106-147 -- the same RTL mapper 100 routes to,
so the answer is identical on MiSTer and Pocket.

House rule (test the DEFECT, not the fix -- [[test-defect-not-fix]]): two-sided at every k.

  A. DEFECT REPRODUCES with DRMMC1RST=0: for k=1..4 the inbound _sel(2) completes with
     prg_bank 5/9/17/1, all of which map PRG index 0 at $8000 -- the JSR lands on the base
     game's soft-entry and wipes RAM.
  B. FIX with DRMMC1RST=1: prg_bank == 2 and $8000 == index 2 for EVERY interleave phase.
  C. THE OUTBOUND SEQUENCE TOO: at the trampoline's RTS the bank is back to 0 for every k
     (a half-applied fix that only resets the inbound sequence leaves the GAME mis-banked).
  D. THE MODE-3 SIDE EFFECT IS REAL AND BOUNDED: the reset bit forces PRG mode 3, so
     $C000-$FFFF becomes index 3 permanently. Asserted explicitly, because it is what makes
     DRRTIVEC's shield have to be bank-discriminating (see tests/test_rtivec.py scenario D).
  E. SCOPE, stated honestly rather than assumed -- and it is where the CO-DEPENDENCE bites.
     The main loop is SUSPENDED for the whole NMI, so a half-done main-thread sequence can
     only be in flight at the trampoline's ENTRY: the reset is load-bearing on the first _sel
     of the NMI and defence-in-depth on the other three. E instead checks the harder property
     at every uncommitted instant of the trampoline -- a re-entrant NMI there must not end up
     executing DRIVER-BANK code. It does not, but NOT for the reason it is tempting to assume:
     during the outbound _sel(0) the driver bank is still mapped low, and mode 3 exposes index
     3 at $C000, so what saves it is DRRTIVEC's shield, not the BUSY guard. The test proves
     this by running E on a DRMMC1RST=1 / DRRTIVEC=0 cart, where it FAILS with DRIVER_CODE at
     `$FFF0<-00`. That is the executable form of "do not land these two independently".
  F. BYTE-INERTNESS: DRMMC1RST unset == DRMMC1RST=0.

KILLED MUTANTS (a check that cannot fail is not a check):
  M1 reset immediate $80 -> $00   (bit 7 clear = not a reset at all, just another shifted bit)
  M2 `INC $FFF0` instead of LDA #$80/STA -- the tempting 3-byte version, and a trap: the reset
     only fires if the WRITTEN byte has bit 7 set and an RMW writes back what it read; the ROM
     byte at $FFF0 is $1C, so this shifts a zero/one in and makes it worse, silently.
  M3 reset placed MID-sequence -- the reset re-zeros the counter in flight, only 4 more bits
     are shifted, the register NEVER loads and the bank silently does not switch.
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
IDX = {i: 0x10 + i * BANK for i in range(4)}
WRAP_CPU = 0xFF54
PRG_REG = 0xFFF0
CHR1_REG = 0xDFFF
NBANKS = 4                                   # cart.sv:2522 masks prgsel by the ROM size


# ------------------------------------------------- MMC1.sv:106-147, transcribed
class MMC1:
    """Bit-exact model of the shared shift register and the PRG mux.

    Omits only `delay_ctrl` (MMC1.sv suppresses a write on the M2 immediately following
    another). Every sequence here is STA abs separated by LSR/LDA, so no two mapper writes
    are ever on consecutive M2 cycles and the suppressor never engages.
    """

    def __init__(self):
        self.shift = 0b10000
        self.control = 0b01100               # power-on: PRG mode 3
        self.chr0 = 0
        self.chr1 = 0
        self.prg_bank = 0b10000

    def write(self, addr, val):
        assert addr & 0x8000, f"not a mapper write: ${addr:04X}"
        if val & 0x80:                       # `if (prg_din[7])`
            self.shift = 0b10000
            self.control |= 0b01100          # <-- FORCES PRG MODE 3. MMC1.sv:110
            return
        if self.shift & 1:                   # `if (shift[0])` -- this is the 5th write
            v = ((val & 1) << 4) | (self.shift >> 1)
            reg = (addr >> 13) & 3
            (self.__setattr__)(("control", "chr0", "chr1", "prg_bank")[reg], v)
            self.shift = 0b10000
        else:
            self.shift = ((val & 1) << 4) | (self.shift >> 1)

    @property
    def prg_mode(self):
        return (self.control >> 2) & 3

    def prgsel(self, a14):
        m = self.prg_mode
        if m in (0, 1):
            sel = (((self.prg_bank >> 1) & 0b111) << 1) | a14
        elif m == 2:
            sel = self.prg_bank & 0xF if a14 else 0
        else:
            sel = 0xF if a14 else self.prg_bank & 0xF
        return sel % NBANKS                  # cart.sv ROM-size mask

    def low(self):
        return self.prgsel(0)

    def high(self):
        return self.prgsel(1)


def base_chr1_prefix(mmc1, k, value=1):
    """Clock k writes of the base game's $DFFF sequence ($B8F4), then stop -- the NMI hits here."""
    a = value
    for _ in range(k):
        mmc1.write(CHR1_REG, a)
        a >>= 1


# ------------------------------------------------- build + run the REAL trampoline
def build(name, **over):
    snap = json.load(open(os.path.join(REPO, "roms", "manifests", "v6c-distlatch.json")))
    flags = dict(snap["flag_snapshot"])
    flags.update({k: str(v) for k, v in over.items()})
    flags["DRBUILDID"] = "0"
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, f"t_mmc1_{name}.nes")
    env = {k: v for k, v in os.environ.items() if not k.startswith("DR")}
    env.update(flags)
    r = subprocess.run([sys.executable, "patch_cartridge_copro.py"], cwd=REPO, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, f"emitter failed for {name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}"
    os.replace(os.path.join(REPO, "drmario_copro.nes"), path)
    info = {}
    for line in r.stdout.splitlines():
        if line.startswith("unit-1 main:"):
            info["main"] = int(line.split("main=$")[1].strip(), 16)
        if line.startswith("trampoline:"):
            info["wrap_len"] = int(line.split()[1])
    return bytearray(open(path, "rb").read()), info


class Bus(list):
    """Flat 64K where $8000-$FFFF is ROM: stores are forwarded to the mapper, never to memory."""

    def __init__(self, data, mmc1):
        super().__init__(data)
        self.mmc1 = mmc1
        self.writes = []

    def __setitem__(self, a, v):
        if isinstance(a, int) and a >= 0x8000:
            self.writes.append((a, v))
            self.mmc1.write(a, v)
            return
        list.__setitem__(self, a, v)


def run_trampoline(rom, info, k, chr_val=1, until="jsr"):
    """Run $FF54 with the main loop k writes into its $DFFF sequence. Returns (mmc1, bus)."""
    mmc1 = MMC1()
    for v in (0x10, 0x08, 0x04, 0x02, 0x01):    # the game's reset: control <- $10 (32KB mode)
        mmc1.write(0x9FFF, v)
    for v in (0x00, 0x00, 0x00, 0x00, 0x00):    # ... and PRG bank <- 0
        mmc1.write(PRG_REG, v)
    assert mmc1.prg_mode == 0 and mmc1.low() == 0, "harness failed to reproduce the boot state"
    base_chr1_prefix(mmc1, k, chr_val)

    mem = [0] * 0x10000
    mem[0x8000:0xC000] = list(rom[IDX[0]:IDX[0] + BANK])
    mem[0xC000:0x10000] = list(rom[IDX[1]:IDX[1] + BANK])
    mem[info["main"]] = 0x60                    # stub `main` as an immediate RTS
    bus = Bus(mem, mmc1)
    mpu = MPU()
    mpu.memory = bus
    mpu.pc = WRAP_CPU
    mpu.sp = 0xFD
    bus[0x6149] = 0xA5                          # NAV_MAGIC warm -> skip the cold bootstrap
    bus[0x6176] = 0x00                          # BUSY free   -> the guard lets us in
    bus[0x6192] = 0x00                          # BUSYSKP
    end_sp = mpu.sp
    for _ in range(400):
        if until == "jsr" and mpu.pc == info["main"]:
            break
        if until == "rts" and mpu.pc == WRAP_CPU + info["wrap_len"]:
            break
        if until == "rts" and mpu.sp > end_sp:   # the trampoline's own RTS popped our frame
            break
        mpu.step()
    return mmc1, bus


# ------------------------------------------------- scenarios
PHASES = range(6)


def scen_A_defect(rom, info):
    hits = {}
    for k in PHASES:
        m, _ = run_trampoline(rom, info, k)
        hits[k] = (m.prg_bank, m.low())
    mid = {k: v for k, v in hits.items() if k in (1, 2, 3, 4)}
    assert hits[0] == (2, 2) and hits[5] == (2, 2), f"aligned phases should be clean: {hits}"
    assert all(low == 0 for _, low in mid.values()), (
        f"expected every mid-sequence phase to map the BASE game at $8000: {mid}")
    assert [pb for pb, _ in mid.values()] == [5, 9, 17, 1], f"prg_bank phases moved: {mid}"
    return ("prg_bank by phase k=0..5: " + ", ".join(f"k{k}->{pb}" for k, (pb, _) in hits.items())
            + "  |  $8000 index: " + ", ".join(f"k{k}->{lo}" for k, (_, lo) in hits.items()))


def scen_B_fix(rom, info):
    bad = {}
    for k in PHASES:
        for cv in (0, 1):
            m, _ = run_trampoline(rom, info, k, chr_val=cv)
            if (m.prg_bank, m.low()) != (2, 2):
                bad[(k, cv)] = (m.prg_bank, m.low())
    assert not bad, f"inbound _sel(2) did not self-align at: {bad}"
    return "prg_bank == 2 and $8000 == index 2 for all 6 interleave phases x both CHR values"


def scen_C_outbound(rom, info):
    bad = {}
    for k in PHASES:
        m, _ = run_trampoline(rom, info, k, until="rts")
        if (m.prg_bank, m.low()) != (0, 0):
            bad[k] = (m.prg_bank, m.low())
    assert not bad, f"outbound _sel(0) left the GAME mis-banked at: {bad}"
    return "at the trampoline RTS: prg_bank == 0 and $8000 == index 0 for all 6 phases"


def scen_D_mode3(rom, info):
    m, _ = run_trampoline(rom, info, 0)
    assert m.prg_mode == 3, (
        f"expected the reset bit to force PRG mode 3 (MMC1.sv:110), got mode {m.prg_mode}")
    m.write(PRG_REG, 0x80)
    for v in (0, 0, 0, 0, 0):
        m.write(PRG_REG, v)
    assert m.low() == 0 and m.high() == 3, (
        f"mode 3 with prg_bank 0 should map idx0/idx3, got {m.low()}/{m.high()}")
    return ("PRG mode 0 -> 3 permanently; with prg_bank=0 the BASE game now runs on "
            "idx0 low / idx3 high -- which is why DRRTIVEC's shield must discriminate")


_KIL = {0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72, 0x92, 0xB2, 0xD2, 0xF2}


def probe_nmi(rom, low_idx, high_idx):
    """Where does an NMI taken with this exact mapping end up? Classifies the three outcomes."""
    mem = [0] * 0x10000
    mem[0x8000:0xC000] = list(rom[IDX[low_idx]:IDX[low_idx] + BANK])
    mem[0xC000:0x10000] = list(rom[IDX[high_idx]:IDX[high_idx] + BANK])
    mpu = MPU()
    mpu.memory = mem
    mpu.pc = mem[0xFFFA] | (mem[0xFFFB] << 8)
    mpu.sp = 0xFD
    for _ in range(12):
        pc = mpu.pc
        if 0x8000 <= pc < 0xC000:
            return "DRIVER_CODE" if low_idx == 2 else "BASE_NMI"
        op = mem[pc]
        if op == 0x40:
            return "SHIELD_RTI"
        if op == 0x00 or op in _KIL:
            return f"BRK/KIL at ${pc:04X}"
        mpu.step()
    return "RUNAWAY"


def scen_E_scope(rom, info):
    """At EVERY instant where prg_bank has not yet committed, a re-entrant NMI must not end up
    executing DRIVER-BANK code. Two safe outcomes: the base game's own NMI (which re-enters the
    trampoline, where the BUSY guard bails it without touching the mapper), or DRRTIVEC's RTI.

    This is also the scenario that proves the CO-DEPENDENCE: it FAILS on a DRMMC1RST=1 /
    DRRTIVEC=0 cart, because mode 3 exposes index 3 at $C000 while the driver bank is still
    mapped low during the outbound _sel(0).
    """
    _, bus = run_trampoline(rom, info, 0)
    replay = MMC1()
    for v in (0x10, 0x08, 0x04, 0x02, 0x01):
        replay.write(0x9FFF, v)
    for v in (0, 0, 0, 0, 0):
        replay.write(PRG_REG, v)
    seen, bad = {}, []
    for a, v in bus.writes:
        replay.write(a, v)
        verdict = probe_nmi(rom, replay.low(), replay.high())
        seen[verdict] = seen.get(verdict, 0) + 1
        if verdict not in ("BASE_NMI", "SHIELD_RTI"):
            bad.append((f"${a:04X}<-{v:02X}", replay.low(), replay.high(), verdict))
    assert not bad, f"pre-commit instants where a re-entrant NMI is UNSAFE: {bad}"
    return f"{sum(seen.values())} instants across the whole trampoline, outcomes {seen}"


# ------------------------------------------------- mutants
def _find_reset(rom):
    """Locate the emitted `LDA #$80 / STA $FFF0` prefixes inside the trampoline (bank 1)."""
    o = 0x4010 + (WRAP_CPU - 0xC000)
    pat = bytes([0xA9, 0x80, 0x8D, PRG_REG & 0xFF, PRG_REG >> 8])
    return [i for i in range(o, o + 140) if bytes(rom[i:i + 5]) == pat]


def mut_bit7_clear(rom):
    """M1: LDA #$80 -> LDA #$00. Not a reset; just shifts another bit in."""
    for i in _find_reset(rom):
        rom[i + 1] = 0x00
    return rom


def mut_inc_rmw(rom):
    """M2: LDA #$80 / STA $FFF0  ->  INC $FFF0 / NOP / NOP (the 3-byte trap)."""
    for i in _find_reset(rom):
        rom[i:i + 5] = bytes([0xEE, PRG_REG & 0xFF, PRG_REG >> 8, 0xEA, 0xEA])
    return rom


def mut_mid_sequence(rom):
    """M3: the reset placed AFTER the first write instead of before it.

    Recon A's wrong_to_reset_sites item 2, made executable. Same 26 bytes, same instructions,
    only the order changes:  LDA #v / STA / LDA #$80 / STA(reset) / 4x (LSR / STA).  The reset
    re-zeros the counter mid-flight, so only 4 more bits are ever shifted in, shift[0] is never
    reached on write 5, and the register NEVER LOADS -- the bank silently does not switch and
    the JSR $8000 that follows runs the base game's soft entry. Strictly worse than no fix.
    """
    sites = _find_reset(rom)
    assert len(sites) == 2, f"expected two reset prefixes, found {len(sites)}"
    sta = bytes([0x8D, PRG_REG & 0xFF, PRG_REG >> 8])
    for i in sites:
        val = rom[i + 6]                       # the LDA #<value> that follows the reset prefix
        rom[i:i + 26] = (bytes([0xA9, val]) + sta            # write 1, then...
                         + bytes([0xA9, 0x80]) + sta         # ...the reset, mid-sequence
                         + (bytes([0x4A]) + sta) * 4)
    return rom


def main():
    fails = []
    print("=" * 78)
    print("DRMMC1RST -- hazard 2: MMC1 shift-register interleave -> RAM wipe + latched BUSY")
    print("=" * 78)

    off, info_off = build("off", DRRTIVEC=0, DRMMC1RST=0)
    on, info_on = build("on", DRRTIVEC=1, DRMMC1RST=1)

    print("\n-- A. the DEFECT, on a DRMMC1RST=0 cart --")
    print("   " + scen_A_defect(off, info_off))
    print("   every mid-sequence phase maps index 0 at $8000; the next instruction is JSR $8000")
    lowbank = bytes(off[IDX[0]:IDX[0] + 5])
    print(f"   base $8000 = {lowbank.hex(' ')} = LDX #$00; JMP $8036  (the RAM-clear soft entry)")

    print("\n-- B/C/D. the FIX, on a DRMMC1RST=1 cart --")
    for fn in (scen_B_fix, scen_C_outbound, scen_D_mode3, scen_E_scope):
        print(f"   {fn.__name__[5:]:9s} {fn(on, info_on)}")

    print("\n-- F. byte-inertness: unset == 0 --")
    unset, _ = build("unset")
    assert hashlib.md5(bytes(unset)).hexdigest() == hashlib.md5(bytes(off)).hexdigest(), \
        "DRMMC1RST unset differs from DRMMC1RST=0"
    print(f"   md5 {hashlib.md5(bytes(off)).hexdigest()} for both")

    print("\n-- CO-DEPENDENCE: scenario E on a DRMMC1RST=1 / DRRTIVEC=0 cart MUST fail --")
    solo, info_solo = build("mmc1only", DRRTIVEC=0, DRMMC1RST=1)
    try:
        scen_E_scope(solo, info_solo)
        fails.append("DRMMC1RST alone did not expose the unshielded-vector hazard")
        print("   NOT REPRODUCED  <-- the co-dependence claim is unsupported")
    except AssertionError as e:
        print(f"   REPRODUCED  scen_E_scope -> AssertionError: {e}")

    print("\n-- KILLED MUTANTS (each MUST make a scenario fail) --")
    for label, mut, scens in [
        ("M1 reset immediate $80 -> $00", mut_bit7_clear, [scen_B_fix]),
        ("M2 `INC $FFF0` instead of LDA #$80/STA", mut_inc_rmw, [scen_B_fix]),
        ("M3 reset placed MID-sequence instead of before it", mut_mid_sequence,
         [scen_B_fix, scen_C_outbound]),
    ]:
        m = mut(bytearray(on))
        killed = False
        for fn in scens:
            try:
                fn(m, info_on)
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
    print("test_mmc1rst: ALL PASS (defect reproduced, fix holds, 3/3 mutants killed)")


if __name__ == "__main__":
    main()
