# Task #43: Pocket opening-quality verdict

**Question**: do the Pocket cart configs differ in opening P2 placement quality, and which
mechanism causes "nonsensical vertical drops in the opening" — fast tempo gates (A), a slam
that fires mid-lateral-transit (A'), or stale driver state carried across a rematch (B)?

**Verdict**: **B, confirmed and cured by `DRCOLDINIT`.** `v2-form` and `v3-form` (both lack
`DRCOLDINIT`) reproduce a 100% "hard-drop at the spawn column" defect across all 8 observed
pills of a rematch (not just pill 1), with driver think-time blown out ~15x. `v4-form`
(`DRCOLDINIT=1`) is statistically indistinguishable from a fresh cold boot. Hypothesis A
(tempo miscalibration, isolated from B) and A' (slam engaging before lateral steering
completes) were both tested and **not reproduced**, including under an adversarial stress
variant — see caveats below on why this doesn't fully close the book on A' for the live v4
report.

## Instrument correction (recon, before this run)

The task briefed the Verilator co-sim (`fpga/copro/sim_mister.cpp` / `mister_vsim`) as the
cycle-accurate instrument. It is byte-identical across every worktree checked (qa-wt,
canonical-wt, main-wt, driver-nav, driver-fidelity, driver-slam, incr-delta, vsaware-wt) and
is **copro-RTL-only**: it instantiates `CoproDrMario.sv`/`LeafEval.sv`/`copro6502.v` and feeds
canned board+colour vectors from `hostdata.txt`, checking the search coprocessor's answer
against a py65 oracle. There is no NES 6502 CPU core, no PPU, and — the disqualifying fact —
no execution of the DRIVER assembly (the code that decides pill movement, rotation, slam
timing, and the cold/warm state in question). It cannot produce a pill trajectory at all.
Confirmed with team-lead 2026-08-02; this write-up uses the corrected instrument below.

**Instrument used**: the real assembled driver bytes (`patch_cartridge_copro.py`'s
`build_main` output, driver-nav worktree) executed instruction-by-instruction via py65,
continuously across 8 simulated pill-locks per game, with a scripted mailbox standing in for
the copro's search (latency + published column/orientation are deterministic per seed — this
is decision-accurate for the DRIVER's own state machine, which is what's in question here;
copro search *quality* is out of scope and was not tested). Script:
`experiments/opening_quality/run_opening_quality.py` (this worktree).

Hook cadence: `patch_cartridge_copro.py:95-112` establishes (measured 2026-08-01, static
analysis of the NMI call graph) that the driver hook runs **exactly 2x per frame**, both
inside the NMI, baked into the base game's `getInputs`/`addExpansionCTRL` call structure —
`DRPOCKET` never touches this (confirmed separately, see Rider 3 below). This harness uses
`HOOKS_PER_FRAME=2` accordingly (a prior gitignored scratch harness,
`driver-nav/tmp/p0lib.py`, used an unmeasured `5`/frame — not reused here).

## Rider 3: static hook-cadence check (done first, 15 min, negative)

`DRPOCKET`'s only effect anywhere in `patch_cartridge_copro.py` is the single-vs-dual mailbox
window layout (`:500-504`, "Analogue Pocket core has only the $5000 window"). It does not gate
hook install site, count, or NMI structure. At the CODE level, hook cadence is identical
between Pocket and MiSTer builds — every hook-counted constant (`MIN_THINK`, `K_OPEN`, etc.)
counts the same number of hooks per frame on both. This rules out a code-level cadence
mismatch as the cause; it says nothing about whether the two platforms' cores run the NES 6502
at the same real-world wall-clock rate, which is outside what static analysis or this harness
can answer (would need silicon/emission timing).

## Arms and warm-state construction

| Arm | Flags | vs v2-form |
|---|---|---|
| v2-form | `DRHUMAN DRNAVDWELL=0 DRNOFREEZE DRPOCKET DRRECOMMIT_NOFREEZE DRSTUDYCOUNTS DRMINTHINK=12 DRSLAM_KOPEN=32 DRWRETRY DRPENDBOUND DRSTALLWD DRBUSYESC` | — |
| v3-form | same minus `DRMINTHINK`/`DRSLAM_KOPEN` | isolates tempo (A) |
| v4-form | v2-form + `DRCOLDINIT=1` | isolates cold-state fix (B) |

**Rider 1** (test infra): `DRCOLDINIT` was wired into `driver-nav/tests/test_driver_fidelity.py`'s
`load_build()` as a first-class knob (`coldinit=` kwarg), committed to the driver-nav
worktree. The existing byte-exactness gate was re-run before and after: 35/41 pass both times,
identical hashes — the 6 failures are a **pre-existing** golden drift on driver-nav's current
HEAD (unrelated to this change; not investigated further, out of scope for #43).

**Rider 4** (warm-state signature): rather than poke memory addresses directly (which a first
draft of this harness did, and which incorrectly made `v4-form` look identical to `v2-form`
because it bypassed the actual code path `DRCOLDINIT` fixes), the final harness drives the
**real code path**: play mode-4 hooks with an in-flight search forced to never `DONE`
(matching the documented P2.2 "soft-relaunch mid-search" scenario — stale `ARMED2` from an
abandoned search), then cut to a non-play/non-intro mode (any value reaches the `"menus"`
label at `patch_cartridge_copro.py:1060`, the **only** place that clears `MATCH_ACTIVE`
`if COLDINIT:`, at `:1061-1064`), then resume play. For non-`COLDINIT` arms `MATCH_ACTIVE`
survives the menu untouched, so the per-match reset block at `:1008-1030` (gated on
`MATCH_ACTIVE==0`) never fires for the "rematch": `PEND2`, `DELAY2`, `LASTY1/2`, `ARMED2`,
`WDOG2`, `WDOGH2`, `WRETRY2` all carry the stale prior-search values into pill 1 of the new
match. For `COLDINIT` arms the menu step zeros `MATCH_ACTIVE`, so the reset block fires on the
first rematch play-hook and the state is clean. Addresses (all cited from
`patch_cartridge_copro.py`): `MATCH_ACTIVE=0x6164` (`:58`), `ARMED2=0x6161` `WDOG2=0x6162`
`WRETRY2=0x6163` (`:57`), `WDOGH2=0x6166` (`:59`), `PEND2=0x614F` (`:43`), `TGT_C2=0x6152`
`TGT_O2=0x6153` `LASTY1=0x6154` `LASTY2=0x6155` (`:46-49`), `DELAY2=0x615F` (`:53`).

## Results (n=400/cell: 50 seeds x 8 pills; matched seeds across arms)

| arm/condition | zero-lateral rate | wrong-column rate | mean think-hooks |
|---|---|---|---|
| v2-form / cold | 12.5% | 0.0% | 77.1 |
| v2-form / **warm** | **100.0%** | 0.0% | **1127.0** |
| v3-form / cold | 13.8% | 0.0% | 77.9 |
| v3-form / **warm** | **100.0%** | 0.0% | **1127.0** |
| v4-form / cold | 12.5% | 0.0% | 77.1 |
| v4-form / warm | 11.8% | 0.0% | 74.0 |

Per-pill breakdown (v2-form/warm and v3-form/warm) shows the defect is **not confined to pill
1** — it is exactly 100% zero-lateral for every one of pills 1-8, i.e. once the wedge forms it
persists for the rest of the observed match, not a one-shot bad opening move. v4-form/warm is
statistically flat pill-by-pill (4-22% per pill, consistent with 400-sample noise around the
12.5% baseline = P(published target column happens to equal spawn column) = 1/8 exactly).

The 12.5%/13.8% baseline in the cold rows is fully explained by chance (the scripted mock
"copro" picks a target column uniformly from 0-7; spawn column is always 3, so 1/8 = 12.5% of
the time the correct decision IS to not move laterally — corroborated by `wrong_column=0%` in
every cold row, meaning locked column always equals the published target). This is a
zero-lateral **rate baseline**, not a bug rate; the `wrong_column` metric is what separates the
two.

### Stress test for A' (mid-transit slam), cold boot, fast gravity (10 frames/row vs the 40-frame baseline), far-column + rotation + late mid-flight target revision, n=400/arm

| arm | wrong-column rate | zero-lateral rate | mean think-hooks |
|---|---|---|---|
| v2-form | 0.0% | 0.0% | 60.9 |
| v3-form | 0.0% | 0.0% | 60.6 |
| v4-form | 0.0% | 0.0% | 60.9 |

Even under conditions deliberately engineered to provoke a slam before lateral steering
finishes (fast gravity, maximum lateral distance, a revision landing 2 hooks before the
scripted search's own latency expires), the driver's commit gate (`ROT_DONE2` latch requiring
rotation-complete + min-think + stability before a slam/lock) held in every trial, for every
arm including v2-form's aggressive `MINTHINK=12`/`KOPEN=32`. **Hypothesis A' is not reproduced
by this harness under either baseline or adversarial conditions.**

## Verdict on mechanism

- **B (stale rematch state) — CONFIRMED, and it is the anchor observation's likely cause.**
  v2-form (the field-tested "lots of vertically dropped pills" config) and v3-form (same minus
  tempo) show *identical* 100%-of-pills zero-lateral hard-drops after a single rematch
  transition; `DRCOLDINIT` (v4-form) eliminates it completely, indistinguishable from a fresh
  cold boot. This is a real, source-traceable, single-flag-curable defect.
- **A (tempo miscalibration, isolated) — not supported.** v2-form vs v3-form (same
  `DRCOLDINIT=0`, differ only in `MINTHINK`/`K_OPEN`) are statistically identical on every
  metric in both cold (12.5% vs 13.8%, well within noise at n=400) and warm (100% vs 100%) and
  stress (0% vs 0%) conditions. Tempo constants alone did not move any metric tested here.
- **A' (mid-transit slam) — not reproduced, including under adversarial stress.** This is a
  genuine negative result, not a shallow one (deliberately engineered far-column + rotation +
  late-revision + fast-gravity conditions), but it does not fully close the book: this harness
  mocks the copro's decisions and does not model board fill / line clears, so it cannot rule
  out A' arising from a real search's timing interacting with a denser real board, or from a
  wall-clock cadence difference between the Pocket and MiSTer cores (flagged as open by Rider 3
  — static analysis rules out a *code-level* cadence difference, not a *silicon* one).

## Caveat: the v4 field report

Mid-task, the team lead relayed a live report that v4 ("fast tempo + `DRCOLDINIT`") *also*
showed "vert pills placed almost randomly." That was subsequently flagged as possibly a
misattributed MiSTer/P1 observation, not confirmed as v4-specific, and the team lead's
guidance was to treat the anchor observation (v2, last night) as the one this task answers
regardless. Recorded here for completeness: **if the v4-specific report is later confirmed**,
it means a mechanism beyond both B (cured here) and A' (not reproduced here, even
adversarially) is at play on v4, and the two candidates worth investigating first would be (a)
a real, denser board interacting with search timing in a way this placeholder-board harness
cannot model, or (b) genuine Pocket-vs-MiSTer silicon/core timing divergence (see Rider 3
caveat) rather than anything in the driver's own state machine. The Mesen+Lua mailbox harness
(`tools/copro_emu.lua`, `tools/bridge/`, qa-wt/main-wt/vsaware-wt — real driver + real PPU +
real board/clears, proven working 2026-07-26 evidence, but not headless, not path-portable,
and with no per-pill logger yet) remains the recommended fuller-fidelity follow-up instrument
if that confirmation comes in.

## B2: does a CvC auto-rematch ever reach the COLDINIT fix at all? — REFUTED (empirically, n=400)

Team-lead sub-hypothesis, raised after the field data was clarified as a MiSTer CvC duel
observation (the actually-deployed "Stomper" probe cart, `DRCOLDINIT=1` already set) rather
than Pocket: does the CvC auto-rematch flow (probe ring: modes `7→3→8→4`) ever reach the
`"menus"` dispatch where `DRCOLDINIT`'s `MATCH_ACTIVE` clear lives, or does an earlier gate
(the `fc_clear` "full-clear auto-advance" block, `:963-989`, which owns the frame and RTSs
before the mode-4/mode-8 dispatch chain, gated only on `MATCH_ACTIVE!=0` + `VCOUNT`/`VSEEN`,
never on `$0046`) structurally bypass it on every mode in that sequence?

**A first static read said "maybe" and was corrected by the empirical arm — this is exactly
the scenario the test-the-defect house rule exists for.** The static trace initially
established that `fc_clear` runs before the mode dispatch and doesn't read `$0046`, which is
true, but missed a second gate: `patch_cartridge_copro.py:975` (inside the `NAV_V4` block,
`NAV_V4` defaulting **on** for the whole driver lineage — `NAVFIX` defaults `"1"`, `DRNAV_V4`
defaults `"1"`) adds `LDA $0046; CMP #4; BCC "fc_no"` **immediately before** `fc_clear`'s own
`MATCH_ACTIVE`/`VCOUNT`/`VSEEN` check. This unconditionally routes **any mode < 4** straight to
`fc_no` (ordinary dispatch), regardless of `fc_clear`'s own gate state. Mode 7 (≥4) gets no such
exemption and IS blocked by `fc_clear` as the static trace predicted; but mode 3 (<4), which is
part of the actually-observed `7→3→8→4` sequence, is **structurally immune** to `fc_clear` by
construction — it reaches `"menus"` and the `DRCOLDINIT` `MATCH_ACTIVE` clear every time,
regardless of what `VCOUNT`/`VSEEN` say.

**Empirical confirmation** (`run_opening_quality.py`'s new `play_through_autorematch` method
and `MISTER_ARM_SPECS`, driving the real compiled bytes of the exact deployed cart —
`driver-nav/roms/manifests/latch-converged-native-probe.json`, commit `ee32402e`, `DRP1NATIVE=1`
CvC duel config, NOT the `DRHUMAN` Pocket arms above, which compile `fc_clear`'s `START`
injection out entirely per `:984-988` and so can't exercise this path). Forced an
abandoned in-flight search (matching the P0.2 "soft-relaunch" signature), triggered the STAGE
CLEAR condition (`VCOUNT_P2=0` with `VSEEN2` set), then drove hooks through modes 7, 3, 8 in
that order with `VCOUNT_P2` held at 0 throughout (the worst case — viruses not repopulated
until mode 4 resumes) before restoring it and observing 8 pills, n=50 seeds:

| arm | zero-lateral rate | mean think-hooks | starts injected/seed | ARMED2 unchanged start-to-end of transit |
|---|---|---|---|---|
| `mister-probe` (as shipped, `DRCOLDINIT=1`) | 11.8% | 70.6 | 4.0 | 50/50 |
| `mister-probe-nocoldinit` (control) | 100.0% | 1127.0 | 9.0 | 50/50 |

`mister-probe` is statistically flat against the 12.5% chance baseline established elsewhere in
this write-up — **the actually-deployed cart already cures the auto-rematch case in this
harness.** (The `injected_starts` counts differ 4 vs 9 between the two arms because
`mister-probe`'s search resolves and pill locks complete faster once state is clean, consuming
fewer of the fixed 60-hook transit window's press-eligible ticks — not evidence of anything
being blocked; both arms' `ARMED2` is provably untouched for the full 60-hook transit in every
one of the 100 combined trials, confirming `fc_clear` genuinely owns mode 7 in both cases, and
the difference is entirely down to what happens once mode 3 is reached.) The same pattern holds
for the Pocket `v2/v3/v4-form` arms run through the identical `7→3→8→4` sequence (`v2/v3-form`:
100% zero-lateral; `v4-form`: 11.8%, flat) — consistent, though as noted those arms can't test
the `START`-injection half of the mechanism since it's compiled out for `DRHUMAN`.

**Conclusion: B2 does not hold for any cart in the current lineage, because `NAV_V4` (on by
default, installed years earlier for an unrelated title-mis-land fix) already guarantees an
escape hatch through any mode-3-like state in the transition.** The practical implication for
the "design a fix" ask that followed the original B2 hypothesis: **no fix is needed** — moving
the reset to fire at `fc_clear`'s own detection point is not required, because the auto-rematch
path already reaches the existing `DRCOLDINIT` fix by a different route than assumed. This
result was reported back before any fix code was written, since building a fix for a defect
that doesn't reproduce would risk exactly the landmine flagged in that discussion for no
benefit. If the live MiSTer duel report is confirmed as real, it now needs a different
explanation than B2 — the leading candidate is simply that the observation was of P1 (the
deliberately crude `DRP1NATIVE` AI on this exact cart), which the team lead's own second
message already flagged as the likely alternate reading.

## Ship recommendation

**Ship v4-form (or any Pocket build with `DRCOLDINIT=1`) for the Pocket cart.** It is the only
arm tested that eliminates the reproduced defect and is otherwise byte-behavior-identical to
v2-form (same tempo constants, same everything else). There is no evidence in this run that
`DRMINTHINK=12`/`DRSLAM_KOPEN=32` cost anything on their own — v3-form (defaults) performs
identically to v2-form on every metric — so there's no tempo trade-off being made by keeping
them; `DRCOLDINIT` is the one load-bearing addition.

## Reproduce

```
cd experiments/opening_quality
/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python run_opening_quality.py \
    --seeds 50 --pills 8 --stress --stress-gravth 10 --autorematch --out results.json
```

Wall time: ~2 minutes (400 game-simulations x 8 pills per arm/condition, well under the 2h
budget). Full raw per-pill records for every (arm, condition, seed, pill) are in
`results.json` (`_stress` holds the A' stress-sweep records; `_autorematch` holds the B2
`mister-probe`/`mister-probe-nocoldinit` records — call `run_autorematch_sweep(arm_specs=
ARM_SPECS)` directly for the Pocket-arm B2 comparison, saved separately as
`autorematch_pocket.json` in this directory; `autorematch_mister.json` duplicates the
default `_autorematch` key standalone).
