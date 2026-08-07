# Tier 3: Adversarial Opponent AI

Objective: find an opponent policy that maximises the shipped champion's DEATH
rate (board-overflow topout), not the opponent's own win rate. See
`ADVERSARY_T3.md` for the full report once the search + measurements finish;
this file just tracks what was reused vs newly built, for anyone auditing later.

## The champion, pinned by value

`fast_rtl_x.variant("winner")` weights + `cascade_stranded_x.StrandedChainD3Decider`
(`w_chain=180, ws=20`). This is h2h_vs.py's `"strand180_20"` pattern and matches
the silicon build `NES_stomper180s20_20260804.rbf` (memory
`dr-mario-eval47-stranded-win`). See `adversary_search.py`'s module docstring for
the full reconciliation against `eval47/ab47.py::_choose_base` (a base-only,
no-chain isolation rig used to prove the `ws=20` term in the first place -- NOT
the deployed VS decider, which is the chain180+stranded combination reproduced
here).

## What was REUSED (not rebuilt)

- `tmp/vs_aware/vs_harness.py::play_match` -- THE match loop, unmodified. ROM-true
  garbage channel (comboCounter summed across cascade, saturating payload,
  `{0,4}` column phase, receiver timing, gravity-before-resolve), side-swap
  seed pairing convention (from `h2h_vs.py`). No second match loop was written.
- `cascade_chain_x`, `cascade_stranded_x`, `fast_rtl_x`, `fast_sim_x`,
  `root_search` -- the whole depth-3 search substrate. The adversary's own
  decider (`adversary_search.py`) is a MECHANICAL COPY of
  `cascade_stranded_x._choose_d3_chain_s` (itself a mechanical copy of
  `cascade_chain_x._choose_d3_chain`) with three new terms added, following
  this project's established discipline for extending the numba kernels
  (`cascade_dbl_x`, `cascade_stranded_x` did the same thing).
- `fast_sim_x.FastDecider(depth=1)` as the offline-sim stand-in for the CvC
  cart's `DRP1NATIVE` (a deliberately artless native 6502 depth-1 AI --
  `personality/PERSONALITY_DESIGN_33.md`). Same POLICY CLASS, not literal
  6502 -- flagged explicitly in the report.

## What is NEW

- `adversary_search.py` -- `_choose_d3_adv`, the opponent-aware numba kernel
  (adds `w_press`, `w_hold`, `w_bigsq` -- see its docstring for the exact
  mechanism of each) + `AdversaryD3Decider` (4-arg `choose(board,cur,nxt,opp_board)`
  signature) + `selfcheck()`.
- `vs_run.py` -- thin decider factories (champion / pre-strand20 champion /
  native-d1) + one-seed paired-swap play helper.
- `batch_run.py` -- parallel paired-seed batch runner over a persistent
  `ProcessPoolExecutor` (mirrors `h2h_vs.py`'s `run()`/`_one()`/`_init()` shape;
  written fresh only because `h2h_vs.py::_mk()` hardwires BOTH sides to the
  blind calling convention and the adversary needs opponent-awareness on one
  side).
- `search_adversary.py` -- (1+lambda) evolution strategy, self-adapting global
  step size, over the 5-int adversary vector. NOT full CMA-ES (no covariance
  adaptation) -- see its docstring for why that trade was made.
- `measure_fourway.py` -- the four-way death-rate comparison, overfitting
  check (train vs held-out seeds), and transfer test (best adversary vs the
  pre-#47 champion lineage).

## Directory the OTHER agent owns

`experiments/adversary/` (Tier 1/2's directory) did not exist for most of this
session; it appeared partway through (contains `adversary_harness.py`,
`adversary_search.py`, `census_run.py`, `SEED_CENSUS.md`, etc.). By the time it
appeared, this tier's own VS-harness reuse (`vs_run.py`/`batch_run.py` wrapping
`vs_harness.play_match` directly) and evolutionary search (`search_adversary.py`)
were already built and running -- not refactored to adopt theirs mid-flight,
per the original brief's own allowance ("if it doesn't exist yet, build your
own minimal equivalent and note the duplication"). Noting it here rather than
pretending the duplication didn't happen. Nothing was read from or written to
that path except a directory listing, to confirm what it contained.

## Off-policy learned adversary (mid-session scope addition)

The team lead restructured this tier mid-flight to add an off-policy LEARNED
adversary trained on rollout data, per the owner's design update. New files:
`adversary_features.py` (15-feature extractor), `gen_rollout_data.py` (mixed
behaviour-policy rollout generation to `/mnt/data/drmario_adversary_t3/`),
`train_adversary_model.py` (sklearn HistGradientBoostingClassifier),
`learned_adversary.py` (the depth-1 + learned-value decider),
`search_adversary_v2.py` (restart + novelty exploration, a separate file so
the live `search_adversary.py` run was never edited mid-execution). See
`ADVERSARY_T3.md` for the full off-policy design rationale and results.

## Column targeting is NOT a knob

The ROM's garbage columns are keyed by `frameCounter & 3` (`vs_harness.py`
`garbage_columns`), not chosen by the sender. Giving the adversary a
"target column" parameter would model a capability the disassembly does not
support -- exactly the ROM-TRUE-ATTACK-RULE mistake this project has paid for
before. Left out on purpose; see `adversary_search.py`'s docstring.
