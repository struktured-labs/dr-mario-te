#!/usr/bin/env python3
"""TE v9 STANDALONE: restore the FULL 2P study tail by RELOCATING it, not evacuating it.

THE PROBLEM v8.2 SOLVED THE EXPENSIVE WAY
-----------------------------------------
The 2P-study tail lived at $9FF8 / $A371 / $BE56 / $BC26. Those look like filler but are
LIVE DATA: they sit inside `RB6C2_PRINT` nametable printing tables and an `LDA $9FF8,X`
lookup, so they are read as bytecode on every draw of those screens ->
  * part3b $BE56  -> level-select junk tiles  (the "garble")
  * part3c $BC26  -> mis-parses the TITLE table -> stack corruption -> $0301 = $02 = KIL
    (hard freeze -- present in the PUBLISHED romhacking.net v6 hack too)
v8.2 fixed both by EVACUATING the tail (part1 ends RTS, the 4 sites restored to vanilla).
Correct, but it costs the 2P study: P1's preview stays at its 1P-default position (over
the RIGHT board) and P2's preview is never drawn -- the "floating/teleported capsule".

WHY WE CAN DO BETTER FOR A STANDALONE RELEASE
---------------------------------------------
FREE_SPACE_MAP.md allocation rule 4 requires space free in BOTH the standalone and the
copro cart. Only ~42 B is shared-free (max run 17 B), which is why the tail (92 B) could
not be relocated and had to be dropped.

★ That constraint does not apply to a PURE STANDALONE release. Per the same map:
    "$FB00-$FCFF -- the COPRO DRIVER blob in the copro carts. Free in the 32KB standalone ONLY."
The v8.2 footer occupies $FB40-$FB7F, leaving $FB80-$FCFF = 384 B free -- four times what
the tail needs. So the standalone can have the full 2P study AND no garble AND no KIL.

WHAT THIS BUILD DOES
--------------------
1. v8.2 exactly (vanilla tail sites + footer at $FB40/$FB60) -- keeps the garble/KIL fix.
2. Assembles parts 2+3a+3b+3c as ONE contiguous blob at $FB80. The 5-part trampoline only
   existed to fit scattered dead runs; with one run we drop the inter-part JMPs.
3. Repoints part1's final JMP from $9FF8 to $FB80.

Result: STUDY text + BOTH previews, mode-correct, with the tail nowhere near a print table.
"""
from __future__ import annotations
import sys, os, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = "/home/struktured/projects/dr-mario-mods-wt/driver-nav"
sys.path.insert(0, DRIVER)

BASE_V82 = "/home/struktured/projects/dr-mario-te-v8.2/tmp/drmario_te_v8_2.nes"
V82_MD5 = "38cc2308d3a26b95c4058090a01f9f24"

TAIL_CPU = 0xFB80                     # standalone-only free run ($FB80-$FCFF = 384 B)
STUDY_2P_Y = 0x08
P1 = 16 + (0xD2CC - 0x8000)           # part1 in the fixed bank
P1_DUP = None                         # 32KB standalone: single copy


def f(cpu: int) -> int:
    return 16 + (cpu - 0x8000)


def build_tail() -> bytes:
    """parts 2 + 3a + 3b + 3c, merged, trampoline removed.

    1P returns immediately (the game draws its own single preview); 2P/VS falls through
    and does the P1 reposition, the P2 preview, and the STUDY Y-lift."""
    body = bytes.fromhex(
        # ---- part2 body: 2P/VS preview positions -------------------------------
        "A933" "8D9402" "8D9802" "8D9C02" "8DA002"   # Y=$33 for slots 37,38,39,40
        "A938" "8D9702"                              # P1 slot37 X=$38 (above LEFT board)
        "A940" "8D9B02"                              # P1 slot38 X=$40
        # ---- part3a: P2 preview tiles + attr -----------------------------------
        "AD9A03" "0960" "8D9D02"                     # P2 slot39 tile = $60|$039A
        "AD9B03" "0970" "8DA102"                     # P2 slot40 tile = $70|$039B
        "A902" "8D9E02" "8DA202"                     # P2 attr, both halves
        # ---- part3b: P2 preview X ----------------------------------------------
        "A9B8" "8D9F02"                              # P2 slot39 X=$B8 (above RIGHT board)
        "A9C0" "8DA302"                              # P2 slot40 X=$C0
        # ---- part3c: lift STUDY clear of the "1P 2P / LEVEL" header ------------
        + "A9%02X" % STUDY_2P_Y +                    # LDA #$08
        "8D8002" "8D8402" "8D8802" "8D8C02" "8D9002" # STUDY slots 32-36 Y
        "60"                                         # RTS (2P/VS path done)
    )
    # LDY $0727 / DEY / BEQ -> the 1P RTS that follows the whole body
    head = bytes.fromhex("AC2707" "88") + bytes([0xF0, len(body)])
    blob = head + body + bytes([0x60])               # trailing RTS = the 1P landing
    assert blob[-1] == 0x60 and blob[len(head) - 1] == len(body)
    return blob


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "drmario_te_v9_standalone.nes")
    d = bytearray(open(BASE_V82, "rb").read())
    assert hashlib.md5(d).hexdigest() == V82_MD5, "base is not v8.2 38cc2308"
    assert len(d) == 65552, f"expected a 32KB-PRG standalone, got {len(d)} B"

    tail = build_tail()
    to = f(TAIL_CPU)
    print(f"tail: {len(tail)} B  ->  ${TAIL_CPU:04X} (file 0x{to:05X})")

    # --- gate 1: the destination must be untouched filler, with margin ----------
    region = bytes(d[to:to + len(tail) + 16])
    assert set(region) <= {0x00, 0xFF}, \
        f"target ${TAIL_CPU:04X} is NOT filler: {region[:16].hex()}"
    # --- gate 2: must not overlap the v8.2 footer ($FB40 routine / $FB60 data) --
    assert TAIL_CPU >= 0xFB80, "would collide with the v8.2 footer region"
    # --- gate 3: part1 must currently be the EVAC form (ends RTS) --------------
    assert bytes(d[P1 + 49:P1 + 52]) == bytes.fromhex("60FFFF"), \
        f"part1 tail is not the v8.2 evac RTS: {bytes(d[P1+49:P1+52]).hex()}"
    # --- gate 4: the 4 old tail sites must still be VANILLA (garble/KIL fix kept)
    for cpu, n, name in ((0x9FF8, 34, "part2"), (0xA371, 27, "part3a"),
                         (0xBE56, 13, "part3b"), (0xBC26, 18, "part3c")):
        reg = bytes(d[f(cpu):f(cpu) + n])
        assert set(reg) <= {0x00, 0xFF}, f"{name} site ${cpu:04X} not vanilla: {reg[:8].hex()}"

    # --- write the tail, and repoint part1 JMP ---------------------------------
    d[to:to + len(tail)] = tail
    d[P1 + 49:P1 + 52] = bytes([0x4C, TAIL_CPU & 0xFF, TAIL_CPU >> 8])   # JMP $FB80

    open(out, "wb").write(bytes(d))
    md5 = hashlib.md5(bytes(d)).hexdigest()
    print(f"wrote {out}\n  md5 {md5}  size {len(d)}")

    # --- post-conditions --------------------------------------------------------
    v = bytes(d)
    assert v[P1 + 49:P1 + 52] == bytes([0x4C, TAIL_CPU & 0xFF, TAIL_CPU >> 8])
    assert v[to:to + len(tail)] == tail
    for cpu, n in ((0x9FF8, 34), (0xA371, 27), (0xBE56, 13), (0xBC26, 18)):
        assert set(v[f(cpu):f(cpu) + n]) <= {0x00, 0xFF}, f"${cpu:04X} disturbed"
    changed = sum(1 for i in range(len(v)) if v[i] != open(BASE_V82, 'rb').read()[i])
    print(f"  bytes changed vs v8.2: {changed}  (expect {len(tail)} tail + 3 JMP = {len(tail)+3})")
    print("  gates: filler-target OK | footer-disjoint OK | vanilla print-table sites OK")


if __name__ == "__main__":
    main()
