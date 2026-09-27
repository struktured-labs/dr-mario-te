import sys, os
RAM = 0x102B08; ROW = 20
d = sys.argv[1]; names = sys.argv[2:]; prev = None
print(f"{'state':5s} {'act':>3} {'pause':>5} {'X':>2} {'Y':>3} {'spd':>3} {'vel':>3} | frames since prev (controlled)  dX")
for n in names:
    p = os.path.join(d, n + ".ss")
    b = open(p, "rb").read(); r = lambda a: b[RAM + a]
    cur = dict(act=r(0x317), pause=r(0x68D), X=r(0x305), Y=r(0x306), spd=r(0x312), vel=r(0x313), cp=r(0x58))
    k = dx = ""
    if prev and cur["act"] == 0 and prev["act"] == 0:
        k = ROW * (prev["Y"] - cur["Y"]) + cur["spd"] - prev["spd"]; dx = cur["X"] - prev["X"]
    print(f"{n:5s} {cur['act']:3d} {cur['pause']:5d} {cur['X']:2d} {cur['Y']:3d} {cur['spd']:3d} {cur['vel']:3d} | {str(k):>6} {str(dx):>4}   (zp currentP={cur['cp']})")
    prev = cur
