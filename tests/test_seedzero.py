#!/usr/bin/env python3
"""DRSEEDZERO defect gate (silicon-fidelity lane, 2026-10-06): does the couch cart upload tie-break SEED nibbles?

DEFECT. The couch cart derives a per-match tie-break seed (SEED2 = (NAV_T | 1) ^ $A4, always odd) on the first play
frame of every match and rides it on the colour uploads' HIGH nibbles (cA <- seed lo << 4, cB <- seed hi). The copro
firmware then jitters every root by +0..3 before its strict argmax AND (a firmware leak) hands the raw S_CA/S_CB bytes,
nibbles included, to the tuck extension. Every replay instrument (co-sim pubtrace, Mesen chained replay, python
faithful brain) runs seed 0, so silicon is a different decider from all of them: the 10/05 "silicon-only" misses.
DRSEED=0 is NOT a fix: it only skips the derivation, and SEED1/SEED2 are zeroed solely by the PRG-RAM power-on init
(NAV_MAGIC != $A5). MiSTer PRG-RAM survives load_core, so a DRSEED=0 cart keeps uploading whatever seed the PREVIOUS
seeded cart (or session) left in $6168.

THE CHECK. The real emitted driver runs closed-loop under py65 in test_gravity_fidelity's ROM-rule P2 world, starting
on the FIRST play frame of a match (MATCH_ACTIVE = 0) with STICKY PRG-RAM: NAV_MAGIC = $A5 (power-on init skipped),
NAV_T = a nonzero counter, and SEED1/SEED2 = a stale nonzero seed (0xB7 / 0x13, both nibbles nonzero). Every GO's
upload is captured ($5280 cA / $5281 cB); a GO is SEEDED iff the high nibble of cA or cB is nonzero. (cB's low-nibble
colour and nA/nB's DRREACHTX/TAPP nibbles are not seed and are not looked at.)
Arms (two-sided):
  MUST SHOW THE DEFECT : the shipped FAIR / FAIRPLUS / FAIR2PLUS flag sets (DRSEED default 1): seeded GOs > 0
                         (the derived seed), and FAIR + DRSEED=0: seeded GOs > 0 (the STALE seed survives).
  MUST PASS            : the same + DRSEEDZERO=1: seeded GOs == 0 with GOs > 0 (also with DRSEED=0 + DRSEEDZERO=1).
  test_seedzero.py [--frames N] [--seeds 5,11] [--arm NAME]
"""
import argparse, collections, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_gravity_fidelity as G  # noqa: E402

NAV_T, SEED1, SEED2 = 0x6147, 0x6167, 0x6168
COUCH = "experiments/lateflip/couch_c960dd49_flags.json"
D = {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1"}
A = dict(D, DRABORTSTALE="1")
P = {"DRLGPRESTART": "1", "DRDISTROW": "2"}
ARMS = {   # name: (flags json, overlays, expect)  expect = "defect" | "pass"
    "fair_D":              (COUCH, D, "defect"),
    "fairplus_DP":         (COUCH, dict(D, **P), "defect"),
    "fair2plus_AP":        (COUCH, dict(A, **P), "defect"),
    "fair_D_seed0":        (COUCH, dict(D, DRSEED="0"), "defect"),
    "fair_D_sz":           (COUCH, dict(D, DRSEEDZERO="1"), "pass"),
    "fairplus_DP_sz":      (COUCH, dict(D, DRSEEDZERO="1", **P), "pass"),
    "fair2plus_AP_sz":     (COUCH, dict(A, DRSEEDZERO="1", **P), "pass"),
    "fair_D_seed0_sz":     (COUCH, dict(D, DRSEED="0", DRSEEDZERO="1"), "pass"),
}


def run(name, frames, seed):
    flags, overlays, expect = ARMS[name]
    ir, snap = G.capture(flags, overlays, name)
    base = G.fresh_mem(seed)
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    # STICKY PRG-RAM at the first play frame of a NEW match (fresh_mem already sets NAV_MAGIC = $A5)
    base[G.MATCH] = 0
    base[NAV_T] = 0x5C
    base[SEED1], base[SEED2] = 0xB7, 0x13
    mem = G.ObservableMemory(subject=base)
    copro = G.Copro(random.Random(seed * 7919 + 1))
    upbuf = [0] * 132
    act = collections.Counter(); ex = []

    def on_up(addr, value):
        upbuf[addr - 0x5200] = value

    def on_go(addr, value):
        ca, cb = upbuf[0x80], upbuf[0x81]
        act["goes"] += 1
        if (ca >> 4) or (cb >> 4):
            act["seeded_goes"] += 1
            if len(ex) < 2:
                ex.append(dict(cA=f"{ca:02X}", cB=f"{cb:02X}", seed2=f"{base[SEED2]:02X}"))
        return copro.on_go(addr, value)
    mem.subscribe_to_write(range(0x5200, 0x5284), on_up)
    mem.subscribe_to_write([0x5284], on_go)
    mem.subscribe_to_read(range(0x5284, 0x5289), copro.read)
    mpu = G.MPU(memory=mem)
    entry = ir["units"]["main"]["base"] + ir["units"]["main"]["labels"]["main"]
    world = G.World(random.Random(seed), base)

    def hook():
        mpu.sp = 0xFD
        r = 0x3000 - 1
        base[0x1FE] = r & 0xFF; base[0x1FF] = (r >> 8) & 0xFF; mpu.pc = entry; base[0x3000] = 0xEA
        k = 0
        while mpu.pc != 0x3000:
            mpu.step(); k += 1
            if k > 400000:
                raise RuntimeError(f"hook runaway pc=${mpu.pc:04X}")

    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        outs = []
        for _ in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0
            hook()
            outs.append(base[0xF6])
        R = outs[0] & outs[1]
        held_used = base[0xF8]
        pressed = R & (R ^ held_used)
        base[0xF6] = pressed; base[0xF8] = R
        world.step(f, pressed, R)
    act["match_active_set"] = int(base[G.MATCH] != 0)
    act["pills"] = world.pills
    return expect, act, ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=3000)
    ap.add_argument("--seeds", default="5,11", help="the verdict is on counts SUMMED over these world seeds")
    ap.add_argument("--arm", action="append")
    a = ap.parse_args()
    ok = True
    for name in a.arm or list(ARMS):
        tot = collections.Counter(); exs = []; expect = ARMS[name][2]
        for sd in (int(x) for x in a.seeds.split(",")):
            expect, act, ex = run(name, a.frames, sd)
            tot.update(act); exs += ex
        if not tot["goes"] or tot["match_active_set"] == 0:
            good, verdict = False, "FAIL (vacuous: no GO, or play never dispatched)"
        elif expect == "defect":
            good = tot["seeded_goes"] > 0
            verdict = (f"DEFECT REPRODUCED ({tot['seeded_goes']}/{tot['goes']} GOs upload a seed)" if good
                       else "SURVIVED -- the gate cannot see the defect")
        else:
            good = tot["seeded_goes"] == 0
            verdict = "PASS" if good else f"FAIL ({tot['seeded_goes']}/{tot['goes']} GOs upload a seed)"
        ok &= good
        print(f"{name:18s} expect={expect:6s} {verdict:44s} seeds {a.seeds} x {a.frames} f: GOs {tot['goes']} seeded "
              f"{tot['seeded_goes']} pills {tot['pills']}" + (f" | e.g. {exs[0]}" if exs else ""))
    print("SEEDZERO GATE: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
