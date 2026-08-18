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
largest window that ever exists** and ~1,900× the window at the heights where it matters.
The window is a *one-to-three extra searches* budget, not a rollout budget. Within that
budget exactly one thing is already built (DRPRESTART: re-search the projected
post-garbage board — mandatory, since 50.5% of argmax decisions flip on it), and exactly
one thing is newly affordable: a **2-candidate, 1-ply deepening of the top-2 tie**, which
fits on **52.4% of releases** at median search cost. That is the shippable step, and the
decisive screen for it costs about **$4** of compute and needs no hardware.

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

### 1.3 Window budget by board height — DERIVED

Pocket (the rematch venue). `budget` = how many whole champion decisions fit in the window.
`extra` = what is left after the **mandatory** post-garbage re-search (§2.1).
`releases` = share of the 208 MEASURED post-garbage decisions at that `h_hit`.

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
| 14 | 40 | 36.4 M | 2.4% | 95.7% | 0.81 | 0.63 | **0.00** |
| 15 | 24 | 21.8 M | 2.4% | 98.1% | 0.48 | 0.38 | **0.00** |
| 16 | 8 | 7.3 M | 1.9% | 100% | 0.16 | 0.13 | **0.00** |

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

1. **The window shrinks exactly where the danger is.** 89.4% of releases land at h ≤ 12,
   where there is room; the near-death regime that dies-ahead comes from is the 6.7% at
   h ≥ 14 where the budget is *below one decision*. Reclaiming the window buys the most
   time where it is least needed. This is the same inversion the shadow-latency pilot
   flagged for DRPRESTART, and it applies with full force here.
2. **p90 is not a rounding error, it is the design question.** (b+) is affordable on 52.4%
   of releases at median cost and only **14.4%** at p90. Whether that gap is a problem
   depends entirely on the pre-emption semantics (§2.4): if an unfinished extra is
   abandoned cleanly, p90 overruns cost only wasted work; if a partial can be adopted, p90
   is where the pair-latch defect gets reinvented.
3. **The linear tail term is not a budget question at all.** At 7.3 K cycles it is
   0.1% of even the h=16 window. It cannot be the thing the window is *for*; it is
   something to run *always*, whose only design question is value, not cost (§3.3).

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

⚠ **Scope caveat on the 50.5%, carried forward unresolved:** every board in that run
landed below 45% fill. There is **zero coverage of the high-fill states** where the window
is shortest and dies-ahead happens. I have asked the mechanics lane whether the high-fill
re-run landed; if it did not, the 50.5% licenses steps 3–4 for the mid-board regime only,
and the near-death regime remains unmeasured.

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

- **The OFF path becomes provably identical.** That is what made DRPRESTART safe to ship
  (byte-identical when unset, 12/12 flag arms plus whole-ROM hash both sides), and it is
  the property to reproduce.
- **Abandonment is not free.** With a search still ARMED at spawn, MATURE's
  lock-while-armed check disarms `SLAM_ARM` for that capsule (CITED, known DRPRESTART
  interaction). So a p90 overrun costs the slam — conservative, not dangerous, but it means
  the 52.4%-vs-14.4% gap in §1.4 has a real price and the budget should be set on the
  pessimistic side.

**A tempting third option, and the gate it needs.** `dr-mario-link-chain-rtl` records
**TRUNCATION IS FREE — 100% move agreement from 80% completion**, because depth-3 is
best-first over a depth-1 ranking. If that transfers, an extra search truncated at ≥80% of
its expected cycles could be adopted rather than dropped, lifting (b+) from 52.4% to 63.5%
of releases at median cost and from 14.4% to **41.3% at p90**. That is the single largest
lever in this design.

⚠ But it is an **assumption, not a measurement**, in two ways. First, the 80% figure was
measured for the *full depth-3 root search*, not for a 2-candidate deepening, whose
best-first structure is different. Second, it sits in direct tension with the pair-latch
result, which found early partials badly wrong (23.2% at ~10% completion). Both can be true
— bad below 10%, fine above 80% — but the middle is unmapped, and the *whole* value of the
truncation lever lives in whether that curve is flat or a cliff. **Do not ship truncated
adoption without measuring the move-agreement-vs-completion curve for the deepening
specifically.** That measurement is cheap (§4.2) and it should gate the lever.

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
2. **TIE.** The top-2 champion values are exactly tied. This is free: the copro already has
   all 32 candidate values. It is also well-founded — H12's flip provenance is **100%
   champion-value ties**, with ranks `{1: 1580, 2: 21273, 3: 1767}` (CITED). The mass is at
   rank 2, which is exactly why a **2-candidate binary comparator** is the right shape and
   a top-4 comparator is mostly wasted budget.

This gate is deterministic, computable on-cart, costs nothing, and has no learned component
to mis-calibrate.

### 3.3 If a learned trigger is ever added — the operating-point discipline

The distill lane's 19 lock-time accumulators (8 per-candidate deltas + 11 running-state
context terms; `temporal_accum.py:42-52`) are the natural candidate trigger, and they meet
a real silicon contract: small integers, updated at lock time only, strictly causal,
computable from the candidate's post-board (`temporal_accum.py:13-24`). At 7.3 K cycles
they are free (§1.4).

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
  The 50.5% is a good prior for the lane existing, not evidence for this number.
- **S0-B · the truncation curve** (§2.4). Move agreement vs fraction-of-cycles-completed,
  for the deepening specifically, at 10/20/…/100%. Decides whether the truncation lever is
  real (52.4% → 63.5% at median, 14.4% → 41.3% at p90) or whether partials must be dropped.

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

- **The 50.5% argmax-flip has no high-fill coverage** (§2.1). The value case for the whole
  lane currently rests on a stratum that excludes the regime the lane is aimed at.
- **The h_hit distribution in §1.3 is n=208, from 10 games, one arm, one level.** The
  decisive cells at h ≥ 13 hold 4–8 observations each. Treat the release-share column as a
  scale, not a rate.
- **The truncation lever is an assumption** (§2.4) and it is worth ~27pp of affordability at
  p90. Measure it before designing around it.
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

**Step 1 (today, ~0.5 d, $0): S0-A, the argmax-flip screen.** Base vs 2-candidate-deepened
argmax on banked post-garbage boards at tie plies. **A flip rate below ~2% closes the lane
for the cost of an afternoon.** Run S0-B (the truncation curve) alongside; it is the same
corpus and it sets the design either way.

**Step 2 (~2 d, ~$4): the farm A/B with compute granted unconditionally**, base and
treatment both on the settled post-garbage board, paired, N=9,000, stratified by h,
dose-matched label-blind null mandatory, dies-ahead primary. This measures the **value
ceiling**.

**Step 3 (analysis, $0): multiply by the completion curve.** The shippable effect is at most
**52.4%** of the ceiling at median search cost, or 63.5% if the truncation lever proves out
— and only **14.4%** if p90 costs must be respected. **Fold that discount into the MDE
before launching Step 2, not after.** If ceiling × 0.524 lands under the MDE, the honest
outcome is a registered DO-NOT-LAUNCH, exactly as the distill lane produced. That is a
success of the process, not a failure of the idea.

**Step 4 (only if Steps 1–3 clear): build it.** Firmware-resident extras behind one GO,
seqlock shadow mailbox, 17-byte budget table, abandon-whole pre-emption, default OFF and
byte-identical when unset, five killed mutants (§4.5), Mesen mechanism gate, then silicon —
**after** the NMI fix spec lands.

### 6.2 The three claims the owner should push back on

1. **"H12 will never fit in the window."** This is the load-bearing negative result and it
   rests on an upper bound (≤300 champion decisions). The bound is loose, but it has ~56× of
   slack against the largest window and ~1,900× at h=12, so no plausible tightening changes
   it. If the owner wants the tight number, §4.5's cheap fork-horizon measurement gives it.
2. **"The window is a 1–3 search budget, not a rollout budget."** If that reframing is
   accepted, the whole lane's ambition should be reset from "gated depth-4 / gated H12" to
   "a binary comparator at a tie" — which is a smaller idea, but a shippable one, and it is
   pointed at the same tie population where H12's entire certified effect lives.
3. **"The prize is where the window is longest, not where the danger is."** 89.4% of
   releases land at h ≤ 12 with room to spare, and the near-death 6.7% at h ≥ 14 cannot
   afford even one search. **Closing the near-death case needs a faster search, not more
   window** — the window there is shorter than any depth-3 decision the copro makes. If
   dies-ahead at h ≥ 14 is the actual goal, this lane is the wrong instrument and a cheap
   endgame search mode is the right one.

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
