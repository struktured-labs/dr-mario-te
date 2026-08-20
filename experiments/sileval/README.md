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
| `seeds_sileval.txt` | 240 pre-registered seeds (recipe in the prereg; alias-deduped, seed 1 excluded) |
| `sileval.env.example` | the only place the new box's IP + pinned template md5s live |
| `mgl/` | loaders for both arms (both reference the proven θ400 core `de7dea35`) |
| `vendor/seedjit_ss.py` | vendored seed-injection tool (`a26a0d5f`), no gitignored-path dependency |

Refusal-gate verification (2026-08-20, offline, no network): 5/5 mutants refused
with exit 2 — placeholder IP, live-box IP (driver + watchdog), unpinned
templates, wrong template md5. Positive control: vendored seedjit patched seed
27875 into a real pre-generation template and read it back (0x6ce3, mode $00).
