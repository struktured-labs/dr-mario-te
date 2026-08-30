#!/usr/bin/env python3
"""GATE for DRVETO -- the spawn-plug veto, variant (a+), against dblcanon b03a586e.

Runs the REAL 6502 firmware under py65 (both flag states) against a Python mirror
that models the veto bit-for-bit (test_search_d3.veto_plug / veto_val + a verbatim
replica of nes_d3_golden.decide_d3's candidate loop).  Pattern: gate_dblcanon.py.
Every check is paired with a mutant that must FAIL it.

  A IDENTITY   DRVETO=0 emits ZERO bytes (image == emitter with the blocks no-op'd).
               The b03a586e byte-identity itself is proven outside this gate by
               build_dbgpub + cmp (tmp/drveto/veto0.hex).
  B BIND       DRVETO=1 changes the image; size delta reported.
  C PARITY     firmware(ON) == mirror(ON) and firmware(OFF) == mirror(OFF) on
               (i) the standard corpus (make_fewlegal) and (ii) a synthesized
               veto-exercising set covering both sides of every threshold:
               fo 1/2/3 x vertical/horizontal x span cols 1..5 x rv 0/nonzero x
               no-virus parent x fully-plugged parent.
  D CONTROL    on the standard corpus (no plug geometry), ON == OFF exactly.
  E FIRES      the veto predicate fires in the mirror on the synth plug cases
               (non-vacuity) and ON != OFF on at least one board.
  F NOTE-A     the fully-plugged-parent board still returns a decision (never an
               empty argmax), firmware and mirror alike.

MUTANTS (each must fail at least one check):
  M1_FOBOUND   vertical arm reads fo<=3 (adds the row-3 cell) -- the wrong-fo-bound
               mutant the task names.  Must break C PARITY on the V-fo3 threshold
               board (it vetoes a legal non-plugging vertical).
  M2_OCAND     the C1 trap: the whole predicate (incl. LEV_RVC/LEV_WIN_R reads)
               moved to o_cand, where the ply-2 loop has already overwritten the
               result regs.  Must break C PARITY on the rv-nonzero synth case
               (stale rv==0 -> it vetoes a CLEARING plug the spec exempts).
  M3_INERT     claims ON but emits nothing.  Must break B BIND and E FIRES.

Usage: gate_drveto.py [--n 40] [--fast]
Exit 0 = all checks pass AND all mutants killed.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

# The dblcanon b03a586e recipe env (FW_RECIPES.json s20t3_th400dblcanon), minus the
# tuck knobs' effect on the SEARCH bytes (none -- tuck lives at $9000+, the direct
# search call never reaches it).  Set BEFORE importing the builders.
RECIPE_ENV = {"DRSTRAND": "20", "DRCHAIN": "180", "DRCOPRO_ARM": "1", "DRFIX": "1",
              "DRCOPRO_TUCKBFS": "1", "DRCOPRO_TUCKBFS_TIER3": "1",
              "DRCOPRO_TUCKV3_THETA": "400", "DRDBLCANON": "1",
              "DRCOPRO_TUCKV3_FIXSLOT": "1"}
os.environ.update(RECIPE_ENV)


def _load():
    import build_copro_d3 as B
    import test_search_d3 as D3
    assert D3.__file__.startswith(os.path.join(ROOT, "tests")), D3.__file__
    return B, D3


def image_for(B, D3, on):
    """Full 64K py65 image + entry point.  DRVETO must be set in the ENVIRONMENT:
    build_image re-reads it on every call (same trap gate_dblcanon documents)."""
    os.environ["DRVETO"] = "1" if on else "0"
    img, clen, _ = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    _code, labels = D3.build()
    return img, 0x8000 + labels["search"], clen


def run_fw(B, D3, img_full, search_ep, board, cA, cB, nA, nB, tseed=0, fired=None):
    """One real firmware decision under py65.  `fired` (optional list) collects the
    (col, o4) of every root candidate whose D_VETO flag the firmware set to 1 --
    the firing-SET observable that makes flag-level parity checkable (and kills
    the fo-bound and inert mutants deterministically, independent of the argmax)."""
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
    if fired is not None:
        base = cpu.mem                      # the engine-emu ObservableMemory
        obs = ObservableMemory(subject=base)

        def on_veto(addr, value):
            base[addr] = value
            if value == 1:
                fired.append((base[D3.D_C1], base[D3.D_O1]))

        obs.subscribe_to_write([D3.D_VETO], on_veto)
        cpu.mpu.memory = obs
        cpu.mem = obs
    cpu.mem[S_CA] = ((int(tseed) & 0x0F) << 4) | cA
    cpu.mem[S_CB] = (int(tseed) & 0xF0) | cB
    cpu.mem[S_NA], cpu.mem[S_NB] = nA, nB
    cpu.call(search_ep, max_steps=B.MAX_STEPS)
    if cpu.mem[D3.D_BO] == 0xFF:
        return None
    return (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])


# --------------------------------------------------------------------- mirror
def g_stranded(b):
    """#47 stranded-half count -- byte-identical to attach_engine_emu's CMD-8 model
    (which is the tb_strand-200/200-verified mirror of the RTL scan).  Needed here
    because the SHIP recipe carries DRSTRAND=20 and the o_cand subtraction happens
    on every root candidate; a mirror without it diverges from the real firmware
    (this gate found exactly that on its first run -- the prior gates never built
    with the recipe env, so the golden never needed the term)."""
    n8 = 0
    for i in range(128):
        v = b[i]
        if v == 0xFF or (v & 0xF0) == 0xD0:
            continue
        k = v & 0x0F
        same = False
        for j, cond in ((i - 8, i >= 8), (i + 8, i <= 119),
                        (i - 1, (i & 7) != 0), (i + 1, (i & 7) != 7)):
            if cond and b[j] != 0xFF and (b[j] & 0x0F) == k:
                same = True
                break
        if not same:
            n8 += 1
    return n8


def decide_mirror(D3, board, pA, pB, nA, nB, seed, veto=True, fired_out=None):
    """VERBATIM replica of nes_d3_golden.decide_d3 (as configured by build_image:
    DISC_SHIFT=1, EXCAV_HANG_PLY1, topk1=32, topk2=8, THIRD pills) with the DRVETO
    (a+) veto inserted exactly where the firmware applies it: geometry+rv+win+
    viruses-remain decided per root candidate at its own CMD-4 result (C1), the
    penalty applied to val1 BEFORE the jitter, 16-bit-saturating (veto_val).
    Returns the (col, o4) the ZERO PAGE would hold, pre-DBLCANON-publish-rewrite;
    the caller applies canon_o4 for comparison, exactly like build_copro_d3's own
    validator (_expect)."""
    import nes_d3_golden as G
    pills3 = D3.THIRD
    topk1, topk2 = D3.TOPK1, 8
    first = []
    for (o4, col, offa, offb, ta, tb) in G._placements4(board, pA, pB):
        b1 = G._place(board, offa, offb, ta, tb)
        cells1, vir1 = G._resolve(b1, offa, offb)
        imm1 = G._imm(cells1, vir1)
        first.append((imm1 + G.leaf_d3(b1), imm1, b1, col, o4, cells1))
    if not first:
        return None
    first.sort(key=lambda t: t[0], reverse=True)
    shortlist = first[:topk1] if topk1 > 0 else first
    parent_has_virus = G._virus_count(board) > 0
    best_val = None
    best_key = None
    for (_k1, imm1, b1, col, o4, cells1) in shortlist:
        win1 = _virus_count_of(G, b1) == 0
        v_fire = (veto and not win1 and cells1 == 0 and parent_has_virus
                  and D3.veto_plug(board, o4, col))
        if win1:
            val = imm1 + G.WIN
        else:
            second = []
            for (_o2, _c2, oa2, ob2, ta2, tb2) in G._placements4(b1, nA, nB):
                b2 = G._place(b1, oa2, ob2, ta2, tb2)
                cells2, vir2 = G._resolve(b2, oa2, ob2)
                imm2 = G._imm(cells2, vir2)
                second.append((imm2 + G.leaf_d3(b2), imm2, b2))
            if not second:
                val = imm1 + G.leaf_d3(b1)
            else:
                second.sort(key=lambda t: t[0], reverse=True)
                keep = second[:topk2] if topk2 > 0 else second
                best2 = None
                for (_k2, imm2, b2) in keep:
                    if _virus_count_of(G, b2) == 0:
                        v2 = imm2 + G.WIN
                    else:
                        tot = 0
                        for (x, y) in pills3:
                            best3 = None
                            for (_o3, _c3, oa3, ob3, ta3, tb3) in G._placements4(b2, x, y):
                                b3 = G._place(b2, oa3, ob3, ta3, tb3)
                                cells3, vir3 = G._resolve(b3, oa3, ob3)
                                v3 = G._imm(cells3, vir3) + G.leaf_d3(b3)
                                if best3 is None or v3 > best3:
                                    best3 = v3
                            tot += best3 if best3 is not None else G.leaf_d3(b2)
                        v2 = imm2 + tot // len(pills3)
                    if best2 is None or v2 > best2:
                        best2 = v2
                if G.DISC_SHIFT is None:
                    val = imm1 + best2
                else:
                    leaf1_ = _k1 - imm1
                    val = imm1 + leaf1_ + ((best2 - leaf1_) >> G.DISC_SHIFT)
                if G.EXCAV_HANG_PLY1:
                    val += G.W_EXCAV * G.g_excav(b1) + G._hang_credit(b1)
        if D3.DRSTRAND:
            # o_cand: val1 -= DRSTRAND * stranded(resolved b1), unconditional (all
            # paths JMP through o_cand), BEFORE the veto penalty and the jitter.
            val -= D3.DRSTRAND * g_stranded(b1)
        if v_fire:
            val = D3.veto_val(val)
            if fired_out is not None:
                fired_out.append((col, o4))
        val += G._jitter(seed, o4, col)
        if best_val is None or val > best_val:
            best_val = val
            best_key = (col, o4)
    return best_key


def _virus_count_of(G, b):
    return G._virus_count(b)


# -------------------------------------------------------------------- mutants
def apply_mutant(D3, name):
    orig = D3._e_veto_flag
    if name is None:
        return lambda: None

    # M1 needs a full replacement emitter (labels are global/one-shot), so rebuild it
    # from the same code with the extra row-3 read in the vertical arm.
    def fobound_full(a):
        D = D3
        a.ins("LDA_imm", 0); a.ins("STA_zp", D.D_VETO)
        a.ins16("LDA_abs", D.LEV_WIN_R); a.br("BNE", "vt_no")
        a.ins16("LDA_abs", D.LEV_RVC); a.br("BNE", "vt_no")
        a.ins("LDA_zp", D.D_VIRF); a.br("BEQ", "vt_no")
        a.ins16("LDA_abs", D.LIVE + 3); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.ins16("LDA_abs", D.LIVE + 4); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.ins("LDA_zp", D.D_O1); a.ins("AND_imm", 0x02); a.br("BNE", "vt_h")
        a.ins("LDA_zp", D.D_C1); a.ins("CMP_imm", 3); a.br("BEQ", "vt_v")
        a.ins("CMP_imm", 4); a.br("BEQ", "vt_v")
        a.jmp("vt_no")
        a.label("vt_v")
        a.ins("LDX_zp", D.D_C1)
        a.ins16("LDA_absX", D.LIVE); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.ins16("LDA_absX", D.LIVE + 8); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.ins16("LDA_absX", D.LIVE + 16); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.ins16("LDA_absX", D.LIVE + 24); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")  # WRONG: fo<=3
        a.jmp("vt_no")
        a.label("vt_h")
        a.ins("LDA_zp", D.D_C1); a.ins("CMP_imm", 2); a.br("BCC", "vt_no")
        a.ins("CMP_imm", 5); a.br("BCS", "vt_no")
        a.ins("TAX")
        a.ins16("LDA_absX", D.LIVE); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_no")
        a.ins16("LDA_absX", D.LIVE + 1); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_no")
        a.ins16("LDA_absX", D.LIVE + 8); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.ins16("LDA_absX", D.LIVE + 9); a.ins("CMP_imm", 0xFF); a.br("BNE", "vt_yes")
        a.jmp("vt_no")
        a.label("vt_yes"); a.ins("LDA_imm", 1); a.ins("STA_zp", D.D_VETO)
        a.label("vt_no")

    def inert(a):                          # M3: emits nothing at the root-replay site
        pass

    if name == "M1_fobound":
        D3._e_veto_flag = fobound_full
        return lambda: setattr(D3, "_e_veto_flag", orig)
    if name == "M3_inert":
        # kill ALL three emissions: flag read, virus scan and penalty are gated on
        # DRVETO, so the honest inert mutant sets the emitter to no-op AND leaves
        # DRVETO=1 claimed.  The virus scan + penalty still emit (they are inline,
        # not routed through _e_veto_flag) -- but D_VETO is never set, so the
        # penalty never fires: behaviourally inert, catchable only by E FIRES (and
        # partially by B BIND's size expectation).
        D3._e_veto_flag = inert
        return lambda: setattr(D3, "_e_veto_flag", orig)
    if name == "M2_ocand":
        # C1 trap made real: the emitter honours the test-only _VETO_AT_OCAND hook,
        # which moves the WHOLE predicate (incl. the LEV_RVC/LEV_WIN_R reads) to
        # o_cand -- after the ply-2 loop has overwritten the result regs.
        D3._VETO_AT_OCAND = True

        def restore():
            D3._VETO_AT_OCAND = False
        return restore
    raise KeyError(name)


# ------------------------------------------------------------------ synth set
V, J = 0xD0, 0x00   # virus / junk high nibbles


def _empty():
    return [0xFF] * 128


def _fill_col(b, col, fo, colors):
    """Occupy rows fo..15 of `col` cycling `colors` (list of (hi, lo) tuples)."""
    for i, r in enumerate(range(fo, 16)):
        hi, lo = colors[i % len(colors)]
        b[r * 8 + col] = hi | lo


CYC = [(J, 2), (J, 0), (J, 1)]      # 3-colour cycle: no vertical runs
CYC2 = [(J, 0), (J, 1), (J, 2)]     # phase-shifted for adjacent columns


def synth_cases():
    """(name, board, (cA,cB,nA,nB), expect_fire) -- both sides of every threshold.
    Side columns 0/1/6/7 are FILLED to keep the py65 candidate count (and hence
    runtime) small without touching the throat geometry; a virus rides inside the
    col-0 fill so viruses remain.  Pill colours are chosen so plug candidates
    resolve NOTHING unless the case says otherwise."""
    cases = []

    def base(open_cols=()):
        b = _empty()
        for c in (0, 1, 6, 7):
            if c in open_cols:
                continue
            _fill_col(b, c, 0, CYC if c in (0, 6) else CYC2)
        b[15 * 8 + 0] = V | 2       # virus, same colour slot the fill cycle put there
        return b

    b = base(); _fill_col(b, 3, 2, CYC * 6)
    cases.append(("V_fo2_c3", b, (0, 0, 1, 1), True))      # vertical col3 plugs rows 0-1

    b = base(); _fill_col(b, 3, 3, CYC * 6)
    cases.append(("V_fo3_c3", b, (0, 0, 1, 1), False))     # lands rows 1-2: NO plug

    b = base(); _fill_col(b, 4, 2, CYC * 6)
    cases.append(("V_fo2_c4", b, (0, 0, 1, 1), True))

    b = base(); _fill_col(b, 2, 2, CYC * 6)
    cases.append(("V_fo2_c2", b, (0, 0, 1, 1), False))     # col 2: not the throat

    b = base(); _fill_col(b, 3, 1, CYC * 5)
    cases.append(("H_min1_c3", b, (0, 0, 1, 1), True))     # H 2-3 and 3-4 rest at row 0

    b = base(); _fill_col(b, 3, 2, [(J, 0), (J, 1)] * 7); _fill_col(b, 4, 2, [(J, 2), (J, 1)] * 7)
    cases.append(("H_min2_c34", b, (0, 0, 1, 1), True))    # H rests row1 (no fire) but V c3/c4 plug

    b = base(); _fill_col(b, 2, 1, CYC * 5)
    cases.append(("H_min1_c2", b, (0, 0, 1, 1), True))     # span 2-3 plugs (0,3)

    b = base(); _fill_col(b, 5, 1, CYC * 5)
    cases.append(("H_min1_c45", b, (0, 0, 1, 1), True))    # span 4-5 plugs (0,4)

    b = base(open_cols=(1,)); _fill_col(b, 1, 1, CYC * 5)
    cases.append(("H_min1_c1", b, (0, 0, 1, 1), False))    # spans 0-1/1-2: NO throat cell

    # rv-nonzero: the vertical col3 plug CLEARS (4-run of colour 0 incl. a virus)
    # -> spec exempts it.  M2_ocand's killer: o_cand-site reads see a stale rv==0
    # from the ply-2 loop and veto it anyway.
    b = base()
    b[2 * 8 + 3] = J | 0; b[3 * 8 + 3] = V | 0
    _fill_col(b, 3, 4, [(J, 2), (J, 1)] * 6)
    cases.append(("RV_clear_c3", b, (0, 0, 1, 1), False))

    # no-virus parent: every resolved board wins -> veto must never fire
    b = _empty()
    for c in (0, 1, 6, 7):
        _fill_col(b, c, 0, CYC if c in (0, 6) else CYC2)
    _fill_col(b, 3, 2, CYC * 6)
    cases.append(("NOVIRUS", b, (0, 0, 1, 1), False))

    # fully-plugged parent (note A): (0,3) occupied, a decision must still emerge
    b = base(); _fill_col(b, 3, 0, CYC * 6)
    cases.append(("PLUGGED_PARENT", b, (0, 0, 1, 1), True))

    # forced-divergence: only cols 3/4 open, both fo=2 -> all four verticals plug
    # (and clear nothing); the horizontals rest at row 1 and are the sole
    # un-vetoed candidates, so DRVETO=1 must abandon the verticals.
    b = base()
    for c in (2, 5):
        _fill_col(b, c, 0, CYC if c == 2 else CYC2)
    _fill_col(b, 3, 2, [(J, 0), (J, 1)] * 7)
    _fill_col(b, 4, 2, [(J, 2), (J, 1)] * 7)
    cases.append(("FORCED_DIVERGE", b, (0, 0, 1, 1), True))

    # forced fo=3 twin (M1_fobound's killer): only cols 3/4 open at fo=3 -- nothing
    # plugs, the correct veto is fully inert; the fo<=3 mutant vetoes every vertical.
    b = base()
    for c in (2, 5):
        _fill_col(b, c, 0, CYC if c == 2 else CYC2)
    _fill_col(b, 3, 3, [(J, 0), (J, 1)] * 7)
    _fill_col(b, 4, 3, [(J, 2), (J, 1)] * 7)
    cases.append(("FORCED_FO3", b, (0, 0, 1, 1), False))
    return cases


# ---------------------------------------------------------------------- gate
def run_gate(n, mutant=None, verbose=True, fast=False):
    B, D3 = _load()
    restore = apply_mutant(D3, mutant)
    checks = {}
    from test_search_d3 import make_fewlegal
    FSIM = os.environ.get(
        "DRM_FAITHFUL_SIM",
        "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim")
    for p in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes
    import random

    try:
        img_off, ep_off, clen_off = image_for(B, D3, False)
        img_on, ep_on, clen_on = image_for(B, D3, True)
        checks["B_bind"] = bytes(img_off[0x8000:0xC000]) != bytes(img_on[0x8000:0xC000])
        size_delta = clen_on - clen_off

        tseeds = [0, (0x10 | 1) ^ 0xA4, (0x3A | 1) ^ 0xA4] if not fast else [(0x10 | 1) ^ 0xA4]
        par_std = par_synth = 0
        mis_std, mis_synth = [], []
        ctl_mismatch = []
        fires = 0
        moved = 0
        notea_ok = True

        def expect(board, cA, cB, nA, nB, ts, veto, fired=None):
            # D_SEED = (S_CA>>4) | (S_CB&F0) = ts exactly, given colors < 4
            k = decide_mirror(D3, board, cA, cB, nA, nB, ts & 0xFF, veto=veto,
                              fired_out=fired)
            if k is None:
                return None
            col, o4 = k
            return (col, D3.canon_o4(o4, cA, cB))

        # ---- standard corpus (parity everywhere; ON==OFF control only on boards
        #      where the mirror veto never fired -- make_fewlegal's six FULL columns
        #      often plug (0,3)/(0,4), where firing is exactly per-spec note A)
        std_flag_mismatch = []
        rng = random.Random(20260830)
        for _ in range(n):
            fb = make_fewlegal(rng, FaithfulBoard)
            nes = list(faithful_to_nes(fb))
            cA, cB = rng.randint(0, 2), rng.randint(0, 2)
            nA, nB = rng.randint(0, 2), rng.randint(0, 2)
            for ts in tseeds:
                f_fired, m_fired = [], []
                g_on = run_fw(B, D3, img_on, ep_on, nes, cA, cB, nA, nB, ts,
                              fired=f_fired)
                e_on = expect(nes, cA, cB, nA, nB, ts, True, m_fired)
                g_off = run_fw(B, D3, img_off, ep_off, nes, cA, cB, nA, nB, ts)
                e_off = expect(nes, cA, cB, nA, nB, ts, False)
                par_std += 1
                if g_on != e_on or g_off != e_off:
                    mis_std.append((nes, cA, cB, nA, nB, ts, g_on, e_on, g_off, e_off))
                if sorted(set(f_fired)) != sorted(set(m_fired)):
                    std_flag_mismatch.append((ts, sorted(set(f_fired)),
                                              sorted(set(m_fired))))
                if not m_fired and g_on != g_off:
                    ctl_mismatch.append((g_on, g_off))

        # ---- synthesized veto-exercising set
        flag_mismatch = []
        exp_fire_bad = []
        for (name, board, (cA, cB, nA, nB), exp_fire) in synth_cases():
            for ts in tseeds:
                m_fired, f_fired = [], []
                g_on = run_fw(B, D3, img_on, ep_on, board, cA, cB, nA, nB, ts,
                              fired=f_fired)
                e_on = expect(board, cA, cB, nA, nB, ts, True, m_fired)
                g_off = run_fw(B, D3, img_off, ep_off, board, cA, cB, nA, nB, ts)
                e_off = expect(board, cA, cB, nA, nB, ts, False)
                par_synth += 1
                if g_on != e_on or g_off != e_off:
                    mis_synth.append((name, ts, g_on, e_on, g_off, e_off))
                if sorted(set(f_fired)) != sorted(set(m_fired)):
                    flag_mismatch.append((name, ts, sorted(set(f_fired)),
                                          sorted(set(m_fired))))
                if bool(m_fired) != exp_fire:
                    exp_fire_bad.append((name, ts, m_fired))
                fires += len(m_fired)
                if g_on != g_off:
                    moved += 1
                if name == "PLUGGED_PARENT" and (g_on is None or e_on is None):
                    notea_ok = False

        checks["C_parity_std"] = not mis_std and par_std > 0
        checks["C_parity_synth"] = not mis_synth and par_synth > 0
        checks["C_flag"] = (not flag_mismatch and not std_flag_mismatch
                            and par_synth > 0)
        checks["C_expfire"] = not exp_fire_bad
        checks["D_control"] = not ctl_mismatch and par_std > 0
        checks["E_fires"] = fires > 0 and moved > 0
        checks["F_notea"] = notea_ok

        if verbose:
            tag = mutant or "REAL"
            print(f"\n=== {tag}  (std={par_std} synth={par_synth} decisions)")
            print(f"  B bind        : {'PASS' if checks['B_bind'] else 'FAIL'} "
                  f"(search {clen_off}B -> {clen_on}B, +{size_delta}B)")
            print(f"  C parity std  : {'PASS' if checks['C_parity_std'] else 'FAIL'} "
                  f"({len(mis_std)} mismatches)")
            print(f"  C parity synth: {'PASS' if checks['C_parity_synth'] else 'FAIL'} "
                  f"({len(mis_synth)} mismatches: {[m[0] for m in mis_synth][:6]})")
            print(f"  C flag-set    : {'PASS' if checks['C_flag'] else 'FAIL'} "
                  f"({len(flag_mismatch)} synth + {len(std_flag_mismatch)} std "
                  f"firing-set mismatches: {[m[0] for m in flag_mismatch][:6]})")
            print(f"  C exp-fire    : {'PASS' if checks['C_expfire'] else 'FAIL'} "
                  f"({len(exp_fire_bad)} cases fired!=expected: "
                  f"{[m[0] for m in exp_fire_bad][:6]})")
            print(f"  D control     : {'PASS' if checks['D_control'] else 'FAIL'} "
                  f"({len(ctl_mismatch)} FIRE-FREE std boards where ON != OFF)")
            print(f"  E fires       : {'PASS' if checks['E_fires'] else 'FAIL'} "
                  f"(mirror fired {fires}x, ON!=OFF on {moved} synth decisions)")
            print(f"  F note-A      : {'PASS' if checks['F_notea'] else 'FAIL'} "
                  f"(plugged parent still decides)")
        return checks
    finally:
        restore()
        D3.DRVETO = 0
        os.environ["DRVETO"] = "0"


def identity_check():
    """A: OFF emits ZERO bytes -- flag ON with all three emissions no-op'd must be
    byte-identical to flag OFF.  The virus scan + penalty are inline, so this uses
    the test-only _VETO_SUPPRESS hook the emitter honours (no-op unless set)."""
    B, D3 = _load()
    img_off, _e, _c = image_for(B, D3, False)
    D3._VETO_SUPPRESS = True
    try:
        img_pre, _e2, _c2 = image_for(B, D3, True)
    finally:
        D3._VETO_SUPPRESS = False
        os.environ["DRVETO"] = "0"
    ok = bytes(img_off[0x8000:0xC000]) == bytes(img_pre[0x8000:0xC000])
    print(f"  A identity  : {'PASS' if ok else 'FAIL'} (ON+suppressed == OFF)")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print("GATE DRVETO -- real 6502 firmware under py65 vs bit-exact mirror")
    print("=" * 70)
    ident = identity_check()
    real = run_gate(args.n, fast=args.fast)
    must = ["B_bind", "C_parity_std", "C_parity_synth", "C_flag", "C_expfire",
            "D_control", "E_fires", "F_notea"]
    real_ok = ident and all(real.get(k) for k in must)

    expect = {"M1_fobound": ("C_parity_synth", "C_flag"),
              "M2_ocand": ("C_parity_synth", "C_flag"),
              "M3_inert": ("E_fires", "C_flag")}
    killed, survived = [], []
    for m, ks in expect.items():
        res = run_gate(args.n if not args.fast else 4, mutant=m, fast=True)
        broke = [k for k in ks if not res.get(k)]
        (killed if broke else survived).append((m, ",".join(broke or ks)))

    print("\n" + "=" * 70)
    print(f"REAL implementation: {'PASS' if real_ok else 'FAIL'}")
    print(f"mutants killed {len(killed)}/{len(expect)}")
    for m, k in killed:
        print(f"  KILLED   {m:<12} by {k}")
    for m, k in survived:
        print(f"  SURVIVED {m:<12} -- {k} did not catch it")
    ok = real_ok and not survived
    print(f"\nGATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
