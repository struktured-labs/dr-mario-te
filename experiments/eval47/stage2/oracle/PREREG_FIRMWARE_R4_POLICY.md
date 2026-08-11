# Explicit firmware-R4 policy path — pre-registration

**Frozen before the first complete root decision was compared with py65 firmware.** The
term-only R4 audit has already been observed and is not prospective evidence: it proved the
hang mirror exact and showed that replacing legacy flat hang changes policy. This gate asks
the still-unanswered question: does an explicit offline R4 + strand20 root scorer reproduce
the complete base-action decision and value of the assembled coprocessor?

## Policy under test

The new path is named `firmware_r4`; it must not silently change `FastShipD3DeciderEH` or
reinterpret any historical oracle output. It keeps the champion `winner` leaf, full 32-action
root enumeration, top-K2=8, four-pill third-ply expectation, discount shift 1, excavation
weight 24, immediate terms, strict keep-first tie order, and strand cost 20. Its only semantic
correction is the deployed R4 hang term on the resolved ply-1 board:

```
sum(40 + 20*gap_rows)
```

over color-matched hovering halves whose column contains at least one virus. Wins receive no
excav/hang add-on, as in firmware.

## Prospective complete-decision gate

Generate real reachable states by playing the frozen legacy champion in the Lulu pressure
rig from seed 30000 upward. Before any firmware decision is observed, deterministically retain:

- the first 4 states where legacy-flat and `firmware_r4` (both strand20) choose differently;
- the first 4 otherwise-unused states where `firmware_r4` strand0 and strand20 differ;
- the first 4 otherwise-unused controls where all three choose the same action.

Refuse to run if any stratum cannot be filled by seed 30031 or 300 pills per seed. On these
12 cases, the assembled tuck-off firmware with `DRSTRAND=20` must match `firmware_r4` on:

1. chosen action, exactly, all 12 cases;
2. signed 16-bit winning root value, exactly, all 12 cases.

The firmware source is the canonical worktree already used by `FirmwareDecider`; its git
revision and assembled image hash are recorded. Tuck is disabled because this gate certifies
the 32-action champion base policy, not the independent tuck extension.

## Checks that must fail

- The pre-existing term mirror must again kill missing-color-match, missing-virus-column,
  and flat-depth R4 mutants.
- The legacy flat-hang action must disagree with firmware in every selected flat-sensitive
  case.
- The strand-disabled action must disagree with firmware in every selected strand-sensitive
  case.
- Adding one to every predicted winning value must fail the exact-value gate.

Any mismatch is a registered NO_GO. No threshold or state-selection rule may be changed after
the run. A pass establishes an observation/simulation instrument; it does not establish that
R4 is stronger, and it does not retroactively relabel the running Hetzner arm.

