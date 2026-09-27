# vendor/ — out-of-repo modules the VS-race / gate (b) tools depend on

Snapshot (2026-09-24) of the 20 modules `vs_race.py`, `gate_b.py` and `vs_race_adaptive.py` import from
outside this repo (sibling worktree `dr-mario-qa-wt` eval47/tuck_v3, the `dr_mario_rl` faithful-sim
package, and `dr_mario_rl/tmp/{combo_term,vs_aware,endgame,pillrng,tuck,champion,film_review_20260804}`).
Sources and vendored paths: `VENDOR_MANIFEST.json`.

- `DRM_VENDOR=1` forces these copies (an import finder in `import_pin.py` maps exactly these module
  names here, whatever `sys.path` says); `DRM_VENDOR=0` forces the originals; default `auto` uses the
  copies only when the originals are absent (i.e. a clean clone). On the original machine `auto` keeps
  using the originals, so no earlier result changes provenance.
- 19 files are byte-identical copies. `bursty_model.py` adds one thing: the owner pressure fit
  (`fit_struktured_20260804`) re-derives from private couch footage, so in vendored mode it loads
  `bursty_owner_fit_20260804.json` — the fitted parameters of that exact fit (numbers only).
- Proof: `python experiments/cvx/tests_vendor_identity.py` — byte identity vs originals, snapshot
  identity vs the footage fit, and four game fingerprints recorded from the ORIGINAL modules
  reproduced under `DRM_VENDOR=1`.
