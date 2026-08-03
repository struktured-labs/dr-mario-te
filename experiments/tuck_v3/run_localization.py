#!/usr/bin/env python3
"""Runs the full 20-board component localization (task #17 stage 3) and prints the
table + verdict the team lead asked for. See component_localize.py / firmware_
components.py module docstrings for the harvest/scoring methodology."""
import sys
import numpy as np

import component_localize as CL
import firmware_components as FC


def main(n=20, seed_range=range(0, 400)):
    print(f"Harvesting {n} boards (real capsule stream, offline model's tuck-won "
          f"decisions ranked by margin over best base action)...", flush=True)
    samples = CL.harvest_boards(n_target=n, seeds=seed_range)
    print(f"got {len(samples)} boards\n", flush=True)

    rows = []
    for i, s in enumerate(samples):
        col = np.frombuffer(s["board"], dtype=np.int8)
        vir = np.frombuffer(s["vir"], dtype=np.int8)
        try:
            fw_base, fw_tuck, agree = FC.score_base_and_tuck(
                col, vir, s["ca"], s["cb"], s["na"], s["nb"],
                s["base_var"], s["base_col"],
                s["tuck_offa"], s["tuck_offb"], s["tuck_ta"], s["tuck_tb"])
        except AssertionError as e:
            print(f"[{i}] seed={s['seed']} margin={s['margin']:.0f}  SKIPPED: {e}")
            continue

        ob, ot = s["offline_base"], s["offline_tuck"]
        print(f"[{i}] seed={s['seed']} offline_margin={s['margin']:+.0f}  "
              f"base_action_agrees={agree['same_action']}")
        print(f"    {'component':<10} {'off_base':>9} {'fw_base':>9} {'d_base':>8}   "
              f"{'off_tuck':>9} {'fw_tuck':>9} {'d_tuck':>8}")
        diffs = {}
        for comp in ("imm1", "leaf1", "best2_raw", "blend", "eh", "total"):
            db = fw_base[comp] - ob[comp]
            dt = fw_tuck[comp] - ot[comp]
            diffs[comp] = (db, dt)
            print(f"    {comp:<10} {ob[comp]:>9.0f} {fw_base[comp]:>9.0f} {db:>+8.0f}   "
                  f"{ot[comp]:>9.0f} {fw_tuck[comp]:>9.0f} {dt:>+8.0f}")
        fw_margin = fw_tuck["total"] - fw_base["total"]
        flips = (s["margin"] > 0) != (fw_margin > 0)
        print(f"    firmware_margin={fw_margin:+.0f} (offline said {s['margin']:+.0f})"
              f"{'  <-- SIGN FLIP' if flips else ''}")
        print()
        rows.append({"seed": s["seed"], "offline_margin": s["margin"], "fw_margin": fw_margin,
                      "flips": flips, "base_action_agrees": agree["same_action"], "diffs": diffs})

    n_ok = len(rows)
    n_flip = sum(r["flips"] for r in rows)
    n_disagree_action = sum(1 for r in rows if not r["base_action_agrees"])
    print("=" * 70)
    print(f"SUMMARY: {n_ok}/{len(samples)} boards scored")
    print(f"  base-action agreement (firmware winner == offline argmax): "
          f"{n_ok - n_disagree_action}/{n_ok}")
    print(f"  sign flips (offline tuck-favourable -> firmware base-favourable or worse): "
          f"{n_flip}/{n_ok}")
    for comp in ("imm1", "leaf1", "best2_raw", "blend", "eh", "total"):
        db_mean = np.mean([r["diffs"][comp][0] for r in rows])
        dt_mean = np.mean([r["diffs"][comp][1] for r in rows])
        print(f"  mean fw-offline diff  {comp:<10} base={db_mean:+8.1f}  tuck={dt_mean:+8.1f}")
    print("=" * 70)

    return rows


if __name__ == "__main__":
    main()
