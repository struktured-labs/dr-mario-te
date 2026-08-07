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

## Where this sits in the ladder

Fast sim for breadth, **co-sim to confirm the survivors**, hardware once. This farm is the
middle tier — not the research substrate. For *ranking* design A against design B, both
arms run under the same simulator and most fidelity error cancels; the fast sim does that
thousands of times faster.

So how much better is the co-sim, actually? Measured on 50 real-L11 boards against RTL
ground truth (`transfer_check.py`, costs no new RTL — it replays decisions the co-sim
already recorded):

| decider | agrees with real RTL on the full (col, orient) move |
|---|---|
| `fast_rtl_x.decide_ship_d3` | **38.0%** (col-only 46%, orient-only 62%) |
| py65 (`CANDIDATE_TIER3.md` §10) | 13.3% |

The fast sim is ~2.9x the proxy py65 is. **Read this as "how good a proxy", not "the fast
sim is wrong":** move agreement is a *lower bound* on ranking fidelity, because two
deciders can disagree per-move and still rank designs identically — that cancellation is
the whole argument for having a fast tier. What it does say is that neither is a
move-level oracle, which is why survivors get confirmed here.

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

### `DRTUCK=1` has never shipped, on any cart

All 67 cart manifests in the repo were scanned. `DRTUCK` appears in exactly two
(`boardhold-v6b`, `mister-human-studycounts-armed2fix`) and is `"0"` in both; every other
manifest omits it, which is also off. **The tuck executor has never run on silicon.** Every
tuck enumerator this project has built — v1, v3, BFS, tier-3 — has been publishing to a
mailbox no shipped cart has ever read.

### …and the shipped descriptors are mostly unperformable anyway

`descriptor_audit.py` replays each published descriptor against the board it was published
for (zero RTL cost) and asks whether the maneuver is possible at all: can the pill even
enter `best_col` at the published trigger row? On 50 real-L11 boards:

| firmware | published | coherent | blocked at trigger | lands deeper than a drop |
|---|---|---|---|---|
| tuck-v1 `e970e9ab` (shipped) | 26 | **11 (42%)** | **15** | **1 (4%)** |
| tier-3 `5d010f62` | 25 | **25 (100%)** | 0 | **15 (60%)**, mean **+3.3 rows** |

v1 is incoherent *by construction*, and `tuck_scan.py`'s own docstring predicts it: v1
enumerates over ALL target columns and keeps the globally deepest rest, while the driver
takes its destination from `best_col` — the two need not name the same column. The one
edge case that could fake this (`translate_ref` allows a vertical anchored at row 0, top
half clipped) rescues **zero** of the 15.

**Consequence: if a `DRTUCK=1` cart is ever built it must ship with tier-3 firmware.**
Enabling the executor with today's v1 would fire 15-of-26 unperformable maneuvers — exactly
the failure v1's own author warned about.

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

## The 2×2: what the whole tuck program is worth

`run_2x2.sh` runs firmware × cart-executor, all four arms on the **same seeds**, so every
delta is within-seed paired:

| | `drop` (today's cart) | `tuck` (a `DRTUCK=1` cart) |
|---|---|---|
| **s20b** `e970e9ab` | **A** the shipped champion | **C** executor on, v1 firmware |
| **s20t3** `5d010f62` | **B** ship tier-3 today | **D** the full program |

- **B − A** — value of shipping tier-3 onto today's cart. Expected ≤ 0: the cart has no
  executor, so a winning tier-3 tuck overwrites `best_col`/`best_orient` and is then
  plain-dropped, landing shallower than scored.
- **C − A** — the executor alone, with the firmware we already ship. Expected ≤ 0 for a
  different reason: 58% of v1's descriptors are unperformable.
- **D − A** — the full program (cart rebuild + tier-3). The number that decides whether
  months of tuck work ship.
- **D − B** — the executor's own value, firmware held fixed. Never measured before.

Pressure defaults to **bursty**, not clean: a 1,474-game census found the champion has ~0
failures on a clean L11 stream, so a clean arm can only measure speed (pills-to-clear),
never survival.

**Incoherent descriptors in `tuck` mode degrade to a plain drop** at `best_col` and are
counted separately (`n_incoherent`). This is deliberately conservative — on silicon the
pill keeps falling wherever the DAS hold left it and can land in a different column
entirely, so arm C's real harm is likely worse than measured here.

## Scope note

These are **solo L11 games**, matching the offline methodology of `firmware_tier3_ab.py`
(clear rate, pills, topout, dies-ahead). The physical rig ran a *VS duel* — P1 native-d1
vs P2 copro, with garbage exchange — and scored whichever side cleared first. The two
measure different things; do not read one as a replication of the other's absolute
numbers, only of the arm ordering.

**Caveat to keep prominent:** the finding that the flag confound between `12a0906b` and
`5d010f62` is empirically inert (0/20 boards) is a **mid-game** result. #47's stranded-half
term is an endgame effect (vc ≤ 8) that mid-game boards cannot exercise. Do not read
"0/20" as "the flags don't matter".
