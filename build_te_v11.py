#!/usr/bin/env python3
"""Reproducible build of Dr. Mario Training Edition v11 -- the romhacking.net STANDALONE release.

  v11 = TE v10 (build_te_v10.py, byte-gated to md5 512b815b)
        + DRSTUDYEND 1P   (6 in-place bytes, te_studyend.apply_studyend_1p): the 1-player GAME OVER
                          keeps the final board (incl. the capsule that could not spawn) on screen until
                          START -- no $FF wipe, no GAME OVER box -- and its START prompt moves below the
                          bottle; START then continues exactly as stock (options screen, high score)
        + title stamp "V10.00 SL" -> "V11.00 SL" (CHR only; 1 of the 4 footer tiles changes)

Plain 32 KB MMC1 (mapper 1). No coprocessor, no expansion, no new code space, no free space used.
The 2-player study screens (round end, match final) are v10's, unchanged.

Outputs:
  <rom-out>                       patched ROM (gitignored; NEVER commit or ship it)
  release/drmario_te_v11.ips      the romhacking.net deliverable (applies to the HEADERED .nes)
  release/drmario_te_v11.bps      BPS alongside (self-checking; refuses a different header)

Every build re-runs the v10 gates plus the v11 gates and is byte-gated against EXPECT_MD5.

  usage: build_te_v11.py [--base drmario.nes] [--rom-out tmp/rel/drmario_te_v11.nes]
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import build_te_v10 as v10                                 # noqa: E402
import te_release_gates as gates                           # noqa: E402
import title_screen as ts                                  # noqa: E402
from make_bps import make_bps, apply_bps                   # noqa: E402
from ips_patch import make_ips                             # noqa: E402
from te_studyend import apply_studyend_1p, describe, START_Y_1P   # noqa: E402
from ipsdiff import apply_ips as independent_apply_ips     # noqa: E402  (separate reader)
from te_release_kit import apply_bps as independent_apply_bps  # noqa: E402  (separate decoder)

VERSION = "v11"
STAMP_OLD, STAMP_NEW = "V10.00 SL", "V11.00 SL"
EXPECT_MD5 = "4ce1622aa27e91e54694099b6f9df163"   # v11, headered (classic iNES header)

md5, hashes = v10.md5, v10.hashes


def build(base: bytes):
    """-> (v11, v10, v9d, edits_2p, edits_1p, stamp_offs_v10, stamp_offs_v11)"""
    rom10, edits2p, stamp10, v9d = v10.build(base)
    v10.gate(base, v9d, rom10, edits2p, stamp10)
    assert md5(rom10) == v10.EXPECT_MD5, f"v10 did not reproduce ({md5(rom10)})"
    rom = bytearray(rom10)
    edits1p = apply_studyend_1p(rom)
    stamp11 = v10.restamp(rom, STAMP_OLD, STAMP_NEW)
    return bytes(rom), rom10, v9d, edits2p, edits1p, stamp10, stamp11


def changed(edits) -> set[int]:
    out = set()
    for off, old, new in edits:
        out.update(off + i for i in range(len(new)) if old[i] != new[i])
    return out


def gate(base: bytes, rom10: bytes, rom: bytes, edits1p, stamp11) -> None:
    # 1. the delta vs v10 is EXACTLY the 1P bytes + the stamp tiles
    onep = changed(edits1p)
    allowed = set(onep)
    for off in stamp11:
        allowed.update(range(off, off + 16))
    delta = {i for i in range(len(rom)) if rom[i] != rom10[i]}
    assert len(onep) == 6 and onep <= delta, "DRSTUDYEND 1P bytes missing"
    assert delta <= allowed, f"unexpected changes vs v10: {sorted(hex(i) for i in delta - allowed)[:10]}"
    # 2. every 1P write lands on STOCK code (identical in base, v9 and v10)
    for off, old, _ in edits1p:
        assert base[off:off + len(old)] == old, f"DRSTUDYEND 1P site 0x{off:X} is not stock code"
    # 3. the relocated START Y pair is stock code read as data, and its 2P entry equals stock $A105[2]
    lda = [(o, n) for o, old, n in edits1p if old == bytes.fromhex("05a1")]
    assert len(lda) == 1, "START-loop operand edit missing"
    t = lda[0][1][0] | (lda[0][1][1] << 8)
    t_off = 0x10 + t - 0x8000
    a105 = 0x10 + 0xA105 - 0x8000
    assert rom[t_off + 1:t_off + 3] == base[t_off + 1:t_off + 3], "START Y pair is not stock bytes"
    assert rom[t_off + 2] == base[a105 + 2] == 0xD3, "2P START Y would change"
    assert rom[t_off + 1] == START_Y_1P
    assert rom[a105:a105 + 3] == base[a105:a105 + 3], "$A105 table must stay stock (stage clear, 2P round end)"
    # 4. freeze signatures (dr-mario-te-freeze-rootcause / FREE_SPACE_MAP.md)
    bad = gates.kil_sites_vanilla(base, rom)
    assert not bad, "KIL/garble site regressed: " + "; ".join(bad)
    over = gates.print_table_overlap(base, rom)
    assert not over, f"changed bytes inside RB6C2_PRINT tables: {[f'${a:04X}' for a in over[:8]]}"
    assert gates.study_tail_relocated(rom), "study part1 does not jump to the relocated $FB80 tail"
    # 5. standard 32 KB MMC1 image, header untouched
    assert len(rom) == len(base) == 0x10010 and rom[:16] == base[:16], "size/header changed"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.path.join(HERE, "drmario.nes"))
    ap.add_argument("--rom-out", default=os.path.join(HERE, "tmp", "rel", f"drmario_te_{VERSION}.nes"))
    ap.add_argument("--ips-out", default=os.path.join(HERE, "release", f"drmario_te_{VERSION}.ips"))
    ap.add_argument("--bps-out", default=os.path.join(HERE, "release", f"drmario_te_{VERSION}.bps"))
    ap.add_argument("--unpinned", action="store_true", help="skip the EXPECT_MD5 byte gate (first build only)")
    a = ap.parse_args()

    base = open(a.base, "rb").read()
    rom, rom10, v9d, edits2p, edits1p, stamp10, stamp11 = build(base)
    gate(base, rom10, rom, edits1p, stamp11)
    if not a.unpinned:
        assert md5(rom) == EXPECT_MD5, f"v11 md5 {md5(rom)} != pinned {EXPECT_MD5}"

    ips = make_ips(base, rom)
    bps = make_bps(base, rom)
    # round-trips through decoders that share no code with the encoders
    assert bytes(independent_apply_ips(bytearray(base), ips)) == rom, "IPS round-trip failed"
    assert independent_apply_bps(base, bps) == rom, "BPS round-trip failed"
    assert apply_bps(bps, base) == rom

    for path, data in ((a.rom_out, rom), (a.ips_out, ips), (a.bps_out, bps)):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        open(path, "wb").write(data)

    h, hb = hashes(rom), hashes(rom[16:])
    print(f"TE {VERSION} STANDALONE -> {a.rom_out}")
    print(f"  base   md5 {v10.BASE_MD5} (Dr. Mario (Japan, USA) (Rev 0), headered)")
    print(f"  v10    md5 {v10.EXPECT_MD5} (reproduced + v10 gates) -> +DRSTUDYEND 1P {describe(edits1p)}")
    print(f"  stamp  '{STAMP_OLD}' -> '{STAMP_NEW}' (CHR page {ts.FOOTER_CHR_PAGE}, "
          f"{sum(1 for off in stamp11 if rom[off:off + 16] != rom10[off:off + 16])} of {len(stamp11)} tiles change)")
    print(f"  patched (headered)   size {h['size']} crc32 {h['crc32']} md5 {h['md5']} sha1 {h['sha1']}")
    print(f"  patched (headerless) size {hb['size']} crc32 {hb['crc32']} md5 {hb['md5']} sha1 {hb['sha1']}")
    print(f"  bytes changed vs base {sum(1 for x, y in zip(base, rom) if x != y)}, vs v10 "
          f"{sum(1 for x, y in zip(rom10, rom) if x != y)}, vs v9 {sum(1 for x, y in zip(v9d, rom) if x != y)}")
    print(f"  IPS {a.ips_out} {len(ips)} B md5 {md5(ips)} (round-trip OK)")
    print(f"  BPS {a.bps_out} {len(bps)} B md5 {md5(bps)} (round-trip OK)")
    print("  gates: v10 reproduced+gated; delta vs v10 == 1P(6)+stamp; 1P sites stock; START pair stock, 2P Y $D3; "
          "KIL sites vanilla; 0 bytes in print tables; $FB80 tail; header intact")


if __name__ == "__main__":
    main()
