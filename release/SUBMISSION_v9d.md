# romhacking.net submission kit — Dr. Mario Training Edition v9

Everything below is ready to paste. **Publishing is manual and user-side** (his account).

- **Patch**: `drmario_te_v9d.bps` — apply to Dr. Mario (USA), MD5 `d3ec44424b5ac1a4dc77709829f721c9`
- **Patched result**: MD5 `0f8f5d89dcf938144d24977d4faf2628` (verify after applying)
- **Full notes**: `RELEASE_NOTES_V9.md` · **QA evidence**: `V9D_QA_EVIDENCE.md`
- **Screenshots**: `screenshots/01_title.png`, `02_level_select.png`, `03_midgame_2p.png`,
  `04_study_2p.png` (2x nearest-neighbour, captured from the framebuffer of the patched ROM)

★ `04_study_2p.png` is the one to lead with: it shows every v9 fix at once — "STUDY" lifted
clear of the two-player header, BOTH players' next-pill previews above their own bottles,
and the VIRUS counters reading 60 and 04 (a two-digit and a leading-zero value, both
BCD-correct — the bug that rendered 48 as "72" in a pre-release build).

## Description blurb (short)

Dr. Mario Training Edition adds a **VS CPU** mode and a **Study Mode** pause. Pause during
play and the screen stays rendered and frozen — bottle, viruses, the falling capsule, both
players' next-pill previews and the level/virus counters all remain visible, so a position
can actually be studied instead of blanked. v9 also fixes a lock-up present in the
published v6.

## Description blurb (long)

Two additions to Dr. Mario (USA):

**VS CPU** — press SELECT on the title screen until the heart sits on 2 PLAYER GAME, then
SELECT once more to arm CPU control of Player 2 (the level-select screen pins both players
together when armed — that's the confirmation). Player 2 is then played by a heuristic AI
with a human-like move cadence. No separate menu line yet; a visible "VS CPU" label is
planned.

**Study Mode** — pressing START freezes the game *with the screen still drawn*, instead of
the vanilla blank "PAUSE". The bottle, every virus, the falling capsule, the next-pill
preview and the LEVEL/VIRUS counters all stay on screen and frozen; in 2-player and VS CPU
both players' previews are shown, each above its own bottle. START again resumes cleanly.

**If you are running v6, upgrade.** v6 — the version currently published — can lock up:
one of Study Mode's code fragments was placed at an address the game also executes as part
of a print table. v9 relocates all of it into documented free space. Also fixed since v6:
the "floating capsule after START" bug in 2-player, level-select corruption, and blanked
counters while paused.

Not shown while paused: the Dr. Mario throwing figure and the magnifier viruses, which are
built by a game phase the freeze skips. Everything study-relevant is shown.

Standard MMC1 (mapper 1) — runs on accurate emulators and on MiSTer.
