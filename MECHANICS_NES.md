# Dr. Mario (NES) — mechanics reference

The canonical place for **how the game itself works**, as distinct from how our AI works.
Every entry is marked with how we know it. Prefer adding here over re-deriving.

- **VERIFIED** — we measured or read it ourselves, and the check is named.
- **SOURCED** — from a primary external source, cited, not independently reproduced.
- **UNVERIFIED** — believed, but nobody has checked. Do not build on these without testing.

---

## 1. Capsule (pill) generation — ★ NOT uniform, and NOT board-dependent

**The algorithm** (SOURCED: [Winslow](https://winslowjosiah.com/blog/2024/06/28/how-dr-mario-nes-creates-its-levels/); corroborated by [dmwit/dr-mario-ngrams](https://github.com/dmwit/dr-mario-ngrams) over all 32767 seeds):

```
next_id = (last_id + (lfsr_low_nibble)) mod 9      # 9 capsule types, ids 0..8
```

A 16-bit LFSR (two bytes `s0,s1`; feedback = bit1(s0) XOR bit1(s1), both bytes shift
right) is stepped once per capsule; its **low nibble (0..15)** is added to the previous
capsule id, mod 9.

★ Because a 0-15 draw is reduced mod 9, **increments 0-6 are twice as likely as 7-8.**
That single fact produces the whole distribution shape.

**Consequences** (VERIFIED — `dr_mario_rl/tmp/pillrng/nes_pills.py::selftest`, an
independent reimplementation that reproduces dmwit's published ratios):

| property | measured | dmwit |
|---|---|---|
| marginal (single capsule) vs uniform | 0.90x - 1.15x | ~0.93 - 1.13x |
| **2-gram (adjacent pair) vs uniform** | **0.39x - 1.70x** | ~0.40 - 1.71x |

So: **weak marginal bias, STRONG sequential correlation.** Any claim that capsules are
"uniformly distributed in [0,8]" (as tetris.wiki / harddrop state) is true only of the
marginal and is wrong about the sequence.

**★ The buffer is precomputed and loops** (VERIFIED: period-128 self-test):
- **128 capsules**, generated **before the level starts**, then **loops** (capsule 129 == capsule 1).
- Filled **backwards** (index 0x7F down to 0), played **forwards** from index 0. Not a typo — it is what the ROM does.
- The generator is called **twice** before play, so the player's first capsule is the sequence's **second** element.
- ROM warm-boot seed is the constant **`$89/$88`**; the LFSR orbit from it is **32767** states, so the entire game has exactly **32767 distinct capsule buffers**. Seed `0x0000` is never used.

**★ It CANNOT depend on bottle/board state** (VERIFIED: same seed -> byte-identical
128-capsule sequence, twice, independent of play). The buffer exists before a single
piece is placed. A question worth closing because a "wait for the ideal capsule" planner
depends on it.

**Drought structure** (VERIFIED, 1500 seeds, NES vs matched uniform):

| you need | NES median / p95 / p99 / max | uniform |
|---|---|---|
| any capsule containing colour X | 1 / 4 / 5 / 13 | 1 / 4 / 6 / 21 |
| **a SPECIFIC double (X,X)** | 7 / **32** / **57** / **121** | 6 / 26 / 39 / 97 |
| a capsule with both X and Y | 4 / 14 / 21 / 37 | 3 / 12 / 19 / 41 |

★ Droughts are a **tail** phenomenon and only for **specific** capsules. For common needs
the NES is indistinguishable from uniform (sometimes better). For a named double the p99
wait is ~46% longer and the worst case is **121 of a 128 buffer** — effectively never.
This is exactly the regime a surgical/goal-directed planner operates in.

**Community fixes** (SOURCED): [Dr. Mario Turbo](https://www.romhacking.net/hacks/6158/)
and the standalone [SNES-RNG mod](https://playdm.net/ips/Dr_Mario_SNES_RNG.ips) swap in
the SNES PRNG "to prevent long droughts or runs and enable more doubles"; per
[wiki.drmar.io](https://wiki.drmar.io/index.php?title=Rom_Hacks) they change the SOURCE
of randomness only — the pill/level generation *algorithms* are untouched. No NES hack
implements a Tetris-style 7-bag guarantee.

**Seed recovery**: the opening virus layout uniquely determines the 16-bit seed
(VERIFIED in our own M2a work, 128/128 exact; community tool
[Granivore](https://tools.drmar.io/granivore/) does the same). Since ~3.17 bits arrive
per capsule, ~5 observed capsules also pin it. So the full future capsule sequence is
**deducible from public information**.

### ⚠ Our simulator does NOT implement this
`faithful_env._rand_pill()` draws `Pill(rng.integers(1,4), rng.integers(1,4))` — two
independent uniform colours — and `faithful_game.py`'s own docstring admits *"pill/virus
RNG is uniform here"*. **Every offline result produced before 2026-07-28 used the uniform
process.** Board-level conclusions (move choice, win rates) are unaffected; anything
about **waiting for a specific capsule** is measured under the wrong process.
Drop-in replacement: `dr_mario_rl/tmp/pillrng/nes_pills.py` (`NesPillSource(seed).attach(env)`).

---

## 2. Virus generation

- **Count = 4 x (level + 1)** — L11 = 48, L14 = 60, L17 = 72. (VERIFIED against the sim.)
- **Max 2 same-colour viruses in a line.** (VERIFIED: validated generator, L11, 300 boards -> max same-colour virus run = 2 in 300/300, never 3.) Viruses never move, so a run present at k=1 is permanent; a 4-run would clear instantly at game start and is therefore impossible.
  ★ Useful as a **data-quality filter**: our vision corpus showed 3-runs on 29% of boards and impossible 4-runs on 5.3%, which is how we caught that its virus flags are over-labelled.
- Placement avoids same-colour neighbours within two cells (SOURCED: Williams et al., *Dr. Mario Puzzle Generation*, JCDCG^2 2019 — abstract only, full PDF 403'd). Same paper: hardest NES board is level 20, 84 viruses.

---

## 3. Clearing

- A maximal run of **4 or more** same-colour cells in a row or column clears. All such runs clear **simultaneously** in one step. (VERIFIED — two independent implementations fuzz-matched on 6000 boards.)
- After a clear, gravity settles and the board is **re-checked** — cascades/chains. Intact capsule pairs fall together; an orphaned half falls alone. (Link state matters; the vision corpus has no link data, which is why it cannot measure cascades.)
- ★ **Two simultaneous runs need >= 7 distinct cells** (4+4 minus a shared corner), so `cells >= 7` is a near-perfect proxy for "double-line clear".
- Level clears when virus count reaches 0.

---

## 4. Gravity / timing

- frames-per-row = `gravityTable[speedBase(LOW=15 / MED=25 / HI=31) + speedup]`, where `speedup` (`$8A`) increments about every 10 capsules.
- **L11 MED runs 19 -> 5 frames/row** across a game. (VERIFIED, ROM-exact.)
- Soft drop ~2 f/row; natural fall ~13 f/row at L11 early.
- The **lock timer is the gravity timer** (`$92` currentP_speedCounter) — rotation does *not* reset it.
- Rotation is **rising-edge only** (`btnsPressed`), which is why a held button never repeats.
- ★ **Crossover**: at ~7-8 f/row a capsule lands before a depth-3 search completes. Past that point an AI that waits for DONE drift-locks. This is a correctness cliff, not just a tempo cost.

---

## 5. Versus mode

- Clearing **2+ lines simultaneously** sends garbage; more lines = more garbage.
- Garbage enters only at columns **{1,5} / {2,6} / {3,7}** per our extracted rule — ★ **columns 0 and 4 are garbage-immune**, so structures completed through them are structurally protected. (UNVERIFIED against the ROM; extracted from observed behaviour — worth confirming before relying on it.)
- Best-of-3 rounds; the player must press START between rounds.
- `$0727` = 2 at both 2P-human and VS-CPU, so it is **ambiguous** for detecting VS-CPU; gate on `$04` instead.

---

## 6. Useful RAM / ROM addresses

| what | where |
|---|---|
| next-capsule preview | `$031A` / `$031B` |
| current capsule orientation | `$03A5` |
| level select | `$0316` |
| gravity/lock counter (P2) | `$0392` (= p2 speedCounter) |
| speedup counter | `$8A` |
| gravity table | ROM `$A795` |
| VS-CPU AI input hook | ROM `$37CF` |
| free space used by our carts | `$FB00` |

Playfield encoding: high nibble = link direction, low nibble = colour. See
[[dr-mario-tile-encoding]].

---

## Sources
- Winslow, *How Dr. Mario (NES) creates its levels* — https://winslowjosiah.com/blog/2024/06/28/how-dr-mario-nes-creates-its-levels/
- dmwit, *dr-mario-ngrams* — https://github.com/dmwit/dr-mario-ngrams
- Dr. Mario community wiki — https://wiki.drmar.io/
- Data Crystal (RAM/ROM maps) — https://datacrystal.tcrf.net/wiki/Dr._Mario_(NES)
- Williams et al., *Dr. Mario Puzzle Generation: Theory, Practice, & History*, JCDCG^2 2019
- Our own: `dr_mario_rl/tmp/pillrng/` (generator + drought measurement), M2a seed-recovery, `faithful-sim`
