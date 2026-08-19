#!/usr/bin/env python3
"""Offline argmax-flip probe for the d_spawn_h penalty (memory law:
dr-mario-spawn-lane-gate-probe -- below ~2% flip the arm is untestable).
For each decision, recompute all-32 candidates' spawn-lane height post-move,
apply val' = val - wq*max(0, sph-k), count argmax changes.
Uses stored cand_vals (gate: recomputed argmax must equal stored action)."""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feature_battery as FB


def build_sph():
    import reach_root as RR
    L = RR._lazy()
    FS = L["FS"]
    from numba import njit
    _expand_core = FS._expand_core

    @njit(cache=False)
    def sph_all32(cols, virs, cura, curb, out):
        n = cols.shape[0]
        c1 = np.empty(128, dtype=np.int8)
        v1 = np.empty(128, dtype=np.int8)
        for i in range(n):
            for var in range(4):
                for cc in range(8):
                    ok, nv, cells = _expand_core(cols[i], virs[i], var, cc,
                                                 cura[i], curb[i], c1, v1)
                    if ok == 0:
                        out[i, var * 8 + cc] = -1
                        continue
                    sph = 0
                    for c in (3, 4):
                        for r in range(16):
                            if c1[r * 8 + c] != 0:
                                h = 16 - r
                                if h > sph:
                                    sph = h
                                break
                    out[i, var * 8 + cc] = sph
    return sph_all32


def main():
    fat = FB.load_npz(os.path.join(HERE, "fatal_windows.npz"))
    ctl = FB.load_npz(os.path.join(HERE, "controls.npz"))
    sph_all32 = build_sph()
    res = {}
    for tag, d in (("fatal_topout", fat), ("ctrl", ctl)):
        m = (d["outcome"] == 1) if tag.startswith("fatal") else slice(None)
        cols = d["board_col"][m]
        virs = d["board_vir"][m]
        cur = d["cur"][m]
        vals = d["cand_vals"][m].astype(np.float64)
        act = d["action"][m].astype(np.int64)
        n = len(act)
        sph = np.zeros((n, 32), dtype=np.int16)
        sph_all32(cols, virs, cur[:, 0], cur[:, 1], sph)
        # gate: argmax of stored vals == stored action value
        am = np.nanargmax(vals, axis=1)
        assert (vals[np.arange(n), am] == vals[np.arange(n), act]).all()
        res[tag] = {}
        for k in (6, 8, 10):
            for wq in (15, 30, 60, 120, 240):
                pen = wq * np.maximum(0, sph - k)
                pen[sph < 0] = 0
                v2 = vals - pen
                am2 = np.nanargmax(v2, axis=1)
                flip = float((v2[np.arange(n), am2]
                              > v2[np.arange(n), act]).mean())
                res[tag][f"k{k}_wq{wq}"] = round(flip, 4)
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(HERE, "flip_probe.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
