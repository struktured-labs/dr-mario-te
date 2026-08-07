# depth4-transfer: can d4's sequential edge be named as a d3 eval term?

**Task #22.** Verdict: **DEAD.**

## Hypothesis (falsifiable)

Depth-4's measured edge over the shipped depth-3 search was already shown (depth4/README.md,
Phase 3 oracle adjudication) to be **sequential** — invisible at the single-move level, alive
only as a clustered rescue in 4 of 119 games. Nobody had asked what those setups have in
*common*. If d4-better disagreements share a compact structural signature in hand-craftable
board features (a kept-open column, a parity, a shape it avoids), that signature could be
encoded as a cheap d3 eval term, buying d4's benefit at d3's cost. **This could be false**: if a
probe on hand features can't beat ~60% held-out AUC separating "d4's move proved better" from
"d3's move proved better," the edge has no learnable local signature and can't be distilled this
way.

## Cheapest kill: re-mine the corpus that already exists, don't resimulate

`experiments/depth4/` (07-31, `depth4-retest` lane) already produced exactly the artifact this
hypothesis needs and left it vendored:

- `results/disagree_nes_k3-6_corpus.jsonl` — 1809 anchored d3-vs-d4 disagreements, full 128-byte
  board + virus mask + current/next capsules, from **real NES-stream L11 trajectories** (119
  distinct seeds/games), engine = `fast_rtl_x` (the shipped decide path's own kernel, not py65).
- `results/adjudicate_rows.jsonl` — the Phase-3 oracle verdict for every row: both `a3` and `a4`
  played forward on the **identical true capsule stream**, d3 steering both branches afterward
  (isolates the value of the one differing move, net of downstream execution), replay-gated
  1809/1809 clean.

Joining these on `(seed, k)` and re-analyzing them costs no new simulation — this is the
cheapest possible test of the hypothesis, and it satisfies the task's `n>=300` bar by ~6x
(974 labeled positions survive margin-gating, drawn from 117 real games).

Script: `mine_signature.py`.

## Method

- **Label**: `value = cost(d3-branch) - cost(d4-branch)`, `cost = pills if res==clear else 300`
  (the depth4 A/B's own censoring convention). Positive -> d4 cheaper. Binarized with a +/-8-pill
  noise margin (search/exec granularity) dropped as ties; robustness-checked at margins
  {0, 4, 15, 20}.
- **Features** (30, all knowable *before* the outcome — no leakage): board shape (per-column
  fill counts, open-column count, height std/max/min, topmost filled row), remaining-virus color
  histogram, `regime`/`vc`/`ply`, the disagreement's own structure (`kind` = col-only /
  orient-only / both, column distance between `a3`/`a4`, orientation flip), and the literal
  candidate mechanism named in the task — **does d4's move target a shorter / more-open column
  than d3's** — plus current/next-pill color-match flags.
- **Split**: `GroupKFold` by **seed** (5 folds), not by row. The depth4 README's own clustering
  finding (rescues concentrate in 4 games; row-level tests overstate significance) makes a
  row-level split invalid here — a game is the correct unit, same discipline this repo already
  learned the hard way once on this exact corpus.
- **Probes**: logistic regression, depth-3 decision tree, depth-4 random forest (200 trees) —
  cheap, standard, no reason a real structural signature would need more.

## Results

| probe | held-out AUC (mean of 5 seed-grouped folds) |
|---|---|
| logistic regression | **0.549** |
| decision tree (depth 3) | 0.499 |
| random forest (depth 4) | 0.515 |

Margin-sweep robustness (n_labeled / seeds / best probe mean AUC):

| margin | n labeled | seeds | logreg | forest |
|---|---|---|---|---|
| 0 | 1434 | 118 | 0.537 | 0.500 |
| 4 | 1170 | 118 | 0.562 | 0.550 |
| **8 (main)** | 974 | 117 | 0.549 | 0.515 |
| 15 | 716 | 115 | 0.578 | 0.547 |
| 20 | 564 | 103 | 0.569 | 0.511 |

Best across every probe and every margin tried: **0.578**, always below the 0.60 kill line.

The literal hypothesized mechanisms, tested individually (in-sample AUC, upper bound):

| feature | AUC | mean\|d4-better | mean\|d3-better |
|---|---|---|---|
| `d4_targets_shorter_col` | **0.500** | 0.406 | 0.405 |
| `d4_targets_open_col` | 0.518 | 0.078 | 0.041 |
| `height_delta_d4_minus_d3` | 0.501 | -0.307 | -0.359 |
| `open_cols` (board-wide) | 0.517 | 0.412 | 0.362 |
| `kind_both`/`kind_col_only`/`kind_orient_only` | 0.500-0.506 | — | — |
| `orient_flip` | 0.505 | 0.445 | 0.455 |

"d4 keeps a column open" — the concrete example named in the task prompt — is **exactly chance**
(0.500). Nothing in the 30-feature set clears 0.55 even in-sample, let alone held out. The
best-ranked feature board-wide (`v2`, a virus-color count) tops out at 0.547 in-sample.

## Interpretation

This sharpens rather than restates the standing finding. `depth4/README.md` had already shown
the edge lives in cross-move steering, not single positions, and that even at the **game** level
the net-rescue effect spans zero (Wilcoxon p=0.389, 4 net-positive vs 14 net-negative seeds).
That result left open the possibility that the *positive* rescues, even if outnumbered, might
still share a common shape worth encoding narrowly (a term doesn't need to fire on every
position to be worth shipping). This experiment closes that door too: even restricted to
"disagreements with a directional pills verdict" (974 of 1809 rows, well-powered), no hand
feature or shallow model built from the board state distinguishes a d4-better disagreement from
a d3-better one above noise. The edge is not merely diffuse — it is **statistically invisible in
this feature space**, which is the operational meaning of "cannot be distilled into a d3 eval
term" for this task.

**What would NOT be settled by this result**: a probe on richer features (multi-ply trajectory
embeddings, sequences of consecutive placements rather than single positions) might still find
structure. But the existing game-level null (Wilcoxon p=0.389, CI spanning zero) already argues
against that being fruitful — if the rescues themselves aren't a net effect at the game level, a
sequence-level classifier is chasing a signal whose existence is itself unconfirmed. Recommend
closing task #22 as refuted rather than escalating to sequence models.

## Files

| file | what |
|---|---|
| `mine_signature.py` | join, feature build, label, GroupKFold-by-seed probe, margin sweep hook |
| `results_signature.json` | main-run (margin=8) numbers, machine-readable |
| Inputs (not copied, read in place) | `experiments/depth4/results/disagree_nes_k3-6_corpus.jsonl`, `experiments/depth4/results/adjudicate_rows.jsonl` |

Reproduce:
```bash
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
$PY mine_signature.py
```
(needs `scikit-learn`, installed into the shared venv via `uv pip install --python $PY scikit-learn`;
not previously present there.)
