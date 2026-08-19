# Task #123 — double-capsule orient canonicalisation (DRDBLCANON)

**Branch `tempo-123`, worktree `dr-mario-tempo-wt`. Everything below is measured on this
tree; no figure is carried in from another lane.**

## The one-line result

A capsule whose halves share a colour produces every placement twice. The two members of a
duplicate pair are the same board but sit 180° apart, and the CCW-only executor makes one of
them cost **two extra rotations**. On a shipped cart the search publishes the expensive member
on **48.94 %** of double plies — worth **57.7 rotations ≈ 0.96 s per game** — and
`DRDBLCANON` recovers all of it with **zero board effect by construction**.

## What the brief got right, and the two things it did not

| brief | reality |
|---|---|
| pairs are adjacent variants, o4 0↔1 and 2↔3, derived from boards | **CONFIRMED**, exhaustively: 7,075/7,075 double plies, partner always legal, exactly equal value, cell-for-cell identical board |
| the cheaper member depends on spawn orientation — measure it | measured, and it is a **constant**: even o4 is cheaper in *both* pairs, so canonicalisation is `AND #$FE` |
| the search does not know about the cost difference | **only true on silicon.** At `DRSEED=0` the argmax already picks the cheap member on 0/7,075 plies. The win exists solely because of the cart's tie-break jitter |
| canonicalise at the enumeration layer | **that design is not board-neutral** (0.158 % of double plies land on a different board). Moved to the publish site |

### Why the win is invisible offline

Both the Python champion and the 6502 select loop resolve ties strictly-greater-keep-first
over an o4-ascending scan, so the *earlier* (even, cheap) member wins every exact tie.
Measured: **0 non-canonical picks in 7,075 double plies**.

Shipped carts run `DRSEED=1` (confirmed in `roms/manifests/mister-human-studycounts-armed2fix.json`'s
own `flag_snapshot`), and the firmware then adds a per-candidate `+0..3` before the argmax:

    t = seed ^ ((o4 << 3) | col)  ;  j = (t ^ (t >> 3)) & 3

A pair shares `col` and differs only in bit 0 of `o4`, which is **bit 3 of `t`**, so
`j(partner) = j(member) ^ 1` — the two jitters are always `{e, e+1}` and the odd one wins.
Which member that is comes out as `bit0(seed) ^ bit3(seed) ^ bit0(col) == 0`, i.e. **fixed
per column**, half the columns each way. A real cart seed is always ODD
(`SEED2 = (NAV_T | 1) ^ $A4`, and `$A4` has bit 0 clear), which collapses it to
`bit3(seed) ^ bit0(col) == 1` — the form the rig used, matching the observed outcome on
**3157/3157** rows. ⚠ The reduced form is valid ONLY for odd seeds; I first wrote it as
though it were general and `test_jitter_pairing.py` caught that on its first run.

⚠ **This also means the offline champion and the cart are different deciders on ~49 % of
double-capsule plies.** Any fidelity or co-sim comparison that leaves `DRSEED` out of the
picture is comparing two things that were never the same.

### Why the enumeration-skip design was abandoned

Dropping the expensive slot also drops a jitter draw. A duplicated placement effectively
draws `max(j, j^1)` while a unique placement draws one value, so duplicates carry a small
systematic advantage in the near-tie lottery; removing the duplicate removes that advantage
and the ply can go to a **genuinely different placement**. Measured: **5/3157 = 0.158 %**.
Small, but it is not zero, and the whole value of this change is that it is free.

Canonicalising the **winner** instead leaves the candidate set, the jitters and the argmax
byte-for-byte as they were and rewrites only the orient — a value the pairing measurement
proves produces an identical board. Zero board effect by construction, not by sampling.

## Implementation

| site | file | what |
|---|---|---|
| firmware emitter | `tests/test_search_d3.py::_e_dblcanon` | 16 bytes at the publish site of both the engine and soft builds: `LDA S_CA; EOR S_CB; AND #$0F; BNE skip; LDA D_BO; AND #$FE; STA D_BO` |
| spec (Python) | `tests/test_search_d3.py::canon_o4` | the same rule, for gates |
| build flag | `fpga/copro/build_copro_d3.py` | `DRDBLCANON` env, default 0 |

**Not `DRCANON`** — that name already means "path to the canonical worktree" in four files
(`fpga/copro/tuck_validation/*.py`, `tests/test_tuck_bfs_translate_6502.py`); setting it to
`1` would send them looking for 6502 sources in a directory called `1`.

**No RTL change.** `CoproDrMario.sv` takes `a_o4` as an argument register and `LeafEval.sv`
evaluates one placement — nothing in the RTL enumerates orientations, so there is no
resynthesis.

### Who consumes the published orient (the executor-consumption audit)

Asked because a rewrite that lands *after* something latches the orient would be worthless.
Every cart-side consumer reaches the orient through exactly one byte — the result mailbox —
and then through `TGT_O2`:

| consumer | `patch_cartridge_copro.py` | reads |
|---|---|---|
| `handle()` DONE branch | `{L}_map` … `{L}_pst` | mailbox `wor`, maps copro→game, stores `TGT_O2` |
| DRROTFIX anytime weave | `nf2_o1` … `nf2_ost` | live mailbox snapshot `$616C` (torn-read checked), → `TGT_O2` |
| argmax-stability counter | `p2_st_chg` | `TGT_O2` vs `LAST_ORI2` |
| DRRECOMMIT | `{L}_rcdone` | `tgt_o` vs `$03A5` |
| rotation executor | `act_p2` | `$03A5` vs `TGT_O2`, presses A |

So **nothing downstream distinguishes odd from even except by rotating to it**, and the
canonicalisation happens in the COPRO, before any value crosses the mailbox — strictly
upstream of every latch, on the other side of the chip boundary, not merely "atomic with" it.

⚠ The one real hazard that leaves is the **ANYTIME** publish: the select loop republishes on
every improving candidate and the pair latch can grab an intermediate. The emission therefore
sits before *both* the mailbox store and the final `D_BO`, and checks **H** (mailbox agrees
with zero page) and **I** (every value the mailbox ever holds is canonical) verify it on the
real firmware. Mutant **M5** — correct final answer, raw orient reaching the mailbox first —
is killed by **I alone**, which is what proves I is load-bearing rather than decorative.

### Scope limit, stated rather than discovered later

`tuck_v3.py:746-748` overwrites `D_BO` from `tuck_o4_table` and republishes `S_BEST_O`
**after** this site, so a winning **tuck** candidate's orient is not canonicalised. That is
deliberate: a tuck's orient is part of a reachability plan the executor navigates, and
flipping it would change the pose being targeted. `DRDBLCANON` covers the base search only.

★ **The two features therefore compose by PRECEDENCE, not by conflict** (nmi-fix's reading,
and it is the right one): when a tuck wins, DRDBLCANON's rewrite is simply superseded, and
there is no state in which the data path holds two disagreeing orientations. That removes one
whole class of risk — the data-path class — by construction.

⚠ **It does NOT discharge the play-level gate, and the precedent says why.** `DRPRESTART` ×
`DRTUCK` was never a data conflict either: it was the executor parking at the approach column
and never switching to final — a timing/navigation failure that no data-path argument can see
or exclude. So precedence closes the data-path risk; the play gate still owns the timing risk,
and only one of those two is closed.

## Gate

`experiments/dblcanon/gate_dblcanon.py` — runs the **real 6502 firmware under py65** in both
flag states over the same boards, at realistic non-zero tie-break seeds.

| check | what it asserts |
|---|---|
| A identity | flag off emits zero bytes (OFF image == image with the block removed) |
| B bind | flag on changes the image |
| C canon-eq | ON publishes `canon(OFF's answer)` |
| C even-o4 | ON's published orient is always even |
| C board-id | ON's and OFF's answers give a cell-for-cell identical resolved board |
| D control | on NON-doubles, ON == OFF exactly |
| E tempo | rotations-from-spawn strictly decrease |
| F binds | the flag actually fired (non-vacuity) |
| G inert@s0 | with the jitter off, the flag changes nothing |
| H mailbox | the ANYTIME mailbox (`$6135`) agrees with the zero page — the cart reads the mailbox, not `D_BC`/`D_BO` |
| I publstream | EVERY value the mailbox holds during a search is canonical (or `0xFF`, the invalid marker the driver peels off) |

⚠ **The first cut of this gate was six-for-six green while measuring nothing**, because it
left the tie-break seed at 0 — where the base search already picks the cheap member and the
flag has nothing to do. `F binds` exists so that cannot happen silently again, and
`run_fw`'s docstring says why `tseed` is load-bearing.

### Result — `GATE: PASS` (full log in `GATE_RESULT.txt`)

100 double decisions and 100 non-double controls per arm, 4 match seeds, real firmware.

    REAL   A identity PASS · B bind PASS (2356B -> 2372B) · C canon-eq PASS
           C even-o4 PASS · C board-id PASS (0 DIFFERENT boards) · D control PASS
           E tempo PASS (rot 200 -> 100) · F binds PASS (50/100)
           G inert@s0 PASS · H mailbox PASS (0/100) · I publstream PASS (0/100)
    mutants killed 5/5

`F binds 50/100` is the algebra landing on the nose: the expensive member wins in exactly
half the columns. `E tempo 200 -> 100` is the same fact in rotations — the flag halves the
double-capsule rotation bill.

★ **M1 changed 0 of 100 decisions.** The `(v, v+2)` key is *inert*, reproducing the h13-gate
null exactly — a de-dup that removes nothing while every plumbing check stays green. That is
the mutant's whole purpose, and it is why "removes nothing" has to count as a kill.

### Mutants

| mutant | caught by |
|---|---|
| M1 `(v, v+2)` key — the canonical wrong answer for this lane | `C_board` or `F_binds`: it either crosses axes and moves the board, or is simply **inert**, removing nothing while looking clean. The inert mode is the failure the gw lane hit, so "removes nothing" counts as a kill |
| M2 no `cA == cB` test (population mutant) | `D_control` — perturbs non-doubles |
| M3 canonicalise to the ODD member | `E_tempo` / `C_even` — board identity still holds, so only tempo catches it |
| M4 claim ON, emit nothing | `B_bind`, `F_binds` |
| M5 correct FINAL answer, raw orient reaches the anytime mailbox first | **`I_stream` alone** — every other check passes. This is the pair-latch failure mode, and M5 surviving would mean the gate never covered it |

## Measured tempo

n = 120 games, 19,798 plies, 7,075 double plies (35.7 %), × 7 realistic match seeds.

| | |
|---|---|
| cart publishes the expensive member | **48.94 %** of double plies [47.20, 50.68] |
| rotations saved per double ply | **0.979** |
| doubles per game | 59.0 [54.1, 64.2] |
| **rotations (= frames) saved per game** | **57.7** [51.1, 65.1] |
| at 60 fps | **0.96 s per game** |

## Ship-hex reproducibility

`dbg_build.py all 0`, twice per arm:

| | md5 |
|---|---|
| `DRDBLCANON=0` | `c87e60a1`, both runs — **exactly the hash `build_copro_d3.py`'s own comment records for this recipe** |
| `DRDBLCANON=1` | `22be358c`, both runs |

Both deterministic; OFF reproduces the documented artifact byte-for-byte. `copro_rom.hex` was
backed up and restored around the sweep, and `git status` confirms it unchanged.

### ⚠ RETRACTED — "the committed copro_rom.hex has no recorded recipe" was MY FALSE ZERO

I reported that the committed `fpga/copro/copro_rom.hex` (`f4b6dfbf`) had no recorded recipe,
on the strength of `dbg_build.py all 0` plus five flag combinations (`DRSTRAND=20`,
`DRCHAIN=180`, both, `DRCOPRO_ARM=1`, `DRSTRAND=20 DRFIX=1`) returning
`111fa9b9 / c87e60a1 / 111fa9b9 / 63bcac9d / 111fa9b9`, none matching. **That claim is wrong
and is withdrawn.** The recipe is recorded, in `experiments/cosim_farm/FW_RECIPES.json` under
`arms.pre20`:

    DRCHAIN=180 DRCOPRO_ARM=1 DRFIX=1 DRCOPRO_TUCK=1
    built via experiments/cosim_farm/build_dbgpub.py

**Verified here: rebuilds to `f4b6dfbf` byte-exact.**

Two reasons the sweep could not have found it, both worth keeping:

1. I never tried `DRCOPRO_TUCK=1`. The recipe file says why — *"DRFIX=1 / DRCOPRO_TUCK=1 are
   not guessable from the arm names"* — those arms were once genuinely unprovenanced and were
   recovered by an exhaustive sweep. I ran a **narrower** sweep than the one that had already
   solved this, and read my miss as absence.
2. Right flags alone would still not have matched: `build_dbgpub.py` exists precisely because
   **a plain build resolves `tuck_v3` from a SIBLING worktree**. It pins the emitter modules
   to this tree.

⇒ Rule 8 of the killed-mutant standard, turned on its author. An absence claim needs a
**liveness-proven search** (mine never showed it could find a recipe it was given) and an
**enumeration of what the search cannot reach** (a `dbg_build.py`-only sweep reaches no
artifact built through `build_dbgpub.py`). The cheap move I skipped: `grep -rl f4b6dfbf`
finds the recipe file immediately. Same shape as the "no artifact in any worktree" false zero
this lane inherited — one week later, from the opposite direction.

## ⚠ The DRDBLCANON × DRTUCK combination is NOT ESTABLISHED

### First, a distinction I got wrong and nmi-fix caught

**`DRTUCK` and `DRCOPRO_TUCKV3` are different flags in different artifacts.**

| flag | artifact | what it gates |
|---|---|---|
| `DRTUCK` | **cart** — `patch_cartridge_copro.py:217` | the tuck **executor** in the driver |
| `DRCOPRO_TUCKV3` / `DRCOPRO_TUCK` | **copro firmware** — `build_copro_d3.py` | the tuck **enumerator/scorer** |

My earlier note said I had "checked the combination" because `DRCOPRO_TUCKV3=1` builds and
validates with `DRDBLCANON` at 0 and 1. That is a real check but it is **not** the arm the
precedent demands, because it never varies `DRTUCK` at all. The verdict below was right; the
flag I named was not.

### Why a build check could not have settled it anyway

The `DRPRESTART`×`DRTUCK` wedge was **not** found by a build failing. It was found by an
18k-frame probe of actual cart play: 83 pills and 171 pills for each flag alone, **9 pills and
a hang together**. A build that assembles says nothing about that failure mode. The required
arm is `DRDBLCANON=1 ∧ DRTUCK=1` **exercised in play**, and it is open.

### And the firmware-side combination cannot be gated in this rig either

`probe_tuck_combo.py` asks the prior question, because `dr-mario-tuck-mailbox-vacuous-gate`
says the stock rig never serves the tuck mailbox:

    double decisions compared: 24
      DRCOPRO_TUCKV3 changed the decision : 0     <-- the tuck path never fired
      DRDBLCANON changed the decision     : 12
      DRDBLCANON changed it WITH tuck on  : 12

**The firmware tuck path is INERT here**, so even the firmware-side combination arm would be
vacuous by construction — green while establishing nothing, the same shape as the `(v, v+2)`
inert detector this lane already documented.

★ **The 0-vs-12 contrast is what makes "inert" a measurement rather than an excuse.** Both
numbers come from the SAME 24 decisions on the SAME corners: `DRDBLCANON` moved 12 of them,
`DRCOPRO_TUCKV3` moved 0. So the harness demonstrably CAN move decisions — it just cannot move
them through the tuck path. That is an internal positive control living beside the null, and
without it "the tuck flag changed nothing" would be indistinguishable from a dead rig.

⇒ **Two open arms, both blockers on any cart carrying both flags, neither on this branch:**
(1) `DRDBLCANON` × `DRTUCK` exercised in play; (2) the firmware-side pair on a rig that
actually serves the tuck mailbox, or on silicon.

Also load-bearing for whoever builds that cart: the CvC tuck line is at a 6502 **branch-range
cliff** — the full `m-v8auto` set with `DRPRESTART=0` fails to assemble ("branch out of range
to not_play"), which is why `9fefaedb` was built UP from the `7611d54b` CvC base. Build up
from `7611d54b`, not down from `m-v8auto`. (My change adds 16 bytes inside the copro
firmware's search, not the cart emitter, so it should not move the cart's branch ranges at
all — a prediction, which fails loudly at assembly if wrong.)

## Side findings worth banking

1. **`nes_d3_golden` resolves to another worktree.** `build_copro_d3.py` force-registers this
   tree's `test_search_d3` into `sys.modules` but does nothing for `nes_d3_golden`, which
   `test_vrdy`/`test_readiness_ext` then win with a hardcoded `dr-mario-mods` path insert.
   The shipped firmware's py65 gate has been validating against a **different worktree's**
   golden — and this tree's own copy would fail it, because it is the weekend-era leaf whose
   docstring says the R1-R7 flags `build_copro_d3` sets on it are no-ops. Not this lane's to
   fix; `canon_o4` lives in `test_search_d3` precisely to avoid depending on the answer.
2. **The jitter gives duplicated placements two lottery tickets** and unique placements one —
   a small systematic bias toward doubles' placements that nobody chose. `DRDBLCANON` does
   not remove it (by design; removing it is what broke board-neutrality).
3. `nes_d3_golden._placements4`'s own docstring independently corroborates the pairing:
   *"the 6502 evaluates o4=1/3 even when cA==cB, and those dup entries occupy top-k slots."*
   The degeneracy was documented in the firmware golden the whole time.
