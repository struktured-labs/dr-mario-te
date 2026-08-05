# Cart fix report — task #49 follow-on (fingerprint, candidate, defect test)

Scope: `dr-mario-mods-wt/driver-nav` only (branch `driver-nav`). No files under `/media`, the
MiSTer, or any `.rbf`/`.rev`/hex were touched. Mesen was not launched (headless py65 only, per
task constraints). All new artifacts live under `tmp_carts/` (gitignored) and `tests/`
(committed). `roms/manifests/_*.json` scratch manifests produced while building references are
also gitignored (pre-existing pattern).

Reads first, in order, as instructed: `dr-mario-qa-wt/experiments/eval47/PAIR_LATCH_AUDIT.md`
(design doc + §6 adversarial REVIEW) and `dr_mario_rl/tmp/film_review_20260804/recon/VERDICT.md`
(the H1 m3-topout adjudication this all rests on).

## 0. Headline

**Fingerprint verdict: FIX PRESENT.** The local copy of the v4 fast+coldinit cart
(`pocket_human_v4_coldinit.nes`, md5 `24dcd9dca5db8b7a21c93b2bb30f124b`) reproduces **byte-exact**
from `driver-nav` HEAD (`121cba1`) using its own recorded manifest — and that manifest's flags
leave `DRROTFIX`/`DRCOLGATE`/`DRRECOMMIT`/`DRSLAM` at their code defaults (all ON), plus
explicitly add `DRRECOMMIT_NOFREEZE=1` for the one reason that flag exists: to extend the
orientation-relatch fix onto this profile's `DRNOFREEZE=1` setting. Every one of driver-nav's
four Pocket-tagged manifests (`classictempo`, `latchfix`, `studycounts`, `v4-coldinit`) — and the
one archived `historical/human-latchfix.json` from before any of them — carries this same
`DRNOFREEZE=1 DRRECOMMIT_NOFREEZE=1` pair. As far as driver-nav's own build history goes, the
pair-latch fix has been part of **every Pocket cart this branch has ever built**, going back to
the commit whose message literally reads "the cart now ON THE POCKET."

**The requested candidate build is byte-identical to what's already shipping.** `DRROTFIX=1
DRCOLGATE=1 DRRECOMMIT=1 DRSLAM=1` on top of the v4 profile produces md5
`24dcd9dca5db8b7a21c93b2bb30f124b` — same as the shipping cart, because those flags were already
at their defaults. There is no new fix to land here; task 2 below documents that explicitly
rather than presenting a diff that doesn't exist.

**One correction to the audit's premise, found while fingerprinting:** `PAIR_LATCH_AUDIT.md` §0
frames "Pocket/freeze-class" as `NO_FREEZE=0` (true on the `copro-canonical` tree it was written
against). The actual driver-nav Pocket lineage instead ships with `DRNOFREEZE=1`. Since the
`dn_p2` gate is `if NO_FREEZE or COLGATE:`, that means **`DRCOLGATE` has been a no-op on every
Pocket cart driver-nav has built** — the confidence gate has always been active via the
`NO_FREEZE` branch, not via `COLGATE`. `RECOMMIT` (via `DRRECOMMIT_NOFREEZE=1`) is the fix that
actually mattered for this platform. This doesn't change the bottom line (fix present), but it
changes *which* flag is doing the work, which matters for anyone reasoning about what a future
`DRCOLGATE=0` build would or wouldn't change on Pocket (answer: nothing).

**SLAM_ARM status (REVIEW §6.1):** confirmed real on the actual shipping build — `SLAM_ARM=0`
does skip the `K_CROSS` feasibility-crossover branch, exactly as the REVIEW says. But its
consequence is milder than "the defect still reproduces": `SLAM_ARM=0` makes an *accelerated*
slam at a stale column structurally unreachable pre-DONE (`dn_hold` is the only branch), so the
original "premature slam at the wrong column" failure mode cannot occur in that state. What
remains exposed is REVIEW §6.2's *separate* concern — lateral DAS-travel vs. fall-time — which no
flag in this fix family (`DRCOLGATE`/`DRRECOMMIT`/`DRSLAM`) touches at all. Full evidence below.

**Blockers:** none for the fingerprint or the SLAM_ARM/RECOMMIT findings — those are settled by
byte-exact rebuild + passing py65 tests. The lateral-distance residual (REVIEW §6.2, commit
6-shaped cases) **is not fixable by widening the commit-TIMING gate alone** — same conclusion the
REVIEW already reached, since no `CROSS_LOWY`/`K_CROSS` retune changes how far the piece can
physically travel. **UPDATE (this session, follow-on task): implemented as `DRDISTGATE`, a
distance-aware *steering* gate rather than a timing gate — see §7.** Default OFF, tested
two-sided, not yet A/B'd on silicon (§7.5). Confirming the *physical* SD card cart matches this
local artifact was explicitly out of scope (no `/media` access) — see §6.

**UPDATE 2 (constants validation from silicon footage, §7.6): the 32/26-hooks defaults `DISTGATE`
originally shipped with were never measured** — they inherited a stale hooks-per-frame conversion
bug from an old code comment. Measured directly from 60fps footage of the real Pocket AI: DAS ≈
12 hooks/edge (not 32), gravity ≈ 30 hooks/row near a topout (not 26). `DIST_TABLE` regenerated,
all tests re-pass. **This also means REVIEW §6.2's own "commit-6-shaped, 3 columns needs ~96
hooks vs a ~40-hook budget" arithmetic was wrong** — corrected, it's 36 hooks, which fits. The
scenario that originally motivated `DISTGATE` turns out to be comfortably feasible without any
distance clamping at all under measured reality; the mechanism's remaining, narrower, honestly-
characterized (not oversold) value is at the true fall-room floor (`Y=0`) — see §7.6.4, including
a genuine, unresolved trade-off flagged there rather than glossed over.

## 1. Fingerprint — artifact + byte evidence

### 1.1 Locating the artifact

```
$ find /home/struktured/projects -maxdepth 4 -iname "*pocket_human_v4*"
/home/struktured/projects/dr-mario-mods-wt/driver-nav/pocket_human_v4_coldinit.nes
/home/struktured/projects/dr-mario-main-wt/roms/manifests/pocket-human-v4-coldinit.json
/home/struktured/projects/dr-mario-playerstyles-wt/roms/manifests/pocket-human-v4-coldinit.json
$ md5sum pocket_human_v4_coldinit.nes
24dcd9dca5db8b7a21c93b2bb30f124b  pocket_human_v4_coldinit.nes
```

This matches project memory's "v4 fast+coldinit ≈ hash prefix 24dcd9dc" — now confirmed, not
assumed. `roms/manifests/pocket-human-v4-coldinit.json` (committed on `driver-nav` at `4c8103a`,
"pocket-human-v4-coldinit 24dcd9dc: fast tempo + the MISSING DRCOLDINIT on Pocket") records:

```json
{
  "base_rom": {"md5": "7d307c3051ebc0f8a10e259e3c270acb", "path": "drmario_v28cs.nes"},
  "emitter": {"file": "patch_cartridge_copro.py", "md5": "661ffa62f7f84428566cb72bf0d968bd"},
  "flags": {
    "DRBUSYESC": "1", "DRCOLDINIT": "1", "DRHUMAN": "1", "DRMINTHINK": "12",
    "DRNAVDWELL": "0", "DRNOFREEZE": "1", "DRPENDBOUND": "1", "DRPOCKET": "1",
    "DRRECOMMIT_NOFREEZE": "1", "DRSLAM_KOPEN": "32", "DRSTALLWD": "1",
    "DRSTUDYCOUNTS": "1", "DRWRETRY": "1"
  },
  "git": {"branch": "driver-nav", "commit": "ea2f6b7acfce6775b9c6a9f0b4715cd7a9dfea4d", "dirty": false},
  "output": {"md5": "24dcd9dca5db8b7a21c93b2bb30f124b", "name": "pocket_human_v4_coldinit.nes", "size": 98320}
}
```

Base ROM md5 `7d307c30...` matches project memory's pinned base ROM hash (`dr-mario-base-rom-
collision`). Note what is **absent** from `flags`: `DRROTFIX`, `DRCOLGATE`, `DRRECOMMIT`,
`DRSLAM` are not overridden anywhere in this manifest — they are at their code defaults
(`ROTFIX=1`, `COLGATE=1`-when-`ROTFIX`, `RECOMMIT` computed, `SLAM=1`; see
`patch_cartridge_copro.py:237,251,285,409-411`).

Naming provenance for "v4 fast+coldinit" (the label used in the task and in the human's own
field notes): `experiments/player_styles/struktured.md` (dr-mario-main-wt) records "2026-08-02
match 2 (v4 fast+coldinit cart): Stomper won 3-1" — same label, same date range as this
manifest's commit (`ea2f6b7`, 2026-08-02 20:12:45 -0400). No literal "STOMPER vs YOU" string
exists anywhere in tracked source across `dr-mario-mods`, `dr-mario-mods-wt/*`, `dr-mario-main-
wt`, or `dr-mario-playerstyles-wt` — that appears to be a Pocket-side display title, which is not
recoverable without touching the SD card (out of scope here; see §6).

### 1.2 Byte-exact reproducibility (ground truth, not inference)

```
$ tools/romgen.py rebuild roms/manifests/pocket-human-v4-coldinit.json \
    --out tmp_carts/rebuild_v4_coldinit.nes
wrote drmario_copro.nes (mapper 100, AUTO-NAV VS-CPU L11, FPGA coprocessor)
  ✅ REPRODUCED byte-exact: 24dcd9dca5db8b7a21c93b2bb30f124b
```

Current emitter md5 (`661ffa62f7f84428566cb72bf0d968bd`) matches the manifest's recorded emitter
hash exactly — HEAD's `patch_cartridge_copro.py` has not moved since this cart was built, so this
is a direct, not merely historical, reproduction.

### 1.3 Concrete byte diff: ON vs. an OFF reference on the same profile

Built a second reference, same v4 profile, with `DRCOLGATE=0 DRRECOMMIT=0` (the flags that
actually matter — see the COLGATE-is-moot-here finding above; `DRRECOMMIT=0` is the one doing the
work):

```
$ md5sum tmp_carts/off_reference_v4profile.nes
7dd2092ccd31c4c8fa53a01e22691502
```

Diffed against the ON build (identical to the shipping cart): **623 differing bytes**, one
contiguous span `$8456`–`$871F` (31 runs when broken at exact-match boundaries, but every gap
between runs is 1-2 identical bytes inside what is clearly one shifted code region — consistent
with `RECOMMIT` adding a whole extra code block, which moves every downstream jump target). Not
a metadata/header difference — this is inside the driver blob's assembled instruction stream.
This is the assembled-bytes evidence the task asked for, not a string/flag-name inference.

### 1.4 Historical cross-check

`roms/manifests/historical/human-latchfix.json` (commit `155579bd`, predates every live manifest,
`dirty: true` at record time) already carries `DRNOFREEZE=1 DRRECOMMIT_NOFREEZE=1`. Every
recorded Pocket/human manifest in driver-nav's git history — live and historical — has this pair.
Driver-nav has never, as far as its own artifact trail shows, shipped a Pocket cart without the
orientation-relatch fix.

### 1.5 Residual uncertainty (stated plainly)

I did not read the physical Pocket SD card (explicitly out of scope: "NEVER touch anything under
`/media`, the MiSTer, or any `.rbf`/`.rev`/hex"). The chain of evidence that this local artifact
*is* what's actually on the SD card is: (a) exact md5 match to the memory-recorded hash prefix,
(b) exact naming match ("v4 fast+coldinit") in the human's own field-report log dated the same
day this manifest was committed, (c) `sync_to_pocket.sh` only ever vendors RTL/firmware hex and
never touches `patch_cartridge_copro.py` or any `.nes` (confirmed by direct read, matching the
audit's own finding) — so there is no automated pipeline that could have substituted a
differently-built cart onto the SD card without a manual copy step. This is strong circumstantial
evidence, not a hardware read. If a physical SD re-check is wanted later, `pocket-sd-card.md`
records the mount path (`/dev/sdb1`, vfat, `udisksctl`) for a future session with hardware access
in scope.

## 2. Candidate build

```
$ DRBUSYESC=1 DRCOLDINIT=1 DRHUMAN=1 DRMINTHINK=12 DRNAVDWELL=0 DRNOFREEZE=1 DRPENDBOUND=1 \
  DRPOCKET=1 DRRECOMMIT_NOFREEZE=1 DRSLAM_KOPEN=32 DRSTALLWD=1 DRSTUDYCOUNTS=1 DRWRETRY=1 \
  DRROTFIX=1 DRCOLGATE=1 DRRECOMMIT=1 DRSLAM=1 \
  tools/romgen.py build --out tmp_carts/drmario_stomper_vs_you_v5_latchfix.nes \
    --tag _v5_latchfix_candidate
  md5      24dcd9dca5db8b7a21c93b2bb30f124b
```

**`tmp_carts/drmario_stomper_vs_you_v5_latchfix.nes` is byte-identical to the shipping v4-coldinit
cart** (same md5). This is not a bug in the build — `DRROTFIX=1 DRCOLGATE=1 DRRECOMMIT=1
DRSLAM=1` are exactly the code defaults, and the v4 profile already carries them (plus
`DRRECOMMIT_NOFREEZE=1`, which the requested flag set doesn't mention but which the v4 profile
already supplies and which is the one that matters here). Naming it "v5_latchfix" would overstate
what changed: nothing did. I built it anyway, under the requested name, so the artifact the task
asked for exists — but the honest characterization is "confirmation build," not "new fix."

## 3. Defect test — `tests/test_task49_slamarm_race.py`

New file (does not modify `test_pocket_placement.py` or any existing fix logic). Run:

```
$ tests/test_task49_slamarm_race.py
==== 8/9 checks passed (E2 is informational; see script output above) ====
$ echo $?
0
```

Existing regression re-confirmed unaffected: `tests/test_pocket_placement.py` still 4/4.

### Test A — SLAM_ARM branch, on the real shipping profile (REVIEW §6.1)

Single-hook, precise: column-aligned, orient-locked, `ARMED2=1` (still searching), `Y` already
past `CROSS_LOWY` (physically low — critically stacked board), `STABLE_CT2` saturated at
`K_CROSS`. Only `SLAM_ARM` varies.

- `SLAM_ARM=1` → `DOWN` pressed (the `K_CROSS` branch fires). **PASS.**
- `SLAM_ARM=0` → `DOWN` **not** pressed, identical Y/stability otherwise. **PASS** — REVIEW §6.1's
  claim is directly confirmed on the actual shipping flags, not a hypothetical build.

**Interpretation:** REVIEW §6.1 is right about the code path. Its implication ("this collapses to
the pre-fix defect") is the part this test refines: `dn_hold` presses nothing, ever, pre-DONE,
when `SLAM_ARM=0` — so the *original* failure mode (accelerated commit to a shallow/stale column)
is structurally impossible in that state, not merely unlikely. `SLAM_ARM=0` is a worse-tempo,
better-safety state relative to `SLAM_ARM=1`, not a return to the pre-COLGATE defect.

### Test B — RECOMMIT two-sided, on the real shipping profile

Reconstructs the DONE-with-stale-shallow-orient scenario under the actual v4 profile (not
`test_pocket_placement.py`'s generic defaults, which use `DRNOFREEZE=0` by default — see the note
in §4). `DRRECOMMIT=1` (shipping) re-opens `ROT_DONE2` when the capsule is still high and the
converged orient differs; `DRRECOMMIT=0` never does. Both PASS — the fix that actually matters
for Pocket works, verified on Pocket's real flags, not just the generic test defaults.

### Test D — COLGATE two-sided, on the class of cart it actually gates, plus the SLAM_ARM=0 axis

Since `DRCOLGATE` is a no-op on the shipping (`DRNOFREEZE=1`) profile, this test targets the
freeze-class family (`DRNOFREEZE=0`, unset) where `DRCOLGATE` has a real effect — extending
`test_pocket_placement.py`'s existing scenario 1 with the `SLAM_ARM` axis it doesn't cover, per
REVIEW §6.5's required-change list.

- `SLAM_ARM=1`, unstable argmax: fixed holds, pre-fix soft-drops. **PASS** (reproduces the
  original documented defect, two-sided).
- `SLAM_ARM=0`, same setup: fixed **still** holds; pre-fix **still** soft-drops. **PASS.**

This corrected an assumption made while designing the test (see inline comment in the script):
pre-fix (`DRCOLGATE=0`, non-`NO_FREEZE`) doesn't route through the gate at all when `SLAM_ARM=0`
— it never evaluates `SLAM_ARM`, because the whole `if NO_FREEZE or COLGATE:` block is false, so
it falls straight to the unconditional `LDY #4`. Net finding: COLGATE's protection is
`SLAM_ARM`-independent on the cart class it actually gates. REVIEW §6.1's gap lives entirely
*inside* the already-gated region (`K_CROSS` vs. `dn_hold`), not at the COLGATE/no-COLGATE
boundary.

### Test E — lateral DAS-vs-gravity race under SLAM_ARM=0 (REVIEW §6.2), real shipping profile

Multi-hook simulation (mailbox column flips from a spawn column to the true best column
mid-window, `SLAM_ARM=0` throughout — the state Test A proves rules out an accelerated slam).
Grounded constants only: DAS = 32 hook-cycles/column-edge (`patch_cartridge_copro.py` comment at
`mv_p2`), gravity = 26 hook-cycles/row (L11 13f/row × 2 hooks/frame, both from project memory /
this file's own audited hook-rate note — not invented).

- **E1** (1-column distance, 40-hook window ≈ commit 6's `spawn_to_lock_frames=20`): reaches the
  converged column, no forced slam. **PASS.**
- **E2** (3-column distance, matching commit 6 exactly — spawn col4 → true col7, decisive margin
  464 per VERDICT.md): does **not** reach col7 in the window; needs ≈96 DAS hooks against a
  40-hook budget. **Reported as FAIL but excluded from the pass/fail gate** — this is not a
  regression to fix, it is REVIEW §6.2's own arithmetic (three column-edges ≈19.2 of the 20-frame
  budget, leaving ~0 margin) reproduced independently. Critically, `forced_down_before_
  convergence=False` — it does not fail via an accelerated wrong-column slam either; whatever
  column it ends up in is purely a WEAVE/DAS-speed outcome. **No `DRCOLGATE`/`DRRECOMMIT`/
  `DRSLAM` flag combination changes this** — it would require a distance-aware term (REVIEW
  §6.2's own required-change suggestion), which is a genuine code change, not a flag flip, and is
  out of this task's scope (task instructions: do not modify the fix logic without flagging it as
  a REVIEW-driven change — I did not implement one; flagging it here instead, per §5 below).
- **E3** (commit-3 counter-case, REVIEW §6.3: no column change, 33-hook window, tape and eval
  already agree): no regression — reaches and holds the unchanging target, no spurious forced
  drop. **PASS.**

## 4. Note on `test_pocket_placement.py`'s coverage

Its `build()` sets `DRHUMAN=1 DRPOCKET=1 DRSLAM=1` and leaves `DRNOFREEZE` unset (default `"0"`)
— i.e. its existing 4/4-passing scenarios validate a `DRPOCKET=1 + DRNOFREEZE=0` combination that,
per the manifest survey in §1, **has never actually been shipped** (every real Pocket manifest
uses `DRNOFREEZE=1`). That test is still valuable (it's the freeze-class family Test D reuses),
but it was not, before this task, exercising the actual shipping flag combination. Tests A and B
here close that gap by building under the literal `pocket-human-v4-coldinit.json` flag set.

## 5. What's left, if wanted

1. ~~Distance-aware commit gate~~ — **DONE, see §7.** REVIEW §6.2's own suggestion, implemented
   as `DRDISTGATE` (default OFF, candidate not yet A/B'd on silicon).
2. **Build-provenance stamp** (`PAIR_LATCH_AUDIT.md` §4): embed emitter commit + `DR*` flags in
   the `.nes` itself or a co-located log, so a future "which build is on the SD card" question
   doesn't require this kind of forensic reconstruction. `tools/romgen.py`'s manifest system
   already gets most of the way there for *local* artifacts; the gap is purely "what's physically
   deployed."
3. **Physical SD confirmation** (§1.5): out of scope for this task (no `/media` access), but
   would close the one remaining evidentiary gap.

## 6. Deploy steps for the human

Since §2 established the flag-only candidate is byte-identical to what's already shipping,
**there is nothing new from that step to copy to the SD card.** §7's `DRDISTGATE=1` candidate
(`tmp_carts/drmario_stomper_vs_you_v5_distgate.nes`, md5 `4681cbf5d27821c6f13893c6e7155153`) IS a
real behavior change and has NOT been A/B'd on silicon — do not ship it to the play SD card as a
replacement for the current cart without a MiSTer/Pocket-side validation pass first (this task
was py65-only, per its constraints). If/when that validation happens:
- Build via `tools/romgen.py build --out <name>.nes --tag <tag>` with the v4 profile flags from
  §1.1 plus `DRDISTGATE=1`.
- Per `pocket-sd-keep-versions.md`: never overwrite in place; use a version-distinct filename
  (e.g. `drmario_stomper_vs_you_v5_distgate.nes`, already following that convention); evict
  oldest only on space pressure, and ask first.
- SD mount path per `pocket-sd-card.md`: `/dev/sdb1`, vfat, `udisksctl`; cart lives under
  `Assets/nes/common/` per `sync_to_pocket.sh`'s own directory convention (that script itself
  only vendors RTL/hex, not the cart — the cart copy is, and remains, a manual step).

## 7. DRDISTGATE — the distance-aware commit gate (REVIEW §6.2, authorized code change)

Team-lead follow-on explicitly authorized this as a REVIEW-driven change to fix logic (not a flag
toggle), per the house rule to flag such changes rather than make them silently.

### 7.1 Mechanism

Neither `COLGATE`/`RECOMMIT`/`SLAM` reasons about *distance* — how many columns the search's
target is from the capsule's current column — only about *when* to commit. `tests/
test_task49_slamarm_race.py`'s Test E showed a commit-6-shaped case (3-column distance, ~40-hook
window) simply cannot complete the DAS traverse in time (needs ~96 hooks, matching REVIEW §6.2's
own arithmetic).

`DRDISTGATE=1` (default OFF) bounds the **steering target itself** by DAS-reachability given the
remaining fall budget, in `mv_p2` (`patch_cartridge_copro.py`, right before the alignment check
that used to read `TGT_C2`/`EFF_C2` directly):

```
_EC = EFF_C2 if TUCK else TGT_C2
if DISTGATE:
    budget = DIST_TABLE[min(BOARD_Y, 15)]              # BOARD_Y = $0386, row-space
    if _EC < PX2:  EFF_DIST2 = max(_EC, max(0, PX2 - budget))     # leftward
    else:          EFF_DIST2 = min(_EC, min(7, PX2 + budget))     # rightward/equal
    _EC = EFF_DIST2
# everything below (alignment check, WEAVE steering, dn_p2's confidence gate) is UNCHANGED code,
# now just reading a distance-bounded target instead of the raw one.
```

`DIST_TABLE[Y] = 0 if Y==0 else max(1, min(7, floor(Y * DIST_GRAVROW / DIST_DASEDGE)))` — a
16-entry lookup table (`DIST_TABLE_LEN=16`, covering the playfield height), computed at Python
codegen time and emitted as raw bytes jumped over at the top of `main` (so `DIST_TABLE_ADDR` is a
concrete address by the time `mv_p2`, emitted later in program order, needs it for `LDA_absX`).
Grounded constants, not invented: `DIST_DASEDGE=32` hooks/column-edge (the `mv_p2` comment's own
"32-hook cycles = 6.4 frames per edge"), `DIST_GRAVROW=26` hooks/row (L11 13f/row × 2 hooks/frame,
the audited hook-rate note earlier in the same file) — identical to what Test E already used, so
the fix and the test share one source of truth. Both are env-overridable
(`DRDIST_DASEDGE`/`DRDIST_GRAVROW`) for future re-derivation if gravity/search latency changes
again (same pattern as `FAST_HI`'s own re-audit note).

New RAM: `DG_BUDGET=$6193`, `EFF_DIST2=$6194` — the next free PRG-RAM bytes past `BUSYSKP=$6192`
(confirmed via full-file grep before allocating; does not collide with the DRPROBE/DRTRACE ring
header at `$6186-$618C` or DRSTALLWD's own registers at `$618D-$6192`, all reserved/documented
ranges checked directly, not assumed).

### 7.2 A real bug found and fixed before it reached the report as a "working" mechanism

The first version of `DIST_TABLE` used a straight `floor(Y * DIST_GRAVROW / DIST_DASEDGE)` with
no minimum. Since `DIST_DASEDGE (32) > DIST_GRAVROW (26)`, one row of remaining fall-time (26
hooks) is **not enough** to complete one DAS edge (32 hooks) — so the naive floor formula reports
budget=0 while `Y` is still > 0, straddling a point PARTWAY through an edge that an earlier hook
(when `Y` was larger) had already promised 1 column of budget for. Because the clamp is
recomputed fresh every hook from the *current* `Y`, this makes the bound **retreat** to wherever
`PX2` already sits — which can be *before the capsule has moved at all*. `STABLE_CT2` (tracking
the raw search-target's stability, accumulating independently since the target first appeared)
can already be past `K_CROSS` by that point, so `dn_p2` fires a confident-looking SLAM at the
column the capsule never actually chose to commit to: **a false-confidence commit AT SPAWN** —
worse than pre-`DISTGATE` behavior (`dn_hold`, no forced button) for exactly the scenario this
gate exists to help.

Caught by `tests/test_task49_distgate.py`'s Test 3a, first version: `down_fired=True at hook=26
locked_col=4` — the gate had slammed at the spawn column it was supposed to be moving *away*
from, having never actually traveled anywhere. Fixed by flooring the budget at 1 whenever any row
of clearance remains (`Y > 0`): the clamped target can now only shrink toward "less movement than
originally hoped," never retreat all the way back to "no movement was ever needed." Re-run after
the fix: `down_fired=True at hook=52 locked_col=5` — committed at the DAS-reachable column, after
actually traveling there. This is exactly the house rule in practice — simulating the defect
surfaced a real design flaw in new code before it shipped, not after.

### 7.3 Tests — `tests/test_task49_distgate.py`, all new, does not modify existing fix logic

```
$ tests/test_task49_distgate.py
==== 7/7 checks passed ====
$ echo $?
0
```

- **Test 1 (unit):** `EFF_DIST2` vs. a plain-Python reference of the same clamp formula, swept
  across all `(PX2, target, BOARD_Y)` combinations in `range(8) × range(8) × {0,3,6,...,25}`
  (640 combinations, including `BOARD_Y` values past the table's own range, to check the
  clamp-to-last-entry path) — **640/640 exact matches.** This isolates the 6502 arithmetic itself
  from the rest of the driver's control flow, per the task's request to unit-test the arithmetic
  before trusting it in the full flow.
- **Test 2 (byte-exact when off):** `DRDISTGATE` unset vs. explicit `=0` — byte-identical
  (1808-byte `build_main` output, zero diff). Full end-to-end `tools/romgen.py rebuild` of the
  shipping manifest still reproduces `24dcd9dca5db8b7a21c93b2bb30f124b` after all the `DISTGATE`
  code additions — the fingerprint from §1 is unaffected by this change.
- **Test 3a (two-sided, commit-6-shaped, 3-column distance, `SLAM_ARM=1`):** WITHOUT the gate,
  chasing the unreachable 3-column target for the whole 80-hook window, `dn_p2` is **never**
  entered (misalignment persists throughout) — no commit ever fires (`down_fired=False`). WITH
  the gate, clamped to the 1-column-reachable target, the capsule reaches alignment and commits
  there once stability saturates (`down_fired=True`, `locked_col=5`). Note this replaced an
  earlier, structurally-wrong version of this test that compared *final resting column* under
  `SLAM_ARM=0` — analysis mid-implementation showed DAS travel rate is target-distance-independent
  in this driver (`mv_p2` presses the same LEFT/RIGHT every hook regardless of how far the target
  is, until aligned), so clamping the steering target alone does not change the final column in a
  pure-natural-gravity scenario; the real, demonstrable effect is whether `dn_p2` is ever reached
  and can commit at all. Documented so the earlier reasoning isn't silently discarded.
- **Test 3b (generous window, no-regression control):** same 3-column distance, but enough hooks
  (`3×32 + 20`) to complete the full traverse even without the gate — both WITH and WITHOUT reach
  column 7. The gate must not become *more conservative* when the raw target is already reachable;
  confirmed.
- **Test 3c (Test E1 parity):** the 1-column-distance case from `test_task49_slamarm_race.py`'s
  Test E1, re-run with the gate on — unchanged (`locked_col=5` both ways).

### 7.4 Candidate build

Two builds exist for this cart, from before and after §7.6's constants correction:

```
$ DRBUSYESC=1 DRCOLDINIT=1 DRHUMAN=1 DRMINTHINK=12 DRNAVDWELL=0 DRNOFREEZE=1 DRPENDBOUND=1 \
  DRPOCKET=1 DRRECOMMIT_NOFREEZE=1 DRSLAM_KOPEN=32 DRSTALLWD=1 DRSTUDYCOUNTS=1 DRWRETRY=1 \
  DRDISTGATE=1 \
  tools/romgen.py build --out tmp_carts/drmario_stomper_vs_you_v5_distgate.nes \
    --tag _v5_distgate_final2
  md5      082f51f3e03d3b53c71a9d6780f35132   # CURRENT — DIST_DASEDGE=12 DIST_GRAVROW=30 (measured)
```

(The pre-correction build, md5 `4681cbf5d27821c6f13893c6e7155153`, used the stale `32`/`26`
defaults and is superseded — kept only as a historical note, not shipped.)

All internal `build_main` assertions (ROM-space overflow guards, hook/blob-head checks) passed
with no errors on both builds, and the determinism check (`romgen.py` builds twice, requires
identical bytes) passed silently both times.

### 7.5 Confidence assessment — NOT silicon-ready without an A/B pass first

High confidence in the **arithmetic** (640/640 unit matches) and in the **byte-exactness when
off** (holds end-to-end, both before and after §7.6). The **mechanism's practical value** is now
better understood but also more modest than originally believed — see §7.6's headline finding.
Explicitly **not** claiming silicon-readiness, for reasons a py65 harness cannot resolve on its
own:
- ~~`DIST_DASEDGE=32`/`DIST_GRAVROW=26` are the same constants Test E already used, but neither
  has been re-validated against current silicon-clocked search latency~~ — **DONE, see §7.6.**
  Measured from real silicon footage: DAS = 12 hooks/edge (not 32), gravity = 30 hooks/row (not
  26) in the near-topout context DISTGATE targets. The corrected constants are now the code
  defaults. One residual: the gravity measurement showed a large, unexplained discrepancy between
  an earlier match segment (~9-13 frames/row) and the near-topout death window (~15 frames/row) —
  flagged in §7.6, not resolved. If that discrepancy reflects a real level/speed-dependent gravity
  table rather than measurement noise, `DIST_GRAVROW` may need to vary by context rather than
  being a single constant — not implemented here.
- This task's test harness models DAS movement and gravity in **Python**, alongside the real
  driver's assembled code — it does not run the actual NES game engine's `fallingPill_checkXMove`
  or gravity table, so "the piece actually arrives at the clamped column in N hooks" is a modeled
  approximation. Cross-checked against real 60fps footage in §7.6 (a stronger check than the
  original version of this report had), but still not the actual game engine executing.
- Section 7.2's bug is evidence the mechanism CAN fail in non-obvious ways under specific
  parameter combinations; finding and fixing one such case increases confidence but does not
  prove there are no others. §7.6 surfaced a SECOND, related edge case (the Y=0 floor trade-off,
  §7.6.4) that was investigated and characterized but deliberately NOT "fixed" — it's a genuine,
  debatable trade-off (earlier commitment vs. potentially cutting off late DAS gains), not a
  clear-cut bug, and is flagged for the team's judgment rather than resolved unilaterally.
- `TUCK` interaction remains untested (v4 shipping profile doesn't use it; `TUCK` and `DISTGATE`
  both write through `_EC` sequentially, `TUCK` first, so `DISTGATE` clamps whatever `TUCK`
  already chose — untested combination, flagged not verified).
- No MiSTer/Pocket A/B has been run (explicitly out of scope for this task — headless only).

Recommend: silicon A/B (or at minimum Verilator co-sim of the timing constants, now that they
have concrete measured values to validate against) before this ships to the play SD card, same
bar as every other candidate in this file's lineage.

### 7.6 DAS/gravity constants — measured from silicon footage (2026-08-05)

Team-lead follow-on: validate `DIST_DASEDGE`/`DIST_GRAVROW` against recorded 60fps footage of the
real Pocket core's AI, without an emulator (Mesen single-instance/occupied; nes-py can't run the
mapper-100 copro cart). **Headline finding: the original 32/26 defaults were never measured — they
inherited a stale hooks-per-frame conversion bug — and the corrected numbers substantially change
the assessed necessity of DISTGATE for the scenario that originally motivated it.**

#### 7.6.1 Method

Confirmed directly from code first, not taken on faith: `patch_cartridge_copro.py`'s own "WHERE
THE HOOK ACTUALLY RUNS" note (search `THE DRIVER RUNS EXACTLY 2x PER FRAME`) — 2 hooks/frame,
measured 2026-08-01, matches what was assumed.

Built a new P2-specific capsule tracker, `dr_mario_rl/tmp/film_review_20260804/
tracker_p2_death.py`, on top of the existing (already-validated) `tracker.py`'s per-frame capsule
search — reusing every pure function unchanged, only re-implementing the crop grid (`p2_60fps_
death/` cut at `x=1120,y=224`, per `vision.py`'s own independently-derived crop dict) and the
outer per-frame loop (`tracker.py` hardcodes the P1 crop/frames-root internally). Ran it against
two footage sources:
- `p2_60fps_death/` — 1920 frames (t=1090.0-1122.0s), the existing death-window extraction.
- A fresh 90s/5400-frame extraction via `ffmpeg` from `~/Videos/drmario_sessions/
  20260804_1955_pocket_dock.mp4` (t=120-210s, same P2 crop `392:824:1120:224`), for a larger DAS
  sample since the death window's AI barely moves laterally (itself consistent with VERDICT.md's
  own finding).

**Validation the tracker is reading the right thing, not just a plausible-looking board:** the
death-window tracker's pill spawn timestamps and spawn-to-lock frame counts reproduce
VERDICT.md's six audited commits exactly (e.g. pill 11 spawns at t=1111.517 with a 95-frame
spawn-to-lock span, matching commit 2's `spawn_to_lock_frames=95` to the frame) — without having
been told those numbers, and using a different row/column coordinate convention than VERDICT.md's
board reconstruction (immaterial to the timing measurement, not chased down further).

#### 7.6.2 DAS repeat cadence

Extracted every frame-to-frame lateral (column-only) move from the per-frame path trace across
both footage sources, then computed intervals between consecutive moves within a run:
- **4 CLEAN steady-state repeats** (no rotation event, no row-advance coincident with the gap):
  **6, 6, 6, 6 frames — zero spread.**
- **5 "first repeat after engaging" gaps** (each coincident with a concurrent row-advance, i.e.
  gravity ticking during the same gap): **16, 16, 16, 16, 16 frames** — with one exception in the
  clean group that also had a coincident row-advance yet stayed at 6, so "row-advance causes the
  16-frame gap" is not a clean, universal rule on this sample; more likely a genuine "first repeat
  after DAS engages" cost that happens to often coincide with an early row-tick in a small sample.
  Frame-level (not hook-level) footage can't fully separate these mechanisms.

Used the clean steady-state number (what governs total distance over a multi-column traverse,
since the first-engage cost is paid once regardless of how far the piece ultimately travels): **6
frames × 2 hooks/frame = 12 hooks/edge.**

This also resolves *why* the original 32-hooks/edge default was wrong: the `mv_p2` code comment
it was copied from says "32-hook cycles = 6.4 frames per edge" — a frame-based design target
(6.4, matching this measurement almost exactly) converted through the OLD, since-corrected
"`NAV_T=5*/frame`" assumption (32 = 6.4 × 5). Re-converting the SAME 6.4-frame target through the
CORRECT 2 hooks/frame gives ~13 hooks — close to, and now superseded by, this direct measurement.

#### 7.6.3 Gravity (natural fall, non-soft-drop)

Row-advance intervals, filtered to exclude the soft-drop cluster (tight at 2 frames/row, matching
project memory's "2f/row soft-drop" exactly — a good sanity check that the interval extraction
itself is sound):
- **Death window** (near-topout, the context `DISTGATE` actually targets): n=10, dominant cluster
  at **15 frames/row** (8/10), 2 at 16. Mean ~15.2.
- **Earlier match segment** (t=120-210s): n=6 clean readings, faster and more scattered: 9, 9, 12,
  13, 16, 16.

**Unexplained discrepancy, flagged not resolved:** the earlier segment reads consistently faster.
Project memory documents a gravity table with a `speedup` component (`gravityTable $A795 +
speedBase+speedup $8A`), so a level- or time-dependent gravity rate is plausible, but this task
didn't chase down the mechanism. Used the death-window reading (15 frames/row) since it's the
context-matched one: **15 frames/row × 2 hooks/frame = 30 hooks/row.**

#### 7.6.4 Net effect — and a finding that goes beyond "update two numbers"

```
                    OLD (stale, unmeasured)     NEW (measured, silicon)
DIST_DASEDGE               32                          12
DIST_GRAVROW                26                          30
DIST_TABLE  [0,1,1,2,3,4,4,5,6,7,7,7,7,7,7,7]  [0,2,5,7,7,7,7,7,7,7,7,7,7,7,7,7]
3 columns cost              96 hooks                    36 hooks
```

DAS is much faster than assumed; gravity is somewhat slower — both push the same direction (more
lateral budget per row of remaining fall-time).

**This means REVIEW #6.2's own arithmetic (`PAIR_LATCH_AUDIT.md`, "three column-edges cost ≈19.2
of the 20-frame budget, leaving ~0 margin") — and this task's own earlier `tests/
test_task49_slamarm_race.py` Test E, built on the identical stale 32/26 pair — used the wrong
hook budget.** Under the corrected numbers, a literal commit-6-shaped case (3 columns, ~40-hook
window) needs 36 hooks, which **fits inside 40** with room to spare. The "physically infeasible"
conclusion that originally motivated `DISTGATE` does not hold up under measured reality. This is
flagged here rather than silently rewritten into the already-committed, already-pushed Test E —
that earlier work stands as-is with this correction attached; a full re-audit of Test E / REVIEW
§6.2 with the corrected constants is recommended as a follow-up, not done in this increment.

**Redesigning `tests/test_task49_distgate.py`'s Test 3a to still demonstrate a real, two-sided
distinction under the corrected numbers surfaced a second, genuine finding, not a bug this time:**
because the clamp is recomputed fresh every hook relative to the capsule's *current* position
(not spawn), the reachable ceiling advances right along with real DAS progress — correctly, since
"how far more can I get from here, given remaining time" is the right recursive definition, not a
fixed spawn-relative cap. The practical consequence: for any `Y > 0`, the clamp converges toward
*effectively unclamped* as soon as movement starts, unless the window is so short that neither a
clamped nor unclamped build could align in time. The clamp is only unconditionally, non-rubber-
band binding at the **true floor, `Y=0`** (`DIST_TABLE[0]=0` by explicit design). Test 3a now
tests that case directly: WITHOUT the gate, chasing an unreachable target at `Y=0` never aligns
within a 20-hook window (natural DAS rests it at col5, 1 edge closer than spawn, but never an
accelerated commit). WITH the gate, `EFF_DIST2=PX2` immediately (0 budget from hook 0), so it's
"aligned" trivially and fires an accelerated SLAM at col4 (spawn — zero progress) once
`STABLE_CT2` saturates, ~8 hooks later.

**Honest reading, not claimed as a clean win:** the gate trades a numerically worse resting column
(4, spawn) for an earlier, definite commit, versus the uncommitted case's natural col5. Whether
that's actually better depends on what the real game does in the hooks between `Y` reading 0 and
genuine physical collision — `Y=0` doesn't necessarily mean "collides this hook," so the
uncommitted case might keep gaining real DAS ground in that window that the gate's immediate
freeze forecloses. This is a genuine, debatable trade-off, characterized and tested (both sides
pass, per the test's own honest assertions) but **deliberately not "fixed"** — it doesn't have the
same clear right-answer shape as §7.2's retreat bug, and is flagged for the team's judgment.

#### 7.6.5 Deliverables (per the task's own list)

1. **Measured distributions with n and spread:** §7.6.2 (DAS, n=4 clean + n=5 confounded) and
   §7.6.3 (gravity, n=10 death-window + n=6 earlier-segment).
2. **Verdict: constants NEED ADJUSTMENT (not confirmed).** Corrected values: `DIST_DASEDGE=12`,
   `DIST_GRAVROW=30`. `DIST_TABLE` regenerated; all 7 of `tests/test_task49_distgate.py`'s checks
   re-run and pass (7/7) — Test 3a substantially redesigned per §7.6.4's finding, with the
   redesign and its reasoning documented in the test file itself, not silently swapped in.
   `tests/test_task49_slamarm_race.py` (8/9) and `tests/test_pocket_placement.py` (4/4)
   re-confirmed unaffected. `tracker_p2_death.py` and the raw event/path data live under
   `dr_mario_rl/tmp/film_review_20260804/` (events/`p2_death.csv`,`p2_death_paths.jsonl`,
   `p2_m1sample.csv`,`p2_m1sample_paths.jsonl`) — that tree is outside `driver-nav`'s scope to
   commit, referenced here by path.
3. This section + `driver-nav` commit (below).

## Files

- `tmp_carts/rebuild_v4_coldinit.nes` — byte-exact rebuild of the shipping cart from HEAD
  (md5 `24dcd9dca5db8b7a21c93b2bb30f124b`), proving reproducibility.
- `tmp_carts/off_reference_v4profile.nes` — same v4 profile, `DRCOLGATE=0 DRRECOMMIT=0`
  (md5 `7dd2092ccd31c4c8fa53a01e22691502`), the byte-diff control.
- `tmp_carts/drmario_stomper_vs_you_v5_latchfix.nes` — the requested flag-only candidate
  (md5 `24dcd9dca5db8b7a21c93b2bb30f124b`, identical to shipping).
- `tmp_carts/drmario_stomper_vs_you_v5_distgate.nes` — the `DRDISTGATE=1` candidate, CURRENT
  build with measured constants (md5 `082f51f3e03d3b53c71a9d6780f35132`), a real,
  untested-on-silicon behavior change; see §7. Superseded pre-correction build (not shipped):
  md5 `4681cbf5d27821c6f13893c6e7155153`.
- `tests/test_task49_slamarm_race.py` — new py65 defect tests A/B/D/E described in §3.
- `tests/test_task49_distgate.py` — new py65 tests (unit + byte-exact + two-sided defect) for
  `DRDISTGATE`, described in §7.3; Test 3a redesigned in §7.6.4 to match the measured constants.
- `patch_cartridge_copro.py` — REVIEW-driven code change (§7): `DRDISTGATE` flag + `DG_BUDGET`/
  `EFF_DIST2` registers + the `mv_p2` clamp block + `DIST_TABLE`, now built from silicon-measured
  `DIST_DASEDGE=12`/`DIST_GRAVROW=30` (§7.6). Default OFF, byte-exact when off (verified). No
  existing fix logic (`COLGATE`/`RECOMMIT`/`SLAM`/`ROTFIX`) was modified.
- `.gitignore` — added `tmp_carts/` (the built `.nes` files were already covered by the existing
  `*.nes` blanket rule; this makes the scratch directory itself explicit).
- (outside `driver-nav`, referenced not committed here) `dr_mario_rl/tmp/film_review_20260804/
  tracker_p2_death.py` — new P2-specific footage tracker (§7.6.1), plus its output
  `events/p2_death.csv`, `events/p2_death_paths.jsonl`, `events/p2_m1sample.csv`,
  `events/p2_m1sample_paths.jsonl`, and the extracted frames `p2_60fps_m1sample/` (90s/5400
  frames from the source video, gitignored `tmp/` scratch, not committed anywhere).
