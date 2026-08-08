# bidwell — player style profile

*Community handle: **bidwell**. Main organizer of the TooManyGames DrMC event;
community nickname "Dr. Mario" (the outfit). Expert-tier player.*

## Style at a glance

- **Expert-tier community player and DrMC/TMG event organizer** — has never faced the AI; a future showcase opponent with scene weight.
- **Lead, not a finding (n=8 volleys, below every confidence band)**: his separated 2024 broadcast profile shows the **highest fast counter-fire rate in the ensemble** — P(counter-volley <=5s | 4-6-cell clear) = 52.0% — suggesting an aggressive fast-follow-through attacker, pending more footage.
- The earlier "slow tempo" read of his match was an artifact of pooling with his slower opponent; treat his own tempo as unestablished.
- Best-quality expert-move material we own (TMG 2026 handheld VOD, never-publish) awaits a perspective-rectification front end.

## Record vs the AI

None yet — bidwell has never played the Combo Stomper. High-value future
opponent: an expert-tier community player AND event organizer, so a good
showing (or a dignified loss) in front of him carries scene weight.

## Footage on hand (unprocessed)

One recording exists, and it is the best expert-move material we own:

- `/mnt/data/drmario/expert_vods/personal-recordings/20260628_tmg2026_struktured_vs_bidwell.mov`
  — struktured vs bidwell, TooManyGames 2026 (Greater Philadelphia Expo
  Center, Oaks PA), 337 s, 1080p60 phone camera. **NEVER-PUBLISH** (friend's
  handheld footage; see README_NEVER_PUBLISH.txt — no public shares, no
  public corpus manifests without struktured's explicit approval; internal
  analysis is fine).
- Caveats for processing: handheld, off-screen, perspective/glare/rolling
  shutter — the manifest itself files it as a hard-mode robustness asset for
  the vision pipeline, and OCR was previously skipped as too heavy. The
  2026-08-04 vision/tracker stack (built for clean capture-card footage) is
  NOT expected to work on it without a perspective-rectification front end.

## Style (footage-observed, 2026-08-05 — bursty pressure fit only, not the full metric battery)

**Supersedes the note above that the only footage is the never-publish TMG handheld clip.**
Broadcast footage of Bidwell exists and is usable: the 2024 DrMC Championship archived every
bracket on YouTube, and Bidwell competed in the White Bracket under his in-game alias.

*Attribution: HIGH confidence — on-screen nameplate "(19) Robert Smith" cross-referenced against
the White Bracket's own `.description` roster line "19 - Chris Bidwell (as Robert Smith)", which
explicitly names the alias.* Footage:
`youtube-drmc-official-2024/009_20241119_B3-PEE6P23Q_THE_2024_DrMC_Championship_-_White_Bracket.mp4`,
t≈200-480s, top-pair slot of the 4-way-split broadcast, vs. Missy (seed 46). Part of the
style-ensemble program (`eval47/STYLE_ENSEMBLE_V1.md`), not the standard metric battery (still
n=0/not run — the handheld TMG clip remains the only material for that, and remains hard-mode for
vision per its own manifest note).

**UPDATE 2026-08-05 (pass 3): per-player separation applied, and the picture flipped.** The n=13
pooled number above summed Bidwell's AND Missy's events together. Refactored to a per-player
SENDING profile (see `eval47/STYLE_ENSEMBLE_V1.md` §5-7): **Bidwell alone: n=8 volleys —
UNINFORMATIVE** (below even the LOW-CONF band; too thin for a settled claim). Own clears n=27.
Reporting the number anyway per the team rule, heavily caveated:
- P(counter-volley within 5s | clear 4-6 cells) = **52.0% (n=25)** — the HIGHEST of any per-player
  fit in the entire ensemble so far, including struktured's own (28.2%) and Jarsdad's (50.0%)
- inter-volley gap 29.1s (n=7 gaps) — still on the slower side, though the sample is now tiny

**This reverses the pooled-match read.** Pass 2's pooled fit called this "the slowest match in the
ensemble" — but Missy's own separated profile (P(4-6)=18.8%, n=32; gap 35.8s) is markedly slower
than Bidwell's own numbers. The pooled "slow" character looks, on this data, like it was driven
more by Missy's response profile than by Bidwell's own attacking tempo — **a hypothesis, not a
finding, given n=8**, but a notable reversal worth flagging rather than repeating the old pooled
read. Needs more footage (a second window/match) before treating Bidwell's own tempo as
established either way.

## Why he matters to the project

- Expert-move corpus: 5.6 minutes of expert placements is exactly the
  (state, move) material the player-data program wants, and the
  agreement-scoring contrast (expert vs struktured on comparable boards) is
  a ready-made evaluation.
- Style-space: likely a distinct pressure profile from both struktured and
  dr_lulu — a third point for the pressure-model ensemble once any readable
  footage exists.
- Community: the DRMC/TMG scene connection makes him a natural future
  showcase opponent (RWE booth arc).

## Evidence index

- The TMG 2026 VOD (path above, never-publish).
- No photos in `evidence/` yet.
