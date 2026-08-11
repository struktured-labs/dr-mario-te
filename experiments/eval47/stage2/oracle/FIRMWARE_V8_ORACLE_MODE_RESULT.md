# Explicit cartridge-faithful oracle policy mode

Date: 2026-08-11  
Verdict: **INFRASTRUCTURE GO; no outcome arm authorized**

The opt-in mode frozen in `PREREG_FIRMWARE_V8_ORACLE_MODE.md` passed every required gate.  Existing
construction still defaults to `historical_compact/seed0`; the new path must be requested explicitly
as `firmware_v8` with either `seed0` or the labeled `p2_surrogate` tie model.

## Gate result

| gate | result |
|---|---:|
| default vs explicit historical action/outcome identity | 6/6 |
| historical arm vs independent direct loop | 6/6 |
| firmware-v8 const arm vs independent direct loop | **6/6** |
| wrong historical policy breaks firmware replay | 6/6 |
| wrong seed-zero mode breaks surrogate replay | 6/6 |
| real gated root + horizon-2 forks request firmware-v8 | **5/5 policy calls** |
| deliberately historical path fails semantic assertion | yes |
| policy/tie/tie-value flip provenance fields | exact |
| changed policy or tie field prevents resume | both rejected |
| firmware/link/chain/strand modules in runtime manifest | yes |
| reversed tie-order mutant | killed |

Gate JSON SHA-256:
`6a0117ab090486baf680558ce16d79144a238b8077487915ddd83aa68fe3e574`.

## Legacy regression

- ordered runner banking and its `as_completed` mutant: PASS;
- oracle verdict and null/adequacy mutation matrix: PASS;
- fork side-effect gate: 2/2 exact after 216 and 628 discarded forks;
- deliberately leaky forks broke both games (106→139 pills and 209→120 pills): PASS.

An end-to-end one-pair const smoke wrote `policy_semantics=firmware_v8` and
`tie_seed_mode=p2_surrogate` to both `META.json` and the row, included all four firmware dependency
modules in the manifest, and kept base/treatment identical.  Smoke META SHA-256:
`a55b0fe4f59547c36cdb1e7272a640f2013cf7e2c29a6ebdf2208d8a82e03fd6`.

## Future usage

Future smoke or preregistered arms can add:

```
--policy-semantics firmware_v8 --tie-seed-mode p2_surrogate
```

This selects the hardware-validated evaluator at the root, in top-four ranking, and on every fork
ply.  It does not alter the running Hetzner arm, whose directory and metadata remain historical.

This infrastructure GO is not a Tier-A launch authorization.  A cartridge-faithful outcome arm
still requires a fresh preregistration, true and dose-matched shuffled-label null, adequate sample
size, explicit tie interpretation, and a distinct output directory.
