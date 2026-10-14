# RESULT TAPOUT (2026-10-13): what kills the AI vs dr. lulu, and do DANGER root penalties cut it?

- **Status: COMPLETE.** Stage 0 (characterisation) and stage 1 (screen, main, Q2) are done. The autopilot
  (`tapout_auto.sh`, systemd unit `tapout-auto`) applied the pre-registered screen rule, ran the main and Q2 phases and
  wrote `tapout/analysis.txt` once, after every farm reported DONE (`AUTO DONE 2026-10-13T22:13:53Z`).
- **Pre-registration:** `PREREG_TAPOUT.md` (f7e5bd00, arms eaed99cd), committed before any danger-arm game.
- **Opponent:** dr. lulu at measured pace (M 167.5 s), STEER14 harness and outcome model (`vs_race.evaluate`), V11
  firmware model. Baseline = the banked STEER14 `S14_d16_u8` rows (A16 + u8).
- **Everything here is a simulator result.** No hardware, RTL, firmware or cart build was touched.

## Short answer
1. **Stage 0:** most kills (about 75-79 %) are a slow THROAT creep (the centre columns sit within 2 rows of the top for
   about 45-50 pills before a spawn is blocked). Garbage triggers about 21-25 %. Searches cut short are not a cause.
2. **Stage 1:** the screen selected D3, D1, D4. **All three HELP** on the primary endpoint (kill-rate Bonferroni upper
   < 0) and pass the co-primary guard (total-loss Bonferroni upper <= +1.0 pp, point estimate <= 0). In fact total
   LULU loss falls for all three.
3. **Lowest kill rate: D4** (quadratic, P 40, h0 10): kills 6.98 % -> 3.27 %, −3.71 pp [Bonferroni −4.67, −2.71];
   total LULU loss 12.61 % -> 10.35 %, −2.25 [Bonferroni −3.55, −0.96]. **Cost:** slow losses rise by +1.45
   [Bonferroni +0.43, +2.45]. This harm is established; the arm plays slower (+5.3 pills per game).
4. **Runner-up: D1** (linear, P 60, h0 11): kills −3.14 [Bonferroni −4.07, −2.20], the best total loss −2.53
   [Bonferroni −3.67, −1.36]. Its slow-loss rise +0.61 [Bonferroni −0.27, +1.49] is not established.
5. **Q2 (descriptive):** D4 at today's gate k32 vs `S14_d4_k32` (n 2,000): kill −1.70 [−2.95, −0.45], loss −2.00
   [−4.15, +0.20].

## 1. Stage 0: what the tap-outs are (sim, STEER14 harness, `tapout/characterisation.txt`)
Every tap-out of both baselines on the STEER14 main block (5,100 seeds) was replayed under the trace wrapper, plus 200
random clears of each. **Identity: 1,455 / 1,455 replays reproduce the banked STEER14 rows** (t_end, how, pills).

| | A16 + u8 | FAIR2PLUS-equiv (d4 k32) |
|---|---|---|
| Kill losses (tap-out before her finish) | 356 / 5,100 (7.0 %) | 307 / 5,100 (6.0 %) |
| Tap-outs at any time | 478 | 577 |
| Kill: pills at death p10/50/90 | 52 / 124 / 202 | 50 / 110 / 178 |
| Kill: time at death (s) p10/50/90 | 70 / 183 / 294 | 74 / 163 / 294 |
| Kill: viruses left at death p10/50/90 | 5 / 11 / 28 | 5 / 14 / 30 |
| Kill: died with >= 10 viruses left | 58 % | 65 % |
| Kill: pills spent with the spawn throat (cols 2-5) at height >= 14 before death, median | 49 | 43 |
| Kill: viruses left when the throat first reached 14, median | 22 | 24 |
| Clears that ever reach throat 14 | 18 % | 20 % |
| Kill: garbage tiles in the last 8 pills, median (p90) | 0 (4) | 2 (5) |
| Class (pre-registered rule, last 8 pills): THROAT / GARBAGE / other | 281 / 74 / 1 | 228 / 77 / 2 |

**Dominant cause: a slow THROAT CREEP, not a sudden garbage kill and not the slam gate.**
- About 79 % (A16 + u8) and 74 % (FAIR2PLUS) of kills are THROAT. The centre columns reach within 2 rows of the top
  mid-game: the median kill game has about 22 viruses left at that point. The AI then lives up there for about 45-50
  pills before a spawn is blocked.
- Garbage is the proximate trigger in only about 21-25 % of kills.
- **Execution degrades up there.** In kill games the landing differs from the chip's final answer on 4.2 % of pills
  while the throat is at 14 or higher, against 1.8 % below it (A16 + u8). In the last 8 pills it is 12.5 %, against
  0.6 % in clears. Reach to the target is lost on a tall board.
- **Search cut short is NOT a cause.** Stability locks (before DONE) are rarer in the last 8 pills of kills (45 %)
  than across clears (80 %) on A16 + u8. A16 + u8 has more kills than FAIR2PLUS (356 vs 307), but that comes from
  playing longer under the same creep, not from u8 cutting searches.
- In 107 of 356 A16 + u8 kills the throat came back down to 12 or below after first reaching 14 and then went up again.
  These are recoverable boards the brain did not keep low.

## 2. Stage 1: DANGER root penalties (screen, main, Q2)
Arms (all A16 + u8, root-side penalty on the soft b1 of each root; Hs = max height of the throat, cols 2-5):

| arm | kind | P | h0 | gate |
|---|---|---|---|---|
| D1 | spawn (linear) | 60 | 11 | - |
| D2 | spawn (linear) | 200 | 11 | - |
| D3 | spawn (linear) | 200 | 13 | - |
| D4 | spawnq (quadratic) | 40 | 10 | - |
| D5 | spawn (linear) | 500 | 12 | root Hs >= 11 |

### 2.1 Screen (`tapout/screen_select.txt`; 600 fresh seeds 47000.. step 2, disjoint from the main block)
Rule (prereg sec. 3, written before any screen row): rank by total LULU loss; keep up to 3 arms whose tap-out-any count
is below the baseline's; ties broken by fewer kills.

| arm | LULU loss | kill | tap-out any | decisions changed | meta_pen_mismatch | qualifies (top < 44) |
|---|---|---|---|---|---|---|
| `T_a16_u8` (base) | 60 (10.0 %) | 27 (4.5 %) | 44 | - | - | - |
| D3 | **49** (8.2 %) | 22 | 37 | 419 / 78,407 (0.5 %) | 0 | yes, rank 1 |
| D1 | **50** (8.3 %) | 15 | 32 | 1,269 / 79,711 (1.6 %) | 0 | yes, rank 2 |
| D4 | **55** (9.2 %) | 20 | 32 | 2,724 / 79,648 (3.4 %) | 0 | yes, rank 3 |
| D2 | 72 (12.0 %) | 23 | 42 | 2,718 / 79,339 (3.4 %) | 0 | yes, rank 4 (not taken) |
| D5 | 63 (10.5 %) | 25 | 46 | 1,699 / 79,903 (2.1 %) | 0 | no |

**Selected: D3, D1, D4** (`tapout/selected.txt`). The main phase therefore uses Bonferroni K = 3.

### 2.2 Main (`tapout/analysis.txt`; n 5,100, seeds 44300.. step 2, paired by seed vs the banked `S14_d16_u8` rows)
Diffs are arm − A16 + u8 in pp, with a 95 % paired bootstrap (10,000 resamples over seeds) and a Bonferroni interval
(two-sided alpha 0.05/3).

| endpoint | A16 + u8 (base) | D3 | D1 | D4 |
|---|---|---|---|---|
| **kill** (primary) | 6.98 % (356) | 4.43 % (226) | 3.84 % (196) | **3.27 %** (167) |
| diff [95 %] | | −2.55 [−3.18, −1.92] | −3.14 [−3.90, −2.37] | −3.71 [−4.51, −2.88] |
| diff {Bonferroni} | | **{−3.31, −1.80}** | **{−4.07, −2.20}** | **{−4.67, −2.71}** |
| **total LULU loss** (guard) | 12.61 % (643) | 10.61 % (541) | **10.08 %** (514) | 10.35 % (528) |
| diff [95 %] | | −2.00 [−2.61, −1.39] | −2.53 [−3.47, −1.57] | −2.25 [−3.31, −1.20] |
| diff {Bonferroni} | | **{−2.75, −1.25}** | **{−3.67, −1.36}** | **{−3.55, −0.96}** |
| slow loss | 5.63 % (287) | 6.18 % (315) | 6.24 % (318) | 7.08 % (361) |
| diff [95 %] | | +0.55 [+0.06, +1.04] | +0.61 [−0.14, +1.33] | +1.45 [+0.63, +2.25] |
| diff {Bonferroni} | | {−0.06, +1.18} | {−0.27, +1.49} | **{+0.43, +2.45}** |
| tap-out any time | 9.37 % (478) | 7.25 % (370) | 6.53 % (333) | 6.31 % (322) |
| diff [95 %] {Bonferroni} | | −2.12 [−2.73, −1.53] {−2.86, −1.39} | −2.84 [−3.71, −1.98] {−3.90, −1.78} | −3.06 [−4.02, −2.08] {−4.24, −1.88} |
| kill churn fixed / new | | 196 / 66 | 276 / 116 | 319 / 130 |
| loss churn fixed / new | | 180 / 78 | 369 / 240 | 444 / 329 |
| decisions changed | | 5,128 / 663,264 (0.77 %) | 11,392 / 666,653 (1.71 %) | 24,295 / 679,593 (3.57 %) |
| meta_pen_mismatch | | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) |
| pills / game (mean) | 128.0 | 130.1 | 130.7 | 133.3 |
| t_clear, clears (median) | 186.4 s | 187.2 s | 187.8 s | 190.3 s |

**Decision rule (prereg sec. 4):**
- Primary: all three arms HELP (Bonferroni upper < 0 on kill).
- Co-primary guard: all three pass (Bonferroni upper <= +1.0 pp on total loss, and point estimate <= 0). Every
  Bonferroni upper bound on total loss is itself below 0.
- META pen mismatch is 0 for every arm, below the 1 % flag, so no arm's tempo is suspect on that count.

**Mechanism:** each arm turns some kills into slow losses. Compared with the baseline:
- D3: −130 kills, +28 slow losses.
- D1: −160 kills, +31 slow losses.
- D4: −189 kills, +74 slow losses.

The penalty keeps the throat lower at the cost of a few more pills per game. Only D4's slow-loss rise is established
under Bonferroni.

**Between the arms** (paired, 95 %, descriptive; not pre-registered contrasts):

| | kill | total loss | slow |
|---|---|---|---|
| D4 − D1 | −0.57 [−1.22, +0.08] | +0.27 [−0.69, +1.24] | +0.84 [+0.02, +1.65] |
| D4 − D3 | −1.16 [−1.86, −0.45] | −0.25 [−1.27, +0.75] | +0.90 [+0.06, +1.75] |
| D1 − D3 | −0.59 [−1.25, +0.10] | −0.53 [−1.41, +0.39] | +0.06 [−0.67, +0.78] |

D4 has fewer kills than D3. Its edge over D1 on kills (−0.57) is not established. On total loss the three arms cannot
be separated.

### 2.3 Q2 (descriptive): the lowest-kill arm at today's gate
D4 (the selected arm with the fewest main-block kills, as chosen by the autopilot) at k32, compared with the banked
`S14_d4_k32` (today's FAIR2PLUS-equivalent) on 2,000 seeds (44300..48298 step 2). Paired, 95 %, no decision rule.

| endpoint | `S14_d4_k32` | D4 at k32 | diff [95 %] |
|---|---|---|---|
| kill | 5.85 % | 4.15 % | −1.70 [−2.95, −0.45] |
| total LULU loss | 24.95 % | 22.95 % | −2.00 [−4.15, +0.20] |
| slow loss | 19.10 % | 18.80 % | −0.30 [−2.35, +1.75] |
| tap-out any time | 11.40 % | 8.05 % | −3.35 [−5.05, −1.65] |

Decisions changed: 10,037 / 273,364 (3.67 %). meta_pen_mismatch: 0. The kill reduction carries over to today's gate,
where it is smaller. The total-loss interval includes 0.

### 2.4 Identity re-check (prereg sec. 4)
`T_a16_u8` (the wrapper with no penalty) was re-run on 50 main-block seeds: 44300, 46300, 48300, 50300 and 52300,
10 each, step 2. **50 / 50 rows equal the banked `S14_d16_u8` rows on every game key** (how, t_end, pills, vleft,
sent, tiles, steer, stuck, tap, rule, ...) and on every `knob` counter. The only differences are the wrapper's
provenance block `rig` and the extra counter `meta_pen_mismatch` (0). **Note:** this re-check ran on 2026-10-13 after
the autopilot had already written `analysis.txt`, not before it as the prereg states. The analysis was not changed or
re-run because of it. Rows: `tapout/rows_ident_recheck.jsonl.gz`. Stage 0 had already reproduced 1,455 / 1,455
banked rows through the same wrapper.

### 2.5 Recommendation
- **D4 (`spawnq`, P 40, h0 10) is the recommended arm for the next (firmware) step.** It has the lowest kill rate of
  the arms tested: 3.27 % vs 6.98 %, −3.71 pp [Bonferroni −4.67, −2.71]. The owner's first metric is AI tap-outs. D4
  also lowers total LULU loss by −2.25 [Bonferroni −3.55, −0.96].
- **D4's cost is established:** about +1.45 pp of slow losses [Bonferroni +0.43, +2.45]. It plays about 5 pills per
  game more (median clear +3.9 s). The net effect on total loss is still a reduction.
- **D1 (`spawn`, P 60, h0 11) is the close runner-up and the fallback.** It has the best total loss (−2.53
  [Bonferroni −3.67, −1.36]) and kills −3.14 [Bonferroni −4.07, −2.20]. Its slow-loss rise is not established.
  - It is linear, so it needs no squaring in firmware.
  - It changes half as many decisions as D4 (1.7 % vs 3.6 %).
  - D4's kill edge over D1 (−0.57 [−1.22, +0.08]) is not established.
  - If the slow-loss cost or the firmware size of D4 matters more than the last half point of kills, D1 is the
    pick.
- **Not measured here:** the guards outside the LULU race (the owner race and the gate-b tap-out), A16 + u8 against
  other opponents, and anything on hardware. These guards should be run in the sim on the chosen arm before a
  firmware build.

## 3. What the recommended arm needs outside the sim
- **Firmware only (6502 root side), no RTL.** The penalty is applied per root after DRVETO, on the soft b1 board that
  the firmware already builds for STEER10's `ereach`/`edig` rules (`rules_steer10._reach_pen` is the closest
  precedent). That covers a column-height scan of 4 columns per root (32 roots), a compare and a multiply-subtract
  with 16-bit saturation. D4 (`spawnq`) also squares the excess (Hs − h0, at most 6 on a 16-row board), which a
  7-entry table covers. D1 (`spawn`) is linear and needs only the multiply.
- **Size:** comparable to ereach, estimated at about 60-120 bytes of 6502 plus a cycle check against the NMI budget
  (the worst frame is currently 28,001 / 29,780).
- **Then needed:**
  - a co-sim gate: Verilator copro plus firmware against `tapout_run`'s choices on fixed boards;
  - a cart build, the existing cart gates and Mesen chained replays;
  - a bluemage soak and a couch test (owner).
- The META-with-penalty publish timeline is a model assumption. The firmware would need to apply pen inside the
  anytime publish loop so that intermediate publishes see it; `meta_pen_mismatch` counts where the model had to force
  this.

## 4. Data and reproduction
- `tapout/rows_stage1_screen.jsonl.gz`: 3,600 rows, the screen (6 arms x 600 seeds). This is the concatenation of
  `tapout/screen/*.jsonl` in file-name order.
- `tapout/rows_stage1_main.jsonl.gz`: 17,300 rows. It has the main phase (`T_D3_u8`, `T_D1_u8`, `T_D4_u8`, 5,100
  each) and Q2 (`T_D4_k32`, 2,000). This is the concatenation of `tapout/main/*.jsonl` in file-name order. There is
  one row per (arm, seed) and no duplicates.
- `tapout/screen_select.txt`, `tapout/selected.txt` and `tapout/analysis.txt` are the autopilot's outputs.
  `tapout/jobs_screen.txt`, `tapout/jobs_main.txt` and `tapout/jobs_q2.txt` are the job lists.
- `tapout/rows_ident_recheck.jsonl.gz`: 50 rows, the identity re-check (sec. 2.4).
- Stage 0: `tapout/rows_stage0.jsonl.gz`, `tapout/traces_stage0.jsonl.gz`, `tapout/characterisation.txt`.
- **To re-run the analysis:** `analyze_tapout.py` globs per-arm files. Unpack with
  `mkdir -p tapout/main tapout/screen` and then
  `zcat tapout/rows_stage1_main.jsonl.gz | python3 -c 'import sys,json;[open("tapout/main/"+json.loads(l)["arm"].split("~")[0]+"_all.jsonl","a").write(l) for l in sys.stdin]'`.
  Do the same for screen into `tapout/screen/`. Then run `python analyze_tapout.py main`. The baseline rows come from
  STEER14 (`steer14/main/`).

## Addendum A (2026-10-14, RUNNING): owner-race + gate-b guards on D4 / D1
- **Design:** `PREREG_TAPOUT.md` addendum A (c295a9f8), committed before any guard game of a danger arm.
  - Both guards as STEER14 defines them, on 5,100 paired seeds vs A16 + u8.
  - Plus D4 / D1 at today's gate k32 on 1,000 seeds (descriptive).
- **Unit:** `tapout-guard` (20 workers, nice 19). Analysis: `analyze_tapout_guard.py` → `tapout/guard_analysis.txt`.
- **Recommendation status:** D4 (fallback D1) stands pending these guards.
- **Firmware sketch for the winner:** `tapout/FIRMWARE_SKETCH_DANGER.md`.
  - About 77 bytes of copro 6502 ROM and 1 zp byte.
  - About 16k copro cycles per decision (≈ 0.011 f MiSTer).
  - The cart NMI budget (28,001 / 29,780) is unchanged, because the penalty runs on the copro.
  - No RTL.
