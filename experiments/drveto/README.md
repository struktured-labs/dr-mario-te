# DRVETO -- spawn-plug veto, variant (a+), against dblcanon b03a586e

Owner ruling 2026-08-30 ("ok, go for it"): arm = dblcanon b03a586e; gate
amendment in force.  Spec + history: memory dr-mario-spawnplug-verdict.md.

## What ships
`DRVETO=1` (env knob, default 0) in the `tests/test_search_d3.py` emitter,
engine variant only (the dblcanon build is `USE_ENGINE=True`):
1. per-search viruses-remain scan of the untouched root board at $0500 -> zp
   `D_VIRF` ($B5);
2. per-root-candidate predicate at the ROOT-REPLAY site (C1: right after the
   candidate's own CMD-4 NODE, where LEV_RVC/$70E9 and LEV_WIN_R/$70F2 are
   FRESH -- by o_cand the ply-2 loop has clobbered them) -> zp `D_VETO` ($B4);
3. penalty at o_cand: val1 -= 20000, 16-bit signed with SATURATION at -32767,
   after the DRSTRAND subtraction, before the jitter.  Penalty, never removal
   (note A): a fully-plugged parent still yields a move, and any CLEARING
   candidate (never vetoed) outranks every vetoed one.

Predicate (veto_plug + rv/win/virf conditions) = variant (a+): fire iff the
candidate's no-clear resolution leaves a cell in (0,3)/(0,4) while viruses
remain.  Geometry arms: parent-plugged; VERTICAL col 3/4 with fo<=2;
HORIZONTAL resting at row 0 whose span covers col 3 or 4 (cols 2-3, 3-4, 4-5
-- the spec's ruling clause; its parenthetical named only 3-4, but spans 2-3 /
4-5 place a cell in the throat identically, and the fired-on set stays provably
fatal-at-next-spawn, so zero-harm is preserved by the same construction).

## R29 answer: world (a)
The firmware enumerator CANNOT generate G3's fo==1 vertical.  Evidence:
- RTL: `fpga/copro/LeafEval.sv:468-476` -- S_FO1 vertical branch: "vertical:
  legal iff fo>=2"; `if (fwp >= 5'd2) ... legal <= 1'b1` else done, legal=0.
- py65 engine model: `dr-mario-mods/tests/nes_d2_golden.py:75-80` `_landing`
  vertical `if fo < 2: return None`.
- The firmware p0 loop (`tests/test_search_d3.py`, engine variant) enumerates
  all 32 (o4,col) and keeps only `LEV_LEGAL != 0` -- legality is the engine's.
G3's exact vertical is therefore an executor/commit artifact (mid-flight
rotation), the fo<=2 vertical arm is cheap insurance, and the generable half of
G3's lethal family (the horizontals, which DO fire on that parent) is covered.

## Budget (MEASURED from the b03a586e hex)
Search-region free space (to TUCK_BFS_ROM $9000, the binding bound): 1,463 B.
DRVETO=1 adds +179 B (search 2,633 -> 2,812 B) -> 1,284 B remain.  Cycle adds:
one 128-cell scan per search + ~50 instructions per root candidate ~ <10k
cycles/search = ~116 us @ 85.9 MHz -- negligible (review nit fixed: an earlier
report quoted 70 us for the same 10k cycles; 10k/85.9e6 is ~116 us).

## Gates
- `DRVETO=0` byte-identity: `build_dbgpub.py` under the FW_RECIPES
  s20t3_th400dblcanon env -> md5 b03a586e8316ccf6741a15ac70123886, `cmp` clean
  (tmp/drveto/veto0*.hex).  Verified again after every emitter edit.
- `gate_drveto.py` (GATE_RESULT.txt): py65 firmware vs bit-exact mirror,
  identity/bind/parity/flag-set/control/fires/note-A + killed mutants
  M1_fobound (wrong fo bound), M2_ocand (the C1 stale-read trap, emitted via
  the test-only `_VETO_AT_OCAND` hook), M3_inert.  The mirror models DRSTRAND
  (the ship recipe carries DRSTRAND=20; the first gate run caught the missing
  term as an fw-vs-golden divergence -- prior gates never built with the
  recipe env).
- `gate_owner_boards.py` (OWNER_GATE_RESULT.txt): the two reconstructed
  owner-match suicide parents (g2_parent/g3_parent.json, decoded from
  plugpred g2d/f0023.png and g3d/f0030.png).  PASS: predicate fires on both,
  firmware==mirror on both, DRVETO=1 never plugs the throat.  Virus flags and
  the colour bijection are INFERRED (disclosed in the script docstring).

## Not run here (next steps, per the workflow)
- zero-harm replay over the banked 116k-ply corpus (s16 machinery);
- the pinned-seed Quartus compile on blackmage + fw-in-image bijection check;
- hardware deployment (separate owner/team-lead decision).

py65-gate scope note: the gate builds USE_DELTA=False (attach_engine_emu has
no CMD-6/7); the ship hex is the delta build.  The DRVETO emissions are
byte-identical in both variants and the root-replay site is CMD-4 in both;
delta-vs-base equivalence is covered by the existing co-sim battery.

## CLOSEOUT 2026-08-30 (supersedes "Not run here" above)
Adversarial review verdict: APPROVE, no code defect; all demanded fixes applied
here.  The two formerly-outstanding gates have now RUN:

- **Zero-harm replay (workflow gate 4): PASS** -- `gate_zero_harm.py`
  (ZERO_HARM_RESULT.txt).  The banked 700-game farm (admission 100%, 116,458
  plies) replayed against the SHIPPING predicate `veto_plug` itself + the
  firmware's exact rv/win/virf conditions, on the chosen move: **2 fires, BOTH
  terminal topouts** (c1_L11_bursty s30152 ply 162/162; c5_L20_bursty s32148
  ply 314/314), **0 non-terminal fires**, 0 divergences from the s16 analytic
  predicate, 0 recorded plies with a plugged parent.  The widened horizontal
  arm and the fo<=2 insurance arm changed nothing on the corpus -- the
  pre-implementation witness carries over to the real implementation.
- **Quartus compile (workflow gate 5):** see COMPILE_RESULT.md (pinned SEED 13,
  ship_build.sh route, fw-in-image bijection vs 3 controls incl. the 2-byte
  theta control).
- Review should-fix DONE: `s20t3_th400dblcanon` (b03a586e) and
  `s20t3_th400dblcanon_veto1` (47edb895) are now REGISTERED in
  experiments/cosim_farm/FW_RECIPES.json and /mnt/data/drmario_cosim/fw/
  RECIPES.json, with RECIPE.json sidecars next to both artifacts
  (fw/th400canon/, fw/th400dblcanon_veto1/ -- the latter holds a byte-verified
  copy of veto1.hex).  Nits fixed: cycle-math above; gate_drveto.py's faithful-
  sim fallback no longer hardcodes one spelling of the rl worktree path.
- Still NOT validated by anything here: on-silicon counterfactual rescue (the
  py65 DRVETO=0 arm never chose the fatal move -- softer leaf than the RTL
  chain leaf), delta-vs-base equivalence beyond the existing co-sim battery,
  VS-mode catch under garbage, and live-fire behaviour under a real soak.
  Deployment is a separate team-lead decision; nothing was deployed.

## FIX A 2026-08-30 (post-repro-verdict): ANYTIME PUBLISH SUPPRESSION
The wf_5acb84d3 repro verdict exonerated the veto's final answer but found a real
hole: the s_loop live-publishes the running best to S_BEST_C/O ($6134/$6135)
with the veto penalty APPLIED but the store UNSUPPRESSED -- iteration 1 always
beats the $8000 sentinel, so on a board whose pass-0 argmax is vetoed, the
lethal candidate IS handed to the pre-DONE driver (mailbox invalid=$FF until the
first store, test_search_d3.py:513; driver treats orient=$FF as no-result,
patch_cartridge_copro.py:257; DRSLAM/MIN_THINK act on the interim, :266-330).

CHANGE (tests/test_search_d3.py, publish site, +4 B): after the DBLCANON
rewrite, `LDA D_VETO / BNE s_next` skips the two S_BEST stores when the
new running best is vetoed.  Internal best (D_BV*/D_BC/D_BO) still updates, so
the FINAL answer -- published unconditionally by the stub at DONE
(build_copro_d3.py stub epilogue) -- is byte-for-byte what it was: note A
(penalty, never removal) is untouched, and on an all-vetoed board the vetoed
best still reaches the driver at o_done via that stub store.  The spec clause
"while ... no unvetoed candidate has yet been published" is subsumed by the
strict form: a vetoed candidate could only displace a published unvetoed best by
out-margining the 20000-unit penalty, and suppressing that store too is the
strictly safer direction (the final at DONE delivers it anyway if it truly is
the argmax).  MEASURED: veto2 search 2,816 B (veto1 2,812; b03a586e 2,633);
DRVETO=0 rebuild == b03a586e byte-exact; cycle cost ~5 cycles per new-best
iteration.

### Zero-harm argument for holding $FF longer (honest form)
Behaviour changes ONLY on searches whose running best is vetoed at some
iteration -- i.e. the pass-0 argmax prefix is vetoed (a later vetoed candidate
cannot beat an unvetoed best through the penalty).  Call the window from
iteration 1 until the first unvetoed running best "the suppressed window"
(measured on the G2 corpus: 1-4 iterations; ~1-4 ms of s_loop time at the
~116 us/candidate scale, MEASURED clocks in g1_cosim outputs).

Case 1 -- an unvetoed candidate exists (the common fired case).
  Unfixed: the driver may act on the vetoed interim through the whole window:
  DRSLAM can commit it (fast-drop on a stable published argmax,
  patch_cartridge_copro.py dn_p2), and every firing-set placement is
  PROVABLY FATAL-AT-NEXT-SPAWN by the (a+) construction -- acting on it is a
  certain loss when it locks.  Fixed: the driver sees $FF, i.e. its documented
  no-result path (the state every search starts in): no slam target, park/weave
  at natural gravity, retarget on the first valid store.
  - The slam hazard is one-directional: only the unfixed arm can commit a
    provably-fatal move during the window.  Removing it cannot create a loss
    that the unfixed arm avoids, because the unfixed arm's extra behaviour IS
    the fatal commit.
  - The residual that keeps this from being a theorem: POSITIONAL side-effects.
    During the window the unfixed driver steers TOWARD the fatal target; the
    fixed driver parks.  If the capsule locks during the window, both arms lock
    in the throat neighbourhood (every firing-set target and the spawn columns
    are the same cells 2-5 at row 0) -- equally fatal, no difference.  If the
    capsule survives the window, the arms differ only in lateral position when
    the first valid answer arrives; that difference is UNSIGNED (the interim
    path can pre-position better or worse for the eventual target).  The
    conjunction required for the fixed arm to lose a game the unfixed arm wins:
    (argmax-vetoed board) AND (margin so tight that 1-2 DAS edges decide
    reachability) AND (the fatal-target path happens to point at the true
    answer) AND (the unfixed arm did NOT slam the fatal interim first).  We do
    not claim this set is empty -- we claim every element of it is also a board
    where the unfixed arm's slam lane is live, and the slam commits a certain
    loss while the positional edge merely improves a chance.  INFERRED, not
    measured: no full-game A/B can see any of this at the 2-in-116,458-ply base
    rate (the mandatory-disclosure clause of the gate amendment applies).
Case 2 -- ALL candidates vetoed (note-A boards: plugged parent or throat-only).
  The mailbox stays $FF for the entire search + tuck phase; the driver waits
  for DONE (its pre-anytime behaviour) and then receives the vetoed best from
  the stub.  Tempo cost: the anytime slam window is forfeited.  Outcome cost:
  ZERO -- on an all-vetoed board every placement is fatal-at-next-spawn, so
  timing cannot change the result, only the wait.  MEASURED: goldens 0-2 and
  traj_c5 in the G2/G1 corpora are exactly this class; final still delivered
  (T3), never a wrong answer.
Case 3 -- the veto never fires (>=99.99% of plies, 116,458-ply witness).
  The suppression code reads one zp byte and falls through; trajectory
  byte-identical to the unfixed build (G2/T5 control, MEASURED).

What the suppression can NEVER do, by construction: change a final answer
(G2/T4 + G1 delta==base, MEASURED over the whole corpus incl. M4 whose finals
match while its trajectory differs); promote a vetoed candidate (the penalty
and saturation are untouched); or alter DRVETO=0 bytes (b03a586e identity,
MEASURED).

SCOPE NOTE (pre-existing, not introduced here): the tuck extension
(tuck_v3.py emit_tuck_root_extension) publishes its own candidates without a
veto flag; a tuck can never rest at row 0 (a tuck requires an overhang above
the landing cell, and there is no row above row 0 -- INFERRED from geometry),
so tuck pubs cannot plug the throat.  The stub's final store and tuck pubs read
zp $B4 as STALE after the s_loop; instruments must therefore phase-separate
(the G1 tb and the G2 reference both do).
