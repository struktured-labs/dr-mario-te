#!/usr/bin/env python3
"""py65 WHOLE-DECISION A/B of the four firmware arms on one board corpus (reset stub -> search -> tuck extension ->
DONE), streaming one JSON row per board. Arms: off (= the fw 1488e158 logic), tr (DRTUCKREACH), ro (DRROOTORD),
tl (DRTUCKLIVE), the pairs trro / trtl / rotl, and ship (all three). Per arm: final (col, o4), tuck descriptor, tuck commits, the live mailbox trajectory, reach state at the tuck
entry. gate_tuckreach.py / gate_rootord.py read the rows.

Corpora (--src):
  game   experiments/reach/corpus game_l11 + game_l15 (gate-(b) games, own pills + gravity), every --step'th board
  couch  the 10/03 couch cases (h16-wt couch_forensics/cases_dist60_20261003.jsonl, all games) as the cart uploads
         them (pubtrace_g2.upload layout: DRSEED nibbles 0, DRREACHTX gravity, DRTAPP 2)
Usage: py65_ab.py --src game --step 7 --out OUT.jsonl [--workers 4] [--arms off,tr,ro,both]
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ARMS = {"off": (0, 0, 0), "tr": (1, 0, 0), "ro": (0, 1, 0), "tl": (0, 0, 1), "trro": (1, 1, 0), "trtl": (1, 0, 1),
        "rotl": (0, 1, 1), "ship": (1, 1, 1)}           # (DRTUCKREACH, DRROOTORD, DRTUCKLIVE)
CF = "/home/struktured/projects/dr-mario-h16-wt/experiments/couch_forensics"
_IMG = {}


def init(arms):
    import fwlib as F
    for a in arms:
        tr, ro, tl = ARMS[a]
        _IMG[a] = F.image(tr, ro, DRTUCKLIVE=tl)
    _IMG["_md5"] = {a: F.hex_md5(_IMG[a]) for a in arms}


def boards(src, step, limit):
    import fwlib as F
    out = []
    if src == "game":
        for j, d in enumerate(F.load_corpus(step=step)):
            p = [x - 1 for x in d["pills"]]
            out.append(dict(id=f"game{d['level']}_{d['seed']}_{d['k']}", nes=d["nes"],
                            go=F.transport(*p, d["speed"], d["speedups"]), thr=F.thr_of(d["speed"], d["speedups"]),
                            nv=sum(1 for v in d["nes"] if v != 0xFF and (v & 0xF0) == 0xD0)))
    elif src == "couch":
        sys.path.insert(0, CF)
        import analyze_g2 as A
        sys.path.insert(0, "/home/struktured/projects/dr-mario-fwtuckreach-wt/experiments/cosim_farm")
        from cosim import board_to_nes
        for fn in ("cases_dist60_20261003.jsonl", "cases_g2_dist60_20261003.jsonl"):
            for l in open(os.path.join(CF, fn)):
                q = json.loads(l)
                if fn.startswith("cases_dist60") and q.get("game") == "G2":
                    continue                       # G2 comes from its own (complete) file
                game = q.get("game", "G2")
                b = A.board_from_strings(q["S"]["color"], q["S"]["virus"], q["S"]["link"])
                nes = list(board_to_nes(b))
                spu = min(49, q["p"] // 10)
                ca, cb = q["cur"][0] - 1, q["cur"][1] - 1
                na, nb = q["nxt"][0] - 1, q["nxt"][1] - 1
                go = F.transport(ca, cb, na, nb, 1, spu)
                out.append(dict(id=f"{game}_p{q['p']}", nes=nes, go=go, thr=F.thr_of(1, spu),
                                nv=q.get("virus_count", sum(1 for v in nes if v != 0xFF and (v & 0xF0) == 0xD0))))
        out = out[::step]
    return out[:limit] if limit else out


def task(bd):
    import fwlib as F
    row = dict(id=bd["id"], nv=bd["nv"], thr=bd["thr"], go=list(bd["go"]), nes=bd["nes"])
    row["mask"] = F.mask_o4(bd["nes"], bd["thr"], F.TAPP)
    for a in [k for k in _IMG if not k.startswith("_")]:
        t0 = time.time()
        r = F.run(_IMG[a], bd["nes"], *bd["go"])
        row[a] = dict(final=r["final"], tuck=r["tuck"], commits=r["commits"], pubs=r["pubs"], entry=r["entry"],
                      steps=r["steps"], cycles=r["cycles"], secs=round(time.time() - t0, 1))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="game"); ap.add_argument("--step", type=int, default=7)
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--arms", default="off,tr,ro,tl,trtl,ship")
    ap.add_argument("--include", default="", help="board ids always run first (e.g. the G2 tuck boards)")
    args = ap.parse_args()
    arms = args.arms.split(",")
    B = boards(args.src, args.step, args.limit)
    if args.include:
        have = {b["id"] for b in B}
        B = [b for b in boards(args.src, 1, 0) if b["id"] in set(args.include.split(",")) - have] + B
    done = set()
    if os.path.exists(args.out):
        done = {json.loads(l)["id"] for l in open(args.out)}
    todo = [b for b in B if b["id"] not in done]
    print(f"{len(B)} boards, {len(done)} already in {args.out}, running {len(todo)} x arms {arms}", flush=True)
    with mp.get_context("fork").Pool(args.workers, initializer=init, initargs=(arms,)) as pool, \
            open(args.out, "a") as fh:
        for i, row in enumerate(pool.imap_unordered(task, todo, chunksize=1)):
            fh.write(json.dumps(row) + "\n"); fh.flush()
            if i % 10 == 0:
                print(f"  {i + 1}/{len(todo)}", flush=True)
    init(arms)
    print("arm md5 (py65 non-delta logic images):", _IMG["_md5"])


if __name__ == "__main__":
    main()
