# Oracle-ceiling arm — handoff

## Resumed status — 2026-08-10

The original handoff below is retained as history. Amendments A5–A8 and the
current executable supersede its “DIST is the headline” next step after the
programme lead clarified the question: **the deliberately unfair
`ORACLE-CLAIR` arm is the desired ideal-headroom measurement.** DIST remains a
useful opponent-clairvoyance decomposition, not a reason to suppress the ideal.

The lane is now executable rather than prose-only:

- Shared flip provenance uses `t_to_end = n_plies - 1 - ply`, champion `tie`,
  oracle `tie_score`, and champion `val_gap`.
- The shuffled-label null is hash-thinned with frozen q
  **169464/1000000**. On reserved seeds its accepted flip-rate ratio was
  **0.9271** versus CLAIR, inside the preregistered [0.90, 1.10] band. Two
  earlier calibration values were rejected before endpoint use and remain in
  `NULL_DOSE.json`/A6–A8.
- The executable combined verdict now forbids GO when clear is undecidable,
  fires N3 when the bad-end CI includes zero, and returns VOID if the mutant
  also reads GO or its full-N dose is mismatched.
- `run_full.sh` now runs G1g plus the DIST-key, null-thinning, real-game
  provenance, and verdict mutation gates. `run_oracle.py` freezes a runtime source/fit manifest and
  refuses to append under changed code or semantics.
- Segment results are banked in ascending seed order. The former
  `as_completed()` loop made an interrupted segment length-biased rather than
  the preregistered balanced prefix; resume summaries also omitted old rows.
  A9 fixes both before endpoint launch.
- DIST exists with collision-free candidate-common pressure keys; the old A1
  formula has an explicit killed collision inside the registered block.

**No dose-matched endpoint-null seed from 30000..38999 had been run when A8 was
sealed.** Reserved calibration used only 42000..42059.

Expected current runtime manifest (decision modules, runner, and Lulu fit):
`a67f47f15d4f82c125956dc2b37cc3c1bc1a0c84877310d5dfd27b96345b3bd8`.
The remote run must print the same rolled hash; paths may differ, hashes may not.
Historical pilot rows are intentionally not imported into the current output:
they predate this manifest/provenance contract. A10 requires replaying the
registered prefix and keeps the old n=125 result descriptive only.

Measured on the local 12-worker box, per 60 pairs:

| label | wall | summed worker time | projected N=9,000 wall |
|---|---:|---:|---:|
| true CLAIR | 7.4 min | 4,531 s | ~18.5 h |
| dose-matched shuffle | 15.8 min | 10,288 s | ~39.5 h |

The measured CCX23 supplies about 2.3 useful cores. Projected there: true
CLAIR ~82 h and shuffled null ~186 h. The fastest use of owned compute is
therefore **true CLAIR on Hetzner (4 workers) and the heavier null locally (12
workers)**, then fetch the remote true directory and analyse them together.

Launch helper (runs preflight, sync, fast remote gates, then a persistent
systemd unit). `launch` keeps an otherwise-idle node busy through true+null;
use `launch-true` for the faster two-box split described above:

```bash
bash deploy_hetzner_oracle.sh root@HOST ~/.ssh/hetzner_rbm launch
```

The environment running this resumption is network-sandboxed and cannot open
SSH sockets, so it could prepare and validate the helper but could not launch
the paid node itself.

**2026-08-10 ~23:45 EDT.** Written because both agent lanes hit the account's weekly token limit
(resets Aug 14, 8am ET). **Nothing failed.** The detached worker processes survived and kept
running. This file is everything needed to resume, by a human or another tool.

## What this arm is for

Does **any** root re-ranker move dies-ahead at all? Stage 2 spent 15,000 games on a learned
evaluator and returned NO_GO with a result **consistent with a slope of zero**, and no calibration
point from offline AUC to the endpoint has ever existed. This arm measures the **maximum**
reachable by any root re-ranker, so it is decisive in both directions:

- **NO_GO** ⇒ root re-ranking is structurally dead for dies-ahead; stop funding leaf evaluators
  for this endpoint. Close the lane on evidence.
- **GO at −2 to −3pp** ⇒ the AUC gap becomes priceable for the first time.

## Where things are

| | |
|---|---|
| worktree | `/home/struktured/projects/dr-mario-oracle-wt` |
| branch | `oracle-ceiling` (pushed, SSH) |
| dir | `experiments/eval47/stage2/oracle/` |
| prereg sealed | `5980a79` · runner `6a5180b` · **amendment A1** `22d171d` |

## STATUS: gates ALL PASS, both directions

```
G1g forks side-effect free : 4/4      G1g MUTANT leaky fork broke: 4/4      G1g PASS
G1a_off_identity_vs_pressure_rig  12/12     G1a_action_determinism        12/12
G1b_reversed_order_MUST_break     12/12     G1c_fork_capsule_independence  True
G1c_mutant_lambda_attach_MUST_share True    G1d_liveness_true_differs      12/12
G1e_gated_frac_of_plies          0.3325     G1f_shuffle_differs_from_true  12/12
GATES PASS
```

Logs in `logs/`, machine-readable in `out/gate_*.json`.

**G1g deserves a note.** It did not exist in the sealed prereg — nothing tested whether a fork
leaks into the parent, and `G1a`'s `const` mode short-circuits *before* the fork routine is called,
so it could never have caught it. On seed 41002, **516 real forks execute and the game stays
bit-identical to the champion**; the leaky variant (one line: `copy.deepcopy(env)` → `env`) drives
the same seed to 144 pills instead of 221. A gate that would have passed a broken arm was found and
closed before any verdict.

## ⚠ THE PILOT NUMBERS ARE THE **CLAIRVOYANT** ARM. DO NOT QUOTE THEM AS A CEILING.

`seg_030000`, n=125 pairs, **`ORACLE-CLAIR`**:

| metric | base | oracle |
|---|---|---|
| dies-ahead | 15.2% | **0.8%** |
| clear | 72.8% | 94.4% |
| topout | 17.6% | 0.8% |
| stall | 9.6% | 4.8% |

flip rate 3.39% of plies · gated 43.1% of plies · 24,860 forks · 0.138 games/s at 5 workers.

**Why this is not the answer.** The fork observes dr. lulu's **realized** volley schedule,
*including target columns*. `bursty_model.py:578` derives volley size and columns from
`(seed, pills_placed)` alone — the board is not an argument — so a fork at pill *p* reads the exact
attack the live game will deliver at *p* and can pre-clear those columns across the 15-pill horizon.
**No cart policy can do that**, so a GO on this channel would be unactionable. Amendment A1 renamed
this arm `ORACLE-CLAIR` and demoted it.

## NEXT STEPS, in order

1. **Implement `ORACLE-DIST` — this is the headline arm and it does not exist yet.** Identical
   gate / TOPK=4 / HORIZON=15 / selection / seeds / endpoint / verdict; the only change is that
   inside a fork, injection is called with `seed_eff = seed + 7919*(ply+1)` in place of `seed`.
   Same rig code path — do not re-implement physics. `seed_eff` varies by ply but **not by
   candidate**, so all four candidates at a ply face the same sampled future (CRN across
   candidates). K=1 sample/ply is registered primary; it is noisier than expectimax and therefore
   **understates** the ceiling — conservative for a NO_GO, dangerous for a GO. Say which way it
   cuts whenever the number is quoted.
2. **Apply the schema arbitration in the same edit**: `t_to_end` → `n_plies - 1 - ply` (0-based,
   "plies remaining after this one"); rename `tie` → `tie_score` (tied in the arm's own re-rank
   score); adopt `val_gap` (champion points surrendered). Shared columns every arm emits: ply,
   t_to_end, viruses, maxh, d_spawn_h, champ_rank_chosen, base_action, trt_action, tie, val_gap,
   seed, arm.
3. **Register the change as amendment A2** before running: DIST + shuffle at full Tier A N,
   CLAIR at ~2,000 purely to size the clairvoyance gap.
4. **Raise the worker cap 6 → 12** in `run_oracle.py`. The cap is inherited from an OOM history
   that does not apply here: measured 184 MB/worker against 77 GB free. This halves wall-clock.
5. **Report dies-ahead per 100 pills alongside the raw endpoint.** The oracle finishes ~58 pills
   sooner, so part of the drop is reduced exposure rather than better decisions. But do not net the
   tempo gain out entirely — finishing faster is itself a win condition here; speed is how the
   champion loses to a human.

### Rules that must not be dropped

- **The programme decides on `ORACLE-DIST` alone.** DIST NO_GO closes the lane even if CLAIR is GO.
  A large CLAIR number must not be allowed to soften a DIST null — CLAIR-GO-with-DIST-NO_GO would
  only mean the headroom lives in opponent modelling, which is a different lane.
- **Never edit `oracle_arm.py` while a run is in flight** — the chained arm re-imports it on worker
  spawn and would be paired against different code.
- **N ≥ 7,826 paired seeds** for any clear-rate gate to be passable at all (`SE = sqrt(d/N)`,
  back-validated against stage-2's published CIs). Register 9,000. Below that, declare the
  clear-rate co-primary NOT DECIDABLE in advance — never report it as a pass.
- **Count 300-pill stalls at parity with topouts.** In stage 2, 19 of 28 avoided topouts reappeared
  as stalls and the condition never fired.

## Running it

```bash
bash experiments/eval47/stage2/oracle/run_full.sh A <WORKERS>
```

Runs the gates first and **aborts if they fail**, then the arm, then the killed mutant, then the
pre-registered verdict. **Resumable** — re-running the identical line skips every banked seed
rather than replaying it. Tier A ≈ 28 h at 12 workers; Tier B (5,500) ≈ 17 h.

## Related

- Per-ply flip provenance shipped separately on branch `flip-provenance` @ `5312267`
  (7/7 mutation gate red one defect at a time, clean tree green before and after). A
  schema-convergence follow-up commit may not have landed before the lane died — check.
- ⚠ `nes_pills.py:93` still installs `env._rand_pill = lambda: ...`; the qa-wt and local copies are
  **byte-identical and both unfixed**. The 2026-08-07 repair was a workaround inside holepoker's
  `vs_poker`, not a fix to `nes_pills`. **Any lane that deepcopies an attached env is exposed.**
  This arm is safe only because it installs its own `PillDraw` object and G1c proves it.
