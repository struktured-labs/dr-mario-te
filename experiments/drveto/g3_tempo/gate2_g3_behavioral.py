#!/usr/bin/env python3
"""GATE 2 (DRPROPH): the g3 behavioral gate, killed-mutant standard.

Substrate = the tier-1 rig's own components, with the ANALYTIC Fix-B press model
replaced by the EMITTED CART CODE:
  * the n=42 scenario bank (g3cases_*.txt, unchanged);
  * the banked RTL mailbox clocks (run_s*/out.txt, ship-hex veto2fixa runs) replayed
    into the driver's copro window at the silicon-tap frame conversion;
  * the REAL Rev-0 base ROM in nes_py (P1 seat, painted boards -- the tier-1 rig's
    convention), driven in LOCKSTEP by py65 executing the BUILT cart's driver hook
    (main @$8000) twice per frame with the live game state mirrored in.
Every $F6/$F8 the ROM sees comes from the emitted bytes -- trigger, pulse, adopt,
rotate, weave, DISTGATE, slam: the whole act path.

Two scorings per run:
  CLASSIFIER (the tier-1 projection's own deadline law, apples-to-apples):
    rescue iff the em-th MOVE toward the code's chosen direction lands by the press
    deadline W_eff-2 (E3), with move times generated from the measured DAS law
    (fresh edge f+1; held engage +16, repeat +6) over the EXTRACTED press stream.
    Window from spawn, natural gravity -- the tier-1 measurement convention (E1p/E3
    measured W with no driver; the freeze_pending GRAV pin's silicon efficacy is an
    OPEN question this gate must not silently decide -- see the report).
  CLOSED LOOP (ground truth on the real ROM): throat cells (0,3)/(0,4) free at lock.

Verdicts (death-regime band W=8-10):
  REAL      win zone reproduces the tier-1 projection (~28/42 pulse rescues beyond
            the 12/42 answer-in-time band, 2/42 unsavable) AND ZERO closed-loop
            regressions vs the DRPROPH=0 control.
  M-hold    (Amendment B violated) LOSES every 2-edge class the pulse rescues.
  M-late    (Amendment A violated) ~+0 rescues beyond the answer band.
  M-wrongdir (direction inverted) fails the eligibility cases (gateblk et al).
Each mutant must FAIL the gate for the gate to stand.
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import nespatch  # noqa: F401  (numpy-2 shim)
from nes_py import NESEnv
from py65_harness import Cpu

SIL_CLK_F = 54.669e6 / 60.0988          # 909652.11 clk/frame (BINDING domain, tier-1)
ROM = "/home/struktured/projects/dr-mario-mods/drmario.nes"
UPS = 10                                # death-regime band anchor (W=10; W=8 scored offline)
T_GO, T_ADOPT = 7.5, 0.5                # tier-1 constants for the (i) answer band

# driver PRG-RAM
ARMED2, PEND2, DELAY2, TGT_C2, TGT_O2 = 0x6161, 0x614F, 0x615F, 0x6152, 0x6153
LASTY2, PROPH_DIR, NAV_MAGIC, MATCH_ACTIVE = 0x6155, 0x61C6, 0x6149, 0x6164
W2 = 0x5200
B_LEFT, B_RIGHT = 0x02, 0x01

# game <-> nes_py pad bit translation (game: A80 B40 SEL20 ST10 U08 D04 L02 R01;
# nes_py: R80 L40 D20 U10 ST08 SEL04 B02 A01 -- verified against measure_rom5's ST/SEL)
def to_action(gbits):
    m = [(0x80, 0x01), (0x40, 0x02), (0x20, 0x04), (0x10, 0x08),
         (0x08, 0x10), (0x04, 0x20), (0x02, 0x40), (0x01, 0x80)]
    return sum(n for g, n in m if gbits & g)

def parse_runs_full():
    out = {}
    for f in glob.glob(os.path.join(HERE, "run_s*/out.txt")):
        for line in open(f):
            m = re.match(r"CASE (\S+) final=(-?\d+),(-?\d+) done=(\d+) b4zero=\d+ "
                         r"b4one=\d+ cmd4viol=\d+ pubs=(\S+) clocks=(\d+) "
                         r"doneclk=(-?\d+) timeout=(\d+)", line)
            if not m: continue
            pubs = []
            if m.group(5) != "-":
                for p in m.group(5).rstrip(";").split(";"):
                    c, o, v, ph, clk = p.split(":")
                    pubs.append((int(c), int(o), int(clk)))
            out[m.group(1)] = dict(final=(int(m.group(2)), int(m.group(3))),
                                   pubs=pubs, done_clk=int(m.group(7)))
    return out

def load_cases():
    cases = {}
    for f in sorted(glob.glob(os.path.join(HERE, "g3cases_*.txt"))):
        lines = open(f).read().split("\n")
        i = 1
        while i + 1 < len(lines) and lines[i].strip():
            name = lines[i].split()[0]
            b = [int(x, 16) for x in lines[i + 1].split()]
            fo = [min([r for r in range(16) if b[r * 8 + c] != 0xFF], default=16)
                  for c in range(8)]
            cases[name] = (b, fo)
            i += 2
    return cases

def geometry(fo):
    """verbatim mirror of analyze_margins.geometry (the tier-1 law)."""
    r = max(0, min(fo[3], fo[4]) - 1)
    periods = max(1, min(fo[3], fo[4]))
    def edges_needed(seq):
        for k, (a, b) in enumerate(seq, 1):
            if fo[a] <= r or fo[b] <= r: return None
            if fo[a] > r + 1 and fo[b] > r + 1: return k
        return None
    eL = edges_needed([(2, 3), (1, 2), (0, 1)])
    eR = edges_needed([(4, 5), (5, 6), (6, 7)])
    return dict(rest_row=r, periods=periods, edges_L=eL, edges_R=eR,
                spawn_rest=min(fo[3], fo[4]) <= 2)

# ---------------- the lockstep driver ----------------
class DriverCart:
    def __init__(self, cart_path):
        d = open(cart_path, "rb").read()
        assert d[:4] == b"NES\x1a"
        prg = d[16:16 + 4 * 16384]
        self.cpu = Cpu()
        self.cpu.load(0x8000, prg[2 * 16384:3 * 16384])
        self.cpu.load(0xC000, prg[3 * 16384:4 * 16384])
        m = self.cpu.mem
        m[NAV_MAGIC] = 0xA5; m[MATCH_ACTIVE] = 1
        m[0x0046] = 4; m[0x04] = 1; m[0x0727] = 2
        m[LASTY2] = 2
        m[W2 + 0x84] = 0; m[W2 + 0x85] = 0xFF; m[W2 + 0x86] = 0xFF
        self.hooks = 0; self.go_hook = None; self.sched = []

    def arm_schedule(self, pubs, done_clk):
        self._pubs, self._done_clk = pubs, done_clk

    def hook(self, ram):
        m = self.cpu.mem
        for a_dst, a_src in ((0x0385, 0x0305), (0x0386, 0x0306), (0x03A5, 0x0325),
                             (0x0381, 0x0301), (0x0382, 0x0302),
                             (0x039A, 0x031A), (0x039B, 0x031B),
                             (0x0324, 0x0324), (0x03A4, 0x03A4), (0x43, 0x43)):
            m[a_dst] = int(ram[a_src])
        for i in range(128):
            m[0x0500 + i] = int(ram[0x0400 + i])
        if self.go_hook is not None:
            for h, col, ori in self.sched:
                if self.hooks >= h:
                    m[W2 + 0x85] = col & 0xFF; m[W2 + 0x86] = ori & 0xFF
            if self._done_hook is not None and self.hooks >= self._done_hook:
                m[W2 + 0x84] = 1
        m[0xF6] = 0                                  # hardware pad read: no P2 controller
        armed_before = m[ARMED2]
        self.cpu.call(0x8000)
        if self.go_hook is None and armed_before == 0 and m[ARMED2] == 1:
            self.go_hook = self.hooks               # driver just GO'd: firmware invalidates
            m[W2 + 0x84] = 0; m[W2 + 0x85] = 0xFF; m[W2 + 0x86] = 0xFF
            self.sched = [(self.go_hook + int(round(2 * clk / SIL_CLK_F)), c, o)
                          for c, o, clk in self._pubs]
            self._done_hook = (self.go_hook + int(round(2 * self._done_clk / SIL_CLK_F))
                               if self._done_clk >= 0 else None)
        self.hooks += 1
        return m[0xF6], m[0xF8]

# ---------------- the nes_py side (tier-1 rig conventions, measure_rom5) ----------------
MODE, NBP = 0x46, 0x0727
P1 = dict(X=0x0305, Y=0x0306, NEXTACT=0x0317, VLEFT=0x0324, SPDUPS=0x030A, SPDSET=0x030B)
NEUTRAL = [10, 10, 10, 16, 16, 10, 10, 10]
ST, SEL = 0x08, 0x04
env = NESEnv(ROM); env.reset(); ram = env.ram
PIN = [1, 0]

def step(act=0, n=1):
    for _ in range(n):
        ram[P1["SPDSET"]], ram[P1["SPDUPS"]] = PIN
        env.step(int(act))

def nav():
    step(0, 240); step(SEL, 2); step(0, 10); assert ram[NBP] == 2
    step(ST, 2); step(0, 60); step(ST, 2); step(0, 120)
    for _ in range(600):
        if ram[MODE] == 4: return
        step(0, 1)
    raise RuntimeError("nav failed")

def paint_board(b):
    # OCCUPANCY-preserving, RUN-FREE recolor ((r+c)%3, period 3 -> no 4-run either axis).
    # The real-color parent/g2/g3 reconstructions cascade-clear during the post-lock resolve
    # (measured: [..,1,1,2,2] degraded to [..,8,2,5,3] over a 131-frame cascade), which
    # destroys the scenario before the driven spawn. Colors are NOT load-bearing here: every
    # tier-1 ROM-side law (gravity, DAS, deadline, geometry) was measured on synth-colored
    # occupancy, and the color-dependent quantity (search latency) is replayed from the
    # banked RTL clocks, not recomputed. fo profile == the case file's, exactly.
    for i in range(128):
        r, c = i // 8, i % 8
        ram[0x0400 + i] = (((r + c) % 3) | 0x40) if b[i] != 0xFF else 0xFF
    ram[P1["VLEFT"]] = 9; ram[0x03A4] = 9
    for i in range(128): ram[0x0500 + i] = 0xFF

def paint_fo(fo):
    b = [0xFF] * 128
    for c in range(8):
        for r in range(16):
            if r >= fo[c]:
                b[r * 8 + c] = ((r + c) % 3) | 0x40
    paint_board(b)

def run_case(name, board, rundat, cart_path):
    g = 0
    while ram[P1["NEXTACT"]] != 0 and g < 4000: step(0, 1); g += 1
    while ram[P1["NEXTACT"]] == 0 and g < 8000: step(0, 1); g += 1
    while ram[P1["NEXTACT"]] != 0 and g < 12000: step(0, 1); g += 1
    if g >= 12000 or ram[MODE] != 4:
        return None
    # paint AT the spawn frame, after the resolve settles: a board painted mid-resolve is
    # eaten by the resolve state machine (measured: parent fo [..,1,1,2,2] -> [..,8,2,5,3]
    # over 131 frames even run-free). Case boards keep spawn cells (0,3)/(0,4) free, so the
    # just-spawned capsule never overlaps the paint. Frame 0 = the spawn frame, painted
    # before the first driver hook mirrors it.
    paint_board(board)
    drv = DriverCart(cart_path)
    drv.arm_schedule(rundat["pubs"], rundat["done_clk"])
    frames = []
    held_shadow = 0
    for f in range(260):
        drv.cpu.mem[0xF8] = held_shadow
        f6a, _ = drv.hook(ram)
        f6b, _ = drv.hook(ram)
        accepted = f6a & f6b
        final_f8 = drv.cpu.mem[0xF8]
        pressed = accepted & (final_f8 ^ 0xFF)
        forced = final_f8 != held_shadow
        # Forced-edge fidelity WITHOUT poking the ROM's input state (a $F7=0 poke measurably
        # SUPPRESSES the previous NMI's edge byte before the main loop consumes it -- lateral
        # motion froze entirely): when the driver forces held=0 while repeating a button the
        # ROM would eat as held, insert a one-frame release so the next frame is a fresh
        # edge. Pulse frames never repeat consecutively (off-frame between) so the pulse is
        # untouched; only multi-rotation presses pay ~1 extra frame (conservative).
        eaten = (accepted & held_shadow) if forced else 0
        fed = accepted & ~eaten & 0xFF
        held_shadow = fed
        y, x = int(ram[P1["Y"]]), int(ram[P1["X"]])
        frames.append(dict(f=f, acc=accepted, prs=pressed, y=y, x=x,
                           pd=drv.cpu.mem[PROPH_DIR], tc=drv.cpu.mem[TGT_C2]))
        step(fed and to_action(fed) or 0, 1)
        if ram[P1["NEXTACT"]] != 0:
            break
    tf = ram[0x0403] == 0xFF and ram[0x0404] == 0xFF
    fy = frames[-2]["y"] if len(frames) > 1 else None
    locked = ram[P1["NEXTACT"]] != 0
    paint_fo(NEUTRAL)
    return dict(name=name, frames=frames, throat_free=bool(tf), final_y=fy,
                locked=bool(locked), go_hook=drv.go_hook,
                dir=frames[0]["pd"] & 0x03 if frames else 0)

# ---------------- classifier over the extracted stream ----------------
def move_times(frames, dirbit, limit_f=None):
    """measured DAS law over the extracted press stream: fresh edge -> move f+1,
    engage 16, repeat 6. Returns move times toward dirbit."""
    moves, das = [], None
    for fr in frames:
        f = fr["f"]
        if limit_f is not None and f > limit_f: break
        if fr["prs"] & dirbit:
            moves.append(f + 1); das = 16
        elif fr["acc"] & dirbit and das is not None:
            das -= 1
            if das <= 0:
                moves.append(f + 1); das = 6
        else:
            das = None
    return moves

def classify(res, fo, pub_f, W):
    geo = geometry(fo)
    W_eff = geo["periods"] * W - (geo["periods"] - 1)
    deadline = W_eff - 2
    tier1 = (T_GO + pub_f + T_ADOPT) <= deadline            # tier-1's own (i) band
    d = res["dir"]
    em = geo["edges_L"] if d == B_LEFT else geo["edges_R"] if d == B_RIGHT else None
    # pulse-phase presses only: before the first-valid-pub hook (retarget takes over there)
    pub_frame = ((res["go_hook"] or 0) + 2 * pub_f) / 2.0 if res["go_hook"] is not None else None
    mv = move_times(res["frames"], d, limit_f=None) if d else []
    rescued = em is not None and len(mv) >= em and mv[em - 1] + 0.5 <= deadline
    return tier1, rescued, em, mv[:4]

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--builds", default="proph0,real,hold,late,wrongdir")
    ap.add_argument("--out", default=os.path.join(HERE, "gate2_results.json"))
    args = ap.parse_args()
    BUILDS = {"proph0": "proph0.nes", "real": "proph1.nes", "hold": "proph1_hold.nes",
              "late": "proph1_late.nes", "wrongdir": "proph1_wrongdir.nes"}
    runs = parse_runs_full()
    cases = load_cases()
    PIN[:] = [1, UPS]
    nav()
    results = {}
    for b in args.builds.split(","):
        cart = os.path.join(ROOT, "tmp", "proph", BUILDS[b])
        rows = {}
        for name in sorted(cases):
            if name not in runs or not runs[name]["pubs"]:
                continue
            board, fo = cases[name]
            r = run_case(name, board, runs[name], cart)
            if r is None:
                print(f"  !! {b}/{name}: rig wedged, renav"); nav(); continue
            first = runs[name]["pubs"][0][2] / SIL_CLK_F
            t1_10, resc_10, em, mv = classify(r, fo, first, 10)
            t1_8, resc_8, _, _ = classify(r, fo, first, 8)
            rows[name] = dict(dir=r["dir"], em=em, moves=mv,
                              tier1_W10=t1_10, rescued_W10=resc_10,
                              tier1_W8=t1_8, rescued_W8=resc_8,
                              survived=r["throat_free"], final_y=r["final_y"],
                              locked=r["locked"])
            del r["frames"]
        results[b] = rows
        n = len(rows)
        for W in ("W10", "W8"):
            t1 = sum(v[f"tier1_{W}"] for v in rows.values())
            plus = sum(v[f"rescued_{W}"] and not v[f"tier1_{W}"] for v in rows.values())
            print(f"{b:9s} {W}: n={n} (i)answer={t1} (ii)pulse+={plus} "
                  f"(iii)left={n - t1 - plus}   closed-loop survived={sum(v['survived'] for v in rows.values())}")
    json.dump(results, open(args.out, "w"), indent=1, default=lambda o: bool(o))
    print("wrote", args.out)

if __name__ == "__main__":
    main()

# ---------------- verdict over saved results ----------------
def verdict(pr_path, mut_path):
    pr = json.load(open(pr_path)); mut = json.load(open(mut_path))
    real, p0 = pr["real"], pr["proph0"]
    hold, late, wrong = mut["hold"], mut["late"], mut["wrongdir"]
    fails = []
    def frac(rows, W):
        t1 = sum(v[f"tier1_{W}"] for v in rows.values())
        plus = sum(v[f"rescued_{W}"] and not v[f"tier1_{W}"] for v in rows.values())
        return t1, plus, len(rows) - t1 - plus
    print("== GATE 2 VERDICT (death-regime band W=8-10; n=42) ==")
    for W in ("W10", "W8"):
        t1, plus, left = frac(real, W)
        ok = (t1, plus, left) == (12, 28, 2)
        print(f" REAL classifier {W}: (i){t1} (ii)+{plus} (iii){left} "
              f"[tier-1 projection: 12/+28/2] {'OK' if ok else 'FAIL'}")
        if not ok: fails.append(f"real classifier {W}")
    regr = [n for n in p0 if p0[n]["survived"] and not real[n]["survived"]]
    resc = [n for n in p0 if not p0[n]["survived"] and real[n]["survived"]]
    print(f" REAL closed loop: survived {sum(v['survived'] for v in real.values())}/42 "
          f"(control {sum(v['survived'] for v in p0.values())}/42), rescues +{len(resc)}, "
          f"regressions {len(regr)} {'OK' if not regr else 'FAIL ' + str(regr)}")
    if regr: fails.append("closed-loop regressions")
    # mutants must FAIL the real bar
    em2p = [n for n, v in real.items()
            if v["em"] == 2 and v["rescued_W10"] and not v["tier1_W10"]]
    hlost = [n for n in em2p if not hold[n]["rescued_W10"]]
    _, hplus, _ = frac(hold, "W10")
    ok = len(hlost) == len(em2p) and hplus < 28
    print(f" M-hold: loses {len(hlost)}/{len(em2p)} pulse-win-zone 2-edge cases, (ii)+{hplus} "
          f"{'KILLED' if ok else 'NOT KILLED'}")
    if not ok: fails.append("M-hold not killed")
    _, lplus, _ = frac(late, "W10")
    print(f" M-late: (ii)+{lplus} {'KILLED (as-specced timing = +0)' if lplus == 0 else 'NOT KILLED'}")
    if lplus != 0: fails.append("M-late not killed")
    elig = [n for n in real if n.startswith(("synth_L4f1_gateblk", "g2", "g3"))]
    wfail = [n for n in elig if not wrong[n]["rescued_W10"]]
    _, wplus, _ = frac(wrong, "W10")
    ok = len(wfail) == len(elig) and wplus < 28
    print(f" M-wrongdir: fails {len(wfail)}/{len(elig)} eligibility cases, (ii)+{wplus} "
          f"{'KILLED' if ok else 'NOT KILLED'}")
    if not ok: fails.append("M-wrongdir not killed")
    print("\nGATE2:", "PASS" if not fails else "FAIL " + str(fails))
    return not fails
