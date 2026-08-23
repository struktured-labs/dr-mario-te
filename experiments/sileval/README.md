# sileval — DRP1SLICE silicon evaluation lane (task #139)

Staged, plug-and-play the moment the NEW MiSTer is on the network. Nothing here
touches the live soak box.

| file | what |
|---|---|
| `PREREG_SLICE_SILICON.md` | pre-registration (DRAFT until team-lead endpoint review) |
| `NEWMISTER_RUNBOOK.md` | new-box day-one: network, fingerprint gate, templates, shakedown |
| `OWNER_SETUP.md` | the owner's ~15 min of hands-on vs what is automated |
| `stage_bundle.sh` | assembles + md5-verifies the SD bundle at `out/newmister_bundle/` |
| `sileval_ab.sh` | the paired-seed ABBA A/B driver (systemd unit `drm-sileval-ab`) |
| `sileval_watchdog.sh` | 2h reload+seedjit soak loop for the new box (`drm-sileval-watchdog`) |
| `score_rows.py` | offline scorer: save-state → timeline CSV (mode, BCD virus, top-3-row occupancy) |
| `e1_winner.py` | **E1 PRIMARY reader** — per-match winners from `$031E`/`$039E`. Use this one. |
| `endframe_scorer.py` | adjudicate one END-FRAME capture (`$0309`/`$0389` primary, `occ_top3` corroborating) |
| `tier1_endframe.py` | cheap screenshot boundary classifier + its gate self-test (`--gate`) |
| `match1_winner.py` | DEPRECATED — virus-counter rule, ~100% UNREADABLE at any usable cadence |
| `seeds_sileval.txt` | 240 pre-registered seeds (recipe in the prereg; alias-deduped, seed 1 excluded) |
| `sileval.env.example` | the only place the new box's IP + pinned template md5s live |
| `mgl/` | loaders for both arms (both reference the proven θ400 core `de7dea35`) |
| `vendor/seedjit_ss.py` | vendored seed-injection tool (`a26a0d5f`), no gitignored-path dependency |

Refusal-gate verification (2026-08-20, offline, no network): 5/5 mutants refused
with exit 2 — placeholder IP, live-box IP (driver + watchdog), unpinned
templates, wrong template md5. Positive control: vendored seedjit patched seed
27875 into a real pre-generation template and read it back (0x6ce3, mode $00).


## ⚠ Two properties of the sample loop that will mislead you

Both are measured on population A (255 rows / 4,593 samples) and both have already
cost a lane a wrong conclusion. Read them before using `out/artifacts/`.

**1. The screenshots LAG the save-states — they are not a synchronous pair.**
The loop in `sileval_ab.sh` is `send_combo leftalt f2` → `pull_state` (which polls up
to 12 s) → `take_shot`. The PNG is therefore captured seconds AFTER the `.ss` beside
it. Consequence: for all 128 samples whose save-state is in the end-of-match window
(mode `$03`/`$05`/`$07`), the PNG shows the **next match's virus-fill animation**
(VIRUS 02/02, 17/17, 35/35, 48/48 — both bottles symmetric), not the ending.
**No game-over frame exists in any of the 4,593 banked screenshots.** Do not use these
PNGs as visual ground truth for a match ending; you will be looking at the wrong moment
and nothing will flag it. Any (input, label) pair drawn across these two transports
needs the skew measured first.

**2. The sampler floors at ~2.8 s, and "just sample faster" cannot fix an endpoint.**
Recovered from local file mtimes (scp does not preserve mtime, so local mtime = write
completion), medians over population A:

| step | cost | note |
|---|---|---|
| `take_shot` (.ss → .png) | **2.70 s** | p10 2.68 / p90 2.71 — a hardcoded `sleep 2` plus ~0.7 s of 4 sequential ssh round-trips. A floor, not load-dependent. |
| `pull_state` (save-state + scp) | **3.78 s** | old box |
| full cycle @ `SAMPLE_SECS=20` | 20.37 s | |
| full cycle @ `SAMPLE_SECS=5` | 6.50 s | asking for 5 s gets 6.5 s |

Save-state is **1,296 KB** vs **7.0 KB** for a PNG — a **184x** ratio. The end-of-match
window is ~2.5 s (capture ≈ min(1, W/T); observed 128/989 = 12.9% at T=20.37 s ⇒ W=2.64 s).
So a trigger-then-capture detector is structurally impossible here: tier 2 costs 3.78 s,
longer than the window it is trying to catch, and lands after mode `$07` has passed.

**The resolution was not a faster sampler.** `L9532_TOP_5` (`$9532`) increments the VS win
counters `$031E`/`$039E` *before* it writes mode 7 at `$9585`, and those counters persist
into the next match. `e1_winner.py` reads them and scores the banked corpus at
**987/988 = 0.10% unreadable at the unchanged 20 s cadence**. When an endpoint looks
cadence-bound, check whether the machine already writes the answer down.
