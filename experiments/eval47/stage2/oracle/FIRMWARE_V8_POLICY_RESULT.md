# Complete v8 policy py65 gate result

**Registered verdict: NO_GO.** The frozen nine-state gate failed: four actions and all
nine winning values disagreed. The implementation lockstep and every non-cap-one mutant
check fired as designed.

This result invalidates the comparator, not the complete mirror. Inspection after the
verdict confirmed canonical's own warning: `attach_engine_emu` is a BASE-search test
double, not the shipped BoardEngine. It:

- calls `_cap1_targeted` for every node;
- computes `180*viruses + 10*cells` with no chain-depth reward;
- calls stale `nes_d3_golden.leaf_d3` rather than the winner `LeafEval.sv`;
- has no CMD-6/7 delta implementation; and
- ignores the firmware's `DRFIX=1` and `DRCHAIN=180` writes.

Therefore `FirmwareDecider(drfix=1, drchain=180)` cannot test those flags: the arguments
change assembled bytes but the attached engine model does not implement their meaning.
Canonical `FIRMWARE.md` explicitly says py65 cannot validate the shipped delta engine and
requires the Verilator `run_gate.sh` co-sim.

The old helper also accepted only color/virus planes. The new optional `lnk=` input now
preserves exact NES link nibbles for future diagnostics while keeping the old default for
historical replay. That repair does not make py65 a shipped-v8 comparator.

Raw output remains at `out/firmware_v8_policy.json`. The next authority is a real
`CoproDrMario.sv` Verilator run using the shipped firmware flags; no future report may call
the py65 engine emulator “actual v8 firmware.”

