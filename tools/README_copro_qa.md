# Copro-cart QA harness (Mesen mailbox emulation)

QA the **shipped mapper-100 coprocessor cart** in Mesen2 with **no FPGA and no SD writes**,
by emulating the copro's memory-mapped mailbox in Lua so the cart's driver runs and its AI
places pills. Built for task #47.

## Why this works

The cart stamps **mapper 100** only to route itself to the MiSTer/Pocket core; its real PRG
banking is plain **MMC1**. So we **remap the iNES header to mapper 1** (PRG+CHR byte-identical —
only the two mapper nibbles change) and Mesen boots it with correct banking. The copro window
`$5000-$53FF` is then open bus, which Lua intercepts with memory callbacks. MMC1 also provides
WRAM `$6000-$7FFF`, where the driver keeps its state (`$614E-$616B`), so it runs unmodified.

## Mailbox contract (per window `W` = `$5000` P1 / `$5200` P2)

From `patch_cartridge_copro.py`:

| Addr | Dir | Meaning |
|---|---|---|
| `W+$00..$7F` | driver→copro | board upload, 128 cells row-major 8×16 (`0xFF` = empty; `0x00`→empty) |
| `W+$80..$83` | driver→copro | colors: fall1, fall2, next1, next2 (low nibble; hi nibble carries a tie seed) |
| `W+$84` | **write = GO** | pulse: latch board, clear DONE |
| `W+$84` | **read = DONE** | `0` = searching; non-zero = ready |
| `W+$85` | read | best column `0..7` |
| `W+$86` | read | orient (`0xFF` = "no result yet"; else copro orient `0..3`) |

The driver maps copro→game orient `{0xFF/0:3, 1:1, 2:0, 3:2}`, writes `tgt_c/tgt_o`
(`$6150/$6151` P1, `$6152/$6153` P2), and navigates the pill there.

## Files

- `copro_emu.lua` — **reusable** mailbox emulator module. `local EMU = dofile(".../copro_emu.lua"); EMU.attach{window, board_src, colA, colB, latency [, brain]}`. Attach once per active window. Default `brain` = emptiest-column, vertical (a plumbing stand-in — not a smart AI; it makes pills stack, not clear).
- `qa_harness.lua` — config-driven runner (single window): attaches the emulator, drives the cart into VS-CPU play, proves the AI places pills, pauses into DRSTUDY, and dumps/screenshots STUDY + both previews (OAM slots 37-40). Edit the `CFG` block per cart.
- `ab_run.lua` — two-window proof: attaches `copro_emu` on **both** `$5000` and `$5200` of the AB dual-copro cart (zero input) and logs GO/DONE + fill for both players.
- `remap_mapper100_mmc1.py` — header remap (mapper 100→1). Byte-identical PRG/CHR.
- `evidence/` — proof screenshots (AI placing pills; 2P STUDY with both previews).

## Usage

```bash
# 1) remap the cart (mapper 100 -> MMC1)
python3 tools/remap_mapper100_mmc1.py tmp/drmario_copro_ab_slam_te.nes tmp/qa_ab_mmc1.nes

# 2) run a proof — ONE Mesen instance only (see single-instance warning)
cd mesen2/bin/linux-x64/Release
DRQA_DIR=<abs>/tools DRQA_OUT=<abs>/tmp/qa \
  timeout 140 ../../../run_mesen.sh <abs>/tmp/qa_ab_mmc1.nes <abs>/tools/ab_run.lua --donotsavesettings
# results: $DRQA_OUT/ab_run.log + screenshots. emu.stop(0) ends emulation; timeout kills the window.
```

`DRQA_DIR` = folder holding `copro_emu.lua` (required). `DRQA_OUT` = output dir (default
`$DRQA_DIR/shots` for `ab_run.lua`, `/tmp` for `qa_harness.lua`).

**Cart choice:** use the **AB dual-copro cart** (`drmario_copro_ab_slam_te.nes`) for the
placement proof — zero-input, both players are copro AI (P1 `$5000`/board `$0400`/colA `$0301`;
P2 `$5200`/board `$0500`/colA `$0381`). Use a **pocket/standalone v8.x cart** for the 2P-STUDY
preview check (`qa_harness.lua` injects P1 START to reach the pause).

## Proven results

Two-window AB run (`ab_slam_te_mmc1.nes` md5 `a91eed57`, zero input, latency=24) — the driver
adopts our answers and both AIs place pills:

```
PLAY at 235  players $0727=2
t+240  P1 fill=54 tgtC=0 GO=4 DONE=4 | P2 fill=54 tgtC=0 GO=4 DONE=4
t+480  P1 fill=60 tgtC=1 GO=7 DONE=6 | P2 fill=62 tgtC=2 GO=7 DONE=7
t+720  P1 fill=64 tgtC=5 GO=11 DONE=10 | P2 fill=64 tgtC=5 GO=10 DONE=10
SUMMARY  P1 GO=12 DONE=11 | P2 GO=11 DONE=11   (both windows served; tgtC varies per pill;
                                                pill X tracks tgtC; both boards fill 48->64)
```

Both windows' callbacks are independent (`$5084` vs `$5284`, no collision) → `copro_emu.lua`
is proven reusable on a multi-window cart. **2P STUDY** (see `evidence/03_2P_study_both_previews.png`):
both next-pill previews render (OAM slots 37-38 P1, 39-40 P2 on-screen) — part-4 verified.

Note: the emptiest-column default brain does no color-matching, so viruses are not cleared —
this proves the **mailbox plumbing + placement**, not clearing. Intelligent clearing needs the
real-planner bridge (a future deliverable).

## Mesen2 gotchas (verified — do not relearn the hard way)

- **Mesen2 is SINGLE-INSTANCE** (`Preferences.SingleInstance=true`). A second
  `Mesen <rom> <lua>` forwards its args into the *running* instance and exits 0 — it does not
  start a new emulator. With many agents, launches collide (your ROM/script is injected into
  someone else's window; results go flaky: clean exit, no output). **Only one driver at a time**,
  or isolate via a private config with `SingleInstance=false`.
- **A read callback that returns an integer overrides the read** (even open bus) — the channel
  for DONE/col/orient. Results must be readable *before* DONE flips.
- **Never call `emu.read()` inside a memory callback — it silently disables that callback.**
  The GO write-callback only flags a snapshot; the board is read from *source RAM*
  (`$0400/$0500`) in an `endFrame` event callback (stable while the pill is airborne).
- Use a **single-address** write callback at `W+$84` for GO; a range write-callback disables an
  overlapping single-address one, and EXEC-based GO detection is unreliable.
- **`emu.stop(0)` stops emulation but does NOT close the process** — rely on `timeout`, and write
  results to a file *before* `emu.stop`.
- On the AB cart, RAM `$0324/$03A4` are **not** the live virus count (they read a flat `72`);
  trust the screen / board fill instead.
- Launch: `Mesen <mmc1.nes> <script.lua> --donotsavesettings` (positional `.lua` auto-loads);
  io/os available; `emu.memType.nesMemory/nesDebug/nesSpriteRam`, `emu.callbackType.read/write`,
  `emu.eventType.startFrame/endFrame/inputPolled`.

## Provenance / validation

Mailbox logic + two-window proof + 2P-STUDY previews were validated on real Mesen (see
`evidence/`). The header-remap tool is byte-verified (produces md5 `a91eed57`, identical to the
reference cart). The `DRQA_DIR`/`DRQA_OUT` path-config wrappers were validated by loading both
runners under a mock `emu` (correct callback registration; clean error when `DRQA_DIR` is unset).
`copro_emu.lua` co-authored with teammate `te-ingame-logo`.
