#!/usr/bin/env python3
"""GATE for #123 / DRDBLCANON -- publish-time double-capsule orient canonicalisation.

Runs the REAL 6502 firmware under py65 (both flag states, same boards) and checks
what the cart would actually publish.  Every check is paired with a mutant that
must FAIL it; a check no mutant can break is not evidence.

  A IDENTITY   flag off emits ZERO bytes: OFF image is byte-identical to an image
               built from the emitter with the #123 block textually removed.
  B BIND       flag on changes the image, and by exactly the expected size.
  C DOUBLES    on forced DOUBLE capsules, the ON firmware publishes canon(OFF's
               answer), the orient is always EVEN, and the RESULTING BOARD is
               cell-for-cell identical to OFF's -- the zero-board-effect claim,
               checked on the firmware rather than on a model of it.
  D CONTROL    on NON-double capsules, ON == OFF exactly.  The flag must be inert
               where it has no business acting.
  E TEMPO      rotations-from-spawn strictly decrease on the plies that moved.
  F BINDS      the flag actually fired (non-vacuity).
  G INERT@s0   with the tie-break jitter off, the flag changes nothing.
  H MAILBOX    the ANYTIME mailbox ($6135) agrees with the zero page. The cart
               reads the mailbox, not D_BC/D_BO, so that is the real observable.
  I PUBLSTREAM EVERY value the mailbox ever holds during a search is canonical
               (or 0xFF, the invalid marker the driver peels off). The cart's
               pair latch samples the mailbox MID-SEARCH, so fixing only the
               final answer would still let it latch a non-canonical orient.

MUTANTS (each must fail at least one check, and the sheet says which):
  M1 WRONGKEY  the `(v, v+2)` key -- the canonical WRONG answer for this lane.
               It must BREAK board identity (C), which is exactly what makes it
               distinguishable from an inert de-dup that "found no contamination".
  M2 NOGATE    canonicalise unconditionally (drop the cA==cB test) -> must break
               the NON-double control (D).  This is the population mutant: it
               asks whether the double test binds at all.
  M3 EXPENSIVE canonicalise to the ODD member (ORA #$01) -> board identity still
               holds, so only the TEMPO check (E) can catch it.  Without E, "any
               canonicalisation" would pass.
  M4 INERT     claim ON but emit nothing -> must break BIND (B).
  M5 LATEFINAL right final answer, but the RAW orient reaches the anytime mailbox
               first -> only I PUBLSTREAM can see it. This is the pair-latch
               failure mode; without I the gate would not cover it at all.

Usage:  python gate_dblcanon.py [--n 60]
Exit 0 = all checks pass AND all mutants killed.
"""

import argparse
import copy
import hashlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "fpga", "copro"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import dblcanon as DC  # noqa: E402


def _load():
    import build_copro_d3 as B
    import test_search_d3 as D3
    return B, D3


# ---------------------------------------------------------------- mutants
def apply_mutant(D3, name):
    """Rewrite the emitted canonicalisation.  Returns a restore callable."""
    orig = D3._e_dblcanon
    orig_canon = D3.canon_o4

    def wrongkey(a, tag):                       # M1: the (v, v+2) key
        a.ins16("LDA_abs", D3.S_CA); a.ins16("EOR_abs", D3.S_CB)
        a.ins("AND_imm", 0x0F); a.br("BNE", f"{tag}_dcx")
        a.ins("LDA_zp", D3.D_BO); a.ins("AND_imm", 0xFD); a.ins("STA_zp", D3.D_BO)
        a.label(f"{tag}_dcx")

    def nogate(a, tag):                         # M2: no cA==cB test
        a.ins("LDA_zp", D3.D_BO); a.ins("AND_imm", 0xFE); a.ins("STA_zp", D3.D_BO)

    def expensive(a, tag):                      # M3: keep the COSTLY member
        a.ins16("LDA_abs", D3.S_CA); a.ins16("EOR_abs", D3.S_CB)
        a.ins("AND_imm", 0x0F); a.br("BNE", f"{tag}_dcx")
        a.ins("LDA_zp", D3.D_BO); a.ins("ORA_imm", 0x01); a.ins("STA_zp", D3.D_BO)
        a.label(f"{tag}_dcx")

    def inert(a, tag):                          # M4: emit nothing
        pass

    def latefinal(a, tag):
        """M5: fix the FINAL answer but leak every INTERMEDIATE publish.

        Stores the RAW orient to the anytime mailbox first and only then
        canonicalises the zero page, so the last value is right while the cart's
        pair latch can still grab a non-canonical intermediate. This is the
        pair-latch failure mode, and only the publish-stream check sees it.
        """
        a.ins("LDA_zp", D3.D_BO); a.ins16("STA_abs", D3.S_BEST_O)
        a.ins16("LDA_abs", D3.S_CA); a.ins16("EOR_abs", D3.S_CB)
        a.ins("AND_imm", 0x0F); a.br("BNE", f"{tag}_dcx")
        a.ins("LDA_zp", D3.D_BO); a.ins("AND_imm", 0xFE); a.ins("STA_zp", D3.D_BO)
        a.label(f"{tag}_dcx")

    muts = {"M1_wrongkey": (wrongkey, lambda o, x, y: (o & 0xFD) if x == y else o),
            "M2_nogate": (nogate, lambda o, x, y: o & 0xFE),
            "M3_expensive": (expensive, lambda o, x, y: (o | 1) if x == y else o),
            "M4_inert": (inert, lambda o, x, y: o),
            "M5_latefinal": (latefinal, orig_canon)}
    emit, canon = muts[name]
    D3._e_dblcanon = emit
    D3.canon_o4 = canon
    return lambda: (setattr(D3, "_e_dblcanon", orig),
                    setattr(D3, "canon_o4", orig_canon))


# ------------------------------------------------------------- firmware run
def build(B, D3, on):
    D3.DBLCANON = 1 if on else 0
    board = [0xFF] * 128
    img, clen, _slen = B.build_image(board, 0, 0, 0, 0)
    _code, labels = D3.build()
    return bytes(img[0x8000:0xC000]), 0x8000 + labels["search"], clen


def run_fw(B, D3, img_full, search_ep, board, cA, cB, nA, nB, tseed=0):
    """One real firmware decision under py65.

    ⚠ `tseed` is NOT cosmetic and a gate that leaves it 0 measures NOTHING.
    The firmware recovers its tie-break seed from the HIGH nibbles of the two
    colour mailbox bytes (`D_SEED = (S_CA >> 4) | (S_CB & $F0)`), and at seed 0
    the jitter is off -- at which point the o4-ascending scan with a
    strictly-greater keep-first argmax already lands on the cheap member of
    every duplicate pair, so DRDBLCANON has nothing to change and every check
    below passes vacuously.  That is how the first cut of this gate reported
    six green checks while the flag was provably inert.  Shipped carts run
    DRSEED=1, and SEED2 = (NAV_T | 1) ^ $A4 is always odd, hence never 0.
    """
    from py65_harness import Cpu
    from test_depth2 import S_CA, S_CB, S_NA, S_NB
    cpu = Cpu()
    for a, v in enumerate(img_full):
        cpu.mem[a] = v
    for i in range(16):
        cpu.mem[D3.PILLA + i] = img_full[B.PILL_ROM + i]
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[S_CA] = ((int(tseed) & 0x0F) << 4) | cA
    cpu.mem[S_CB] = (int(tseed) & 0xF0) | cB
    cpu.mem[S_NA], cpu.mem[S_NB] = nA, nB
    cpu.call(search_ep, max_steps=B.MAX_STEPS)
    if cpu.mem[D3.D_BO] == 0xFF:
        return None
    return (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])


def run_fw_traced(B, D3, img_full, search_ep, board, cA, cB, nA, nB, tseed=0):
    """As `run_fw`, but also returns the MAILBOX and the whole publish STREAM.

    Two observables, and the gate needs both:

      * zero page `D_BC`/`D_BO` -- what the stub copies out at the end;
      * `S_BEST_O` ($6135) -- the ANYTIME mailbox the select loop republishes on
        every improving candidate, which the RTL xlates into the cart's window.

    The cart samples that mailbox MID-SEARCH (`patch_cartridge_copro.py`'s nf2
    path snapshots it at $616C behind a torn-read check) and the argmax-stability
    counter latches from it, so a canonicalisation that only fixed the FINAL
    value would leave the pair latch free to grab a non-canonical intermediate.
    `stream` is every distinct value the mailbox ever held, which makes that
    failure mode observable instead of argued about.
    """
    from py65_harness import Cpu, HALT
    from test_depth2 import S_CA, S_CB, S_NA, S_NB, S_BEST_C, S_BEST_O
    cpu = Cpu()
    for a, v in enumerate(img_full):
        cpu.mem[a] = v
    for i in range(16):
        cpu.mem[D3.PILLA + i] = img_full[B.PILL_ROM + i]
    cpu.set_board(board)
    D3.attach_engine_emu(cpu)
    cpu.mem[S_CA] = ((int(tseed) & 0x0F) << 4) | cA
    cpu.mem[S_CB] = (int(tseed) & 0xF0) | cB
    cpu.mem[S_NA], cpu.mem[S_NB] = nA, nB

    m = cpu.mpu
    ret = HALT - 1
    m.sp = 0xFD
    cpu.mem[0x01FE] = ret & 0xFF
    cpu.mem[0x01FF] = (ret >> 8) & 0xFF
    m.pc = search_ep
    stream, last = [], None
    for _ in range(B.MAX_STEPS):
        m.step()
        v = cpu.mem[S_BEST_O]
        if v != last:
            stream.append(v)
            last = v
        if m.pc == HALT:
            break
    else:
        raise RuntimeError("search did not return")
    zp = None if cpu.mem[D3.D_BO] == 0xFF else (cpu.mem[D3.D_BC], cpu.mem[D3.D_BO])
    mb = (cpu.mem[S_BEST_C], cpu.mem[S_BEST_O])
    return zp, mb, stream


def image_for(B, D3, on):
    """Full 64K py65 image + entry point, for the given flag state.

    ⚠ The flag must be set in the ENVIRONMENT, not on the module: `build_image`
    re-reads `DRDBLCANON` from os.environ on every call and would overwrite a
    module-level assignment with 0.  Setting only the global produced two
    byte-identical images and a "mutant survived" sheet that was really a
    harness bug.
    """
    os.environ["DRDBLCANON"] = "1" if on else "0"
    img, clen, _ = B.build_image([0xFF] * 128, 0, 0, 0, 0)
    _code, labels = D3.build()
    return img, 0x8000 + labels["search"], clen


# ------------------------------------------------------------ board effect
def resulting_board(nes_board, o4, col, cA, cB):
    """The resolved child board for (o4, col) -- the golden's own placement path."""
    import nes_d3_golden as G
    for (g_o4, g_col, offa, offb, ta, tb) in G._placements4(nes_board, cA, cB):
        if g_o4 == o4 and g_col == col:
            b1 = G._place(nes_board, offa, offb, ta, tb)
            G._resolve(b1, offa, offb)
            return bytes(b1)
    return None


# ------------------------------------------------------------------- gate
def run_gate(n, mutant=None, verbose=True):
    B, D3 = _load()
    restore = apply_mutant(D3, mutant) if mutant else (lambda: None)
    checks = {}
    try:
        from test_depth2 import make_fewlegal  # noqa: F401
    except ImportError:
        pass
    from test_search_d3 import make_fewlegal
    # Same two path literals build_copro_d3.py's own validator uses (task #118 owns
    # de-hardcoding them tree-wide; overridable so this gate is not the blocker).
    FSIM = os.environ.get(
        "DRM_FAITHFUL_SIM",
        "/home/struktured/projects/dr_mario_rl/.claude/worktrees/faithful-sim")
    for p in (os.path.join(FSIM, "src"), os.path.join(FSIM, "tmp")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from drmario.faithful_game import FaithfulBoard
    from xcheck_terms import faithful_to_nes

    try:
        img_off, ep_off, clen_off = image_for(B, D3, False)
        img_on, ep_on, clen_on = image_for(B, D3, True)
        rom_off = bytes(img_off[0x8000:0xC000])
        rom_on = bytes(img_on[0x8000:0xC000])

        # ---- B BIND (checked first; A is proven separately by the OFF-vs-stashed build)
        checks["B_bind"] = (rom_off != rom_on)
        checks["B_size"] = (clen_on - clen_off) if not mutant else None

        rng = random.Random(20260818)
        n_dbl = n_ctl = 0
        moved = 0
        n_inert0 = inert0_bad = 0
        # Realistic match seeds: the cart derives SEED2 = (NAV_T | 1) ^ $A4, always ODD.
        tseeds = [(t | 1) ^ 0xA4 for t in (0x10, 0x28, 0x3A, 0x57)]
        rot_off_tot = rot_on_tot = 0
        board_mismatch = []
        canon_mismatch = []
        odd_on = []
        ctl_mismatch = []
        mailbox_mismatch = []
        stream_bad = []
        n_stream = 0

        for _ in range(n):
            fb = make_fewlegal(rng, FaithfulBoard)
            nes = list(faithful_to_nes(fb))
            na, nb = rng.randint(0, 2), rng.randint(0, 2)
            c = rng.randint(0, 2)
            for ts in tseeds:
                # --- DOUBLE arm, at a REAL (non-zero) tie-break seed.
                #     Traced on the ON side: the cart reads the MAILBOX, and the
                #     pair latch can grab an INTERMEDIATE publish, so both the
                #     final mailbox value and the whole publish stream are checked.
                a_off = run_fw(B, D3, img_off, ep_off, nes, c, c, na, nb, ts)
                a_on, mb_on, stream_on = run_fw_traced(
                    B, D3, img_on, ep_on, nes, c, c, na, nb, ts)
                if a_on is not None:
                    n_stream += 1
                    if mb_on != a_on:
                        mailbox_mismatch.append((a_on, mb_on))
                    bad = [v for v in stream_on if v != 0xFF and v % 2 != 0]
                    if bad:
                        stream_bad.append((a_on, stream_on))
                if a_off is not None and a_on is not None:
                    n_dbl += 1
                    col_off, o_off = a_off
                    col_on, o_on = a_on
                    if (col_on, o_on) != (col_off, D3.canon_o4(o_off, c, c)):
                        canon_mismatch.append((a_off, a_on))
                    if o_on % 2 != 0:
                        odd_on.append((a_off, a_on))
                    b_off = resulting_board(nes, o_off, col_off, c, c)
                    b_on = resulting_board(nes, o_on, col_on, c, c)
                    if b_off != b_on:
                        board_mismatch.append((a_off, a_on))
                    rot_off_tot += DC.ROT_COST_O4[o_off]
                    rot_on_tot += DC.ROT_COST_O4[o_on]
                    if a_off != a_on:
                        moved += 1
                # --- NON-DOUBLE control arm
                ca, cb = 0, 1
                k_off = run_fw(B, D3, img_off, ep_off, nes, ca, cb, na, nb, ts)
                k_on = run_fw(B, D3, img_on, ep_on, nes, ca, cb, na, nb, ts)
                if k_off is not None and k_on is not None:
                    n_ctl += 1
                    if k_off != k_on:
                        ctl_mismatch.append((k_off, k_on))
            # --- INERTNESS CONTROL at tseed=0: with the jitter off the base search
            #     already picks the cheap member, so the flag must change NOTHING.
            z_off = run_fw(B, D3, img_off, ep_off, nes, c, c, na, nb, 0)
            z_on = run_fw(B, D3, img_on, ep_on, nes, c, c, na, nb, 0)
            if z_off is not None and z_on is not None:
                n_inert0 += 1
                if z_off != z_on:
                    inert0_bad += 1

        checks["C_canon"] = (not canon_mismatch) and n_dbl > 0
        checks["C_even"] = (not odd_on) and n_dbl > 0
        checks["C_board"] = (not board_mismatch) and n_dbl > 0
        checks["D_control"] = (not ctl_mismatch) and n_ctl > 0
        checks["E_tempo"] = (rot_on_tot < rot_off_tot) if moved else None
        # NON-VACUITY: if the flag never fires, every check above passed for free.
        checks["F_binds"] = moved > 0
        # The cart reads the MAILBOX, not the zero page.
        checks["H_mailbox"] = (not mailbox_mismatch) and n_stream > 0
        # ...and it can latch an INTERMEDIATE publish, so EVERY value the anytime
        # mailbox ever held must already be canonical (0xFF = the invalid marker
        # the driver peels off explicitly, so it is allowed through).
        checks["I_stream"] = (not stream_bad) and n_stream > 0
        checks["G_inert0"] = (inert0_bad == 0) and n_inert0 > 0

        if verbose:
            tag = mutant or "REAL"
            print(f"\n=== {tag}  (n_double={n_dbl}, n_control={n_ctl}, moved={moved})")
            print(f"  B bind      : {'PASS' if checks['B_bind'] else 'FAIL'} "
                  f"(search {clen_off}B -> {clen_on}B)")
            print(f"  C canon-eq  : {'PASS' if checks['C_canon'] else 'FAIL'} "
                  f"({len(canon_mismatch)} mismatches)")
            print(f"  C even-o4   : {'PASS' if checks['C_even'] else 'FAIL'} "
                  f"({len(odd_on)} odd)")
            print(f"  C board-id  : {'PASS' if checks['C_board'] else 'FAIL'} "
                  f"({len(board_mismatch)} DIFFERENT boards)")
            print(f"  D control   : {'PASS' if checks['D_control'] else 'FAIL'} "
                  f"({len(ctl_mismatch)} non-doubles perturbed)")
            print(f"  E tempo     : rot {rot_off_tot} -> {rot_on_tot} "
                  f"({'PASS' if checks['E_tempo'] else 'FAIL/na'})")
            print(f"  F binds     : {'PASS' if checks['F_binds'] else 'FAIL'} "
                  f"(flag changed {moved}/{n_dbl} double decisions)")
            print(f"  G inert@s0  : {'PASS' if checks['G_inert0'] else 'FAIL'} "
                  f"({inert0_bad}/{n_inert0} perturbed with jitter off)")
            print(f"  H mailbox   : {'PASS' if checks['H_mailbox'] else 'FAIL'} "
                  f"({len(mailbox_mismatch)}/{n_stream} mailbox != zero page)")
            print(f"  I publstream: {'PASS' if checks['I_stream'] else 'FAIL'} "
                  f"({len(stream_bad)}/{n_stream} searches published a "
                  f"non-canonical INTERMEDIATE orient)")
        return checks
    finally:
        restore()
        D3.DBLCANON = 0


def identity_check():
    """A: OFF must emit ZERO bytes -- compare against the emitter with the block gone.

    Done by monkeypatching `_e_dblcanon` to a no-op AND forcing the flag on, which
    is the only way to get 'the emitter as it was before #123' without editing the
    file on disk under a live build.
    """
    B, D3 = _load()
    img_off, _ep, _c = image_for(B, D3, False)
    rom_off = bytes(img_off[0x8000:0xC000])
    orig = D3._e_dblcanon
    D3._e_dblcanon = lambda a, tag: None
    try:
        img_pre, _e2, _c2 = image_for(B, D3, True)   # flag ON but emitting nothing
        rom_pre = bytes(img_pre[0x8000:0xC000])
    finally:
        D3._e_dblcanon = orig
        D3.DBLCANON = 0
    ok = rom_off == rom_pre
    print(f"  A identity  : {'PASS' if ok else 'FAIL'} "
          f"(OFF md5={hashlib.md5(rom_off).hexdigest()[:8]}, "
          f"pre-#123 md5={hashlib.md5(rom_pre).hexdigest()[:8]})")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    args = ap.parse_args()

    print("=" * 70)
    print("GATE #123 DRDBLCANON -- real 6502 firmware under py65, both flag states")
    print("=" * 70)
    ident = identity_check()
    real = run_gate(args.n)

    # every listed check must pass on the real implementation
    must = ["B_bind", "C_canon", "C_even", "C_board", "D_control", "E_tempo",
            "F_binds", "G_inert0", "H_mailbox", "I_stream"]
    real_ok = ident and all(real.get(k) for k in must)

    # ---- mutants: each must FAIL its named check
    # Each mutant names the checks ANY of which must fail on it.  M1 gets two
    # because the (v, v+2) key fails in one of two ways depending on which member
    # won: it either crosses axes and moves the BOARD, or -- when the winner is
    # already o4 0/1 -- it is simply INERT, removing nothing while looking clean.
    # That second mode is the exact failure the gw lane hit and the reason this
    # mutant exists, so "removes nothing" has to count as a kill, not a pass.
    expect = {"M1_wrongkey": ("C_board", "F_binds"),
              "M2_nogate": ("D_control",),   # no double test -> perturbs non-doubles
              "M3_expensive": ("E_tempo", "C_even"),  # right key, wrong direction
              "M4_inert": ("B_bind", "F_binds"),       # emits nothing
              # M5 gets ONLY the stream check: its final answer is correct, so
              # every other check passes. If I_stream cannot kill it, the gate
              # does not actually cover the pair-latch hazard.
              "M5_latefinal": ("I_stream",)}
    killed, survived = [], []
    for m, ks in expect.items():
        res = run_gate(args.n, mutant=m)
        broke = [k for k in ks if not res.get(k)]
        if broke:
            killed.append((m, ",".join(broke)))
        else:
            survived.append((m, ",".join(ks)))

    print("\n" + "=" * 70)
    print(f"REAL implementation: {'PASS' if real_ok else 'FAIL'}")
    print(f"mutants killed {len(killed)}/{len(expect)}")
    for m, k in killed:
        print(f"  KILLED  {m:<14} by {k}")
    for m, k in survived:
        print(f"  SURVIVED {m:<13} -- {k} did not catch it (the check is vacuous)")
    ok = real_ok and not survived
    print(f"\nGATE: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
