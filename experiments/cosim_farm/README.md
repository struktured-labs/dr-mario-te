# Batched Verilator co-sim farm

Full Dr. Mario games in which **the real RTL makes every placement decision**, run many at
a time, on as many machines as you like.

The premise: "silicon-faithful" does not require silicon. `CoproDrMario.sv` +
`LeafEval.sv` + `copro6502.v` verilated *are* the logic the FPGA runs. py65 is not — it
agrees with the real RTL on **13.3%** of real-L11 base-search moves
(`CANDIDATE_TIER3.md` §10). So the fidelity problem and the throughput problem have one
answer: run the RTL, in parallel, everywhere.

Against the physical MiSTer this buys **paired seeds** (impossible on the cart, whose RNG
is boot-frame-count dependent), no wedges, no SD handling, and byte-reproducible results.

---

## The load-bearing finding: the deployed cart has no tuck executor

Checked before any measurement, because it decides what a tier-3 A/B can even mean.

`roms/manifests/latch-converged-native-probe.json` records the exact flags the deployed
probe cart was built with. **`DRTUCK` is not among them**, and
`patch_cartridge_copro.py` at that manifest's own commit (driver-nav `b3b9b402`, emitter
md5 `661ffa62…` — a byte-for-byte match to the manifest) defaults `DRTUCK` to `"0"`,
which compiles the executor out.

So the cart never reads `$5087`/`$5088`. It steers to `best_col` and plain-drops. The
tier-3 vocabulary can still change play, but only via a side effect: `tuck_v3.py:644-645`
overwrites `D_BC`/`D_BO` with a winning tuck candidate's target, so the pill is steered to
a tuck's column and then **plain-dropped** — landing at the straight-drop rest, not the
deeper cell the search scored. That is the hazard `tuck_scan.py`'s own docstring names
("publishing a tuck the executor cannot perform … strictly worse than no tuck").
Arm A's tuck-v1 never touches `D_BC`/`D_BO` (grepped: zero hits), so it is inert.

Hence two execution modes:

| mode | meaning |
|---|---|
| `drop` (default) | what the deployed cart does. Descriptor ignored. **Use for anything claiming to describe silicon.** |
| `tuck` | honours the descriptor. Prices what a `DRTUCK=1` cart would buy. |

---

## Validation gate

Nothing here should be believed until these pass. Each targets a specific way the harness
could be silently wrong.

| gate | what it proves | how |
|---|---|---|
| (b) agreement | the farm *wraps* the co-sim, it does not change it | `gate_agree.py` — same boards through `farm_vsim` and the stock `mister_vsim`; requires identical col, orient **and clocks** |
| (e) orientation | H/V and colour order are not swapped | `gate_validate.py` — `VAR_OF_O4` (recovered empirically from the pinned RTL node corpus) vs `RING_OF_O4` (read off `tuck_v3.py`'s `O4_TABLE`); two independent statements must agree on all 4 codes |
| (d) physics | `fall_from()` is validated physics, not a second opinion | `gate_validate.py` — must reproduce the faithful sim's `resting_position()` over thousands of (board, column, orientation) cases |
| (a1) determinism | same seed twice = same game | two fresh co-sim processes |
| (a2) **reuse** | no state leaks between games in one long-lived co-sim | same seed as 1st vs Nth game in one process — **the one that matters**, since workers reuse a co-sim across many games. Tests the defect, not the guard. |

`clocks` is compared in (b) deliberately: a move can match coincidentally while the search
took a different path, and `clocks` is the project's own most diagnostic field.

---

## Layout

    sim_farm.cpp     persistent co-sim server: one VCoproDrMario, decisions over stdin
    build.sh         verilates farm_vsim AND the stock mister_vsim from the same sources
    cosim.py         client + board encoding (link nibbles included). No Python decider.
    game.py          one full game: RTL decides, faithful sim does gravity/resolve/spawn
    run_farm.py      parallel runner over a seed range -> JSONL
    gate_agree.py    validation gate (b)
    gate_validate.py validation gates (a)(d)(e)
    analyze.py       paired analysis: McNemar + paired bootstrap
    deploy_node.sh   ship binary + firmware to another machine (no toolchain needed there)

## Arm selection is by working directory

`CoproDrMario.sv` does `initial $readmemh("copro_rom.hex", rom)` — resolved at **runtime**,
relative to the process CWD. So one binary serves every arm; the firmware is chosen by
which directory the process runs in, and `Cosim.fw_md5` records the hash of the file
actually opened. The arm is verified from content, never inferred from a filename. This
also sidesteps the `update_mif`-is-a-no-op-for-`$readmemh` trap entirely: there is no
synthesis step to be fooled.

## Firmware arms (all hashes reproduced locally)

| arm | recipe | md5 |
|---|---|---|
| `s20b` | `DRSTRAND=20 DRCOPRO_TUCK=1 DRCOPRO_ARM=1 DRFIX=1 DRCHAIN=180` | `e970e9ab…` — the shipped champion |
| `s20t3` | as above but `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` instead of `DRCOPRO_TUCK=1` | `5d010f62…` — **flag-matched**, the clean comparison |
| `s20t3flash` | `DRCOPRO_TUCKBFS=1 DRCOPRO_TUCKBFS_TIER3=1` only | `12a0906b…` — what CANDIDATE_TIER3 §11 recorded and vendored |

`s20t3flash` differs from `s20b` by tier-3 **and** the loss of `DRSTRAND=20` (#47
stranded-half) and `DRCOPRO_ARM=1`. §11 describes it as the full "M5 ship recipe"; §9's own
table lists the two-knob command, and the two-knob command is what reproduces the hash.
(`DRFIX`/`DRCHAIN=180` are no-ops on this path — verified by build.) Keeping it as a third
arm is what lets the confounded silicon comparison be interpreted rather than guessed at.

## Running

    ./build.sh
    python gate_validate.py --fast                       # instant checks
    python gate_agree.py <fw_dir> <hostdata.txt>         # agreement vs stock
    python gate_validate.py --fw <fw_dir>                # determinism (runs real games)

    python run_farm.py --arm s20b  --fw /mnt/data/drmario_cosim/fw/s20b \
        --out /mnt/data/drmario_cosim/results/ab.jsonl \
        --seed-start 0 --seed-count 100 --workers 6
    python analyze.py .../ab.jsonl --a s20b --b s20t3

Runs are **resumable** — existing `(arm, seed)` rows are skipped, so a killed job restarts
where it stopped instead of redoing hours of RTL.

## Scaling out

Shards are disjoint seed ranges. No shared state, no coordination, results concatenate.

`farm_vsim` is built `-O2` and deliberately **without** `-march=native` (measured: native
bought nothing, and would have pinned the binary to one CPU). It is therefore portable —
verified by running a decision on the Hetzner box, which has no verilator installed at
all. `deploy_node.sh` ships the binary plus firmware; the target needs no toolchain.

Memory is not the constraint: **~7 MB RSS per co-sim**, so 20 workers is well under 1 GB.
Cores are the constraint. `run_farm.py --per-worker-rss-mb` sets a hard `RLIMIT_AS` per
worker so a runaway dies with `MemoryError` instead of taking the machine down.

## Scope note

These are **solo L11 games**, matching the offline methodology of `firmware_tier3_ab.py`
(clear rate, pills, topout, dies-ahead). The physical rig ran a *VS duel* — P1 native-d1
vs P2 copro, with garbage exchange — and scored whichever side cleared first. The two
measure different things; do not read one as a replication of the other's absolute
numbers, only of the arm ordering.
