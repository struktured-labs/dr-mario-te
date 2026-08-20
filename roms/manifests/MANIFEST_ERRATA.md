# Manifest errata

## 2026-08-19 — hardened-*-20260819 manifests: `dirty: true` is CORRECT; a commit message said otherwise

The five `hardened-*-20260819.json` manifests record `git.commit = bbc08b3` with
`git.dirty = true`. **The dirty flag is correct and stays.** Commit 3b5f120's message
("re-recorded from the clean commit (dirty:false)") is WRONG on that one field — the tree
was never porcelain-clean, and history is not rewritten to fix a message.

**What the dirt is** (so a future reader can verify none of it is a build input): ten
pre-existing untracked files, all mtime 2026-08-10..16, i.e. days before the hardened
lane started (2026-08-19 ~20:00 EDT):

- `roms/manifests/audit-hb1.json`, `cen6e-off.json`, `cen6e-rl.json`,
  `prgram-holdboard.json`, `prgram-no-prestart.json`, `prgram-ship-v6e.json`,
  `prgram-trace.json` — stale manifests of OTHER carts; romgen only reads a manifest
  when explicitly asked to rebuild that manifest.
- `tools/build_cen6e.sh` — another cart family's build script; not invoked by
  `tools/build_hardened.sh`, `tools/romgen.py`, or the emitter.
- `tools/gate/run_xcart60.sh` — a gate runner; not part of any build path.
- `tools/relatch_sig.bin` — a gate artifact; grep confirms nothing under `tools/` or the
  emitter reads it (DRRELATCH is pure code emission, no data file).

**Build inputs and how each is pinned:** emitter `patch_cartridge_copro.py` (tracked at
bbc08b3; md5 in each manifest), `patch_vs_cpu.py` + `tools/romgen.py` (tracked),
base ROM `drmario_v28cs.nes` (deliberately untracked — `*.nes` is gitignored to keep
copyrighted content out of git — and hash-pinned as `base_rom.md5 = 7d307c30…` in every
manifest; romgen refuses a wrong base). The full DR* flag set is in each manifest's
`flag_snapshot`. So reproduction is: checkout bbc08b3 + a base ROM matching the pinned
hash + `romgen rebuild <manifest>` — none of the untracked files participate.

Why this entry exists: a wrong provenance field left standing is how
tier-3-hash-confound class problems start (team-lead ruling, 2026-08-19).
