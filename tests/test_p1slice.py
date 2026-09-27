#!/usr/bin/env python3
"""DRP1SLICE gate battery (#126 enforcement 1) -- 12-rule standard.

GATES
  G1 BYTE-IDENTITY OFF: every emitted unit under the TCVC ship flags is
     byte-identical with DRP1SLICE unset (the flag may not cost ship carts a
     byte).
  G2 WHOLE-CHAIN ARGMAX EQUIVALENCE: for every corpus board x colour pair,
     the sliced state machine -- driven tick by tick with ALL v18 zp scratch
     CLOBBERED between ticks (the game owns those bytes between NMIs) -- must
     publish the SAME (column, orient) AND the same best score as one
     synchronous search_entry run. Also: the board is bit-identical after
     both (eval must undo its trial placements).
  G3 KILLED MUTANTS (each must break G2 on >=1 corpus case):
     M1 v-pass exits at column 7 instead of 8   (skips a placement)
     M2 tick does not SAVE Z_BEST to PRG-RAM    (state dies with the zp clobber)
     M3 swap re-eval skipped                    (publishes pre-swap orient)
     M4 tick does not RESTORE Z_COL             (resume column garbage)
  G4 CYCLE BUDGET: measured worst tick <= its census bound, and the census
     same-frame pair bound + measured game-NMI head (2,040) + tail eps (300)
     < 29,780 -- the (a) certificate for the sliced cart.

Run with the dr-mario-mods venv python (py65):
  /home/struktured/projects/dr-mario-mods/.venv/bin/python tests/test_p1slice.py
"""
import json
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "nmi126"))

MANIFEST = "roms/manifests/tuck-cvc-mister.json"
IR_OFF = "tmp/nmi126/gate_tcvc_off.json"
IR_ON = "tmp/nmi126/gate_tcvc_slice.json"

# v18 AI zero-page scratch: the game's between NMIs, so the sliced search may
# depend on NONE of it across ticks. Clobbered with 0xA5 between every tick.
ZP_SCRATCH = [0x00, 0x01, 0x6B, 0x6D, 0x6E, 0x6F] + list(range(0xCA, 0xD0)) \
             + list(range(0xD0, 0xDC))

P1AI_C, P1AI_O = 0x617E, 0x617F
SL_PH, SL_COL, SL_BEST, SL_TGT = 0x61BB, 0x61BC, 0x61BD, 0x61BE
SL_ORI, SL_OFA, SL_OFB = 0x61BF, 0x61C0, 0x61C1
SENT = 0x3000


def capture(out, *overlay):
    subprocess.run([sys.executable, "tools/nmi126/capture_ir.py", MANIFEST, out,
                    *overlay], check=True, capture_output=True)
    return json.load(open(out))


def build_mem(meta):
    mem = [0] * 0x10000
    for u in meta["units"].values():
        b = bytes.fromhex(u["bytes"])
        mem[u["base"]:u["base"] + len(b)] = list(b)
    mem[SENT] = 0xEA
    return mem


def run_sub(m, entry, max_steps=3_000_000):
    m.pc = entry
    m.memory[0x1FE] = (SENT - 1) & 0xFF
    m.memory[0x1FF] = ((SENT - 1) >> 8) & 0xFF
    m.sp = 0xFD
    c0 = m.processorCycles
    steps = 0
    while m.pc != SENT and steps < max_steps:
        m.step()
        steps += 1
    assert m.pc == SENT, f"no return from ${entry:04X} (pc=${m.pc:04X})"
    return m.processorCycles - c0


def corpus():
    """Boards ($0400 layout, 0xFF empty) x colour pairs."""
    out = []
    empty = [0xFF] * 128
    out.append(("empty", empty, (0, 0)))
    tall = [0xFF] * 128
    for c in range(8):
        for r in range(4 + (c % 2), 16):
            tall[r * 8 + c] = 0xD0
    out.append(("tall_same", tall, (0, 0)))
    floor = [0xFF] * 128
    for c in range(8):
        floor[15 * 8 + c] = 0xD0
        floor[14 * 8 + c] = 0xD1
    out.append(("floor", floor, (0, 1)))
    # swap-decisive construction: a colour-1 virus column stub where the
    # swapped tile order clears and the direct order does not.
    swp = [0xFF] * 128
    for r in (13, 14, 15):
        swp[r * 8 + 3] = 0xD1
    out.append(("swap_bait", swp, (0, 1)))
    rng = random.Random(126)
    fills = [0xFF] * 6 + [0xD0, 0xD1, 0xD2, 0x80, 0x81, 0x82]
    for i in range(40):
        b = [0xFF] * 128
        depth = rng.randrange(0, 14)
        for c in range(8):
            top = rng.randrange(max(1, 16 - depth), 17)
            for r in range(top, 16):
                b[r * 8 + c] = rng.choice(fills[6:]) if rng.random() < 0.7 else 0xFF
        cols = (rng.randrange(3), rng.randrange(3))
        out.append((f"rand{i}", b, cols))
    return out


def unsliced_result(meta_off, board, colors):
    from py65.devices.mpu6502 import MPU
    m = MPU(memory=build_mem(meta_off))
    for i, v in enumerate(board):
        m.memory[0x0400 + i] = v
    m.memory[0x0301], m.memory[0x0302] = colors
    se = meta_off["units"]["p1ai"]["base"] + meta_off["units"]["p1ai"]["labels"]["search_entry"]
    run_sub(m, se)
    res = (m.memory[0x00], m.memory[0xDA], m.memory[0x01])
    assert m.memory[0x0400:0x0480] == list(board), "unsliced: board not restored"
    return res


def sliced_result(meta_on, board, colors, patch=None, want_cycles=False):
    from py65.devices.mpu6502 import MPU
    mem = build_mem(meta_on)
    if patch:
        for a, v in patch:
            mem[a] = v
    m = MPU(memory=mem)
    for i, v in enumerate(board):
        m.memory[0x0400 + i] = v
    m.memory[0x0301], m.memory[0x0302] = colors
    # arm exactly as the spawn edge does
    m.memory[SL_PH], m.memory[SL_COL], m.memory[SL_BEST] = 1, 0, 0
    m.memory[SL_TGT] = 3
    m.memory[SL_ORI] = m.memory[SL_OFA] = m.memory[SL_OFB] = 0
    tick = meta_on["units"]["main"]["base"] + meta_on["units"]["main"]["labels"]["p1s_tick"]
    worst = 0
    ticks = 0
    while m.memory[SL_PH] != 0 and ticks < 24:
        for a in ZP_SCRATCH:                       # the game owns zp between NMIs
            m.memory[a] = 0xA5
        worst = max(worst, run_sub(m, tick))
        ticks += 1
    if m.memory[SL_PH] != 0:
        return ("NONTERM", ticks, None, None, worst)
    res = (m.memory[P1AI_C], m.memory[P1AI_O], m.memory[SL_BEST])
    board_ok = m.memory[0x0400:0x0480] == list(board)
    return ("OK", ticks, res, board_ok, worst)


def find_patch(meta_on, which):
    """Locate mutant patch bytes from the IR (offset-robust, label-anchored)."""
    u = meta_on["units"]["main"]
    base, labs = u["base"], u["labels"]
    recs = [r for r in u["records"] if r["k"] != "label"]

    def between(a, b):
        return [r for r in recs if labs[a] <= r["off"] < labs.get(b, 1 << 30)]

    if which == "M1":  # p1s_vnext's CMP_imm 8 -> 7
        for r in between("p1s_vnext", "p1s_vret"):
            if r["k"] == "ins" and r["m"] == "CMP_imm" and r["ops"] == [8]:
                return [(base + r["off"] + 1, 0x07)]
    if which == "M2":  # save block: first STA_abs SL_BEST after the tick's JSR
        for r in between("p1s_tick", "p1s_one"):
            if r["k"] == "ins" and r["m"] == "STA_abs" and \
               r["ops"] == [SL_BEST & 0xFF, SL_BEST >> 8]:
                a = base + r["off"]
                return [(a, 0xEA), (a + 1, 0xEA), (a + 2, 0xEA)]
    if which == "M3":  # p1s_sw's JSR $9200 -> NOPs
        for r in between("p1s_sw", "act"):
            if r["k"] == "jsr" and r["target"] == 0x9200:
                a = base + r["off"]
                return [(a, 0xEA), (a + 1, 0xEA), (a + 2, 0xEA)]
    if which == "M4":  # restore of SL_COL (LDA_abs SL_COL + STA_zp $6B) -> NOPs
        rs = between("p1s_tick", "p1s_one")
        for i, r in enumerate(rs):
            if r["k"] == "ins" and r["m"] == "LDA_abs" and \
               r["ops"] == [SL_COL & 0xFF, SL_COL >> 8]:
                nxt = rs[i + 1]
                assert nxt["m"] == "STA_zp" and nxt["ops"] == [0x6B]
                a = base + r["off"]
                return [(a + k, 0xEA) for k in range(5)]
    raise SystemExit(f"mutant {which}: patch site not found (layout changed?)")


def main():
    meta_off = capture(IR_OFF)
    meta_off2 = capture(IR_OFF + ".2", "DRP1SLICE=0")
    meta_on = capture(IR_ON, "DRP1SLICE=1")

    # ---- G1 byte-identity OFF ----
    for name in meta_off["units"]:
        a = meta_off["units"][name]["bytes"]
        b = meta_off2["units"][name]["bytes"]
        assert a == b, f"G1 FAIL: unit {name} differs between unset and DRP1SLICE=0"
    assert meta_off["units"]["main"]["bytes"] != meta_on["units"]["main"]["bytes"], \
        "G1 sanity: DRP1SLICE=1 must change the driver (flag inert?)"
    print("G1 byte-identity OFF: PASS")

    # ---- G2 equivalence ----
    cases = corpus()
    worst_tick = 0
    max_ticks = 0
    for name, board, colors in cases:
        want = unsliced_result(meta_off, board, colors)
        st, ticks, got, board_ok, w = sliced_result(meta_on, board, colors)
        assert st == "OK", f"G2 {name}: sliced did not terminate ({ticks} ticks)"
        assert board_ok, f"G2 {name}: sliced left the board modified"
        assert got == want, f"G2 {name}: sliced {got} != unsliced {want}"
        worst_tick = max(worst_tick, w)
        max_ticks = max(max_ticks, ticks)
    print(f"G2 argmax equivalence: PASS ({len(cases)} cases, zp clobbered every "
          f"tick; max {max_ticks} ticks, worst tick {worst_tick} cyc)")
    assert max_ticks <= 16, f"tick count {max_ticks} exceeds the 16-hook design"

    # ---- G3 mutants ----
    for mut in ("M1", "M2", "M3", "M4"):
        patch = find_patch(meta_on, mut)
        killed = False
        for name, board, colors in cases:
            want = unsliced_result(meta_off, board, colors)
            st, ticks, got, board_ok, _ = sliced_result(meta_on, board, colors,
                                                        patch=patch)
            if st != "OK" or got != want or not board_ok:
                killed = True
                print(f"G3 {mut}: KILLED on {name} "
                      f"({'nonterm' if st != 'OK' else f'{got} != {want}'})")
                break
        assert killed, f"G3 {mut}: MUTANT SURVIVED -- the corpus cannot see it"

    # ---- G4 cycle budget ----
    import census
    nodes = census.load_from_meta(meta_on)
    so = census.detect_site_overrides(meta_on, nodes)
    an = census.Analyzer(nodes, site_overrides=so)
    wrap = meta_on["units"]["wrapper"]["base"]
    an.worst(wrap)
    tick_addr = meta_on["units"]["main"]["base"] + \
        meta_on["units"]["main"]["labels"]["p1s_tick"]
    tick_bound = an.routine_cost[(tick_addr, frozenset())][0]
    assert worst_tick <= tick_bound, \
        f"G4: measured tick {worst_tick} EXCEEDS its census bound {tick_bound}"
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])
    res = {}
    for sname, cuts in census.SCENARIO_CUTS.items():
        cuts_here = [(k, l) for k, l in cuts if l in have]
        a2 = census.Analyzer(nodes, cuts_here, site_overrides=so)
        res[sname] = a2.worst(wrap)
    pair = res["p1_search"] + res["spawn_edge_p2"] + 12
    GAME_HEAD, EPS, FRAME = 2040, 300, 29780
    total = pair + GAME_HEAD + EPS
    assert total < FRAME, f"G4: pair {pair} + head + eps = {total} >= {FRAME}"
    print(f"G4 cycle budget: PASS (tick bound {tick_bound}, measured {worst_tick}; "
          f"pair {pair} + head {GAME_HEAD} + eps {EPS} = {total} < {FRAME})")
    print("test_p1slice: ALL PASS")


if __name__ == "__main__":
    main()
