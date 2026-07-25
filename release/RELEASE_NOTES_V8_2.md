# Dr. Mario Training Edition v8.2

A stability release: fixes a hard freeze and level-select graphical corruption present in every
prior Training Edition (v6–v8) and in the coprocessor carts. The STUDY pause, VS-CPU opponent, and
"Dr. MARIO TE / TRAINING EDITION" title branding are unchanged.

## Download

- **[v8.2 BPS patch](../release/drmario_te_v8_2.bps)** — apply to a clean USA `drmario.nes`.
- **[v6.1 BPS patch](../release/drmario_te_v6_1.bps)** — the same freeze/corruption fix backported
  onto the published v6 base, for anyone updating from the v6 release.

## What's fixed

- **First-capsule freeze (the big one).** In a 1P/VS game the CPU could jump into RAM and execute a
  `KIL` opcode — a permanent lock-up with the capsule frozen mid-air, no inputs. On real hardware
  (Pocket/MiSTer) it hit almost every boot. Root cause: the 2-player STUDY-preview routines were
  placed on bytes the game reads as *nametable data* every time it draws a screen, so the title
  screen's draw mis-parsed them and corrupted the stack.
- **Level-select junk tiles.** The same misplacement drew garbage tiles on the level-select screen
  (the FEVER/CHILL/OFF row). Gone.

## How it's fixed

The five-part STUDY chain is trimmed to the part that matters (the STUDY text + your own next-pill
preview), which lives in genuinely-free space; the four colliding routines are removed and those
ROM locations restored to stock, so the title and level-select screens draw exactly like the
original game. A companion `FREE_SPACE_MAP.md` documents the ROM's real free space so this class of
bug can't recur.

## Changes to STUDY behavior

- **1-player STUDY pause is unchanged** (byte-identical): STUDY text + your next-pill preview,
  frozen board, background visible.
- **2-player / VS study pause** shows STUDY text + Player-1 preview; the **Player-2 preview and the
  2P position-lift are removed in this version** (restoration planned via a ROM-size expansion in a
  future release).

## Coprocessor carts (Pocket / MiSTer)

The self-running VS-CPU cart gets the same freeze/level-select fix. Because the cart's spare space
is used by the coprocessor driver, the small "V8.00 SL" sprite footer is dropped on the carts (the
"Dr. MARIO TE / TRAINING EDITION" title branding is kept); the standalone ROM keeps the footer.

## Known limitations (unchanged from v6)

- Dr. Mario / dancing-virus intro sprites disappear during pause.
- The falling capsule is frozen (by design — that's the study freeze).
