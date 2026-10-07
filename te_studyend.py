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

1-PLAYER GAME OVER (``apply_studyend_1p``, TE v11; owner 2026-10-06: "in single player mode if
u tap out it clears ur board still"). Measured in Mesen on v10 (stock 1P): the top-out's
capsule is written into the field by action_sendPill's fail path (confirmPlacement), so the
final board incl. that capsule is field RAM. Top state 7 then waits 64 + 128 frames with
the board on screen, and in ONE frame (+193) fills $0400-$05FF with $FF ($B894), writes the
GAME OVER box into field rows 2-8 of both fields (renderGameOver $96D4) and sets both status
bytes to $0F, so the NMI redraws the bottle row by row (+194..+209). START is read from +192
in the loop at $9607 (blinking START sprite at Y = $A105[nbPlayers] = $C3 -- the bottom
board row in 1P); START fills both fields with $FE and goes to the options screen.

After ``apply_studyend`` the code from $95C9 to $9606 is reached ONLY by the 1-player game
over (the 2P final now branches straight to $9607), so it can be changed without touching
any 2P path:

  $95D4  JSR $B894 -> JSR $96CF   (no $FF fill; $96CF = LDA #$0F / STA $80 / RTS, the
                                   status tail renderGameOver itself ends with)
  $95DB  JSR $96D4 -> JSR $96CF   (no GAME OVER box in P1's field)
  $95E7  JSR $96D4 -> JSR $96CF   (no GAME OVER box in P2's field)

Everything else on that path runs as stock (the waits, both status stores -- the redraw
repaints the same board --, whoFailed / whoWon, the START loop, the $FE fill, the options
screen, the high-score check). Mesen, full-RAM dumps vs v10: during the hold only the two fields,
the START letters' OAM-shadow Y bytes (with start_y) and, for one frame, the $01 fill pointer
differ; the whole RAM is identical again from the START frame on.

Optional (``start_y``, shipped ON in v11): the START prompt is moved off the board, below
the bottle. The shared START loop's ``LDA $A105,X`` (X = nbPlayers) gets a new operand T with
T[1] = start_y for 1P and T[2] = $D3 = $A105[2], so the 2P match final reads the SAME value
as before (identical A and flags). No free space exists for a 3-byte table (FREE_SPACE_MAP's
$A02E/$A049 runs are inside the $9FF8 cutscene table, see below), so T points at two stock
code bytes with the right values: $D4D2/$D4D3 = the operand of a stock ``JSR $D3D8``
(read-only; the 1P STAGE CLEAR loop at $B2EE and the 2P round-end loop at $9653 keep $A105).
1P: 4 + 2 = 6 bytes.
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


START_Y_1P = 0xD8          # 1P START prompt: below the bottle (NT row 27), off the board


def apply_studyend_1p(rom: bytearray, start_y: int | None = START_Y_1P) -> list[tuple[int, bytes, bytes]]:
    """Keep the final board on the 1-player GAME OVER screen until START (see the module doc).

    ``rom`` must already carry ``apply_studyend`` (its match-final rewrite is what makes the
    patched block 1P-only; asserted). ``start_y=None`` leaves the START prompt where stock
    draws it (4 bytes); the default also moves it below the bottle (6 bytes).
    Returns ``[(file_offset, old_bytes, new_bytes), ...]``."""
    edits: list[tuple[int, bytes, bytes]] = []

    def put(off: int, new: bytes) -> None:
        old = bytes(rom[off:off + len(new)])
        rom[off:off + len(new)] = new
        edits.append((off, old, bytes(new)))

    # the 2P match final must already branch past this block (apply_studyend, step 3)
    fin = bytes.fromhex("a9058df506" "a90b8df506" "a980200197")
    fin_i = _unique(rom, fin, "DRSTUDYEND match-final (apply_studyend first)")
    assert rom[fin_i + 15] == 0xF0, "DRSTUDYEND: match-final BEQ missing (apply_studyend first)"
    loop_i = fin_i + 17 + rom[fin_i + 16]                            # its BEQ target = the START loop

    # the 1P game-over block, right after the rewritten 2P block, falling into that same loop
    go = bytes.fromhex("a980200197" "a9ffa204a005" "2094b8" "a9048558" "20d496" "a90f8d0003"
                       "a9058558" "20d496" "a90f8d8003" "a90f8580"
                       "a9008561" "a9018555" "ad1e03cd2507f004" "a9028555")
    go_i = _unique(rom, go, "1P game-over block")
    assert go_i == fin_i + 17, "DRSTUDYEND: 1P block is not right after the match-final block"
    assert go_i + len(go) == loop_i, "DRSTUDYEND: 1P block does not fall into the match-final START loop"
    assert bytes(rom[loop_i:loop_i + 16]) == bytes.fromhex("a5432908f013a96d8544ae2707bd05a1"), \
        "DRSTUDYEND: START loop changed"
    _cpu0(go_i), _cpu0(loop_i + 14)                                  # both edit sites in PRG bank 0

    # targets: renderGameOver (asserted) and the status tail of emptyLowerFieldOnLose_2P
    rg_cpu = rom[go_i + 19] | (rom[go_i + 20] << 8)
    assert rg_cpu == (rom[go_i + 31] | (rom[go_i + 32] << 8))
    rg_i = 0x10 + rg_cpu - 0x8000
    assert bytes(rom[rg_i:rg_i + 13]) == bytes.fromhex("a9008557a200a010bd38a8f007"), "renderGameOver changed"
    el_i = _unique(rom, bytes.fromhex("a9008557a040a9ff9157c8c080d0f7a90f858060"), "emptyLowerFieldOnLose_2P")
    tail_cpu = _cpu0(el_i) + 15
    assert bytes(rom[el_i + 15:el_i + 20]) == bytes.fromhex("a90f858060")
    jt = bytes([tail_cpu & 0xFF, tail_cpu >> 8])
    put(go_i + 12, jt)                                               # JSR $B894 -> JSR $96CF
    put(go_i + 19, jt)                                               # JSR $96D4 (P1) -> JSR $96CF
    put(go_i + 31, jt)                                               # JSR $96D4 (P2) -> JSR $96CF

    if start_y is not None:
        tbl = rom[loop_i + 14] | (rom[loop_i + 15] << 8)             # $A105: [0] -, [1] 1P, [2] 2P
        y2 = rom[0x10 + tbl - 0x8000 + 2]
        anchor = bytes.fromhex("20e0d3" "20") + bytes([start_y, y2]) + bytes.fromhex("20e8d3")
        a_i = _unique(rom, anchor, "stock JSR $D3E0 / JSR $D3D8 / JSR $D3E8 (START Y pair)")
        assert 0x4010 <= a_i < 0x8010, "DRSTUDYEND: START Y pair must be in the fixed upper 16 KB (32 KB layout)"
        t_cpu = 0x8000 + (a_i + 3) - 0x10                            # T: T+1 = start_y, T+2 = y2
        assert rom[0x10 + t_cpu - 0x8000 + 1] == start_y and rom[0x10 + t_cpu - 0x8000 + 2] == y2
        put(loop_i + 14, bytes([t_cpu & 0xFF, t_cpu >> 8]))          # LDA $A105,X -> LDA T,X

    n = sum(sum(1 for a, b in zip(o, nw) if a != b) for _, o, nw in edits)
    assert n == (6 if start_y is not None else 4), f"DRSTUDYEND 1P: unexpected changed-byte count {n}"
    return edits
