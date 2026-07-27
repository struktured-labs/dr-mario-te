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

## Provenance gap: we cannot prove a shipped FPGA core was built from the RTL we think it was

This is a **process finding**, first hit auditing `nes.rev.r47b5_c11_pad` (the vrdy 24→12 eval core,
2026-07-26). It is not specific to that core; it recurs on **every** FPGA core we ship. Same disease as
the firmware drift above and the "python golden was a pre-release build" trap: *the repo/manifest
describes something whose presence on the actual device is unproven.*

**Motivating incident (2026-07-26, live — not hypothetical).** The hardware lane needed to know whether
the MiSTer's *deployed* core carried the eval fix (`vrdy=12`) or the old `vrdy=24`. No inspectable
artifact could answer it: the bitstream is opaque, and the audit could confirm only the *source commit*
and that a genuine re-fit had happened — not that *this deployed bitstream* contains the fix. The lane had
to fall back on **inferring the eval from the AI's playing style** — measuring average landing/board
height across games and reasoning backward about which weight produces it. That is an enormous amount of
work to answer "which build is this?", and it is the concrete cost of having no build-ID readout.
Worse, that fallback **failed on its own terms**: fill-height's ~4-point phase swing across a game swamps
the ~1.1-row vrdy 24-vs-12 signature (see the decision-fingerprint method warning), so even the behavioral
workaround could not answer it. Either fix below would have turned the whole question into a single
save-state RAM read.

**What IS verifiable from inspectable artifacts:**
- **Source commit.** The staged core names its build commit; you can `git show <sha>:fpga/copro/LeafEval.sv`
  and confirm the RTL says what it claims (e.g. `16'd12 * vrdy_p`, not `16'd24`), and that the parent
  had the old value — i.e. the source change is real and isolated.
- **Rebuild determinism of the firmware.** `copro_rom.hex` is reproducible byte-exact (`dbg_build.py all 0`
  → `c87e60a1`); the py65/co-sim gates are cell-exact. The 6502 firmware side is fully pinned.
- **Artifact identity.** The `.rev` md5 matches the manifest, and a real re-fit is distinguishable from a
  copy (a one-constant RTL change still perturbs most of the bitstream + the fitter report).

**What is NOT verifiable — the gap:**
- **Bitstream → RTL.** A Quartus `.rbf`/`.rev` cannot be decompiled, and the compile is not bit-reproducible
  here. Nothing in the shipped bitstream ties it to a specific source commit. So "source commit X contains
  the fix" + "this is a genuine distinct build" does **not** prove the fix is in *this* bitstream. The only
  definitive check today is a **hardware A/B** (see task #52) — behavioral, not byte-level. Treat that A/B
  as load-bearing, not merely nice-to-have, whenever an eval/logic change reaches silicon.
- **Bitstream → card (no deployment record).** Even given a specific bitstream, nothing records *which*
  bitstream was written to a physical card at a given time. **Motivating incident (2026-07-26, live):** asked
  which of the July-18/19 weekend cores the user actually played, the honest answer was **not determinable.**
  The SD snapshot proves the card held `87bc69c4` at 07-18 09:50, but five later weekend builds
  (`seed5_85_9` 13:56, `anytime` 14:58, `discount` 17:17, `eh` 21:29, `combo` 07-19 11:25) exist only in the
  staging dir -- and **staging presence is not deployment.** No deploy log, no staging note (the earliest is
  07-25), and an un-timestamped 2000-line bash history that no longer reaches that far: which build reached the
  card is simply unrecorded, and the physical card has been rewritten many times since. (The vrdy=12 eval
  conclusion is unaffected -- *every* weekend build predates the 07-22 vrdy 12->24 change -- but "we have the
  exact core he liked" is not established.)
  - ⚠ **The staged `nes.rev.*` files in `/mnt/data/drmario/pocket-copro/` (16 and counting) have no ordering,
    no provenance, and no deployment record between them.** Anyone reading that directory in three months will
    assume the newest is what shipped. It is not necessarily. **Do not treat mtime order as ship order.**

**Cheapest ways to close it going forward (PROPOSED — not built):**
0. **Deploy log — adopt immediately, no code, no build required (the bitstream->card half).** Every time
   anything is written to a physical card, append one line to a `DEPLOY_LOG.txt`: **timestamp, artifact
   filename, md5, destination.** Three fields, one append, no tooling. Unlike the register (1) and the
   buildinfo sidecar (2) — which both need a *build* to exist and close the RTL->bitstream half — this needs
   only the habit, and it alone would have answered tonight's "which weekend core did he play?". **Start it
   with the very next card write.**
1. **Build-ID / eval-signature register in RTL, readable over the existing `$5000` mailbox (preferred).**
   Synthesize a small read-only register holding a build stamp — e.g. a 16–32-bit git-hash prefix and/or a
   packed digest of the eval constants (`W_VRDY`, `W_MAXH`, `W_RDY`, …). Expose it via a new mailbox
   read (a reserved `$5000` sub-address or a new CMD), so the host 6502 can read the core's own identity
   and drop it into the `$6200` diagnostic ring. Then "which core / does it have vrdy=12?" becomes a
   **one-line savestate-RAM read on silicon** (same channel as the existing frozen-RAM forensics), instead
   of tonight's unprovable claim. **Feasible:** the mailbox is already a host↔copro dual-port/2FF path,
   and a constant register is trivial logic on its own async group; the only real cost is the tiny
   firmware+driver read path. This is the highest-leverage fix and would have made tonight a 10-second read.
2. **Quartus build-manifest sidecar (near-zero cost, weaker).** At build time, write a `<core>.buildinfo`
   next to the `.rev`: source commit, `.qsf`/revision, fitter report hash, key eval constants, toolchain
   version. It only attests what the build *system* claims (not what the bitstream *contains*), but it makes
   provenance a recorded artifact rather than tribal memory, and it costs one file at package time.
   **Where it must live (2026-07-26 finding):** the effective home is the FPGA lane's **local** Quartus
   build + bit-reverse step (`~/projects/pocket-nes-mapper100`, `output_files/nes_pocket.rbf` → `nes.rev.*`),
   NOT the upstream OpenGateware CI publish helper (`.github/publish/helpers/package.py:reverse_bitstream`,
   `release.py`). That CI path is keyed off `GITHUB_REF`/tags, but dev cores (e.g. r47b5) are built locally
   and explicitly carry NO tag until silicon — so patching only the CI helper would miss the cores that
   actually ship. Owner (assigned 2026-07-26): the **mister-ab** lane — they build a core locally with
   Quartus for the silicon A/B (#52) and are the very lane that just spent an hour unable to tell which eval
   a deployed bitstream carried, so the first core to carry provenance should be theirs; spec sent to them
   directly. Spec: emit `<name>.buildinfo` = `git rev-parse HEAD`, the LeafEval eval constants
   (`grep 16'd.. * .._p LeafEval.sv`), `.qsf` revision, and the fitter-report ALM/register/slack lines,
   at the moment the `.rev`/`.rbf` is produced.

Recommendation: do (0) and (2) immediately (both free), and schedule (1) as the real fix — a core that self-identifies
on silicon turns an entire class of "is this really the build we think?" questions into a register read.

## Running the gate / long jobs (process note, 2026-07-26)
`run_gate.sh` now **builds `mister_vsim` from source every run** (Verilator `--build` is incremental — a
no-op when nothing changed, a correct rebuild when the RTL changed). This closes three defects that cost
~2h on 2026-07-26 and made a merge gate un-diagnosable:

- **No committed binary.** The old committed `obj_mister/mister_vsim` was **~50x slower** than a fresh
  build (case-0 delta: 240s+ timeout vs 11s fresh) despite the *recorded* verilate command being byte-
  identical — i.e. the build flags that made it slow were never captured. A committed binary nobody can
  attribute is the same provenance disease as the firmware drift above, one layer down. `obj_mister/` is
  now gitignored and rebuilt here. (What made the ~50x: an unoptimised compile, **not** tracing — the
  committed and a fresh binary carry the same trace-symbol count, so VCD linkage was not the cause.)
- **Re-verilate before every gate.** The gate used to run a *pre-built* binary and only rebuilt the 6502
  firmware (`dbg_build.py` → `copro_rom.hex`). The eval constants live in `LeafEval.sv` and are baked into
  `mister_vsim` at Verilator-compile time, so **editing `LeafEval.sv` and gating without re-verilating
  tested the STALE constants and passed green on the old eval** — a false green on exactly the change you
  made. Building from source here means an RTL edit is always what gets gated. (Verify a constant-only edit
  propagated by diffing the generated `obj_mister/…DepSet…cpp` *contents* — the partition-hash filename does
  NOT change for a constant-only edit.) NEVER glob the source list: `ALU.v`/`cpu.v` are the old Arlet core
  and collide with `copro_alu.v`/`copro6502.v` as duplicate module defs.
- **Visible progress + `clocks=` kept.** Output is line-buffered (the old `vsim | grep | sed > file` pipe
  was block-buffered — a 0-byte log hid all progress, so "is it hung?" was unanswerable). And the gate no
  longer strips `clocks=` (the GO→DONE master-clock search-cost counter — the single most diagnostic field
  the sim emits; a delta count materially exceeding base on the same board is a divergence). It is kept in
  the per-case log and in `/tmp/gate_{base,all}_full.txt`; the cell-exact diff runs on a move-only
  projection, since `clocks` legitimately differs base vs delta.

A fresh full-12 gate is ~2–3 min (base ~173s, delta ~116s), not the ~15 min the unoptimised binary took.
A kill mid-run leaves `copro_rom.hex` at whatever the last `dbg_build` phase wrote — check it before
assuming a dirty tree: `c87e60a1` means the kill landed after the delta rebuild (line "restore the SHIPPED
hex"); a base `412615b2` residue means it landed during the baseline phase. Rules for long jobs here:
- **Launch it fully detached** — `nohup ./run_gate.sh 12 > some.log 2>&1 & disown` — not as a tracked
  background task, so the harness's ~20-min background-task lifetime cap cannot reach it. Poll the logfile.
- **Never silently retry after a kill** — report it, and verify the hex is intact (`md5sum copro_rom.hex`
  == `c87e60a1`) first.

## History
- Delta engine landed cell-exact at `9e040e3` (2026-07-25); RTL + `dbg_build.py` + `USE_DELTA`.
- Shipped delta `c87e60a1` vendored to Pocket at `b7429de` from a `9e040e3-dirty` tree — never
  committed back to canonical, so the committed hex stayed at the base `412615b2` (fd8e495, 2026-07-22).
- Reconciled (this note + committed `copro_rom.hex` = `c87e60a1`) under the r47b5 eval build, 2026-07-26.
