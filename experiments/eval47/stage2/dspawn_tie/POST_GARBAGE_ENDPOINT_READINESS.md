# Exact-v8 post-garbage endpoint — launch readiness

**Ready but unlaunched as of 2026-08-11. No seed in 80000..88999 has been
opened.** Owner launch is required by the sealed preregistration.

## Frozen identity

- preregistration: `85d7898`
- null table: `a749aa2`, SHA-256
  `c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d`
- runner/selector gate: `095774a`, final live-pipeline binding `56fe541`
- analyzer/provenance verdict gates: `2b6b62d`
- current prospective gate: PASS, SHA-256
  `ccf705e00e9fb38c01749451f641bf132b14f445215b37662f5fc2e0578e4801`
- current runtime manifest (before any endpoint META exists):
  `3d794dbc958cf59ee60856c3947faac76a211cab14d669570b3605f7557738c8`

The launch gate is bound to the exact policy module, endpoint runner, gate, and
analyzer source bytes. Any edit makes `require_gate()` fail until the complete current
engineering/selector gate is rerun. The gate includes exact-v8 base identity,
K4/K+1, association, alias, table/bin/cutoff mutants, and exact reproduction of
all 616 frozen validation selections. Four live three-arm rows pass the
analyzer pipeline, and its self-test kills all 11 registered verdict and
provenance directions.

## Measured cost

A four-worker run on 12 already-disclosed smoke seeds (three arms each) took
25.18 seconds after cache warm-up: 1,716 paired seeds/hour. Linear projection:

- **~5.25 wall-hours at four local workers**;
- **~21 core-hours**;
- budget 6--8 wall-hours for cold cache, tail variance, flushes, and analysis.

This is a small smoke estimate, not a billing guarantee. It is nevertheless far
below the remote H15 oracle's measured cost. Do not contend with or alter the
user-launched historical oracle job to run this arm.

## Owner launch commands

```bash
cd /home/struktured/projects/dr-mario-te/champion-source
PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
export NUMBA_CACHE_DIR=/tmp/dr-mario-te-numba-cache

$PY experiments/eval47/stage2/dspawn_tie/gate_post_garbage_endpoint.py
$PY experiments/eval47/stage2/dspawn_tie/analyze_post_garbage_v8_endpoint.py --selftest
$PY experiments/eval47/stage2/dspawn_tie/run_post_garbage_v8_endpoint.py --workers 4
$PY experiments/eval47/stage2/dspawn_tie/analyze_post_garbage_v8_endpoint.py
```

The runner banks ordered 250-seed segments and safely resumes only when META,
gate, table, and all runtime hashes are identical. Do not inspect or interpret
partial outcome summaries as a verdict.
