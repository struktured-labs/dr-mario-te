# DRTUCKGUARD stranding A/B — RESULT 2026-09-07 (Mesen, CRN-paired)

**The guard prevents stranding: 96% -> 7%** (13x), identical across seeds 7/13/29/41/53.

| arm | strand rate | pills placed |
|---|---|---|
| baseline (guard OFF) | 0.957 (22/23 strand in the approach column) | 23 |
| guard-ON | 0.071 (39/42 reach target) | 42 |

## How it was measured (the harness that finally works)
- **Two prior blockers fixed:** (1) `crn.lua`/`engage.lua` called `emu.write(a,v,NES,false)` — 4 args,
  but emu.write takes 3 — which errored on the seed-force and gave a false `pills=0` on EVERY run;
  (2) the Mesen copro_emu (`tools/copro_emu.lua`) serves only the DONE/col/orient mailbox fields
  ($84/$85/$86), NOT the tuck descriptor at $87/$88 (`W_TCOL`/`W_TROW`), so `TUCK_C2` read open-bus
  garbage (0x52) and the guard vetoed 100% of GARBAGE tucks (not a defect).
- `copro_emu_strand.lua` serves a stranding-prone tuck: W_TCOL = target+2, W_TROW = 13 (LOW trigger
  => short fall). `copro_emu_tuck.lua` serves a payable one (target+1, high trigger) to show the
  ALLOW path fires (10/42 allowed, 0 over-vetoes).
- `crn6_stranding.lua` measures the prereg PRIMARY: PX2 ($0385) = P2 capsule column; stranded = its
  lock column (1 frame before the next spawn) != target `TGT_C2` ($6152).
- Mesen build: dr-mario-mods `.../Release/Mesen` + gate sandbox settings (the harness's own
  mesen2-vsrules build also gives pills=0). Seeds forced via SEED1/SEED2 ($6167/$6168).

## Caveats (load-bearing; see memory dr-mario-tuckguard-successor-lane)
1. SYNTHETIC descriptor — proves the guard STOPS a strander, not how OFTEN the real firmware emits one.
2. Near-deterministic substrate (dumb brain + fixed descriptor) => seeds are mechanistic replicas.
3. NOT the end-to-end outcome (tap-outs / pills-to-clear vs Childproof) — the couch A/B is still owed.
