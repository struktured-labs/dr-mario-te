#!/usr/bin/env python3
"""Gate for the #126 static cycle census (gate-standard rules 1/2/5).

Part A -- MATH EXACTNESS on synthetic fixtures whose worst case is computed BY
HAND (independent implementation of the spec, rule 4): a branch diamond, a
counted loop, a nested loop, and a JSR. The analyzer must return the exact
hand-derived number, not merely something plausible.

Part B -- KILLED MUTANTS: each deliberately wrong input MUST make the analyzer
fail or change its answer in the predicted direction:
  M1 undeclared loop            -> hard fail (SystemExit)
  M2 unknown opcode             -> hard fail
  M3 recursion (JSR cycle)      -> hard fail
  M4 loop bound lowered by 1    -> bound DECREASES by exactly one worst-iteration
  M5 extra straight-line instrs -> bound INCREASES by exactly their cost

Part C -- WHOLE-CHAIN ANCHOR against reality: execute the REAL emitted
wrapper+main bytes (v6e config) on py65 from a concrete idle-hook machine
state, count actual cycles, and require actual <= the static bound. A bound
the real program can exceed is not a bound. (Run with the dr-mario-mods venv
python; py65 is not on the default python.)

Usage: python3 tools/nmi126/test_census.py   (from the worktree root)
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census


def mk_meta(records, labels, base=0x8000, main_off=0):
    """Wrap raw IR records into the census input shape (bytes irrelevant to
    the analyzer's math; the ground-truth byte gate lives in capture_ir)."""
    return {
        "manifest": "<fixture>",
        "flags_on": {},
        "p1native": False,
        "main_cpu": base + main_off,
        "units": {
            "main": {"base": base, "labels": labels, "records": records},
            # a wrapper that just JSRs main and RTSes: JSR(6)+W(main)+RTS(6)
            "wrapper": {"base": 0xFF54, "labels": {},
                        "records": [
                            {"k": "jsr", "off": 0, "m": "JSR", "target": base + main_off},
                            {"k": "ins", "off": 3, "m": "RTS", "ops": []},
                        ]},
        },
    }


def analyze(meta):
    nodes = census.load_from_meta(meta)
    an = census.Analyzer(nodes)
    w = an.worst(0xFF54)
    return w, an


def expect_fail(fn, tag):
    try:
        fn()
    except (SystemExit, AssertionError) as e:
        print(f"  {tag}: KILLED ({str(e)[:70]})")
        return
    raise SystemExit(f"MUTANT SURVIVED: {tag}")


def fixtures():
    ok = True

    # ---- F1: branch diamond. LDA_imm(2); BNE{long:LDA_abs(4)+RTS | short:RTS}
    recs = [
        {"k": "ins", "off": 0, "m": "LDA_imm", "ops": [1]},
        {"k": "br", "off": 2, "m": "BNE", "target": "long"},
        {"k": "ins", "off": 4, "m": "RTS", "ops": []},          # short arm
        {"k": "ins", "off": 5, "m": "LDA_abs", "ops": [0, 0]},  # 'long'
        {"k": "ins", "off": 8, "m": "RTS", "ops": []},
    ]
    labs = {"long": 5}
    # hand: wrapper JSR 6 + [LDA 2 + BNE taken 3 (same page) + LDA_abs 4 + RTS 6] + wrapper RTS 6
    w, _ = analyze(mk_meta(recs, labs))
    exp = 6 + (2 + 3 + 4 + 6) + 6
    assert w == exp, f"F1 diamond: got {w} want {exp}"
    print(f"  F1 diamond exact: {w}")

    # ---- F2: counted loop, declared bound 5.
    # l: INC_abs(6); BNE l(taken 3) ... exits fallthrough(2); RTS(6)
    recs = [
        {"k": "ins", "off": 0, "m": "INC_abs", "ops": [0, 0]},   # 'l'
        {"k": "br", "off": 3, "m": "BNE", "target": "l"},
        {"k": "ins", "off": 5, "m": "RTS", "ops": []},
    ]
    labs = {"l": 0}
    census.LOOP_BOUNDS["l"] = 5
    w, _ = analyze(mk_meta(recs, labs))
    # hand: one DAG pass = INC 6 + BNE not-taken 2 + RTS 6 = 14
    # loop extra = (5-1) * worst_iter; worst_iter = INC 6 + BNE taken 3 = 9
    exp = 6 + (14 + 4 * 9) + 6
    assert w == exp, f"F2 loop: got {w} want {exp}"
    print(f"  F2 counted loop exact: {w}")

    # M4: bound lowered by one -> decreases by exactly one worst-iteration (9)
    census.LOOP_BOUNDS["l"] = 4
    w2, _ = analyze(mk_meta(recs, labs))
    assert w2 == w - 9, f"M4 bound sensitivity: got {w2} want {w - 9}"
    print(f"  M4 bound-1 shifts by one iteration: {w2} = {w}-9  KILLED")
    census.LOOP_BOUNDS.pop("l")

    # ---- F3: nested loop. outer(3) contains inner(4).
    # o: LDA_imm(2); i: DEX(2); BNE i; DEY(2); BNE o; RTS
    recs = [
        {"k": "ins", "off": 0, "m": "LDA_imm", "ops": [0]},      # 'o'
        {"k": "ins", "off": 2, "m": "DEX", "ops": []},           # 'i'
        {"k": "br", "off": 3, "m": "BNE", "target": "i"},
        {"k": "ins", "off": 5, "m": "DEY", "ops": []},
        {"k": "br", "off": 6, "m": "BNE", "target": "o"},
        {"k": "ins", "off": 8, "m": "RTS", "ops": []},
    ]
    labs = {"o": 0, "i": 2}
    census.LOOP_BOUNDS["o"] = 3
    census.LOOP_BOUNDS["i"] = 4
    w, _ = analyze(mk_meta(recs, labs))
    # hand: inner iter = DEX2+BNEtaken3 = 5; inner extra = 3*5 = 15 at 'i'
    # outer iter = LDA2 + [DEX2+BNEnt2 + inner extra 15] + DEY2 + BNEtaken3 = 26
    # outer extra = 2*26 = 52
    # DAG pass: LDA2 + DEX2+BNEnt2 +15 + DEY2 + BNEnt2 + RTS6 = 31; + 52 = 83
    exp = 6 + 83 + 6
    assert w == exp, f"F3 nested: got {w} want {exp}"
    print(f"  F3 nested loop exact: {w}")
    census.LOOP_BOUNDS.pop("o")
    census.LOOP_BOUNDS.pop("i")

    # ---- F4/M5: straight-line JSR + additive exactness.
    base_recs = [
        {"k": "jsr", "off": 0, "m": "JSR", "target": "sub"},
        {"k": "ins", "off": 3, "m": "RTS", "ops": []},
        {"k": "ins", "off": 4, "m": "LDA_zp", "ops": [0]},       # 'sub'
        {"k": "ins", "off": 6, "m": "RTS", "ops": []},
    ]
    labs = {"sub": 4}
    w, _ = analyze(mk_meta(base_recs, labs))
    exp = 6 + (6 + (3 + 6) + 6) + 6
    assert w == exp, f"F4 jsr: got {w} want {exp}"
    # M5: add NOP(2) + LDA_abs(4) + STA_abs(4) = +10 in sub
    recs = [
        {"k": "jsr", "off": 0, "m": "JSR", "target": "sub"},
        {"k": "ins", "off": 3, "m": "RTS", "ops": []},
        {"k": "ins", "off": 4, "m": "NOP", "ops": []},           # 'sub'
        {"k": "ins", "off": 5, "m": "LDA_abs", "ops": [0, 0]},
        {"k": "ins", "off": 8, "m": "STA_abs", "ops": [0, 0]},
        {"k": "ins", "off": 11, "m": "LDA_zp", "ops": [0]},
        {"k": "ins", "off": 13, "m": "RTS", "ops": []},
    ]
    labs = {"sub": 4}
    w2, _ = analyze(mk_meta(recs, labs))
    assert w2 == w + 10, f"M5 additive: got {w2} want {w + 10}"
    print(f"  F4 jsr exact {w}; M5 +10 additive exact: {w2}  KILLED")

    # ---- M1: undeclared loop
    recs = [
        {"k": "ins", "off": 0, "m": "DEX", "ops": []},           # 'u'
        {"k": "br", "off": 1, "m": "BNE", "target": "u"},
        {"k": "ins", "off": 3, "m": "RTS", "ops": []},
    ]
    expect_fail(lambda: analyze(mk_meta(recs, {"u": 0})), "M1 undeclared loop")

    # ---- M2: unknown opcode
    recs = [
        {"k": "ins", "off": 0, "m": "XYZZY_zp", "ops": [0]},
        {"k": "ins", "off": 2, "m": "RTS", "ops": []},
    ]
    expect_fail(lambda: analyze(mk_meta(recs, {})), "M2 unknown opcode")

    # ---- M3: recursion
    recs = [
        {"k": "jsr", "off": 0, "m": "JSR", "target": "a"},       # main JSR a
        {"k": "ins", "off": 3, "m": "RTS", "ops": []},
        {"k": "jsr", "off": 4, "m": "JSR", "target": "b"},       # 'a' JSR b
        {"k": "ins", "off": 7, "m": "RTS", "ops": []},
        {"k": "jsr", "off": 8, "m": "JSR", "target": "a"},       # 'b' JSR a
        {"k": "ins", "off": 11, "m": "RTS", "ops": []},
    ]
    expect_fail(lambda: analyze(mk_meta(recs, {"a": 4, "b": 8})),
                "M3 recursion")
    return ok


def anchor_py65():
    """Part C: run the REAL v6e wrapper+main on py65 from an idle-hook state;
    actual cycles must be <= the static hook bound."""
    ir_path = "tmp/nmi126/v6e_ir.json"
    if not os.path.exists(ir_path):
        subprocess.run([sys.executable, "tools/nmi126/capture_ir.py",
                        "roms/manifests/v6e.json", ir_path], check=True)
    meta = json.load(open(ir_path))
    nodes = census.load_from_meta(meta)
    an = census.Analyzer(nodes)
    bound = an.worst(meta["units"]["wrapper"]["base"])

    try:
        from py65.devices.mpu6502 import MPU
    except ImportError:
        raise SystemExit(
            "ANCHOR REQUIRES py65 -- run with "
            "/home/struktured/projects/dr-mario-mods/.venv/bin/python "
            "(absence is not pass)")

    scenarios = {
        # (name, ram setup dict addr->val). NAV_MAGIC=$6182? read from emitter
        # constants below. Idle: warm init done, menu mode, nothing armed.
    }
    # pull constants from the emitter under the same env
    env = json.load(open("roms/manifests/v6e.json"))["flag_snapshot"]
    os.environ.update({k: str(v) for k, v in env.items()})
    sys.path.insert(0, os.getcwd())
    import patch_cartridge_copro as pcc

    mem = [0] * 0x10000
    for uname, u in meta["units"].items():
        b = bytes.fromhex(u["bytes"])
        mem[u["base"]:u["base"] + len(b)] = list(b)

    results = {}
    for name, state in {
        "idle_menu": {pcc.NAV_MAGIC: 0xA5, 0x0046: 0x00},
        "play_unarmed": {pcc.NAV_MAGIC: 0xA5, 0x0046: 0x04, 0x04: 1},
        "cold_init": {pcc.NAV_MAGIC: 0x00, 0x0046: 0x00},
    }.items():
        m = MPU(memory=list(mem))
        for a, v in state.items():
            m.memory[a] = v
        # call wrapper: push a sentinel return address $FFFF-1
        SENT = 0x3000
        m.memory[SENT] = 0xEA  # NOP landing pad
        m.pc = 0xFF54
        m.memory[0x1FE] = (SENT - 1) & 0xFF
        m.memory[0x1FF] = ((SENT - 1) >> 8) & 0xFF
        m.sp = 0xFD
        steps = 0
        while m.pc != SENT and steps < 500000:
            m.step()
            steps += 1
        assert m.pc == SENT, f"{name}: did not return (pc=${m.pc:04X})"
        results[name] = m.processorCycles
        assert m.processorCycles <= bound, (
            f"ANCHOR VIOLATION: {name} actual {m.processorCycles} > static "
            f"bound {bound}")
    print(f"  anchor (v6e, bound {bound}): " +
          ", ".join(f"{k}={v}cyc" for k, v in results.items()) + "  ALL <= bound")


def main():
    print("PART A+B: fixtures + mutants")
    fixtures()
    print("PART C: py65 whole-chain anchor")
    anchor_py65()
    print("test_census: ALL PASS")


if __name__ == "__main__":
    main()
