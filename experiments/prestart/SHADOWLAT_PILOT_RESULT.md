# Shadow-latency pilot: how often would the copro's answer be late?

**Data:** `/mnt/data/drmario_cosim/results/prestart_pilot.jsonl` — 10 games, s20b, drop +
bursty, **1500 decisions**, 208 of them post-garbage. Produced by `drm-shadowlat-chain`
after its three gate stages passed.
**Tool:** `experiments/prestart/shadowlat_analyze.py` (selftest PASS — 12 hand-computed
cases, 4 killed mutants; whole-chain fixture PASS). Numbers below were produced
independently twice (team-lead's run and mine) and agree to the digit.

**What this is and is not.** The farm is turn-based: the board freezes during `decide()`,
so **none of these decisions was actually late**. This is a projection from raw per-decision
clocks onto the game's real-time budgets — "would this answer have missed its deadline on
hardware". It cannot show a panic vertical; it can only show a budget exceeded.

---

## The gate that makes the pilot trustworthy

| check | result |
|---|---|
| new ≡ parent on the determinism key, per seed | **PASS**, 0 diffs / 3 seeds |
| `lat` invariants (5-tuples, `sum(lat clocks) == clocks`) | hold on every row (156/205/129 decisions) |
| mutant ≢ parent (stale-move injection) | **KILLED** on 3/3 seeds, 4 of 5 key fields |

The mutant's 6-minute runtime vs ~45 for each control is **not** a defect: it plays every
pill with the previous pill's move, tops out at 14/27/27 pills instead of clearing at
156/205/129, and its runtime tracks the work done — pills 7.2x, clocks 8.6x, wall 7.8x.
Rows are real games with real captures, not empty or degenerate.

⚠ **Gate weakness found:** `moves` is **absent from all 9 gate rows**. `compare_key.py`
uses `.get()`, so a missing field compares `None == None` and passes silently — the key is
effectively **four** fields, not five. It changed no verdict here, but the gate would stay
silent about a mutation that moved only the move sequence. Fix: assert every key field is
present in both files before comparing.

⚠ The mutant is **catastrophic** (100% of decisions stalled), so it proves the comparison is
non-vacuous, not that it is *sensitive*. A 5%-stall mutant would test the latter.

---

## A. Fall-budget overrun — answer arrived after the capsule passed its target

Budget = 13 f/row (L11) from the spawn row to the chosen `entry_row`. Banded on `max_h`.

| band | n | silicon late | 95% CI | sim-lockstep late |
|---|---|---|---|---|
| 0-4 | 22 | 0.0% | [0.0, 14.9] | 0.0% |
| 5-8 | 318 | 0.0% | [0.0, 1.2] | 0.0% |
| **9-12** | 743 | **14.1%** | [11.8, 16.8] | 2.8% |
| 13+ | 417 | 8.9% | [6.5, 12.0] | 3.8% |
| **ALL** | 1500 | **9.5%** | [8.1, 11.1] | **2.5%** |

Median decision 49.6 silicon frames / 31.6 sim; p90 63.8 / 40.6.

## B. Garbage-window overrun — would the answer miss the pre-spawn window?

Budget = `264 − 16·h_hit`. Banded on `h_hit`.

| band | n | silicon late | 95% CI | sim-lockstep late |
|---|---|---|---|---|
| 0-4 | 30 | 0.0% | [0.0, 11.4] | 0.0% |
| 5-8 | 102 | 0.0% | [0.0, 3.6] | 0.0% |
| 9-12 | 54 | 0.0% | [0.0, 6.6] | 0.0% |
| **13+** | 22 | **68.2%** | [47.3, 83.6] | 36.4% |
| ALL | 208 | 7.2% | [4.4, 11.6] | 3.8% |

---

## ★ The 13+ band is not uniform, and the mechanism is exact

Broken out by exact `h_hit`, the picture is sharper than the band suggests:

| h_hit | n | late | W (f) | median decision (f) |
|---|---|---|---|---|
| 0-12 | **186** | **0** | 264 … 72 | 33-52 |
| 13 | 8 | 2 (25%) | 56 | 48.6 |
| 14 | 5 | 4 (80%) | 40 | 43.8 |
| 15 | 5 | 5 (100%) | 24 | 43.6 |
| 16 | 4 | 4 (100%) | 8 | 36.7 |

**The median decision cost is essentially FLAT in h (~44-48 frames).** What changes is the
budget. So the crossover is mechanical and predictable:

> the prestart completes within the window iff **264 − 16·h > ~46**, i.e. **h < ~13.6**

Everything at h ≤ 12 clears the bar with room; everything at h ≥ 14 is hopeless; h = 13 is
the knife edge (W=56 vs a 48.6-frame median).

## ⚠ What this means for DRPRESTART — a correction worth making explicitly

A natural reading of table B is *"the prize is concentrated at h ≥ 13, exactly where the
dies-ahead deaths live."* **That inverts the mechanism.** A window overrun is the prestart
FAILING to finish before spawn. So h ≥ 13 is where the prestart is **weakest**, not
strongest.

The accurate read is better news than the inverted one:

- **At h ≤ 12 — 186/208 = 89.4% of all post-garbage decisions — the prestart completes
  within the window with 100% reliability.** The answer is ready the instant the capsule
  spawns. That is the prize, and it covers the large majority of releases.
- **It lands precisely where lateness is most common.** Fall-budget lateness peaks at
  `max_h` 9-12 (**14.1%**, the worst band), and the window overrun there is **0%** — so the
  prestart fully covers the band that actually suffers late decisions.
- **At h ≥ 13 (22/208 = 10.6%) the prestart degrades to a partial head start.** It does not
  stop helping: the offline timing rig measures the answer still arriving **63 frames
  earlier at h=13 and 31 frames earlier at h=15** than the spawn-edge baseline. But it is no
  longer ready at spawn, and above h=14 it essentially never is.

⇒ **DRPRESTART is a mid-board instrument, not a near-death one.** Anyone hoping it will fix
dies-ahead at h≥14 should expect a partial head start, not a ready answer. Closing the
near-death case needs a *faster search* (or a cheaper endgame mode), not an earlier start —
the window there is shorter than any depth-3 decision the copro makes.

## The domain trap, live in production data

Silicon 9.5% / 7.2% vs sim-lockstep 2.5% / 3.8% — the two clock domains disagree by ~2-4x on
the headline, and at h_hit 13+ by 68.2% vs 36.4%. The selftest pre-registered exactly this:
a 33e6-clock decision at h_hit=15 is 36.3 f in silicon (misses the 24-frame window) and
23.1 f in sim-lockstep (fits it) — same decision, opposite verdict.
**Silicon is the right domain for any cart claim** (the copro runs its own 54.669 MHz tap;
the sim's 48x lockstep is an artifact of the verilated harness). A late-decision rate quoted
without naming its domain is not imprecise, it is unfalsifiable.

## Caveats

- 10 games. The decisive cells are small: **22 post-garbage decisions at h ≥ 13**, 4-8 per
  exact h. The 68.2% carries a [47.3, 83.6] interval and the per-h rates rest on n=4-8.
- Turn-based farm ⇒ projection, not observation (see the top of this file).
- One arm (s20b, drop + bursty), one level.
- `264 − 16·h` is ROM-derived and emulator-verified 8/8, but assumes no clear is triggered by
  the garbage (a clear only ever *lengthens* the window, so the budget is conservative).
