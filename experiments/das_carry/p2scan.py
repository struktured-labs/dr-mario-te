import sys, glob, os, collections
R = 0x102B08
# ROM speedCounterTable (NTSC) and baseSpeedSettingValue
T = [0x45,0x43,0x41,0x3F,0x3D,0x3B,0x39,0x37,0x35,0x33,0x31,0x2F,0x2D,0x2B,0x29,0x27,0x25,0x23,0x21,0x1F,0x1D,0x1B,0x19,0x17,
     0x15,0x13,0x12,0x11,0x10,0x0F,0x0E,0x0D,0x0C,0x0B,0x0A,0x09,0x09,0x08,0x08,0x07]
BASE = [0x0F, 0x19, 0x1F]
d = sys.argv[1]; vel = collections.Counter(); rows = []
for p in sorted(glob.glob(os.path.join(d, "s*.ss"))):
    b = open(p, "rb").read(); r = lambda a: b[R + a]
    act, X, Y, spd, v, ups, st = r(0x397), r(0x385), r(0x386), r(0x392), r(0x393), r(0x38A), r(0x38B)
    if r(0x46) != 4: continue
    idx = min(len(T) - 1, BASE[st % 3] + ups); fr = T[idx] + 1
    ctl = fr * (15 - Y) + spd if act == 0 else None
    vel[v] += 1
    rows.append((os.path.basename(p), act, X, Y, spd, v, fr, ctl))
print("P2 horVelocity histogram (all in-game snapshots):", dict(sorted(vel.items())))
print("controlled snapshots (act=0): name X Y spd v frames/row ~frames-since-spawn |X-3|")
for n, act, X, Y, spd, v, fr, ctl in rows:
    if act == 0: print(f"  {n} X={X} Y={Y} spd={spd} v={v} fr/row={fr} f~{ctl} dx={abs(X-3)}")
