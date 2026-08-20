# PRESTART latency in the co-sim farm — design memo (scoping only, nothing implemented)

**Date:** 2026-08-08
**Context:** Verified finding: the farm does NOT model decision latency. `game.py` is per-PILL
turn-based — the board freezes while `Cosim.decide()` blocks (game.py:175-186), placement is
instantaneous (`faithful_env.step` -> `place_pill`), and the RTL search cost surfaces only as the
JSONL `clocks` field (game.py:186, 274; sim_farm.cpp:96-103). Garbage release and settle are
atomic inside one placement step (game.py:248-253 -> `inject_bursty_garbage`, settle-to-fixpoint
at bursty_model.py:652-653), so the baseline arm already receives the settled post-garbage board
at zero cost — a DRPRESTART A/B in today's farm shows zero effect BY CONSTRUCTION.

The only clocks-to-outcome coupling that exists is `CLOCK_LIMIT = 2e9` (sim_farm.cpp:58, 97-99):
a wedge detector ~60x the observed worst case, not a latency model. Any latency model must
subsume it (an `ERR timeout` stays a wedge, never a priced delay).

---

## 1. clocks -> frames conversion at the search site

`sim_farm.cpp` already returns per-decision cost: `used = clocks - c0` on the reply line
(line 103), and `game.py` already has it in hand as `d["clocks"]` (line 186). No RTL or C++
change is needed — the raw material exists; only harness accounting is missing.

**The conversion must pick a clock domain explicitly, and the two candidates differ by ~1.57x:**

| Domain | Formula (frames) | Worst case (~33e6 clocks) |
|---|---|---|
| Sim lockstep (`tick()` advances copro clk and the 48x-CPU bus together, sim_farm.cpp:35-44; implicitly ~85.9 MHz) | `used / (48 * 29780.5)` = `used / 1.4295e6` | ~23 frames |
| **Real silicon copro tap, 54.669 MHz** (dr-mario-copro-clock-tap; `used` counts copro cycles 1:1) | `used * 60.0988 / 54.669e6` = `used / 909,650` | **~36 frames** |

**Recommendation: price in the silicon domain (54.669 MHz).** The point of the exercise is the
cart/MiSTer champion, and the copro cycle count for a search is the domain-invariant quantity;
the sim's lockstep pacing is an artifact. Note the worst case (~36 frames) exceeds the entire
h=15 garbage window (264 - 16*15 = 24 frames) — the latency model is not a formality, and it
binds exactly in the near-death regime the project cares about (cf. fidelity-is-regime-dependent).

**Prestart accounting:** the prestart arm starts its clock at the release edge — the
`inject_bursty_garbage` call site (game.py:248-253) — earning a credit of
`min(F, 264 - 16*h)` frames (h = `game.garbage_hit_h`: the MIN, over the volley's own target
columns, of the PRE-garbage stack heights, per #124 — not the max, not post-settle heights,
and the column set re-derived from the injector's model draw rather than inferred from the
board, since a hit column that then clears vanishes from any board-difference set).
⚠ The volley column model is itself low-fidelity: `bursty_model.sample` draws random distinct
columns while the ROM releases maximally spread sets (`checkReleaseAttack` $9C01), which find
a shallow column more often — so real windows are LONGER than the farm reports, and every
window-overrun count is an upper bound. The baseline arm starts at the next
spawn. Same moves, different frame charges. Bursty draws key on `(seed, pills_placed)`
(bursty_model.py:628-632), so pairing survives as long as placements remain the pairing index.

## 2. Where gravity would have to tick during the wait

Nothing on the board moves during a search except the ACTIVE capsule: viruses are static,
settled cells are static, and garbage settle is already atomic at injection. So "gravity during
the wait" reduces entirely to the falling pill, and there are two designs:

- **(A) Accounting model (recommended):** charge `rows_lost = floor(F / 13)` (L11 fall
  13 f/row, tempo-chew) as a deeper effective entry row for the pill. Then a feasibility
  check: a placement is degraded/unreachable if its landing cannot be reached from entry row
  `rows_lost` — implementable Python-side with the existing `fall_from` machinery (already used
  at game.py:196 and gate_validate.py:102). The copro mailbox has NO entry-row field, so the
  fallback (re-pick best feasible placement, or score a stale-move/topout penalty) must live in
  Python, not the RTL. Turn-based structure, env, and RTL stimulus are all untouched.
- **(B) Full frame axis:** give `faithful_env` a per-frame loop (gravity tick, nav input model,
  lock delay) and interleave the decide() wait with it. This is a rebuild of the 6502 driver's
  nav model inside the farm — weeks of work, invalidates comparability with every existing
  baseline row, and reintroduces the nav-fidelity problems the turn-based farm was built to
  avoid. Not recommended for pricing DRPRESTART.

A useful stage-0 before either: **shadow pricing** — log per-decision `F` and the h-dependent
budget into the JSONL (report-only, zero behavior change) and pilot on 2 workers to a FRESH out
file (`/mnt/data/drmario_cosim/results/prestart_pilot.jsonl`; run_farm.py skips existing
(arm,seed) rows in the same file). That measures how often latency would bind at all before any
behavioral surgery. Per-game `clocks` totals in existing results cannot answer this; the
per-decision value is consumed and summed away at game.py:186.

## 3. Do gate_validate.py's gates survive?

Yes, with one caveat about comparability:

- **gate_agree.py** (server reproduces stock binary bit-for-bit): unaffected — design (A)
  changes no RTL stimulus, no C++, no firmware.
- **Gates (e) orientation and (d) physics** (gate_validate.py:53, 78): unaffected — pure checks.
- **Gate (a) determinism** (gate_validate.py:134): survives PROVIDED the latency model is a pure
  function of the reply's `clocks` and the board (it is, in design A — the RTL is deterministic,
  so `F` is deterministic). `_key` (line 128-131) includes `clocks` and `moves`; both stay
  reproducible. Keep `clocks` in the key.
- **Caveat:** the fallback path changes `moves` relative to non-latency arms, so latency rows
  are NOT comparable to any legacy baseline row. Use new arm names and a fresh out file; never
  mix into tuck2x2_bursty.jsonl. Re-run the full gate battery once per new arm as usual, and per
  the gate standard, show the feasibility check FAILS on a wrong input (e.g. a mutant that skips
  the `rows_lost` charge) before trusting any A/B number.

## 4. Estimated effort

| Stage | Work | Effort |
|---|---|---|
| 0. Shadow pricing (report-only) | expose per-decision `F` + budget in JSONL, 2-worker pilot | ~0.5 day |
| A. Accounting model | converter + entry-row feasibility + fallback + gate battery + mutant test + pilot | ~2-4 days |
| B. Full frame axis | per-frame env + nav model + revalidation of everything | weeks; NOT recommended |

Risk concentrates in the fallback policy of (A): it is a modeling choice (what does an overrun
COST — deeper entry? stale pre-garbage move? forced topout?) and the answer is exactly the
50.5% argmax-flip fact — a stale move is wrong half the time — so the choice materially shapes
the measured price. That is the strongest argument for section 5.

## 5. The alternative: price prestart ONLY on silicon (staged v7 cart)

DRPRESTART v7 is already staged with a passing settle gate:
`/home/struktured/projects/pocket-nes-mapper100/staging/prestart_v7_20260808/gate_settle_200.log`
(200/200 EXACT; note the staging dir is under `projects/pocket-nes-mapper100/`, not
`projects/dr-mario-rl/...`). A silicon A/B — DRPRESTART=1 vs 0 carts, MiSTer headless rig,
save-state RAM readout — measures the TRUE price with zero modeling choices: real driver
overhead, real 54.669 MHz tap, real garbage window, no fallback-policy assumption.

Cart hygiene: pin DRBUILDID=0 (defaults ON and moves 1868 ROM bytes — breaks reproduction),
seed is deterministic on boot (entropy only from level-select frames), and the release edge is
the attacker-side buffer clear ($0318), already the driver's hook.

Trade-off: throughput. The farm runs ~arbitrary seeds/hour; silicon runs real-time games. But
the farm route needs stages 0+A of new machinery plus a debatable overrun-cost model before it
can say anything, while silicon answers the actual question directly.

**Recommendation:** (1) do stage-0 shadow pricing in the farm (cheap; tells us how often latency
binds and at what h, and sizes the effect a silicon A/B must detect); (2) price DRPRESTART on
silicon with the staged v7 cart; (3) build the stage-A accounting model only if the silicon
effect is real but too small for real-time sample sizes. Do not build (B).
