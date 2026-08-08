# Dr. Mario TE — PRG free-space map & allocation authority

The v7 footer→study and v8 relocation→Settings-table collisions BOTH happened because "filler
looks free." It is not. A byte is only free if it is **execution-dead AND outside every
`RB6C2_PRINT` printing table AND not read by any indexed data table**. This is the derivation and
the resulting map. Re-run `derive()` (below) after any base/cart change.

## Why filler ≠ free: `RB6C2_PRINT`

`RB6C2_PRINT` ($B6C2) is the nametable "printing-program" bytecode interpreter. Each
`jsr RB6C2_PRINT` is followed by an **inline 2-byte table pointer** (RB74B fetches it off the
stack). It walks the table via ptr $00/$01 as bytecode: a chunk = 3-byte header
{ppuHi, ppuLo, count} + data (count = p2&$3F, repeat = p2&$40, autoinc32 = p2&$80); `$4C` = CALL
(push ptr), `$60` = RETURN (`pla;pla`), byte ≥ $80 = `rts`/end. **Every byte a table walks is read
as data on each draw of that screen** — code placed there uploads as garbage tiles, or (part3c
$BC26) mis-parses into a stack-corrupting `$60` → wild `rts` → `$0301` = `$02` = KIL.

## The 21 printing tables (data-read-live; walk them to get the exact read-set)

Small cluster: `$A26A`, `$A2B8`, `$A2FF`, `$A346`, `$A56B`,`$A58F`,`$A5B3`,`$A5D7`,`$A5FB`,`$A61F`,
`$A643`,`$A667`,`$A67B`,`$A69F`,`$A6C3`,`$A6E7`.
Five big nametable tables:
| table | range | screen |
|---|---|---|
| `$B91C` | `$B91C-$BD7B` | TITLE (part3c $BC26 lived here = the KIL) |
| `$BD7D` | `$BD7D-$C196` | SETTINGS / level-select (part3b $BE56 row 6; footer $C0A9 row 23 / $C0EF row 25) |
| `$C198` | `$C198-$C5F8` | (nametable) |
| `$C5F9` | `$C5F9-$CA59` | (nametable) |
| `$CA5A` | `$CA5A-$CEFF` | (nametable) |

## Also NOT free (indexed data tables / occupied)
- `$9FF8` region — read by `LDA $9FF8,X` (10 sites incl. the $B5C3/$B5FA two-level lookup). (part2 lived here.)
- `$CF00-$CF7F` — board-init table, `LDA $CF00,X` @ $9CEC copies it to $0400.
- `$D2CC-$D2FF` — TE study blob (part1).
- `$FF30-$FFCF` — TE embedded VS-CPU AI / trampoline. `$FFFA-$FFFF` = vectors.
- **`$FB00-$FCFF` — the COPRO DRIVER blob in the copro carts.** Free in the 32KB standalone ONLY.

## SHARED-FREE (free in base AND the copro cart's unit0, outside every table, unreferenced)
Derivation = ($FF/$00 runs) ∩ (∉ any table read-set) ∩ (no abs/indexed ref) ∩ (filler in base+copro):
| run | size | notes |
|---|---|---|
| `$A02E-$A03D` | 16 B | clean, 0 refs |
| `$CEEC-$CEFC` | 17 B | clean, 0 refs (trailing pad after the $CA5A table's walked content) |
| `$A049-$A057` | 9 B | clean, but `$A058` starts a `LDA $A058,X` table — usable part is 9 B |

Total shared-free ≈ 42 B in three runs, max single run 17 B. Insufficient for the ~84 B 2P-study
tail or the 23 B footer routine → the footer takes the **split build** (standalone → its free
`$FB40/$FB60` in `$FB20-$FB7F`, which is 0-ref/outside-all-tables in the standalone; copro carts
drop the sprite footer since $FBxx = driver). The 2P tail is EVACUATED (v8.2), not relocated.

## Allocation rule for any future TE code/data
1. execution-dead, or code you intentionally `JMP`/`JSR` to;
2. outside every `RB6C2_PRINT` table above (walk them; don't eyeball);
3. not read by any `LDA/STA/CMP abs,X/Y` data table (e.g. `$9FF8`, `$CF00`, `$A058`);
4. free in BOTH targets (32KB standalone AND copro unit0 — copro driver owns `$FB00-$FCFF`, AI owns
   `$FF30+`, board-init `$CF00`, study-blob `$D2CC`).

## derive() — the reproducible method
Simulate the interpreter (`scratchpad/print_walker.py`), union the read-sets of all 21 table
pointers (found by scanning for `20 C2 B6` + the inline 2 bytes), then scan for `$FF/$00` runs
outside that union with zero abs/indexed refs, filler in base AND the copro cart. Validation: the
title-table walk must terminate at `$B91C+1120 = $BD7C` and include `$BC26` (the KIL byte).
