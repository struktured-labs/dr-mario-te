# GARBAGE-WINDOW COMPUTE — design document

**Lane:** task #117 (gw-design) · **Date:** 2026-08-18 · **Status:** design + feasibility
only. No RTL change, no cart build, no cloud spend was made for this document.

Every number below carries a label:
**MEASURED** (I computed it from real captured data or read it out of a build artifact),
**DERIVED** (arithmetic on measured/cited inputs, with the arithmetic shown),
**CITED** (established by an earlier lane; I did not re-run it).

Reproduce the tables with `experiments/gw_design/budget_table.py`.

---

## 0. The one-paragraph answer

The copro is idle for the whole garbage drop, and that window is worth
**0.16 to 5.3 champion decisions** depending on board height — not the "3–8 seconds of
free thinking" the idea started from, and **not remotely enough for H12**. H12 as
certified costs up to **300 champion decisions per intervention**, which is **56× the
largest window that ever exists**, 207× the window at h=12, and 620× at h=15.
The window is a *one-to-three extra searches* budget, not a rollout budget. Within that
budget exactly one thing is already built (DRPRESTART: re-search the projected
post-garbage board — mandatory, since 50.5% of argmax decisions flip on it ⚠ but see §2.1:
that number is both **out-of-regime and un-reproducible**, and no GO may rest on it), and exactly
one thing is newly affordable: a **2-candidate, 1-ply deepening of the top-2 tie**, which
fits on **52.4% of releases** at median search cost, rising to **63.5%** if truncated at
80% completion — which the RTL measures as costing **zero moves**. ⚠ Its trigger population
is **~0.48% of plies** once candidates are de-duplicated by resulting board — **4× smaller
than H12's 1.98% dose**, because 87% of "exact top-2 ties" turn out to be a placement and
its own 180° mirror (§1.6b). Power is therefore a live risk, not a reassurance. The decisive
screen still costs about **$4** and needs no hardware, and it is still the right next step —
but it is now screening a smaller population than this document originally claimed.

---

## 1. BUDGET TABLE

### 1.1 The currency, and why it is cycles

All budgeting is in **copro clock cycles**. A decision costs the same number of cycles on
MiSTer and on Pocket; only the cycles-per-frame conversion differs, and it differs by
1.57×. Quoting frames without naming the clock domain is what
`dr-mario-cosim-farm-turnbased` calls unfalsifiable — the same 33 M-cycle decision *fits*
the h=15 window in one domain and *misses* it in the other. So: measure cycles, convert at
the end, report both.

| constant | value | label |
|---|---|---|
| Window `W(h) = 264 − 16h` frames, h = shallowest garbage-hit column's stack height | — | CITED (`dr-mario-garbage-window-mechanics`; ROM-derived, emulator-verified 8/8) |
| NTSC frame rate | 60.0988 Hz | CITED |
| Pocket copro tap | 54.66935836 MHz → **909,658 cycles/frame** | CITED (PLL IP, a0d5190f lineage) + DERIVED |
| MiSTer copro tap | 85.909088 MHz → **1,429,464 cycles/frame** | CITED (PLL IP at build 7f6ba69) + DERIVED |

⚠ Derive cycles/frame from `HZ / 60.0988`; do not transcribe the rounded 909,650 literal
that appears in the older memo.

Three mechanical facts that constrain the trigger, re-confirmed by the mechanics lane
(ROM-derived, verified 8/8 on the real ROM in a real 2P VS game):

- **Volley SIZE is irrelevant.** 2-, 3- and 4-tile volleys on the same board all give the
  same window. Only `h_min`, the stack height of the *shallowest hit column*, matters.
- **The window is per-RECEIVER-PILL, not per-volley.** Garbage is buffered attacker-side in
  `p1/p2_attackSize` (`$0318`/`$0398`) and releases only when the receiver reaches
  `action_checkAttack` — strictly between the receiver's own pill lock and its next spawn.
  So the trigger fires on the receiver's clock, and the window always sits in the gap the
  copro is idle in anyway.
- At **h=16** the column is full to row 0, the garbage **overwrites row 0**, W = 24 f, and
  the following spawn tops the receiver out. That row of the budget table is describing a
  board that is already lost.

### 1.2 What one champion decision actually costs — MEASURED

Source: `/mnt/data/drmario_cosim/results/prestart_pilot.jsonl` — **1,500 real
per-decision copro-cycle costs** from the Verilator co-sim farm running the real champion
firmware (`fw_md5 e970e9ab0208cdbce1d39ed33e2f51ee`), 10 games, arm
`pilot_s20b_drop_bursty`. The `lat` field is `[raw_clocks, entry_row, max_h,
post_garbage, h_hit]`; `sum(lat clocks) == clocks` holds on every row.

| population | n | p10 | median | p90 | p99 | max |
|---|---|---|---|---|---|---|
| all decisions | 1500 | 37.7 M | **45.1 M** | 58.1 M | 72.1 M | 80.3 M |
| post-garbage only | 208 | 35.9 M | **41.8 M** | 50.5 M | 57.7 M | 62.5 M |

`C_median = 45.1 M cycles = 49.6 Pocket frames = 31.6 MiSTer frames`.

★ **Pipeline check.** The published shadow-latency pilot reports "median decision 49.6
silicon frames" from a completely separate script. My independent conversion lands on
**49.6**. And "base search only" comes out affordable on **89.4%** of releases at p90 cost
(§1.4) — reproducing the published `89.4% at h≤12` DRPRESTART headline from arithmetic
that never saw it. Two independent reproductions; the clock domain and the unit
interpretation are right.

### 1.2b ⚠ A 3× conflict over C, raised in review — RESOLVED, and the resolution is a live hazard

The mechanics lane challenged the whole table with a different figure: *"a warm depth-3
search is ~300 hooks = 150 frames (`patch_cartridge_copro.py:391`), so the window fits one
entire warm search only while h ≤ 7."* If that were right the base search alone would fit on
a minority of releases and this lane would be dead. Worth resolving, not averaging.

**The 300-hook constant is an orphan, and 150 frames is a stale-unit misreading of it.**

- The driver comment cites its derivation as `tmp/driver_slam/round1_repro.py` +
  `TEMPO_DESIGN.md` §2.3. **`round1_repro.py` contains neither the string "300" nor
  "hook"**, and **`TEMPO_DESIGN.md:119` states `T_s ≈ 60 f`**, not 150.
- 300 hooks ÷ **5 hooks/frame** = **60 frames** — exactly `TEMPO_DESIGN`'s figure. The
  constant was authored to encode ~60 frames, under the hook rate assumed at the time.
- The 2026-08-01 audit **corrected the rate to 2 hooks/frame** (measured, by tracing the
  single NMI call site) and rescaled the *wall-clock prose* around `FAST_HI` — but left
  `T_s` as a raw hook count. Read at the corrected rate, "300 hooks" now says 150 frames:
  **2.5× what it was calibrated to mean.**
- The file **warns about exactly this** at `patch_cartridge_copro.py:104-110`: several
  comments still assume ~5 calls/frame, they are "calibration prose, not measured", and
  should be revisited "before anyone RE-TUNES the hook-counted constants".

**Five independent measurements agree with each other and with the constant's original
intent, not with 150 f:**

| source | DONE latency | domain |
|---|---|---|
| this document, 1,500 decisions | median **31.6 f** (p90 40.6) | MiSTer |
| pair-latch co-sim, 69 real L11 boards | median **34 f**, max 60 | MiSTer |
| link-chain ship report, stomper180 | worst **57.2 f** of ~80 | MiSTer |
| **the emitter's own measured wall-clock**, `patch_cartridge_copro.py:403-411` | worst case **0.78 s = 46.9 f** | MiSTer |
| `TEMPO_DESIGN.md:119` — the constant's own cited source | **≈60 f** | — |

★★ **The clincher sits fifteen lines below the line that carries the error** (found by the
mechanics lane): *"MiSTer chain180 @ 85.909 MHz 0.78 s = 18% of threshold / Pocket chain180
@ 54.669 MHz 1.23 s = 29% (projected)"*. 150 f = 2.50 s would be **3.2× the file's own
measured MiSTer worst case** and would exceed even the Pocket projection — the reading is not
merely uncalibrated, it is impossible. Meanwhile 300/5 = 60 f = 1.0 s sits just above the
0.78 s worst case, exactly where a warm-typical figure belongs.

★ **Cross-check in the clock-free unit, which settles it with no domain argument at all:**
0.78 s at 85.909 MHz = **67.0 M copro cycles**, landing between this document's p90 (58.1 M)
and p99 (72.1 M). Two instruments, different arms (chain180 vs champion), agreeing in the one
unit that needs no clock assumption.

⚠ **Provenance note, because the citation was challenged:** both derivation files exist but
are **gitignored** (`.gitignore:27` → `/tmp/`), so a git-history search reports them absent.
They are at `dr-mario-mods-wt/driver-slam/tmp/driver_slam/round1_repro.py` and
`dr-mario-mods/tmp/tempo/TEMPO_DESIGN.md`. Checkable — but only by someone who knows not to
trust `git log` for them, which is its own provenance hazard.

⇒ **The budget table stands.** Two things must not be lost:

1. ⚠ **This is cross-lane contamination, not a local nit.** The prestart lane's modelled
   baseline timeline carries "`T_s` = 300 hooks warm depth-3" *alongside* its own measured
   49.6-frame median — one lane holding both numbers, inconsistently. A stale hook-counted
   constant has already propagated into a second lane's model.
2. ⚠⚠ **THE MATURITY GATE HAS NEVER FIRED ON ANY SHIPPED CART** (task #122 — stronger than
   "looser than intended", which is how I first filed it). At the measured worst case,
   0.78 s × 2 hooks/frame × 60.0988 = **93.8 hooks** (Pocket 1.23 s → 147.8), so
   `WDOGH2 = hooks >> 8 = 0` on both platforms. The gate is `CMP #FAST_HI(2); BCS mat_slow`,
   disarming only at ≥ 512 hooks = 4.27 s. **The disarm branch has never been taken**, so the
   "arm the slam iff the search was fast" semantics have never been exercised — and any A/B
   that thought it was testing them was testing nothing. Reaching the threshold needs ~2.9×
   the worst latency ever measured. Free confirmation with no silicon time: the driver stores
   `LAST_LAT = WDOGH2` at DONE in PRG-RAM at `$6173`; all zeros in any soak save-state closes
   it.
   ⚠⚠ **But `DRSLAM_MATURE=0` is NOT the equivalent no-op this makes it look like.**
   `MATURE = (FAST_HI > 0) and SLAM` (`:413`) also gates **`RECOMMIT`** (`:551`) — the
   converged-orient pair-latch fix, worth −15.8pp clear rate when absent — plus nine other
   sites, and the emitter's own note at `:431-434` says removing it pushes a branch out of
   range. The safe claim is *"the FAST_HI comparison never fires"*, **not** *"the two
   settings are equivalent"*. **Driver-lane item; flagged, not fixed here** — and not to be
   "fixed" by arithmetic, since the constants were tuned empirically on silicon and may be
   right for reasons unrelated to their stated derivation.

★ The general shape: **a hook-counted constant is a unit-bearing quantity whose unit was
later revised.** The audit that fixed the rate fixed the prose and not the constants, so
every consumer since has silently read them 2.5× long.

### 1.3 Window budget by board height — DERIVED

> ## ⚠⚠ THE `releases` COLUMN IS INVALID — WRONG VARIABLE. Recompute pending (task #124).
>
> **The co-sim farm logs `h_hit` as the MAX stack height over garbage-hit columns. The
> window formula needs the MIN.** `game.py:184` even states the reasoning — *"the tallest
> hit column sets the binding window"* — and it is backwards. A tile falls `15 − h`, so the
> animation ends with the tile that falls **furthest**, i.e. the one in the **shallowest**
> hit column: `W = 24 + 16(15 − h_min) = 264 − 16·h_min`.
>
> Measured on 446 real boards × 12 volley shapes (5,352 pairs): the logged variable gives
> median h **11** and W **88 f** where the correct one gives median h **4** and W **200 f** —
> **overstating h by 7 and understating the window by 112 frames**, with 42.5% of pairs
> pushed to h ≥ 13 against a true 0.0%.
>
> ⇒ **Every percentage in this section and §1.4 that is a share OF RELEASES is wrong**,
> including the **52.4%** that gates the recommendation and the 14.4% p90 figure. The
> **h-axis itself is correct** — `W(h)`, the cycle costs, and the budget columns are all
> sound; only the *distribution over h* is corrupt. **Direction is favourable**: true windows
> are longer, so real affordability is **higher** than stated here. Nothing is silently
> patched; the figures stand marked until recomputed from `h_min`.
>
> ⚠ The same field feeds the **published DRPRESTART "89.4% at h ≤ 12" headline**, which
> inherits the same defect.
>
> ★ **And it kills a validation I was proud of.** I cited reproducing that 89.4% "from
> arithmetic that never saw it" as evidence my pipeline was right. It was evidence of
> **agreement, not correctness** — two lanes computing from the same wrong field is a shared
> dependency wearing corroboration's clothes. Independent reproduction corroborates only when
> the *inputs* are independent, and here they were the same 5 bytes.

Pocket (the rematch venue). `budget` = how many whole champion decisions fit in the window.
`extra` = what is left after the **mandatory** post-garbage re-search (§2.1).
~~`releases` = share of the 208 MEASURED post-garbage decisions at that `h_hit`.~~ **INVALID,
see the box above.**

| h | W (f) | W (cycles) | releases | cum. | budget @median | budget @p90 | **extra @median** |
|---|---|---|---|---|---|---|---|
| 0 | 264 | 240.1 M | 1.0% | 1.0% | 5.32 | 4.14 | **4.32** |
| 2 | 232 | 211.0 M | 1.9% | 3.4% | 4.68 | 3.63 | **3.68** |
| 4 | 200 | 181.9 M | 7.2% | 14.4% | 4.03 | 3.13 | **3.03** |
| 5 | 184 | 167.4 M | 13.9% | 28.4% | 3.71 | 2.88 | **2.71** |
| 6 | 168 | 152.8 M | 13.0% | 41.3% | 3.39 | 2.63 | **2.39** |
| **7** | 152 | 138.3 M | 11.1% | **52.4%** | 3.06 | 2.38 | **2.06** |
| 8 | 136 | 123.7 M | 11.1% | 63.5% | 2.74 | 2.13 | **1.74** |
| 9 | 120 | 109.2 M | 10.1% | 73.6% | 2.42 | 1.88 | **1.42** |
| 10 | 104 | 94.6 M | 4.3% | 77.9% | 2.10 | 1.63 | **1.10** |
| 11 | 88 | 80.0 M | 7.7% | 85.6% | 1.77 | 1.38 | **0.77** |
| **12** | 72 | 65.5 M | 3.8% | **89.4%** | 1.45 | 1.13 | **0.45** |
| 13 | 56 | 50.9 M | 3.8% | 93.3% | 1.13 | 0.88 | **0.13** |
| 14 | 40 | 36.4 M | 2.4% | 95.7% | 0.81 | 0.63 | **— base itself doesn't fit** |
| 15 | 24 | 21.8 M | 2.4% | 98.1% | 0.48 | 0.38 | **— base itself doesn't fit** |
| 16 | 8 | 7.3 M | 1.9% | 100% | 0.16 | 0.13 | **— base itself doesn't fit** |

⚠ **Read the last column carefully** — a reviewer misread an earlier draft's `0.00` there as
"the window is zero at h ≥ 14". It is not: the *window* is 40 f at h=14 and 24 f at h=15
(the `W` columns), and at h=16 the column is full to row 0, the garbage overwrites row 0 and
the following spawn tops the receiver out. What is zero is the *extra* budget — because at
h ≥ 14 even the single mandatory base search does not complete, so there is nothing left over
by definition. The rows now say so instead of clamping to zero.

MiSTer's tap is 1.57× faster, so every budget column scales by 1.57 (h=0 → 8.36 decisions,
h=12 → 2.28, h=14 → 1.27). **MiSTer is a materially roomier machine for this feature** —
which matters, because it is the one with ALM headroom too (§5.1). Full 17-row tables for
both domains are in the script output.

### 1.4 Where the cliff is

| computation | cycles | Pocket frames | fits up to | affordable on… (@median / @p90) | label |
|---|---|---|---|---|---|
| (a) linear tail term, per-feature LUT in 6502 firmware — 19 terms × 32 candidates | 7.3 K | 0.008 | h ≤ 16 | 100% / 100% | DERIVED |
| (a′) same term in RTL beside LeafEval | 1.3 K | 0.001 | h ≤ 16 | 100% / 100% | DERIVED |
| base post-garbage re-search — **mandatory** | 45.1 M | 49.6 | h ≤ 13 | 93.3% / **89.4%** | MEASURED |
| (b) 2-candidate × 1 extra ply | 90.3 M | 99.2 | h ≤ 10 | — | DERIVED |
| **(b+) base + 2-candidate deepening** | 135.4 M | 148.8 | **h ≤ 7** | **52.4% / 14.4%** | DERIVED |
| (b+) at 80% truncation (see §2.4) | 117.3 M | 129.0 | h ≤ 8 | 63.5% / 41.3% | DERIVED |
| base + **1** extra candidate at 80% | 81.2 M | 89.3 | h ≤ 10 | 77.9% / 73.6% | DERIVED |
| (c) top-4 × 1 extra ply + base | 225.7 M | 248.1 | h ≤ 0 | 1.0% / 0.0% | DERIVED |
| (c′) **H12 as certified** — topk 4 × fork_samples 5 × horizon 15 | 13.5 **G** | 14,884 | **never** | 0% | DERIVED |

**The cliff is between (b+) and (c).** Two extra candidate-plies is the last thing that
fits on a majority of releases; four is the last thing that fits at all; the certified
rollout is off the chart by four orders of magnitude.

**Costing (c′), and why the conclusion is robust.** `oracle_arm.py:281-311` shows
`_fork_label` playing `horizon` pills forward, calling `_champ_values` — a full 32-candidate
root evaluation — once per pill. `oracle_arm.py:104-107` fixes `TOPK=4, HORIZON=15`;
`h12_arm.py:30-33` fixes `fork_samples=5`. So one triggered ply issues 4×5 = 20 forks
(confirmed MEASURED in the endpoint output: a game with `forks: 300` had 15 tie plies), each
of ≤15 champion decisions ⇒ **≤300 champion decisions per intervention**.
⚠ **What "champion decision" means here, precisely.** `_champ_values` is the *fast-sim*
mirror of the champion's move choice, not the firmware. The composition is nevertheless the
right one for a silicon budget: a rollout step requires the copro to *pick a move*, and a
copro move-pick is the thing measured at 45.1 M cycles. So "300 champion decisions" reads as
"300 copro move-picks", which is exactly what porting the rollout would cost. It is not a
claim that the Python function costs 45 M cycles.

⚠ The 300 is also an upper bound: forks terminate early on clear or topout, and the gate opens at a
median of 3 viruses, so the true mean horizon is shorter. **The bound's slack cannot change
the verdict** — even if the average fork ran only *one tenth* of its horizon, H12 would
still exceed the largest window that ever exists by **5.6×**, and the h=12 window by 20×.
Measuring the true mean horizon is a cheap refinement (§4.5) and a sign-preserving one.

### 1.5 Reading the table honestly

Three things this table says that are easy to get backwards:

1. ~~**The window shrinks exactly where the danger is.**~~ ⚠⚠ **REFUTED — and this was the
   lane's central pessimism.** The mechanics lane retracted it after measuring `h_min` on
   the same 125 real kill-game boards this document uses elsewhere:

   | on real near-death boards | |
   |---|---|
   | tallest column | median **15** (13-15) — genuinely near death |
   | **h_min (shallowest garbage-hit column)** | median **4** (0-13) |
   | **W = 264 − 16·h_min** | median **200 f = 3.33 s** |
   | boards at W ≤ 56 f | **4/125 = 3.2%** |
   | worst volley phase per board (adversarial) | median 136 f = 2.26 s |

   **Near-death boards are towers, so the garbage — which lands in spread columns
   ({c, c+4}, {c, c+2, c+4}, …) — almost always finds a low one, and one low column sets
   the whole window.** The near-death window is **~3.3 s, not the 0.93 s** the flat-stack
   synthetic implied; the short-window shape occurs in 3.2% of real deaths.

   ⇒ **The compute is abundant AND most valuable in the same regime**: ~3.3 s of window
   alongside the highest flip rate measured anywhere (66.3%, §2.1). Every "arrives where it
   is least needed" caveat in earlier drafts argued against a fact that is not true.

   ★ The error was mine and the mechanics lane's in the same shape, one level apart: I used
   *fill* as the axis for a *height*-keyed formula; they had the right per-column quantity
   (`h_min`) but described its behaviour with an aggregate ("as the board fills") and then
   reasoned about a regime from that aggregate. **A formula in a per-column quantity
   licenses no claim about a regime described by an aggregate.** Hence `h_hit` must be the
   **min over hit columns** — that single column sets the entire window regardless of the
   other seven.
2. **p90 is not a rounding error, it is the design question.** (b+) is affordable on 52.4%
   of releases at median cost and only **14.4%** at p90. Whether that gap is a problem
   depends entirely on the pre-emption semantics (§2.4): if an unfinished extra is
   abandoned cleanly, p90 overruns cost only wasted work; if a partial can be adopted, p90
   is where the pair-latch defect gets reinvented.
3. **The linear tail term is not a budget question at all.** At 7.3 K cycles it is 0.1% of
   even the h=16 window, so it is **free to run**. ⚠ But free is not the same as useful, and
   the budget side must not be used to re-open a closed lane: the distill verdict stands
   unchanged — as a decision-maker it peaks at **2.7% of H12's effective dose, 6.6× under
   the MDE**. Its admissible role here is **trigger / prior, never decision-maker**
   (§3.3). *Free to run, unproven to help.*

### 1.6 How big is the dose? — MEASURED, and it is the number the power calculation needs

A budget table says what *can* run. Whether an experiment can *detect* it depends on how
often it fires. Both halves are measurable from banked data.

| quantity | value | source |
|---|---|---|
| plies that are post-garbage decisions | **13.87%** (208 / 1500) | MEASURED — prestart pilot |
| plies with an exact top-2 champion-value tie | **18.88%** (234,198 / 1,240,445) | MEASURED — H12 endpoint, 9,000 games |
| **H12's own accepted-flip dose** | **1.98%** of plies | MEASURED — same |
| H12's accept rate at a tie (after the θ margin) | 10.5% | MEASURED — same |

★ **Third pipeline reproduction:** 1.98% recovers H12's published "~2.0% flip dose" from
its raw per-game counters.

⇒ Raw trigger population = 13.87% × 18.88% = 2.62% of plies, of which 52.4% are affordable
⇒ 1.37–1.66% of plies. **I published that as "the same order as H12's 1.98%, the
encouraging part of this document". ⚠⚠ IT IS WRONG, AND THE RETRACTION IS BELOW.**

### 1.6b ⚠⚠ RETRACTED — 87% of "exact top-2 ties" are the SAME PHYSICAL PLACEMENT

Found 2026-08-18 while gating the S0-A screen, **before** the registered run. The screen as
pre-registered would have measured almost nothing and returned a spurious CLOSE.

**MEASURED** (12 seeds, 2,085 plies, 359 post-garbage plies, champion under lulu pressure):

| observation | value |
|---|---|
| at a raw top-2 tie, the two candidates produce a **literally identical board** | **87.1%** (108/124) |
| tie events whose capsule is a **double** (`cur.a == cur.b`) | **89.5%** |
| top-2 landing in the **same column** | 91.9% |
| successor value spectra identical under max / sorted-vector / top-3 / mean | 94-96% |
| legal-move count identical | **100%** |

**Mechanism, and it is arithmetic, not a bug.** A Dr. Mario capsule is a double with
probability 1/3 (three colours, drawn independently). For a double, orientations 0 and 2 are
the same placement, and so are 1 and 3 — the capsule is symmetric under 180°. So the action
space collapses from 32 to 16, and every surviving placement appears **twice with exactly
equal value**. The "exact top-2 tie" predicate therefore fires overwhelmingly on a candidate
and its own mirror.

⇒ **A binary comparator over the raw top-2 is comparing a board with itself.** No amount of
deepening can discriminate; the boards are equal. This is the wrong-observable trap in its
purest form, and neither the non-vacuity check (n > 0) nor the M-D1/M-D2 mutants caught it —
they all passed while the instrument measured nothing.

**Corrected population — de-duplicate candidates by RESULTING BOARD, then test for a tie
among distinct boards** (MEASURED, same corpus):

| | of post-garbage plies | of all plies |
|---|---|---|
| raw top-2 tie, as originally registered | 39.8% | 6.86% |
| **de-duplicated top-2 tie (distinct boards)** | **5.29%** | **0.911%** |
| shrinkage | | **7.53×** |

⇒ **corrected trigger population = 0.911% × 52.4% affordable ≈ 0.48% of plies**, against
H12's measured **1.98%** accepted-flip dose. **The garbage-window comparator's trigger
population is ~4× SMALLER than H12's dose, not comparable to it** — and the *flip* dose is
strictly smaller still, since flips are a subset of triggers. The power argument I gave is
withdrawn; §6 now treats power as a live risk rather than a reassurance.
⚠ n = 19 de-duplicated tie events; the 5.29% is order-of-magnitude, the **7.53× shrinkage is
not in doubt**.

### 1.6c Three consequences that outlive this lane

1. **H12 itself is NOT invalidated, and the reason is worth recording.** Its trigger is the
   same raw predicate, so its `tie_plies` count is inflated the same way. But identical
   candidates produce **identical fork labels**, so the θ-margin gate (`margin_sum ≥ 3`)
   rejects them automatically. H12 self-protects; its certified effect stands. What is
   overstated is `tie_plies` **as a dose statistic** — anyone sizing a new arm from 18.88%
   (as I did) overcounts by ~7× for any top-2 comparator.
2. **A free tempo win, unrelated to this lane** (feeds task #114). For a double capsule,
   orientations 0/2 and 1/3 are the same placement — but **not the same cost to reach**:
   the executor is CCW-only, so orient 1 costs 3 rotations from spawn where orient 3 costs 1.
   Canonicalising double-capsule orientations to the cheapest-to-reach member is a pure
   tempo gain with **provably zero board effect**, which makes it about the safest change
   available anywhere in this project.
3. **De-duplication is nearly free on silicon — but I had the pairing WRONG.** I wrote
   *"skip orientations 2 and 3"*, reasoning that a double is 180°-symmetric so `o ↔ o+2`.
   ⚠ **False in this encoding, and the h13-gate lane caught it before it reached #123.**
   Their `(v, v+2)` detector found *nothing* — 1.1% on doubles vs 0.9% on non-doubles, no
   signal — while the board-level tie rate on those same doubles is **1.0000**. A de-dup
   that removes nothing reports "no contamination found", indistinguishable from a broken
   detector, and arrives wearing a green badge.

   **MEASURED instead** (413 double-capsule plies, 12 seeds, actions paired by *resulting
   board*): identical-board pairs are **var 2 ↔ var 3** and **var 0 ↔ var 1**, always same
   column — **adjacent** variants, slots differing by 8, never 16. With
   `_VAR_OF_O4 = [2,3,0,1]` that is orientations **o4 0↔1 and o4 2↔3**.

   The physics is more natural than my guess: **for a double, the two colour-orderings
   within each axis are the same placement.** Variants 0/1 are one axis's two orderings,
   2/3 the other's, and a double makes the ordering irrelevant. It was never about rotation.

   ⇒ still one byte compare and a branch — `if cur.a == cur.b`, keep one member of each
   *adjacent* pair — but **derive the pairing from boards, never read it off a constant**.
   `_VAR_OF_O4` looks like it answers this and does not.

⚠ **Three ways this could be optimistic, and they must not be waved through.**
1. **Size is not dose.** The distill lane's law is that dose must be weighted by *selection
   quality*: its safe linear rule fired at a nominally usable rate but carried only 2.7% of
   H12's effective dose because precision fell as fast as firing rose. One extra ply is a
   far weaker discriminator than a 15-pill rollout, so the per-flip quality here is unknown
   and is exactly what S0-A and Stage 1 exist to measure. **Do not quote 2.62% as a dose.**
2. **The two rates come from different corpora** — 13.87% from the prestart pilot (10 games,
   s20b, drop+bursty), 18.88% from the H12 endpoint (9,000 games, lulu). Multiplying them
   assumes ties are no rarer on post-garbage boards than elsewhere, which is untested. It is
   cheap to test directly and should be, since the product is load-bearing.
3. **The release rate is a property of the pressure model.** 13.87% is what dr. lulu's
   bursty injector produces. A different opponent produces a different number, and against a
   weak opponent this feature has almost no trigger population at all.

---

## 2. ARCHITECTURE SKETCH

### 2.1 What must happen, in order, and why the first step is not optional

The mailbox is `CoproDrMario.sv:26-36`: `$5000-$507F` board bytes, `$5080-$5083` capsule
colours, `$5084` W=GO / R=DONE, `$5085` best_col, `$5086` best_orient (P2's window is at
`$5200`, or `$5000` on Pocket where `DRPOCKET` relocates it).

```
volley release detected (6502, driver hook)
  │
  ├─ 1. project the SETTLED post-garbage board in 6502  ── already built (DRPRESTART)
  │      ⚠ RAM does NOT hold the settled board during the animation: gravity applies one
  │        row per 16 frames, so uploading $0500 at the release frame uploads garbage
  │        floating at row 0.  The 6502 must settle it itself.  CITED, and this is the
  │        defect dr-mario-garbage-floats-at-row0 already cost the project once.
  │
  ├─ 2. compute h_min and look up the BUDGET  ── new, ~10 instructions + a 17-byte table
  │
  ├─ 3. GO.  Base search on the post-garbage board.        cost 1 × C   [MANDATORY]
  │
  ├─ 4. if budget ≥ 3: deepen the top-2 tie by one ply.    cost 2 × C   [the new work]
  │
  └─ 5. publish ATOMICALLY into a shadow mailbox; the driver adopts at the spawn edge
```

Step 3 is mandatory because of the single largest measured fact in this lane:
**50.5% of argmax decisions flip between the pre-garbage and post-garbage board**
(n=200, champion mirror, CITED, gate floor ~2%). Letting the existing search run *longer*
on the stale board is wasted work half the time. Any implementation that spends the window
without first re-searching the projected post-garbage board is spending it on the wrong
board.

### ✅ CROSS-CHECK LANDED — the window profile is REGIME-GENERAL

The h13-gate flip-screen corpus (**446 mid-game flips**, median 15 viruses) run through the
near-death rig's own `h_min` definition, method-identical by construction:

| | tallest column | `h_min` median | W median | W ≤ 56 f |
|---|---|---|---|---|
| **mid-game**, 446 flips | 13 | **4** | **200 f** | **0.0%** |
| **near-death**, 125 kill boards | 15 | **4** | **200 f** | 3.2% |

Indistinguishable. **This fires pre-committed branch 1** (registered in §5.4 before the data
existed): ample windows are **regime-general**, and §1.5's retraction generalises well beyond
death boards. Worst-phase figures agree too (mid-game W 152 f vs near-death 136 f).

⚠ The h13-gate lane's stated prior was "regime-dependent" and it was **wrong** — they had
withdrawn their stake before the number landed, and said so unprompted. Their separate
*narrow-tower geometry* hunch was **right**: towers recur across regimes, which is exactly
why `h_min` stays low everywhere. Rig: `experiments/gw_design/hmin_screen_corpus.py`.

### ✅ RESOLVED — I published two defects here and BOTH WERE FALSE

**Earlier revisions of this section said the 50.5% was (a) out-of-regime and (b)
un-reproducible, and made the whole recommendation conditional on re-deriving it. Both
claims were wrong.** All three rigs exist, all three have now run, and **the effect survives
in every stratum measured — it is strongest in the near-death regime the lane targets.**

Recovered and committed to this branch at `experiments/gw_design/flip_rigs/`. They lived in
the **session scratchpad**, which is why repo-scoped and git-scoped searches missed them:

| rig | corpus | flips | rate |
|---|---|---|---|
| `gate.py` → `flip_result.txt` | 200 mid-game boards, all <45% fill | 101/200 | **50.5%** |
| `gate_hifill.py` → `hifill_result.txt` | seeds 300-699, drip garbage injected *during* play | 224/383 | **58.5%** |
| — of which fill 45-60% | | 33/62 | **53.2%** |
| `gate_neardeath.py` → `neardeath_result.txt` — **had no saved result; I ran it** | 125 real kill-game boards, **stack 13-16** | 67/101 | **66.3%** |

⇒ **The mandatory post-garbage re-search is justified across the whole playable range.**
50.5% / 58.5% / 66.3% against a 2% floor. The conditional framing is withdrawn.

### ★ 2.1b The near-death rig corrected my own stratifier — STACK HEIGHT ≠ FILL

`gate_neardeath.py` reports its own fill distribution: **median 36%, min 23%, max 46%** on
boards at **stack 13-16**. That is precisely the regime where the window is shortest — and
its **fill is LOW**, because near-death boards are narrow towers, not full boards. `W = 264 −
16·h` is a function of **height**, not of fill.

⇒ **`PREREG_S0A_v2` stratifies on the wrong variable.** The ≥60%-fill stratum its decision
rule is built around may essentially never occur in real play: boards top out from a tower
long before they fill. The screen must key on **`h_hit` / `max_h`**, the quantity that
actually sets the budget, with fill demoted to a secondary readout. The screen already logs
both; only the decision rule was wrong. Amended pre-data (v2 §C.2).

⚠ Also from that rig: **24 of 125** near-death boards were *instant-death-on-drop* — the
volley ends the game and no decision exists at all. Those plies are outside the reach of any
compute policy, and a "flip rate" over them would be meaningless.

### ⚠ 2.1c What I got wrong here, and the rule that comes out of it

I accepted a teammate's negative — "no artifact in any of 30 worktrees" — without re-running
it, while independently re-running two of their *other* claims because those contradicted me.
**That asymmetry is the error: I verified what threatened my position and trusted what
flattered my caution.** Their search tool was silently dead, but escalating it into this
document, the pre-registration, a task and a published page was mine.

★ **RULE: an absence claim needs a liveness-proven search AND an enumeration of what the
search cannot reach.** On this box that list includes at least: gitignored subtrees (`tmp/`,
where `TEMPO_DESIGN.md` was), the **session scratchpad** (where all three rigs above were),
NUL-containing files under the shimmed grep, and process-substitution inputs. *"I searched
the worktrees"* is not *"it does not exist"* — every artefact that mattered in this lane
lived outside them. This is now rule 8 of the project gate standard.

⚠ **The real risk was storage, not existence.** These rigs were one scratchpad cleanup from
being gone. They are committed now, and **#121 changes from "re-derive the number" to "keep
the rigs in the repo".**

### 2.2 Where results are latched — and not recreating the pair-latch defect

**Read `dr-mario-pair-latch-defect` before touching this.** The shipped defect is that
orientation and column are committed by two unrelated rules: orient latches at
`MIN_THINK = 25` hooks (`patch_cartridge_copro.py:381`, v8-wt @ 47707f9), column keeps
refining to DONE. The capsule played is *(orient of an early partial, column of the
converged search)* — a pair the search never scored. On real L11 positions that is **23.2%
orient disagreement**, rising to **39.1% in the endgame**, and modelling it full-game cost
**−15.8pp clear rate and +29 median pills** (all CITED).

The structural cause is not "the latch is too early". It is **that a two-field result was
sampled field-by-field across time.** Any mid-window publish reproduces it by default,
because the driver runs exactly **2 hooks per frame, both inside the NMI**
(`patch_cartridge_copro.py:104`) — so a publish that updates col in hook *N* and orient in
hook *N+1* is the identical bug with a new name.

**Design rule: the garbage-window result is a single atomic object, or it does not exist.**

Concretely, a **seqlock** in the shadow mailbox:

```
copro writes:   SEQ ← odd      (mark in-flight)
                COL, ORI, SRC  (SRC = which computation produced it)
                SEQ ← even+1   (publish)

6502 reads:     s1 ← SEQ ;  if odd → discard, use today's path
                COL, ORI, SRC
                s2 ← SEQ ;  if s2 ≠ s1 → discard, use today's path
```

This costs three extra bytes of PRG-RAM (allocate via `PRG_RAM_MAP.md`, which is the
derived authority for `$6000-$7FFF` — two lanes nearly collided there in one day) and about
a dozen 6502 instructions. It makes "a pair the search never scored" **unrepresentable**
rather than merely unlikely, which is the right standard given the history.

### 2.3 How adoption integrates with the existing decision path

At **h ≤ 12 — 89.4% of releases — the result is ready before the capsule spawns**, so no
mid-flight adoption is needed at all. The driver simply seeds `TGT_C2`/`TGT_O2` before the
spawn edge fires. This is much the safer path and it covers the large majority of cases.

At h ≥ 13 the result may arrive mid-flight. The mechanism to adopt a late orientation
already exists and is validated: `DRRECOMMIT` / `DRRELATCH` re-open `ROT_DONE2` at DONE so
`act_p2` rotates once to the converged orient (`patch_cartridge_copro.py:2138-2146`;
validated 0/100 stale vs 83/100 with the fix off). **My recommendation is nevertheless to
DROP the late result rather than adopt it** — see §2.4. The reachability race
(`dr-mario-pair-latch-defect`, the m3 autopsy) means a late column change can target a
column the capsule can no longer reach, and the executor is CCW-only and slam-oriented.
Late adoption re-opens a race the project has already paid for twice.

### 2.4 Pre-emption semantics — the hard requirement

> When the window closes early, degrade to the certified champion's move. Never a partial.

**Rule: an extra computation is abandoned WHOLE.** The `SRC`/`SEQ` pair is written only on
completion. If the spawn edge arrives first, the driver sees no valid shadow result and
re-GOes the ordinary spawn-edge search exactly as today. Two consequences worth stating:

⚠ **§6.3 amends this into a HEIGHT-DEPENDENT rule, and the amendment is the lane's main
near-death argument.** Abandon-whole is right below h = 13, where a complete search fits and
a partial therefore signals that something went wrong. At **h ≥ 14 it is the wrong default**:
the window buys only 0.16-0.81 of a search, so abandoning discards a result the measured
curve prices at **90-100% move fidelity**. Above h = 13 the rule becomes *adopt at ≥ 0.80
completion*, gated on a **completion counter, never a timer**, behind the same seqlock.

- **The OFF path becomes provably identical.** That is what made DRPRESTART safe to ship
  (byte-identical when unset, 12/12 flag arms plus whole-ROM hash both sides), and it is
  the property to reproduce.
- **Abandonment is not free.** With a search still ARMED at spawn, MATURE's
  lock-while-armed check disarms `SLAM_ARM` for that capsule (CITED, known DRPRESTART
  interaction). So a p90 overrun costs the slam — conservative, not dangerous, but it means
  the 52.4%-vs-14.4% gap in §1.4 has a real price and the budget should be set on the
  pessimistic side.

**A third option — and it is the single largest lever in this design.** The search commits
to its final answer early, because depth 3 is best-first over a depth-1 ranking: phase 0
scores every legal root move at depth 1, and the deep loop walks that shortlist in
descending shallow score, so it commits the shallow favourite immediately and spends the
rest confirming. If an extra search truncated at fraction *f* can be adopted rather than
dropped, its cost falls to *f* × C and affordability rises sharply.

★ **I initially wrote this up as an unmeasured assumption with an "unmapped middle". That
was wrong — the whole curve exists**, RTL-measured on 69 real boards on the shipped
`stomp180` arm (`dr-mario-qa-wt/experiments/rtl_chain/README.md:240-252`,
`TEMPO_BASELINE_37.md:110-125`). Combining it with §1.3:

| truncate at f | move agreement (MEASURED, n=69) | cost of base + deepening | affordable @median | @p90 |
|---|---|---|---|---|
| 1.00 | 100% | 3.0 × C | 52.4% | 14.4% |
| 0.80 | **100%** | 2.6 × C | 63.5% | **41.3%** |
| 0.70 | 98.6% | 2.4 × C | 73.6% | 41.3% |
| 0.50 | 95.7% | 2.0 × C | 77.9% | 63.5% |
| 0.20 | 82.6% | 1.4 × C | 89.4% | 77.9% |

**Truncating at f = 0.80 is free by measurement and nearly triples p90 affordability
(14.4% → 41.3%).** Going further to f = 0.50 costs 4.3% of moves and buys another 22pp at
p90. That is a real, priced knee, and it should be a knob.

Two things stop this from being vacuous, both from the same source: agreement at f = 0.05
is only **65.2%**, so the search genuinely does refine late on a third of boards — the
100%-at-80% is earned, not automatic — and the early convergence has a *mechanism*, which
is why it extrapolates to tail boards never sampled. It also **reconciles cleanly with the
pair-latch result**: 34.8% disagreement at f = 0.05 sits right beside the pair latch's
23.2%/39.1% at a comparable completion fraction. The two findings were never in tension;
they are the same curve read at opposite ends.

⚠ What is still genuinely open — and it is narrower than I first claimed: the curve was
measured for the **full depth-3 root search**, not for a 2-candidate deepening, whose
best-first structure differs. Re-measure it for the deepening (§4.2 S0-B) before setting f.
And note the source's own caveat: agreement is *move identity*, so 100% means zero cost, but
a disagreement would not imply a *large* cost — and it models "the answer changed", not
"the driver could still physically steer there".

### 2.5 Where the computation should live — and the trade this forces

| | driver (6502 in the cart) | copro firmware |
|---|---|---|
| NMI-overrun exposure | **adds to the hook**, which is the confirmed field-crash mechanism | **zero** — the 6502 only writes GO |
| A/B agility | rebuild a cart (seconds), swap on the SD card | **a full ~40 min Quartus compile per arm** |
| artifact identity | cart hash | core hash — and **the cart cannot see which core it is plugged into** |

**Recommendation: the extras live in copro firmware, issued by a single GO.** The 6502 does
the settle + budget lookup + one write, exactly as DRPRESTART already does; the copro loops
internally over the base search and the deepening. This keeps the host-side hook length
**unchanged**, which matters enormously given §5.2.

The cost is real and must be stated: `$readmemh` is resolved at synthesis, so
`quartus_cdb --update_mif` is a no-op and three differently-labelled arms produced one
identical `.rbf` (MEASURED, recorded in `CoproDrMario.sv` lines 96-112). Every firmware arm
is a full compile. And per `dr-mario-theta-is-core-not-cart`, a firmware-resident feature
becomes a **core** property the cart can neither see nor verify — the exact trap that made
"v8 + tuck at the validated dose" an artifact that could not exist.

⇒ **Mitigation, and it is new work worth doing regardless:** have the firmware expose a
**capability/version byte** in the mailbox that the cart reads at init. Then a cart can
refuse to enable a feature the installed core does not implement, instead of silently
running an inert executor or a wrong-dose arm. That single byte would have prevented the
θ150/θ400 pairing hazard outright.

---

## 3. TRIGGER POLICY

### 3.1 The window's trigger population is not H12's

H12's gate is `d_spawn_h >= 12 OR viruses <= 8`, and the census over 60,686 plies shows it
is **overwhelmingly an endgame gate**: `viruses<=8` is involved in 89.6% of opens, and the
height clause fires *alone* on only **5.7% of plies** (CITED). It is tempting to reuse it.

**Do not.** The garbage window fires on *volley releases*, not on plies — a different
population with a different base rate and, critically, a **budget that varies with h**. The
right gate is the one that answers the question actually being asked: *can I afford the
extra work, and would it change anything?*

### 3.2 Recommended: a budget gate plus the free tie predicate

**Always spend the window on the base post-garbage search** (that is DRPRESTART, already
priced and built). Spend it on *extras* iff both:

1. **BUDGET.** `N_extra(h) ≥ 2`, read from a 17-byte ROM table indexed by h. h is known at
   the release frame — the deadline is exactly predictable there, from the row-0 write and
   the column heights, in about ten 6502 instructions (CITED). This is what lets the search
   be **budgeted rather than merely started**, which is precisely what the pair-latch
   history demands.
2. **TIE, over DE-DUPLICATED candidates.** The top-2 values are exactly tied *after*
   collapsing actions that produce the same board. H12's flip provenance is 100%
   champion-value ties with ranks `{1: 1580, 2: 21273, 3: 1767}` (CITED) — the mass at rank
   2 is why a **2-candidate binary comparator** is the right shape and top-4 is mostly
   wasted budget.
   ⚠⚠ **The de-duplication is not an optimisation, it is a correctness requirement**
   (§1.6b): 87% of raw top-2 ties are a placement and its duplicate, so an un-de-duplicated
   comparator spends the whole window comparing a board with itself. On silicon it costs one
   byte compare on `cur.a == cur.b` — but see §1.6c item 3: the pair is **adjacent
   variants** (o4 0↔1, 2↔3), **not** `o ↔ o+2`, and that must be derived from boards rather
   than from the orientation constant.

This gate is deterministic, computable on-cart, costs nothing, and has no learned component
to mis-calibrate.

### 3.3 If a learned trigger is ever added — the operating-point discipline

The distill lane's 19 lock-time accumulators (8 per-candidate deltas + 11 running-state
context terms; `temporal_accum.py:42-52`) are the natural candidate trigger, and they meet
a real silicon contract: small integers, updated at lock time only, strictly causal,
computable from the candidate's post-board (`temporal_accum.py:13-24`). At 7.3 K cycles
they are free (§1.4).

⚠⚠ **BOUNDARY WITH THE CLOSED DISTILL LANE, so nobody re-litigates it from the budget
side.** That the term is free to *run* says nothing about whether it *helps*. The distill
verdict is unchanged and binding: as a decision-maker the safe linear rule carries **2.7% of
H12's effective dose, 6.6× under the MDE**, and the A/B is registered DO-NOT-LAUNCH. Its
only admissible role in this design is as a **trigger or prior over which plies deserve the
window's compute** — a job where firing rarely and imprecisely is tolerable because the
*decision* is still made by real search. **Free to run, unproven to help. It must never be
promoted to decision-maker on the grounds that it costs nothing.**

Three rules apply, all paid for in blood by that lane:

- **No AUC without the operating-point table.** Report realized value (mean true margin of
  the picks) and tail risk (% of picks ≤ −3) **at the actual firing rate**, plus precision
  against the base rate. AUC misled that lane three times in one night, including once by
  *understating* a usable rule.
- **The safe rule is a dose limiter, not a value source.** The best operating point found
  was ridge-on-signed-margin at **+1.04 mean margin, 0.5% dose, 0.07 tail** — genuinely
  safe, and peaking at **2.7% of H12's effective dose**. Used as a *trigger* for real
  compute that is 100× cheaper than a rollout, that same weakness is fine. Used as a
  *substitute* for the compute, it is 6.6× under the MDE.
- **Compute the MDE before launching.** An experiment that cannot detect is not an
  experiment.

⚠ And note the structural warning in `temporal_accum.py:18-27`: the 11 running-state terms
are candidate-**invariant** and cancel exactly to zero in any differenced scoring. They must
enter as undifferenced event-level context. Getting that backwards produces an arm
mathematically guaranteed to score 0.5, which would read as a refutation of the idea.

---

## 4. VALIDATION PLAN

### 4.1 The blindness, stated precisely — and the decomposition that gets around it

The co-sim farm **has no time axis**: `game.py`'s loop is per-pill, the board freezes during
`cosim.decide()`, and per-decision `clocks` reaches the JSONL as a report-only field that
never converts to frames (CITED, verified by `command grep` over every farm `.py` and
`sim_farm.cpp`). Worse, `inject_bursty_garbage` settles the volley to fixpoint *inside* the
same placement step, so **the farm baseline is secretly a perfect prestart already**. A
naive ON/OFF A/B of anything timing-shaped returns zero by construction.

**The way through is to stop asking the farm a joint question.** The shippable effect
factorises:

> shippable effect = **P(the extra compute completes | h)** × **value(the move it produces | granted)**

- The **left factor** is a pure timing question. It is answered by §1.3 plus the
  shadow-latency instrument, both of which already exist and are already validated
  (selftest + 4 killed mutants).
- The **right factor** is a pure decision-quality question with no timing content at all.
  **The farm can measure it honestly**, by granting the extra compute unconditionally at
  every triggered ply and comparing outcomes.

★ The key point that makes this lane priceable where DRPRESTART was not: the farm's
prestart bias hits **both arms identically**, because both arms play from the settled
post-garbage board. The bias that voided the DRPRESTART A/B is a *common-mode* term here
and cancels. Set the base arm to the champion-on-settled-board (which is what the farm
already plays) and the treatment arm to champion + deepening, and the comparison is clean.

⚠ The factorisation assumes independence between completion and value — that the boards
where the extra completes are not systematically the boards where it is worth less. That is
**not** obviously true (completion correlates with low h; value may correlate with high h),
and it must be checked by reporting the right factor **stratified by h** rather than pooled,
so the product can be formed h-by-h.

### 4.2 Stage 0 — the screens that can close the lane for ~$0

Both run on banked data; neither needs hardware or the farm.

- **S0-A · argmax-flip of the deepening.** On a corpus of real post-garbage boards, compare
  `argmax(champion)` with `argmax(champion + 2-candidate deepening)` at tie plies. If the
  flip rate is **below ~2%, close the lane** — below that floor an arm is untestable and a
  null means nothing. ⚠ Note this is a *different* flip from the 50.5%: that one measured
  pre- vs post-garbage *board*; this measures base vs deepened *search* on the same board.
  The 50.5% is a good prior for the lane existing, not evidence for this number — and per
  §2.1 it is itself un-reproducible, so S0-A should **re-derive it** at proper fill with a
  committed rig while it is in there.

  Three by-products to log while it runs, each of which closes a gap in this document at
  zero marginal cost:
  **(i)** the **tie rate on post-garbage boards specifically** — §1.6's dose estimate
  multiplies two rates from different corpora and this is the direct measurement;
  **(ii)** the **h_hit distribution on a proper corpus**, replacing §1.3's n=208 from 10
  games; **(iii)** per-flip provenance — ply index, `t_to_end`, champion rank chosen,
  first-divergence marker. That last one is not optional: Stage 2 spent 15,000 games to
  reach a NO_GO with **zero mechanism**, because `flips` was logged as a bare integer.
  Per-ply flip provenance is mandatory for every arm now.
- **S0-B · the truncation curve for the deepening** (§2.4). Move agreement vs
  fraction-of-cycles-completed at 5/20/50/70/80/100%, replicating the existing 69-board
  root-search protocol on the 2-candidate deepening. The root-search curve is already
  measured and free at f = 0.80; this checks it transfers, and sets f. It is worth up to
  **27pp of p90 affordability**, so it deserves its own measurement rather than an
  extrapolation.

### 4.3 Stage 1 — the farm A/B, priced

Granted-compute arm vs champion, paired seeds, **stratified by h**, pre-registered.

- **N:** the standing constraint is **≥ 7,826 paired seeds, register 9,000** (task #106).
  Independently, Stage 2 showed that at ~2% ply flip rate the paired clear-rate CI half-width
  is ±1.58pp at N=3,000, making a +1.0pp non-inferiority margin **unreachable by
  construction** — so 9,000 is a floor, not a target.
- **Cost:** the arm is nearly fork-free. Re-certifying a fork-free arm at N=9,000 is
  ~30 core-h (CITED); the deepening adds ~2 searches at maybe 10–20 triggered events per
  game against ~110 plies, i.e. **+20-30%** ⇒ **~40 core-h ≈ $4** at the measured
  $0.101/core-h. Compare H12's endpoint at ~$135. **This is a cheap decisive experiment,
  and that is the main argument for running it.**
- **Endpoint:** dies-ahead primary, clear-rate non-inferiority co-primary. Measure on
  dies-ahead, not clear rate — clear rate was blind to a 7.3× effect once already
  (p=0.19 vs p=1.6e-4).
- **Dose-matched null:** mandatory. Stage 2's headline died precisely here — a
  **label-blind LUT with row-permuted tables, scaled to match the fitted arm's flip rate,
  did just as well** (DiD −0.27pp). Any arm that cannot beat a dose-matched random
  perturbation of the same size has not shown direction, only churn.

### 4.4 Stage 2 — Mesen, then silicon

Mesen is frame-accurate and is the right instrument for the *mechanism*, not the value:
the seqlock, the pre-emption path, and the NMI hazards. This is not speculative — the
prestart autotest's Mesen gate is what **found both trace-proven NMI-overrun hazards, and
it failed correctly without ever touching hardware**. Mapper 100 does not run on Mesen; use
the proven routes (mapper-1 twin build with the copro window reading open bus, or
`tmp/prestart_gate/prestart_gate.lua`'s mailbox emulation, which already implements a
two-sided fire classifier, projection compare, an interleave instrument and crash canaries).

⚠ Mesen fails three silent ways (stale .NET mutex, Xvfb dying after one launch, rc=134);
**verify the log's tag on every arm — a missing log from any arm voids the batch.**

Silicon last, and only behind a hash of the cart that actually booted (a 17.9 h soak once
measured a stale pre-v6 cart through a silent MGL fallback, and produced three "new bugs"
that were one already-fixed defect).

### 4.5 What a killed-mutant gate looks like for a timing feature

The standard is that **a check must fail on wrong inputs**. Timing features make this harder
because the farm cannot see time — so each mutant must be paired with the observable that
*can* see it. Pairing them wrongly produces a mutant that survives correctly and teaches
nothing (`m_no_deepcopy` survived 0/12 because the property it guarded was not an
action-sequence property at all).

| mutant | what it breaks | observable that must kill it |
|---|---|---|
| **M1** budget ignored — always issue 2 extras | the h-dependent budget | shadow-latency projection: window-overrun rate at h ≥ 10 must jump from ~0 to ~100% |
| **M2** partial adopted — publish without waiting for completion | pre-emption | replay determinism: the adopted move matches neither the champion's nor the completed extra's |
| **M3** seqlock removed — write col and orient in separate hooks | atomicity | **cell-for-cell replay** (forced-move / census harness): must reproduce a (col,orient) pair the search never scored |
| **M4** pre-emption inverted — keep the stale target instead of re-GOing | degradation | stale-move signature; the shadow-lat lane's stale-move mutant was killed 3/3, so this observable is proven |
| **M5** trigger inverted — fire extras only at h ≥ 14 | trigger policy | completion rate collapses to ~0; the arm must become behaviourally identical to the champion |

Two gate-design rules from recent lanes apply directly. **Gate the object that actually
runs, not its parent** — `gate_h13.py` certified `H13Arm` while every screen game was played
by a forking subclass that was never gated. And **a logger that never fired proves nothing**:
require `events > 0` in every gate assertion.

Also fix the known hole while building: the shadow-latency comparison key uses `.get()`, so
a missing field compares `None == None` and passes silently — `moves` was absent from all 9
gate rows, making a five-field key effectively four. **Assert every key field is present in
both files before comparing.**

### 4.6 Effort

| stage | effort | cost | can it close the lane? |
|---|---|---|---|
| S0-A argmax-flip screen | ~0.5 d | ~$0 (local, banked boards) | **yes — a flip < 2% closes it** |
| S0-B truncation curve | ~0.5 d | ~$0 | no, but sets the design |
| Stage 1 farm A/B, N=9,000 | ~1 d setup + ~1 d wall | **~$4** | **yes, both directions** |
| Mesen mechanism gate | ~2 d | $0 | no — mechanism only |
| firmware + seqlock + Quartus | ~3 d + 40 min/arm | $0 | no |
| silicon soak | ~1 d | $0 | confirmatory |

---

## 5. RISK REGISTER

### 5.1 Fit headroom — and the constraint it imposes

| target | ALM | free | source |
|---|---|---|---|
| **Pocket, deployed strand20** | **18,262 / 18,480 = 99%** | **~218 ALMs (1.2%)** | MEASURED — `pocket-nes-mapper100/staging/strand20_20260808/INSTALL.txt:99` |
| Pocket, r47b2 seed8 build | 17,640 / 18,480 = 95% | 840 | MEASURED — `output_files_r47b2_seed8/nes_pocket.fit.summary:8` |
| MiSTer, shipped stomper180 | 37,249 / 41,910 = 88.9% | 4,661 (11.1%) | CITED |
| MiSTer, single-copro speed baseline | 36,467 / 41,910 = 87% | 5,443 | CITED |

⇒ **HARD CONSTRAINT: on Pocket this feature must cost 0 ALMs.** 218 spare ALMs is inside
fitter-seed noise (the link-chain lane measured 628 ALMs of seed noise on that device), so
"it might fit" is not a plan. The design in §2 satisfies this by construction — the extras
are *re-invocations of the existing search* plus a 17-byte ROM table and a seqlock, all
6502. **Nothing in this design requires new RTL.** Any variant that does is MiSTer-only and
therefore cannot ship to the rematch venue, which is currently the Pocket.

Two Pocket-specific traps that have each already cost a lane: `DRPOCKET=0` leaves P2's
mailbox at `$5200` reading **open bus**, and area-squeeze qsf settings inherited from a
different config silently traded 26 MHz of Fmax. A single-copro build **must** use SPEED
settings.

### 5.2 NMI overrun — the highest-severity risk on this page

Two trace-proven hazards fire when an NMI hook runs long, both cart-real:
(1) an overrun vblank NMI fetches `$FFFA` while the driver bank is mapped and re-enters
driver main **unguarded** → stack corruption → KIL; (2) the base game's 5-write MMC1 CHR
sequence gets straddled by a long hook, the shared shift register completes with mixed bits,
bank 0 is mapped mid-hook → **full RAM wipe → title screen**. Mechanism 2 is **confirmed on
ship bytes** as the root cause of the 2026-08-09 field failure (straddle ↔ bank0-entry ↔
wipe correlate same-frame 2/2, with a clean 0/0 control), and the corrupt title's
consecutive tile indices corroborate it independently.

The load-bearing sentence for this lane: **`DRHOLDBOARD` was the *trigger*, not the cause —
it merely lengthened the hook — and any hook-lengthening flag re-arms it. `DRPRESTART` is
already exactly such a flag**, with an 11.9 K-cycle release-edge spike = **40% of a
29,780-cycle frame**, the largest single-hook spike in the driver. **No shipped cart uses
reset-before-sequence discipline.**

Three requirements follow, and I would treat the first as blocking:

1. **The NMI fix spec must land before this feature, not with it** — (a) driver bank gets
   its own NMI/IRQ vectors with an in-bank RTI stub, (b) `_sel` writes the `$80` reset bit
   before *every* 5-write sequence, making it self-aligning. Both are drafted and neither is
   shipped. Building a hook-lengthening feature on top of a confirmed, unfixed field crash
   is the wrong order.
2. **Put the extras in firmware, not the driver** (§2.5), so host-side hook length is
   *unchanged* and the feature adds **zero** new overrun exposure.
3. **⚠ Ask whether the fix you just made caused the new bug.** The two NMI fixes brick each
   other if shipped naively — the bit-7 reset forces PRG mode 3, and `INC $FFF0` is a trap.
   **Gate the combination, not the parts.**

### 5.3 Flag interactions

`DRPRESTART × DRTUCK` is a **wedge pair**: 1/0 gives 83 pills, 0/1 gives 171, **1/1 gives 9
pills and hangs** — neither flag is at fault alone, and the obvious suspects (`DRDISTGATE`,
`DRNAVESC`, `DRMMC1RST+DRRTIVEC`) were all measured and refuted. A new garbage-window knob is
an *extension of DRPRESTART*, so it inherits that interaction and must be gated as a matrix,
with a killed mutant on each pair, not as a single flag.

⚠ Two follow-on facts that constrain where this can ship: turning `DRPRESTART` off in the
full `m-v8auto` flag set **does not assemble** (a 6502 relative branch goes out of range), so
tuck-enabled CvC carts must be built *up* from the `7611d54b` base; and since a tuck CvC cart
must ship `DRPRESTART=0`, **the garbage-window feature and the tuck executor cannot coexist
on that cart line at all.** That is a real product fork, not a build detail.

Finally: **default OFF and byte-identical when unset**, verified by whole-ROM hash on both
sides across every flag arm — the standard DRPRESTART met (12/12 arms) and the one to
reproduce. Pin `DRBUILDID=0` when hashing, or default-on stamps decouple the artifact from
the recipe.

### 5.4 Measurement risks specific to this lane

- ★★ **The 50.5% argmax-flip is un-reproducible AND out-of-regime** (§2.1) — no artifact in
  any worktree, and every board below 45% fill. This is the single biggest evidence risk on
  the page. The value case for the whole
  lane currently rests on a stratum that excludes the regime the lane is aimed at.
- **The h_hit distribution in §1.3 is n=208, from 10 games, one arm, one level.** The
  decisive cells at h ≥ 13 hold 4–8 observations each. Treat the release-share column as a
  scale, not a rate. **This is now the single weakest distribution in the budget table** —
  every "% of releases" figure inherits it.
  ⏳ **Cross-check pending, at zero marginal cost:** the h13-gate lane stores both board
  planes per screened flip, so `h_min` is recomputable post-hoc over its v2-only corpus
  (~420 flips, a **mid-game** population at median 15 viruses) with no re-run. Two
  independent `h_min` distributions from different regimes — near-death and mid-game —
  would replace this n=208 with something quotable as a rate. Requested; expected with
  their verdict.
  ⚠ **Pre-committed reading, so the result cannot be rationalised afterwards:** if the
  mid-game distribution resembles the near-death one (median `h_min` ≈ 4), ample windows
  are regime-general and §1.5's retraction generalises beyond death boards. If it differs
  materially, window length is **regime-dependent** and every release-share percentage in
  §1.3-1.4 is under-powered and must be re-derived per regime before being quoted as a rate.
- **TRUNCATION TRANSFER — treat as an ASSUMPTION, and the recommendation does not depend on
  it.** The agreement-vs-completion curve is measured (n=69, 100% at f=0.80) but **for the
  full depth-3 root search**, not for the 2-candidate deepening, whose best-first structure
  differs. It is worth ~27pp of p90 affordability, which is precisely why it must be earned
  rather than extrapolated. **Gate:** S0-B replicates the 69-board protocol on the
  deepening at f = 0.05/0.20/0.50/0.70/0.80/1.00 and sets f from the result; until then the
  go/no-go arithmetic uses **52.4%**, the untruncated number (§6.1 Step 3). ⚠ I first wrote
  this risk up as "unmapped" and was wrong — check whether the measurement exists before
  pricing something as unknown; the correction is in §2.4.
- **A corpus that never reaches the regime under test is not a bound, it is a different
  experiment.** The prestart lane published a 69%-fire figure that was an artifact of a
  random-play corpus topping out below the injector's own threshold. Before quoting any
  proxy corpus as conservative, check it can *reach* the regime.

---

## 6. RECOMMENDATION

### 6.1 What to build, smallest first

**Ship nothing yet. Run one $4 experiment.**

The design is settled enough that the open question is no longer *how* but *whether*: does
two extra candidate-plies at a tie change the outcome? Everything else — the seqlock, the
budget table, the firmware placement, the flag matrix — is engineering that is worth doing
only if that answer is yes, and all of it is cheap once it is.

⚠ **THE RECOMMENDATION IS CONDITIONAL, AND ON AN OPEN DEPENDENCY.** Step 3 of §2.1 — the
post-garbage re-search that everything else sits on top of — is justified by a 50.5%
argmax-flip that is **un-reproducible and measured entirely below 45% board fill** (§2.1).
Read every step below as: *if the flip rate survives re-derivation at high fill, then…*
**If it does not survive, the lane closes at Step 1 and nothing further is owed.** The
dependency is marked OPEN, not assumed, and S0-A re-derives it as a by-product.

**Step 1 (today, ~0.5 d, $0): S0-A, the argmax-flip screen — and the re-derivation.** Base
vs 2-candidate-deepened argmax on post-garbage boards at tie plies, plus a committed rig
that re-measures the pre-vs-post-garbage flip at proper fill. **A deepening flip rate below
~2% closes the lane for the cost of an afternoon**, and a pre-vs-post flip that does not
survive at high fill closes it just as decisively. Run S0-B (the truncation-transfer curve)
alongside; it is the same corpus.

**Step 2 (~2 d, ~$4): the farm A/B with compute granted unconditionally**, base and
treatment both on the settled post-garbage board, paired, N=9,000, stratified by h,
dose-matched label-blind null mandatory, dies-ahead primary. This measures the **value
ceiling**.

**Step 3 (analysis, $0): multiply by the completion curve.** The shippable effect is at most
**52.4%** of the ceiling at median search cost — and only **14.4%** if p90 costs must be
respected. **Use 52.4%; do not credit the truncation lever here.** It would raise the
figure to 63.5% (and p90 to 41.3%), but it depends on a transfer that S0-B has not yet
measured, so the go/no-go arithmetic must stand without it and treat any lift as upside.
**Fold the discount into the MDE before launching Step 2, not after.** If ceiling × 0.524
lands under the MDE, the honest
outcome is a registered DO-NOT-LAUNCH, exactly as the distill lane produced. That is a
success of the process, not a failure of the idea.

**Step 4 (only if Steps 1–3 clear): build it.** Firmware-resident extras behind one GO,
seqlock shadow mailbox, 17-byte budget table, abandon-whole pre-emption, default OFF and
byte-identical when unset, five killed mutants (§4.5), Mesen mechanism gate, then silicon —
**after** the NMI fix spec lands.

### 6.2 The three claims the owner should push back on

1. **"H12 will never fit in the window."** This is the load-bearing negative result and it
   rests on an upper bound (≤300 champion decisions). The bound is loose, but it has ~56× of
   slack against the largest window and 207× at h=12, so no plausible tightening changes
   it. If the owner wants the tight number, §4.5's cheap fork-horizon measurement gives it.
2. **"The window is a 1–3 search budget, not a rollout budget."** If that reframing is
   accepted, the whole lane's ambition should be reset from "gated depth-4 / gated H12" to
   "a binary comparator at a tie" — a smaller idea, but a shippable one.
   ⚠ **And it is smaller than this document first claimed.** The tie population it aims at
   is ~0.48% of plies once mirrored placements are removed, **4× under H12's dose** (§1.6b).
   A reasonable push-back is: *is a comparator over 0.48% of plies worth building at all?*
   My answer is that Step 1 costs an afternoon and settles it, and that the same
   de-duplication finding pays for the lane on its own via the free tempo win (§1.6c) —
   but if the owner would not fund a 0.48%-dose arm even at a good flip rate, **say so now
   and close the lane before Step 2**, not after.

**⚠ POWER IS NOW A LIVE RISK, AND IT SHOULD GATE STEP 2.** The withdrawn version of §1.6
was the reassurance that this arm was "plausibly powered rather than a formality". With the
population 4× smaller, that reassurance is gone. Before spending the $4, redo the MDE against
the corrected dose (§6.1 Step 3), and apply the distill lane's law directly: **an experiment
that cannot detect is not an experiment.** If ceiling × 0.524 × (0.48/1.98 relative dose)
lands under the MDE at N = 9,000, the correct output is a registered DO-NOT-LAUNCH — and that
outcome is now more likely than it looked this morning.
3. **"The prize is where the window is longest, not where the danger is."** ⚠ **I wrote
   that, and §6.3 partly overturns it.** 89.4% of releases land at h ≤ 12 with room to
   spare, and at h ≥ 14 the window is shorter than a *complete* depth-3 decision. But those
   boards flip at **66.3%**, and §6.3 shows a **truncated** re-search fits there at 90-100%
   move fidelity. The honest version is narrower: a *complete* search does not fit near
   death; a *usable* one does.

### 6.3 ★ The tension the team lead named — and it resolves in the lane's favour

> *"h ≥ 14 can't afford even the base search, yet flips 2-in-3."*

That is the sharpest objection to this lane, and the truncation curve answers it. Dividing
the window by the measured decision cost gives the completion fraction the near-death regime
can actually buy; the RTL agreement curve says what that fraction is worth. Pocket tap,
`C_median` 45.1 M and `C_p90` 58.1 M:

| h | W (f) | f at median cost | agreement | f at p90 cost | agreement |
|---|---|---|---|---|---|
| 13 | 56 | 1.00 | **completes** | 0.88 | **~100%** |
| 14 | 40 | 0.81 | **~100%** | 0.63 | **~98%** |
| 15 | 24 | 0.48 | **~95%** | 0.38 | **~90%** |
| 16 | 8 | 0.16 | ~78% | 0.13 | ~74% |

⇒ **A truncated post-garbage re-search is viable down to h = 15**, costing 0-5% of move
fidelity (0-10% at p90). h = 16 is the only genuine write-off, and that board is lost anyway
(§1.1: the garbage overwrites row 0 and the next spawn tops the receiver out).

★★ **AND the regime this rescues is rarer than it looks — which is better news still.**
§1.5 point 1 records the retraction: on real near-death boards `h_min` has median **4**, and
only **3.2%** land at W ≤ 56 f. So the primary near-death story is not truncation at all — it
is that **a COMPLETE re-search fits, in ~3.3 s of window, at the highest flip rate measured
(66.3%)**. Truncation is the *tail insurance* covering that 3.2%, not the main mechanism.
Both readings favour the lane; do not let the truncation machinery obscure the simpler and
stronger fact.

★★ **Here the truncation lever needs NO transfer assumption.** §2.4 flags that the 69-board
curve was measured for the *full depth-3 root search* and only *assumed* to carry to the
2-candidate deepening. **The base re-search IS that full depth-3 root search** — same object,
same best-first structure. For the mandatory step the curve is measurement, not
extrapolation; the assumption is confined to the optional extras.

⇒ **This reframes the near-death story.** Not "the window is useless where the danger is",
but: *the regime with the strongest evidence (66.3% flip) is reachable, provided the design
adopts truncated results instead of abandoning them.* That makes the abandon-whole rule of
§2.4 the **wrong default at h ≥ 14** — there, abandoning discards a result worth 90-100%
fidelity. The policy should be height-dependent: **abandon whole below h = 13** (a complete
search fits, so a partial signals something went wrong), **adopt at ≥ 0.80 completion above
it**.
⚠ This is a design change with a real hazard attached — adopting partials is exactly how the
pair-latch defect happened. It must ship behind the seqlock (§2.2), gate on a **completion
counter and never a timer**, and carry its own killed mutant: adopt below the threshold and
the stale-move signature must reappear.

---

## Appendix: sources

**Data (MEASURED here).** `/mnt/data/drmario_cosim/results/prestart_pilot.jsonl` — 1,500
decisions, `fw_md5 e970e9ab0208cdbce1d39ed33e2f51ee`, manifest `bed03caf0f5290be`.
Regenerate every table with `experiments/gw_design/budget_table.py`.

**Code read for this document.**
`NES_MiSTer-winner/rtl/mappers/CoproDrMario.sv` (mailbox map :26-36; arm-swap compile cost
:96-112) ·
`dr-mario-v8-wt/patch_cartridge_copro.py` @ 47707f9, md5 `a7539cf7` (2 hooks/frame :104;
`MIN_THINK=25` :381; RECOMMIT :551-553, :2138-2146; spawn-edge detect :1965-2010) ·
`dr-mario-te/h13-gate/experiments/eval47/stage2/oracle/oracle_arm.py` (`GATE_DSPAWN_H`,
`GATE_VIRUSES`, `TOPK`, `HORIZON` :104-107; `_fork_label` :281-311) ·
`.../h12_arm.py` (`fork_samples`, `margin_sum` :30-35) ·
`dr-mario-te/h12-distill/.../temporal_accum.py` (silicon contract :13-24; the 19 names
:42-52; the differencing warning :18-27) ·
`pocket-nes-mapper100/staging/strand20_20260808/INSTALL.txt:99` ·
`pocket-nes-mapper100/projects/output_files_r47b2_seed8/nes_pocket.fit.summary:8`.

**Memories cited.** `dr-mario-garbage-window-compute` · `dr-mario-garbage-window-mechanics` ·
`dr-mario-copro-idle-during-garbage` · `dr-mario-garbage-prestart` ·
`dr-mario-cosim-farm-turnbased` · `dr-mario-h12-endpoint-verdict` ·
`dr-mario-h12-gate-is-endgame-gate` · `dr-mario-distill-pivot-magnitude` ·
`dr-mario-auc-operating-point-law` · `dr-mario-pair-latch-defect` ·
`dr-mario-nmi-overrun-hazards` · `dr-mario-holdboard-softbrick` ·
`dr-mario-rtivec-mmc1rst-codependent` · `dr-mario-prestart-tuck-wedge` ·
`dr-mario-theta-is-core-not-cart` · `dr-mario-link-chain-rtl` ·
`dr-mario-single-copro-fit` · `dr-mario-stage2-shippable-lut` ·
`dr-mario-garbage-floats-at-row0` · `dr-mario-gate-standard-killed-mutants` ·
`dr-mario-mesen-launch-verification` · `dr-mario-watchdog-mgl-silent-cart-fallback` ·
`dr-mario-prg-ram-map` · `pocket-rbf-md5-gate-unsound`.
