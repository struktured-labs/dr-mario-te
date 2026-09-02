# DRTUCKGUARD per-descriptor correctness — 4/4 MATCH, but the ALLOW path is UNTESTED

Run by the team lead after proph-cvc's session died. Cart `cvc_tg1_mmc1.nes` (md5 `c595d85c`),
20,000 frames, harness `predtest3.lua`. **4 scored cases, 5 discarded** by the stale-board guard
(board changed between publication and decision) — the guard is working.

## Two HARNESS defects found and fixed; NO cart defect demonstrated

**1. ROW CONVENTION (fixed before this run).** v2 published `W_TROW = 15 − rt`. The cart does
`TUCK_R2 = 15 − W_TROW` and `TUCK_R2` is compared against `$0386`, which counts **UP from the
floor** — so the mailbox field must arrive **TOP-relative**. v2's inversion made the cart faithfully
evaluate row 14 for a pocket at row 1. Confirmed from the cart's own logging this run:
`trow_board=1 → cart_TUCK_R2=14`, i.e. `15 − 1`. Correct.

**2. THE GUARD DOES NOT USE THE HARNESS'S `final` COLUMN — it uses the DRIVER'S TARGET (`tgt_c`).**
The tell was `cart_TG_NEED` varying (5, 5, 2, 6) where `|approach − final| + 2` would be a constant 3.
Deriving `tgt_c` from `TG_NEED` and cross-checking against `TG_OFF`'s column agrees in all 4 cases.
⇒ **The descriptor is only (approach column, trigger row).** Where the capsule is actually going
comes from the search's target column. The harness invented a `final` field the protocol does not
carry — a modelling error, not a cart error.

## Result: 4/4 MATCH

| case | approach | cart tgt_c | start row | free below | need | independent | cart | |
|---|---|---|---|---|---|---|---|---|
| 001 | 2 | 5 | 1 | 1 | 5 | VETO | VETOED | MATCH |
| 002 | 2 | 5 | 1 | 1 | 5 | VETO | VETOED | MATCH |
| 003 | 5 | 5 | 1 | 1 | 2 | VETO | VETOED | MATCH |
| 004 | 5 | 1 | 1 | 1 | 6 | VETO | VETOED | MATCH |

Replaying the cart's own loop (start at `15 − TUCK_R2`, add 8 **before** each read, stop on a
non-empty cell under the `$00`-or-`$FF` dual-encoding rule) on the logged boards reproduces its
decision exactly, every time.

## ⚠⚠ THE GAP THAT MATTERS: EVERY CASE WAS A VETO

**All four are VETO. The ALLOW path has never been observed.** A guard hardwired to `TUCK_C2 <- $FF`
unconditionally would also score 4/4 here. ⇒ **This does not yet distinguish a correct guard from
one that always vetoes** — R96 in its exact form: the mechanism has not been shown able to do the
other thing.
⇒ **REQUIRED NEXT: a case where the predicate says ALLOW and the cart ALLOWS.** That is the positive
control, and it is the difference between "logic verified" and "veto path verified".
⇒ Why they are rare, and why seeking them is legitimate: only **~12.8% of real L11 tuck targets are
payable** (team-lead analysis over 1,809 banked boards), so random sampling yields mostly vetoes.
Seeking payable configurations is fine here because this is a **per-case LOGIC test, not a rate
test** — the substrate's distribution does not enter a case-by-case correctness claim (R102).
