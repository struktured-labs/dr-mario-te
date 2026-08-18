"""FLIP SCREEN — price gate-v2's EXTRA flips directly, per flip.

Approved 2026-08-18 by the team lead in place of the N=9,000 endpoint. Registered
in PREREG_H13.md sec 9 with its decision rule fixed BEFORE any screen data
existed.

WHY THIS AND NOT THE ENDPOINT. H13 flips on a strict SUPERSET of H12's flip
plies, so the only decisions that can differ from H12 are the accepted flips
whose trigger was v2-ONLY (`gate_v2 and not gate_v1`). The endpoint would look
at those through whole-game outcomes — ~176 discordant pairs for $173-384. This
looks at them directly: ~200 flips for ~21 core-hours.

THE SCREEN is the project-standard CAPSULE-FAIR REFORK
([[dr-mario-flip-fairness-screen]]), which killed 7 of 10 "evaluator gap"
exhibits by showing they were seed-peeking. At each v2-only accepted flip we
fork BOTH the H12 keep (the champion's base action) and the H13 flip under K
UNSEEN capsule streams and compare mean progress. Within one alternate stream
both lines face the identical future, so the comparison is fair; averaging over
K streams removes the single-draw luck that a true-stream fork would reward.

⚠ SCOPE, and it is registered rather than discovered later: this prices PER-FLIP
quality, not the compounding of many flips across a game. It is a RULE-OUT
instrument ([[dr-mario-label-budget-rules]] — proxies rule out only). A negative
kills gate-v2 cheaply. A positive does NOT certify it; it licenses paying for
the endpoint that can.

The screen runs INLINE at the flip, so no board replay and no stored actions are
needed: the arm is already holding the exact env at the deciding ply.
"""
import argparse
import copy
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_W = {}


def alt_stream_clone(env, alt_seed):
    """Deepcopy `env` onto an UNSEEN capsule stream.

    `cur` is kept — it is the capsule being placed, part of the decision under
    test. `nxt` is redrawn from the alternate source, because under a different
    stream the preview is different. Both candidate lines then see the same
    alternate future (common random numbers), which is what makes the pair
    comparable within a stream.
    """
    from oracle_arm import PillDraw
    from nes_pills import NesPillSource
    e = copy.deepcopy(env)
    e._rand_pill = PillDraw(NesPillSource(seed=int(alt_seed)))
    e.nxt = e._rand_pill()
    return e


def _alt_seed(base, play_seed, j):
    """An UNSEEN capsule-stream seed, guaranteed different from the play seed.

    NesPillSource keys on 16 bits and seeds 2k/2k+1 alias to one stream
    ([[dr-mario-seed-space-is-32767]]), so equality must be checked on the
    CANONICAL (even) member, not the raw value — otherwise a "different" alt
    seed can silently be the game's own stream and quietly re-introduce the
    seed-peeking this screen exists to remove.
    """
    s = (base + 7919 * (play_seed % 100000) + 131 * j) & 0xFFFF
    if (s & ~1) == (play_seed & 0xFFFF & ~1) or s <= 1:
        s = (s + 12345) & 0xFFFF
    return s


def _board_args(env):
    """(col, vir, cur.a, cur.b, nxt.a, nxt.b) for _champ_values."""
    from fb import FB
    import root_search as RS
    col, vir = RS.board_flat_from_fb(FB.from_board(env.board))
    return (col, vir, int(env.cur.a), int(env.cur.b),
            int(env.nxt.a), int(env.nxt.b))


def _winit(thresh, k_streams, horizon, alt_base):
    import oracle_arm as O
    C, bmodel = O.init_rig("lulu")
    _W.update(O=O, C=C, bmodel=bmodel, thresh=thresh, k=k_streams,
              horizon=horizon, alt_base=alt_base)


SCREEN_MUTANTS = ("m_cursor_steal", "m_no_deepcopy")


def _hexb(arr):
    """Board plane -> hex. json-safe, diff-able, no pickle, no version skew."""
    import numpy as np
    return np.asarray(arr, dtype=np.uint8).tobytes().hex()


def _bhash(col, vir):
    """Board identity for dedup. Features are a lossy hash; use the bytes."""
    import hashlib
    import numpy as np
    h = hashlib.sha256()
    h.update(np.asarray(col, dtype=np.uint8).tobytes())
    h.update(np.asarray(vir, dtype=np.uint8).tobytes())
    return h.hexdigest()[:12]


class ScreeningArm:
    """Mixin factory — built at call time so it can close over rig constants.

    Defined at MODULE level, not inside `_work`, so `gate_screen.py` can prove
    the screening logger is INERT: its action sequence must equal the plain
    H13Arm's, seed for seed. Comparing outcomes is not enough — a logger that
    perturbs one decision in fifty passes an outcome check and still invalidates
    every screened flip. (Thanks to the distill lane for this one; my H13 gate
    certified H13Arm, while the thing that actually runs here is this SUBCLASS,
    which the gate never saw — a check whose scope was smaller than its claim.)
    """


def make_screening_arm(C, K, H, alt_base, events, mutant=None, store_boards=True):
    import numpy as np
    from oracle_arm import (_fork_label, gate_fires, heights, _champ_values,
                            CHAMP_ORDER)
    from h13_arm import H13Arm

    class _Arm(H13Arm):
        def choose(self, env, seed_, C_, bmodel_, w_, fl_, wt_, ws_, ply):
            v1_open, _ds, _vir = gate_fires(env)
            a, base_a = super().choose(env, seed_, C_, bmodel_, w_, fl_,
                                       wt_, ws_, ply)
            if a is None or base_a is None or a == base_a or v1_open:
                return a, base_a
            H_ = heights(env.board.color)
            rec = {"seed": int(seed_), "ply": int(ply),
                   "maxh": int(H_.max()), "d_spawn_h": int(max(H_[3], H_[4])),
                   "viruses": int(env.board.virus_count()),
                   "keep_action": int(base_a), "flip_action": int(a),
                   "keep": [], "flip": [], "rand": []}
            bargs = _board_args(env)
            if store_boards:
                # BOTH PLANES, taken from the SAME flattening the champion's
                # own decider consumes. Every virus-dependent term (BURIED,
                # MATCHED, g_stranded, g_tower) is UNRECOVERABLE from colour
                # alone, and you find that out on the day you want one.
                rec["pre_col"] = _hexb(bargs[0])
                rec["pre_vir"] = _hexb(bargs[1])
                rec["cur"] = [int(env.cur.a), int(env.cur.b)]
                rec["nxt"] = [int(env.nxt.a), int(env.nxt.b)]
                rec["bhash"] = _bhash(bargs[0], bargs[1])

            vals = _champ_values(*bargs, w_, fl_, wt_, ws_)
            legal = [int(s) for s in CHAMP_ORDER if np.isfinite(vals[int(s)])]
            pool = [c for c in legal if c not in (int(a), int(base_a))]
            rand_a = (pool[(int(seed_) * 7919 + ply) % len(pool)]
                      if pool else None)
            rec["rand_action"] = rand_a

            if mutant == "m_cursor_steal":
                # The classic defect this project already paid for: the screen
                # draws from the LIVE env, advancing the game's own capsule
                # cursor ([[dr-mario-deepcopy-pill-closure]]).
                env._rand_pill()

            for j in range(K):
                alt = _alt_seed(alt_base, int(seed_), j)
                if mutant == "m_no_deepcopy":
                    e_alt = env                      # screens ON the live game
                else:
                    e_alt = alt_stream_clone(env, alt)
                arms = [("keep", base_a), ("flip", a)]
                if rand_a is not None:
                    arms.append(("rand", rand_a))
                for tag, act in arms:
                    surv, prog = _fork_label(e_alt, act, C_, seed_, bmodel_,
                                             w_, fl_, wt_, ws_, H)
                    rec[tag].append([int(surv), int(prog)])
            events.append(rec)
            return a, base_a

    return _Arm


def _work(seed):
    """Play the H13 arm on `seed`; screen every v2-only accepted flip inline."""
    O, C, bmodel = _W["O"], _W["C"], _W["bmodel"]
    T, K, H = _W["thresh"], _W["k"], _W["horizon"]
    events = []
    Arm = make_screening_arm(C, K, H, _W["alt_base"], events)
    arm = Arm(gate_mode="v2", maxh_thresh=T, label_mode="true",
              tie_margin=0.5, provenance=True)
    t0 = time.monotonic()
    res = O.play_one(seed, arm, C, bmodel)
    # STORE THE ACTION SEQUENCE, not just the boards. Boards cover only the
    # plies we logged; the action sequence makes the WHOLE trajectory
    # replayable, which is the difference between a null screen being a dead
    # end and being a reusable v2-only corpus at ~6 s/game instead of ~150.
    actions = [int(x) for x in (res.pop("_actions", None) or [])]
    return {"seed": seed, "res": res["res"], "pills": res["pills"],
            "dies_ahead": res["dies_ahead"], "plies": res["plies_scored"],
            "flips": res["flips"], "actions": actions,
            "v1_gated_plies": arm.stats["v1_gated_plies"],
            "v2_only_gated_plies": arm.stats["v2_only_gated_plies"],
            "arm_tag": arm.arm_tag(), "events": events,
            "secs": round(time.monotonic() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, default=90000)
    ap.add_argument("--seed-count", type=int, default=500)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--thresh", type=int, default=13)
    ap.add_argument("--k-streams", type=int, default=17,
                    help="unseen capsule streams per flip (project standard 17)")
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--alt-base", type=int, default=500000,
                    help="alternate-stream seed base; MUST be far from every "
                         "registered play block so a screen stream is never a "
                         "block seed")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    assert a.seed_start >= 90000, (
        "PREREG_H13 sec 9 amendment: the screen block is 90000-90499 "
        "(72000-80999 was released to the distill lane)")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    done = set()
    if os.path.exists(a.out):
        for ln in open(a.out):
            try:
                done.add(json.loads(ln)["seed"])
            except Exception:
                pass
    seeds = [s for s in range(a.seed_start, a.seed_start + a.seed_count)
             if s not in done]
    print(f"SCREEN seeds={len(seeds)} (resume: {len(done)} already banked) "
          f"T={a.thresh} K={a.k_streams} H={a.horizon} workers={a.workers}",
          flush=True)

    from concurrent.futures import ProcessPoolExecutor
    t0 = time.monotonic()
    n = nev = 0
    with open(a.out, "a") as fh, ProcessPoolExecutor(
            max_workers=a.workers, initializer=_winit,
            initargs=(a.thresh, a.k_streams, a.horizon, a.alt_base)) as ex:
        for r in ex.map(_work, seeds):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            n += 1
            nev += len(r["events"])
            if n % 10 == 0:
                el = time.monotonic() - t0
                print(f"  {n}/{len(seeds)} games, {nev} screened flips, "
                      f"{el/60:.1f}min, {nev/max(n,1):.2f} flips/game",
                      flush=True)
    el = time.monotonic() - t0
    print(f"DONE {n} games, {nev} screened v2-only flips in {el/60:.1f} min "
          f"({el*a.workers/max(n,1):.0f} core-s/game) -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
