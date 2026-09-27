# DRREACH — reach-root pre-filter (copro firmware) + DRREACHTX transport (cart)

STEER2 (h16-wt `experiments/cvx/RESULT_STEER2.md`) passed its pre-registered bar under the steering-faithful
simulator:
- **Survival:** tap≤100 fell from 28.8% to 9.8% (−19.0 pp [−22.7, −15.3]).
- **Race:** +17.0 pp.

Spec and Python reference: `reach_fw.py`, copied verbatim from h16-wt (md5 a3291879).

## What ships
- **Firmware** `DRREACH=1` (`tests/test_search_d3.py`, `fpga/copro/build_copro_d3.py`, `fpga/copro/reach_6502.py`):
  - A 1,439 B mask routine at `$A800` (the v1-tuck window; its RAM is `$0A80-$0AD9`, zp `$B6-$C9`).
  - The search `JSR $A800` after the board upload.
  - Pass 0 skips legal candidates with `R_FLT && !ROK[o4*8+col]`; an all-masked Pass 0 reruns unfiltered.
  - Search +38 B. Default 0 is byte-identical.
- **Cart** `DRREACHTX=1` (`patch_cartridge_copro.py`):
  - Both P2 GO paths (`handle()` and the DRPRESTART commit) OR P2's speedUps ($038A) and speed+1 ($038B) into the
    free high nibbles of nA/nB.
  - Default 0 is byte-identical.
  - The "+1" is a DELIBERATE DEVIATION from the STEER2 spec: a transport cart never sends a zero NB high nibble, so
    the firmware treats zero as "old cart, no filter".
- **Pairing:** filtering is live only with a DRREACH firmware AND a DRREACHTX cart. Either half alone runs today's
  search (G1a/G1b).

## Gates (all PASS 2026-09-25)
| gate | file | result |
|---|---|---|
| G0 firmware identity | `build_fw.py 540 … 0` | DRREACH=0 = shipped CHAIN540 **6d13e6a1** (and 180 = Childproof a2b2e4ac) |
| G0 cart identity | recipes in CHAIN540_REACH_BUILD.md | DRREACHTX=0: couch = **4b4fce5e**, CvC = **9f20c795** |
| G2 mask bit-exact (py65) | `gate_reach_mask.py` → GATE_REACH_MASK.txt | see below |
| G1/G3/S whole search (py65) | `gate_reach_search.py` → GATE_REACH_SEARCH.txt | see below |
| cart transport | `gate_reachtx.py` → GATE_REACHTX.txt | see below |
| cart hazard gates | `tools/gate/run_cart_gates.sh` | ALL PASS |
| NMI cycle census | `tools/nmi126` | couch 14/14 OK, CvC bounds unchanged ±71 |

- **G2 mask bit-exact:**
  - 7,412 boards: 1,412 real L11/L15 couch-steering game boards plus 6,000 synthetic.
  - 404,536 legal-candidate checks, with both empty encodings: **0 mismatches**.
  - Transport decode: 150/150.
  - 4/4 mutants killed: T_LAT±1, DISTGATE off, fallback off.
- **G1 / G3 / S whole search:**
  - **S (static audit):** 8/8 S_NA/S_NB reads are LDA+AND #$0F.
  - **G1a (random nibbles inert):** 120/120.
  - **G1b (old cart = today's search):** 120/120.
  - **G3 (firmware = masked golden mirror):** 240/240. The filter moved the argmax on 51 boards.
  - Mutants killed: PENALTY and NOAND.
- **Cart transport:**
  - The py65 nibble code equals `pack_nibbles` for every (speed, speedUps).
  - The NB high nibble is never 0.
  - The blocks appear at exactly the expected sites: couch ×2 (handle + prestart), CvC ×1.
  - The opcode-level diff against the DRREACHTX=0 cart is exactly those inserted runs.
- **NMI cycle census:** worst spawn-edge path +78 cycles.

## Reproduce
```
python experiments/reach/synth_corpus.py 6000          # corpus/synth.jsonl (gitignored, deterministic)
python experiments/reach/gate_reach_mask.py --synth 6000 --mut-boards 800
python experiments/reach/gate_reach_search.py --game 120 --fast 80 --few 40 --g1 80 --workers 10
python experiments/reach/gate_reachtx.py <cart.nes> <expected sites>
```
The game corpus (`corpus/game_l1{1,5}.jsonl`) comes from h16-wt `experiments/cvx/reach_corpus_dump.py`
(gate-(b) fw540, owner model, couch steering, seeds 36734.. step 2 at L11, 40134.. step 2 at L15).

## Known limits
- The tuck root extension (tuck_bfs) runs after the search and may still publish a tuck whose approach the mask
  never saw. This is unchanged from today; the mask covers straight-drop root candidates only, as in STEER2.
- T_LAT = 19 frames is TODAY's silicon answer latency. The filter shrinks Pass 0, so answers get faster and the
  mask becomes conservative, not wrong.
- DRPRESTART sends the gravity state at lock time. speedUps can tick once between the lock and the spawn (every
  10 pills), so thr may be stale by one step for that one pill.

# DRTAPP — tap steering up to the controller-interface limit (owner ruling 2026-09-25)
The AI may steer faster than a human, but never faster than a real pad. The game samples the pad once per frame, and
a press edge needs a released frame before it, so the ceiling is one press per 2 frames.

## Cart dial `DRTAPP=P` (unset/0 = today's DAS, byte-identical; 2..15; 2 = the ceiling)
- **One shared press scheduler for every P2 press edge (A/B rotation, L/R lateral, PROPH pulse).**
  - Frame-start bookkeeping at `act` (first hook pass of a game frame, keyed to `$43`) captures the ROM's held byte
    `$F8` = the TRUE previous-frame pad, and advances a cooldown.
  - The TAP FILTER at `act_p1` (every P2 path ends there) lets a press intent through only if the cooldown is 0
    and the bit was released last frame; otherwise it drops the intent. Holds (DOWN) pass through.
  - The filter restores `$F8`, so the driver can never manufacture an edge.
- **Interactions (code read + the emulated gate below):**

| path | behaviour under DRTAPP |
|---|---|
| **rotation** | Today's `held:=0` idiom (a fresh A/B edge every frame) is neutralised; rotation taps every P. |
| **lateral / WEAVE** | L/R intents are tapped every P. The pill falls at natural gravity (never pinned). No DAS component remains. |
| **DISTGATE** | `DIST_DASEDGE = 2P` hooks/column. At P=2 the budget is `min(7, 7y)`, so it clamps only at y=0 (no free row under the span) — the same zero-budget condition the reach mask models. |
| **SLAM / COLGATE / stuck force-drop** | DOWN holds pass unchanged. The ROM's fast drop needs DOWN alone on the d-pad, and the driver only slams when aligned. |
| **PROPH** | Requests its direction every hook; the scheduler spaces it at P. The first press is on the detect frame. It no longer uses the `$43`-parity idiom, which is the P=2 special case. |
| **DRPRESTART** | A GO path with no pad writes; its transport carries P like `handle()`. |
| **TUCK** | Lateral taps are faster than DAS. TUCKGUARD's bound is DAS-free (1 row/column), so it is unchanged and conservative. |

- **Transport (with DRREACHTX):** P rides the nA/nB colour LOW-nibble bits 2-3 (nA[3:2]=P[1:0], nB[3:2]=P[3:2]).
  - Every search read of S_NA/S_NB is `LDA; AND #$0F; STA $70E2/$70E3` (engine colour-arg registers; static audit).
  - The RTL keeps only DO[1:0] there, so the bits are dead to the search. Older firmware ignores them.

## Firmware `DRREACHTAP=1` (needs DRREACH; default 0 = the DRREACH fw d8014d77, byte-identical)
- The reach routine decodes P (<2 → DAS model) and applies the tap timing.
  - PROPH presses at F0, F0+P, …; the first answer press at `max(T_LAT, last PROPH + P)`.
  - Rotation attempts every P; a blocked attempt spends its slot.
  - Lateral presses start at the last rotation press + P, then every P.
- `reach_fw.py` gained `tap=P` (tap=None is unchanged: 0 diffs vs the banked masks).
- One TAP firmware serves both DAS reach carts (P=0) and tap carts.

## Gates (all PASS unless noted)
- **Identity:**
  - DRTAPP off reproduces couch 4b4fce5e / 09cdb6ae and CvC 08211ef4 / 9f20c795 / 2291a61d.
  - DRREACHTAP=0 reproduces fw d8014d77; DRREACH=0 reproduces 6d13e6a1.
- **G2 mask bit-exact, tap routine** (`gate_reach_mask.py --tap --taps 0,2,3`):
  - 0 mismatches at P=0, 2 and 3 on 7,412 boards (404,536 checks each).
  - Mutants killed: T_LAT±1, DISTGATE off, fallback off, and the new `rot_das` (rotation stepping 1 frame).
  - GATE_REACH_MASK_TAP.txt.
- **G1/G3 whole search, tap firmware** (`gate_reach_search.py --tap`), GATE_REACH_SEARCH_TAP.txt:
  - Static audit: every S_NA/S_NB read lands in LEV_A_CA/CB.
  - G1a (random high AND low-nibble bits inert under DRREACH=0): 102/102. G1b: 102/102.
  - G3 firmware == masked golden mirror: 243/243 (81 each at P=0/2/3).
  - PENALTY and NOAND mutants killed.
- **INTERFACE COMPLIANCE** (`gate_tap_interface.py`, GATE_TAP_INTERFACE.txt):
  - Method: the REAL emitted driver under py65, closed-loop with a ROM-rule world + an emulated copro, two hook
    passes per frame, and the ROM's AND / pressed / held semantics.
  - Checks: C1 no manufactured edge (pressed == R & ~R_prev); C2 never a press on consecutive frames; C3 press
    spacing ≥ P.
  - Couch P=2 ×3 seeds and P=3 ×2, CvC P=2 ×2: **0 violations over 280,000 frames** (≈5,900 pills, ≈5,100
    searches); the minimum gap equals P.
  - **Mutant `everyframe`: KILLED** on both carts (C1/C2/C3).
  - ⚠ **Baseline, today's DAS driver (dial off): FAILS C1/C2** about 1,600–1,800 times per 40k frames, all on
    the A button. The DAS-era rotation forces held := 0 and manufactures a rotation press every frame, faster than
    a real pad. Lateral DAS is compliant.
  - Info: hook passes disagree on ≈10 frames per 40k (the ROM ANDs them, so this is harmless). ≈1.4% of frames
    change more than one button, e.g. a tap release and a DOWN hold together. That is ONE sampled pad state per
    frame, which a physical pad can produce.
- **Cart hazard gates:** ALL PASS. **PRG RAM map** regenerated: no collisions; TAP_* declared at $61D0-$61D3.
- **NMI census:**
  - Couch tap: 14/14 OK; worst spawn-edge 15,308 cycles; same-frame pair 27,872 < 29,780.
  - CvC tap: bounds +79..+155 cycles vs the DAS cart.

## Timing notes for the steering sim (STEER3 alignment)
1. ONE scheduler: the next press of ANY button comes no sooner than P frames after the previous press.
2. Rotation taps at P. Today's DAS driver rotated every frame, via the manufactured edge above.
3. PROPH: the first press is on the detect frame (F0=3), then every P. The first answer press is at
   max(T_LAT, last PROPH + P).
4. The first lateral press is P after the last rotation press (or the first free slot if no rotation), then every
   P. There is no DAS 16/6 anywhere.
5. In the harness, the first press after the answer is published comes after a median of P frames.
