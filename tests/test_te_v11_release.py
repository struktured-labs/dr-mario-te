#!/usr/bin/env python3
"""TE v11 romhacking.net release gates (build_te_v11.py, te_studyend.apply_studyend_1p).

  A  BUILD REPRODUCES: v10 (pinned 512b815b, v10 gates) + DRSTUDYEND 1P + stamp == the pinned v11 md5;
     the delta vs v10 is exactly the 6 1P bytes + the one changed stamp tile
  B  THE COMMITTED PATCHES ARE THE BUILD: release/drmario_te_v11.ips/.bps applied to the base by decoders
     that share no code with the encoders give the pinned md5; the IPS never touches the header (so it
     also patches a No-Intro NES 2.0-headered dump) and carries no unchanged base byte
  C  1P PATCH SHAPE: the exact 6 bytes; the start_y=None variant is the 4 board bytes only; it refuses a ROM
     without the 2P DRSTUDYEND (whose match-final branch is what makes the block 1P-only) and refuses a
     second application; static reachability: the only branch/jump into the patched block is the
     nbPlayers != 2 BNE at $959A
  D  1P GAME OVER (py65, the real playerLoses_endScreen from $958A, NMI wait stubbed = 1 frame/call):
     v10 (= stock 1P) wipes both fields and stamps GAME OVER -- the defect reproduces; v11 keeps both
     boards byte-intact. Both reach the START loop after the same 192 frames; at that point RAM differs
     ONLY in the two fields and the $00/$01 fill pointer; after START RAM is identical (stock $FE fill,
     options screen). START prompt Y: v10 $C3 (on the bottom board row), v11 $D8 (below the bottle)
  E  2P MATCH FINAL UNCHANGED (py65): v10 and v11 produce the identical write trace and RAM, with and
     without the START-prompt blink frame (the shared START loop now reads Y from the stock pair at
     $D4D2/$D4D3; its 2P entry is $D3 like $A105[2])
  F  FREEZE SIGNATURES, TWO-SIDED on v11 (KIL sites vanilla, 0 bytes in print tables, $FB80 tail);
     the published v6 still fails them
  G  FREE-SPACE NOTE: FREE_SPACE_MAP's "$A02E-$A03D" and "$A049-$A057" runs are INSIDE the 96-byte
     cutscene table at $9FF8 (LDA $9FF8,X with X = speed*32 + level); v11 writes nothing there

ROM-dependent cases skip (loudly) when the untracked base ROM is absent.
    python tests/test_te_v11_release.py     # or: python -m pytest tests/test_te_v11_release.py
"""
import hashlib
import os
import sys

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))

import build_te_v10 as b10                                 # noqa: E402
import build_te_v11 as b11                                 # noqa: E402
import te_release_gates as gates                           # noqa: E402
from ipsdiff import apply_ips                              # noqa: E402
from te_release_kit import apply_bps as kit_apply_bps      # noqa: E402
from make_bps import apply_bps                             # noqa: E402
from te_studyend import apply_studyend_1p  # noqa: E402

BASE = os.path.join(REPO, "drmario.nes")
NOINTRO_HDR = bytes.fromhex("4e45531a020410085000000000000001")
END_SCREEN, START_LOOP, NMI_WAIT = 0x958A, 0x9607, 0xB654
ONEP_BYTES = {0x95D5: (0x94, 0xCF), 0x95D6: (0xB8, 0x96), 0x95DC: (0xD4, 0xCF), 0x95E8: (0xD4, 0xCF),
              0x9615: (0x05, 0xD1), 0x9616: (0xA1, 0xD4)}
SKIPPED = []


def md5(x):
    return hashlib.md5(x).hexdigest()


def need(path, why):
    if not os.path.exists(path):
        SKIPPED.append(f"{why}: {path} absent (untracked)")
        try:
            import pytest
            pytest.skip(f"{path} absent")
        except ImportError:
            pass
        return False
    return True


_CACHE = {}


def roms():
    if "r" not in _CACHE:
        base = open(BASE, "rb").read()
        v11, v10, v9d, e2, e1, s10, s11 = b11.build(base)
        _CACHE["r"] = (base, v11, v10, e1, s11)
    return _CACHE["r"]


def test_A_build_reproduces():
    if not need(BASE, "A"):
        return
    base, v11, v10, e1, s11 = roms()
    assert md5(v10) == b10.EXPECT_MD5
    b11.gate(base, v10, v11, e1, s11)
    assert md5(v11) == b11.EXPECT_MD5, f"A FAIL: build {md5(v11)} != pinned {b11.EXPECT_MD5}"
    delta = sorted(i for i in range(len(v11)) if v11[i] != v10[i])
    cpu = {0x8000 + i - 0x10: (v10[i], v11[i]) for i in delta if i < 0x8010}
    assert cpu == ONEP_BYTES, f"A FAIL: PRG delta vs v10 {cpu}"
    chr_delta = [i for i in delta if i >= 0x8010]
    assert chr_delta and all(s11[1] <= i < s11[1] + 16 for i in chr_delta), "A FAIL: CHR delta is not stamp tile 1"
    print(f"A PASS  v11 == {b11.EXPECT_MD5}; vs v10: 6 PRG bytes {sorted(f'${a:04X}' for a in cpu)} + "
          f"{len(chr_delta)} bytes of one stamp tile")


def test_B_committed_patches():
    if not need(BASE, "B"):
        return
    base = open(BASE, "rb").read()
    ips = open(os.path.join(REPO, "release", "drmario_te_v11.ips"), "rb").read()
    bps = open(os.path.join(REPO, "release", "drmario_te_v11.bps"), "rb").read()
    out = bytes(apply_ips(bytearray(base), ips))
    assert md5(out) == b11.EXPECT_MD5, "B FAIL: committed IPS"
    assert md5(kit_apply_bps(base, bps)) == b11.EXPECT_MD5, "B FAIL: committed BPS (kit decoder)"
    assert md5(apply_bps(bps, base)) == b11.EXPECT_MD5, "B FAIL: committed BPS (make_bps decoder)"
    assert ips[:5] == b"PATCH" and ips[-3:] == b"EOF"
    ni = bytes(apply_ips(bytearray(NOINTRO_HDR + base[16:]), ips))
    assert ni[:16] == NOINTRO_HDR and ni[16:] == out[16:], "B FAIL: IPS touched the header"
    p, carried, nrec = 5, 0, 0
    while ips[p:p + 3] != b"EOF":
        off = int.from_bytes(ips[p:p + 3], "big"); size = int.from_bytes(ips[p + 3:p + 5], "big"); p += 5
        nrec += 1
        if size == 0:
            n = int.from_bytes(ips[p:p + 2], "big"); p += 3
            carried += sum(1 for i in range(n) if base[off + i] == out[off + i])
        else:
            carried += sum(1 for i in range(size) if base[off + i] == ips[p + i]); p += size
    assert carried == 0, f"B FAIL: {carried} unchanged base bytes carried"
    print(f"B PASS  IPS {len(ips)} B ({nrec} records) / BPS {len(bps)} B -> {b11.EXPECT_MD5}; header untouched; "
          "0 base bytes carried")


def test_C_patch_shape():
    if not need(BASE, "C"):
        return
    base, v11, v10, e1, _ = roms()
    r = bytearray(v10)
    e = apply_studyend_1p(r, start_y=None)
    got = {0x8000 + o - 0x10 + i: (old[i], new[i]) for o, old, new in e for i in range(len(new)) if old[i] != new[i]}
    assert got == {k: v for k, v in ONEP_BYTES.items() if k < 0x9600}, f"C FAIL: start_y=None footprint {got}"
    for bad, what in ((bytearray(base), "stock (no 2P DRSTUDYEND)"), (bytearray(v11), "already patched")):
        try:
            apply_studyend_1p(bad)
            raise AssertionError(f"C FAIL: accepted a ROM that is {what}")
        except AssertionError as x:
            assert "C FAIL" not in str(x), str(x)
    # reachability: every JMP/JSR abs and relative branch (decoded at EVERY byte offset -- a superset)
    # whose target lands inside the patched 1P block $95C9-$9606
    prg = v11[0x10:0x8010]
    hits = []
    for i in range(len(prg) - 2):
        op, a = prg[i], 0x8000 + i
        if op in (0x4C, 0x20):
            t = prg[i + 1] | (prg[i + 2] << 8)
        elif op in (0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0):
            t = a + 2 + (prg[i + 1] - 256 if prg[i + 1] >= 128 else prg[i + 1])
        else:
            continue
        if 0x95C9 <= t <= 0x9606 and not (0x95C9 <= a <= 0x9606):
            hits.append((a, t))
    # the superset has exactly two hits: the real 1P branch, and $965C = the #$10 operand of the
    # `LDA #$10` at $965B (2P round-end loop) read as a BPL -- not an instruction
    assert hits == [(0x959A, 0x95C9), (0x965C, 0x95E3)], f"C FAIL: entries into the 1P block {hits}"
    assert prg[0x965B - 0x8000:0x965D - 0x8000] == b"\xA9\x10", "C FAIL: $965C is not an LDA #imm operand"
    assert v11[0x10 + 0x959A - 0x8000 - 5:0x10 + 0x959A - 0x8000 + 2] == bytes.fromhex("ad2707c902d02d"), \
        "C FAIL: $959A is not the nbPlayers != 2 branch"
    print("C PASS  1P footprint exact (6 B; 4 B with start_y=None); refuses stock and double application; "
          "only entry into $95C9-$9606 is BNE @$959A (nbPlayers != 2); the one other decode hit is an operand byte")


class TraceMem(list):
    def __init__(self, data):
        super().__init__(data)
        self.log = []

    def __setitem__(self, a, v):
        if isinstance(a, int):
            self.log.append((a, v))
        list.__setitem__(self, a, v)


BOARD1 = [(0x40 + i) & 0xFF for i in range(128)]
BOARD2 = [(0x90 + 3 * i) & 0x7F for i in range(128)]


def end_screen(rom, players, p1_wins, p2_wins, who_failed, clock=5, limit=3_000_000):
    """The real playerLoses_endScreen ($958A), START held, NMI wait stubbed (one call = one frame).
    clock=8 makes the START loop take its blink branch (draws the START metasprite into OAM $0200)."""
    m = MPU()
    m.memory[0x8000:0x10000] = list(rom[0x10:0x8010])
    m.memory[NMI_WAIT] = 0x60
    ram = m.memory
    ram[0x0400:0x0480] = BOARD1; ram[0x0480:0x0500] = [0xFF] * 128
    ram[0x0500:0x0580] = BOARD2; ram[0x0580:0x0600] = [0xFF] * 128
    ram[0x0727] = players; ram[0x0725] = 3; ram[0x031E] = p1_wins; ram[0x039E] = p2_wins
    ram[0x61] = who_failed; ram[0x55] = 0; ram[0x0731] = 0; ram[0x43] = clock; ram[0xF5] = 0x10
    ram[0x58] = 0x04; ram[0x80] = 0xFF; ram[0x0300] = 0xFF; ram[0x0380] = 0x0F; ram[0x42] = 0
    ram[0x00] = 0x00; ram[0x01] = 0x01
    m.memory = TraceMem(m.memory)
    m.memory[0x0700:0x0703] = [0x20, END_SCREEN & 0xFF, END_SCREEN >> 8]
    m.pc = 0x0700
    frames, at_loop = 0, None
    for _ in range(limit):
        if m.pc == NMI_WAIT:
            frames += 1
        if m.pc == START_LOOP and at_loop is None:
            at_loop = (frames, list(m.memory[0:0x800]))
        if m.pc == 0x0703:
            break
        m.step()
    assert m.pc == 0x0703, f"end screen did not return (pc=${m.pc:04X})"
    oam = list(m.memory[0x0200:0x0214])
    return at_loop, list(m.memory[0:0x800]), list(m.memory.log), oam


def ramdiff(a, b):
    return sorted(i for i in range(0x800) if a[i] != b[i] and not (0x100 <= i < 0x200))


def test_D_onep_game_over():
    if not need(BASE, "D"):
        return
    _, v11, v10, _, _ = roms()
    o_loop, o_end, o_log, _ = end_screen(v10, 1, 0, 0, 0)
    n_loop, n_end, n_log, _ = end_screen(v11, 1, 0, 0, 0)
    assert o_loop[0] == n_loop[0] == 192, f"D FAIL: frames to the START loop {o_loop[0]} / {n_loop[0]}"
    o, n = o_loop[1], n_loop[1]
    for page in (0x0400, 0x0500):                       # v10 = stock: wiped + GAME OVER box rows 2-8
        f = o[page:page + 0x80]
        assert f[:16] == [0xFF] * 16 and f[72:] == [0xFF] * 56 and f[34:38] == [0x10, 0x0A, 0x16, 0x0E], \
            f"D FAIL: v10 ${page:04X} is not wipe+GAME OVER (the defect must reproduce)"
    assert n[0x0400:0x0480] == BOARD1 and n[0x0500:0x0580] == BOARD2, "D FAIL: v11 changed a final board"
    d = ramdiff(o, n)
    assert set(d) <= set(range(0x0400, 0x0600)) | {0x00, 0x01} and any(0x400 <= x < 0x500 for x in d), \
        f"D FAIL: RAM diff at the START loop outside fields/$00-$01: {[hex(x) for x in d if not 0x400 <= x < 0x600]}"
    assert (o[0x55], o[0x61], o[0x0300], o[0x0380], o[0x80]) == (n[0x55], n[0x61], n[0x0300], n[0x0380], n[0x80]), \
        "D FAIL: whoWon/whoFailed/status differ"
    assert n_end[0x0400:0x0600] == [0xFE] * 0x200 and n_end[0x46] == 1 and n_end[0x54] == 0xFF
    assert ramdiff(o_end, n_end) == [], f"D FAIL: post-START RAM diff {[hex(x) for x in ramdiff(o_end, n_end)]}"
    nfield = sum(1 for a, _ in n_log if 0x0400 <= a < 0x0600)
    ofield = sum(1 for a, _ in o_log if 0x0400 <= a < 0x0600)
    assert nfield == 0x200, f"D FAIL: v11 wrote the fields {nfield} times (expect only the START $FE fill = 512)"
    # START prompt position (blink frame): OAM Y of the 5 letters
    _, _, _, o_oam = end_screen(v10, 1, 0, 0, 0, clock=8)
    _, _, _, n_oam = end_screen(v11, 1, 0, 0, 0, clock=8)
    oy, ny = o_oam[0::4][:5], n_oam[0::4][:5]
    assert oy == [0xC3] * 5 and ny == [0xD8] * 5, f"D FAIL: START Y v10 {oy} v11 {ny}"
    assert o_oam[3::4][:5] == n_oam[3::4][:5] == [109, 117, 125, 133, 141], "D FAIL: START X changed"
    print(f"D PASS  1P game over: both reach START after 192 frames; v10 wipes + GAME OVER ({ofield} field writes), "
          f"v11 boards intact (0 field writes before START, then the stock $FE fill); diff at the loop = fields + "
          f"$00/$01 only; identical RAM after START; START Y $C3 -> $D8")


def test_E_twop_final_unchanged():
    if not need(BASE, "E"):
        return
    _, v11, v10, _, _ = roms()
    for clock in (5, 8):
        for args in ((2, 0, 3, 1), (2, 3, 1, 2)):
            o = end_screen(v10, *args, clock=clock)
            n = end_screen(v11, *args, clock=clock)
            assert o[2] == n[2] and o[1] == n[1] and o[0] == n[0], f"E FAIL: 2P final differs (clock {clock}, {args})"
    _, _, _, oam = end_screen(v11, 2, 0, 3, 1, clock=8)
    assert oam[0::4][:5] == [0xD3] * 5, f"E FAIL: 2P START Y {oam[0::4][:5]}"
    print("E PASS  2P match final (P1 and P2 winning, blink and no-blink frame): identical write trace and RAM; START Y $D3")


def test_F_freeze_gates_two_sided():
    if not need(BASE, "F"):
        return
    base, v11, _, _, _ = roms()
    assert not gates.kil_sites_vanilla(base, v11) and not gates.print_table_overlap(base, v11)
    assert gates.study_tail_relocated(v11)
    v6 = apply_bps(open(os.path.join(REPO, "release", "drmario_te_v6.bps"), "rb").read(), base)
    assert gates.kil_sites_vanilla(base, v6) and gates.print_table_overlap(base, v6)
    print("F PASS  v11 clean on the freeze gates; published v6 still caught")


def test_G_free_space_note():
    if not need(BASE, "G"):
        return
    base, v11, _, _, _ = roms()
    prg = base[0x10:0x8010]
    readers = [0x8000 + i for i in range(len(prg) - 2) if prg[i] == 0xBD and prg[i + 1:i + 3] == b"\xF8\x9F"]
    assert len(readers) >= 4, readers
    # X = speed ($8B, 0..2) * 32 + level ($96): the table spans $9FF8-$A057, covering both "free" runs
    assert 0x9FF8 + 1 * 32 + 22 == 0xA02E and 0x9FF8 + 2 * 32 + 5 == 0xA03D and 0x9FF8 + 95 == 0xA057
    lo, hi = 0x10 + 0x9FF8 - 0x8000, 0x10 + 0xA058 - 0x8000
    assert v11[lo:hi] == base[lo:hi], "G FAIL: v11 touched the cutscene table"
    print(f"G PASS  $9FF8 cutscene table (readers {[f'${a:04X}' for a in readers]}) spans $9FF8-$A057 incl. the map's "
          "'free' $A02E-$A03D/$A049-$A057; v11 leaves it stock")


if __name__ == "__main__":
    for t in (test_A_build_reproduces, test_B_committed_patches, test_C_patch_shape, test_D_onep_game_over,
              test_E_twop_final_unchanged, test_F_freeze_gates_two_sided, test_G_free_space_note):
        t()
    for s in SKIPPED:
        print("SKIPPED", s)
    print("ALL PASS" + (" (with skips)" if SKIPPED else ""))
