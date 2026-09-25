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
