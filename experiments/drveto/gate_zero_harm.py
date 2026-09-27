#!/usr/bin/env python3
"""ZERO-HARM REPLAY GATE for DRVETO (workflow gate 4, closeout 2026-08-30).

The banked zero-harm witness (2 fires / 116,458 plies, both terminal) was measured
2026-08-29 by tmp/spawnplug/s16_veto_split.py with an ANALYTIC predicate
(plug_shape from the engine's resting cells) -- it predates this implementation.
The adversarial review therefore requires the gate re-run with the SHIPPING
predicate: `test_search_d3.veto_plug` itself (fo-walk geometry incl. the fo<=2
vertical insurance arm and the widened horizontal spans 2-3/4-5), plus the exact
firing conditions of the firmware (rv_cells==0 / win==0 / D_VIRF viruses-remain
scan of the parent).

Machinery: identical to s16 -- replay the banked 700-game real-firmware farm
(regime_map/out/farm.jsonl, c4 extension excluded) through the faithful engine
with recorded moves.  Admission bar: result AND viruses_left reproduce per row,
>=95% must pass.

Per recorded placement the gate computes what the firmware's D_VETO flag would
have been ON THE CHOSEN MOVE:

  fire  =  veto_plug(parent_nes, o4, col)          # the shipping geometry fn
        AND not cleared        (LEV_RVC == 0 analog: occ(P)+len(rc)-occ(A) == 0)
        AND not won            (LEV_WIN_R == 0 analog)
        AND parent has viruses (D_VIRF analog: any (v&0xF0)==0xD0 in parent NES)

A fire on a non-terminal ply is a FAILURE (the veto would have changed a healthy
decision).  Fires on the chosen move are the only decision-relevant ones: the
penalty only ever LOWERS a candidate, so flags on non-chosen candidates cannot
change the argmax (they can only demote candidates that already lost).

Cross-check: the s16 analytic plug_shape is computed alongside; divergences on
recorded (generable) moves are reported -- expected 0 (the widened arms only
differ on non-generable or illegal placements, which are never recorded).

Exit 0 = admission bar met AND zero non-terminal fires.
"""
import json
import os
import sys
import importlib.util

HERE = "/home/struktured/projects/dr-mario-regime-wt/experiments/regime_map"
FARM = "/home/struktured/projects/dr-mario-regime-wt/experiments/cosim_farm"
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
FSIM = os.environ.get("DRM_FAITHFUL_SIM")
if not FSIM:
    for cand in (RL + "/.claude/worktrees/faithful-sim",
                 "/home/struktured/projects/dr-mario-rl/.claude/worktrees/faithful-sim"):
        if os.path.isdir(os.path.join(cand, "src")):
            FSIM = cand
            break
    else:
        raise SystemExit("faithful-sim worktree not found; set DRM_FAITHFUL_SIM")
for _p in (HERE, FARM, FSIM + "/src", FSIM + "/tmp", QA, QA + "/eval47"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# The predicate under test comes from THIS worktree, pinned by path (the
# provenance rule: never let sys.path decide which tree's spec you gated).
_D3_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "..", "tests", "test_search_d3.py"))
_spec = importlib.util.spec_from_file_location("_drveto_spec", _D3_PATH)
_D3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_D3)
veto_plug = _D3.veto_plug
assert _D3.__file__ == _D3_PATH

import numpy as np
import drmario.faithful_env as FE
import bursty_model as BM
import game as G
from regime_pressure import wrap_model
from drmario.faithful_game import ORIENT_H
from xcheck_terms import faithful_to_nes

SPAWN = ((0, 3), (0, 4))
NES_EMPTY = 0xFF


def occ(board):
    return int(np.count_nonzero(board))


def plugged(board):
    return bool(board[0, 3] != 0 or board[0, 4] != 0)


EV = []

_orig_step = FE.FaithfulDrMarioEnv.step


def spy_step(self, action):
    P = self.board.color.copy()
    nes = faithful_to_nes(self.board)
    virf = any(v != NES_EMPTY and (v & 0xF0) == 0xD0 for v in nes)
    orient, acol, pill = self._decode(action)
    rc = self.board.resting_position(pill, orient, acol)
    out = _orig_step(self, action)
    A = self.board.color.copy()
    term = bool(out[2])
    info = out[4]
    cells = [tuple(x) for x in rc] if rc is not None else []
    cleared = occ(P) + len(cells) - occ(A) > 0
    won = bool(term and info.get("won"))
    # firmware-terms candidate: o4 bit1 = horizontal; col = anchor (left/single)
    if cells:
        cols = sorted({c for (_r, c) in cells})
        o4 = 2 if orient == ORIENT_H else 0
        col = cols[0]
        geom = bool(veto_plug(nes, o4, col))
    else:
        geom = False                      # no placement -> no candidate to flag
    fire = geom and not cleared and not won and virf
    placed_plug = any((r, c) in SPAWN for (r, c) in cells)
    s16_shape = plugged(P) or placed_plug
    s16_fire = s16_shape and not cleared and not won
    EV.append({
        "geom": geom, "fire": fire, "s16_fire": s16_fire,
        "parent_plug": bool(nes[3] != NES_EMPTY or nes[4] != NES_EMPTY),
        "cleared": cleared, "won": won, "term": term,
        "topout": bool(term and not info.get("won")),
        "plugged_after": plugged(A), "virf": virf,
    })
    return out


FE.FaithfulDrMarioEnv.step = spy_step

_orig_inj = BM.inject_bursty_garbage
GARB = []


def spy_inj(board, model, seed, gp, cs):
    pre = plugged(board.color)
    out = _orig_inj(board, model, seed, gp, cs)
    GARB.append({"ply": len(EV) - 1, "pre": pre, "post": plugged(board.color)})
    return out


BM.inject_bursty_garbage = spy_inj


class ReplayCosim:
    def __init__(self, moves, lat):
        self.moves = list(moves)
        self.lat = list(lat)
        self.i = 0
        self.fw_md5 = None

    def decide(self, b, cA, cB, nA, nB):
        col, o4, tcol, trow = self.moves[self.i]
        cl = self.lat[self.i][0] if self.i < len(self.lat) else 0
        self.i += 1
        return {"col": int(col), "o4": int(o4), "tcol": int(tcol),
                "trow": int(trow), "clocks": int(cl)}


def build_base():
    import run_bursty_v1_1_validity as V11
    m = V11.build_v1_1()
    m.meta = {k: v for k, v in m.meta.items() if k != "raw_events"}
    return m


def main():
    rows = [json.loads(l) for l in open(HERE + "/out/farm.jsonl") if l.strip()]
    rows = [r for r in rows
            if not (r.get("arm") == "c4_L20_clean" and r.get("seed", 0) >= 31600)]
    print(f"banked corpus rows (extension excluded): {len(rows)}")

    base = build_base()
    models = {}

    def model_for(v):
        if v not in models:
            models[v] = wrap_model(base if v != "clean" else None, v)
        return models[v]

    n_ok = n_mis = n_err = 0
    plies = 0
    fires = []            # (arm, seed, ply_idx, n_plies, event)
    diverge = 0           # veto_plug fire != s16 analytic fire on a recorded move
    parent_plug_recorded = 0

    for r in rows:
        if not r.get("moves"):
            continue
        variant = r.get("pressure_model") or "clean"
        model, pressure = model_for(variant)
        EV.clear()
        GARB.clear()
        rc = ReplayCosim(r["moves"], r.get("lat") or [])
        try:
            res = G.play_game(rc, seed=r["seed"], level=r["level"],
                              max_pills=r.get("max_pills_cap", 300),
                              exec_mode=r["exec_mode"], pressure=pressure,
                              model=model, trace=False)
        except Exception:
            n_err += 1
            continue
        if res["result"] != r["result"] or res["viruses_left"] != r["viruses_left"]:
            n_mis += 1
            continue
        n_ok += 1
        plies += len(EV)
        for i, e in enumerate(EV):
            if e["fire"] != e["s16_fire"]:
                diverge += 1
            if e["parent_plug"]:
                parent_plug_recorded += 1
            if e["fire"]:
                fires.append((r.get("arm"), r.get("seed"), i, len(EV), dict(e)))

    adm = 100.0 * n_ok / max(1, n_ok + n_mis + n_err)
    print(f"replay: ok={n_ok} mismatch={n_mis} error={n_err} "
          f"admission={adm:.1f}% (bar 95%)")
    print(f"plies scored: {plies}")
    print(f"veto_plug-vs-s16-analytic divergences on recorded moves: {diverge}")
    print(f"recorded plies with parent (0,3)/(0,4) occupied: {parent_plug_recorded}")
    print()
    nonterm = [f for f in fires if not f[4]["topout"]]
    print(f"== FIRES of the SHIPPING predicate on the chosen move: {len(fires)} "
          f"({100.0 * len(fires) / max(1, plies):.4f}% of plies) ==")
    for arm, seed, i, n, e in fires:
        kind = "TERMINAL-topout" if e["topout"] else "NON-TERMINAL  <-- FAILURE"
        print(f"  arm={arm} seed={seed} ply {i + 1}/{n}: {kind} "
              f"cleared={e['cleared']} plugged_after={e['plugged_after']} "
              f"parent_plug={e['parent_plug']}")
    print()
    ok = adm >= 95.0 and len(nonterm) == 0
    print(f"non-terminal fires (must be 0): {len(nonterm)}")
    print(f"ZERO-HARM GATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
