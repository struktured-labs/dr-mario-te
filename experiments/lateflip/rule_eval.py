"""Offline check of DRLATEGUARD rule variants against FLAG-OFF Mesen traces (lateflip_probe logs).

For every target change the driver adopted AFTER committing (the late retargets), evaluate the rule on the state the
hook saw (the previous frame's endFrame values: x, rot, y, gravity counter) and the injected board, and compare with
what the flag-off cart actually did: did it COMPLETE the new target (landing == new target) or land something else?

Usage: rule_eval.py CASES.jsonl LOG [M=0] [mode=cool|first]
"""
import json, re, sys
sys.path.insert(0, "/home/struktured/projects/dr-mario-lateflip-wt/tools/lateflip")
from parse_lateflip import load

SPEED = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
         0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
         0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
         0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
         0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00]
G2V = {0: 0, 2: 1, 3: 2, 1: 3}           # game orient -> sim variant
T = re.compile(r"^T p(\d+) f=(\d+) y=(\d+) x=(\d+) rot=(\d+) na=(\d+) grav=(\d+) \| tgt=(\d+),(\d+) rd2=(\d+)")


def rule(board, x, rot, y, grav, c2, o2, spu, M, P=2, mode="cool", rowcap=2):
    thr = SPEED[min(80, 0x19 + spu)]
    dcol = abs(c2 - x)
    d = (o2 - rot) & 3
    presses = dcol + (0 if d == 0 else (2 if d == 2 else 1))
    need = presses * P + M if mode == "cool" else (presses - 1) * P + 1 + M
    lo = min(x, c2)
    hi = min(7, max(x, c2 + (1 if o2 % 2 == 0 else 0)))     # sweep after the pre-phase rotation (V->H kicks left)
    r = 15 - min(15, y)
    occ = lambda rr, cc: board[rr * 8 + cc] not in (0x00, 0xFF)
    if any(occ(r, c) for c in range(lo, hi + 1)):
        return False, need, -1, "own-row blocked"
    K = 0
    while K < rowcap and r + 1 + K <= 15 and not any(occ(r + 1 + K, c) for c in range(lo, hi + 1)):
        K += 1
    left = max(0, thr - grav)
    if dcol > 0:
        avail = left + (K - 1) * (thr + 1) if K >= 1 else -1
    else:
        avail = left + K * (thr + 1)
    return avail >= need, need, avail, f"K={K} thr={thr} grav={grav}"


def main():
    cases = {json.loads(l)["p"]: json.loads(l) for l in open(sys.argv[1])}
    log = sys.argv[2]
    M = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    mode = sys.argv[4] if len(sys.argv) > 4 else "cool"
    rowcap = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    L = load(log)
    rows = []
    for line in open(log, errors="replace"):
        m = T.match(line)
        if m:
            rows.append(tuple(int(v) for v in m.groups()))
    tab = {"acc&done": 0, "acc&hyb": 0, "ref&done": 0, "ref&hyb": 0}
    for p, c in sorted(L.items()):
        if not c["land"] or p not in cases:
            continue
        R = [r for r in rows if r[0] == p][: len(c["frames"])]
        board = [int(v, 16) for v in cases[p]["upload"].split()[4:]]
        spu = (int(cases[p]["upload"].split()[2]) >> 4) | ((int(cases[p]["upload"].split()[3]) >> 4) & 3) << 4
        committed = False
        for i in range(1, len(R)):
            prev, cur = R[i - 1], R[i]
            if prev[9] == 1 or prev[9] == 0 and committed:
                pass
            if prev[9] == 1:
                committed = True
            if committed and (cur[7], cur[8]) != (prev[7], prev[8]):
                ok, need, avail, why = rule(board, prev[3], prev[4], prev[2], prev[6], cur[7], cur[8], spu, M, mode=mode, rowcap=rowcap)
                tgt_act = G2V[cur[8]] * 8 + cur[7]
                done = c["land"]["act"] == tgt_act
                key = ("acc" if ok else "ref") + ("&done" if done else "&hyb")
                tab[key] += 1
                print(f"p{p:3d} f={cur[1]:3d} ({prev[3]},{prev[4]}) -> ({cur[7]},{cur[8]}) a{tgt_act:2d} need={need:2d} "
                      f"avail={avail:3d} {why:24s} rule={'ACCEPT' if ok else 'REFUSE'} | flag-off landed a{c['land']['act']} "
                      f"{'(completed)' if done else '(NOT completed)'} sil a{c['land']['sil']}")
    print(tab)


if __name__ == "__main__":
    main()
