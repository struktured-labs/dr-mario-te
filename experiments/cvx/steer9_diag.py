"""STEER9 post-hoc diagnostic (NOT pre-registered): why do the veto arms top out early? Replays gb10 games of an arm
with a per-decision log: chosen root vs the no-penalty argmax (= FAIR's brain), heights, n_new of both, whether the
chosen root plugs the spawn cells (DRVETO's _veto_plug test), and the root values.

  python steer9_diag.py ARM SEED [SEED ...]   -> steer9/diag/diag_ARM.jsonl + printed summary
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import steer9_run as R9
import stuck_probe as SP, refit_opp as RO
import seal_steer9 as S9
from cascade_link_x import board_flat

arm = sys.argv[1]; seeds = [int(s) for s in sys.argv[2:]]
steer, choose, dec = R9.make(arm)
log = []
orig = dec.choose
def wrapped(board, cur, nxt, k=0):
    col, vir = board_flat(board)
    a = orig(board, cur, nxt, k)
    a0 = int(dec.act0[0])
    h = [16 - next((r for r in range(16) if board.color[r, c]), 16) for c in range(8)]
    plug = (lambda x: None if x is None or x < 0 else bool(S9._veto_plug(col, x // 8, x % 8)))
    log.append(dict(k=k, a=a, a0=a0, h=h, nv=int(vir.sum()), nnew_a=int(dec.nnew[a]) if a is not None else None,
                    nnew_a0=int(dec.nnew[a0]) if a0 >= 0 else None, plug_a=plug(a), plug_a0=plug(a0),
                    val_a=int(dec.vals[a]) if a is not None else None, nzero=int(np.sum(dec.nnew == 0)),
                    nallowed=int(np.sum(dec.nnew >= 0))))
    return a
dec.choose = wrapped
opp = RO.make_opponent("owner202610")
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "steer9", "diag", f"diag_{arm}.jsonl"), "a")
for s in seeds:
    log.clear()
    r = SP.play_gb(s, choose, steer, opp, probe=None)
    ch = [x for x in log if x["a"] != x["a0"]]
    cols = np.zeros(8, int)
    for x in ch:
        c = x["a"] % 8; cols[c] += 1
        if x["a"] // 8 < 2 and c < 7: cols[c + 1] += 1
    print(f"seed {s} {r['how']} pills {r['pills']} vleft {r['vleft']}: changed {len(ch)}/{len(log)}; changed roots that PLUG "
          f"{sum(1 for x in ch if x['plug_a'])}, base would plug {sum(1 for x in ch if x['plug_a0'])}; columns of changed "
          f"roots {cols.tolist()}; final heights {log[-1]['h']}")
    print("   last 8 decisions:", [(x["k"], x["a"], x["a0"], x["nnew_a0"], x["plug_a"], x["h"][3], x["h"][4]) for x in log[-8:]])
    out.write(json.dumps({"seed": s, "arm": arm, "row": {k: r[k] for k in ("how", "pills", "vleft", "topout")}, "log": log}) + "\n")
