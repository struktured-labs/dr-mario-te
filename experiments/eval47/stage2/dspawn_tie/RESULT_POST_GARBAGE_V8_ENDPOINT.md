# Exact-v8 post-landed-garbage K4/wq60 endpoint — result

**Completed 2026-08-12. Registered verdict: `NO_GO`.**

This is the final result of `PREREG_POST_GARBAGE_V8_ENDPOINT.md`: N=9,000
paired seeds 80000..88999, exact `firmware_v8/p2_surrogate` base semantics,
candidate-independent `exo_lulu` pressure, and three arms per seed (base,
treatment, association-blind stratified null). The fail-closed analyzer read
all 9,000 ordered rows under META SHA-256
`9d870f20c8c1c0132ae707b5d7c77510d6cfd4fafa2d248be60603fecf4180bb`
and runtime manifest
`c0a059e69f1e55bb8991d31a62219bd7e94bbb926604cbcd9cf61eb1fff48c26`.
All 13 analyzer/provenance/META mutants failed. Statistical adequacy passed.

## Verdict table

| endpoint | treatment − comparator | paired 95% CI | McNemar p | registered requirement |
|---|---:|---:|---:|---|
| dies-ahead vs base | **+0.1667 pp** | [-0.1222, +0.4556] pp | 0.2843 | upper bound < 0 — **FAIL** |
| dies-ahead vs null | -0.1556 pp | [-0.5003, +0.1889] pp | 0.4053 | upper bound < 0 — **FAIL** |
| bad ends vs base | **+0.3444 pp** | [-0.1222, +0.8000] pp | 0.1512 | upper bound < +1 pp — PASS |
| bad ends vs null | -0.5444 pp | [-1.0778, -0.0333] pp | 0.0467 | upper bound < +1 pp — PASS |

The treatment did not establish dies-ahead efficacy against either comparator.
Its point estimates versus the exact-v8 base were worse for both dies-ahead
and bad ends. Safety passing is not efficacy; the mechanical verdict is
therefore `NO_GO`.

## Counts

| arm | clear | topout | stall | bad ends | dies-ahead |
|---|---:|---:|---:|---:|---:|
| base | 8,433 | 261 | 306 | 567 | 165 |
| treatment | 8,402 | 271 | 327 | 598 | 180 |
| null | 8,353 | 302 | 345 | 647 | 194 |

Among 8,199 common clears, treatment minus base pills was -0.278
[-0.855, +0.306], also indistinguishable from zero.

## Null and mechanism validity

The null was valid; unlike the exact-tie experiment, this verdict is not
confounded by action aliases or mismatched state-changing dose.

- canonical distinct-state flips: treatment 9,667; null 9,795;
- flip-rate mismatch: 1.046% (limit 10%);
- distribution TV: Hamming 0.0687, early/late timing 0.0057, value gap 0.0320,
  K-offset 0.0132 (each limit 0.10);
- first-flip p10/median/p90 absolute differences: 0/2/4 plies (limits
  20/15/20);
- bad-end +1 pp non-inferiority was reachable for both comparisons.

Treatment changed at least one canonical successor in 3,593 games. It changed
the terminal result in 456 and the result-or-pill count in 3,256. This is
another direct demonstration that narrow-looking action churn is not cheap.

## Scope of the negative result

Close the exact **post-landed-garbage K=4, weight=60, hinge=10** functional
form. Do not tune K, weight, hinge, null cutoffs, or endpoint definitions on
seeds 80000..88999, and do not reverse the sensor merely because this sign was
unfavorable.

This does **not** prove that every garbage-reactive policy, every temporal
feature, or every use of spawn-lane resolution is dead. It proves that the one
externally nominated exact-v8 intervention did not move the registered
endpoint in the desired direction despite a valid matched-churn control.

Machine-readable result:
`out/post_garbage_endpoint/result.json`, SHA-256
`4a14c0c162c98c75f5164878c722e8b4a9ae2052695678de07fd1398b76e62b0`.
