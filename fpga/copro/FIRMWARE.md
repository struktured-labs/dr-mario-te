# copro firmware (`copro_rom.hex`) — base vs delta, and why the committed hex is the DELTA build

The CoproDrMario 6502 firmware ROM (`$8000-$BFFF`, loaded by `$readmemh("copro_rom.hex", rom)`) exists
in two byte-different but **behaviorally cell-exact** builds. This note exists because the committed
hex silently drifted to the wrong one, and a blind vendor almost shipped that drift to silicon.

## The two builds

| build | md5 | what it is | validated by | how to produce |
|---|---|---|---|---|
| **DELTA (SHIPPED)** | `c87e60a1` | drives the RTL CMD-6/7 incremental-leaf engine (CMD-6 BASE per parent + CMD-7 DELTA per child, CMD-4 fallback on a clearing placement). Faster; this is what vendors to the Pocket/MiSTer and runs on devices. | **Verilator co-sim** `./run_gate.sh` (delta moves == base moves, cell-exact). py65 **cannot** validate it — `attach_engine_emu` models CMD-1/4 only, not the RTL delta engine. | `python dbg_build.py all 0` (USE_DELTA=True, DEBUG_VAL1=False) → writes `copro_rom.hex` |
| BASE (reference) | `412615b2` | full leaf per node via CMD-4; no delta engine. Same search decisions, slower. A py65-validatable reference for the search LOGIC. | **py65** `build_copro_d3.py` (direct-call + stub-flow vs `decide_d3`) | `python build_copro_d3.py` → writes `copro_rom.base.hex` (gitignored) |

`USE_DELTA` is a module flag in `tests/test_search_d3.py` (default **False**). The RTL delta engine
(CMD-6/7, `S_FO1/S_FO2` delta_mode-leak fix, `dv_fallback`) lives in `LeafEval.sv` + `CoproDrMario.sv`
and is committed. Delta is a **speed** optimization; it does not change play (cell-exact to base).

## The committed `copro_rom.hex` is the DELTA build

Reproduce it byte-exact:
```bash
python dbg_build.py all 0        # -> copro_rom.hex, md5 c87e60a1
./run_gate.sh                    # co-sim cell-exact gate; also leaves the DELTA hex in place
```
`build_copro_d3.build_image()` with `USE_DELTA=True` and the LOCAL emitter produces the identical
bytes; `dbg_build.py` is the wrapper that force-loads that local emitter (see the shadow trap below)
and is the canonical delta builder.

## Three ways the committed hex used to drift back to BASE (all now guarded)

1. **`run_gate.sh` "restore pristine baseline"** ran `dbg_build.py baseline 0` at the end, leaving the
   BASE hex in the working tree. Whoever committed next captured base. → **Fixed:** it now restores
   `dbg_build.py all 0` (delta).
2. **`build_copro_d3.py` standalone** built base and overwrote `copro_rom.hex`. → **Fixed:** `main()`
   now writes `copro_rom.base.hex` (a clearly-named reference) and never touches the ship hex; it
   reports the ship hex md5 + the delta recipe instead.
3. **`sync_to_pocket.sh`** copied the canonical hex over the vendored (shipped) hex verbatim. A blind
   RTL-only sync would have reverted the shipped CMD-6/7 delta engine — presenting on silicon as "the
   new eval plays worse." → **Fixed:** it now FAILS LOUDLY when canonical ≠ vendored (RTL-only syncs
   never touch firmware). A deliberate firmware update validates via `run_gate.sh` then re-runs with
   `ALLOW_HEX_UPDATE=1`.

## The shadow-emitter trap (why `dbg_build.py`, not `build_copro_d3.py`, builds delta)

A naive `import build_copro_d3` (or `python build_copro_d3.py`) imports
`/home/struktured/projects/dr-mario-mods/tests/test_search_d3.py` — the **main-repo (study-pause)
shadow**, which is the PRE-delta emitter with no `USE_DELTA` at all — so it can only build BASE.
`dbg_build.py` exists precisely to force-load the LOCAL incr-delta `tests/test_search_d3.py` (the delta
emitter) into `sys.modules` before `build_copro_d3` imports it. Always build the shipped firmware via
`dbg_build.py all 0`. `build_copro_d3.py` warns if it detects the shadow emitter.

## Vendor source of truth: only `incr-delta` (→ `copro-canonical`). NEVER `study-pause`.

`sync_to_pocket.sh` vendors from whatever tree it runs in. The ONLY safe vendor source is the branch
that carries the delta engine + the reconciled ship hex + the guard together — `incr-delta`, now
promoted into `copro-canonical`.

`study-pause` (`~/projects/dr-mario-mods`) is a **research tree, never a vendor source**:
- It has NO delta engine (base `LeafEval.sv`) and still carries the **pre-fix `build_copro_d3.py`**
  that overwrites `copro_rom.hex` with the BASE build. Running any firmware build there produces
  **base-hex residue** (`412615b2`) in the working tree — that residue is not device firmware and must
  never be vendored. Its committed hex is older still (`3d73b374`).
- It typically holds active, uncommitted eval-research changes. Do not reach into it to "fix" the
  build script; whoever owns that lane picks up the `build_copro_d3.py` / `run_gate.sh` /
  `sync_to_pocket.sh` fixes when they next sync from canonical.
If you must vendor, run `sync_to_pocket.sh` from `incr-delta`/`copro-canonical` only. The guard will
still fail-loud if the hex disagrees, but the source-tree choice is your first line of defense.

## History
- Delta engine landed cell-exact at `9e040e3` (2026-07-25); RTL + `dbg_build.py` + `USE_DELTA`.
- Shipped delta `c87e60a1` vendored to Pocket at `b7429de` from a `9e040e3-dirty` tree — never
  committed back to canonical, so the committed hex stayed at the base `412615b2` (fd8e495, 2026-07-22).
- Reconciled (this note + committed `copro_rom.hex` = `c87e60a1`) under the r47b5 eval build, 2026-07-26.
