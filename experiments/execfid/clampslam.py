"""Q2 census: DISTGATE CLAMP-SLAMS in Mesen replay logs (execfid_probe / lateflip_probe T lines).
A clamp-slam = the first frame the driver holds DOWN ($F8 bit $04: a new press or a hold it keeps) while the capsule sits at
DISTGATE's clamped target EFF_DIST2 ($6194) and that is NOT the answer's column TGT_C2 ($6152): the slam gate (dn_p2)
reads the clamped target as "aligned". p107-type = on a PROPH-armed pill (PROPH_DIR $61B2 != 0 on the spawn row).
'reachable' = the frames left in the current row before the next gravity tick, thr - $0392 (thr from the ROM table at
MED, speedUps = the case's spu), cover |x - tgt| presses at one per 2 f (DRDISTROW's budget).
Usage: clampslam.py LOG [LOG ...]"""
import re, sys
T = re.compile(r"^T p(\d+) f=(\d+) y=(\d+) x=(\d+) rot=(\d+) na=(\d+) grav=(\d+) \| tgt=(\d+),(\d+) rd2=(\d+) arm=(\d+) "
               r"pend=(\d+) dly=(\d+) eff=(\d+) bud=(\d+) fall=(\d+) proph=(\w+) lg=(\d+),(\d+) \| pad=(\w+) held=(\w+)")
LAND = re.compile(r"^LAND p(\d+) f=(\d+) x=(\d+) y=(\d+) rot=(\d+) action=(\d+) \| sil=(-?\w+) sim=(\d+) cosim_final=(\d+)")
INJ = re.compile(r"^INJECT p(\d+) at f=\d+ \(.*\) spu=(\d+)")
SPEED = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27, 0x25, 0x23,
         0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D, 0x0C, 0x0B, 0x0A, 0x09,
         0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
         0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03, 0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01,
         0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00]


def scan(path):
    C = {}; spu = {}
    for line in open(path, errors="replace"):
        m = INJ.match(line)
        if m:
            spu[int(m.group(1))] = int(m.group(2)); continue
        m = T.match(line)
        if m:
            g = m.groups(); p = int(g[0]); c = C.setdefault(p, {"fr": [], "land": None})
            if c["land"] is None:
                c["fr"].append(dict(f=int(g[1]), y=int(g[2]), x=int(g[3]), na=int(g[5]), grav=int(g[6]), tc=int(g[7]),
                                    rd2=int(g[9]), eff=int(g[13]), bud=int(g[14]), proph=int(g[16], 16),
                                    pad=int(g[19], 16), held=int(g[20], 16)))
            continue
        m = LAND.match(line)
        if m:
            p = int(m.group(1)); c = C.setdefault(p, {"fr": [], "land": None})
            if c["land"] is None:
                c["land"] = dict(act=int(m.group(6)), sil=m.group(7), fin=int(m.group(9)), x=int(m.group(3)))
    out = []
    for p, c in sorted(C.items()):
        fr = [x for x in c["fr"] if x["na"] == 0]
        if not fr or not c["land"]:
            continue
        armed = any(x["proph"] and x["y"] == 15 for x in fr)
        ev = None
        for i, x in enumerate(fr):
            # first frame the committed capsule sits at DISTGATE's clamped target: the budget is short of the answer
            # column (a TUCK approach column also differs from TGT_C2, but with budget to spare: not a clamp)
            if x["rd2"] and x["x"] == x["eff"] and x["eff"] != x["tc"] and x["bud"] < abs(x["x"] - x["tc"]):
                thr = SPEED[min(80, 0x19 + spu.get(p, 0))]
                left = max(0, thr - x["grav"])
                slam = any(y["held"] & 4 for y in fr[i:])
                ev = dict(f=x["f"], x=x["x"], tgt=x["tc"], bud=x["bud"], y=x["y"], frames_left=left,
                          reachable=left // 2 >= abs(x["x"] - x["tc"]), how="slam" if slam else "gravity",
                          landed_there=c["land"]["x"] == x["x"])
                break
        out.append(dict(p=p, armed=armed, ev=ev, land=c["land"]))
    return out


def main():
    tot = dict(pills=0, armed=0, cs=0, cs_armed=0, cs_armed_reach=0, cs_armed_miss=0, cs_other_reach=0)
    for path in sys.argv[1:]:
        R = scan(path)
        a = [r for r in R if r["armed"]]
        cs = [r for r in R if r["ev"]]
        csa = [r for r in cs if r["armed"]]
        print(f"{path.split('/')[-2]:32s} pills {len(R):3d} PROPH-armed {len(a):2d} | clamps {len(cs):2d} (on PROPH-armed "
              f"{len(csa)}, target reachable in the current row {sum(r['ev']['reachable'] for r in csa)}, landing != copro final "
              f"{sum(r['land']['act'] != r['land']['fin'] for r in csa)}) | non-armed clamp-slams reachable "
              f"{sum(r['ev']['reachable'] for r in cs if not r['armed'])}")
        for r in cs:
            e = r["ev"]
            print(f"     p{r['p']:3d} {'PROPH' if r['armed'] else 'plain'} {e['how']} clamp f{e['f']} y={e['y']} x={e['x']} answer col {e['tgt']} "
                  f"budget {e['bud']} frames-left {e['frames_left']} {'REACHABLE' if e['reachable'] else 'unreachable'} | "
                  f"land a{r['land']['act']} final a{r['land']['fin']} silicon a{r['land']['sil']}")
        tot["pills"] += len(R); tot["armed"] += len(a); tot["cs"] += len(cs); tot["cs_armed"] += len(csa)
        tot["cs_armed_reach"] += sum(r["ev"]["reachable"] for r in csa)
        tot["cs_armed_miss"] += sum(r["land"]["act"] != r["land"]["fin"] for r in csa)
        tot["cs_other_reach"] += sum(r["ev"]["reachable"] for r in cs if not r["armed"])
    print("TOTAL", tot)


if __name__ == "__main__":
    main()
