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
6-shaped cases) is **not fixed and not fixable by a commit-timing flag** — same conclusion the
REVIEW already reached; see §5. Confirming the *physical* SD card cart matches this local
artifact was explicitly out of scope (no `/media` access) — see §6.

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

## 5. What's left, if wanted (not done here — flagging per task instructions, not implementing)

1. **Distance-aware commit gate** (REVIEW §6.2's own suggestion): widen `CROSS_LOWY` or lower
   `K_CROSS` as a function of `|current_col - TGT_C2|`. This is a real code change to
   `patch_cartridge_copro.py`'s fix logic — I did not make it, per the task's explicit
   instruction not to modify existing fix logic without flagging it first. Test E2 above is the
   reproducible harness to validate it against, if the human wants it built.
2. **Build-provenance stamp** (`PAIR_LATCH_AUDIT.md` §4): embed emitter commit + `DR*` flags in
   the `.nes` itself or a co-located log, so a future "which build is on the SD card" question
   doesn't require this kind of forensic reconstruction. `tools/romgen.py`'s manifest system
   already gets most of the way there for *local* artifacts; the gap is purely "what's physically
   deployed."
3. **Physical SD confirmation** (§1.5): out of scope for this task (no `/media` access), but
   would close the one remaining evidentiary gap.

## 6. Deploy steps for the human (nothing new to deploy, but recording per instructions)

Since §2 established the candidate is byte-identical to what's already shipping, **there is
nothing new to copy to the SD card** for this task. If a future session *does* implement §5.1 and
wants to ship it:
- Build via `tools/romgen.py build --out <name>.nes --tag <tag>` with the v4 profile flags from
  §1.1 plus whatever new flag the distance-aware change adds.
- Per `pocket-sd-keep-versions.md`: never overwrite in place; use a version-distinct filename
  (e.g. `drmario_stomper_vs_you_v6_<change>.nes`); evict oldest only on space pressure, and ask
  first.
- SD mount path per `pocket-sd-card.md`: `/dev/sdb1`, vfat, `udisksctl`; cart lives under
  `Assets/nes/common/` per `sync_to_pocket.sh`'s own directory convention (that script itself
  only vendors RTL/hex, not the cart — the cart copy is, and remains, a manual step).

## Files

- `tmp_carts/rebuild_v4_coldinit.nes` — byte-exact rebuild of the shipping cart from HEAD
  (md5 `24dcd9dca5db8b7a21c93b2bb30f124b`), proving reproducibility.
- `tmp_carts/off_reference_v4profile.nes` — same v4 profile, `DRCOLGATE=0 DRRECOMMIT=0`
  (md5 `7dd2092ccd31c4c8fa53a01e22691502`), the byte-diff control.
- `tmp_carts/drmario_stomper_vs_you_v5_latchfix.nes` — the requested candidate
  (md5 `24dcd9dca5db8b7a21c93b2bb30f124b`, identical to shipping).
- `tests/test_task49_slamarm_race.py` — new py65 defect tests A/B/D/E described above.
- `.gitignore` — added `tmp_carts/` (the built `.nes` files were already covered by the existing
  `*.nes` blanket rule; this makes the scratch directory itself explicit).
