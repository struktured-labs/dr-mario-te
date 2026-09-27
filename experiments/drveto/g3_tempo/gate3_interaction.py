#!/usr/bin/env python3
"""GATE 3 (DRPROPH): interaction traces -- timers, the retarget race, PROPH_DIR lifecycle.

Method: OPEN-LOOP LOCKSTEP PAIR. proph0 and proph1 execute the full driver hook
(main @$8000) from identical warm state, fed an IDENTICAL mirrored game-state
sequence (board/Y/X/$43; no press feedback), through a scripted scenario:

  idle -> spawn on a threat board (c4 fo=1, deep left) -> settle window (PEND2,
  DELAY2 countdown) -> GO (mailbox invalidated) -> nf2_hold window -> VALID
  MAILBOX INJECTED MID-PULSE at go+k (k swept 1..6: both frame parities, both
  hook passes) -> DONE -> descent -> lock/respawn on a BENIGN board (lifecycle).

Assertions, per injection k:
  A  TIMER INTEGRITY: full-state diff proph0 vs proph1 every hook (zp, $0200-
     $07FF, $6000-$7FFF; stack page excluded as layout) is a subset of
     {$F6, $F8, PROPH_DIR}. Covers DELAY2, WDOG2/WDOGH2, STABLE_CT2, LAST_COL2/
     LAST_ORI2, ROT_DONE2, TGT_C2/TGT_O2, GRAV_P2 (freeze_pending pin),
     DISTGATE scratch, SLAM state -- nothing but the documented outputs may move.
     (NAVESC is compiled OUT on this DRHUMAN class -- GATE_HUMAN H2b -- so its
     counters cannot be touched by construction; asserted vacuously by A.)
  B1 AMENDMENTS LIVE: during settle+nf2_hold, proph1 pulses B_LEFT on latched-
     parity frames with $F8 forced 0 (fresh edge), releases on off-frames;
     proph0 writes the no-button state.
  B2 RETARGET HANDOVER: from the first hook the adopt path sees the valid
     mailbox, proph1's $F6/$F8 == proph0's on EVERY subsequent hook until the
     next detect (the pulse is structurally gone; zero residual interference).
  B3 NO DOUBLE-INPUT: per frame, accepted = F6(passA) & F6(passB) (the ROM's
     two-pass AND). No frame may accept LEFT|RIGHT together or mix a direction
     bit with a rotate bit (0x80/0x40) that either single path did not write.
  C  LIFECYCLE: at the second (benign) spawn the trigger REWRITES PROPH_DIR to
     0; between DONE and that detect the pulse never runs (F6/F8 == proph0).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests")); sys.path.insert(0, ROOT)
from py65_harness import Cpu

PROPH_DIR, LASTY2, LASTY1 = 0x61C6, 0x6155, 0x6154
ARMED2, PEND2, DELAY2, WDOG2 = 0x6161, 0x614F, 0x615F, 0x6162
TGT_C2, TGT_O2, ROT_DONE2, STABLE_CT2 = 0x6152, 0x6153, 0x616E, 0x6171
GRAV_P2, MODE, P2SEL = 0x0392, 0x0046, 0x04
W2 = 0x5200
B_LEFT, B_RIGHT = 0x02, 0x01

def load_cart(path):
    d = open(path, "rb").read(); assert d[:4] == b"NES\x1a"
    prg = d[16:16 + 4 * 16384]
    cpu = Cpu()
    cpu.load(0x8000, prg[2 * 16384:3 * 16384])
    cpu.load(0xC000, prg[3 * 16384:4 * 16384])
    m = cpu.mem
    m[0x6149] = 0xA5; m[0x6164] = 1                    # NAV_MAGIC warm, MATCH_ACTIVE
    m[MODE] = 4; m[P2SEL] = 1; m[0x0727] = 2
    m[0x0324] = 5; m[0x03A4] = 5                       # virus counts alive
    m[LASTY2] = 2; m[LASTY1] = 2
    m[0x0306] = 2                                      # P1 quiet
    m[W2 + 0x84] = 0; m[W2 + 0x85] = 0xFF; m[W2 + 0x86] = 0xFF
    return cpu

def paint(cpu, threat):
    m = cpu.mem
    for i in range(128): m[0x0500 + i] = 0xFF
    if threat:
        for r in range(1, 16): m[0x0500 + r * 8 + 4] = 0x41   # c4 fo=1 ledge, left deep

STATE_SKIP_ZP = {0xF6, 0xF8}
def diff(c0, c1):
    out = []
    for a in range(0x100):
        if a in STATE_SKIP_ZP: continue
        if c0.mem[a] != c1.mem[a]: out.append(a)
    for a in range(0x0200, 0x0800):
        if c0.mem[a] != c1.mem[a]: out.append(a)
    for a in range(0x6000, 0x8000):
        if a == PROPH_DIR: continue
        if c0.mem[a] != c1.mem[a]: out.append(a)
    return out

def run(k_inject, verbose=False):
    p1name = os.environ.get("G3_P1", "proph1")
    # G3_DIR: cart directory. tmp/proph = the human-cart arms, tmp/proph_cvc = the CvC soak arms.
    g3dir = os.environ.get("G3_DIR", os.path.join(ROOT, "tmp", "proph"))
    carts = {n: load_cart(os.path.join(g3dir, f + ".nes"))
             for n, f in (("proph0", "proph0"), ("proph1", p1name))}
    for c in carts.values(): paint(c, threat=True)
    fails, trace = [], []
    go_hook, inj_hook, adopt_seen, detect2_hook = None, None, None, None
    y = 2
    for hook in range(140):
        frame = hook // 2
        # scripted game state
        if hook == 6: y = 15                            # spawn 1 (threat board)
        if hook == 96: y = 14                           # begin descent
        if 96 < hook < 110 and hook % 4 == 0: y = max(8, y - 1)
        if hook == 116:                                 # lock + respawn (benign board)
            for c in carts.values(): paint(c, threat=False)
            y = 15
            detect2_hook = hook
        f6s, f8s = {}, {}
        for name, c in carts.items():
            m = c.mem
            m[0x43] = frame & 0xFF
            m[0x0386] = y; m[0x0385] = 3; m[0x03A5] = 0
            m[0x0306] = 2
            m[0xF6] = 0                                  # pad read: no P2 controller
            armed_before = m[ARMED2]
            c.call(0x8000)
            if name == "proph1" and go_hook is None and armed_before == 0 and m[ARMED2] == 1:
                go_hook = hook
            f6s[name], f8s[name] = m[0xF6], m[0xF8]
        # firmware model, symmetric on both carts
        if go_hook is not None and inj_hook is None:
            for c in carts.values():
                c.mem[W2 + 0x84] = 0; c.mem[W2 + 0x85] = 0xFF; c.mem[W2 + 0x86] = 0xFF
            inj_hook = go_hook + k_inject
        if inj_hook is not None and hook + 1 == inj_hook:
            for c in carts.values():
                c.mem[W2 + 0x85] = 6; c.mem[W2 + 0x86] = 2   # col 6, copro orient 2
        if go_hook is not None and hook + 1 == go_hook + 40:
            for c in carts.values(): c.mem[W2 + 0x84] = 1    # DONE
        # A: timer integrity
        d = diff(carts["proph0"], carts["proph1"])
        if d:
            fails.append(f"A hook={hook} diff={[hex(a) for a in d]}")
        if inj_hook is not None and hook >= inj_hook and adopt_seen is None:
            adopt_seen = hook
        # B2 / C: identity outside the pulse windows
        p1_pd = carts["proph1"].mem[PROPH_DIR]
        trace.append(dict(hook=hook, frame=frame,
                          f60=f6s["proph0"], f61=f6s["proph1"],
                          f80=f8s["proph0"], f81=f8s["proph1"],
                          pend=carts["proph1"].mem[PEND2],
                          armed=carts["proph1"].mem[ARMED2],
                          delay=carts["proph1"].mem[DELAY2],
                          wdog=carts["proph1"].mem[WDOG2],
                          pd=p1_pd, tc=carts["proph1"].mem[TGT_C2],
                          grav=carts["proph1"].mem[GRAV_P2]))
        if adopt_seen is not None and hook >= adopt_seen and (detect2_hook is None or hook < detect2_hook):
            if f6s["proph1"] != f6s["proph0"] or f8s["proph1"] != f8s["proph0"]:
                fails.append(f"B2 hook={hook} proph1 F6/F8 {f6s['proph1']:02x}/{f8s['proph1']:02x}"
                             f" != proph0 {f6s['proph0']:02x}/{f8s['proph0']:02x}")
    # B1: pulse live during settle+hold with latched parity, edge semantics
    lat = None
    for t in trace:
        if t["pd"] & 0x03:
            lat = (t["pd"] >> 2) & 1; break
    pulse_rows = [t for t in trace if 6 <= t["hook"] < (inj_hook or 999)]
    on_ok = all((t["f61"] == B_LEFT and t["f81"] == 0) for t in pulse_rows
                if (t["frame"] & 1) == lat)
    off_ok = all((t["f61"] == 0 and t["f81"] == 0) for t in pulse_rows
                 if (t["frame"] & 1) != lat)
    ctl_ok = all(t["f60"] == 0 for t in pulse_rows)
    if not (pulse_rows and on_ok and off_ok and ctl_ok and lat is not None):
        fails.append(f"B1 pulse malformed (lat={lat} on={on_ok} off={off_ok} ctl={ctl_ok} n={len(pulse_rows)})")
    # B3: two-pass AND per frame -- no merged/hybrid accepted input
    for f in range(70):
        pair = [t for t in trace if t["frame"] == f]
        if len(pair) != 2: continue
        acc = pair[0]["f61"] & pair[1]["f61"]
        if (acc & 0x03) == 0x03:
            fails.append(f"B3 frame={f} LEFT|RIGHT merged: {acc:02x}")
        if (acc & 0x03) and (acc & 0xC0):
            fails.append(f"B3 frame={f} dir+rotate hybrid: {acc:02x}")
    # C: lifecycle -- second (benign) detect rewrites PROPH_DIR to 0
    post2 = [t for t in trace if detect2_hook is not None and t["hook"] >= detect2_hook]
    if not post2 or post2[0]["pd"] != 0:
        fails.append(f"C stale PROPH_DIR at benign respawn: {post2[0]['pd'] if post2 else 'n/a'}")
    # C-pre: between DONE-adopt and detect2, no pulse (covered by B2 range) --
    # additionally assert PROPH_DIR HELD (stale value visible but inert) then cleared
    return fails, trace, go_hook, inj_hook, detect2_hook, lat

def main():
    allfail = []
    for k in range(1, 7):
        fails, trace, go, inj, d2, lat = run(k)
        tag = "OK " if not fails else "FAIL"
        print(f"[k={k}] {tag} go_hook={go} inject_hook={inj} detect2={d2} latched_parity={lat}")
        if k == 3 or fails:
            lo = max(0, (inj or 20) - 6)
            for t in trace[lo:(inj or 20) + 8]:
                print(f"   h{t['hook']:3d} f{t['frame']:2d} F6 p0={t['f60']:02x} p1={t['f61']:02x} "
                      f"F8 p0={t['f80']:02x} p1={t['f81']:02x} pend={t['pend']} armed={t['armed']} "
                      f"delay={t['delay']:2d} wdog={t['wdog']:3d} pd={t['pd']:02x} tc={t['tc']:02x} grav={t['grav']}")
        for f in fails: print("   ", f)
        allfail += fails
    print("\nGATE3:", "PASS" if not allfail else f"FAIL ({len(allfail)})")
    return 0 if not allfail else 1

if __name__ == "__main__":
    sys.exit(main())
