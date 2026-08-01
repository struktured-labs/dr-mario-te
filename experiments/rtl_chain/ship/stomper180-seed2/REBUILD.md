# Rebuild the shipped Combo Stomper core

What ran on the user's MiSTer on 2026-08-01. The `.rbf`/`.sof` are deliberately NOT in git
(3.5 MB each); they live on disk at `dr_mario_rl/tmp/rtl_chain/ship/stomper180-seed2/` and
are referenced by hash below. Everything needed to regenerate them byte-for-byte is here.

## Identity

| | |
|---|---|
| arm | **Combo Stomper**, chain180 (`$70E5 a_fix=1`, `$70E6 = 45` → dose 180) |
| rbf | `71d2de37b1fbcabbb92701fc4094f833` — deployed as `_Console/NES_stomper180_20260801.rbf` |
| firmware | `f4b6dfbf76c9beb80d19b3659fb99d26` (`fw_tuckstomp180.hex`, here) |
| RTL | `NES_MiSTer-drmario` `claude/winner-single-copro` @ `887043e` |
| seed | **2**, and it must be the ONLY `SEED` line in `NES.qsf` |
| cart | `latch_converged_wiggle.nes` `d6daedbc150d47aaafae1a2d2ac94b69` — **unchanged** |

## Recipe

    git -C NES_MiSTer-winner checkout 887043e
    cp fw_tuckstomp180.hex  NES_MiSTer-winner/copro_rom.hex
    # exactly one SEED line -- the project qsf already ships SEED 5
    sed -i '/set_global_assignment -name SEED /d' NES_MiSTer-winner/NES.qsf
    printf '\nset_global_assignment -name SEED 2\n' >> NES_MiSTer-winner/NES.qsf
    cd NES_MiSTer-winner && rm -rf db incremental_db && ./run_fit.sh

Expect **copro slack +0.181 ns, 37,249 / 41,910 ALMs, pll_hdmi +0.094** (`verdict.txt`).
Matching slack is the evidence the pinned-seed placement reproduced — that is how the
same-placement property is established here, by measurement rather than by construction.

To regenerate the firmware instead of using the copy here:

    cd dr-mario-canonical-wt/fpga/copro
    DRCOPRO_TUCK=1 DRCOPRO_ARM=1 DRFIX=1 DRCHAIN=180 python dbg_build.py all 0

## Three things that will bite a rebuilder

1. **`DRCOPRO_TUCK=1` is not optional.** The baseline this replaced (`751b6ce9`) is the tuck
   build. An arm image without it silently drops the tuck enumerator and ships a regression
   that looks like worse play, not like a missing feature.
2. **There is no "swap the arm" shortcut.** `quartus_cdb --update_mif` is a no-op for
   `$readmemh`-initialised memory, so it exits 0 and re-emits the *same* bitstream. Changing
   arms means a full compile with the firmware in place. `swap_arm.sh` is kept, disabled,
   with the autopsy in its header. **Always check the new rbf md5 DIFFERS.**
3. **`clk85` is the SDRAM clock**, not a copro-only timing knob — `rtl/sdram.sv` pins its
   constants to that rate. It also feeds the EEPROM. Never retune it for timing closure.

## Verify a rebuild

    experiments/rtl_chain/fit_verdict.sh          # triple vs the +0.10 bar
    experiments/rtl_chain/firmware_pair.sh        # arms differ in exactly 2 bytes
    cd experiments/bitexact_gate && python gate.py linknode   # 7,282 cases, 9/9 mutants
