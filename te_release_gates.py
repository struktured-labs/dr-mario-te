#!/usr/bin/env python3
"""Static release gates for the standalone TE ROM -- the freeze signatures, as code.

The TE study-mode KIL freeze (published v6) and the level-select garble (v8) both came from
code placed on bytes the game READS AS DATA: the RB6C2_PRINT nametable "printing programs"
($B6C2 interpreter; FREE_SPACE_MAP.md) and indexed data tables. "Filler is NOT proof of free
space." These gates turn that history into checks a build must pass:

  kil_sites_vanilla()      the six historical collision sites + the $CF00 board-init table are
                           byte-identical to the clean base ($BC26 is the KIL byte itself)
  print_table_overlap()    simulate RB6C2_PRINT over every `JSR $B6C2` table (on the base AND the
                           patched ROM) and return every changed PRG byte that the walk reads
  study_tail_relocated()   the study part-1 blob jumps to the relocated $FB80 tail, not $9FF8

The walker self-validates against the map's own control: the TITLE table walk must end at
$BD7C and must include $BC26.
"""
from __future__ import annotations

HDR = 0x10
PRG_LEN = 0x8000

# (cpu address, length, what) -- every site that has ever hosted TE bytes and turned out to be live data
KIL_SITES = [
    (0xBC26, 18, "study part3c -- TITLE print table: the published-v6 KIL freeze"),
    (0xBE56, 13, "study part3b -- SETTINGS print table: level-select garble"),
    (0x9FF8, 34, "study part2 -- read by LDA $9FF8,X"),
    (0xA01A, 62, "rest of the $9FF8 cutscene table (X = speed*32 + level; FREE_SPACE_MAP's $A02E/$A049 'free' runs)"),
    (0xA371, 27, "study part3a -- print table $A346"),
    (0xC0A9, 23, "v8 footer routine -- SETTINGS print table row 23"),
    (0xC0EF, 17, "v8 footer metasprite -- SETTINGS print table row 25"),
    (0xCF00, 128, "board-init table, LDA $CF00,X"),
]


def cpu_to_file(cpu: int) -> int:
    assert 0x8000 <= cpu <= 0xFFFF
    return HDR + (cpu - 0x8000)


def file_to_cpu(off: int) -> int | None:
    return 0x8000 + (off - HDR) if HDR <= off < HDR + PRG_LEN else None


def kil_sites_vanilla(base: bytes, rom: bytes) -> list[str]:
    """Return a list of failures (empty = pass)."""
    bad = []
    for cpu, n, what in KIL_SITES:
        o = cpu_to_file(cpu)
        if rom[o:o + n] != base[o:o + n]:
            bad.append(f"${cpu:04X}+{n} differs from base ({what})")
    return bad


def _walk(prg: bytes, start: int, touched: set[int], limit: int = 20000) -> int:
    """Simulate RB6C2_PRINT from table `start`; add every CPU address READ to `touched`.
    Returns the address of the byte that ends the whole program.
    Bytecode: chunk = {ppuHi, ppuLo, p2} + data (count = p2&$3F, repeat = p2&$40 -> 1 data byte);
    $4C = CALL (2-byte pointer, pushes), $60 = RETURN, >= $80 = end / rts."""
    def rd(a: int) -> int:
        return prg[a - 0x8000]
    stack: list[int] = []
    p, n = start, 0
    while n < limit:
        n += 1
        b = rd(p)
        touched.add(p)
        if b == 0x4C:
            touched.update((p + 1, p + 2))
            stack.append(p + 3)
            p = rd(p + 1) | (rd(p + 2) << 8)
            continue
        if b == 0x60 or b >= 0x80:
            if not stack:
                return p
            p = stack.pop()
            continue
        p2 = rd(p + 2)
        touched.update((p + 1, p + 2))
        ndata = 1 if (p2 & 0x40) else (p2 & 0x3F)
        touched.update(p + 3 + i for i in range(ndata))
        p += 3 + ndata
    raise RuntimeError(f"RB6C2_PRINT walk from ${start:04X} did not terminate")


def print_table_readset(rom: bytes) -> tuple[set[int], list[int]]:
    prg = rom[HDR:HDR + PRG_LEN]
    tables = sorted({prg[i + 3] | (prg[i + 4] << 8)
                     for i in range(len(prg) - 4) if prg[i:i + 3] == b"\x20\xC2\xB6"})
    touched: set[int] = set()
    for t in tables:
        _walk(prg, t, touched)
    # the map's own control: the TITLE program ends on the byte at $BD7C and reads the KIL byte $BC26
    title: set[int] = set()
    end = _walk(prg, 0xB91C, title)
    assert end == 0xBD7C and 0xBC26 in title, f"walker self-check failed (title end ${end:04X})"
    return touched, tables


def print_table_overlap(base: bytes, rom: bytes) -> list[int]:
    """CPU addresses of PRG bytes that differ from base AND are read by a printing table
    (read-sets walked on both images, so a patch that reroutes a table is caught too)."""
    rs_base, _ = print_table_readset(base)
    rs_rom, _ = print_table_readset(rom)
    readset = rs_base | rs_rom
    changed = [file_to_cpu(o) for o in range(HDR, HDR + PRG_LEN) if base[o] != rom[o]]
    return sorted(a for a in changed if a in readset)


def study_tail_relocated(rom: bytes) -> bool:
    blob = rom[cpu_to_file(0xD2CC):cpu_to_file(0xD2CC) + 0x34]
    return b"\x4C\x80\xFB" in blob and b"\x4C\xF8\x9F" not in blob
