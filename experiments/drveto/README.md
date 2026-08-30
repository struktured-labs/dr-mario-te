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
cycles/search @ 85.9 MHz -- negligible.

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
