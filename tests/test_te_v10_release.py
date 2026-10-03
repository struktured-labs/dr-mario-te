#!/usr/bin/env python3
"""TE v10 romhacking.net release gates (build_te_v10.py, te_studyend.py, ips_patch.py, te_release_gates.py).

  A  BUILD REPRODUCES: base + committed v9 patch + DRSTUDYEND + stamp == the pinned EXPECT_MD5
  B  THE COMMITTED PATCHES ARE THE BUILD: release/drmario_te_v10.ips and .bps applied to the base by
     decoders that share no code with the encoders (tools/ipsdiff.py, tools/te_release_kit.py) give
     EXPECT_MD5; the IPS leaves the 16-byte header alone (so it also patches a NES 2.0-headered dump)
  C  DRSTUDYEND PORT == SHIPPED CART: applied to the couch control cart c960dd49 the standalone port
     reproduces the silicon-verified DRSTUDYEND cart 8c6e4196 byte for byte
  D  FREEZE SIGNATURES, TWO-SIDED: v10 passes every gate; the published v6 (the KIL freeze) FAILS
     them -- a gate that cannot see the defect it rules out proves nothing
  E  IPS ENCODER EDGE CASES (synthetic, no ROM needed): RLE records, the "EOF" offset 0x454F46,
     the 0xFFFF record-size split, and size changes are refused
  F  STAMP GLYPH IS ADDITIVE: adding "1" to the footer font leaves the published stamps' layouts as-is

ROM-dependent cases skip (loudly) when the untracked ROMs are absent; E and F always run.
    tests/test_te_v10_release.py     # or: python -m pytest tests/test_te_v10_release.py
"""
import hashlib
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))

import build_te_v10 as b                                   # noqa: E402
import te_release_gates as gates                           # noqa: E402
import title_screen as ts                                  # noqa: E402
from ips_patch import make_ips, EOF_OFFSET                 # noqa: E402
from ipsdiff import apply_ips                              # noqa: E402
from te_release_kit import apply_bps as kit_apply_bps      # noqa: E402
from make_bps import apply_bps                             # noqa: E402
from te_studyend import apply_studyend                     # noqa: E402

BASE = os.path.join(REPO, "drmario.nes")
EVID = os.environ.get("DRSTUDYEND_EVIDENCE", "/home/struktured/projects/dr_mario_rl/tmp/studyend_evidence/studyend_repro")
COUCH_CTRL, COUCH_FLAG = os.path.join(EVID, "control.nes"), os.path.join(EVID, "studyend.nes")
NOINTRO_HDR = bytes.fromhex("4e45531a020410085000000000000001")   # No-Intro "Dr. Mario (Japan, USA) (En).nes"

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


def test_A_build_reproduces():
    if not need(BASE, "A"):
        return
    base = open(BASE, "rb").read()
    rom, edits, stamp, v9d = b.build(base)
    b.gate(base, v9d, rom, edits, stamp)
    assert md5(rom) == b.EXPECT_MD5, f"A FAIL: build {md5(rom)} != pinned {b.EXPECT_MD5}"
    print(f"A PASS  v10 == {b.EXPECT_MD5}; {len(edits)} DRSTUDYEND edits, {len(stamp)} stamp tiles, gates green")


def test_B_committed_patches():
    if not need(BASE, "B"):
        return
    base = open(BASE, "rb").read()
    ips = open(os.path.join(REPO, "release", "drmario_te_v10.ips"), "rb").read()
    bps = open(os.path.join(REPO, "release", "drmario_te_v10.bps"), "rb").read()
    out_ips = bytes(apply_ips(bytearray(base), ips))
    assert md5(out_ips) == b.EXPECT_MD5, "B FAIL: committed IPS does not produce the pinned ROM"
    assert md5(kit_apply_bps(base, bps)) == b.EXPECT_MD5, "B FAIL: committed BPS (kit decoder)"
    assert md5(apply_bps(bps, base)) == b.EXPECT_MD5, "B FAIL: committed BPS (make_bps decoder)"
    assert ips[:5] == b"PATCH" and ips[-3:] == b"EOF"
    # records never touch the header -> the same IPS patches the No-Intro NES 2.0-headered file
    ni = NOINTRO_HDR + base[16:]
    out_ni = bytes(apply_ips(bytearray(ni), ips))
    assert out_ni[:16] == NOINTRO_HDR and out_ni[16:] == out_ips[16:], "B FAIL: IPS touched the header"
    # no record carries an unchanged byte (only the hack's own bytes are distributed)
    p, carried = 5, 0
    while ips[p:p + 3] != b"EOF":
        off = int.from_bytes(ips[p:p + 3], "big"); size = int.from_bytes(ips[p + 3:p + 5], "big"); p += 5
        if size == 0:
            n = int.from_bytes(ips[p:p + 2], "big"); p += 3
            carried += sum(1 for i in range(n) if base[off + i] == out_ips[off + i])
        else:
            carried += sum(1 for i in range(size) if base[off + i] == ips[p + i]); p += size
    assert carried == 0, f"B FAIL: {carried} unchanged base bytes carried in IPS records"
    print(f"B PASS  IPS {len(ips)} B / BPS {len(bps)} B -> {b.EXPECT_MD5}; header untouched; 0 base bytes carried")


def test_C_port_matches_shipped_cart():
    if not (need(COUCH_CTRL, "C") and need(COUCH_FLAG, "C")):
        return
    ctrl = bytearray(open(COUCH_CTRL, "rb").read())
    assert md5(ctrl) == "c960dd499e877f01c483af1347ed8df6", "C: control cart is not c960dd49"
    flag = open(COUCH_FLAG, "rb").read()
    assert md5(flag) == "8c6e419631ee80612379e8f5f0259d62", "C: flag cart is not 8c6e4196"
    apply_studyend(ctrl)
    assert bytes(ctrl) == flag, "C FAIL: port != shipped DRSTUDYEND cart"
    print("C PASS  apply_studyend(c960dd49) == 8c6e4196 byte for byte")


def test_D_freeze_gates_two_sided():
    if not need(BASE, "D"):
        return
    base = open(BASE, "rb").read()
    rom, *_ = b.build(base)
    assert not gates.kil_sites_vanilla(base, rom) and not gates.print_table_overlap(base, rom)
    assert gates.study_tail_relocated(rom)
    v6 = apply_bps(open(os.path.join(REPO, "release", "drmario_te_v6.bps"), "rb").read(), base)
    bad = gates.kil_sites_vanilla(base, v6)
    assert any("$BC26" in x for x in bad), "D FAIL: the gate cannot see the published-v6 KIL bytes"
    assert gates.print_table_overlap(base, v6), "D FAIL: the print-table walk cannot see v6's collision"
    assert not gates.study_tail_relocated(v6)
    print(f"D PASS  v10 clean; published v6 caught ({len(bad)} sites, "
          f"{len(gates.print_table_overlap(base, v6))} bytes inside print tables)")


def test_E_ips_edge_cases():
    rnd = random.Random(1)
    # RLE + literal mix
    src = bytes(rnd.randrange(256) for _ in range(4096))
    tgt = bytearray(src)
    tgt[100:140] = b"\x42" * 40                      # long run -> RLE
    tgt[200:205] = bytes(x ^ 0xFF for x in src[200:205])
    for i in range(300, 340):                        # alternating -> literal
        tgt[i] = src[i] ^ 0x5A
    ips = make_ips(src, bytes(tgt))
    assert bytes(apply_ips(bytearray(src), ips)) == bytes(tgt)
    assert b"\x00\x00\x00\x28\x42" in ips, "E FAIL: expected an RLE record for the 40-byte run"
    # a change starting exactly at the "EOF" offset must not produce a record at 0x454F46
    n = EOF_OFFSET + 64
    src = bytearray(n); tgt = bytearray(n)
    tgt[EOF_OFFSET:EOF_OFFSET + 3] = b"\x01\x02\x03"
    ips = make_ips(bytes(src), bytes(tgt))
    assert ips[5:8] != b"EOF", "E FAIL: first record starts at the EOF magic"
    assert bytes(apply_ips(bytearray(src), ips)) == bytes(tgt)
    # > 0xFFFF changed bytes in one run are split
    src = bytes(70000); tgt = bytes(rnd.randrange(1, 256) for _ in range(70000))
    ips = make_ips(src, tgt)
    assert bytes(apply_ips(bytearray(src), ips)) == tgt
    # resizing is refused, not silently mishandled
    try:
        make_ips(b"\x00" * 10, b"\x00" * 11)
        raise AssertionError("E FAIL: size change accepted")
    except ValueError:
        pass
    print("E PASS  RLE, EOF-offset guard, 0xFFFF split, size-change refusal")


def test_F_stamp_glyph_additive():
    assert ts.footer_layout("V8.00 SL") == ts.footer_layout("V10.00 SL") == (4, 112)
    assert ts.footer_layout("V7.00 STRUK LABS") == (8, 96)
    old = b.render_footer_tiles("V8.00 SL")
    assert len(old) == 4 and old != b.render_footer_tiles("V10.00 SL")
    print("F PASS  '1' glyph added; V7/V8 layouts unchanged; V10.00 SL = same 4 tiles at X=112")


if __name__ == "__main__":
    for t in (test_A_build_reproduces, test_B_committed_patches, test_C_port_matches_shipped_cart,
              test_D_freeze_gates_two_sided, test_E_ips_edge_cases, test_F_stamp_glyph_additive):
        t()
    for s in SKIPPED:
        print("SKIPPED", s)
    print("ALL PASS" + (" (with skips)" if SKIPPED else ""))
