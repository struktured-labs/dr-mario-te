"""Dump real game boards for the DRREACH firmware gate: gate-(b) fw540 games with couch steering on.
Each line: {"level", "seed", "k", "speed", "speedups", "thr", "color": 16x8 (0 empty), "virus": 16x8, "mask": reach_fw 32}.
Usage: python reach_corpus_dump.py OUT.jsonl LEVEL SEED [SEED ...]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import import_pin; import_pin.pin()
import gate_b as G, bursty_model as BM, vs_race as V, steer_model as SM, reach_fw as RF
out, level, seeds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3:]]
m = BM.fit_struktured_20260804(); base = V._decider("fw540")
fh = open(out, "a")
for s in seeds:
    rec = []
    def choose(env, col, vir, ctx):
        k = env.pills_placed
        su = min(49, k // 10)
        color = env.board.color.tolist()
        thr = SM.table_threshold(k)
        rec.append({"level": level, "seed": s, "k": k, "speed": 1, "speedups": su, "thr": thr, "color": color,
                    "nes": [0xFF if int(env.board.color[r, c]) == 0 else ((0xD0 if env.board.is_virus[r, c] else 0x40) | (int(env.board.color[r, c]) - 1)) for r in range(16) for c in range(8)], "pills": [int(env.cur.a), int(env.cur.b), int(env.nxt.a), int(env.nxt.b)],
                    "virus": env.board.virus.tolist() if hasattr(env.board, "virus") else None,
                    "mask": RF.reach_mask_fw(color, thr)})
        return base(env, col, vir, ctx)
    G.play(s, None, m, level=level, choose=choose, steer=SM.Steer(proph="throat"))
    for r in rec:
        fh.write(json.dumps(r) + "\n")
    fh.flush(); print(s, len(rec), flush=True)
