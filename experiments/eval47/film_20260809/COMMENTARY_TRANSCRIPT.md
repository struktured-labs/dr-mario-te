# v6c session — owner verbal commentary transcript (2026-08-09)

Transcribed from the three session recordings in `/home/struktured/Videos/drmario_sessions/`.
The owner reported v6c cart bugs aloud assuming the mic was recording. **It was.**

## Headline

**All of the owner's Dr. Mario bug commentary is in segment 1, between t=52.1 s and t=90.4 s.**
Segments 2 and 3 contain **no Dr. Mario commentary at all** — he had moved on to a different
game (see [Segments 2 and 3](#segments-2-and-3--not-dr-mario)). Do not mine them for freeze-5
evidence; they are neither for nor against.

Every bug he named is **corroborated on the video frames**, and the instrument found one more
event that he described only vaguely ("weird flickering") which is in fact **the cart dropping
out of a live VS match back to a corrupting title screen**.

---

## Method / provenance

| | |
|---|---|
| Audio | 1 stereo AAC track per file, 48 kHz. Speech and game audio are **mixed on the same track**; L≈R (side signal 26 dB down), so no source separation is possible. |
| Extraction | `ffmpeg -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le` |
| STT | `uvx --from whisper-ctranslate2 whisper-ctranslate2 --model large-v3 --device cpu --compute_type int8 --threads 16 --language en --word_timestamps True` (CUDA unavailable: `libcublas.so.12` missing). The pinned venv at `dr_mario_rl/tmp/venv` was **not touched**. |
| Passes | **A** raw audio, no VAD, no prompt · **B** loudness-normalised, no prompt · **C** normalised + Dr. Mario domain `initial_prompt`. Three passes so that disagreement exposes hallucination. |
| Working files | `/home/struktured/projects/dr-mario-qa-wt/tmp/commentary/` (wavs, `out_A_raw/`, `out_B_norm/`, `out_C_prompt/`, `frames/`, spectrograms) |

Levels: segment 1 peaks −0.6 dBFS (clean speech); segments 2–3 peak −10.6 / −9.4 dBFS.

**Reliability.** Whisper's own per-segment `no_speech_prob` separates the two classes cleanly:

| Window | avg_logprob | no_speech_prob | verdict |
|---|---|---|---|
| seg 1, 52–90 s (the bug commentary) | −0.263 … −0.286 | 0.083 – 0.300 | **high confidence**, and frame-corroborated |
| seg 1, 0–10 s | −0.552 | 0.097 | background game audio, not Dr. Mario |
| seg 2, all | −0.743 … −0.341 | **0.407 – 0.654** | low confidence, non-Dr.-Mario content |
| seg 3, all | −0.570 … −0.365 | 0.268 – 0.552 | low confidence, non-Dr.-Mario content |

---

## THE BUG LIST — in his words

Quotes are verbatim from pass A (raw audio, no prompt); word-level timestamps.
Wall-clock is derived from the filename start time `20:29:15`.

### BUG 1 — blue bars over the title-screen copyright line
> **"Okay, first thing I want to comment on is the weird blue streak in the bottom."** — seg 1, t=52.10 (20:30:07)
> **"That's messed up."** — t=56.58

**CORROBORATED.** Frames at t=5, 30, 55, 62 all show two solid blue horizontal bars across the
bottom of the title menu oval, overwriting the `© 1990 Nintendo` line — only `1990` and `Nin`
survive, and the `©` is gone.

**Lead:** the bars sit *exactly* on the copyright line, which is where a branding overlay would
be written. **After the reset at t≈85.8 the same title screen redraws with `© 1990 Nintendo`
fully intact** (frames `flash_85_95.jpg`, `flash_88_10.jpg`). So the corruption is on the
**boot/branding draw path only**, not a permanent tile/CHR fault. That points at the
branding-at-boot feature rather than at the ROM.

### BUG 2 — logo still says TM, not TE
> **"It should show TE instead of TM in the upper right. That's also just something that I thought was done. It's not done."** — seg 1, t=57.44–63.34 (20:30:12)

**CORROBORATED.** The superscript at the top-right of the Dr. MARIO capsule reads `TM` in every
title frame, boot draw and post-reset draw alike. He explicitly flags this as a **regression
against something he believed was already shipped.**

### BUG 3 — title menu cursor locked on "2 PLAYER GAME"; UP does nothing
> **"It's locking the player 2 now."** — seg 1, t=64.24 (20:30:19)
> **"When I hit up, yeah, it's still locking the player 2, but whatever it's fine."** — t=69.70 (20:30:24)

**CORROBORATED.** The heart cursor sits beside `2 PLAYER GAME` in every title frame and never
moves, including across his UP press. The cart then auto-advances into the 2-player setup screen
(`VIRUS LEVEL 11/11`, `SPEED MED`, `MUSIC TYPE FEVER`) at t≈76.

Note his resigned follow-up, which reads as *the driver overrode my input*:
> **"What I wanted to do… Just not sure if that's what you wanted to do. Alright, here we go."** — t=73.98–79.00

### BUG 4 — title screen corrupts into "random blue and red stuff"
> **"It's just showing random blue and red stuff. It's really screwed up."** — seg 1, t=66.68 (20:30:21)

**CORROBORATED.** Frames at t=66, 68, 70, 72 show the title screen broken into large blue and
magenta rectangular blocks with the `Dr.` text partially erased, the menu oval torn apart, and
black scanline banding on the right. Per-frame luma confirms this window is genuinely unstable
(t=64–74: sd 4.01, 3 frame-to-frame jumps >5, versus sd 0.71 and **zero** jumps for t=10–64).

### BUG 5 — "weird flickering" — this is the big one, and it is worse than he realised
> **"Alright, I see some weird flickering which I think is… it's all buggy."** — seg 1, "flickering" @ t=84.76 (20:30:39.8)

**CORROBORATED, AND IT IS NOT A FLICKER.** What the instrument finds at t=85.6–90.6:

1. At t=85.60 the cart is in a **normal, live VS match** — Level 11/11, MED/MED, `VIRUS 46/46`,
   both bottles rendering cleanly. Gameplay luma over t=80–85.6 is rock stable (sd 0.30, zero
   frame-to-frame jumps >5). **Nothing is wrong up to this instant.**
2. At t=85.771 the screen goes **fully black for 0.117 s (7 frames)**.
3. At t=85.95 it is **back at the TITLE SCREEN** — the live match is gone, unrequested.
4. It then **alternates every 1–3 frames** between a correctly-drawn title and a badly corrupted
   one whose logo is replaced by garbage tiles and whose menu text reads
   `1 974B5A 5485 / 2 974B5A 5485 / C 1330 GHIJKL`. Fragments of the **gameplay** nametable
   (a vertical `VIRUS` panel) are visible inside the corrupt frames — two different screens are
   being drawn on alternate frames.
5. Two more full-black spans follow at **t=87.921** and **t=90.088**, each 0.116–0.117 s.
   Cadence 2.150 s and 2.167 s.
6. The recording ends 0.4 s later, at t=90.62 (20:30:45.6), still in this state.

Quantified: t=85.7–90.6 has luma sd **11.27** and **9** frame-to-frame jumps >5, against sd
**0.30** and **0** during the preceding gameplay.

**This is a mid-match crash into a repeating title-screen corruption loop, and it is the last
thing on the capture before the feed dies for good.** He narrated it as "flickering" because
that is what it looks like at speed.

---

## FREEZE-5 RELEVANCE — read this before using segments 2/3

The blackout timeline, measured rather than assumed:

| Wall clock | t | State |
|---|---|---|
| 20:30:40.8 | seg1 85.771 | first full-black flash; live VS match lost, back to title |
| 20:30:42.9 | seg1 87.921 | second black flash |
| 20:30:45.1 | seg1 90.088 | third black flash |
| 20:30:45.6 | seg1 90.62 | **recording 1 ends, still looping** |
| *(gap ≈ 2 min 1 s — no recording)* | | |
| 20:32:47 → 20:33:51.9 | seg 2, all 64.85 s | **video absolutely black, every frame** |
| 20:34:05 → 20:35:42.0 | seg 3, all 96.98 s | **video absolutely black, every frame** |

The black in segments 2–3 is not a dark scene: `signalstats` gives **YMAX = 16 on every one of
3890 and 5820 frames** — the video-range black floor, i.e. a dead feed.

**But the owner was not looking at it.** His voice in segments 2–3 is narrating a completely
different game, calmly and continuously. He never mentions Dr. Mario, a freeze, a black screen,
or the handheld.

**Verdict: segments 2 and 3 are NOT usable evidence for or against freeze-5.** The team lead's
decision rule ("if he describes a black/frozen screen → freeze-5 data point; if he describes
ongoing play → capture-side only") does not apply, because he describes **neither**. He had
moved on. Absence of a complaint here is not evidence the console was fine.

**The real freeze-5 data point is in segment 1, not segments 2–3** — the t=85.6–90.6 crash loop
above is a first-party capture of the cart going from healthy live play to a repeating
black/corrupt cycle, 2 minutes before the feed is permanently dead.

---

## Segments 2 and 3 — NOT Dr. Mario

All three passes, **including pass C which was primed with Dr. Mario vocabulary** (`STUDY button,
virus count, capsules and pills, the P2 side, the coprocessor, black screen, freeze`),
independently decode the same non-Dr.-Mario content. A Dr.-Mario-primed decode that still
returns "thievery" and "healing potion" is strong evidence the audio really is that, and not
Dr. Mario commentary mangled by low SNR.

Content: an RPG with a merchant, a **Thievery** skill, stealing at night, and jail, plus a
dice/betting minigame. Representative lines, agreed across passes:

- seg 2: *"Why do you keep disappearing?"* · *"you got the three hammers, that's the second best, right?"* · *"every time I bet, I have a really good roll"* · *"I don't care about the history, just give me the cash!"* · *"62! Look at that!"* · *"I'm not even cheating that much."*
- seg 3: *"I need a healing potion!"* · *"Can't you sell me anything?"* · *"I got this money from your husband."* · *"Can I climb this?"* · *"we can also try stealing lots of people"* · *"It's late at night. Why not?"* · *"What's our thieving at right now? …26. I'm assuming out of 100, that's not too bad."* · *"In the name of justice…"* · *"Spend your life in jail."*

The **first ~10 s of segment 1 is the same background game**, not Dr. Mario — *"the history…"*,
*"62, look at that"*, *"I haven't been cheating that much"*. His Dr. Mario commentary begins only
after his mic check at t=41.66: **"Mic working? Cool."**

**Not duplicated audio.** FFT cross-correlation of seg1[0:12] against seg2[26:52] peaks at
**NCC 0.245**, versus **1.000** self-correlation and **0.022** for a control window — similar
content from the same background game, at genuinely different moments. The recurring phrases are
real, not an STT repeat artifact.

Spectrograms agree: segment 1 carries time-varying musical tonal content; segments 2–3 carry only
speech formants plus perfectly constant hum lines (unchanging across 65 s and 97 s — no melody
does that).

---

## FULL TRANSCRIPT

### Segment 1 — `20260809_202915_struktured_v6c.mkv` (90.62 s, starts 20:29:15)
**Video present throughout. This is the only segment with Dr. Mario commentary.**

```
[ 0.00 -  4.10]  The history is giving me the gash. 62, look at that.        <- background game
[ 6.76 - 10.42]  Russian mess. Shit, I haven't been cheating that much.      <- background game
[41.66 - 42.82]  Mic working? Cool.                                          <- MIC CHECK
[48.18 - 49.06]  What is this for?
[49.70 - 50.14]  Wow.
[52.10 - 55.40]  Okay, first thing I want to comment on is the weird         *** BUG 1
                 blue streak in the bottom.
[56.58 - 57.44]  That's messed up.                                           *** BUG 1
[57.44 - 63.34]  It should show TE instead of TM in the upper right.         *** BUG 2
                 That's also just something that I thought was done.
                 It's not done.
[64.24 - 68.68]  It's locking the player 2 now. It's just showing random     *** BUG 3 + BUG 4
                 blue and red stuff. It's really screwed up.
[69.70 - 72.76]  When I hit up, yeah, it's still locking the player 2,       *** BUG 3
                 but whatever it's fine.
[73.98 - 75.20]  What I wanted to do
[76.68 - 79.00]  Just not sure if that's what you wanted to do.
                 Alright, here we go.
[81.40 - 81.80]  Alright
[81.80 - 90.38]  Alright, I see some weird flickering which I think is,      *** BUG 5
                 it's all buggy, buggy does that.
                 ("flickering" @ 84.76)
```

Trailing words of the last line are low confidence; passes render it *"it's all buggy, a buggy
disaster"* / *"buggy does that"*. The word **"flickering"** is stable across all passes.

### Segment 2 — `20260809_203247_struktured_v6c_part2.mkv` (64.85 s, starts 20:32:47)
**Video black on every frame (YMAX=16). No Dr. Mario content.**

```
[ 0.00 -  4.14]  If I could do that by the nature, I don't know if I would be able to do it again.
[ 5.30 - 10.52]  Keep that... [unintelligible] ...and hold the three hammers.
[10.78 - 11.62]  Look at this.
[14.56 - 15.24]  I'm brushing it.
[17.94 - 19.38]  Why do you keep disappearing?
[19.66 - 22.48]  Ooh, you got the three hammers. That's the second best, right?
[26.92 - 30.08]  I haven't caught on, but every time I bet, I have a really good roll.
[33.92 - 38.30]  Yeah. I don't care about the history, just give me the cash!
[39.60 - 40.80]  62! Look at that!
[43.06 - 44.02]  I'm rushing this.
[45.36 - 47.06]  I'm not even cheating that much.
[   ~50       ]  But that's probably the ace of them, so I don't know if I would do it again.
[57.34 - 60.60]  Oh, should I have, like, lost some? Should I keep playing with me?
[61.46 - 62.92]  Should I never play with me again?
```

### Segment 3 — `20260809_203405_struktured_v6c_part2.mkv` (96.98 s, starts 20:34:05)
**Video black on every frame (YMAX=16). No Dr. Mario content.**

```
[ 0.00 -  2.28]  I think it's just a relative. I need a healing potion!
[ 5.86 -  7.38]  Can't you sell me anything?
[ 9.52 - 10.38]  Oh, here we go.
[12.02 - 13.00]  There we go.
[14.02 - 14.54]  25?
[16.30 - 16.82]  Sweet!
[17.56 - 20.44]  I got this money from...
[23.86 - 26.40]  I got this money from your husband at the tavern.
[30.62 - 38.68]  Alright, let's go take this to, uh, what's his name?
                 Oh, here's his place, let's see if I can find him.
[39.28 - 44.28]  Can I climb this?
[48.60 - 53.52]  Let's try another spot. Oh, we can also try stealing lots of people.
[54.44 - 57.08]  It's late at night. Why not?
[58.38 - 61.42]  Practice the trade. That guy's... he can wait until morning. Probably not.
[64.08 - 65.94]  What's our thieving at right now?
[66.14 - 69.98]  And 10, 14, thievery 26. I'm assuming out of 100.
[70.16 - 71.14]  That's not too bad.
[78.38 - 79.62]  In the name of justice.
[81.58 - 86.34]  It's unfortunate. Spend your life in jail.
[95.08 - 96.98]  Are there any tools or anything?
```

---

## Evidence files (committed alongside this transcript)

| File | Shows |
|---|---|
| `evidence/seg1_t05_bluebars.jpg` | BUG 1 + BUG 2 — blue bars over `© 1990 Nintendo`, `TM` top-right |
| `evidence/seg1_t62.jpg` | BUG 1 + 2 + 3 together, during his commentary; heart cursor pinned to `2 PLAYER GAME` |
| `evidence/seg1_t66.jpg` | BUG 4 — "random blue and red stuff" |
| `evidence/flash_85_60.jpg` | healthy live VS match, `VIRUS 46/46`, 0.17 s before the crash |
| `evidence/flash_85_95.jpg` | title screen after the crash — note `© 1990 Nintendo` is **clean** here |
| `evidence/flash_86_20.jpg` | corrupt title — menu reads `1 974B5A 5485 / 2 974B5A 5485 / C 1330 GHIJKL` |
| `evidence/cycle_montage.jpg` | 4×4 montage, t=85.6→88.2 at 5 fps — the whole clean/corrupt alternation |
| `stt_raw/{A_raw,B_norm,C_prompt}/` | all three STT passes, `.srt` + `.txt` |
| `stt_raw/run_stt.sh` | exact commands used, including the pass-C domain prompt |

## Recommended follow-ups

1. **Treat seg 1 t=85.6–90.6 as the freeze-5 artifact.** It is a clean before/after: healthy live
   VS at 85.60, black at 85.771, title screen at 85.95, corruption loop thereafter. The corrupt
   frames contain gameplay-nametable fragments, so capture the PPU nametable/CHR bank state, not
   just the CPU RAM.
2. **Blue bars (BUG 1) are a boot-path-only fault.** The post-reset redraw is clean. Diff the
   boot branding write against the post-reset title draw rather than hunting a tile/CHR bug.
3. **BUG 2 is a regression** by his own account — "something that I thought was done".
4. **BUG 3 (cursor pinned to 2 PLAYER, UP ignored)** is the driver overriding a human input at
   the title. Same family as the boot-nav dwell work.
5. Do not spend further effort on segments 2–3 audio; it is settled and it is not ours.
