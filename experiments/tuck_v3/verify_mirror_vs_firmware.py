#!/usr/bin/env python3
"""Closes the loop (team-lead directive): verify mirrored_leaf's totals (base and
tuck) agree with the REAL FIRMWARE's D_V1 readback on the SAME 20 boards the
localization already used. If this matches, the RTL-faithful leaf mirror is proven
end-to-end and the theta curve under it can be trusted as a faithful stand-in for
the real firmware, not just a plausible-looking python reconstruction."""
import sys
import numpy as np

import component_localize as CL
import firmware_components as FC
import mirrored_leaf as ML
import fast_rtl_x as FX


def main(n=20, seed_range=range(0, 400)):
    print(f"Harvesting {n} boards (same methodology as the component localization)...",
          flush=True)
    samples = CL.harvest_boards(n_target=n, seeds=seed_range)
    print(f"got {len(samples)} boards\n", flush=True)

    FX.warmup_ship_eh(topk2=8)
    w, fl = FX.variant("winner")

    diffs_base, diffs_tuck = [], []
    for i, s in enumerate(samples):
        # ROOT CAUSE FOUND HERE (this session's re-run of this script crashed with a
        # numba TypingError inside _resting/_top_occ): np.frombuffer returns a READ-ONLY
        # array, a DIFFERENT numba type from a writable one -- _expand_core's already-
        # compiled specializations don't have a read-only-array overload, so calling it
        # directly from plain python (not from inside an already-jitted caller) with a
        # bare frombuffer array fails type inference. Every OTHER working call site in
        # this codebase (root_search.board_flat_from_fb) does `.astype(np.int8)` AFTER
        # frombuffer specifically because that makes a WRITABLE copy -- confirmed via a
        # minimal repro (bare frombuffer array: TypingError; same array .astype()'d:
        # works) before touching this fix, not guessed from the traceback alone.
        col = np.frombuffer(s["board"], dtype=np.int8).astype(np.int8)
        vir = np.frombuffer(s["vir"], dtype=np.int8).astype(np.int8)

        try:
            fw_base, fw_tuck, agree = FC.score_base_and_tuck(
                col, vir, s["ca"], s["cb"], s["na"], s["nb"],
                s["base_var"], s["base_col"],
                s["tuck_offa"], s["tuck_offb"], s["tuck_ta"], s["tuck_tb"])
        except AssertionError as e:
            print(f"[{i}] seed={s['seed']}  SKIPPED (firmware score failed): {e}")
            continue

        var, cc, bc1, bv1, bnv, bcells = s["base_var"], s["base_col"], None, None, None, None
        # recompute the base argmax's resolved board fresh (harvest didn't store the
        # raw c1/v1 arrays, only the offline component dict) via the SAME _expand_core
        # call choose_with_base_argmax used, using stored (var, col).
        from fast_sim_x import _expand_core, NCELL
        c1 = np.empty(NCELL, dtype=np.int8)
        v1 = np.empty(NCELL, dtype=np.int8)
        ok, nv, cells = _expand_core(col, vir, s["base_var"], s["base_col"],
                                      s["ca"], s["cb"], c1, v1)
        assert ok, "stored base action is illegal on replay -- harvest/board mismatch"
        mirror_base_total = ML.root_value_mirrored(c1, v1, nv, cells, s["na"], s["nb"],
                                                     8, FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w)

        import root_search as RS
        r0, c0, r1, c1_ = s["tuck_cells"]
        col0, col1 = s["tuck_ta"] , s["tuck_tb"]
        tc1 = np.empty(NCELL, dtype=np.int8)
        tv1 = np.empty(NCELL, dtype=np.int8)
        tnv, tcells = RS._expand_core_at(col, vir, r0, c0, r1, c1_, s["tuck_ta"], s["tuck_tb"], tc1, tv1)
        mirror_tuck_total = ML.root_value_mirrored(tc1, tv1, tnv, tcells, s["na"], s["nb"],
                                                     8, FX._W_EXCAV_SHIP, FX._W_HANG_SHIP, w)

        db = mirror_base_total - fw_base["total"]
        dt = mirror_tuck_total - fw_tuck["total"]
        diffs_base.append(db)
        diffs_tuck.append(dt)
        print(f"[{i}] seed={s['seed']}  base: mirror={mirror_base_total:.0f} fw={fw_base['total']} "
              f"diff={db:+.0f}   tuck: mirror={mirror_tuck_total:.0f} fw={fw_tuck['total']} "
              f"diff={dt:+.0f}")

    print("\n" + "=" * 70)
    print(f"SUMMARY: {len(diffs_base)}/{len(samples)} boards checked")
    print(f"  base  mean diff {np.mean(diffs_base):+.1f}  max abs diff {np.max(np.abs(diffs_base)):.0f}")
    print(f"  tuck  mean diff {np.mean(diffs_tuck):+.1f}  max abs diff {np.max(np.abs(diffs_tuck)):.0f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
