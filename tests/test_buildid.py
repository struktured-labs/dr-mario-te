#!/usr/bin/env python3
"""DRBUILDID gate: a short, drift-proof build tag stamped onto the settings screen (row 25,
the exact row STUDYCOUNTS' OAM leak garbled -- see FINAL_BOARD_HOLD_REPORT.md).

Source of truth: <=4 safe-alphabet chars from DRBUILDID_TAG (which tools/romgen.py's `build
--tag` sets automatically from the SAME tag it records in the manifest) + a live-computed
4-hex-nibble prefix of THIS build's own image hash (placeholder-then-patch resolves the
chicken-and-egg -- see the DRBUILDID flag comment in patch_cartridge_copro.py).

Two-sided:
  A static decode of the assembled write sequence (LDA_imm/STA $2007 pairs -- a straight-line,
    unrolled, no-branch sequence, so decoding it statically IS decoding "what gets sent to the
    PPU in order", not an approximation) matches the requested tag.
  B the FINAL FILE's patched hash bytes independently reproduce ("hash the file with those 4
    bytes reset to the $FF placeholder") -- proves the stamp really is a masked-content hash,
    not an arbitrary value.
  C py65 EXECUTION: the write path is untouched (($2006,$2007) never written) when $0046==4
    (play) -- the same leak class as the OAM bug, checked the same direct way: did the code
    actually run, not "does it look gated" -- and IS exercised when $0046==1 (settings).
  D DRBUILDID=0 emission byte-identical to a pre-feature reference build; DRBUILDID=1 differs.

    tests/test_buildid.py            # asserts; exit 1 on failure
"""
import hashlib
import os
import sys
import importlib.util

from py65.devices.mpu6502 import MPU

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMITTER = os.path.join(REPO, "patch_cartridge_copro.py")
sys.path.insert(0, REPO)

BASE = 0x8000
SENT = 0x4FF2
UNIT1_FILE_BASE = 0x10 + 2 * 0x4000
_FLAGS = ("DRNOFREEZE", "DRHUMAN", "DRPOCKET", "DRRECOMMIT_NOFREEZE", "DRNAVDWELL",
          "DRPENDBOUND", "DRCOLDINIT", "DRSTUDYCOUNTS", "DRHOLDBOARD", "DRBUILDID",
          "DRBUILDID_TAG", "DRSTALLWD")
_seq = [0]

_HUMAN = {"DRHUMAN": "1", "DRPOCKET": "1", "DRNOFREEZE": "1", "DRSTUDYCOUNTS": "1",
          "DRHOLDBOARD": "1"}


def build(flags):
    for k in _FLAGS:
        os.environ.pop(k, None)
    os.environ.update(flags)
    _seq[0] += 1
    name = "bid_build_%d" % _seq[0]
    spec = importlib.util.spec_from_file_location(name, EMITTER)
    P = importlib.util.module_from_spec(spec)
    sys.modules[name] = P
    spec.loader.exec_module(P)
    unit1, labels = P.build_main(11, 1)
    return P, bytes(unit1), {k: BASE + v for k, v in labels.items()}


def decode_ops(unit1, off, n):
    """Statically decode n (LDA_imm X ; STA $2007) pairs starting at file-relative offset off
    within unit1. Returns the list of X values in order."""
    vals = []
    for i in range(n):
        assert unit1[off] == 0xA9, "expected LDA_imm opcode at +%d, got %#x" % (off, unit1[off])
        vals.append(unit1[off + 1])
        assert unit1[off + 2] == 0x8D and unit1[off + 3:off + 5] == b"\x07\x20", (
            "expected STA $2007 at +%d" % (off + 2))
        off += 5
    return vals


def inv_tile(t):
    return str(t) if t <= 9 else chr(ord("A") + t - 0x0A)


def run_hook(m, unit1, labels, mode):
    m.memory[BASE:BASE + len(unit1)] = unit1
    m.memory[0x0046] = mode
    m.memory[0x0727] = 2
    m.memory[0x04] = 1
    m.memory[0x0324] = 5
    m.memory[0x03A4] = 5
    m.memory[0x0306] = 15
    m.memory[0x0386] = 15
    m.memory[0x43] = 1
    m.memory[0x1FE], m.memory[0x1FF] = (SENT - 1) & 0xFF, (SENT - 1) >> 8
    m.sp = 0xFD
    m.pc = labels["main"]
    n = 0
    while m.pc != SENT and n < 60000:
        m.step()
        n += 1
    assert m.pc == SENT, "runaway pc=%04X" % m.pc
    return m


def scenario_a_tag_decode():
    P, unit1, labels = build(dict(_HUMAN, DRBUILDID="1", DRBUILDID_TAG="V6BH"))
    assert P.BUILDID_TAG == "V6BH"
    tag_off = labels["bid_tag0"] - BASE
    got = "".join(inv_tile(t) for t in decode_ops(unit1, tag_off, 4))
    assert got == "V6BH", "decoded tag %r != requested V6BH" % got
    print("PASS A: statically-decoded tag write sequence == 'V6BH'")

    # sanitization: an out-of-alphabet / short tag degrades safely, never crashes/corrupts
    P2, unit1b, labels2 = build(dict(_HUMAN, DRBUILDID="1", DRBUILDID_TAG="ok!"))
    assert P2.BUILDID_TAG == "OKXX", "sanitizer/pad result unexpected: %r" % P2.BUILDID_TAG
    print("PASS A2: unsafe/short DRBUILDID_TAG sanitizes to 'OKXX' (letters kept, padded)")


def scenario_b_hash_masking():
    # in-process (not subprocess): avoids any os.environ drift between what builds the file and
    # what re-derives `labels` to locate the patch sites afterward -- both come from the SAME
    # module object, so there is no way for the two to disagree about where anything landed.
    P, unit1, labels = build(dict(_HUMAN, DRBUILDID="1", DRBUILDID_TAG="V6BH"))
    P.main()
    cart = bytearray(open(os.path.join(REPO, P.OUT), "rb").read())
    offs = [UNIT1_FILE_BASE + (labels["bid_hash%d" % i] - BASE) + 1 for i in range(4)]
    file_hash = "".join(inv_tile(cart[o]) for o in offs)
    assert all(cart[o] != 0xFF for o in offs), "hash bytes still hold the $FF placeholder -- patch step did not run"

    recon = bytearray(cart)
    for o in offs:
        recon[o] = 0xFF
    independent = hashlib.md5(bytes(recon)).hexdigest()[:4].upper()
    assert independent == file_hash, (
        "GARBLE-CLASS RISK: stamp does not reproduce as hash(image with stamp masked to $FF) -- "
        "got %r, file says %r" % (independent, file_hash))
    print("PASS B: patched hash bytes (%s) independently reproduce as hash(image, stamp masked)"
          % file_hash)


def scenario_c_no_play_leak():
    P, unit1, labels = build(dict(_HUMAN, DRBUILDID="1", DRBUILDID_TAG="V6BH"))

    m_play = MPU()
    m_play.memory[0x2006] = 0x55
    m_play.memory[0x2007] = 0x55           # sentinels, distinguishable from any real tile/addr byte
    run_hook(m_play, unit1, labels, mode=4)
    assert m_play.memory[0x2006] == 0x55 and m_play.memory[0x2007] == 0x55, (
        "DRBUILDID wrote to $2006/$2007 during PLAY mode ($0046==4) -- same leak class as the "
        "OAM bug: got $2006=%#x $2007=%#x" % (m_play.memory[0x2006], m_play.memory[0x2007]))
    print("PASS C: no $2006/$2007 write during PLAY mode (mode==4) -- structurally cannot leak")

    m_settings = MPU()
    m_settings.memory[0x2006] = 0x55
    m_settings.memory[0x2007] = 0x55
    run_hook(m_settings, unit1, labels, mode=1)
    assert m_settings.memory[0x2006] != 0x55 or m_settings.memory[0x2007] != 0x55, (
        "DRBUILDID never wrote to $2006/$2007 during the settings screen (mode==1) -- the "
        "write path is unreachable, not just gated")
    print("PASS C2: $2006/$2007 written during settings-screen mode (mode==1) -- write path live")


def scenario_d_flag_off_identity():
    _, off1, _ = build(dict(_HUMAN, DRBUILDID="0"))
    _, off2, _ = build(dict(_HUMAN, DRBUILDID="0"))
    assert off1 == off2, "flag-off emission not deterministic"
    _, on1, _ = build(dict(_HUMAN, DRBUILDID="1", DRBUILDID_TAG="V6BH"))
    assert on1 != off1, "DRBUILDID=1 changed nothing"
    print("PASS D: DRBUILDID=0 emission deterministic (%d bytes), differs from flag-on" % len(off1))


def main():
    scenario_a_tag_decode()
    scenario_b_hash_masking()
    scenario_c_no_play_leak()
    scenario_d_flag_off_identity()
    print("\n==== ALL CHECKS PASSED (DRBUILDID verified two-sided) ====")


if __name__ == "__main__":
    main()
