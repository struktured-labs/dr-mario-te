#!/usr/bin/env python3
"""GATE for DRLATEGUARD's decision routine: the REAL emitted lg_gate (couch cart flags + DRLATEGUARD=1, captured by
tools/nmi126/capture_ir.py) run under py65 on random driver/board states == the Python reference rule below, which is
the flag-block spec in patch_cartridge_copro.py written out:

  not committed (LG_CMT2 == 0)         -> adopt                 (pre-commit retargets untouched)
  already frozen (LG_LOCK2 != 0)       -> keep
  candidate == (TGT_C2, TGT_O2)        -> adopt                 (nothing changes)
  else  presses = |C - X| + rot(O - R) (DRROTDIR: delta 1|3 -> 1, 2 -> 2)
        need    = presses * P + M
        thr     = speedCounterTable[min(80, base[$038B (>=3 -> 1)] + $038A)]
        span    = [min(X, C) .. max(X, min(7, C + H'))]      H' = 1 if O is horizontal (even)
        own row (15 - Y) must be empty across the span, else keep+freeze
        avail   = max(0, thr - $0392) + (thr + 1) * K         K = empty rows below across the span, <= min(Y, ROWCAP)
        lateral (C != X): avail -= thr + 1 (borrow -> keep+freeze)
        adopt iff avail >= need, else keep+freeze (LG_LOCK2 <- 1)

Checks: 0 mismatches (carry AND LG_LOCK2) over N random states on the real routine; both test-only mutants
(DRLATEGUARD_MUT=always / never) are KILLED (they must disagree with the reference); DRLATEGUARD=0 emits no lg_gate.
Usage: gate_lateguard.py [--n 20000] [--seed 1]
"""
import argparse, json, os, random, subprocess, sys
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPEED = [0x45, 0x43, 0x41, 0x3F, 0x3D, 0x3B, 0x39, 0x37, 0x35, 0x33, 0x31, 0x2F, 0x2D, 0x2B, 0x29, 0x27,
         0x25, 0x23, 0x21, 0x1F, 0x1D, 0x1B, 0x19, 0x17, 0x15, 0x13, 0x12, 0x11, 0x10, 0x0F, 0x0E, 0x0D,
         0x0C, 0x0B, 0x0A, 0x09, 0x09, 0x08, 0x08, 0x07, 0x07, 0x06, 0x06, 0x05, 0x05, 0x05, 0x05, 0x05,
         0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04, 0x04, 0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x03,
         0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00]
BASE = [0x0F, 0x19, 0x1F]
LG_LOCK2, LG_CMT2, LG_C, LG_O = 0x61D6, 0x61D7, 0x61D8, 0x61D9
TGT_C2, TGT_O2 = 0x6152, 0x6153
X, Y, ROT, GRAV, SPU, SPD = 0x0385, 0x0386, 0x03A5, 0x0392, 0x038A, 0x038B


def capture(overlay, tag):
    snap = json.load(open(os.path.join(HERE, "couch_c960dd49_flags.json")))["flag_snapshot"]
    snap.update(overlay)
    d = os.path.join(ROOT, "tmp", "lateguard_gate"); os.makedirs(d, exist_ok=True)
    man, out = os.path.join(d, f"{tag}.manifest.json"), os.path.join(d, f"{tag}_ir.json")
    json.dump({"flag_snapshot": snap}, open(man, "w"))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "nmi126", "capture_ir.py"), man, out],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.load(open(out)), snap


def reference(m, P, M, rowcap, mut="none"):
    """returns (adopt, lock2_after)"""
    if m[LG_CMT2] == 0:
        return True, m[LG_LOCK2]
    if m[LG_LOCK2] != 0:
        return False, m[LG_LOCK2]
    C, O = m[LG_C], m[LG_O]
    if C == m[TGT_C2] and O == m[TGT_O2]:
        return True, 0
    if mut == "always":
        return False, 1
    if mut == "never":
        return True, 0
    x, rot = m[X], m[ROT]
    d = (O - rot) & 3
    presses = abs(C - x) + (0 if d == 0 else 2 if d == 2 else 1)
    need = presses * P + M
    spd = m[SPD] if m[SPD] < 3 else 1
    idx = min(80, BASE[spd] + m[SPU])
    thr = SPEED[idx]
    avail = max(0, thr - m[GRAV])
    lo = min(C, x)
    hi = max(x, min(7, C + (1 if O % 2 == 0 else 0)))
    y = min(15, m[Y])
    r = 15 - y
    empty = lambda rr, cc: m[0x0500 + rr * 8 + cc] in (0x00, 0xFF)
    if not all(empty(r, c) for c in range(lo, hi + 1)):
        return False, 1
    k = 0
    while k < min(y, rowcap) and all(empty(r + 1 + k, c) for c in range(lo, hi + 1)):
        k += 1; avail = min(255, avail + thr + 1)
    if C != x:
        avail -= thr + 1
        if avail < 0:
            return False, 1
    return (True, 0) if avail >= need else (False, 1)


def random_state(rng):
    m = {}
    tops = [rng.choice([16, 16, 15, 14, 13, 12, 11, 10, 9, 8, 6, 4, 2, 1, 0]) for _ in range(8)]
    for rr in range(16):
        for cc in range(8):
            occ = rr >= tops[cc] or (rng.random() < 0.04)
            m[0x0500 + rr * 8 + cc] = rng.choice([0x40, 0x52, 0x61, 0x70, 0x81, 0xD0, 0xD2]) if occ else rng.choice([0xFF, 0xFF, 0x00])
    m[X] = rng.randrange(8); m[ROT] = rng.randrange(4); m[Y] = rng.choice(list(range(16)) + [15, 14, 13, 12])
    m[SPD] = rng.choice([1, 1, 1, 0, 2]); m[SPU] = rng.randrange(50)
    thr = SPEED[min(80, BASE[m[SPD]] + m[SPU])]
    m[GRAV] = rng.randrange(thr + 2)
    m[LG_C] = rng.randrange(8); m[LG_O] = rng.randrange(4)
    m[TGT_C2] = rng.randrange(8) if rng.random() < 0.9 else m[LG_C]
    m[TGT_O2] = rng.randrange(4) if rng.random() < 0.9 else m[LG_O]
    m[LG_CMT2] = 1 if rng.random() < 0.9 else 0
    m[LG_LOCK2] = 0 if rng.random() < 0.9 else 1
    return m


def run_arm(overlay, tag, n, seed, mut="none"):
    ir, snap = capture(overlay, tag)
    main = ir["units"]["main"]
    if "lg_gate" not in main["labels"]:
        return None
    P, M, rowcap = int(snap["DRTAPP"]), int(snap.get("DRLATEGUARD_M", "0")), int(snap.get("DRLATEGUARD_ROWCAP", "2"))
    image = [0] * 0x10000
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); image[u["base"]:u["base"] + len(b)] = list(b)
    entry = main["base"] + main["labels"]["lg_gate"]
    rng = random.Random(seed)
    bad, adopt_n, cyc_max = [], 0, 0
    for i in range(n):
        mem = list(image)
        st = random_state(rng)
        for a, v in st.items():
            mem[a] = v
        mpu = MPU(memory=mem)
        mpu.sp = 0xFD
        ret = 0x3000 - 1                                   # JSR-style return address -> PC 0x3000 = sentinel
        mem[0x01FE], mem[0x01FF] = ret & 0xFF, ret >> 8
        mpu.sp = 0xFD
        mpu.pc = entry
        steps = 0
        while mpu.pc != 0x3000 and steps < 5000:
            mpu.step(); steps += 1
        assert mpu.pc == 0x3000, f"lg_gate did not return (state {i})"
        cyc_max = max(cyc_max, mpu.processorCycles)
        got = (bool(mpu.p & 1), mem[LG_LOCK2])
        want = reference(st, P, M, rowcap, mut="none")
        adopt_n += got[0]
        if (got[0], got[1] != 0) != (want[0], want[1] != 0):
            bad.append((i, got, want))
    return dict(n=n, bad=len(bad), adopt=adopt_n, cycles_max=cyc_max, first=bad[:3])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=20000); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    ok = True
    off = run_arm({"DRLATEGUARD": "0"}, "off", 1, a.seed)
    print(f"DRLATEGUARD=0: lg_gate emitted = {off is not None}")
    ok &= off is None
    on = run_arm({"DRLATEGUARD": "1"}, "on", a.n, a.seed)
    print(f"DRLATEGUARD=1 vs reference: {on['n']} states, mismatches {on['bad']}, adopted {on['adopt']}, "
          f"refused {on['n'] - on['adopt']}, worst measured cycles {on['cycles_max']}  {on['first']}")
    ok &= on["bad"] == 0 and 0 < on["adopt"] < on["n"]
    for mut in ("always", "never"):
        r = run_arm({"DRLATEGUARD": "1", "DRLATEGUARD_MUT": mut}, "mut_" + mut, a.n // 4, a.seed + 7)
        print(f"mutant {mut}: {r['n']} states, mismatches vs reference {r['bad']} -> {'KILLED' if r['bad'] else 'SURVIVED'}")
        ok &= r["bad"] > 0
    print("GATE_LATEGUARD", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
