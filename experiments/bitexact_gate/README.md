# bitexact_gate — leaf-eval bit-exactness validation gate

Proof chain (all links machine-checked, no hardcoded goldens):

    candidate (delta-eval / Rust)  ==  numba _eval_rtl (combo_term/fast_rtl_x.py)
    numba _eval_rtl                ==  LeafEval.sv  (Verilator co-sim, LEAF + NODE)
    RTL CMD6/7 delta engine        ==  RTL full NODE recompute  (bonus cross-check)

The RTL's weights/flags are **parsed from the .sv being co-simulated** (rtlparse.py),
never hardcoded — a re-tuned combine, a drifted matched-site, or a brand-new term
either parses into the comparison or fails LOUDLY. This is the structural defense
against the "golden is weekend-era" failure mode.

## Quickstart

    PY=/home/struktured/projects/dr_mario_rl/tmp/venv/bin/python
    RC="/home/struktured/projects/dr_mario_rl/tmp/runcapped 8"
    cd /home/struktured/projects/dr_mario_rl/tmp/bitexact_gate

    $RC $PY gate.py selfcheck                       # gate proves ITSELF (mutants must all die)
    $RC $PY gate.py rtl                             # numba vs RTL; BLESSES the reference
    $RC $PY gate.py candidate --py my.py:leaf       # your leaf vs the blessed reference
    $RC $PY gate.py pairs     --py my.py:pair       # delta-shaped candidate
    $RC $PY gate.py candidate --cmd './my_rust_bin' # subprocess candidate (Rust)
    $RC $PY gate.py repro --file results/fail_...   # replay a failure w/ term breakdown

Exit codes: 0 pass, 1 fail, 2 config error. Verdict lines grep as `GATE PASS|GATE FAIL`.

`--rtl <path>` selects the LeafEval.sv to gate against (default: NES_MiSTer-winner).
Known-good alternates: dr-mario-canonical-wt (r47-weights + delta engine),
dr-mario-qa-wt (legacy weekend structure) — all three parse.

## Candidate contracts

**Level 1 (leaf), in-process python/numba** — `fn(col, vir, w, fl) -> int`
- `col` int8[128] row-major from top, 0=empty, 1..3=color; `vir` int8[128] 0/1
- `w` float64[16], integer-valued, fast_rtl_x layout (indices 0..10 = bias, maxh,
  holes, toprisk, spawn, setup, matched, buried, rdyext, vrdy, poll; 14 = cross)
- `fl` int32[3] = (color_aware, nearest2, matched)
- return the S_DONE2 score with **signed-16 wrap** (compute the sum in >=48-bit
  signed, then wrap: `s &= 0xFFFF; if s >= 0x8000: s -= 0x10000`)

**Level 1, subprocess (Rust)** — one request line on stdin per case:
`bias maxh holes toprisk spawn setup matched buried rdyext vrdy poll cross
f_colaware f_nearest2 f_matched <128 hex NES cells>`; NES cells: `ff` empty,
`d0|c` virus, `40|c` pill, c=0..2. Respond one signed decimal score per line.
Reference implementation: `examples/candidate_stdin.py`.

**Pairs (delta-shaped)** — `fn(pcol, pvir, variant, column, pa, pb, w, fl) -> int`
- placement in **fast_sim convention**: variant 0..3 (0/1 horizontal a-first/b-first,
  2/3 vertical), column 0..7, pa/pb colors 1..3
- pairs are guaranteed legal and **no-clear**; return the child-board leaf score
- NOTE the RTL mailbox o4 is `variant XOR 2` (empirically recovered from the pinned
  node corpus, map (2,3,0,1) — the gate handles this; candidates never see o4)

## The blessing interlock

fast_rtl_x.py is concurrently edited (delta-eval lands in the same file). A level-1
PASS is only meaningful against the exact `_eval_rtl` source the co-sim proved, so:
- `gate.py rtl` PASS writes `results/reference_blessing.json` (sha256 of the
  imported `_eval_rtl` source <-> RTL md5)
- `gate.py candidate|pairs` refuse to run if the current source hash differs
  (override for provisional runs: `--unblessed`)

## Corpus (pinned; `gate.py corpus --force` to rebuild)

948 boards, 21 classes: empty, full x5 kinds, single_virus(45), virus_on_stack(27),
buried_suite(60: cover-run x color x depth + nearest-2 cap), matched_suite(15),
exact4(24: formed/open/span-blocked runs), cross_suite(12: both-axis gating),
near_win(6), no_clear(6), cascade(9, incl. unsettled/floating), spawn_toprisk(14),
wrap_stress(16), rand_settled(120), rand_scatter(60), real boards(524: pinned RTL
leaf corpus 205 + hostdata_real 69 + node-corpus parents 250).
Plus 4494 placement records (node_cases.txt) / 3147 no-clear pairs (pairs_noclear.txt).

23 weight variants per level-1 run: shipped named sets (r47, winner, vrdy12,
weekend_burial, combined, cross8, parsed_rtl), 12 single-term isolation vectors
(any term miscount fails exactly one, so failures self-attribute), flag-off
isolations, and 2 wrap-stress vectors (multi-wrap both signs).

## What is covered / NOT covered

Covered: the LEAF eval (all terms, flags, signed-16 wrap incl. 1x/2x/3x positive
wraps at RTL weights and both signs at level 1), NODE mechanics (land, legality,
cap-1 targeted resolve, child board cell-exact, imm), RTL CMD6/7 delta vs full
recompute (3751 legal no-clear + 743 clear-fallback assertions).

NOT covered — do not over-claim:
- the SEARCH above the leaf (_choose_d1/d2/d3, topK pruning, imm-vs-leaf mixing)
- negative prewrap (< -32768) at FIXED shipped weights: unreachable on real
  boards there; exercised only via level-1 extreme-weight vectors (negheavy)
- multi-step cascade resolve (both sides implement cap-1 by design; boards WITH
  cascade potential are scored, the cascade itself never runs)
- CoproDrMario.sv mailbox/driver plumbing (sim_mister.cpp covers that, separately)
- non-integer or out-of-range weights (weights are integer-valued by contract)

## Files

gate.py (CLI) / rtlparse.py (SV constant parser) / corpus.py (board generator) /
pyleaf.py (independent term-level port + 18 mutants) / common.py /
tb_leafeval_gate.cpp (Verilator tb: LEAF + NODE + optional CMD6/7 delta phase) /
corpus.txt, node_cases.txt, pairs_noclear.txt (pinned) / results/ (verdicts,
reproducers, blessing) / examples/ (good, bad, subprocess-protocol candidates)
