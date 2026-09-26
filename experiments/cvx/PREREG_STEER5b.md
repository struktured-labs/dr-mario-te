# PRE-REG STEER5b (2026-09-26): POST-HOC follow-up, written AFTER STEER5 failed and BEFORE this arm runs

**Trigger.** None of the six pre-registered STEER5 arms passed; most harmed (RESULT_STEER5.md). The coordinator's
couch contrast (RESULT_COUCH_TAP.md 2nd addendum, `6b0821e`, n = 2 deaths vs 4 healthy games):
- deaths started with 7 viruses in cols 3–5 above row 9 and never cleared them;
- healthy games cleared theirs within 13–27 s;
- height can't discriminate (the layout alone puts the spawn lane above 10 almost immediately).
⇒ Target: **prompt clearing of HIGH spawn-column viruses.**

**Arm.** Leaf term HSV = −W · #(viruses in cols 3–5 at row < 9) remaining in the leaf board.
- Added at every leaf (the same three paths as STEER5), in `cascade_leaf5b_x.py`: an exact copy of the STEER5
  module plus this one term (w5[3]).
- Zero once they are gone, so it is active only while the count is > 0. It rewards reducing that count at all 3 plies.
- Unit-tested; w5 = 0 is identical to the baseline (311/311).
- Doses: `s5b_hsv180` (W = 180 = a virus clear's imm) / `s5b_hsv540` (W = 540 = one chain step).
- **vs prior art:**
  - STEER4 sv180/sv540 were ROOT proxies (RVV × a landing-region indicator), not a count of the remaining
    high viruses at the leaf.
  - STEER5's burial/access terms price covering, not the remaining count.
- **RTL shape:** a per-leaf region count (cols 3–5, rows 0–8, virus bit) from the existing column walk, plus
  one combine term.

**Design.** As STEER5:
- gate (b), OWNER model, L11 MED, n=600 paired seeds 36734.. step 2;
- baseline = the banked `s4_base`;
- PRIMARY tap≤100 and whole-game tap-out, paired;
- PASS = one CI entirely below 0 and the other's upper CI ≤ +1 pp;
- race secondary if it passes;
- the pre-treatment hsv9 stratification reported (does the benefit sit in the high-count stratum?).

**Declared post-hoc.** Chosen after seeing STEER5, on the same reused seeds. A pass would need a holdout on the
fresh block before any build.
