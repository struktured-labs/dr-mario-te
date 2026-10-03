# Dr. Mario Training Edition v10

A practice hack for Dr. Mario (NES). Pause during play and the screen stays up so the position can be
**studied**. New in v10: when a 2-player round ends, **both final boards stay on screen**, so you can
see exactly how it was won and lost.

## Download

- **IPS (the romhacking.net deliverable):** `drmario_te_v10.ips`. Apply it to the **headered** `.nes`
  of *Dr. Mario (Japan, USA)*, Rev 0 (65,552 bytes). It never touches the 16-byte header, so it
  patches both the classic iNES dump and the No-Intro NES 2.0 dump.
- **BPS:** `drmario_te_v10.bps`. It accepts only the classic iNES-headered file (CRC32 `B1F7E3E9`)
  and refuses the No-Intro NES 2.0 header.

Rebuild both from source with `build_te_v10.py`. Every rebuild is byte-gated to the md5 below.

## New in v10

### End-of-round study screen (2-player)

| screen | v9 (stock behaviour) | v10 |
|---|---|---|
| round lost by topping out | X-sign virus over the loser's bottle; the loser's lower half wiped | both final boards intact, no sign |
| match final (third win), by top-out **or** by virus clear | both bottles replaced by GAME OVER boxes, Dr. Mario dances | both final boards intact; waits for START |
| round won by clearing every virus (not the final) | STAGE CLEAR box; the loser's board stays visible | unchanged |

- After START the game continues as before, and the next match starts clean: wins 0/0, fresh viruses
  only.
- On a match won by clearing the last virus, that final clear stays drawn as outlined "pops" in the
  winner's bottle. Stock covers the frame with GAME OVER; v10 leaves it visible.

This is the `DRSTUDYEND` change from the cart lineage (PR #28; silicon-verified on MiSTer in the couch
cart), ported to the standalone ROM by `te_studyend.py`. It is 15 in-place bytes of **stock game code**
and uses no free space:

| CPU | stock | v10 | effect |
|---|---|---|---|
| `$954F`/`$9579` | `JSR $96C0` | `JSR $96CF` | skip the 64 × `$FF` wipe of the loser's rows 8-15; keep the routine's status-redraw tail |
| `$8890` | `TAX` | `RTS` | `whoFailed != 0` returns before drawing the X-sign / red virus |
| `$95BD-$95C8` | 2P re-check + music | music `$0B`, the same 128-frame wait, `BEQ $9607` | the match final skips the both-field fill, the GAME OVER stamps and the win-state stores |

Applied to the couch control cart `c960dd49`, the port reproduces the shipped DRSTUDYEND cart
`8c6e4196` byte for byte (`tests/test_te_v10_release.py` C). None of the bytes depends on the
coprocessor, the driver, PRG-RAM or the in-cart opponent.

### Title stamp

The title now reads `V10.00 SL`. v9 shipped `V8.00 SL` (issue #12). The change is 4 CHR tiles with the
same layout, so the footer routine and metasprite are untouched.

## Unchanged from v9

Everything else is byte-for-byte v9. 35 bytes differ from v9: the 15 code bytes above plus 20 bytes of
stamp graphics. 1P games run frame-for-frame identical to v9 (RAM compared every frame in Mesen).

## Hashes

| | CRC32 | MD5 | SHA-1 |
|---|---|---|---|
| base, No-Intro *Dr. Mario (Japan, USA) (En)*, headerless | `198C2F41` | `5B401F4CA7E1B12AF3F29D8FC758DD2F` | `FF6459BC3AF5743E3D303823999F33D74ABDF1AA` |
| base, classic iNES header | `B1F7E3E9` | `D3EC44424B5AC1A4DC77709829F721C9` | `01DE1E04C396298358E86468BA96148066688194` |
| base, No-Intro NES 2.0 header | `556AE5C3` | `B1EC5AF2D666BFDDA49328793E05FE47` | `D51BF5CABD06FFAC94D3B72E6D9BBC0F014ECC9C` |
| **v10**, headerless | `E80D18E4` | `83CE64DC38B25DABF51B79AB11B76A1E` | `F6838BBC34F96D067412F920E4B610DD72C28037` |
| **v10**, classic iNES header | `4076D44C` | `512B815B9A2944754AF3B28E9852D4ED` | `52905762015688129589ED4FB826127CA439CB66` |
| **v10**, No-Intro NES 2.0 header (IPS) | `A4EBD266` | `6724286DC8D0167C52C51184A76BCB85` | `E893B71F993AAB96285E94D79FC2C1DCFB7E08E9` |
| `drmario_te_v10.ips` (1,385 B) | `FDA88FA7` | `422BEC4C95A097911CEB92150F5C3714` | `524E136BAE7C029ED290BB86AF9D7954A4FA783B` |
| `drmario_te_v10.bps` (1,168 B) | `2144DF1C` | `E4A03FC211A229CD81E006DF4294FD93` | `48843EFA41E65115906AB0FBF14A93B7DAFC835E` |

Rev 1 / Rev A (`A4E02BAF…` headered) is a different ROM; a patch applied to it produces garbage.

## Validation

See `V10_QA_EVIDENCE.md`. In brief:

- **Build gates** (`build_te_v10.py`, `te_release_gates.py`):
  - the delta vs v9 is exactly DRSTUDYEND plus the stamp;
  - the historical KIL/garble sites (`$BC26 $BE56 $9FF8 $A371 $C0A9 $C0EF $CF00`) are vanilla;
  - a simulated `RB6C2_PRINT` walk of all 21 printing tables finds 0 changed bytes inside them;
  - the gates are two-sided: they flag the published v6 (KIL) build.
- **Patch round-trips:** IPS and BPS were applied to the base by Floating IPS (built from source) and
  by decoders that share no code with the encoders (`tools/ipsdiff.py`, `tools/te_release_kit.py`).
  All three give md5 `512b815b…`. The IPS also patches the No-Intro-headered file.
- **Mesen 2, full games, both controllers driven from Lua** (`tools/te_release_qa/`): 1P to game over,
  2P human-vs-human matches through every round end (top-outs and virus clears) and match finals,
  VS CPU matches, STUDY pauses, the next match, and two 40k-frame (11+ min) mixed soaks, one with
  random power-on RAM. 0 freezes. The published v9 ROM run on the same scripts is the positive
  control.
- **nes-py cross-check** (`tools/te_release_kit.py`, dry run): RELEASE-READY. The stamp change was
  detected against the v9 title capture.

## Credits

- Hack: struktured. Patch created with assistance from Claude Code (Anthropic).
- Disassemblies:
  - Nostaljipi, [dr-mario-disassembly](https://github.com/Nostaljipi/dr-mario-disassembly)
  - Brian Huffman, [drmario](https://github.com/brianhuffman/drmario)
- Mesen 2 (Sour).
- Dr. Mario © Nintendo. This is an unofficial fan patch and contains no Nintendo code; supply your own
  ROM.
