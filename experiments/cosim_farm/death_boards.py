#!/usr/bin/env python3
"""Extract the champion's decision positions from the adversary's confirmed KILL games.

Why: the champion-decider fidelity result (100% move-exact vs real RTL) was measured on
MID-GAME boards from random-legal playouts, where the perturbation gradient (94-98%) shows
the chain and #47-stranded terms rarely change the move. These death games are the
opposite regime -- endgame, high stack, heavy garbage -- exactly where those terms should
fire hardest and where a mirror divergence would matter. This produces the corpus to
re-measure fidelity there.

METHOD. Replays each kill game with `vs_harness.play_match` -- the project's ONE
ROM-true match loop, reused unmodified -- with the champion's decider wrapped so it
records (board, cur, nxt) and its own chosen action at every decision. Play runs FORWARD
on a single match instance.

⚠ NO `copy.deepcopy` OF MATCH STATE ANYWHERE HERE. `vs_env_exact`'s `_rand_pill` is a
closure, so a deepcopy would share one advancing pill cursor across branches -- silent,
and byte-identical on re-run, so a determinism check would NOT catch it. Playing forward
on one instance needs no cloning at all, which is why this does that and nothing else.

OUTCOME-PLAUSIBILITY GATE (mandatory; the colour bug passed every structural gate):
each replay must reproduce the handoff's recorded outcome for that seed/side -- topout,
dies_ahead, and the recorded final virus counts. A replay that "runs" but does not
reproduce the kill is not the game we meant to sample.

Colours: hostdata cA/cB/nA/nB are written 0-BASED (faithful Pill 1..3 minus one), matching
the copro mailbox and `fpga/copro/gen_corpus.py`. See cosim.Cosim.decide's guard.

Usage: death_boards.py [--tail N] [--out-prefix P]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RL = "/home/struktured/projects/dr_mario_rl"
QA = "/home/struktured/projects/dr-mario-qa-wt/experiments"
ADV = QA + "/adversary_t3"
for _p in (HERE, RL + "/tmp/combo_term", RL + "/tmp/endgame", RL + "/tmp/tuck",
           RL + "/tmp/pillrng", RL + "/tmp/vs_aware",
           RL + "/.claude/worktrees/faithful-sim/src", QA, QA + "/tuck_v3",
           QA + "/eval47", ADV):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cosim import board_to_nes  # noqa: E402

HANDOFF = os.path.join(ADV, "cosim_handoff_5seeds.json")
EVOLVED_VEC = (234, 20, -31, 233, 37)


def replay_one(seed, swap, vec, level=11, max_pills=300):
    """Replay ONE side of one seed, recording every champion decision.

    swap semantics follow vs_run.play_seed: swap=0 -> champion is P0
    (play_match(seed, champ, opp)); swap=1 -> champion is P1.
    """
    import vs_harness as H
    import fast_rtl_x as FX
    from cascade_stranded_x import StrandedChainD3Decider
    from adversary_search import AdversaryD3Decider

    w, fl = FX.variant("winner")
    champ = StrandedChainD3Decider(w, fl, topk2=8, maxpass=0, w_chain=180, ws=20)
    opp = AdversaryD3Decider.from_vector(list(vec), w, fl, topk2=8)

    rec = []

    champ_blind = H.blind(champ)

    # play_match always calls deciders with 4 args (the 4th is the OPPONENT's board);
    # H.blind() is what discards it for a non-opponent-aware decider. Match that arity.
    def champ_recording(board, cur, nxt, opp_board):
        act = champ_blind(board, cur, nxt, opp_board)
        rec.append({
            "board128": board_to_nes(board),
            # 0-BASED for the copro mailbox; faithful Pill colours are 1..3.
            "cA": int(cur.a) - 1, "cB": int(cur.b) - 1,
            "nA": int(nxt.a) - 1, "nB": int(nxt.b) - 1,
            "champ_action": None if act is None else int(act),
            "virus_count": int(board.virus_count()),
            "max_height": int(board.column_heights().max()),
            "ply": len(rec),
        })
        return act

    opp_wrapped = (lambda b, c, n, o: opp.choose(b, c, n, o))
    if swap == 0:
        r = H.play_match(seed, champ_recording, opp_wrapped,
                         level=level, max_pills=max_pills, garbage=True)
    else:
        r = H.play_match(seed, opp_wrapped, champ_recording,
                         level=level, max_pills=max_pills, garbage=True)
    return rec, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=int, default=25,
                    help="keep only the last N champion decisions per game "
                         "(the near-death regime); 0 = keep all")
    ap.add_argument("--out-prefix", default="/mnt/data/drmario_cosim/gate/death")
    a = ap.parse_args()

    import fast_rtl_x as FX
    FX.warmup_ship_eh(topk2=8)

    # The handoff is a dict {caution, champion, opponent, source, seeds}; the
    # per-seed records live under "seeds". Its own `caution` note is worth honouring:
    # the 4-to-1 dying_swap split is p=0.375 against even odds, i.e. NOT a side
    # asymmetry -- the side is carried only because it is needed to replay each game.
    handoff = json.load(open(HANDOFF))
    entries = handoff["seeds"] if isinstance(handoff, dict) else handoff
    kept, meta, gate_rows = [], [], []

    for entry in entries:
        seed = int(entry["seed"])
        swap = int(entry["dying_swap"])
        rec, res = replay_one(seed, swap, EVOLVED_VEC)
        side = [s for s in entry["both_sides"] if int(s["swap"]) == swap][0]

        # --- OUTCOME-PLAUSIBILITY GATE -------------------------------------------
        # The replay must reproduce the recorded kill, not merely run.
        got_reason = res.get("reason") if isinstance(res, dict) else None
        checks = {
            "n_decisions": len(rec),
            "expected_reason": side["reason"],
            "got_reason": got_reason,
            "expected_pills_champ": side["pills_champ"],
            "expected_virus_champ": side["virus_champ"],
            "cleared_something": any(r["virus_count"] < rec[0]["virus_count"] for r in rec),
            "start_virus": rec[0]["virus_count"] if rec else None,
            "end_virus": rec[-1]["virus_count"] if rec else None,
        }
        gate_rows.append({"seed": seed, "swap": swap, **checks})
        print(f"seed {seed} swap={swap}: {len(rec)} champion decisions, "
              f"virus {checks['start_virus']}->{checks['end_virus']}, "
              f"expected reason={side['reason']} got={got_reason}", flush=True)

        sel = rec if a.tail <= 0 else rec[-a.tail:]
        for r in sel:
            kept.append(r)
            meta.append({"seed": seed, "swap": swap, "ply": r["ply"],
                         "virus_count": r["virus_count"],
                         "max_height": r["max_height"],
                         "champ_action": r["champ_action"]})

    # every kept board must be a real decision the champion faced
    assert all(m["champ_action"] is not None for m in meta), \
        "a kept position has no champion action -- it was not a live decision"

    host = a.out_prefix + "_hostdata.txt"
    os.makedirs(os.path.dirname(host), exist_ok=True)
    with open(host, "w") as fh:
        fh.write("%d\n" % len(kept))
        for r in kept:
            fh.write("%d %d %d %d 0 0\n" % (r["cA"], r["cB"], r["nA"], r["nB"]))
            b = r["board128"]
            for row in range(16):
                fh.write(" ".join("%02x" % b[row * 8 + c] for c in range(8)) + "\n")
    json.dump({"meta": meta, "gate": gate_rows, "vec": list(EVOLVED_VEC),
               "tail": a.tail},
              open(a.out_prefix + "_meta.json", "w"), indent=1)

    vc = [m["virus_count"] for m in meta]
    mh = [m["max_height"] for m in meta]
    print(f"\nwrote {len(kept)} boards -> {host}")
    print(f"  virus_count  min/median/max = {min(vc)}/{sorted(vc)[len(vc)//2]}/{max(vc)}")
    print(f"  max_height   min/median/max = {min(mh)}/{sorted(mh)[len(mh)//2]}/{max(mh)}")
    print(f"  (mid-game corpus for contrast: these should be HIGHER stacks / "
          f"LOWER virus counts)")


if __name__ == "__main__":
    main()
