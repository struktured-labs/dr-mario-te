"""H12 pre-launch gates. Each must FAIL on a wrong input by construction:
G1 IDENTITY: tie_margin=1e9 (accepts nothing) => outcomes == const arm, seed for seed.
G2 DETERMINISM: same seed twice => identical results dict.
G3 DOSED SMOKE: theta=0.5 on 12 seeds => flip dose within [0.5%,6%] of plies
   (calibration said ~2.3%), secs/pair printed for cost projection."""
import sys, time
sys.path.insert(0, '.')
import oracle_arm as OA
from h12_arm import H12Arm

C, bmodel = OA.init_rig("lulu")
ok = True

# G1 identity
for s in (41000, 41001, 41002, 41003, 41004, 41005, 41006, 41007, 41008, 41009):
    ai = H12Arm(label_mode="true", tie_margin=1e9, provenance=False)
    ri = OA.play_one(s, ai, C, bmodel)
    ac = OA.OracleArm(label_mode="const")
    rc = OA.play_one(s, ac, C, bmodel)
    same = all(ri[k] == rc[k] for k in ("won","topout","stall","pills","dies_ahead"))
    ok &= same and ri["flips"] == 0
    if not same: print(f"G1 FAIL seed {s}")
print(f"G1 IDENTITY (margin=inf == const, 10 seeds): {'PASS' if ok else 'FAIL'}")

# G2 determinism
g2 = True
for s in (41010, 41011):
    r1 = OA.play_one(s, H12Arm(label_mode='true', tie_margin=0.5), C, bmodel)
    r2 = OA.play_one(s, H12Arm(label_mode='true', tie_margin=0.5), C, bmodel)
    r1.pop('_actions', None); r2.pop('_actions', None)
    g2 &= (r1 == r2)
print(f"G2 DETERMINISM: {'PASS' if g2 else 'FAIL'}"); ok &= g2

# G3 dosed smoke
t0 = time.monotonic(); fl = pl = 0; secs = []
for s in range(41020, 41032):
    ts = time.monotonic()
    ab = OA.OracleArm(label_mode="const"); OA.play_one(s, ab, C, bmodel)
    at = H12Arm(label_mode="true", tie_margin=0.5, provenance=True)
    rt = OA.play_one(s, at, C, bmodel)
    fl += rt["flips"]; pl += rt["plies_scored"]; secs.append(time.monotonic()-ts)
dose = 100*fl/max(pl,1); sp = sum(secs)/len(secs)
g3 = 0.5 <= dose <= 6.0
print(f"G3 SMOKE: dose {dose:.2f}% of plies ({fl}/{pl}), {sp:.1f}s/pair -> 9000 pairs ~ {9000*sp/3600:.0f} core-h: {'PASS' if g3 else 'FAIL'}")
ok &= g3
print("H12 GATES", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
