#!/usr/bin/env python3
"""gate_verfix_sim.py -- offline battery for the #129 DRVERFIX stock fix, BOUND TO THE CART.

Transcribes checkVerMatch (from drmario_prg_game_logic.asm, same transcription that diagnosed
the wedge in tempo-wt tmp/wedge129/) and runs it with the scan-break predicate DECODED FROM THE
BYTES OF THE CART UNDER TEST, not from a hand-coded "what the fix should be" (gate standard
rule 6: gate the object that actually runs). Batteries:

  A. every known hang state (the captured silicon wedge field + the minimal $8F triggers)
     must HANG under the control cart's predicate and COMPLETE under the fixed cart's.
  B. 4000 random legal-colour boards: field byte-identical + identical match/combo counts
     between the two carts' predicates (the fix must not touch legal play).
  C. legitimate vertical matches INCLUDING bottom-row (rows 12-15) must still clear under the
     fixed predicate (the fix must bound the scan, not break real matches).
  D. overrun-clear: a colour-matching byte in the trailing region must NOT be clear-written
     under the fixed predicate (the fix removes the out-of-field write, i.e. the wedge's
     persistence mechanism).

MUTANT KILLS (rule 5 -- the batteries must FAIL on wrong fixes; each mutant is a real 3-byte
variant someone could have shipped):
  m_bound88  CMP #$88 / BCS  -- off-by-one bound, scans one row past the field  -> killed by D
  m_bcc      CMP #$80 / BCC  -- inverted carry branch, breaks every chain       -> killed by C
  m_bne      AND #$F8 / BNE  -- inverted zero branch on the original test       -> killed by C

usage: gate_verfix_sim.py <control_cart.nes> <fixed_cart.nes> <wedge_ram.hex>
exit 0 only if every battery passes and every mutant is killed.
"""
import sys, random

ROWSIZE, MATCH_LEN = 8, 4
LASTROW = 0x80 - 8 * (MATCH_LEN - 1)      # 0x68
MASK_COLOR, JUST_EMPTIED, CLEARED, LASTCOL = 0x0F, 0xF0, 0xB0, 0x07
ANCHOR = bytes.fromhex("a55a186908855aa55a")   # row step: LDA $5A/CLC/ADC #$08/STA $5A/LDA $5A


def decode_predicate(cart_path):
    """Read the 3 scan-break bytes after the anchor and decode them into a python predicate.
    Refuses anything it cannot decode (a gate that silently guesses is not a gate)."""
    rom = open(cart_path, "rb").read()
    i = rom.find(ANCHOR)
    assert i >= 0, f"{cart_path}: checkVerMatch anchor not found"
    assert rom.find(ANCHOR, i + 1) < 0, f"{cart_path}: anchor not unique"
    return decode_bytes(rom[i + 9:i + 12]), rom[i + 9:i + 12].hex()


def decode_bytes(b):
    op, imm, br = b[0], b[1], b[2]
    if op == 0x29 and br == 0xF0:   # AND #imm / BEQ  (break when (ft & imm) == 0)
        return lambda ft: (ft & imm) == 0
    if op == 0x29 and br == 0xD0:   # AND #imm / BNE
        return lambda ft: (ft & imm) != 0
    if op == 0xC9 and br == 0xB0:   # CMP #imm / BCS  (break when ft >= imm)
        return lambda ft: ft >= imm
    if op == 0xC9 and br == 0x90:   # CMP #imm / BCC
        return lambda ft: ft < imm
    raise AssertionError(f"undecodable scan-break bytes {b.hex()}")


def check_ver_match(F, broken, limit=200_000):
    """('done'|'HANG', field, matches, combo). Faithful transcription; `broken(ft)` is the
    decoded scan-break predicate (the ONLY thing the fix changes)."""
    F = list(F)
    matches = combo = 0
    fieldPos = it = 0
    while True:
        it += 1
        if it > limit:
            return "HANG", F, matches, combo
        fieldPos_tmp = fieldPos
        colorChain = 0
        startingColor = F[fieldPos]
        if startingColor >= JUST_EMPTIED:
            fieldPos = (fieldPos + ROWSIZE) & 0xFF
        else:
            startingColor &= MASK_COLOR
            while True:
                fieldPos_tmp = (fieldPos_tmp + ROWSIZE) & 0xFF
                if broken(fieldPos_tmp):
                    break
                if (F[fieldPos_tmp] & MASK_COLOR) != startingColor:
                    break
                colorChain += 1
            if colorChain >= MATCH_LEN - 1:
                combo += 1
                fieldPos_last, fieldPos_tmp = fieldPos_tmp, fieldPos
                while True:
                    F[fieldPos_tmp] = (F[fieldPos_tmp] & MASK_COLOR) | CLEARED
                    fieldPos_tmp = (fieldPos_tmp + ROWSIZE) & 0xFF
                    if fieldPos_tmp == fieldPos_last:
                        break
                matches += 1
                fieldPos_tmp = fieldPos_last
            fieldPos = fieldPos_tmp
        if fieldPos >= LASTROW:
            fieldPos = (fieldPos + 1) & LASTCOL
            if fieldPos == 0:
                return "done", F, matches, combo


def mk(cells, tail=0xFF):
    F = [0xFF] * 128 + [tail] * 128
    for (r, c), v in cells.items():
        F[r * 8 + c] = v
    return F


def battery(name_ctl, pred_ctl, name_fix, pred_fix, wedge_field, verbose=True):
    """Run A-D. Returns list of failure strings (empty = pass)."""
    fails = []

    # A. known hangs: control HANGs, fixed completes
    hangs = [("captured wedge P2 field", wedge_field),
             ("$8F at r11c3", mk({(11, 3): 0x8F})),
             ("$8F at r12c3", mk({(12, 3): 0x8F}))]
    for nm, F in hangs:
        o = check_ver_match(F, pred_ctl)[0]
        f = check_ver_match(F, pred_fix)[0]
        ok = (o == "HANG" and f == "done")
        if verbose:
            print(f"   A {nm:26s} {name_ctl}={o:5s} {name_fix}={f:5s} {'OK' if ok else '*** FAIL'}")
        if not ok:
            fails.append(f"A:{nm}")

    # B. 4000 random legal boards: byte-identical outcome
    rng = random.Random(7)
    bdiff = 0
    for t in range(4000):
        F = [0xFF] * 256
        for _ in range(rng.randint(20, 90)):
            r, c = rng.randint(3, 15), rng.randint(0, 7)
            typ = rng.choice([0x40, 0x50, 0x60, 0x70, 0x80, 0xD0])
            F[r * 8 + c] = typ | rng.randint(0, 2)          # legal colours only
        ro, Fo, mo, co = check_ver_match(F, pred_ctl)
        rf, Ff, mf, cf = check_ver_match(F, pred_fix)
        if not (ro == rf == "done" and Fo == Ff and (mo, co) == (mf, cf)):
            bdiff += 1
    if verbose:
        print(f"   B legal boards identical: {4000 - bdiff}/4000 {'OK' if bdiff == 0 else '*** FAIL'}")
    if bdiff:
        fails.append(f"B:{bdiff} boards diverge")

    # C. legitimate vertical matches (incl. bottom row) must clear under the FIX
    cases = [("rows 3-6 col 2", {(r, 2): 0x40 | 1 for r in (3, 4, 5, 6)}),
             ("rows 12-15 col 5 (bottom)", {(r, 5): 0x40 | 2 for r in (12, 13, 14, 15)}),
             ("rows 10-15 col 0 (6-chain)", {(r, 0): 0x40 | 0 for r in range(10, 16)})]
    for nm, cells in cases:
        F = mk(cells)
        rf, Ff, mf, _ = check_ver_match(F, pred_fix)
        cleared = all((Ff[r * 8 + c] & 0xF0) == CLEARED for (r, c) in cells)
        ok = (rf == "done" and mf >= 1 and cleared)
        if verbose:
            print(f"   C {nm:26s} {name_fix}: result={rf} matches={mf} all-cleared={cleared} "
                  f"{'OK' if ok else '*** FAIL'}")
        if not ok:
            fails.append(f"C:{nm}")

    # D. overrun-clear: legit 4-chain rows 12-15 + colour-matching byte in the TRAILING region
    # directly below the column. The chain must clear (it is a real match), but the FIX must
    # bound the scan at the field edge: the tail byte stays byte-untouched. An off-by-one bound
    # (m_bound88) extends the chain into the tail and clear-stomps it -- as the ORIGINAL did.
    # (A chain STARTING below row 12 is never a scan start -- start cells stop at LASTROW --
    # so the discriminating case must be a row-12 start reaching the field edge.)
    F = mk({(r, 4): 0x40 | 2 for r in (12, 13, 14, 15)})
    F[0x80 + 4] = 0x02                                       # tail byte, same colour nibble
    rf, Ff, mf, _ = check_ver_match(F, pred_fix)
    ok = (rf == "done" and mf == 1 and Ff[0x80 + 4] == 0x02
          and all((Ff[r * 8 + 4] & 0xF0) == CLEARED for r in (12, 13, 14, 15)))
    if verbose:
        print(f"   D edge 4-chain + matching tail {name_fix}: result={rf} matches={mf} "
              f"tail=0x{Ff[0x80 + 4]:02X} {'OK' if ok else '*** FAIL'}")
    if not ok:
        fails.append("D:overrun-clear")
    return fails


def main():
    ctl_cart, fix_cart, ramhex = sys.argv[1], sys.argv[2], sys.argv[3]
    hexs = open(ramhex).read().split()
    raw = bytes.fromhex("".join(hexs))
    assert len(raw) == 2048, f"wedge ram must be 2048 bytes, got {len(raw)}"
    wedge_field = list(raw[0x500:0x600])                     # P2 field + trailing region

    pred_ctl, b_ctl = decode_predicate(ctl_cart)
    pred_fix, b_fix = decode_predicate(fix_cart)
    print(f"control cart scan-break bytes: {b_ctl}  (decoded)")
    print(f"fixed   cart scan-break bytes: {b_fix}  (decoded)")
    assert b_ctl != b_fix, "control and fixed carts carry the SAME scan-break -- vacuous gate"

    print("== batteries on the two carts' DECODED predicates ==")
    fails = battery("ctl", pred_ctl, "fix", pred_fix, wedge_field)

    print("== mutant kills (each wrong 3-byte fix must fail at least one battery) ==")
    mutants = [("m_bound88", "c988b0", "D"), ("m_bcc", "c98090", "C"), ("m_bne", "29f8d0", "C")]
    mfails = []
    for nm, hx, expect in mutants:
        mpred = decode_bytes(bytes.fromhex(hx))
        mf = battery("ctl", pred_ctl, nm, mpred, wedge_field, verbose=False)
        killed = any(f.startswith(expect + ":") for f in mf)
        print(f"   {nm:10s} bytes={hx}  failures={mf if mf else 'NONE'}  "
              f"{'KILLED (by ' + expect + ')' if killed else '*** SURVIVED'}")
        if not killed:
            mfails.append(nm)

    if fails or mfails:
        print(f"GATE FAIL: batteries={fails} surviving_mutants={mfails}")
        sys.exit(1)
    print("GATE PASS: all batteries green on cart-decoded predicates; 3/3 mutants killed")


if __name__ == "__main__":
    main()
