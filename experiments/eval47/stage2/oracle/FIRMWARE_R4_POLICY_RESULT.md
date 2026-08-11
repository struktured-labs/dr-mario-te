# Explicit firmware-R4 policy gate result

**Registered verdict: NO_GO.** The frozen 12-case gate ran against canonical firmware
`d025fa8` with tuck off and `DRSTRAND=20`. The term-level R4 mirror remained exact and
killed all three term mutants, but the complete offline decision path did not reproduce
the assembled policy.

| stratum | cases | action mismatches |
|---|---:|---:|
| legacy-flat vs R4 sensitive | 4 | 2 |
| strand0 vs strand20 sensitive | 4 | 2 |
| all-offline-paths agree control | 4 | 0 |
| **total** | **12** | **4** |

Winning values mismatched on all 12 cases. Firmware values were 864--1,153 points above
the cap-one R4 mirror in this sample. The legacy-flat mutant was rejected; the strand0
mutant was not consistently rejected because the complete R4 mirror itself disagreed
with firmware on two strand-sensitive cases.

This does not retract the earlier finding that R4 hang semantics are policy-material. It
proves they are insufficient for complete cartridge fidelity. The assembled champion also
runs link-aware fixpoint resolution and `DRCHAIN=180`, while the historical
`FastShipD3DeciderEH`/oracle path resolves only one compact-gravity clear round and carries
no chain-depth reward. Those omitted mechanics are the next localization target.

The raw result is retained at `out/firmware_r4_policy.json`. The named `firmware_r4`
module remains useful only as an isolated R4/cap-one instrument; it is not authorized to
claim complete v8 policy fidelity.

