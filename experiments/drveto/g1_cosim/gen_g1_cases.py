#!/usr/bin/env python3
"""G1-minimal case generator: emits g1cases.txt (for sim_g1_veto.cpp) plus
g1_reference.json (py65 full-stub reference: final answer, $B4:=0 write count,
mirror fired set post-canon, unvetoed_exists) for the runner's comparisons.

Cases (the workflow's minimal blocking set + the delta-trajectory control):
  1-5  the five vetog1 fatal-board reconstructions (parent_s{1A,1B,2A,3A,4A}),
       cap (R,Y)=(1,0), next (0,1) -- the exact class of the live failure
  6-8  golden make_fewlegal boards (rng 2026, the build_copro_d3 battery family)
  9    RV_clear_c3 synth case -- the M2 killer (stale rv==0 at o_cand vetoes a
       CLEARING plug the spec exempts)
  10   PC4cap0 -- pass-0-argmax-vetoed board (the anytime-hole positive control;
       on the pre-Fix-A veto1 hex the vetoed pub MUST be bus-visible)

py65 reference runs the FULL STUB FLOW (reset @$BF80 -> tables -> search -> tuck
-> final publish -> DONE) on the Fix-A BASE build (USE_DELTA=False; py65 has no
CMD-6/7), so the reference final includes the tuck extension exactly like the
silicon flow.  The vsim gate's BINDING equality is delta==base WITHIN the rig;
the py65 final is a cross-check (the RTL chain leaf may diverge from the
engine-emu leaf on dense boards -- reported, not gated).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRVETO_DIR = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, DRVETO_DIR)
import gate_drveto as GG                       # noqa: E402  (recipe env first)
import gate_mailbox_traj as GT                 # noqa: E402

VETOG1 = os.environ.get("VETOG1_DIR", os.path.join(HERE, "vetog1_parents"))

CMAP = {"Y": 0, "R": 1, "B": 2}


def load_vetog1(path):
    d = json.load(open(path))
    vs = {tuple(x) for x in d["virus_cells"]}
    b = [0xFF] * 128
    for r in range(16):
        for c in range(8):
            ch = d["grid"][r][c]
            if ch == ".":
                continue
            b[r * 8 + c] = CMAP[ch] | (0xD0 if (r, c) in vs else 0x40)
    return b


def golden_boards(n=3):
    """First n make_fewlegal draws PLUS the first veto-silent draw (a fw whose two
    open columns avoid the throat), so the delta path is exercised with the veto
    firing (plugged-parent note-A boards) AND fully silent."""
    import random
    from test_search_d3 import make_fewlegal
    FSIM = None
    for cand in ("/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim",
                 "/home/struktured/projects/dr-mario-rl/.claude/worktrees/faithful-sim"):
        if os.path.isdir(os.path.join(cand, "src")):
            FSIM = cand
            break
    for p in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes
    rng = random.Random(2026)
    out = []
    draws = 0
    have_silent = False
    while len(out) < n or not have_silent:
        fb = make_fewlegal(rng, FaithfulBoard)
        nes = list(faithful_to_nes(fb))
        cA, cB = rng.randint(0, 2), rng.randint(0, 2)
        nA, nB = rng.randint(0, 2), rng.randint(0, 2)
        draws += 1
        assert draws < 50
        silent = nes[3] == 0xFF and nes[4] == 0xFF
        if len(out) < n:
            out.append((f"golden{len(out)}", nes, cA, cB, nA, nB))
            have_silent = have_silent or silent
        elif silent:
            out.append((f"golden{len(out)}_silent", nes, cA, cB, nA, nB))
            have_silent = True
    return out


def full_stub_run(B, D3, img_full, board, cA, cB, nA, nB):
    """py65 full stub flow with the same observers the vsim tb carries."""
    from py65.memory import ObservableMemory
    from py65_harness import Cpu
    from test_depth2 import S_CA, S_CB, S_NA, S_NB
    cpu = Cpu()
    for a, v in enumerate(img_full):
        cpu.mem[a] = v
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    base = cpu.mem
    obs = ObservableMemory(subject=base)
    stats = {"b4zero": 0, "b4one": 0, "pubs": [], "tuck_started": False}

    def on_write(addr, value):
        base[addr] = value
        if addr == D3.D_VETO:
            stats["b4zero" if value == 0 else "b4one"] += 1
        elif addr == 0x6135 and value != 0xFF:
            stats["pubs"].append((base[0x6134], value, base[D3.D_VETO],
                                  "search" if not stats["tuck_started"] else "post"))

    obs.subscribe_to_write([D3.D_VETO, 0x6134, 0x6135], on_write)
    # phase marker: the first FETCH into the tuck ROM window [$9000,$A800) ends the
    # search phase -- after it, zp $B4 is STALE (last root candidate's flag) and a
    # pub's veto tag is meaningless.  The search code+data never touches that window
    # (search ends <$8C00; SQ tables live at $B000).
    def on_read(addr):
        if not stats["tuck_started"]:
            stats["tuck_started"] = True
        return base[addr]
    obs.subscribe_to_read(list(range(0x9000, 0xA800, 1)), on_read)
    cpu.mpu.memory = obs
    cpu.mem = obs
    cpu.mem[S_CA] = cA
    cpu.mem[S_CB] = cB
    cpu.mem[S_NA], cpu.mem[S_NB] = nA, nB
    cpu.mem[B.DONE] = 0
    m = cpu.mpu
    m.pc = B.STUB
    m.sp = 0xFF
    steps = 0
    while steps < B.MAX_STEPS:
        m.step()
        steps += 1
        if cpu.mem[B.DONE]:
            break
    assert cpu.mem[B.DONE] == 1, "stub flow never reached DONE"
    return (cpu.mem[0x6134], cpu.mem[0x6135]), stats


def main():
    B, D3 = GG._load()
    img_on, _ep, _c = GG.image_for(B, D3, True)

    cases = []
    for nm in ("parent_s1A", "parent_s1B", "parent_s2A", "parent_s3A", "parent_s4A"):
        cases.append((nm, load_vetog1(os.path.join(VETOG1, nm + ".json")),
                      1, 0, 0, 1))
    cases += golden_boards(3)
    rv = next(x for x in GG.synth_cases() if x[0] == "RV_clear_c3")
    cases.append(("RV_clear_c3", rv[1], *rv[2]))
    cases.append(("PC4cap0", GT.pc4_board(0), 0, 0, 1, 2))

    ref = {}
    lines = [str(len(cases))]
    for (name, board, cA, cB, nA, nB) in cases:
        mi = GT.mirror_info(D3, board, cA, cB, nA, nB, 0)
        fired_canon = sorted({(c, D3.canon_o4(o, cA, cB)) for (c, o) in mi["fired"]})
        img = bytearray(img_on)
        final, stats = full_stub_run(B, D3, img, board, cA, cB, nA, nB)
        ref[name] = {"final": list(final), "b4zero": stats["b4zero"],
                     "b4one": stats["b4one"],
                     "pubs": [list(p) for p in stats["pubs"]],
                     "fired_canon": [list(f) for f in fired_canon],
                     "unvetoed_exists": mi["unvetoed_exists"],
                     "n_short": mi["n_short"],
                     "final_search_mirror": list(mi["final_on"]) if mi["final_on"] else None}
        nf = len(fired_canon)
        lines.append(f"{name} {cA} {cB} {nA} {nB} {nf} " +
                     " ".join(f"{c} {o}" for (c, o) in fired_canon) +
                     (" " if nf else "") + f"{1 if mi['unvetoed_exists'] else 0}")
        lines.append(" ".join("%02x" % x for x in board))
        print(f"{name}: final={final} b4zero={stats['b4zero']} "
              f"pubs={len(stats['pubs'])} fired={fired_canon} "
              f"unvetoed={mi['unvetoed_exists']}")
    with open(os.path.join(HERE, "g1cases.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(HERE, "g1_reference.json"), "w") as f:
        json.dump(ref, f, indent=1)
    print(f"wrote g1cases.txt ({len(cases)} cases) + g1_reference.json")


if __name__ == "__main__":
    main()
