# PRE-REGISTRATION: DRTUCKGUARD A/B (CRN-paired, Mesen, RAM truth)

**CLAIM BOUNDARY, first because a limitation in a limitations section does not survive
paraphrase: Mesen's P2 brain is a weak Lua heuristic, so ABSOLUTE pills-to-clear will NOT match
silicon. THE PAIRED DIFFERENCE BETWEEN ARMS ON IDENTICAL SEEDS IS THE ESTIMAND; THE LEVEL IS
NOT.** No pixel adjudication is involved — every quantity is read from RAM.

Registered before any A/B run. Arms: **`30c92183`** (Childproof, the standing baseline every
successor is scored against) vs **`7a22474f`** (`DRTUCKGUARD=1`).

## ⚠ WHY UNPAIRED IS NOT AN OPTION — measured, not assumed

Banked `dblcanon` base corpus, cleared games (n=91 of 120): pills-to-clear **mean 139.7, median
126, sd 49.2**. Games **per arm** for 80% power, unpaired:

| effect | n/arm |
|---|---|
| 2 fewer pills | **9,489** |
| 3 fewer pills | 4,218 |
| 5 fewer pills | 1,519 |

The owner's description — *"wasted a couple pills"* — is a **2-3 pill** effect, i.e. 0.04-0.06 sd.
**An unpaired design is not underpowered here, it is hopeless.**

⇒ **CRN-PAIRED: identical seeds in both arms, paired differences.** Most of that sd is common to
both arms (same virus layout, same capsule stream), and DRTUCKGUARD only alters behaviour where a
tuck descriptor is engaged AND the fall budget is short — so the arms should be **pill-for-pill
identical on the large majority of placements**.

**CRN mechanism:** `SEED1 $6167` / `SEED2 $6168` are set from `NAV_T` on the first play frame of
each match. The harness **overwrites both from Lua immediately after**, with a per-pair seed
value, forcing identical virus layouts and capsule streams across arms.

⚠ **The unpaired sd = 49.2 MUST NOT be used to size the paired run** — it would over-size by
orders of magnitude. **Pilot ~30-40 seed pairs, MEASURE the paired sd, then size.**

## PRIMARY / SECONDARY — inverted from the original tasking, and here is why

**PRIMARY: STRANDING RATE per ENGAGED placement.**
**SECONDARY: pills-to-clear, paired difference.**

Reasoning, recorded before running:
* stranding is **per-placement**, so its n is **thousands of placements** rather than tens of
  games; pills-to-clear is per-game and, if divergence is rare, most pairs contribute an **exact
  zero** and the effective n collapses to the divergent subset;
* stranding is **the mechanism's own signature** and the direct test of the banked 4/4 finding;
* pills-to-clear is the **owner's** metric and stays as the secondary that translates mechanism
  into value — but it is **underpowered by construction** and will not carry a GO/NO-GO unless
  the pilot shows enough divergence to support it.

**Definitions, from RAM:**
* *engaged placement* — `TUCK_C2 $6179 != $FF` at the pill's lock;
* *stranded* — the capsule locks in the **approach** column (`TUCK_C2`) rather than the intended
  **final** column (`TGT_C2 $6152`);
* *pills-to-clear* — pill count at the frame P2's virus counter (`$03A4`) reaches 0.

## ⚠ THE PILOT MUST REPORT THE DIVERGENCE RATE FIRST

**The fraction of seed pairs where the arms differ at all.** If DRTUCKGUARD engages on, say, 5%
of games, then 95% of pairs contribute an exact zero and **the effective n is 5% of the nominal**.
**Divergence rate, not nominal n, determines power** — pairs that carry no information still sit
in the denominator. The pilot reports it before any effect estimate is computed.

## Fixed in advance

* **Effect direction:** DRTUCKGUARD should **reduce** stranding and **reduce or not increase**
  pills-to-clear. An increase in pills-to-clear is a **harm** and is reported as such.
* **R96 controls, rebuilt for this pipeline** (not assumed to transfer): a negative control with
  arm labels randomised (must show no effect) and a positive control with stranding forced to
  track arm (must show one).
* **Two-sided mutant gate** (Gate 2): `approachcol` over-vetoes ⇒ tucks collapse toward zero;
  `nomargin` under-vetoes ⇒ stranding returns. **Both must fail**, and a one-sided gate would
  pass one of them.
* ⚠ **A veto reverts to pre-tuck behaviour, so it cannot be worse than not tucking — that is an
  argument from the CODE, not evidence. Safe-by-construction must not slide into
  assumed-beneficial. The A/B still has to show it HELPS.**
