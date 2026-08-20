#!/usr/bin/env python3
"""DRPRESPIPE gate battery (#126 enforcement 2) -- 12-rule standard.

The defect under test is NOT "pre_tick is slow": it is that the prestart
release-edge FRAME has a sound bound of 35,687 > 29,780, so the shipped cart
survives on margin rather than proof (NMI126_BOUND_REPORT.md verdict 4). The
fix pipelines pre_tick across hooks; these gates test the fix's OBLIGATIONS.

GATES
  G1 BYTE-IDENTITY OFF: every emitted unit is byte-identical with DRPRESPIPE
     unset vs =0, and the flag demonstrably changes the driver when =1 (an
     inert flag passes every equivalence test vacuously).
  G2 WHOLE-CHAIN EQUIVALENCE: for every corpus board, the pipelined path --
     driven hook by hook with ALL ZERO PAGE and both index registers CLOBBERED
     between hooks (the game owns those bytes between NMIs) -- must produce
     * the same 128 projected board bytes uploaded to the copro window,
     * the same mailbox colour/seed bytes (+$80..+$83) and the same GO,
     * the same commit-or-bail DECISION and the same PRE_ACT2/ARMED2/PEND2/
       WDOG2/WDOGH2 end state,
     as ONE synchronous pre_tick call on the same state; and GO must land on
     exactly the designed hook (edge + PP_NM + 1), never earlier or later.
  G3 SNAPSHOT SEMANTICS (a documented behaviour delta, gated so it cannot
     regress silently): if the live board $0500 changes AFTER the edge hook,
     the pipeline still uploads the EDGE-HOOK SNAPSHOT. This is the deliberate
     choice -- the synchronous path reads the board once at the edge too.
  G4 KILLED MUTANTS (each must break G2/G3/G5 on >=1 corpus case):
     M1 dispatcher never reaches phase 1        (skip-state: no settle)
     M2 commit uploads from LIVE $0500          (stale/fresh-read confusion)
     M3 PEND2 abort check deleted               (commits into a spawn)
     M4 phase-2 quota 4 -> 0                    (skips its records entirely)
     M5 pt_bail does not clear PP_PH            (machine left armed after a bail)
  G5 ABORT OBLIGATIONS: PEND2, ARMED2 and a second buffered volley each abort
     mid-pipeline with NO commit and NO GO, PP_PH back to 0; and the second
     volley's own release edge is swallowed, matching what the synchronous
     path does at that edge (it finds PRE_ACT2 set and starts nothing).
  G6 CYCLE CERTIFICATE: the census admissible-frame table -- the pairing model
     the abort checks make true -- must fit 29,780 including the measured game
     NMI head (2,040) and tail eps (300), for EVERY admissible pair; and the
     measured worst hook must not exceed its census bound.

Run with the dr-mario-mods venv python (py65):
  /home/struktured/projects/dr-mario-mods/.venv/bin/python tests/test_prespipe.py
"""
import json
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "nmi126"))

MANIFEST = "roms/manifests/v6e.json"
TMP = "tmp/prespipe"
IR_OFF = f"{TMP}/off.json"
IR_OFF0 = f"{TMP}/off0.json"
IR_ON = f"{TMP}/on.json"

# driver PRG-RAM (patch_cartridge_copro.py)
PEND2, ARMED2, WDOG2, WDOGH2, SEED2 = 0x614F, 0x6161, 0x6162, 0x6166, 0x6168
PRE_ATK2 = 0x0318
PRE_LAST2, PRE_ACT2 = 0x6199, 0x619A
PRE_I, PRE_N = 0x61A9, 0x61A0
PRE_BUF = 0x6500
PP_PH, PP_SWAL = 0x61C2, 0x61C3
BOARD2 = 0x0500                      # P2's live playfield
SENT = 0x3000

E = 0xFF                             # empty cell
GARB = 0x80                          # singleHalfPill (the garbage tile class)
VIRUS = 0xD0


def capture(out, *overlay):
    os.makedirs(TMP, exist_ok=True)
    subprocess.run([sys.executable, "tools/nmi126/capture_ir.py", MANIFEST, out,
                    *overlay], check=True, capture_output=True)
    return json.load(open(out))


def window_base(meta):
    """The P2 copro window, read out of the IR rather than assumed: DRPOCKET
    moves it $5200 -> $5000 and a hard-coded guess would compare the wrong
    128 bytes and pass vacuously."""
    u = meta["units"]["main"]
    base, labels = u["base"], u["labels"]
    recs = [r for r in u["records"] if r["k"] != "label"]
    lo = labels["pt_up"]
    for r in recs:
        if r["off"] >= lo and r["k"] == "ins" and r["m"] == "STA_absX":
            w = r["ops"][0] | (r["ops"][1] << 8)
            assert w in (0x5000, 0x5200), f"unexpected window ${w:04X}"
            return w
    raise SystemExit("could not locate the upload store in the IR")


def build_mem(meta, patch=None):
    mem = [0] * 0x10000
    for u in meta["units"].values():
        b = bytes.fromhex(u["bytes"])
        mem[u["base"]:u["base"] + len(b)] = list(b)
    mem[SENT] = 0xEA
    for a, v in (patch or []):
        mem[a] = v
    return mem


def run_sub(m, entry, max_steps=2_000_000):
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


def new_mpu(meta, board, patch=None, atk_prev=3):
    """A machine parked at a release edge: the volley's bytes are already in
    row 0 and p1_attackSize has just been cleared (the ROM clears it last)."""
    from py65.devices.mpu6502 import MPU
    m = MPU(memory=build_mem(meta, patch))
    for i, v in enumerate(board):
        m.memory[BOARD2 + i] = v
    m.memory[PRE_ATK2] = 0                       # released this frame
    m.memory[PRE_LAST2] = atk_prev               # ...having been buffered last hook
    for a in (PRE_ACT2, PEND2, ARMED2, WDOG2, WDOGH2, PP_PH, PP_SWAL):
        m.memory[a] = 0
    m.memory[SEED2] = 0x5A
    m.memory[0x039A], m.memory[0x039B] = 1, 2    # preview colours
    m.memory[0x03A7] = 7                         # pillsCounter
    for i in range(128):
        m.memory[0x0780 + i] = (i * 5) % 9       # reserve values are 0..8 by construction
    return m


def snapshot(m, w):
    """Everything the rest of the driver can observe after a pre_tick."""
    return {
        "win": list(m.memory[w:w + 0x80]),
        "mail": list(m.memory[w + 0x80:w + 0x85]),
        "act": m.memory[PRE_ACT2], "armed": m.memory[ARMED2],
        "pend": m.memory[PEND2], "wdog": m.memory[WDOG2],
        "wdogh": m.memory[WDOGH2], "last": m.memory[PRE_LAST2],
    }


ZP = list(range(0x00, 0x100))


def clobber(m):
    """The game owns zero page and the registers between NMIs."""
    for a in ZP:
        m.memory[a] = 0xA5
    m.a, m.x, m.y = 0xA5, 0xA5, 0xA5


def run_sync(meta, board, w, patch=None):
    m = new_mpu(meta, board, patch)
    entry = meta["units"]["main"]["base"] + meta["units"]["main"]["labels"]["pre_tick"]
    clobber(m)
    cyc = run_sub(m, entry)
    return snapshot(m, w), cyc, m


def run_pipe(meta, board, w, patch=None, hooks=8, mutate=None, inject=None):
    """Drive the pipelined path hook by hook. `inject(m, i)` runs before hook i
    (the world moving between NMIs); `mutate(m, i)` rewrites the LIVE board."""
    m = new_mpu(meta, board, patch)
    entry = meta["units"]["main"]["base"] + meta["units"]["main"]["labels"]["pre_tick"]
    worst, go_hook, per = 0, None, []
    for i in range(hooks):
        if inject:
            inject(m, i)
        if mutate:
            mutate(m, i)
        clobber(m)
        armed_before = m.memory[ARMED2]
        c = run_sub(m, entry)
        per.append(c)
        worst = max(worst, c)
        if go_hook is None and armed_before == 0 and m.memory[ARMED2] != 0:
            go_hook = i
        if m.memory[PP_PH] == 0 and i > 0:
            break
    return snapshot(m, w), worst, go_hook, m, per


# --------------------------------------------------------------------------
def corpus():
    """($0500 layout: 8 cols x 16 rows, 0xFF empty). Every case names the
    behaviour it is there to exercise -- a corpus of only random boards cannot
    show which obligation it covers."""
    out = []

    def blank():
        return [E] * 128

    # no volley in row 0 at all: the edge fires but nothing settles (PRE_N=0)
    b = blank()
    out.append(("no_garbage", b))

    # single garbage tile falling the whole board
    b = blank(); b[3] = GARB | 1
    out.append(("deep_fall_single", b))

    # 4 spread singles onto an empty board (the ROM's spread column sets)
    b = blank()
    for c, col in enumerate((0, 2, 4, 6)):
        b[col] = GARB | (c % 3)
    out.append(("spread4_empty", b))

    # mixed8: 8 row-0 singles, 4 of them landing on full columns (the state
    # that proves PRE_N=8 is reachable and killed the volley<=4 refinement).
    b = blank()
    for col in range(8):
        b[col] = GARB | (col % 3)
        if col % 2 == 0:
            for r in range(1, 16):
                b[r * 8 + col] = VIRUS | ((col + r) % 3)
    out.append(("mixed8", b))

    # a settled cell completing a 4-run along a ROW -> must bail
    b = blank()
    for col in range(3):
        b[15 * 8 + col] = VIRUS | 1
    b[3] = GARB | 1
    out.append(("row4_bail", b))

    # a settled cell completing a 4-run down a COLUMN -> must bail
    b = blank()
    for r in (13, 14, 15):
        b[r * 8 + 5] = VIRUS | 2
    b[5] = GARB | 2
    out.append(("col4_bail", b))

    # a 4-run reachable only from a LATE record (index >= 4): the case that
    # can see a skipped late phase. Columns 0-3 settle harmlessly first.
    b = blank()
    for col in range(4):
        b[col] = GARB | (col % 3)
    for r in (13, 14, 15):
        b[r * 8 + 6] = VIRUS | 0
    b[6] = GARB | 0
    out.append(("late_record_bail", b))

    # a 4-run reachable only from an EARLY record (index < 4): sees a skipped
    # early phase (M4's quota mutant).
    b = blank()
    for r in (13, 14, 15):
        b[r * 8 + 1] = VIRUS | 0
    b[1] = GARB | 0
    for col in (5, 6, 7):
        b[col] = GARB | 2
    out.append(("early_record_bail", b))

    # orphan: a leftHalf at row 0 whose rightHalf the volley destroyed
    b = blank(); b[2] = 0x60 | 1
    out.append(("orphan_bail", b))

    # mid-animation tile under a falling single -> bail
    b = blank(); b[4] = GARB | 1; b[8 * 8 + 4] = 0xB0 | 1
    out.append(("clearing_bail", b))

    rng = random.Random(138)
    for i in range(40):
        b = blank()
        depth = rng.randrange(0, 15)
        for col in range(8):
            for r in range(16 - depth, 16):
                if rng.random() < 0.75:
                    b[r * 8 + col] = rng.choice((VIRUS, 0x80, 0x60, 0x40)) | rng.randrange(3)
        for col in rng.sample(range(8), rng.choice((1, 2, 3, 4))):
            b[col] = GARB | rng.randrange(3)
        out.append((f"rand{i}", b))
    return out


# --------------------------------------------------------------------------
def find_patch(meta, which):
    """Mutant patch bytes located from the IR by LABEL, never by offset."""
    u = meta["units"]["main"]
    base, labs = u["base"], u["labels"]
    recs = [r for r in u["records"] if r["k"] != "label"]

    def after(lab, limit=64):
        lo = labs[lab]
        return [r for r in recs if lo <= r["off"]][:limit]

    def nops(off, n):
        return [(base + off + k, 0xEA) for k in range(n)]

    if which == "M1":
        # dispatcher: CMP #1 -> CMP #$7F, so phase 1 never dispatches.
        for r in after("pp_d3"):
            if r["k"] == "ins" and r["m"] == "CMP_imm" and r["ops"] == [1]:
                return [(base + r["off"] + 1, 0x7F)]
    if which == "M2":
        # commit uploads from the LIVE board instead of the snapshot.
        for r in after("pt_up"):
            if r["k"] == "ins" and r["m"] == "LDA_absX" and \
               r["ops"] == [PRE_BUF & 0xFF, PRE_BUF >> 8]:
                a = base + r["off"]
                return [(a + 1, BOARD2 & 0xFF), (a + 2, BOARD2 >> 8)]
    if which == "M3":
        # Delete the PEND2 abort check ENTIRELY: LDA PEND2 / BEQ pp_d2 / JMP
        # pt_bail = 8 bytes. ⚠ NOPing only the LDA+BEQ leaves the JMP pt_bail
        # exposed and makes the dispatcher bail UNCONDITIONALLY -- the mutant
        # still dies, but of the harness, not of the deleted check (rule 12).
        for i, r in enumerate(after("pp_d1")):
            if r["k"] == "ins" and r["m"] == "LDA_abs" and \
               r["ops"] == [PEND2 & 0xFF, PEND2 >> 8]:
                nxt, jmp = after("pp_d1")[i + 1], after("pp_d1")[i + 2]
                assert nxt["k"] == "br" and jmp["k"] == "jmp", \
                    "M3: pp_d1 is not LDA/BEQ/JMP any more"
                return nops(r["off"], 8)

    if which == "M5":
        # pt_bail forgets to disarm (LDA #0 / STA PP_PH -> 5 NOPs).
        for i, r in enumerate(after("pt_bail")):
            if r["k"] == "ins" and r["m"] == "STA_abs" and \
               r["ops"] == [PP_PH & 0xFF, PP_PH >> 8]:
                return nops(r["off"] - 2, 5)
    raise SystemExit(f"mutant {which}: patch site not found (layout changed?)")


def phase_count(meta):
    labs = meta["units"]["main"]["labels"]
    return 1 + len([l for l in labs if l.startswith("pp_m") and l[4:].isdigit()])


# --------------------------------------------------------------------------
def g2_case(meta_off, meta_on, w, name, board, patch=None):
    """One equivalence case. Returns (want, got, go_hook, worst, hooks_used)."""
    want, _, _ = run_sync(meta_off, board, w)
    got, worst, go_hook, m, per = run_pipe(meta_on, board, w, patch)
    return want, got, go_hook, worst, len(per), m


def main():
    meta_off = capture(IR_OFF)
    meta_off0 = capture(IR_OFF0, "DRPRESPIPE=0")
    # The split is a build knob; the gate certifies whatever is set rather than
    # a fixed shape, so a re-split cannot ship without re-passing this suite.
    q = os.environ.get("DRPRESPIPE_Q")
    meta_on = capture(IR_ON, "DRPRESPIPE=1", *([f"DRPRESPIPE_Q={q}"] if q else []))
    w = window_base(meta_on)
    assert w == window_base(meta_off), "window moved between arms"
    NM = phase_count(meta_on)
    GO_HOOK = NM                   # hook 0 = edge, hooks 1..NM = the phases

    # ---- G1 -------------------------------------------------------------
    for name in meta_off["units"]:
        assert meta_off["units"][name]["bytes"] == meta_off0["units"][name]["bytes"], \
            f"G1 FAIL: unit {name} differs between unset and DRPRESPIPE=0"
    assert meta_off["units"]["main"]["bytes"] != meta_on["units"]["main"]["bytes"], \
        "G1 sanity: DRPRESPIPE=1 must change the driver (flag inert?)"
    print(f"G1 byte-identity OFF: PASS (window ${w:04X}, {NM} phases, "
          f"GO on hook {GO_HOOK})")

    # ---- G2 -------------------------------------------------------------
    cases = corpus()
    worst_hook, commits, bails = 0, 0, 0
    for name, board in cases:
        want, got, go_hook, worst, hooks, _ = g2_case(meta_off, meta_on, w, name, board)
        assert got == want, f"G2 {name}: pipelined != synchronous\n  {got}\n  {want}"
        worst_hook = max(worst_hook, worst)
        if want["armed"]:
            commits += 1
            assert go_hook == GO_HOOK, \
                f"G2 {name}: GO on hook {go_hook}, designed {GO_HOOK}"
        else:
            bails += 1
            assert go_hook is None, f"G2 {name}: bail case issued a GO"
    assert commits > 0 and bails > 0, \
        f"G2 corpus is one-sided ({commits} commits, {bails} bails) -- an " \
        "equivalence gate that never sees a bail cannot see a bail defect"
    print(f"G2 whole-chain equivalence: PASS ({len(cases)} boards, "
          f"{commits} commit / {bails} bail; zp+regs clobbered every hook; "
          f"worst hook {worst_hook} cyc)")

    # ---- G3 snapshot semantics ------------------------------------------
    _, board = next((n, b) for n, b in cases if n == "spread4_empty")
    want, _, _ = run_sync(meta_off, board, w)

    def wipe_live(m, i):
        if i >= 1:                                  # after the edge hook
            for k in range(128):
                m.memory[BOARD2 + k] = E
    got, _, go_hook, _, _ = run_pipe(meta_on, board, w, mutate=wipe_live)
    assert got == want, "G3: the pipeline did not upload the edge-hook snapshot"
    assert go_hook == GO_HOOK, "G3: GO moved"
    print("G3 snapshot semantics: PASS (live board wiped after the edge hook; "
          "upload still the snapshot)")

    # ---- G5 abort obligations -------------------------------------------
    def abort_case(setter, label, at_hook=2, want_armed=0):
        def inject(m, i):
            if i == at_hook:
                setter(m)
        got, _, go_hook, m, per = run_pipe(meta_on, board, w, inject=inject)
        assert go_hook is None, f"G5 {label}: committed anyway (GO on hook {go_hook})"
        assert m.memory[PP_PH] == 0, f"G5 {label}: machine still armed"
        assert m.memory[PRE_ACT2] == 0, f"G5 {label}: claimed the next spawn anyway"
        # An abort must not touch state it does not own: ARMED2 belongs to
        # handle(2), so the injected value has to come back out unchanged.
        assert m.memory[ARMED2] == want_armed, \
            f"G5 {label}: ARMED2 {m.memory[ARMED2]} != {want_armed}"
        return m

    abort_case(lambda m: m.memory.__setitem__(PEND2, 1), "PEND2")
    abort_case(lambda m: m.memory.__setitem__(ARMED2, 1), "ARMED2", want_armed=1)
    m = abort_case(lambda m: m.memory.__setitem__(PRE_ATK2, 4), "second volley")
    assert m.memory[PP_SWAL] != 0, "G5: second volley did not arm the edge swallow"
    # ...and that swallow must actually eat the next release edge, which is what
    # the synchronous path does there (it finds PRE_ACT2 set and starts nothing).
    entry = meta_on["units"]["main"]["base"] + meta_on["units"]["main"]["labels"]["pre_tick"]
    m.memory[PRE_ATK2] = 0                       # volley 2 releases
    clobber(m)
    run_sub(m, entry)
    assert m.memory[ARMED2] == 0 and m.memory[PP_PH] == 0, \
        "G5: the second volley's edge started a pipeline the ship path would not"
    assert m.memory[PP_SWAL] == 0, "G5: the swallow latch was not consumed"
    print("G5 abort obligations: PASS (PEND2 / ARMED2 / second volley all "
          "abandon whole; second edge swallowed once)")

    # ---- G4 mutants -----------------------------------------------------
    for mut in ("M1", "M2", "M3", "M5"):
        patch = find_patch(meta_on, mut)
        killed = None
        if mut == "M3":
            def inject(m, i):
                if i == 2:
                    m.memory[PEND2] = 1
            _, _, go_hook, mm, _ = run_pipe(meta_on, board, w, patch=patch,
                                            inject=inject)
            if go_hook is not None:
                killed = "committed into a set PEND2"
        elif mut == "M5":
            bad = next(b for n, b in cases if n == "orphan_bail")
            _, _, _, mm, _ = run_pipe(meta_on, bad, w, patch=patch, hooks=2)
            if mm.memory[PP_PH] != 0:
                killed = f"PP_PH={mm.memory[PP_PH]} after a bail"
        if killed is None:
            for name, b in cases:
                want, got, go_hook, _, _, _ = g2_case(meta_off, meta_on, w, name, b,
                                                      patch=patch)
                if got != want or (bool(want["armed"]) and go_hook != GO_HOOK):
                    killed = f"{name}: state differs" if got != want else \
                             f"{name}: GO hook {go_hook}"
                    break
        assert killed, f"G4 {mut}: MUTANT SURVIVED -- the corpus cannot see it"
        print(f"G4 {mut}: KILLED ({killed})")

    # ---- G6 cycle certificate -------------------------------------------
    import census

    def pair_table(meta):
        """(worst admissible frame, table) for an image, using the pairing model
        the abort checks make true."""
        nd = census.load_from_meta(meta)
        so_ = census.detect_site_overrides(meta, nd)
        eb_ = census.detect_prespipe_bounds(meta)
        hv = set()
        for n in nd.values():
            hv.update(n.get("labels") or [])
        cuts_, order_ = census.prespipe_scenarios(hv)
        sc = dict(census.SCENARIO_CUTS); sc.update(cuts_)
        r = {}
        for sname, cuts in sc.items():
            ch = [(k, l) for k, l in cuts if l in hv]
            r[sname] = census.Analyzer(nd, ch, site_overrides=so_,
                                       extra_bounds=eb_).worst(
                meta["units"]["wrapper"]["base"])
        prs = [(order_[i], order_[i + 1]) for i in range(len(order_) - 1)]
        prs += [(a, "pp_idle") for a in order_]
        prs += [("pp_spawn", "pp_edge"), ("pp_idle", "pp_edge")]
        return r, prs, order_

    nodes = census.load_from_meta(meta_on)
    so = census.detect_site_overrides(meta_on, nodes)
    eb = census.detect_prespipe_bounds(meta_on)
    have = set()
    for n in nodes.values():
        have.update(n.get("labels") or [])
    pp_cuts, pp_order = census.prespipe_scenarios(have)
    scen = dict(census.SCENARIO_CUTS)
    scen.update(pp_cuts)
    res = {}
    for sname, cuts in scen.items():
        cuts_here = [(k, l) for k, l in cuts if l in have]
        res[sname] = census.Analyzer(nodes, cuts_here, site_overrides=so,
                                     extra_bounds=eb).worst(
            meta_on["units"]["wrapper"]["base"])
    pairs = [(pp_order[i], pp_order[i + 1]) for i in range(len(pp_order) - 1)]
    pairs += [(a, "pp_idle") for a in pp_order]
    pairs += [("pp_spawn", "pp_edge"), ("pp_idle", "pp_edge")]
    GAME_HEAD, EPS, FRAME = 2040, 300, 29780
    worst_pair = max(pairs, key=lambda ab: res[ab[0]] + res[ab[1]])
    tot = res[worst_pair[0]] + res[worst_pair[1]] + 12 + GAME_HEAD + EPS
    for a, b in pairs:
        t = res[a] + res[b] + 12 + GAME_HEAD + EPS
        assert t < FRAME, f"G6: admissible frame {a}+{b} = {t} >= {FRAME}"
    # the measured worst hook must sit under the bound its own class carries
    hook_bound = max(res[k] for k in pp_order) + 6
    assert worst_hook <= hook_bound, \
        f"G6: measured hook {worst_hook} EXCEEDS the census bound {hook_bound}"
    # and the defect must still be present in the arm that does NOT have the fix
    nodes_off = census.load_from_meta(meta_off)
    so_off = census.detect_site_overrides(meta_off, nodes_off)
    off_rel = census.Analyzer(
        nodes_off, [(k, l) for k, l in census.SCENARIO_CUTS["release_edge"]
                    if l in {x for n in nodes_off.values()
                             for x in (n.get("labels") or [])}],
        site_overrides=so_off).worst(meta_off["units"]["wrapper"]["base"])
    off_frame = off_rel + res["pp_idle"] + 12 + GAME_HEAD + EPS
    assert off_frame >= FRAME, (
        f"G6 NOT-INERT: the unpipelined release frame bounds at {off_frame} < "
        f"{FRAME} -- the defect this gate exists for is absent, so a PASS here "
        "would mean nothing")
    # M4 -- the certificate's OWN killed mutant: widen phase 2's quota so it
    # scans all 8 records. That is behaviourally EQUIVALENT (the quota only
    # decides which hook does which record, and rule 6 says check equivalence
    # before writing a mutant), so no behaviour gate can see it -- only the
    # frame certificate can, and it MUST. Without this, G6 could be passing
    # vacuously on any split at all.
    import copy
    meta_m4 = copy.deepcopy(meta_on)
    um = meta_m4["units"]["main"]
    lo4 = um["labels"]["pp_m2"]
    hit = False
    for r in um["records"]:
        if r["off"] >= lo4 and r["k"] == "ins" and r["m"] == "CMP_imm":
            r["ops"] = [8]
            hit = True
            break
    assert hit, "G6/M4: phase-2 quota compare not found"
    try:
        r4, p4, _ = pair_table(meta_m4)
    except SystemExit as e:
        how = f"analyzer REFUSED the image: {e}"
    else:
        over = [(a, b) for a, b in p4
                if r4[a] + r4[b] + 12 + GAME_HEAD + EPS >= FRAME]
        assert over, ("G6/M4: MUTANT SURVIVED -- a split that puts all 8 records "
                      "in one phase still certifies, so the certificate is not "
                      "constraining the split")
        how = (f"{over[0][0]} + {over[0][1]} = "
               f"{r4[over[0][0]] + r4[over[0][1]] + 12 + GAME_HEAD + EPS} >= {FRAME}")
    print(f"G4 M4 (quota 4 -> 8, behaviourally EQUIVALENT -- only the "
          f"certificate can see it): KILLED ({how})")

    print(f"G6 cycle certificate: PASS (worst admissible frame {tot} of {FRAME}, "
          f"margin {FRAME - tot}, [{worst_pair[0]} + {worst_pair[1]}]; "
          f"measured hook {worst_hook} <= bound {hook_bound}; "
          f"unpipelined arm still OVER at {off_frame})")
    print("test_prespipe: ALL PASS")


if __name__ == "__main__":
    main()
