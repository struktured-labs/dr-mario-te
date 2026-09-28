# PREREG (2026-09-27): STEER6c — does the STEER6 gain survive the RTL route's answer latency?

Written and committed BEFORE any STEER6c game. It was requested by the coordinator mid-STEER6b: in our regime the
answer latency (T_LAT, median 19 f) drives the steering model and the reach mask, and STEER1–3 showed timing is
where the couch deaths came from.

## 1. Latency cost of each RTL route (`steer6_latency.py` → `steer6/latency_leaves.jsonl`)
**Leaf counts.** Leaves per root search were counted with the firmware search's own enumeration on 1,166 real
ANTIBODY decision boards. The firmware is the golden mirror bit-for-bit.
- All decisions: median **26,129**, max 29,730.
- Decisions at ≤ 4 viruses: median **17,844**, p95 29,673.
- Clearing (NODE-path) share: 7.8%.

**Calibration.**
- The 69-board co-sim median DONE latency is 48.3M clocks, i.e. ≈ **1,849 clocks per leaf** on average.
- So each extra cycle per leaf costs ≈ **0.05%** of search time.
- Clocks: MiSTer copro 85.909 MHz; Pocket 54.669 MHz.

| route | extra cycles/leaf | Δ answer latency on ACTIVE decisions (MiSTer) | (Pocket) |
|---|---|---|---|
| (d) dist_target, sequential: 1 window per cycle; target row/col cells latched during S_COLWALK / updated in the delta path | 8 | **+0.10 f median, +0.17 f p95/max** | +0.16 / +0.26 |
| (a) dist_end, sequential per virus: 12 cell reads + 8 window steps × ≤ 4 viruses | 20 × nv | +0.49 f median, **+1.25 f p95**, +1.66 f max | +0.77 / +1.96 / +2.60 |
| (c) dist_stall, sequential per virus × ALL viruses when active | 20 × nv | +3.0 f median, **+17.6 f p95**, +20.0 f max | +4.7 / +27.6 / +31.4 |
| any, CONCURRENT route: an independent D-FSM running beside the existing ≥ 10-state delta sequence / the 128-cycle column walk | 0 (if it finishes first) | 0 | 0 |

## 2. Re-run with T_LAT shifted (`steer6_dlat.py`; ΔT = 0 reproduces the screen rows 4/4)
**How the shift is applied.** It goes to EVERY decision, which is conservative because the cost is only paid while
the term is active.
- steer_model answer frame +Δ.
- reach_fw_tap `T_LAT` 19 → 19 + Δ: the mask constant, matched.
- vs_race `BASE_F` +Δ per ply: tempo, with no overlap credit.
- gate-(b) clock +Δ/60 s.

**Runs.** ΔT is the MiSTer p95/max cost rounded UP to whole frames:
- **(d) `s6_dist_target60` @ ΔT = +1 f.**
- **(a) `s6_dist_end60` @ ΔT = +2 f.**
- (c) `s6_dist_stall60` @ ΔT = +18 f runs ONLY if STEER6b recommends (c). Its sequential route is otherwise
  disqualified on latency, and a concurrent route would be required.

**Seeds and instruments.** The screen block 37934–39132 (600 paired), where ANTIBODY and each arm at ΔT = 0 are
banked. Gate (b) OWNER-0804, plus race lam 6 at M 177 δ 2.65.

## 3. Bar (per arm, 95% seed-bootstrap CIs, paired vs ANTIBODY at nominal latency)
**GAIN SURVIVES** iff:
- tap-out Δ upper CI < 0; AND
- race Δ lower CI ≥ −2 pp; AND
- tap≤100 Δ upper CI ≤ +1 pp.

Also reported: the latency cost itself, arm@ΔT − arm@0, paired.

**If the chosen arm's gain does NOT survive,** a 0-added-cycle RTL route (concurrent D-FSM, or a fold into the
existing column walk the way HSV was folded) becomes a hard requirement of the build.

## 4. Pick rationale
"Cheapest RTL" in the STEER6b recommendation rule means TOTAL cost: area, AND latency (measured here), AND fit risk.
The STEER6b recommendation is re-stated in the result with this column included.

**Execution:** after STEER6b finishes. 2 arms × (600 + 600) = 2,400 games (+1,200 if (c)). Hetzner + local.

## ADDENDUM (2026-09-28, POST-HOC sensitivity, written before any STEER6c-s game)
**Primary result, as pre-registered:** with a whole-game shift of +1 f (dist_target) and +2 f (dist_end), BOTH
gains **do NOT survive**.
- dist_target@+1: tap-out −1.50 [−4.67, +1.67]; latency cost vs @0 +2.67 [+0.33, +5.00].
- dist_end@+2: tap-out −2.00; cost +4.00, race −6.5.

**Why that test overstates the cost.**
- The real cost of the sequential routes is paid only on ACTIVE decisions (root ≤ 4 viruses).
- Its size is FRACTIONAL: dist_target +0.10 f median / +0.17 f max; dist_end +0.49 f median / +1.25 f p95.
- The sim takes whole frames, so the pre-registered test rounded up to +1 and +2 f and applied them to EVERY
  decision. That is 6–10× the dist_target route's real cost, spread over the whole game.

**Sensitivity STEER6c-s** (`steer6_dlat_frac.py`; with no shift it reproduces the screen rows 5/5).
- **How the shift is realised:**
  - On active decisions only: floor(D) + Bernoulli(frac(D)) extra whole frames, deterministic per board.
  - D is the MiSTer p95 cost: **dist_target D = 0.17 f**, **dist_end D = 1.25 f**.
  - Inactive decisions run at nominal latency.
- **Samples and bar:** the same 600 gate-b + 600 race seeds as STEER6c, and the same bar.
- **Labelled POST-HOC.**
  - If the gain survives here but failed the pre-registered test, the conclusion is that the sequential route is
    probably acceptable but not demonstrated.
  - The 0-added-cycle concurrent route stays the RECOMMENDED build requirement either way.
