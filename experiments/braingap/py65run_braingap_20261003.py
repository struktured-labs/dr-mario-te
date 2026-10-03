#!/usr/bin/env python3
"""Run the shipped firmware logic under py65 with the RTL-faithful engine (rtlengine_braingap_20261003) on the couch
boards exactly as the cart uploaded them (the co-sim timeline's `upload` line), and bank per-board rows.

Usage: py65run_braingap_20261003.py TIMELINE.jsonl OUT.jsonl [--debug] [--delta] [--workers N] [p ...]
  TIMELINE  a pubtrace_G*_fw1488e158.jsonl (upload bytes + the Verilator co-sim final = ground truth)
  --debug   use the DEBUG_VAL1 image and bank the per-root components (C1,O1,V1,B2,I1,L1,AD,strand,veto)
  --delta   run the delta (shipped-byte) image instead of the non-delta build
Row: p, game, cosim final (col,o4), py65 final, match, tuck, per-root list (debug), reach R_FLT/ROK, DIST target,
     steps, engine command count, seconds.
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_IMG = {}


def init(debug, delta):
    import rtlengine_braingap_20261003 as E
    _IMG["img"] = E.image(delta=delta, debug=debug)
    _IMG["debug"] = debug


def task(rec):
    import rtlengine_braingap_20261003 as E
    nes, cA, cB, nA, nB = E.parse_upload(rec["upload"])
    t0 = time.time()
    r = E.run(_IMG["img"], nes, cA, cB, nA, nB, debug=_IMG["debug"])
    fin = list(r["final"])
    cos = rec["final"][:2]
    return dict(p=rec["p"], game=rec.get("game", "G2"), cosim=cos, py65=fin, match=fin == cos,
                cosim_tuck=rec.get("tuck"), py65_tuck=list(r["tuck"]), sim_action=rec.get("sim_action"),
                roots=r["roots"], rflt=r["rflt"], rok=r["rok"], tgt=r["tgt"], steps=r["steps"], ncmd=r["ncmd"],
                npub=len(r["pubs"]), secs=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("timeline"); ap.add_argument("out"); ap.add_argument("ps", nargs="*", type=int)
    ap.add_argument("--debug", action="store_true"); ap.add_argument("--delta", action="store_true")
    ap.add_argument("--workers", type=int, default=1); ap.add_argument("--game", default=None)
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(a.timeline)]
    game = a.game or ("G3" if "G3" in a.timeline else "G4" if "G4" in a.timeline else "G2")
    for r in recs:
        r["game"] = game
    if a.ps:
        want = set(a.ps)
        recs = [r for r in recs if r["p"] in want]
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(l)["p"] for l in open(a.out)}
    recs = [r for r in recs if r["p"] not in done]
    print(f"{len(recs)} boards to run ({len(done)} already banked) -> {a.out}", flush=True)
    with mp.get_context("fork").Pool(a.workers, initializer=init, initargs=(a.debug, a.delta)) as pool, \
            open(a.out, "a") as fh:
        for row in pool.imap(task, recs, chunksize=1):
            fh.write(json.dumps(row) + "\n"); fh.flush()
            print(f"p{row['p']:3d} cosim {row['cosim']} py65 {row['py65']} {'MATCH' if row['match'] else 'DIFF '} "
                  f"tuck {row['py65_tuck']} steps {row['steps']} cmds {row['ncmd']} {row['secs']}s", flush=True)


if __name__ == "__main__":
    main()
