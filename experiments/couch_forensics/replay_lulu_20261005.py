"""2026-10-05 couch: brain-only replays (perfect-execution bound) for any game -- would the AI, executing the
SILICON-FAITHFUL brain (Leaf6FwDecider = fw 1488e158's main search) perfectly, have finished before dr. lulu?

g2_counterfactual_dist60's replay: from silicon's board at start pill p0, the brain places every OBSERVED capsule by
straight drop, her OBSERVED garbage (surviving cells of each received volley) dropped after the same pill. Outcome per
start: CLEAR (at which pill / time, and her remaining viruses then), TOPOUT, or alive at the last observed capsule with
N viruses. The capsule sequence is only known up to the AI's last spawn, so in a game she won by clearing, a replay that
is still alive at the end did NOT beat her.
Usage: GAME=m1g2 STEP=5 python replay_lulu_20261005.py   -> replay_<game>_lulu_20261005.jsonl
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m4g2_fair_20261004 as M  # noqa: E402  (pins the braingap paths)
import g2_counterfactual_dist60_20261003 as GC  # noqa: E402

GAME = os.environ["GAME"]; STEP = int(os.environ.get("STEP", "5"))


def main():
    dec = M.brain()
    Q = [json.loads(l) for l in open(os.path.join(HERE, f"cases_ai_{GAME}_lulu_20261005.jsonl"))]
    L = [json.loads(l) for l in open(os.path.join(HERE, "cases_lulu_20261005_lulu_pills.jsonl"))]
    L = [r for r in L if r["game"] == GAME]
    S = {g["game"]: g for g in json.load(open(os.path.join(HERE, "summary_lulu_20261005.json")))["games"]}[GAME]
    tq = {q["p"]: q["t_rel"] for q in Q}

    def her_at(t):
        v = 48
        for r in L:
            if r["t_rel"] <= t:
                v = r["virus_count"]
        return v
    out = open(os.path.join(HERE, f"replay_{GAME}_lulu_20261005.jsonl"), "w")
    for i0 in range(0, len(Q), STEP):
        R = GC.replay(Q, dec, i0)
        last = R[-1]
        rec = {"game": GAME, "p0": Q[i0]["p"], "t0": Q[i0]["t_rel"], "end": last[1], "end_p": last[0],
               "end_t": tq.get(last[0]), "viruses_end": last[2], "max_h_end": max(last[3]),
               "her_viruses_then": her_at(tq.get(last[0], 1e9)), "silicon_viruses_at_end": Q[-1]["virus_count"],
               "winner": S["winner"], "how": S["how"], "trace": [(p, s, v, max(h)) for (p, s, v, h) in R]}
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"{GAME} from p{rec['p0']:3d} (t {rec['t0']:6.1f}): {rec['end']:6s} at p{rec['end_p']} t {rec['end_t']} viruses "
              f"{rec['viruses_end']:2d} maxh {rec['max_h_end']:2d} | her viruses then {rec['her_viruses_then']}", flush=True)
    out.close()


if __name__ == "__main__":
    main()
