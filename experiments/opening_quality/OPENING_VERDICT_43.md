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

## Residual item: B2 (does a CvC auto-rematch ever reach the COLDINIT fix at all?)

Team-lead sub-hypothesis, raised after the field data was clarified as a MiSTer CvC duel
observation (Stomper cart, `DRCOLDINIT=1` already set) rather than Pocket: does the CvC
auto-rematch flow ever reach the `"menus"` dispatch where `DRCOLDINIT`'s `MATCH_ACTIVE` clear
lives, or does it structurally bypass it — which would mean the fix in this write-up doesn't
even apply to the duel cart that showed the symptom?

**Direct factual answer**: yes, mode 3 (and every mode except 4 and 8) reaches `"menus"`
(`patch_cartridge_copro.py:1042-1043`: `CMP #8; BNE "menus"` — only mode 8 skips it) and gets
the `if COLDINIT:` `MATCH_ACTIVE` clear at `:1061-1064`. Mode 8 itself gets an **unconditional**
`MATCH_ACTIVE`/`VSEEN1`/`VSEEN2` clear (`:1043-1048`), regardless of `DRCOLDINIT`. So the
probe-ring-observed `7→3→8→4` sequence passes through two different code paths that both clear
`MATCH_ACTIVE`, on paper.

**But there's an earlier gate that can make this moot**: the "full-clear auto-advance" block
(`:963-989`) runs *before* the mode==4/mode==8 dispatch chain entirely, and its condition
(`MATCH_ACTIVE!=0` and a player's `VCOUNT==0` with `VSEEN` set for that player) never reads
`$0046` at all (the `NAV_V4` addition at `:975` only adds a `mode>=4` floor, which mode 3 and 8
both clear or fail on their own terms — mode 3 fails it, mode 8 passes it, so this floor doesn't
save mode 3 specifically). When this gate is true, the driver injects `START` and `RTS`s
(`:989`) *before* reaching the mode-3/mode-8 clears described above, on every hook, regardless
of what mode value the underlying game is in. Since `VSEEN1/2` are cleared by nothing except
that same mode-8 unconditional reset, whether this gate stays true throughout `7→3→8→4` depends
entirely on **when the base game repopulates the players' virus counts relative to those mode
transitions** — that's base-game engine behavior, not something in the driver patch, and this
write-up did not determine it (would need base ROM disassembly or an instrumented run
correlating `$0046` against `VCOUNT_P1`/`VCOUNT_P2` frame-by-frame, e.g. from the probe ring if
it captured `VCOUNT`, or a fourth harness arm). Left open rather than asserted either way.

**Practical takeaway for the fix**: regardless of how this resolves, moving the `MATCH_ACTIVE`
clear (or the fuller per-match reset) to fire the moment `fc_clear` detects a completed match
(`:982`) rather than depending on reaching `"menus"`/mode-8 — as already recommended in the
team-lead thread — sidesteps this whole question, since it acts before the ambiguity can matter
for any mode-transition path, auto-rematch or human-menu-driven alike.

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
    --seeds 50 --pills 8 --stress --stress-gravth 10 --out results.json
```

Wall time: ~2 minutes (400 game-simulations x 8 pills, well under the 2h budget). Full raw
per-pill records for every (arm, condition, seed, pill) are in `results.json`
(`_stress` key holds the stress-sweep records).
