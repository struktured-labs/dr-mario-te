"""Independent implementation of the DRTUCKGUARD predicate, for the per-descriptor test.

⚠ Written from the SPEC, deliberately NOT by reading the cart's emitted 6502 back. If it were
derived from the same code it would agree by construction and test nothing.

Spec (emitter, adoption site): refuse an approach whose remaining fall cannot pay for the
lateral trip --
    free rows STRICTLY BELOW the trigger, in the FINAL column  >=  |approach - final| + 2
A cell is EMPTY iff its byte is $00 or $FF (the dual-encoding rule). Board is 16 rows x 8 cols
at $0500, index = row*8 + col. TUCK_R2 is stored as 15 - board_row.
"""
def empty(b, r, c):
    v = b[r * 8 + c]
    return v == 0x00 or v == 0xFF

def free_rows_below(board, trigger_row, col):
    """Count contiguous free rows strictly below trigger_row in `col`, stopping at the first
    occupied cell -- mirroring the cart's loop, which walks down by 8 and halts on occupancy."""
    n = 0
    r = trigger_row + 1
    while r <= 15:
        if not empty(board, r, col):
            break
        n += 1
        r += 1
    return n

def verdict(board, approach, final, trigger_row, margin=2, scan_col=None):
    """Returns 'ALLOWED' or 'VETOED'. scan_col defaults to FINAL (the correct column);
    pass approach to model the `approachcol` mutant. margin=0 models `nomargin`."""
    need = abs(approach - final) + margin
    col = final if scan_col is None else scan_col
    have = free_rows_below(board, trigger_row, col)
    return ("ALLOWED" if have >= need else "VETOED"), need, have

if __name__ == "__main__":
    import re, sys, collections
    path = sys.argv[1] if len(sys.argv) > 1 else "pred_tg1v2.log"
    rows = []
    for line in open(path):
        m = re.search(r"CASE (\d+) approach=(\d+) final=(\d+) trow_board=(\d+) "
                      r"cart_TUCK_C2=(\w+) verdict=(\w+) board=([0-9A-F]+)", line)
        if m:
            rows.append(dict(n=int(m.group(1)), a=int(m.group(2)), f=int(m.group(3)),
                             rt=int(m.group(4)), cart=m.group(6),
                             board=bytes.fromhex(m.group(7))))
    if not rows:
        print("no cases parsed from", path); sys.exit(1)
    print("cases: %d\n" % len(rows))
    agree = collections.Counter()
    for r in rows:
        exp, need, have = verdict(r["board"], r["a"], r["f"], r["rt"])
        ok = (exp == r["cart"])
        agree["agree" if ok else "DISAGREE"] += 1
        if len(rows) <= 40 or not ok:
            print("  case %03d a=%d f=%d trow=%-2d need=%d have=%-2d  independent=%-7s cart=%-7s %s"
                  % (r["n"], r["a"], r["f"], r["rt"], need, have, exp, r["cart"],
                     "OK" if ok else "*** DISAGREE ***"))
    print("\nAGREEMENT: %s" % dict(agree))
    # mutant predictions on the SAME cases
    for lbl, kw in (("approachcol", dict(scan_col="A")), ("nomargin", dict(margin=0))):
        d = 0
        for r in rows:
            base, _, _ = verdict(r["board"], r["a"], r["f"], r["rt"])
            if lbl == "approachcol":
                mut, _, _ = verdict(r["board"], r["a"], r["f"], r["rt"], scan_col=r["a"])
            else:
                mut, _, _ = verdict(r["board"], r["a"], r["f"], r["rt"], margin=0)
            if mut != base: d += 1
        print("MUTANT %-12s differs from the correct predicate on %d/%d cases" % (lbl, d, len(rows)))
