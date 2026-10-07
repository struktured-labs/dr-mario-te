# RESULT (silicon-fidelity lane, 2026-10-06): DRPUBLOG, a per-pill copro log for exact silicon-vs-Verilator replay

## Why
- **What the first trace showed.** The bluemage save-state trace matched Verilator on 32/32 samples, so silicon's copro
  equals Verilator on identical input (dr-mario-rl h16 `experiments/silfid/RESULT_SILFID_20261006.md` section 9).
- **Why that is not enough.** Every sample was an early-game L20 board, and the couch's unexplained misses are endgame,
  tuck and garbage-window pills.
- **The limit of the method.** One save-state gives one sample.
- **What this cart does instead.** It logs every P2 search, so each save-state yields up to 25 complete pills (exact
  upload + the full read timeline + DONE + the landing).

## The cart (dr-mario-te `claude/silfid-publog`, stacked on `claude/silfid-seedzero`)

**Base `cvcp2`** (`tools/silfid/publog_flags.py`, frozen in `experiments/silfid/cvcp2_flags.json`).

Why this base:
- P2 runs the FAIR couch driver: dbbb5007's flags minus DRSTUDYEND. That includes the garbage-window DRPRESTART +
  DRPRESPIPE, DRPROPH(FIRST), DRLATEGUARD, settle 3 without the pin, and the seeded upload, so the logged searches are
  the couch's.
- The seat / menu config is the CvC cart's, because the couch cart cannot run unattended:
  - its P1 is a human seat and it does not autonav;
  - DRSTUDYEND holds every match end until START.
- The CvC config gives:
  - P1 = the native AI (it clears, so garbage arrives and the prestart path runs);
  - autonav;
  - L11, the couch level, where games reach the endgame (the first trace's L20 games ended early).
- P1 is the SLICED native AI (DRP1SLICE). It is the only native-P1 variant whose frame cost is certifiable next to
  DRPRESPIPE: the PP_RAN phase/slice interlock, #140. The deployed fair CvC cart's unsliced search has a 98,601-cycle
  hook bound.

**Two enabling flags (default 0, byte-identical when off):**
- `DRP1AIHI=1`: the P1 AI + swap_eval at $A040/$A240 instead of $9000/$9200.
  - The couch P2 driver is 4.3 KB, which overflows the 4 KB below $9000.
  - The bank above the RTIVEC probe is empty, and every reference goes through P1AI_CPU (the census capture too).
- `DRSLICEGUARD2=1`: handle(2) sets PP_RAN after a spawn upload + GO, so that hook's P1 slice tick is skipped (one hook of
  P1 latency per P2 pill).
  - Without it: pp_spawn + pp_idle = 30,724, OVER by 944.
  - With it: the worst admissible frame is 27,906 (+1,874).
  - The census's pp_spawn class gets the matching cut, and the premise is checked behaviourally.

**`DRPUBLOG=1` (default 0, byte-identical when off).** Ring layout, from the flag block:

| region | contents |
|---|---|
| header page $6600 | magic 'SLG' v1 (power-on init), slot index, 16-bit pill seq, 16-bit hook counter |
| slots $6700-$7FFF | 25 × 256 B, one per P2 GO (kind 0 spawn, kind 1 prestart) |
| slot +0 | $A7 when complete |
| slot +1..5 | seq, hook counter, kind |
| slot +6..9 | cA cB nA nB exactly as uploaded |
| slot +10..15 | frame counter, event count, viruses, Y, X, nextAction |
| slot +16..143 | the 128 board bytes exactly as uploaded |
| slot +144.. | 18 events × 6 B: [type, hooks, frames, a, b, c] |

Event types:
1. the live mailbox change, i.e. the cart's untorn read, before any gate;
2. DONE (final + tuck descriptor);
3. the cart's target change;
5. the P2 lock pose.

How it is built:
- **The board is TEED inside the existing upload loops.** The handle(2) loop is now Y-indexed: `h2_cp` stays the census
  cut label, and the loop head is `h2_cq`. The prestart `pt_up` loop is the same. Each byte costs one STA (zp),Y,
  ~6 cycles, and there is no second copy.
- **One event per hook at most**, priority DONE > live > target > lock; a deferred one is re-detected next hook.
- **Zero-page pointer:** $CA/$CB, borrowed and restored.
- **Decoder `tools/silfid/publog.py`:** it ties each slot to its sequence number, so stale or power-on PRG-RAM is
  ignored, and it merges snapshots, newest final copy wins.
- **Replay `tools/silfid/ss_cosim.py --publog`:** every final pill's exact upload goes through vsim_pub2 (fw 1488e158).
  - Each live read is judged against the co-sim publish valid at hooks/2.
  - Publications ≥ 1.5 f that the cart never read count as missed.
  - Pill verdicts: DONE vs the final + tuck → EXACT / AMBIGUOUS / DIVERGED / NO_DONE.

## Gates (`experiments/silfid/GATES_PUBLOG.txt`, `tools/silfid/gates_publog.sh`)

| gate | result |
|---|---|
| negative controls (`tools/silfid/build_publog.sh`) | the three flags at 0 rebuild dbbb5007, b1b57638, 5b3d8183, 5a1695da, 90b442c7, 821cafdb and 4dfa9c79 byte-identically; base with DRPUBLOG=0 == base unset (3a310e5b) |
| **debug cart** | **8355ddc7** (`tmp/carts_publog/publog_cvcp2.nes`) |
| static NMI census, worst admissible frame / 29,780 | base without the guard 30,724 (OVER −944); base with the guard 27,906 (+1,874); **DRPUBLOG cart 29,217 (+563)**, worst pair pp_ph4 + pp_idle. The logger costs +1,311 on that pair: the ~770-cycle tee in the prestart-commit hook + at most one event per hook |
| `tools/gate/run_cart_gates.sh` | ALL PASS |
| gravity fidelity, `cvcp2_base` / `cvcp2_publog` arms, seeds 5/11/23 × 3000 f | PASS with identical counters; the 464a4b75 pin is killed on every seed |
| `tests/test_lateguard_census_cut.py` on this flag set | GATE_LGCUT PASS (5 mutants killed). The test's aborted-hook model got the #140 interlock cut on combined (PRESPIPE+P1SLICE) images, the same cut the census gives every pipeline-work class (pre_tick sets PP_RAN before jumping to pp_disp); without it the model charged a slice tick the guard excludes (17,200 vs 11,159). It is a no-op on the couch image |
| `tests/test_publog.py` (py65, the real driver, ROM-rule P2 world + re-armed P1 slice) | RING: every GO's slot == the bytes written to the window (prestart kind included); LIVE: events ⊂ published, no long-lived publication missed; DONE / LOCK == truth; ZP: $CA/$CB unchanged across every hook; GUARD: no hook both uploads and ticks the slice (1,272 ticks); **mutant DRSLICEGUARD2=0 KILLED** (8 such hooks) |
| **Mesen** (`tools/silfid/publog_validate.py`, chained M1 G4 replay with garbage, RAM dumps every 60 f) | **148/148** logged pills == the GO uploads (10 prestart), 0 seq gaps; **334/334** live events inside the case timelines; **0/277** long-served values missed; DONE **51/51**; lock **134/134** |
| **Mesen end-to-end** (`ss_cosim.py --publog` on the same dumps: decode → Verilator co-sim of every logged upload → judge; `MESEN_PUBLOG.txt`) | **every case GO 134/134: 128 EXACT + 6 AMBIGUOUS, 0 DIVERGED**. The 10 DIVERGED are the probe's own non-copro answers, so the comparator flags exactly what it should: the 3 warm-up GOs got the FILLER schedule; 7 of 10 prestart GOs were served the NEXT case's tracker-board timeline while the cart uploaded its projected board with the probe's synthetic garbage colours (3 of 10 happened to coincide → EXACT) |

## Kit + capture
`dr_mario_rl/tmp/couch_kit/publog_20261006/` (BUILD.md has the exact install / load / capture steps):
- the cart, plus `PUBLOG_CVC.mgl` on rbf 318607aa;
- `ring_capture.sh --interval 10` for 60 min, keeping every .ss;
- the ring spans about 40 s, and states land every ~20 s.
