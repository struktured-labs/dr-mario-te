"""Validate the proph_trigger transcription against hand-computed boards."""
import eligibility as E

ok = True
def check(label, got, want):
    global ok
    good = got == want
    print("  %-58s %s%s" % (label, "PASS" if good else "FAIL",
                            "" if good else "  got %s want %s" % (got, want)))
    ok &= good

def board(filled):
    """filled = set of (row,col) occupied."""
    return [[1.0 if (r, c) in filled else 0.0 for c in range(8)] for r in range(16)]

FLOOR = {(r, c) for r in range(10, 16) for c in range(8)}   # deep stack, far from the throat

print("\n-- trigger --")
check("empty board -> no trigger, OTHER", E.evaluate(board(set()))["stratum"], "OTHER")
check("stack only at row 10 -> fo=10 > 2, OTHER", E.evaluate(board(FLOOR))["stratum"], "OTHER")
check("fo3 = 3 (just below the bar) -> OTHER",
      E.evaluate(board({(3, 3)} | FLOOR))["stratum"], "OTHER")
check("fo3 = 2 -> triggers", E.evaluate(board({(2, 3)} | FLOOR))["trigger"], True)
check("fo4 = 0 -> triggers", E.evaluate(board({(0, 4)} | FLOOR))["trigger"], True)

print("\n-- direction: toward the DEEPER fo, ties LEFT --")
# fo3=1, fo4=16 -> fo4 > fo3 -> prefer RIGHT
check("col3 ledge, col4 empty -> RIGHT",
      E.evaluate(board({(1, 3)} | FLOOR))["direction"], "RIGHT")
# fo4=1, fo3=16 -> fo4 < fo3 -> prefer LEFT
check("col4 ledge, col3 empty -> LEFT",
      E.evaluate(board({(1, 4)} | FLOOR))["direction"], "LEFT")
check("tie (both fo=1) -> LEFT",
      E.evaluate(board({(1, 3), (1, 4)} | FLOOR))["direction"], "LEFT")

print("\n-- gates and fallback --")
L_BLOCK, R_BLOCK = {(0, 2)}, {(0, 5)}
check("tie, LEFT gate blocked -> falls through to RIGHT",
      E.evaluate(board({(1, 3), (1, 4)} | L_BLOCK | FLOOR))["direction"], "RIGHT")
check("prefer RIGHT but RIGHT gate blocked -> falls back to LEFT",
      E.evaluate(board({(1, 3)} | R_BLOCK | FLOOR))["direction"], "LEFT")
check("both gates blocked -> UNADDRESSABLE, no direction",
      E.evaluate(board({(1, 3), (1, 4)} | L_BLOCK | R_BLOCK | FLOOR))["stratum"],
      "UNADDRESSABLE")
check("gate needs BOTH rows: (1,2) alone blocks LEFT",
      E.evaluate(board({(1, 3), (1, 4), (1, 2)} | FLOOR))["direction"], "RIGHT")
check("trigger + a free gate -> ADDRESSABLE",
      E.evaluate(board({(1, 3), (1, 4)} | FLOOR))["stratum"], "ADDRESSABLE")

print("\n-- fo is FIRST occupied from the top, not the stack height --")
check("occupied at rows 1 and 8 -> fo = 1", E.fo(board({(1, 3), (8, 3)}), 3), 1)
check("empty column -> fo = 16", E.fo(board(set()), 3), 16)

print("\n" + ("ELIGIBILITY VALIDATION: ALL PASS" if ok else "ELIGIBILITY VALIDATION: FAILED"))
raise SystemExit(0 if ok else 1)
