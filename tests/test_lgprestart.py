#!/usr/bin/env python3
"""DRLGPRESTART defect gate (execution-fidelity lane, 2026-10-04): does a garbage-window PRESTART answer reach the
capsule it was searched for?

DEFECT (silicon 10/04, both fair builds; reproduced in Mesen): DRLATEGUARD's per-pill latches LG_CMT2 / LG_LOCK2 are
reset only at the next spawn edge, but a DRPRESTART search runs for the NEXT capsule during the garbage window, while
those latches still describe the capsule that just LOCKED. lg_gate prices the prestart's publishes against the locked
capsule (its own cells now sit in the "current row"), FREEZES, and drops the prestart's DONE answer; the spawn edge is
prestart-owned (no new search), so the new capsule executes the PREVIOUS pill's target.

THE CHECK. The real emitted driver runs closed-loop under py65 in test_gravity_fidelity's ROM-rule P2 world (garbage
releases -> DRPRESTART pipelines run; the anytime copro model publishes, flips and DONEs). On every hook that consumes a
DONE (the copro's $5284 read returns 1 for the first time after a GO), the hook must leave TGT_C2 = the DONE column,
unless DRLATEGUARD legitimately refuses it for the FALLING capsule. Counted separately:
  prestart DONEs (PRE_ACT2 != 0 at the DONE hook) and how many were DROPPED (TGT_C2 != the answer after the hook);
  falling-capsule DONEs refused by DRLATEGUARD (LG_LOCK2 = 1, PRE_ACT2 = 0) -- the gate's intended job, must survive.
Arms (two-sided):
  MUST SHOW THE DEFECT : the shipped fair flag sets D (dbbb5007) and A = D + DRABORTSTALE (b1b57638): dropped > 0.
  MUST PASS            : D / A + DRLGPRESTART=1 (+ DRDISTROW=1): dropped == 0, prestart DONEs > 0, LATEGUARD still
                         refuses some falling-capsule DONEs (> 0), and the gravity-fidelity check (run B) still passes.
  test_lgprestart.py [--frames N] [--seeds 5,11,23,77] [--arm NAME] [--grav]   (verdict on counts summed over seeds)
"""
import argparse, collections, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_gravity_fidelity as G  # noqa: E402

TGT_C2, PRE_ACT2, LG_LOCK2, LG_CMT2 = 0x6152, 0x619A, 0x61D6, 0x61D7
COUCH = "experiments/lateflip/couch_c960dd49_flags.json"
D = {"DRLATEGUARD": "1", "DRSTUDYEND": "1", "DRSETTLE": "3", "DRSETTLEPIN": "0", "DRPROPHFIRST": "1"}
A = dict(D, DRABORTSTALE="1")
ARMS = {   # name: (flags json, overlays, expect)  expect = "defect" | "pass"
    "couch_fair_D":            (COUCH, D, "defect"),
    "couch_fair_A":            (COUCH, A, "defect"),
    "couch_fair_D_lgp":        (COUCH, dict(D, DRLGPRESTART="1"), "pass"),
    "couch_fair_A_lgp":        (COUCH, dict(A, DRLGPRESTART="1"), "pass"),
    "couch_fair_A_lgp_row":    (COUCH, dict(A, DRLGPRESTART="1", DRDISTROW="1"), "pass"),
    "couch_fair_D_lgp_row":    (COUCH, dict(D, DRLGPRESTART="1", DRDISTROW="1"), "pass"),
}


def run(name, frames, seed, grav=False):
    flags, overlays, expect = ARMS[name]
    G.ARMS[name] = (flags, overlays, "pass")               # reuse the gravity-fidelity run B on the same flag set
    ir, snap = G.capture(flags, overlays, name)
    base = G.fresh_mem(seed)
    for u in ir["units"].values():
        b = bytes.fromhex(u["bytes"]); base[u["base"]:u["base"] + len(b)] = list(b)
    mem = G.ObservableMemory(subject=base)
    copro = G.Copro(random.Random(seed * 7919 + 1))
    seen = {"pending": False, "consumed": False}

    def on_go(addr, value):
        seen["pending"] = False
        return copro.on_go(addr, value)

    def on_read(addr):
        v = copro.read(addr)
        if addr == 0x5284 and v == 1 and seen["pending"]:
            seen["pending"] = False; seen["consumed"] = True
        return v
    mem.subscribe_to_write([0x5284], on_go)
    mem.subscribe_to_read(range(0x5284, 0x5289), on_read)
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

    act = collections.Counter(); examples = []
    was_done = 1
    for f in range(frames):
        base[0x43] = f & 0xFF
        copro.tick(f)
        if copro.done == 1 and was_done == 0:
            seen["pending"] = True                          # the copro DONE'd this frame: the next $5284=1 read consumes it
        was_done = copro.done
        outs = []
        for _ in (1, 2):
            base[0xF6] = 0; base[0xF5] = 0
            pre = base[PRE_ACT2]; lock_before = base[LG_LOCK2]
            seen["consumed"] = False
            hook()
            outs.append(base[0xF6])
            if seen["consumed"] and copro.col < 8:
                adopted = base[TGT_C2] == copro.col
                if pre:
                    act["prestart_dones"] += 1
                    if not adopted:
                        act["prestart_dropped"] += 1
                        if len(examples) < 3:
                            examples.append(dict(frame=f, answer_col=copro.col, tgt_c2=base[TGT_C2], lg_lock=base[LG_LOCK2],
                                                 lg_cmt=base[LG_CMT2], y=base[G.Y2], na=base[G.NA]))
                else:
                    act["falling_dones"] += 1
                    if not adopted and base[LG_LOCK2]:
                        act["falling_refused_by_lateguard"] += 1
        R = outs[0] & outs[1]
        held_used = base[0xF8]
        pressed = R & (R ^ held_used)
        base[0xF6] = pressed; base[0xF8] = R
        world.step(f, pressed, R)
    act["garbage"] = world.cnt.get("garbage", 0); act["pills"] = world.pills
    return expect, act, examples, (G.run_arm(name, frames, seed) if grav else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=6000)
    ap.add_argument("--seeds", default="5,11,23,77", help="the verdict is on counts SUMMED over these world seeds")
    ap.add_argument("--arm", action="append")
    ap.add_argument("--grav", action="store_true", help="also run the gravity-fidelity check per seed (tests/"
                    "test_gravity_fidelity.py carries these arms too; run_cart_gates.sh runs them)")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    ok = True
    for name in a.arm or list(ARMS):
        tot = collections.Counter(); ex = []; grav_ok = True; expect = ARMS[name][2]
        for sd in seeds:
            expect, act, e, grav = run(name, a.frames, sd, a.grav)
            tot.update(act); ex += e
            if grav is not None:
                grav_ok &= (not grav["diverged"] and grav["upload_mismatches"] == 0)
        if expect == "defect":
            good = tot["prestart_dropped"] > 0
            verdict = (f"DEFECT REPRODUCED ({tot['prestart_dropped']}/{tot['prestart_dones']} prestart answers dropped)"
                       if good else "SURVIVED -- the gate cannot see the defect")
        else:
            good = (tot["prestart_dropped"] == 0 and tot["prestart_dones"] > 0 and tot["falling_refused_by_lateguard"] > 0
                    and grav_ok)
            verdict = ("PASS" if good else
                       f"FAIL ({tot['prestart_dropped']} prestart answers dropped)" if tot["prestart_dropped"] else
                       "FAIL (no prestart DONE exercised)" if not tot["prestart_dones"] else
                       "FAIL (LATEGUARD never refused a falling capsule: gate unexercised or disabled)"
                       if not tot["falling_refused_by_lateguard"] else "FAIL (gravity fidelity)")
        ok &= good
        print(f"{name:22s} expect={expect:6s} {verdict:58s} seeds {a.seeds} x {a.frames} f: prestart DONEs "
              f"{tot['prestart_dones']} dropped {tot['prestart_dropped']} | falling DONEs {tot['falling_dones']} refused by "
              f"LATEGUARD {tot['falling_refused_by_lateguard']} | garbage {tot['garbage']} pills {tot['pills']}"
              + ("" if not a.grav else f" | gravity-fidelity {'PASS' if grav_ok else 'FAIL'}") + (f" | e.g. {ex[0]}" if ex else ""))
    print("LGPRESTART GATE: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
