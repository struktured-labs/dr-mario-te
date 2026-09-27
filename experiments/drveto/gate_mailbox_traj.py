#!/usr/bin/env python3
"""G2: MAILBOX-TRAJECTORY GATE for DRVETO Fix A (anytime publish suppression).

Every prior gate scored the FINAL answer; the driver acts on the ANYTIME STREAM
(S_BEST_C/O at $6134/$6135, live-published per s_loop iteration, orient=$FF =
no-result sentinel), and the two diverge pre-DONE: without Fix A, iteration 1
always beats the $8000 sentinel, so a vetoed pass-0 argmax IS handed to the
pre-DONE driver (DRSLAM / MIN_THINK act on it).  This gate records the FULL
S_BEST_C/O write trajectory of the real 6502 firmware under py65 and asserts,
per search:

  T1 NO-VETOED-VISIBLE   no store of a vetoed candidate to the mailbox while the
                         shortlist contains >=1 unvetoed candidate (the strict
                         form: a vetoed candidate may be mailbox-visible ONLY on
                         all-vetoed boards, and then only via the o_done/stub
                         store of the final answer -- never mid-search).
  T2 LIVENESS            if an unvetoed candidate exists, the mailbox ends the
                         s_loop VALID (the driver is never starved of an answer
                         the search had).  Corpus-scoped: a vetoed candidate
                         out-margining the 20000 penalty could starve it in
                         principle; no corpus board is within 4 orders of that.
  T3 ALL-VETOED FALLBACK if EVERY shortlist candidate is vetoed, the mailbox
                         stays $FF-invalid for the whole s_loop AND the internal
                         final (D_BC/D_BO) is still a real decision (note A) --
                         the stub publishes it at o_done/DONE.
  T4 FINAL CONSERVATION  the final answer equals the mirror's (Fix A must never
                         change an argmax, only the interim stream).
  T5 SILENT-VETO CONTROL on standard-corpus boards where the veto never fires,
                         the ON trajectory is byte-identical to the OFF
                         trajectory (Fix A invisible when the veto is silent).

POSITIVE CONTROL / KILLED MUTANT (the gate must SEE the hole):
  M4_pubveto  (_VETO_PUB_MUTANT=True) drops the suppression -- byte-identical to
              the PRE-FIX-A shipped emitter (proven: its USE_DELTA=True build
              rebuilds veto1.hex md5 47edb895 exactly) -- and must FAIL T1 on
              the PC4 boards.  Running the gate on M4 IS running it on the
              unfixed emitter, bit for bit.

PC4 positive-control board family (synthetic, legal state, no resolved runs):
cols 0,1,2,5,6,7 full; col3 fo=2 with a capsule-colour virus at (2,3) (readiness
run-3 + matched cover pull the vetoed V col3 to the TOP of pass-0); col4 fo=4
with a wrong-colour virus at (4,4) (buried+pollution push the unvetoed V col4
just below).  Both verticals occupy 2 spawn-lane cells, so the leaf's -150/cell
spawn term -- which otherwise buries every throat placement -- cancels out.
Measured pass-0 margin: vetoed argmax +54 over the best unvetoed, for all three
double-capsule colours.

Usage: gate_mailbox_traj.py [--n 8] [--fast]
Exit 0 = all checks pass AND M4 killed.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_drveto as GG  # noqa: E402  (sets the recipe env before builder import)
from gate_owner_boards import load_board  # noqa: E402

S_BEST_C, S_BEST_O = 0x6134, 0x6135
VETO1_MD5 = "47edb8952dd3ae10e26c980eda405fd0"

V, J = 0xD0, 0x40


def _fill_col(b, col, fo, colors):
    for i, r in enumerate(range(fo, 16)):
        b[r * 8 + col] = colors[i % len(colors)]


def _no_resolved_runs(b):
    for r in range(16):
        run = 1
        for c in range(1, 8):
            x, y = b[r * 8 + c], b[r * 8 + c - 1]
            run = run + 1 if (x != 0xFF and y != 0xFF and (x & 3) == (y & 3)) else 1
            if run >= 4:
                return False
    for c in range(8):
        run = 1
        for r in range(1, 16):
            x, y = b[r * 8 + c], b[(r - 1) * 8 + c]
            run = run + 1 if (x != 0xFF and y != 0xFF and (x & 3) == (y & 3)) else 1
            if run >= 4:
                return False
    return True


def pc4_board(cap):
    """The argmax-vetoed positive-control board for double capsule (cap, cap)."""
    b = [0xFF] * 128
    oth = [c for c in (0, 1, 2) if c != cap]
    for c in (0, 1, 2, 5, 6, 7):
        _fill_col(b, c, 0, [J | oth[0], J | oth[1], J | oth[0], J | oth[1]] * 4)
    _fill_col(b, 3, 2, [V | cap, J | oth[0], J | oth[1], J | oth[0]] * 4)
    _fill_col(b, 4, 4, [V | oth[1], J | oth[0], J | oth[1], J | oth[0]] * 3)
    assert _no_resolved_runs(b)
    return b


def load_traj_board(path):
    """traj_c*_parent.json loader (viruses lowercase)."""
    d = json.load(open(path))
    M = {"Y": 0, "R": 1, "B": 2}   # project convention (gate_owner_boards.CMAP)
    b = [0xFF] * 128
    for r in range(16):
        for c in range(8):
            ch = d["grid"][r][c]
            if ch == ".":
                continue
            b[r * 8 + c] = (0xD0 if ch.islower() else 0x40) | M[ch.upper()]
    m = d["_meta"]
    return b, m["cA"], m["cB"], m["nA"], m["nB"]


def run_fw_traj(B, D3, img_full, search_ep, board, cA, cB, nA, nB, tseed=0):
    """One firmware decision with the FULL mailbox trajectory recorded.
    Returns (final, traj): final = (D_BC, D_BO) or None; traj = list of
    ("inval",) and ("pub", col, o4, d_veto_at_store) events in store order."""
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    from test_depth2 import S_CA, S_CB, S_NA, S_NB
    cpu = Cpu()
    for a, v in enumerate(img_full):
        cpu.mem[a] = v
    for i in range(16):
        cpu.mem[D3.PILLA + i] = img_full[B.PILL_ROM + i]
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    base = cpu.mem
    obs = ObservableMemory(subject=base)
    traj = []

    def on_store(addr, value):
        base[addr] = value
        if addr == S_BEST_O:
            if value == 0xFF:
                traj.append(("inval",))
            else:
                traj.append(("pub", base[S_BEST_C], value, base[D3.D_VETO]))

    obs.subscribe_to_write([S_BEST_C, S_BEST_O], on_store)
    cpu.mpu.memory = obs
    cpu.mem = obs
    cpu.mem[S_CA] = ((int(tseed) & 0x0F) << 4) | cA
    cpu.mem[S_CB] = (int(tseed) & 0xF0) | cB
    cpu.mem[S_NA], cpu.mem[S_NB] = nA, nB
    cpu.call(search_ep, max_steps=B.MAX_STEPS)
    final = None if cpu.mem[D3.D_BO] == 0xFF else (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])
    return final, traj


def mirror_info(D3, board, cA, cB, nA, nB, ts):
    """Shortlist size + fired set + finals from the bit-exact mirror."""
    import nes_d3_golden as G
    first = []
    for (o4, col, offa, offb, ta, tb) in G._placements4(board, cA, cB):
        b1 = G._place(board, offa, offb, ta, tb)
        cells1, vir1 = G._resolve(b1, offa, offb)
        first.append((G._imm(cells1, vir1) + G.leaf_d3(b1), col, o4))
    first.sort(key=lambda t: t[0], reverse=True)
    n_short = min(len(first), D3.TOPK1)
    fired = []
    fin_on = GG.decide_mirror(D3, board, cA, cB, nA, nB, ts & 0xFF, veto=True,
                              fired_out=fired)
    fin_off = GG.decide_mirror(D3, board, cA, cB, nA, nB, ts & 0xFF, veto=False)

    def canon(k):
        return (k[0], D3.canon_o4(k[1], cA, cB)) if k else None

    return {"n_short": n_short, "fired": sorted(set(fired)),
            "unvetoed_exists": n_short > len(set(fired)),
            "final_on": canon(fin_on), "final_off": canon(fin_off)}


def corpus(n, fast):
    """(name, board, cA, cB, nA, nB, kind) -- kind in {std, synth, pc, real}."""
    import random
    from test_search_d3 import make_fewlegal
    FSIM = os.environ.get("DRM_FAITHFUL_SIM")
    if not FSIM:
        for cand in ("/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim",
                     "/home/struktured/projects/dr-mario-rl/.claude/worktrees/faithful-sim"):
            if os.path.isdir(os.path.join(cand, "src")):
                FSIM = cand
                break
        else:
            raise SystemExit("faithful-sim worktree not found; set DRM_FAITHFUL_SIM")
    for p in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes
    out = []
    rng = random.Random(20260830)
    for i in range(n):
        fb = make_fewlegal(rng, FaithfulBoard)
        out.append((f"std{i}", list(faithful_to_nes(fb)), rng.randint(0, 2),
                    rng.randint(0, 2), rng.randint(0, 2), rng.randint(0, 2), "std"))
    for (name, board, (cA, cB, nA, nB), _exp) in GG.synth_cases():
        out.append((f"synth:{name}", board, cA, cB, nA, nB, "synth"))
    for cap in (0, 1, 2):
        out.append((f"PC4cap{cap}", pc4_board(cap), cap, cap, 1 if cap != 1 else 2,
                    2 if cap != 2 else 0, "pc"))
    g2 = load_board(os.path.join(HERE, "g2_parent.json"), 2, [15, 14])
    g3 = load_board(os.path.join(HERE, "g3_parent.json"), 15, [15, 14, 13, 12])
    out.append(("ownerG2", g2, 0, 2, 0, 1, "real"))
    out.append(("ownerG3", g3, 2, 0, 0, 1, "real"))
    for nm in ("traj_c1_parent.json", "traj_c5_parent.json"):
        b, cA, cB, nA, nB = load_traj_board(os.path.join(HERE, nm))
        out.append((nm.split("_parent")[0], b, cA, cB, nA, nB, "real"))
    if fast:
        out = [x for x in out if x[6] != "std"] + [x for x in out if x[6] == "std"][:2]
    return out


def run_gate(n, mutant=False, fast=False, verbose=True):
    B, D3 = GG._load()
    if mutant:
        D3._VETO_PUB_MUTANT = True
    try:
        img_on, ep_on, _ = GG.image_for(B, D3, True)
        img_off, ep_off, _ = GG.image_for(B, D3, False)
        boards = corpus(n, fast)
        viol, starve, fbviol, finmis, ctlmis = [], [], [], [], []
        n_pub_veto_seen = n_allvetoed = n_decisions = 0
        ts = 0
        for (name, board, cA, cB, nA, nB, kind) in boards:
            mi = mirror_info(D3, board, cA, cB, nA, nB, ts)
            fin, traj = run_fw_traj(B, D3, img_on, ep_on, board, cA, cB, nA, nB, ts)
            n_decisions += 1
            pubs = [e for e in traj if e[0] == "pub"]
            veto_pubs = [e for e in pubs if e[3] == 1]
            n_pub_veto_seen += len(veto_pubs)
            if mi["unvetoed_exists"]:
                if veto_pubs:                                   # T1
                    viol.append((name, veto_pubs))
                if not pubs:                                    # T2
                    starve.append(name)
            elif mi["n_short"] > 0 and mi["fired"]:
                n_allvetoed += 1
                if pubs or fin is None:                         # T3
                    fbviol.append((name, pubs, fin))
            if fin != mi["final_on"]:                           # T4
                finmis.append((name, fin, mi["final_on"]))
            if kind == "std" and not mi["fired"]:               # T5
                fin2, traj2 = run_fw_traj(B, D3, img_off, ep_off, board,
                                          cA, cB, nA, nB, ts)
                if traj != traj2 or fin != fin2:
                    ctlmis.append((name, traj, traj2))
        checks = {
            "T1_no_vetoed_visible": not viol,
            "T2_liveness": not starve,
            "T3_allvetoed_fallback": not fbviol and n_allvetoed > 0,
            "T4_final_conserved": not finmis,
            "T5_silent_control": not ctlmis,
            "coverage_pc_boards": any(k == "pc" for (*_x, k) in boards),
        }
        if verbose:
            tag = "M4_pubveto" if mutant else "REAL(FixA)"
            print(f"\n=== {tag}  ({n_decisions} searches; all-vetoed boards: "
                  f"{n_allvetoed}; vetoed stores seen: {n_pub_veto_seen})")
            print(f"  T1 no-vetoed-visible : "
                  f"{'PASS' if checks['T1_no_vetoed_visible'] else 'FAIL'} "
                  f"({len(viol)} violations: {[v[0] for v in viol][:6]})")
            print(f"  T2 liveness          : "
                  f"{'PASS' if checks['T2_liveness'] else 'FAIL'} "
                  f"({len(starve)} starved: {starve[:6]})")
            print(f"  T3 all-vetoed fallbk : "
                  f"{'PASS' if checks['T3_allvetoed_fallback'] else 'FAIL'} "
                  f"({len(fbviol)} bad: {[v[0] for v in fbviol][:6]})")
            print(f"  T4 final conserved   : "
                  f"{'PASS' if checks['T4_final_conserved'] else 'FAIL'} "
                  f"({len(finmis)} mismatches: {finmis[:4]})")
            print(f"  T5 silent control    : "
                  f"{'PASS' if checks['T5_silent_control'] else 'FAIL'} "
                  f"({len(ctlmis)} ON!=OFF trajectories on fire-free boards)")
        return checks
    finally:
        D3._VETO_PUB_MUTANT = False
        os.environ["DRVETO"] = "0"


def m4_is_prefix_emitter():
    """Prove M4 == the pre-Fix-A shipped emitter: its USE_DELTA=True build must be
    byte-identical to tmp/drveto/veto1.hex (md5 47edb895)."""
    import hashlib
    code = r"""
import importlib.util, os, sys, hashlib
ROOT = %r
COPRO = os.path.join(ROOT, "fpga", "copro")
sys.path.insert(0, COPRO)
def pin(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod
    spec.loader.exec_module(mod); return mod
D3 = pin("test_search_d3", os.path.join(ROOT, "tests", "test_search_d3.py"))
TV = pin("tuck_v3", os.path.join(COPRO, "tuck_v3.py"))
D3.DEBUG_VAL1 = False; D3.USE_DELTA = True
D3.DELTA_P0 = D3.DELTA_P2 = D3.DELTA_P3 = None
D3._VETO_PUB_MUTANT = True
import build_copro_d3 as B
img, clen, slen = B.build_image([0xFF]*128, 0, 0, 0, 0)
for i in range(128): img[0x0500+i] = 0xFF
rom = img[0x8000:0xC000]
txt = "\n".join("%%02x" %% x for x in rom) + "\n"
print(hashlib.md5(txt.encode()).hexdigest())
""" % (os.path.abspath(os.path.join(HERE, "..", "..")),)
    env = dict(os.environ)
    env.update(GG.RECIPE_ENV)
    env["DRVETO"] = "1"
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, env=env)
    md5 = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    ok = md5 == VETO1_MD5
    print(f"  M4==pre-FixA emitter : {'PASS' if ok else 'FAIL'} "
          f"(M4 delta build md5 {md5[:8]} vs shipped veto1 {VETO1_MD5[:8]})")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--mutant-only", action="store_true",
                    help="run only the M4 arm (positive control)")
    args = ap.parse_args()
    print("=" * 70)
    print("G2 -- MAILBOX-TRAJECTORY GATE (anytime stream, not the final answer)")
    print("=" * 70)
    ident = m4_is_prefix_emitter()
    if args.mutant_only:
        mres = run_gate(args.n, mutant=True, fast=args.fast)
        killed = not mres["T1_no_vetoed_visible"]
        print(f"\nM4_pubveto (== unfixed emitter): "
              f"{'FAILS T1 as required (gate SEES the hole)' if killed else 'SURVIVED -- gate is blind'}")
        return 0 if (ident and killed) else 1
    real = run_gate(args.n, mutant=False, fast=args.fast)
    must = ["T1_no_vetoed_visible", "T2_liveness", "T3_allvetoed_fallback",
            "T4_final_conserved", "T5_silent_control", "coverage_pc_boards"]
    real_ok = all(real.get(k) for k in must)
    mres = run_gate(args.n if not args.fast else 4, mutant=True, fast=True)
    killed = not mres["T1_no_vetoed_visible"]
    print("\n" + "=" * 70)
    print(f"REAL (Fix A) implementation: {'PASS' if real_ok else 'FAIL'}")
    print(f"M4_pubveto (bit-exact pre-Fix-A emitter): "
          f"{'KILLED by T1' if killed else 'SURVIVED -- gate cannot see the hole'}")
    ok = ident and real_ok and killed
    print(f"\nG2 GATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
