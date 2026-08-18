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
Which member that is comes out as `bit3(seed) ^ bit0(col)`, i.e. **fixed per column**, half
the columns each way. The closed form matched the observed outcome on **3157/3157** rows.

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

### Scope limit, stated rather than discovered later

`tuck_v3.py:746-748` overwrites `D_BO` from `tuck_o4_table` and republishes `S_BEST_O`
**after** this site, so a winning **tuck** candidate's orient is not canonicalised. That is
deliberate: a tuck's orient is part of a reachability plan the executor navigates, and
flipping it would change the pose being targeted. `DRDBLCANON` covers the base search only.

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

⚠ **The first cut of this gate was six-for-six green while measuring nothing**, because it
left the tie-break seed at 0 — where the base search already picks the cheap member and the
flag has nothing to do. `F binds` exists so that cannot happen silently again, and
`run_fw`'s docstring says why `tseed` is load-bearing.

### Mutants

| mutant | caught by |
|---|---|
| M1 `(v, v+2)` key — the canonical wrong answer for this lane | `C_board` or `F_binds`: it either crosses axes and moves the board, or is simply **inert**, removing nothing while looking clean. The inert mode is the failure the gw lane hit, so "removes nothing" counts as a kill |
| M2 no `cA == cB` test (population mutant) | `D_control` — perturbs non-doubles |
| M3 canonicalise to the ODD member | `E_tempo` / `C_even` — board identity still holds, so only tempo catches it |
| M4 claim ON, emit nothing | `B_bind`, `F_binds` |

## Measured tempo

n = 120 games, 19,798 plies, 7,075 double plies (35.7 %), × 7 realistic match seeds.

| | |
|---|---|
| cart publishes the expensive member | **48.94 %** of double plies [47.20, 50.68] |
| rotations saved per double ply | **0.979** |
| doubles per game | 59.0 [54.1, 64.2] |
| **rotations (= frames) saved per game** | **57.7** [51.1, 65.1] |
| at 60 fps | **0.96 s per game** |

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
