"""2026-10-05 M1 G4: ANTIBODY_DIST_FAIR (cart dbbb5007 + rbf 318607aa, fw 1488e158) TAPPED OUT vs dr. lulu at lulu 03 /
AI 16 (HUD) -- the only AI loss-by-top-out in the two matches. Forensics in the RESULT_COUCH_DIST60_G2 / 10/04 M4 G2 style.

Input: cases_ai_m1g4_lulu_20261005.jsonl (cases_lulu_20261005.py: hidden-spawn tracker + repair + the SILICON-FAITHFUL
brain Leaf6FwDecider = fw 1488e158's main search), the co-sim publish timeline (pubtrace_m1g4_lulu_20261005.jsonl), and
the chained + silicon-garbage Mesen replays of the real carts dbbb5007 (FAIR, as played) and 5b3d8183 (FAIRPLUS).

  stall     stall_fair_20261004.main on this game: virus provenance / sealing material / clearing moves per pill
            -> stall_m1g4_lulu_20261005.json + cases_stall_m1g4_lulu_20261005.jsonl
  replay    brain-only replays (the faithful brain, perfect execution, observed capsules + observed garbage) from EVERY
            pill p0 >= 60 to the last observed capsule: alive / cleared / topped out, viruses, heights. The decisive pills
            are where "brain from p0" survives but "brain from p0+1" does not.
            -> replay_m1g4_lulu_20261005.jsonl
  replay_early  the same from p0 = 0, 2, ..., 58 -> replay_early_m1g4_lulu_20261005.jsonl
  report    kill-sequence table (silicon vs brain vs copro final vs Mesen FAIR / FAIRPLUS), printed
Usage: python m1g4_lulu_20261005.py stall | replay | report
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("GAME", "m1g4")
import m4g2_fair_20261004 as M  # noqa: E402  (pins the braingap paths first)
import lulu_20261005 as L  # noqa: E402  (fair_20261004.SCAN / GAMES / window -> this recording)
import fair_20261004 as FA  # noqa: E402

GAME = "m1g4"
CASES = os.path.join(HERE, f"cases_ai_{GAME}_lulu_20261005.jsonl")
PUB = os.path.join(L.FX, "timelines", f"pubtrace_{GAME}_lulu_20261005.jsonl")   # banked copy: couch_forensics/pubtrace_*
RUNS = os.path.join(L.FX, "execfid", "runs")


def stall():
    import shutil
    import tempfile
    import stall_fair_20261004 as SF
    SF.GAME = GAME
    tmp = tempfile.mkdtemp(dir=os.path.join(L.FX, "scan"))
    SF.HERE = tmp
    SF.main()
    shutil.move(os.path.join(tmp, f"cases_stall_{GAME}_fair_20261004.jsonl"), os.path.join(HERE, f"cases_stall_{GAME}_lulu_20261005.jsonl"))
    shutil.move(os.path.join(tmp, f"stall_{GAME}_fair_20261004.json"), os.path.join(HERE, f"stall_{GAME}_lulu_20261005.json"))
    os.rmdir(tmp)


def replay(early=False):
    """early=False: every start pill p0 >= 60 -> replay_m1g4_lulu_20261005.jsonl; early=True: p0 = 0, 2, ..., 58 ->
    replay_early_m1g4_lulu_20261005.jsonl."""
    import g2_counterfactual_dist60_20261003 as GC
    dec = M.brain()
    Q = [json.loads(l) for l in open(CASES)]
    out = open(os.path.join(HERE, f"replay{'_early' if early else ''}_{GAME}_lulu_20261005.jsonl"), "w")
    for i0 in range(len(Q)):
        if (not early and Q[i0]["p"] < 60) or (early and (Q[i0]["p"] >= 60 or Q[i0]["p"] % 2)):
            continue
        R = GC.replay(Q, dec, i0)
        last = R[-1]
        rec = {"p0": Q[i0]["p"], "pills": len(R), "end": last[1], "end_p": last[0], "viruses_end": last[2], "heights_end": last[3],
               "max_h_end": max(last[3]), "silicon_viruses_at_p0": Q[i0]["virus_count"],
               "trace": [(p, s, v, max(h)) for (p, s, v, h) in R]}
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"from p{rec['p0']:3d}: end {rec['end']:6s} at p{rec['end_p']} viruses {rec['viruses_end']:2d} maxh {rec['max_h_end']:2d} "
              f"h {rec['heights_end']}", flush=True)
    out.close()


def report():
    sys.path.insert(0, os.path.join(HERE, "..", "execfid"))
    import report as XR
    Q = {q["p"]: q for q in map(json.loads, open(CASES))}
    T = {t["p"]: t for t in map(json.loads, open(PUB))}
    D = XR.landings(os.path.join(RUNS, f"lulu1005_{GAME}_D_chain_garb", f"lateflip_lulu1005_{GAME}_D_chain_garb.log"), PUB)
    P = XR.landings(os.path.join(RUNS, f"lulu1005_{GAME}_P_chain_garb", f"lateflip_lulu1005_{GAME}_P_chain_garb.log"), PUB)
    for p in sorted(Q):
        q = Q[p]; t = T.get(p, {}); d = D.get(p, {}); pp = P.get(p, {})
        fin = t.get("final", [None, None, None])[2]
        print(f"p{p:3d} v{q['virus_count']:2d} maxh {q['maxh']:2d} lane {q['lane']:2d} {q['category']:13s} sil a{q['actual_action']} "
              f"brain a{q['sim_action']} final a{fin} | Mesen FAIR a{d.get('act')} {'HYB' if d.get('hyb') else ''} | "
              f"FAIRPLUS a{pp.get('act')} {'HYB' if pp.get('hyb') else ''} | recv {q['garbage_recv']}")


if __name__ == "__main__":
    {"stall": stall, "replay": replay, "replay_early": lambda: replay(early=True), "report": report}[sys.argv[1]]()
