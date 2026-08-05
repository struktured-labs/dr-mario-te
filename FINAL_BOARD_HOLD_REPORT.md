# Final board hold + level-select garble fix

Worktree: `dr-mario-finalboard-wt` (branch `feature/final-board-hold`, off `origin/driver-nav`).
Commits: `dbd15c2` (garble fix), `4cce693` (DRHOLDBOARD). No SD/MiSTer/hardware touched. Mesen
used read-only for the garble diagnosis (confirmed free via `pgrep -x Mesen` before each use);
never used for the copro-cart work (mapper 100 is not Mesen-emulable). All new builds live under
`tmp_carts/` (gitignored); the reproducibility record is `roms/manifests/boardhold-v6.json`.

## Job 1 — level-select garble

**Root cause, one sentence:** `DRSTUDYCOUNTS` (default ON for human carts) writes live virus/
level digit sprites into OAM shadow-buffer slots 8-15 every PLAY-mode hook, but previously did
nothing on any other mode — neither redraw nor blank — so stale digit tiles from the last play
frame could survive into the settings screen, which uses few of its own sprites and therefore
never forces the base ROM's own OAM padding (`R8712`, which only pads from that screen's own
sprite high-water-mark onward, not an unconditional clear) to reach those slots.

**This is NOT the TE v6 print-table collision class the task briefed against.** Direct byte-diff
of the shipping v4-coldinit cart against vanilla `drmario_v28cs.nes` shows the settings-screen
print table (`$BD7D-$C196`, confirmed by disassembly to be the *only* `RB6C2_PRINT` table backing
this screen) and all 16 small per-item attribute/palette tables (`$A26A`-`$A6E7`) are **byte-
identical** — the v8.2 EVAC mechanism (already in this driver's HEAD) already fixed that class.
A full 32KB unit-0 diff of the shipping cart against vanilla found exactly 7 runs, 141 bytes,
none inside any documented print table (`$97B7`/`$97D4-5`/`$97E3` = the STUDY pause-routine
hooks; `$D2CC`/`$D2E0-FF` = the STUDY blob's RTS entry; `$FB02-4`/`$FF55-B9` = the driver's own
head/trampoline). Direction: **runtime OAM leak, not a ROM data collision** — confirmed further
by driving vanilla `drmario.nes` AND `drmario_v28cs.nes` through the identical title→2P→settings
nav sequence in Mesen and hashing the nametable: both render **byte-for-byte clean** (0 diffs),
ruling out both the base ROM and the pre-driver-patch AI base as the source.

**Fix** (`patch_cartridge_copro.py`, `not_play` label): on every non-play hook, explicitly write
`Y=$FF` (off-screen) to all 8 digit-sprite slots. One writer now owns the whole slot-8-15
lifecycle: draw-when-valid (`dispatch`) or blank-always (`not_play`).

**Two-sided evidence** (`tests/test_studycounts_leak.py`, py65, one persistent MPU across two
hook calls so OAM content carries across "frames" exactly as it would on real hardware):
- Pre-fix: a settings-screen hook run immediately after a play-mode hook leaves the OAM Y-bytes
  **byte-for-byte identical** to what the play hook wrote (`[43,43,43,43,191,191,191,191]` both
  before and after) — the garble reproduces, measured not eyeballed.
- Post-fix: the same sequence leaves all 8 slots at `$FF`.
- `DRSTUDYCOUNTS=0` builds are byte-identical before and after the fix
  (`4eeff568d6427ea1508c85a610b6964d`, both sides).
- Full existing regression suite re-passes (`test_study2p`, `test_cart_matrix`, `test_pocket_*`,
  `test_nav_*`); `test_nav_flicker.py`'s pre-existing 1/5 failure reproduces identically with and
  without this change (confirmed via `git stash`), so it is unrelated.

## Job 2 — final-board hold (`DRHOLDBOARD`)

**Mechanism, one sentence:** since the vanilla end-of-match routines destroy the `$0400`/`$0500`
playfield RAM model itself (fill-with-`$FF` + banner/dialog text) synchronously with no
START-gated checkpoint beforehand, the driver continuously mirrors both boards into PRG-RAM
during active play and, once a match-end is detected, restores + re-triggers the game's own
row-redraw every hook until the human's START releases it (or, for a CvC/autonav cart only, a
frame-count safety cap).

### Why STUDY's technique doesn't transfer

STUDY defers the pause routine's *own* OAM-blank call by patching bytes **inside** `$978E`'s
body, before it ever executes. I looked for an equivalent checkpoint in the end-of-match paths
and there isn't one — read directly from the disassembly (`tmp/refs/drmario/drmario.a65`):

- **Inter-match (`RB24F_CHECK_WIN`, `$B24F`):** checks `L0324_P1_VIRUS`/`L03A4_P2_VIRUS`, and if
  either is 0, calls `RB337_STAGE_CLEAR` (`$B337`) **immediately** — no `$F5`/`$F7` read precedes
  it. `RB337_STAGE_CLEAR` fills the clearing player's whole playfield page with `$FF` then copies
  the "STAGE CLEAR" message into it. Only *after* that does the routine reach its own
  START-wait loop (`$B2E4`-`$B306`). `RB24F_CHECK_WIN` is itself a **blocking** routine (its own
  loop calls `RB654_NEXT_FRAME` directly, never returning to the outer state machine) — confirmed
  by the fact `L46_TOP_STATE` is not written until *after* that wait loop exits at `$B312`/`$B331`.
- **Set-final (`L958A_TOP_7`, `$958A`):** sleeps, then `RB894_FILL_PAGES` fills **both** pages
  (`$0400` and `$0500`) with `$FF`, then `R96D4_GAME_OVER` stamps "GAME OVER" into each, *then*
  its own START-wait loop. Also fully blocking, same shape.

So "gate the phase-advance on a START edge" (my original suggestion) is not applicable — there is
no phase-advance write to gate; the destructive write and the wait-for-start are two different
steps of one already-committed routine, and the write happens first, unconditionally. **The
alternative is snapshot+redraw**, which is what's implemented, with its cost stated below rather
than glossed over.

### Design

Two independent arm points, one shared restore/release block:

- **`fc_clear`** (existing full-clear detector): arms on the *first* hook that sees a player's
  virus count hit 0. Fires every hook of the whole STAGE CLEAR wait (mode stays 4 throughout,
  confirmed above), but only the first such hook actually arms (idempotent check on `HOLD_ACTIVE`).
  Does **not** touch `MATCH_ACTIVE` — that gate has to stay set for the whole wait, or the very
  next hook falls through to `go_ai`'s match-START init mid-STAGE-CLEAR.
- **`not_play`** (existing non-play dispatch): a topout never sets either virus count to 0
  (burying, not clearing), so `fc_clear` never fires for it — `L46_TOP_STATE` instead transitions
  `4→5→7` (`L9532_TOP_5` does book-keeping then jumps into `L958A_TOP_7`'s own blocking wait).
  Arms on the first hook `not_play` sees with `MATCH_ACTIVE` still set from the just-ended match,
  and **does** clear `MATCH_ACTIVE` as part of arming — otherwise, once released, the next idle
  menu hook would see `MATCH_ACTIVE` still nonzero and re-arm a hold with nothing to hold, forever,
  at the title screen.
- **Restore/release** runs first, every hook, ahead of the mode split entirely (so it applies
  whether `$0046` currently reads 4, 5, 6, or 7): if `HOLD_ACTIVE`, restore both 256B pages from
  the PRG-RAM mirror, set `L0300_P1_UPDATE_ROW`/`L0380_P2_UPDATE_ROW = $0F` (the *same* redraw-
  drain mechanism `RB337_STAGE_CLEAR`/`R96D4_GAME_OVER` themselves use — not a hand-rolled PPU
  write), then check release: human START (`($F5|$F7)&$10`, read exactly like the vanilla wait
  loops so the same press satisfies both) always releases; for a non-`HUMAN_P1` (CvC) cart only,
  a `$43`-clock-edge-driven 16-bit counter forces release after `DRHOLDBOARD_F` frames (default
  600 ≈ 10s) regardless. **Both release paths RTS immediately**, owning the whole hook exactly
  like `fc_clear`'s `fc_ret` — clearing `MATCH_ACTIVE` mid-hook and then letting the rest of
  `main()` run in the same hook makes `go_ai` treat it as a brand-new match and re-arm state; this
  was caught by `test_holdboard.py`'s own release assertion during development and fixed before
  landing (see the test's scenario A2 comment).

### Cost, stated honestly

The continuous mirror (`dispatch`, gated `if HOLDBOARD`, unconditional on `STUDY`/`STUDYCOUNTS`)
is a `2×256B` copy every "dispatch" hook, i.e. twice per frame during **all** of active pre-clear
play, not just near the end — there is no cheaper correct trigger: the board only needs to be
captured *fresh* through the very last (winning) placement and its cascade, and any coarser
trigger (e.g. "snapshot on next-pill-spawn") misses exactly that placement, since no next pill
ever spawns after the match-ending one. Measured-equivalent cost ≈ 23 cycles/byte-pair × 256 ≈
5.9k cycles/hook, ~11.8k cycles/frame (2 hooks) against a 29,780-cycle NES frame budget — roughly
40%. On a frame where this coincides with an AI search (16-23k cyc, once/pill), the frame budget
can be exceeded; this is the same class of "hitched frame" the project already accepts and
already guards (`DRBUSYESC`) for the AI-search cost itself, so it is not a new failure mode, only
a larger dose of an already-mitigated one. If this proves too expensive in practice, the cheapest
correct optimization is alternating which page is mirrored on odd/even hooks (halves the
per-hook cost, doubles snapshot staleness to ~1 frame) — not implemented, since I have no
hardware timing data to justify trading correctness margin for headroom I haven't shown is needed.

### Byte-identical guarantee

`DRHOLDBOARD=0` (default): verified byte-identical **both before and after** the fix-up commit
that changed the release path to RTS-immediately (md5 `25ad1c161c7936cce70099695278796b` both
times) — the flag gate means the whole feature, including the bugfix inside it, contributes zero
bytes when off.

### Two-sided validation (`tests/test_holdboard.py`, py65)

Same technique as the garble test: one persistent MPU across a sequence of hook calls, so PRG-RAM
state (the mirror, `HOLD_ACTIVE`, the frame counter) carries across "frames" exactly as on real
hardware, and the game's own destructive write is simulated landing **between** hooks — not
inside the same hook that observes the transition — because the driver hook only runs inside the
NMI, after that frame's synchronous main-loop work (including the destructive write) has already
happened; the test asserts this exact one-hook lag rather than hiding it.

- **Scenario A (inter-match, mode stays 4):** mirrors a distinct 256B pattern into the PRG-RAM
  buffer during play; simulates `RB337_STAGE_CLEAR`'s fill+text landing; on the arming hook, the
  destructive content is confirmed **still present** (the honest one-hook lag); on the very next
  hook, both pages read back exactly the pre-clear pattern and `L0300`/`L0380_UPDATE_ROW` both
  read `$0F`. A follow-up hook with START set releases (`HOLD_ACTIVE`+`MATCH_ACTIVE`→0).
- **Scenario B (set-final, mode 4→5→7):** same shape via the `not_play` arm point; confirms
  **both** pages (not just one) are restored, matching `TOP_7`'s both-pages fill. START releases here too.
- **Scenario C (CvC safety cap):** a non-`HUMAN_P1` build with `DRHOLDBOARD_F=20` and no START
  ever injected auto-releases within 19 hooks — confirms the nav cart cannot wedge.
- **Scenario D (flag-off identity):** `DRHOLDBOARD=0` emission deterministic across two builds;
  `DRHOLDBOARD=1` differs.

All pass. Full existing regression suite (12 files spanning nav/pocket/study/cart-matrix)
re-passes with both changes applied.

## Candidate build

```
DRBUSYESC=1 DRCOLDINIT=1 DRHUMAN=1 DRMINTHINK=12 DRNAVDWELL=0 DRNOFREEZE=1 DRPENDBOUND=1 \
DRPOCKET=1 DRRECOMMIT_NOFREEZE=1 DRSLAM_KOPEN=32 DRSTALLWD=1 DRSTUDYCOUNTS=1 DRWRETRY=1 \
DRHOLDBOARD=1 \
tools/romgen.py build --out tmp_carts/drmario_stomper_vs_you_v6_boardhold.nes --tag boardhold-v6
```

`tmp_carts/drmario_stomper_vs_you_v6_boardhold.nes` — md5 `3e7c6ed92daa80fc77320be6de73cc45`,
98,320 bytes, mapper 100. Recipe recorded at `roms/manifests/boardhold-v6.json` (base ROM md5
`7d307c30...`, emitter md5 `8e3fa439...`, commit `4cce693`) and **reproduces byte-exact** from
that commit via `tools/romgen.py rebuild roms/manifests/boardhold-v6.json`. Base profile is the
same v4-coldinit flag set used by the shipping Pocket/MiSTer human cart, plus `DRHOLDBOARD=1` on
top of Job 1's garble fix (which is unconditional, not flag-gated — it's a bugfix, not a feature).

## Blockers

None for either job — both are code-complete, tested two-sided at the RAM/OAM level (the only
level reachable without a mapper-100-capable emulator; Mesen cannot run this cart, per project
notes), and committed. Not done, and explicitly out of scope per the task: a real Mesen/MiSTer
visual confirmation of either fix (mapper 100 isn't Mesen-emulable; no hardware access was
authorized for this task), and no A/B of the ~40% active-play cost against real hardware timing —
flagged above as the one place a smarter implementation (page-alternating mirror) is available if
the current cost turns out to matter in practice.
