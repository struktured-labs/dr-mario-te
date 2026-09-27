#!/usr/bin/env python3
"""Extract the parent boards of the two zero-harm TERMINAL fires (the only two
plies in the banked 116,458 where the shipping veto predicate fires on the chosen
move) for the mailbox-trajectory gate (G2).

Replays exactly those two farm games with the gate_zero_harm machinery and dumps
the pre-move NES parent + capsule/next colours at the fire ply:

  c1_L11_bursty seed 30152 ply 162/162  ->  traj_c1_parent.json
  c5_L20_bursty seed 32148 ply 314/314  ->  traj_c5_parent.json

Grid format matches g2_parent.json (16x8 of . R Y B, viruses lowercased) plus a
"_meta" sidecar with 0-based colour bytes as the firmware mailbox takes them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gate_zero_harm as Z          # reuses spies + replay machinery

TARGETS = {("c1_L11_bursty", 30152): "traj_c1_parent.json",
           ("c5_L20_bursty", 32148): "traj_c5_parent.json"}

DEC = []                            # (nes_parent, cA, cB, nA, nB) per decide call

_orig_decide = Z.ReplayCosim.decide


def spy_decide(self, b, cA, cB, nA, nB):
    # game.py:329 passes b128 (already NES bytes) and 0-based colours
    DEC.append((list(b), cA, cB, nA, nB))
    return _orig_decide(self, b, cA, cB, nA, nB)


Z.ReplayCosim.decide = spy_decide


def nes_to_grid(nes):
    """NES bytes -> the g2_parent.json grid convention (viruses lowercase)."""
    M = {0: "Y", 1: "R", 2: "B"}   # project convention (gate_owner_boards.CMAP)
    grid = []
    for r in range(16):
        row = []
        for c in range(8):
            v = nes[r * 8 + c]
            if v == 0xFF:
                row.append(".")
            else:
                ch = M[v & 0x03]
                row.append(ch.lower() if (v & 0xF0) == 0xD0 else ch)
        grid.append(row)
    return grid


def main():
    rows = [json.loads(l) for l in open(Z.HERE + "/out/farm.jsonl") if l.strip()]
    base = Z.build_base()
    from regime_pressure import wrap_model
    import game as G

    for r in rows:
        key = (r.get("arm"), r.get("seed"))
        if key not in TARGETS or not r.get("moves"):
            continue
        variant = r.get("pressure_model") or "clean"
        model, pressure = wrap_model(base if variant != "clean" else None, variant)
        Z.EV.clear()
        DEC.clear()
        rc = Z.ReplayCosim(r["moves"], r.get("lat") or [])
        res = G.play_game(rc, seed=r["seed"], level=r["level"],
                          max_pills=r.get("max_pills_cap", 300),
                          exec_mode=r["exec_mode"], pressure=pressure,
                          model=model, trace=False)
        assert res["result"] == r["result"] and \
            res["viruses_left"] == r["viruses_left"], f"admission fail {key}"
        fire_idx = [i for i, e in enumerate(Z.EV) if e["fire"]]
        assert len(fire_idx) == 1, f"{key}: expected exactly 1 fire, got {fire_idx}"
        i = fire_idx[0]
        nes, cA, cB, nA, nB = DEC[i]
        move = r["moves"][i]
        out = {"grid": nes_to_grid(nes),
               "_meta": {"arm": r["arm"], "seed": r["seed"],
                         "ply": i + 1, "n_plies": len(Z.EV),
                         "cA": int(cA), "cB": int(cB),
                         "nA": int(nA), "nB": int(nB),
                         "colors_note": "0-based bytes as S_CA/S_CB/S_NA/S_NB take",
                         "chosen_move_col_o4": [int(move[0]), int(move[1])],
                         "event": Z.EV[i]}}
        path = os.path.join(HERE, TARGETS[key])
        with open(path, "w") as f:
            json.dump(out, f, indent=1)
        print(f"wrote {path}  ply {i+1}/{len(Z.EV)} chosen={move[:2]} "
              f"cA={cA} cB={cB} nA={nA} nB={nB}")


if __name__ == "__main__":
    main()
