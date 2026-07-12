# Dr. Mario NES — FPGA AI Coprocessor

A hardware-accelerated depth-3 AI that plays Dr. Mario (NES) on a real
[MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/wiki) FPGA. A custom mapper drops a
**second 6502 core plus an RTL board-engine** into the NES core; a companion cartridge
auto-navigates into a VS-CPU match and lets the coprocessor drive a player — no controller,
no host PC in the loop. It is a self-running demo of an expectimax search running on silicon
alongside the game it is playing.

## Milestone — depth-3 on hardware at ~1 second per move

The AI runs a **depth-3 expectimax search** (current pill + preview pill known, third pill
averaged over a pill subset) with an endgame-tuned evaluation. In pure simulation the
decision function clears **93.8%** of L11 boards solo (n=48, exact firmware model). The whole
pipeline — search → firmware → cycle-accurate sim → Quartus → hardware — is validated
cell-exact at each stage.

**Latency, start of port → now:**

| Build | First-pill decision | What changed |
| --- | --- | --- |
| initial | ~400 s | copro fed the 21.5 MHz NES clock (never the intended 85.9 MHz) |
| `clk85` | ~100 s | dual-clock fix: 6502 + engine on the master clock |
| 4-pill | ~50 s | 4-pill expectimax subset (measured 100% solo, no quality loss) |
| LeafEval | ~4 s | full leaf evaluation in RTL (~1.5k cycles vs ~50k on the 6502) |
| **BoardEngine** | **~1 s** | land + place + resolve + leaf + board copies all in RTL; 6502 is pure search control |

Steady-state moves are sub-second — the demo is now paced by the game's own pill-drop and
clear animations, not by the AI.

## How it works

- **Mapper 100** (`fpga/copro/CoproDrMario.sv`) = MMC1 banking + this block. A second 6502
  (`copro6502.v`, Arlet core) free-runs at the core master clock (`clk85`), with a host
  register window at `$5000–$51FF` (one window per player, dual-copro so P1/P2 never
  time-share). The game CPU writes the board + pill colors, pulses GO, polls DONE, reads back
  the chosen column + orientation.
- **BoardEngine** (`fpga/copro/LeafEval.sv`) is the RTL accelerator at `$7000–$70FF`: a single
  `NODE` command does landing + placement + a capped targeted resolve + the full leaf eval,
  plus single-command snapshot/restore of the working boards. This is what collapsed the
  per-search-node cost and made depth-3 practical on hardware.
- **The cartridge** (`patch_cartridge_copro.py` → `drmario_copro.nes`) is a patched ROM whose
  every-frame hook auto-navigates to VS-CPU L11 and, in play, uploads each locked pill to the
  coprocessor and executes the returned move. It also carries a per-player **seeded tie-break**
  so the two same-strategy copros desync into distinct games (same evaluation, different
  near-tie resolution — not a strategy divergence).

## Validation chain

Every acceleration step is proven the same way before it reaches hardware:

1. **py65** — the 6502 search vs a Python golden (`tests/`, cell-exact).
2. **Verilator** — the RTL block vs the same board-suite goldens the 6502 primitives passed
   (`fpga/copro/tb_leafeval.cpp`: 205/205 leaf, 250/250 node), and the full mapper vs an oracle
   (`fpga/copro/sim_mister.cpp`).
3. **Quartus** — timing closed at 85.9 MHz; the generated firmware MIF is byte-verified against
   `copro_rom.hex` before every deploy.
4. **Hardware** — deployed to the MiSTer, pace + play confirmed live.

## Build / deploy

```bash
# firmware (depth-3 4-pill BoardEngine) — writes fpga/copro/copro_rom.hex, validates in py65
.venv/bin/python fpga/copro/build_copro_d3.py

# auto-nav cartridge (level/speed via env)
DRLEVEL=11 DRSPEED=1 .venv/bin/python patch_cartridge_copro.py   # -> drmario_copro.nes

# FPGA core: copy copro_rom.hex into the NES_MiSTer tree, then
#   quartus_sh --flow compile NES   -> output_files/NES.rbf
# deploy NES.rbf + drmario_copro.nes to the MiSTer and launch.
```

The RTL sources here (`fpga/copro/CoproDrMario.sv`, `LeafEval.sv`) are the source of truth;
they are mirrored into a local `NES_MiSTer` checkout for Quartus synthesis.

## Further reading

- `INTEGRATION_SPEC.md`, `ROM_WIRING_PLAN.md` — cartridge/mapper wiring
- `DEPTH2_BUILD.md`, `DEPTH2_FEASIBILITY.md` — the depth-2 predecessor
- `VS_CPU_PLAN.md` — auto-nav VS-CPU demo design
- `CLAUDE.md` — memory map, tile encoding, mechanics reference

## Known open items

- **Match clear-rate is unmeasured on hardware** — the screenshot OCR's hamming gate rejects
  the near-clear virus-count reads, so the automated clear tally is currently blind. Fix the
  detector before trusting a hardware clear-rate figure.
- **The search does not engineer cascade combos** — the model's resolve is capped (one clear +
  one gravity, no chain), so cascade payoffs earn no immediate reward. The BoardEngine now
  makes a full cascading resolve cheap to add; it is a quality-gated change (an earlier fuller
  resolve regressed in a small isolation, so it must win in sim first).
