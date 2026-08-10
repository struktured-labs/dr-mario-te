# Multi-match ship gate (the harness that would have caught the v6c soft-brick)

## Why this exists

The v6c acceptance harness (`census_run_dist.lua`) keeps P1 alive on purpose — it erases P1's
non-virus cells every frame so P2 plays unbroken games. That instrument means **a match never
ends**, so every flag whose behaviour lives on the end-of-match path is *structurally
unexercisable* by it. `DRHOLDBOARD` is exactly such a flag, and it shipped in v6c as a cart that
soft-bricks after one match: the AI plays a match, the cart drops to the title mid-match, and it
then loops `0→1→2→3→8→0` forever, never reaching play again. Every v6c acceptance number was
true and irrelevant to that flag.

`fieldplay.lua` is the opposite instrument: **it lets matches end.** P1 (the human seat on a
DRHUMAN cart) is left to top out exactly as an idle human would, so the whole
end-of-match → title → next-match cycle runs, repeatedly.

## What it measures

Per run it reports, from `run.log`'s `SUMMARY` line and the `MODE` transitions:

| metric | healthy | meaning |
|---|---|---|
| `8->4` count | high | matches actually STARTED |
| `4->5` count | ≈ matches | clean round-ends via the topout path |
| **`4->0` count** | **0** | **catastrophic mid-match abort to title — the v6c signature** |
| `matches_ended` | ≈ `8->4` | matches that finished |
| `patho_frames` | 0 | frames with the board-hold latch armed during live play |

A `4->0` is the kill condition. On the v6c ship cart it fires on match 1; on v6b on match 4; on
the `DRHOLDBOARD=0` control it never fired in 10 matches.

## Running it

```bash
# 1. remap the SHIP bytes to MMC1 so Mesen boots them (header-only; PRG+CHR untouched)
python3 tools/gate/remap_mapper.py roms/<cart>.nes /tmp/<cart>_mmc1.nes

# 2. multi-match run. 18000 frames ~ 20 matches. Mesen is SINGLE-INSTANCE and shared:
#    launch_fp.sh WAITS for a free seat and never kills another lane's run.
bash tools/gate/launch_fp.sh <outdir> /tmp/<cart>_mmc1.nes <tag> 18000 0 114 34 600

# 3. verdict
grep -a SUMMARY <outdir>/run.log
grep -ac '4->0' <outdir>/run.log     # MUST be 0
```

Run it against the **exact ship bytes** (header remap only) with the **full shipping flag set**.
A cart that does not clear 10 matches with zero `4->0` does not go near the SD card.

## Companion instrument

`probe2.lua` is the mechanism probe, not the gate: MMC1 shift-register write ring + straddle
counter + `$8036` bank0-entry canary + RAM-wipe canary. Use it when the gate FAILS, to tell a
mapper-interleave crash (`$DFFF` run of 4 then `$FFF0`, same frame as a `$8036` entry and a wipe)
from a logic fault. `ramscan2.py` does static reach analysis on PRG-RAM addresses — it accounts
for an 8-bit index walking in from a lower base, which a naive operand scan misses.

## Gotchas

- Mesen needs the sandbox disabled and a DISPLAY; `launch_fp.sh` handles Xvfb.
- ⚠ **CORRECTED**: `emu.getState().cpu` is nil, but that does **not** mean registers are
  unreadable — I concluded that and it nearly cost us a live A-integrity assertion.
  `getState()` returns a **flat map with dotted string keys**: there is no `cpu` *table* to
  index, but **`cpu.a` is a valid key**, and likewise `cpu.pc`, `cpu.sp`, `cpu.ps`, `cpu.x`,
  `cpu.y`. Derived from `NesCpu.cpp` / `Serializer.cpp`'s `NormalizeName`, confirmed empirically
  by the soak lane. **One failed access is not proof an API is absent — check its shape first.**
- No `emu.*` call may run inside a memory callback; it silently kills the callback for the rest
  of the run — which reads as "the check never fired", i.e. indistinguishable from a PASS. Sample
  registers from an event callback (`endFrame`), or prove the exec-callback path survives.
- A low `goes`/matches count is NOT a cart property — this rig has faked "reached mode 4 then did
  nothing" three times on carts that were fine (v6e: `goes=2` → re-run 155). Re-run it AND pair it
  with a known-good cart on the same runner before believing it. A tag-verified, SUMMARY-bearing
  log does not rule it out.
- Reap Mesen by the **PID you launched**, never `pkill -f <cartpath>` — the runner's own command
  line contains that path, so the pattern matches the runner and kills it mid-report.
- `emu.write` takes three args `(addr, value, type)`; a four-arg call dies inside the callback.
