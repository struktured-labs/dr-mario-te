#!/usr/bin/env python3
"""Reproducible build of Dr. Mario Training Edition v10 -- the romhacking.net STANDALONE release.

  v10 = published v9 (release/drmario_te_v9d.bps, md5 0f8f5d89)
        + DRSTUDYEND  (15 in-place bytes of stock code, te_studyend.py): on the 2-player
                       round-end and match-final screens BOTH final boards stay visible --
                       no X-sign virus, no lower-half wipe, no GAME OVER wipe -- until START
        + title stamp "V8.00 SL" -> "V10.00 SL" (4 CHR tiles; issue #12: v9 shipped "V8.00 SL")

Plain 32 KB MMC1 (mapper 1). No coprocessor, no expansion, no new code space: the release runs
on any NES / accurate emulator. The in-cart VS CPU code inherited from v6/v9 is unchanged and
this release does not advertise it.

Inputs (both pinned by md5): the clean base ROM and the committed v9 patch. Outputs:
  <rom-out>                       patched ROM (gitignored; NEVER commit or ship it)
  release/drmario_te_v10.ips      the romhacking.net deliverable (applies to the HEADERED .nes)
  release/drmario_te_v10.bps      BPS alongside (self-checking; refuses a different header)

Every build re-runs the gates and is byte-gated against EXPECT_MD5.

  usage: build_te_v10.py [--base drmario.nes] [--rom-out tmp/rel/drmario_te_v10.nes]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import title_screen as ts                                  # noqa: E402
import te_release_gates as gates                           # noqa: E402
from make_bps import make_bps, apply_bps                   # noqa: E402
from ips_patch import make_ips                             # noqa: E402
from te_studyend import apply_studyend, describe           # noqa: E402
from ipsdiff import apply_ips as independent_apply_ips     # noqa: E402  (separate reader)
from te_release_kit import apply_bps as independent_apply_bps  # noqa: E402  (separate decoder)

VERSION = "v10"
BASE_MD5 = "d3ec44424b5ac1a4dc77709829f721c9"      # Dr. Mario (Japan, USA) (Rev 0), classic iNES header
V9D_BPS = os.path.join(HERE, "release", "drmario_te_v9d.bps")
V9D_BPS_MD5 = "9adbdcc6691563e477743f67c2976a55"   # the patch published on romhacking.net (TE v9)
V9D_MD5 = "0f8f5d89dcf938144d24977d4faf2628"

STAMP_OLD, STAMP_NEW = "V8.00 SL", "V10.00 SL"
FOOTER_ROUTINE_OFF = 0x7B50                       # $FB40 (v8.2 placement, standalone-only free run)
FOOTER_DATA_OFF = 0x7B70                          # $FB60

EXPECT_MD5 = "512b815b9a2944754af3b28e9852d4ed"   # v10, headered (classic iNES header)


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def render_footer_tiles(text: str) -> list[bytes]:
    """The footer CHR tiles for `text`, exactly as title_screen.apply_training_edition_title renders them."""
    n, _ = ts.footer_layout(text)
    canvas = [[0] * (n * 8) for _ in range(8)]
    for x, y in ts._footer_pixels(text, n):
        canvas[y][x] = 2
    return [ts._encode_tile([row[i * 8:(i + 1) * 8] for row in canvas]) for i in range(n)]


def restamp(rom: bytearray, old: str, new: str) -> list[int]:
    """Swap the title version stamp in place. Only CHR changes: the new text must keep the same
    tile count and centring, so the footer routine ($FB40) and metasprite ($FB60) stay as-is."""
    (n_old, x_old), (n_new, x_new) = ts.footer_layout(old), ts.footer_layout(new)
    assert (n_old, x_old) == (n_new, x_new), f"stamp layout changes {(n_old, x_old)} -> {(n_new, x_new)}"
    routine = ts.footer_routine(FOOTER_DATA_OFF, x_old)
    assert bytes(rom[FOOTER_ROUTINE_OFF:FOOTER_ROUTINE_OFF + len(routine)]) == routine, "footer routine not at $FB40"
    meta = ts.footer_metasprite(n_old)
    assert bytes(rom[FOOTER_DATA_OFF:FOOTER_DATA_OFF + len(meta)]) == meta, "footer metasprite not at $FB60"
    assert bytes(rom[ts.FOOTER_HOOK_OFFSET:ts.FOOTER_HOOK_OFFSET + 3]) == ts.footer_hook_patched(FOOTER_ROUTINE_OFF)
    offs = []
    for i, (t_old, t_new) in enumerate(zip(render_footer_tiles(old), render_footer_tiles(new))):
        off = ts._tile_offset(ts.FOOTER_CHR_PAGE, ts.FOOTER_TILE_IDS[0] + i)
        assert bytes(rom[off:off + 16]) == t_old, f"footer tile {i} is not the '{old}' rendering"
        rom[off:off + 16] = t_new
        offs.append(off)
    return offs


def hashes(b: bytes) -> dict:
    return {"size": len(b), "crc32": f"{zlib.crc32(b):08x}", "md5": md5(b),
            "sha1": hashlib.sha1(b).hexdigest()}


def build(base: bytes) -> tuple[bytes, list, list[int], bytes]:
    assert md5(base) == BASE_MD5, f"base ROM md5 {md5(base)} is not Dr. Mario (Japan, USA) Rev 0 ({BASE_MD5})"
    v9d_patch = open(V9D_BPS, "rb").read()
    assert md5(v9d_patch) == V9D_BPS_MD5, "release/drmario_te_v9d.bps is not the published v9 patch"
    v9d = apply_bps(v9d_patch, base)
    assert md5(v9d) == V9D_MD5, f"v9 did not reproduce ({md5(v9d)})"
    rom = bytearray(v9d)
    edits = apply_studyend(rom)
    stamp_offs = restamp(rom, STAMP_OLD, STAMP_NEW)
    return bytes(rom), edits, stamp_offs, v9d


def gate(base: bytes, v9d: bytes, rom: bytes, edits, stamp_offs) -> None:
    # 1. the delta vs the published v9 is EXACTLY DRSTUDYEND + the stamp tiles
    allowed = set()
    for off, old, new in edits:
        allowed.update(off + i for i in range(len(new)) if old[i] != new[i])
    studyend_bytes = set(allowed)
    for off in stamp_offs:
        allowed.update(range(off, off + 16))
    delta = {i for i in range(len(rom)) if rom[i] != v9d[i]}
    assert len(studyend_bytes) == 15 and studyend_bytes <= delta, "DRSTUDYEND bytes missing"
    assert delta <= allowed, f"unexpected changes vs v9: {sorted(hex(i) for i in delta - allowed)[:10]}"
    # 2. DRSTUDYEND writes only over STOCK bytes (identical in base and v9) -- no TE code is touched
    for off, old, _ in edits:
        assert base[off:off + len(old)] == old, f"DRSTUDYEND site 0x{off:X} is not stock code"
    # 3. freeze signatures (dr-mario-te-freeze-rootcause / FREE_SPACE_MAP.md)
    bad = gates.kil_sites_vanilla(base, rom)
    assert not bad, "KIL/garble site regressed: " + "; ".join(bad)
    over = gates.print_table_overlap(base, rom)
    assert not over, f"changed bytes inside RB6C2_PRINT tables: {[f'${a:04X}' for a in over[:8]]}"
    assert gates.study_tail_relocated(rom), "study part1 does not jump to the relocated $FB80 tail"
    # 4. standard 32 KB MMC1 image, header untouched
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
    rom, edits, stamp_offs, v9d = build(base)
    gate(base, v9d, rom, edits, stamp_offs)
    if not a.unpinned:
        assert md5(rom) == EXPECT_MD5, f"v10 md5 {md5(rom)} != pinned {EXPECT_MD5}"

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
    print(f"  base   md5 {BASE_MD5} (Dr. Mario (Japan, USA) (Rev 0), headered)")
    print(f"  v9     md5 {V9D_MD5} (published) -> +DRSTUDYEND {describe(edits)}")
    print(f"  stamp  '{STAMP_OLD}' -> '{STAMP_NEW}' (CHR page {ts.FOOTER_CHR_PAGE} tiles "
          f"${ts.FOOTER_TILE_IDS[0]:02X}-${ts.FOOTER_TILE_IDS[0] + len(stamp_offs) - 1:02X})")
    print(f"  patched (headered)   size {h['size']} crc32 {h['crc32']} md5 {h['md5']} sha1 {h['sha1']}")
    print(f"  patched (headerless) size {hb['size']} crc32 {hb['crc32']} md5 {hb['md5']} sha1 {hb['sha1']}")
    print(f"  bytes changed vs base {sum(1 for x, y in zip(base, rom) if x != y)}, vs v9 "
          f"{sum(1 for x, y in zip(v9d, rom) if x != y)}")
    print(f"  IPS {a.ips_out} {len(ips)} B md5 {md5(ips)} (round-trip OK)")
    print(f"  BPS {a.bps_out} {len(bps)} B md5 {md5(bps)} (round-trip OK)")
    print("  gates: delta==STUDYEND+stamp, KIL sites vanilla, 0 bytes in print tables, $FB80 tail, header intact")


if __name__ == "__main__":
    main()
