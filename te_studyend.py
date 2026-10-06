#!/usr/bin/env python3
"""DRSTUDYEND for the STANDALONE (no-coprocessor) Training Edition ROM.

Keep both final boards visible on the 2-player round-end screen AND on the match-final
screen: no X-sign / red-virus sprites over the loser's bottle, no wipe of the loser's
lower half, no GAME OVER wipe of both bottles on the final. The screen still waits for
START, so it becomes a study view of the deciding position.

This is a byte-for-byte port of the DRSTUDYEND block in ``patch_cartridge_copro.py``
(owner request 2026-10-03, PR #28, silicon-verified on the couch cart 8c6e4196). Every
patched byte is STOCK Dr. Mario code -- nothing here touches or depends on the
coprocessor driver, the copro mailbox, PRG-RAM, or any free space:

  $954F / $9579  JSR $96C0 -> JSR $96CF   (emptyLowerFieldOnLose_2P: jump to its own
                                           tail, so the status redraw still runs but the
                                           64 x $FF wipe of the loser's rows 8-15 does not)
  $8890          TAX -> RTS              (updateSprites_2p_endGame: whoFailed != 0 returns
                                           before drawing the X-sign / red virus)
  $95BD-$95C8    12 B                     (2P-only match-final block: same final music and
                                           the same 128-frame wait, then BEQ to the START
                                           loop -- skipping the both-field $FF fill, both
                                           GAME OVER stamps and the whoFailed/whoWon stores)

15 bytes, all in PRG bank 0 ($8000-$BFFF). The 1-player game over enters the shared code
at $95C9, after the rewritten block, and runs every stock byte. Sites are located by
content, verified unique, and their original bytes are asserted before any write, so
the function refuses a ROM it does not recognise and is idempotent-safe (a second call
fails loudly instead of double-patching).

Cross-check (tests/test_te_v10_release.py): applied to the couch control cart c960dd49
this function reproduces the shipped DRSTUDYEND cart 8c6e4196 byte for byte.
"""
from __future__ import annotations

BANK0_LO, BANK0_HI = 0x10, 0x4010   # file offsets of PRG bank 0 ($8000-$BFFF) in every TE layout


def _cpu0(off: int) -> int:
    assert BANK0_LO <= off < BANK0_HI, f"DRSTUDYEND: file offset 0x{off:X} is not in PRG bank 0"
    return 0x8000 + off - 0x10


def _unique(rom: bytes, pat: bytes, what: str, start: int = 0) -> int:
    i = rom.find(pat, start)
    assert i >= 0 and rom.find(pat, i + 1) < 0, f"DRSTUDYEND: {what} anchor not found / not unique"
    return i


def apply_studyend(rom: bytearray) -> list[tuple[int, bytes, bytes]]:
    """Patch ``rom`` (a full .nes image incl. the 16-byte header) in place.

    Returns ``[(file_offset, old_bytes, new_bytes), ...]`` -- exactly the 15 changed bytes."""
    edits: list[tuple[int, bytes, bytes]] = []

    def put(off: int, new: bytes) -> None:
        old = bytes(rom[off:off + len(new)])
        rom[off:off + len(new)] = new
        edits.append((off, old, bytes(new)))

    # 1) round end: anyPlayerLoses' two calls to emptyLowerFieldOnLose_2P -> its own tail
    el = bytes.fromhex("a9008557a040a9ff9157c8c080d0f7a90f858060")   # emptyLowerFieldOnLose_2P
    el_i = _unique(rom, el, "emptyLowerFieldOnLose_2P")
    el_cpu = _cpu0(el_i)
    tail_cpu = el_cpu + 15                                           # LDA #$0F / STA $80 / RTS
    assert bytes(rom[el_i + 15:el_i + 20]) == bytes.fromhex("a90f858060")
    assert (tail_cpu >> 8) == (el_cpu >> 8), "DRSTUDYEND: tail crosses a page; JSR hi byte would change"
    jsr = bytes([0x20, el_cpu & 0xFF, el_cpu >> 8])
    sites = [i for i in range(len(rom) - 2) if bytes(rom[i:i + 3]) == jsr]
    ctx = {bytes.fromhex("a9018561"): "P1", bytes.fromhex("a9028561"): "P2"}   # their whoFailed stores
    assert sorted(ctx.get(bytes(rom[s + 3:s + 7]), "?") for s in sites) == ["P1", "P2"], (
        f"DRSTUDYEND: expected exactly anyPlayerLoses' 2 JSR ${el_cpu:04X} calls, found {sites}")
    for s in sites:
        _cpu0(s)
        put(s + 1, bytes([tail_cpu & 0xFF]))

    # 2) round end: no X-sign / red virus (updateSprites_2p_endGame, whoFailed != 0 branch)
    rv = bytes.fromhex("a561f020aabd")                               # LDA $61 / BEQ +$20 / TAX / LDA tbl,X
    rv_i = _unique(rom, rv, "red-virus")
    assert rom[rv_i + 4 + 0x20] == 0x60, "DRSTUDYEND: the BEQ target is not the routine's RTS"
    _cpu0(rv_i + 4)
    put(rv_i + 4, b"\x60")                                           # TAX -> RTS

    # 3) match final: 2P-only block of playerLoses_endScreen -> music, 128f wait, BEQ to START loop
    fin = bytes.fromhex("a9058df506" "ad2707c902d005" "a90b8df506" "a980200197" "a9ffa204a005" "2094b8")
    fin_i = _unique(rom, fin, "match-final")
    wait_cpu = rom[fin_i + 20] | (rom[fin_i + 21] << 8)              # operand of the stock JSR $9701
    wi = 0x10 + wait_cpu - 0x8000
    assert bytes(rom[wi:wi + 16]) == bytes.fromhex("8551a901855d2054b6c651a551d0f760"), (
        "DRSTUDYEND: waitFor_A_frames changed; the always-taken BEQ is no longer proven")
    loop = bytes.fromhex("a5432908f013a96d8544")                      # first START-wait loop after the block
    loop_i = rom.find(loop, fin_i)
    assert loop_i > fin_i, "DRSTUDYEND: final START-wait loop not found after the final block"
    site = fin_i + 5                                                 # $95BD
    _cpu0(site)
    assert bytes(rom[site:site + 12]) == bytes.fromhex("ad2707c902d005a90b8df506"), "DRSTUDYEND: final block"
    rel = loop_i - (site + 12)
    assert 0 < rel < 0x80, f"DRSTUDYEND: START loop out of branch range ({rel})"
    put(site, bytes([0xA9, 0x0B, 0x8D, 0xF5, 0x06,                   # LDA #$0B / STA $06F5 final music
                     0xA9, 0x80, 0x20, wait_cpu & 0xFF, wait_cpu >> 8,   # LDA #$80 / JSR $9701 (128f)
                     0xF0, rel]))                                    # BEQ START loop (Z=1 always)

    n = sum(sum(1 for a, b in zip(o, nw) if a != b) for _, o, nw in edits)
    assert n == 15, f"DRSTUDYEND: expected 15 changed bytes, got {n}"
    return edits


def describe(edits) -> str:
    return "; ".join(f"${_cpu0(o):04X} {old.hex()}->{new.hex()}" for o, old, new in edits)
