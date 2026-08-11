# Exact-v8 post-garbage endpoint — launch readiness

**Ready but unlaunched as of 2026-08-11. No seed in 80000..88999 has been
opened.** Owner launch is required by the sealed preregistration.

## Frozen identity

- preregistration: `85d7898`
- null table: `a749aa2`, SHA-256
  `c64ce845e3e7d19242a359f868012bd04623c1bbee21d139202722f686e9c82d`
- runner/selector gate: `095774a`, final fail-closed binding `7b5fa36`
- analyzer/provenance verdict gates: `2b6b62d`, final META binding `bb87b67`
- current prospective gate: PASS, SHA-256
  `31b404c6ad027911ecb17709ef04903f47e238c036942682f84e61076c48e89a`
- current runtime manifest (before any endpoint META exists):
  `c0a059e69f1e55bb8991d31a62219bd7e94bbb926604cbcd9cf61eb1fff48c26`

The launch gate is bound to the exact policy module, endpoint runner, gate, and
analyzer source bytes. Any edit makes `require_gate()` fail until the complete current
engineering/selector gate is rerun. The gate includes exact-v8 base identity,
K4/K+1, association, alias, table/bin/cutoff mutants, and exact reproduction of
all 616 frozen validation selections. Four live three-arm rows pass the
analyzer pipeline, and its self-test kills all 13 verdict/provenance/zero-dose/
META directions. The analyzer independently requires the registered META and
current full runtime manifest before reading outcomes. A killed predecessor
check also proves base active-duty telemetry is nonzero under landed pressure;
out-of-range resume rows fail immediately.

## Measured cost

A repeated run on the same 12 already-disclosed smoke seeds (three arms each)
measured both allowed local settings after cache warm-up:

- four workers: 25.18 s, 1,716 pairs/hour, **~5.25 wall-hours / 21.0 core-hours**;
- six workers: 18.16 s, 2,379 pairs/hour, **~3.78 wall-hours / 22.7 core-hours**.

Prefer six local workers when the box is otherwise free; budget 4.5--6
wall-hours for cold cache, tail variance, flushes, and analysis. Use four when
lower contention matters.

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
$PY experiments/eval47/stage2/dspawn_tie/run_post_garbage_v8_endpoint.py --workers 6
$PY experiments/eval47/stage2/dspawn_tie/analyze_post_garbage_v8_endpoint.py
```

The runner banks ordered 250-seed segments and safely resumes only when META,
gate, table, and all runtime hashes are identical. Do not inspect or interpret
partial outcome summaries as a verdict.

Read-only local status (does not restart or edit the job):

```bash
bash experiments/eval47/stage2/dspawn_tie/monitor_post_garbage_endpoint.sh
```

The initial monitor implementation summed `wc`'s per-file rows and its
synthetic `total` row, doubling progress once multiple segments existed. The
monitor now excludes that summary row; this operational fix does not touch the
runner, policy, META, gate, or endpoint data.
