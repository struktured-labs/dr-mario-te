# Dr. Mario Training Edition v11

A practice hack for Dr. Mario (NES). Pause during play and the screen stays up so the position can be
**studied**. When a game or a round ends, the final board stays on screen so you can see exactly how it
was won and lost. New in v11: this now covers the **1-player game over** too.

## Download

- **IPS (the romhacking.net deliverable):** `drmario_te_v11.ips`. Apply it to the **headered** `.nes`
  of *Dr. Mario (Japan, USA)*, Rev 0 (65,552 bytes). It never touches the 16-byte header, so it
  patches both the classic iNES dump and the No-Intro NES 2.0 dump.
- **BPS:** `drmario_te_v11.bps`. It accepts only the classic iNES-headered file (CRC32 `B1F7E3E9`)
  and refuses the No-Intro NES 2.0 header.

Rebuild both from source with `build_te_v11.py`. It first reproduces v10 (byte-gated `512b815b`), and
every rebuild is byte-gated to the md5 below.

## New in v11: 1-player game over study screen

Owner request (2026-10-06): *"in single player mode if u tap out it clears ur board still"*.

| | v10 (stock 1P) | v11 |
|---|---|---|
| board after a top-out | shown for 192 frames, then wiped; a GAME OVER box is drawn in the bottle | stays until START, every virus and capsule in place, incl. the capsule that could not spawn |
| START prompt | blinks over the bottom board row (Y `$C3`) | blinks below the bottle (Y `$D8`) |
| when START is accepted | from +192 frames | the same |
| after START | level select, high-score check | the same, byte for byte |

The 1P game over (Mesen, measured on v10):
1. The top-out writes the blocked capsule into the field (`confirmPlacement`).
2. Top state 7 waits 64 + 128 frames.
3. In one frame it fills both fields with `$FF` (`$95CE`), writes the GAME OVER box into field rows 2-8
   (`$95DB`/`$95E7` → `renderGameOver $96D4`) and sets both status bytes, so the NMI redraws the bottle
   over 16 frames.
4. The START loop at `$9607` follows.

After v10's 2-player patch, `$95C9-$9606` is reached only by the 1P game over: the 2P final branches
straight to `$9607`. So v11 changes that block in place, plus one operand in the shared START loop.
It uses no free space:

| CPU | v10 (stock) | v11 | effect |
|---|---|---|---|
| `$95D4` | `JSR $B894` | `JSR $96CF` | no `$FF` fill |
| `$95DB` | `JSR $96D4` | `JSR $96CF` | no GAME OVER box (P1 field) |
| `$95E7` | `JSR $96D4` | `JSR $96CF` | no GAME OVER box (P2 field) |
| `$9614` | `LDA $A105,X` | `LDA $D4D1,X` | START Y: 1P `$D8` (was `$C3`), 2P `$D3` (as before) |

- `$96CF` is the `LDA #$0F / STA $80 / RTS` status tail that `renderGameOver` itself ends with, the
  same target v10's 2P patch uses.
- The new Y pair, `$D4D2`/`$D4D3` = `D8 D3`, is two **stock code bytes** (the operand of a `JSR $D3D8`)
  read as data. The 2P match final therefore reads `$D3` exactly as before.
- `$A105` stays stock for the 1P STAGE CLEAR and 2P round-end loops.
- `te_studyend.apply_studyend_1p(start_y=None)` is the 4-byte variant without the START move.

## Title stamp

The title stamp reads `V11.00 SL`, with the same 4-tile layout as v10. Only one tile changes.

## Unchanged from v10

10 bytes differ from v10: the 6 code bytes above and 4 bytes of one stamp tile. Every 2-player byte is
v10's. In Mesen, every 2P scenario is RAM-identical to v10 on every frame. 1P games differ from v10
only while the game over is held, and only in three places:
- the two board pages;
- the Y bytes of the 5 START-prompt sprites in the OAM shadow;
- for one frame, the `$01` fill pointer.

From the START frame on, RAM is identical again (full-RAM dump, `V11_QA_EVIDENCE.md`).

## Hashes

| | CRC32 | MD5 | SHA-1 |
|---|---|---|---|
| base, No-Intro *Dr. Mario (Japan, USA) (En)*, headerless | `198C2F41` | `5B401F4CA7E1B12AF3F29D8FC758DD2F` | `FF6459BC3AF5743E3D303823999F33D74ABDF1AA` |
| base, classic iNES header | `B1F7E3E9` | `D3EC44424B5AC1A4DC77709829F721C9` | `01DE1E04C396298358E86468BA96148066688194` |
| base, No-Intro NES 2.0 header | `556AE5C3` | `B1EC5AF2D666BFDDA49328793E05FE47` | `D51BF5CABD06FFAC94D3B72E6D9BBC0F014ECC9C` |
| **v11**, headerless | `3759A400` | `7FCC8C3AF9E07422DFBF0F854B909B55` | `EF701897A69995365AAE377E8ADCE8C1A1027092` |
| **v11**, classic iNES header | `9F2268A8` | `4CE1622AA27E91E54694099B6F9DF163` | `2CDC6F978C5D66A6686BB13C6D62BF7BEFBB8817` |
| **v11**, No-Intro NES 2.0 header (IPS) | `7BBF6E82` | `8891CFC2CAFCD468F8766E8FC8B977F0` | `10B23F8150796DA55233849A6FE03A68D87842AD` |
| `drmario_te_v11.ips` (1,411 B) | `758D72ED` | `6370F051C79A7BFA2050176D377A6C09` | `6779C15F9457DCF52B1539B5CBFE6A600BB68ECD` |
| `drmario_te_v11.bps` (1,183 B) | `2144DF1C` | `896A9AC5BD5C13B9E9A938F5262FC39F` | `A25B96F0F0C451A6045696837E2752542DDBEDDE` |

(A BPS file's own CRC32 is always `2144DF1C`: the format ends with the CRC of everything before it.)

## Validation

See `V11_QA_EVIDENCE.md`. In brief:

- **Build gates** (`build_te_v11.py`, `te_release_gates.py`):
  - v10 is reproduced and its gates re-run;
  - the delta vs v10 is exactly the 6 bytes plus one stamp tile;
  - every write lands on stock code;
  - the START pair is stock with its 2P entry `$D3`;
  - the KIL/garble sites, now including the whole `$9FF8-$A057` cutscene table, are vanilla;
  - 0 changed bytes inside any `RB6C2_PRINT` table; the published v6 still fails the gates.
- **Patch round-trips** on the canonical base (md5 `d3ec4442…`): Floating IPS (IPS and BPS), a freshly
  written IPS applier, and the repo's independent decoders all give `4ce1622a…`.
- **py65** (`tests/test_te_v11_release.py`), the real end-screen code:
  - 1P: v10 wipes; v11 keeps both fields, with the same 192 frames to the START loop. RAM differs only
    in the fields and `$00/$01`, and is identical after START.
  - 2P match final: identical write trace and RAM in v10 and v11.
- **Mesen 2, full games, both controllers driven from Lua** (`tools/te_release_qa/`):
  - 1P game overs at levels 0-20 on all three speeds, held 600 frames past the stock wipe point;
  - an early START during the stock waits, which is ignored as in stock;
  - 1P stage clears, the full 2P matrix and VS CPU;
  - No-Intro header and random power-on RAM;
  - two 40k-frame soaks.

## Free-space note

FREE_SPACE_MAP.md listed `$A02E-$A03D` and `$A049-$A057` as shared-free. Both runs are inside the 96-byte
cutscene table at `$9FF8` (`LDA $9FF8,X`, X = speed × 32 + level). Their HI-speed entries for levels
0-5 and 17-21 are live data. The map is corrected and the gate now protects the whole table. v11 needs no free space.

## Credits

- Hack: struktured. Patch created with assistance from Claude Code (Anthropic).
- Disassemblies:
  - Nostaljipi, [dr-mario-disassembly](https://github.com/Nostaljipi/dr-mario-disassembly)
  - Brian Huffman, [drmario](https://github.com/brianhuffman/drmario)
- Mesen 2 (Sour).
- Dr. Mario © Nintendo. This is an unofficial fan patch and contains no Nintendo code; supply your own
  ROM.
