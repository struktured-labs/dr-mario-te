#!/usr/bin/env python3
"""VALIDATION GATE for the forced-move harness (killed-mutant style).

THE CLAIM UNDER TEST is not "the harness runs". It is: a board lifted out of a
real game and re-injected reproduces that game EXACTLY -- so any later difference
between two forced placements is attributable to the placement and not to the
injection.

ARM 1 (MATCH). Play a reference game on a seed with the ordinary champion
decider. At ply P, snapshot the board, cur, nxt and the pill-source cursor, and
record the action the decider actually chose. Keep the reference game running for
H more pills, recording the board cell-for-cell (colours + viruses + LINKS) after
every lock. Then feed the snapshot through the harness, forcing that same action,
with the TRUE continuation stream. Every one of the H locks must match.

ARM 2 (CONTROL). Same snapshot, same stream, but force a DIFFERENT legal action.
The trajectory must DIVERGE -- at lock 1 by construction, and the run must not
re-converge to the reference by lock H (a harness that ignored `forced_action`
would pass arm 1 and fail here; a harness that ignored the CONTINUATION would
pass here for the wrong reason, which is why arm 1 checks every lock, not the
last one).

Both arms must behave on every snapshot or the harness does not ship. Failure is
exit 1.

WHY A REPLAY AND NOT A BOARD COMPARE. `dr-mario-deepcopy-pill-closure`: a shared
pill cursor produces plausible boards and run-to-run determinism, and was caught
by nothing except an independent replay. Arm 1 is that replay.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import forced_board as FBM   # noqa: E402  (sets up the rest of sys.path)


def reference_game(seed, decider, level=11, max_pills=300, snap_plies=(20, 35, 50)):
    """A plain solo champion game; returns (snapshots, locks).

    `locks[i]` is the board key after the i-th placement, so a snapshot taken at
    ply P is checked against locks[P:P+H]. No garbage is injected: the gate is
    about the injection mechanism, and an injector would add a second source of
    divergence that the gate could not attribute.
    """
    from drmario.faithful_env import FaithfulDrMarioEnv
    from nes_pills import NesPillSource

    env = FaithfulDrMarioEnv(level=level, seed=seed, max_pills=max_pills)
    env.reset()
    src = NesPillSource(seed=seed)
    src.attach(env)
    env.cur = env._rand_pill()
    env.nxt = env._rand_pill()

    snaps, locks = [], []
    want = set(snap_plies)
    for ply in range(max_pills):
        if env.board.virus_count() == 0:
            break
        a = decider(env)
        if a is None:
            break
        if ply in want:
            snaps.append({
                "ply": ply,
                "col": env.board.color.copy(),
                "vir": env.board.is_virus.copy(),
                "lnk": env.board.link.copy(),
                "cur": (int(env.cur.a), int(env.cur.b)),
                "nxt": (int(env.nxt.a), int(env.nxt.b)),
                "src_i": int(src.i),
                "action": int(a),
                "viruses": int(env.board.virus_count()),
            })
        _, _, term, trunc, _ = env.step(int(a))
        locks.append(FBM.board_key(env.board))
        if term or trunc:
            break
    return snaps, locks


def _env_from_snapshot(s, seed, level, max_pills, cur=None, nxt=None):
    """Rebuild the harness env from a reference snapshot.

    The pill source is a FRESH NesPillSource wound to the reference's own cursor
    -- `skip=s['src_i']` -- so the continuation is the TRUE one. `cur`/`nxt` come
    from the snapshot, because they were already drawn before the cursor was read.
    """
    planes = (s["col"].copy(), s["vir"].copy(), s["lnk"].copy())
    return FBM.make_env(planes, stream_seed=seed,
                        cur=cur or s["cur"], nxt=nxt or s["nxt"],
                        stream_skip=s["src_i"], level=level, max_pills=max_pills)


def run_gate(seeds, horizon, snap_plies, level=11, wt=0, ws=20, verbose=True):
    dec = FBM.Decider(wt=wt, ws=ws, level=level)
    results = []
    all_ok = True

    for seed in seeds:
        snaps, locks = reference_game(seed, dec, level=level, snap_plies=snap_plies)
        for s in snaps:
            ply = s["ply"]
            ref = locks[ply:ply + horizon]
            if len(ref) < 2:
                continue   # reference ended too soon to gate anything

            # ---- ARM 1: MATCH -------------------------------------------------
            env, src, meta = _env_from_snapshot(s, seed, level, 300)
            settle_ok = not meta["settle_moved"]
            r1 = FBM.rollout(env, dec, len(ref), forced_action=s["action"])
            got = [t["key"] for t in r1["traj"]]
            n_cmp = min(len(ref), len(got))
            first_bad = next((i for i in range(n_cmp) if got[i] != ref[i]), None)
            match_ok = (first_bad is None and len(got) == len(ref))

            # ---- ARM 2: CONTROL -----------------------------------------------
            env2, src2, _ = _env_from_snapshot(s, seed, level, 300)
            alts = [p["action"] for p in FBM.legal_placements(env2)
                    if p["action"] != s["action"]]
            if not alts:
                continue   # only one legal move here: nothing for the control to vary
            alt = alts[len(alts) // 2]
            r2 = FBM.rollout(env2, dec, len(ref), forced_action=alt)
            got2 = [t["key"] for t in r2["traj"]]
            m = min(len(ref), len(got2))
            ctrl_first_div = next((i for i in range(m) if got2[i] != ref[i]), None)
            # The control must differ AT THE FORCED LOCK ITSELF. Anything later
            # (or never) means `forced_action` did not actually drive move 1.
            ctrl_ok = (ctrl_first_div == 0)

            ok = match_ok and settle_ok and ctrl_ok
            all_ok &= ok
            row = {"seed": seed, "ply": ply, "horizon": len(ref),
                   "forced": s["action"], "alt": alt,
                   "settle_moved": meta["settle_moved"],
                   "match_ok": match_ok, "match_first_bad": first_bad,
                   "match_len": (len(got), len(ref)),
                   "control_ok": ctrl_ok, "control_first_div": ctrl_first_div,
                   "ok": bool(ok)}
            results.append(row)
            if verbose:
                print(f"  seed {seed:5d} ply {ply:3d} H={len(ref):2d}  "
                      f"MATCH {'PASS' if match_ok else 'FAIL'}"
                      f"{'' if first_bad is None else f' (first bad lock {first_bad})'}"
                      f"  CONTROL {'PASS' if ctrl_ok else 'FAIL'}"
                      f" (diverges at lock {ctrl_first_div})"
                      f"  settle_moved={meta['settle_moved']}", flush=True)
    return all_ok, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(2, 12)))
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--plies", type=int, nargs="+", default=[20, 35, 50])
    ap.add_argument("--level", type=int, default=11)
    ap.add_argument("--wt", type=int, default=0)
    ap.add_argument("--ws", type=int, default=20)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    print(f"=== forced-move harness GATE: seeds={a.seeds} plies={a.plies} "
          f"H={a.horizon} L{a.level} wt={a.wt} ws={a.ws} ===", flush=True)
    ok, rows = run_gate(a.seeds, a.horizon, a.plies, a.level, a.wt, a.ws)
    n = len(rows)
    nm = sum(r["match_ok"] for r in rows)
    nc = sum(bool(r["control_ok"]) for r in rows)
    print(f"\n  snapshots gated : {n}")
    print(f"  MATCH   passed  : {nm}/{n}")
    print(f"  CONTROL passed  : {nc}/{n}")
    print(f"\nGATE {'PASS' if ok and n else 'FAIL'}")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump({"ok": bool(ok and n), "rows": rows}, fh, indent=1)
    return 0 if (ok and n) else 1


if __name__ == "__main__":
    raise SystemExit(main())
