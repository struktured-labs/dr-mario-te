# PRE-REG (2026-09-26, before any STEER5 arm runs): LEAF-evaluator screen under the real regime (sim-only)

**Why.** The couch deaths (RESULT_COUCH_TAP.md) are towers built on viruses left high in spawn columns 3–5, with
pills and garbage stacked on them. STEER4 showed root add-ons don't move it; the lever is the leaf evaluator. RTL
cost (see [[dr-mario-leaf-has-no-timing-budget]]: a new leaf term likely needs a pipeline stage) is paid only if
something passes.

**Baseline.** The STEER4 base, i.e. the shipping REACH+TAP build in sim:
- fw540 + the `reach_fw_tap(tap=2)` mask;
- unified DRTAPP=2 steering (`Steer(tap_unified=True)`);
- banked rows `steer4/remote/s4_base_*`. `s5_base` (w5 = 0) reproduces them field for field.

**Implementation.** `cascade_leaf5_x.py` holds mechanical copies of the leaf / ply-3 / root search functions. The new
terms are added at EVERY leaf value, on three paths:
- clearing leaves (`_leafv_ship` → `_eval_rtl`);
- non-clearing leaves (the CMD-6/7 delta path `_combine_terms`);
- the ply-3 fallback.

At w5 = 0 it is action-identical to the baseline decider (selfcheck 311/311). Terms were unit-tested on crafted
boards.
- ⚠ Finding while wiring: the existing extra `_eval_rtl` terms (R_SPAWNCOL, R_ENDH, R_LANEW, R_EDGEW, R_HOLESREL,
  R_CVX) are NOT in `_combine_terms`. So in the chain search those variants were applied ONLY at clearing leaves.
  Flagged for prior results that used them. STEER5's terms are added on both paths.
- Why not edit `fast_rtl_x` in place: `_eval_rtl` backs the bit-exact gate's blessed source and every other lane's
  numba cache. The term definitions below are written in the same per-column / per-virus vocabulary as
  `_eval_rtl`, so a passer maps onto LeafEval.sv's existing walks.

## Arms
gate (b), OWNER model, L11 MED, cap 600, n=600 paired seeds 36734.. step 2 (declared reuse). Paired vs the baseline.

| arm | term (leaf) | doses | vs prior art |
|---|---|---|---|
| `s5_bur32` / `s5_bur96` | **BUR35**: −W·Σ over viruses v in cols 3–5 of #(non-virus cells above v in its column whose colour ≠ v's) | 32 / 96 | R_BURIED (48, global) counts ALL cells above minus only the contiguous same-colour run directly above, for the nearest 2 viruses per column. BUR35 counts only NON-MATCHING cells (a matching cell anywhere above is free), every virus, cols 3–5 only. |
| `s5_acc60` / `s5_acc180` | **ACC35**: +W·#(viruses in cols 3–5 ACCESSIBLE: nothing non-matching above, OR a supported, open-above side slot where a straight drop lands beside it) | 60 / 180 (180 = a virus clear's imm) | No existing term rewards ACCESS. holes80 (holes 20→80, global) penalises empty cells under fill, a different notion, and was rejected on the firmware brain. |
| `s5_rb48` / `s5_rb144` | **RB35**: −W·Σ_{c=3..5} c_bur(c), R_BURIED's own per-column count, i.e. burial price 48 → 96 / 192 in cols 3–5 only | 48 / 144 | coef-opt raised R_BURIED 30→48 (shipped). **burial96 (48→96 GLOBAL) HARMED** under perfect execution (13.0→21.7%, contortion under garbage). RB35 prices burial only where towers kill (spawn columns) and leaves cols 0–2 and 6–7 at 48. |
| `s5_control` | the baseline on a FRESH block (n=464) | — | TUCKGUARD is a cart-side stranding veto, not an eval term, so it's not a comparator here. |

**Control block** (the seed space is exhausted: `seed_registry.py --suggest 600` finds no free run). Use the five
longest free runs, all `--check` PASS and registered AT LAUNCH:
- 4002–4462 (231), 40934–41098 (83), 17000–17098 (50), 17300–17398 (50), 20900–20998 (50);
- = 464 fresh streams, even seeds.

It sizes the seed-reuse bias as an unpaired difference of the baseline's rates: fresh vs reused block, bootstrap CI.

## Endpoints and bar
- **PRIMARY:** tap≤100 and whole-game tap-out, paired vs baseline, seed-bootstrap 95% CI.
- **PASS** = one primary CI entirely below 0 AND the other primary's upper CI ≤ +1 pp (the STEER4 rule).
- **SECONDARY, passers only:** VS race lam 6, n=300, vs the 177-s human at δ 2.65 / 2.0. Recommend only if the
  win-diff lower bound is ≥ −2 pp.
- **For any passer:** an RTL cost estimate (per-leaf computation; fits the existing pipeline or needs a stage), and
  the weight popcount (the RTL shift-add cost).
- 6 arms on reused seeds: a pass recommends a holdout (on the fresh-ish block) before any build.

**Compute.** Hetzner rbm-train-2 (IRON RULE, local↔remote md5 exactness gate) plus local at nice 19, ≤ 4 workers.
