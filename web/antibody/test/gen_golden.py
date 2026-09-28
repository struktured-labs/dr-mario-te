import sys, json, random, os
CVX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "experiments", "cvx")
CVX = os.path.abspath(CVX)
sys.path.insert(0, CVX)
os.chdir(CVX)
import import_pin; import_pin.pin()
import numpy as np
import fast_rtl_x as FX
import cascade_leaf5b_x as L5b
import reach_fw_tap as RT
import steer_model as SM
from fb import FB

w, fl = FX.variant("winner")
w = np.asarray(w, dtype=np.float64); fl = np.asarray(fl, dtype=np.int32)
w5 = np.asarray([0, 0, 0, 512], dtype=np.int64)
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
out = []
while len(out) < N:
    fb = FB()
    lvl = rng.randrange(0, 21)
    nvir = min(84, 4 * (lvl + 1))
    vtop = 6 if lvl <= 14 else (5 if lvl <= 16 else (4 if lvl <= 18 else 3))
    placed = 0
    while placed < nvir:
        r = rng.randrange(vtop, 16); c = rng.randrange(8)
        if fb.col[r * 8 + c]: continue
        fb.col[r * 8 + c] = rng.randint(1, 3); fb.vir[r * 8 + c] = 1; placed += 1
    for _ in range(rng.randrange(0, 40)):
        o = rng.randrange(2); c = rng.randrange(8)
        rest = fb.resting(o, c)
        if rest is None: continue
        r0, c0, r1, c1 = rest
        fb.place_at(r0, c0, rng.randint(1, 3), r1, c1, rng.randint(1, 3))
        fb.resolve()
    if fb.virus_count() == 0: continue
    col = np.array(fb.col, dtype=np.int8); vir = np.array(fb.vir, dtype=np.int8); lnk = np.array(fb.lnk, dtype=np.int8)
    k = rng.randrange(0, 200)
    speed = rng.randrange(3)
    thr = SM.table_threshold(k, speed)
    color2d = [[int(col[r * 8 + c]) for c in range(8)] for r in range(16)]
    mask = np.asarray(RT.reach_mask_fw(color2d, thr, tap=2), dtype=np.int8)
    ca, cb, na, nb = [rng.randint(1, 3) for _ in range(4)]
    a = L5b._choose_d3_chain_s_leaf5(col, vir, lnk, ca, cb, na, nb, 8, 24, 40, w, fl, 0, 540, 20, mask, 0, 9, 0, 10, w5)
    out.append(dict(col=col.tolist(), vir=vir.tolist(), lnk=lnk.tolist(), ca=ca, cb=cb, na=na, nb=nb,
                    thr=int(thr), mask=mask.tolist(), action=int(a)))
json.dump(out, sys.stdout)
