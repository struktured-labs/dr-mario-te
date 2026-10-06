# RESULT (silicon-fidelity lane, 2026-10-06): the tie-break seed, which every replay instrument left out

The analysis of the 10/05 "silicon-only" misses is in dr-mario-rl h16 `experiments/silfid/RESULT_SILFID_20261006.md`.
This file covers the cart side and the firmware side:
- the defect (two halves: the jitter and a firmware leak);
- the two default-off flags;
- the gates;
- the save-state co-sim tool for the silicon trace.

## 1. The defect: silicon and every replay instrument are different deciders

**Where the seed comes from:**
- The couch cart derives a per-match tie-break seed on the first play frame: `SEED2 = (NAV_T | 1) ^ $A4`. It is always
  odd and never 0.
- It rides the colour uploads' high nibbles: cA gets the seed's low nibble, cB its high nibble.

**What the copro firmware does with it:**
1. **Jitter (by design).** `val1 += (t ^ (t >> 3)) & 3`, with `t = seed ^ ((o4 << 3) | col)`, before the strict root argmax.
   - Only seed bits 0/1/3/4 matter, so an odd seed falls in one of 8 jitter classes.
   - It flips near-ties of 3 points or less.
2. **Leak (not by design).** `tuck_v3.emit_tuck_cell_prep` loads S_CA/S_CB RAW, nibbles included.
   - The base search masks with `AND #$0F`.
   - `land_place_at` then stores `LA | $40` into CUR. So the tuck extension's own two cells become
     `(nibble | 4) << 4 | colour`: half A is `$5x / $7x / $Dx (= a VIRUS) / $Fx`, half B is `$4x..$Fx`, instead of `$4x`.
   - **Measured** (Verilator vsim_pub2, seed $99, the 61 lulu-10/05 pills whose seed-0 final is a tuck):
     - fw 1488e158 vs the same fw with the mask: the timelines differ on **38/61**. The leaky image mostly LOSES the tuck:
       14 have fewer publishes and 22 finals change.
     - The masked image equals seed 0 on **52/61**. The other 9 are the intended jitter.

**Why every replay instrument disagrees with silicon.** They all run seed 0:
- the co-sim pubtrace (`SEED` default 0);
- the Mesen chained replay (it writes SEED2 = 0 and serves seed-0 timelines);
- the python faithful brain.

The DBLCANON report already warned about this for double capsules.

**On the 10/05 boards** (h16 RESULT, section 4):
- With the matching jitter class, the copro FINAL itself flips to silicon's landing. M1 G2, class 1: p52 a3 → a22, p73
  a28 → a29, p87 a20 → a13, p132 a11 → a31, p140 a10 → a27, p171 a28 → a29, every one = silicon.
- The best class per game reproduces **14** of the 102 silicon-only misses; the union over 12 seed variants is **19**.
- So the seed is real but a minority. The silicon-only residual is still open, and the silicon trace is in section 5.

## 2. Two default-off fixes

### DRSEEDZERO=1 (cart, `patch_cartridge_copro.py`; unset/0 → byte-identical)
- **Behaviour:** on the first play frame of every match it STORES 0 into SEED1/SEED2 instead of deriving them.
  - Every GO then uploads seed nibbles 0, whatever PRG-RAM inherited.
  - That means jitter off and clean tuck colours: silicon becomes the same decider as the co-sim, the Mesen replay and the
    python brain.
- **Cost:** 5 bytes smaller than the derivation, and the census margin is 4–12 cycles better.
- **Why it is safe on the couch cart:** the couch cart (P1 = human) has no mirror to desync, the seed's only purpose.
  DBLCANON already canonicalises double capsules, and at seed 0 the argmax picks the cheap member on 7075/7075 plies.
- **Why DRSEED=0 is NOT the fix:**
  - It only skips the derivation. SEED1/SEED2 are zeroed solely by the PRG-RAM POWER-ON init (`NAV_MAGIC != $A5`).
  - MiSTer PRG-RAM survives `load_core`, so a DRSEED=0 cart loaded after any seeded cart keeps uploading the previous
    cart's last seed.
  - `tests/test_seedzero.py` shows it: arm `fair_D_seed0` uploads the stale $13 on 93/93 GOs.

| cart | md5 | = |
|---|---|---|
| `couch_D_sz` | 90b442c7 | FAIR dbbb5007 + DRSEEDZERO=1 |
| `couch_DP_sz` | **607e819c** | FAIRPLUS 5b3d8183 + DRSEEDZERO=1 (pair with rbf 318607aa) |
| `couch_AP_sz` | **f954774d** | FAIR2PLUS 5a1695da + DRSEEDZERO=1 (pair with V11 seed-3 43aa62d5) |

### DRCOPRO_TUCKV3_SEEDMASK=1 (firmware, `fpga/copro/tuck_v3.py`; unset/0 → byte-identical)
- **Behaviour:** `AND #$0F` after each of the four colour loads in tuck_cell_prep.
- **Hexes:** the antibody-dist60 recipe (`experiments/reach/build_fw.py 540 OUT 1 1 1`) gives **1488e158** with the flag
  unset or 0, and **4c005042** with it set.
- **When it matters:** it is the fix for CvC carts, which KEEP their seeds for mirror desync, and for any future seeded
  use. Needs an rbf build, which is NOT done here.
- With DRSEEDZERO the leak is moot, so the couch needs no rbf.

## 3. Gates (`experiments/silfid/GATES.txt`; `tools/silfid/gates_final.sh`)

| gate | result |
|---|---|
| negative controls | DRSEEDZERO unset AND =0 rebuild dbbb5007, b1b57638, 5b3d8183 (FAIRPLUS), 5a1695da (FAIR2PLUS) and CvC 821cafdb byte-identically |
| `tools/gate/run_cart_gates.sh` | ALL PASS (8 suites; registers the new `test_seedzero`) |
| gravity-fidelity, `_sz` arms + bases, seeds 5/11/23 × 6000 f | all PASS with counters identical to the base arms; 464a4b75 KILLED on every seed |
| `tests/test_seedzero.py` (new cart DEFECT gate, two-sided) | **Defect side:** shipped FAIR / FAIRPLUS / FAIR2PLUS upload a seed on **93/93, 90/90, 222/222** GOs; DRSEED=0 on **93/93** (the stale seed survives). **Fix side:** every DRSEEDZERO=1 arm uploads **0** |
| `tests/test_tuck_seedmask.py` (new firmware DEFECT gate, py65 on the real emitted tuck_cell_prep + land_place_at) | **Defect side:** shipped image, seeded uploads → **40/40** tuck cells dirty (e.g. seed $13 writes $72/$51 instead of $42/$41). **Fix side:** SEEDMASK=1 → 0 dirty; seed 0 is clean on both |
| fw hex negative control | `DRCOPRO_TUCKV3_SEEDMASK` unset/0 → 1488e158; =1 → 4c005042 |
| `tests/test_lateguard_census_cut.py`, both `_sz` sets | GATE_LGCUT PASS (5 mutants killed) |
| static NMI census, worst admissible frame / 29,780 | DP 27,929 → DP_sz **27,925**; AP 28,001 → AP_sz **27,989** |
| TAP interface (P=2, 40k f) | both `_sz` sets PASS; `everyframe` mutant KILLED |

**What the gates cannot show:** whether silicon's silicon-only misses go away. Emulation attributes only a minority of
them to the seed (section 1). The rest needs the silicon trace (section 5).

## 4. Chained replay before/after
- The Mesen replay serves co-sim timelines, so it is seed-agnostic on the copro side.
- The DRSEEDZERO cart differs from its base only in the uploaded seed nibbles, which the probe already forces to 0.
- **Consequence:** the replays of `_sz` and base are the same experiment. The before/after that matters is the co-sim:
  seed 0 (= `_sz` on silicon) vs the silicon seed classes, in the h16 RESULT section 4.

## 5. Tool: `tools/silfid/ss_cosim.py`, one exact silicon-vs-Verilator comparison per MiSTer save-state

**Requirements:** no new cart, no new rbf.

**What it reads.** A save-state taken while P2's capsule is falling with its search ARMED carries:
- **the exact upload:**
  - the board at `$0500` (the falling capsule is not in the field, and VS garbage only drops between pills);
  - the colours `$0381/2`, `$039A/B`;
  - speedUps / speed `$038A/B`;
  - SEED2 `$6168`;

  the tool rebuilds it byte for byte, the way handle(2) does;
- **silicon's own copro publish:** `$616C / $616D`, the cart's last untorn live read, BEFORE LATEGUARD;
- **the time since GO:** WDOGH2:WDOG2 hooks, at about 2 per frame.

**What it does.** The shipped copro (vsim_pub2, fw 1488e158) runs the same upload. Each snapshot gets one verdict: MATCH,
AMBIGUOUS (within 1 frame of a publish change), MISMATCH_IN_SEQ or MISMATCH_NEW.

**Validation (emulation):**
- 140 synthetic save-states from a Mesen FAIR replay of M1 G4 (`silfid_dump_probe.lua` RAM dumps in the 1,327,112-byte
  container): **117 MATCH, 6 AMBIGUOUS, 0 MISMATCH, 17 unusable**.
- Both mutants are KILLED (the column changed to a never-published value / to the earlier publish).
- The seeded upload rebuild equals the co-sim's encoding on **246/246** samples (seeds $19, $D3).

## Files
- `patch_cartridge_copro.py` (DRSEEDZERO), `fpga/copro/tuck_v3.py` (DRCOPRO_TUCKV3_SEEDMASK).
- Tests:
  - `tests/test_seedzero.py`, `tests/test_tuck_seedmask.py` (new);
  - `tests/test_gravity_fidelity.py` (two `_sz` arms);
  - `tools/gate/run_cart_gates.sh` (+ test_seedzero).
- `tools/silfid/build_carts.sh`, `tools/silfid/gates_final.sh`, `tools/silfid/ss_cosim.py`.
