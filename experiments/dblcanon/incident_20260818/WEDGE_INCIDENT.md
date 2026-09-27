# SOAK WEDGE — CvC tuck cart, 2026-08-18 ~20:21–22:21 EDT

**Found while collecting the old-core control arm for #123 arm (b). Not a #123 defect —
the wedge is on the CURRENTLY SHIPPED core+cart, with no DRDBLCANON anywhere near it.**

## Verdict

The live soak wedged **mid-match** and stayed wedged until the watchdog reload. It did not
crash, did not drop to title, and kept a plausible-looking board on screen — which is why a
screenshot alone would have read as healthy.

## The replay handle (this is the valuable part)

    2026-08-18T20:21:45-04:00  seedjit  seed=4557
      template_md5=0d9e7b2fad7ea47869ea3f8c41e787f8
      patched_md5 =3ba69e69b334cdbfca1465aefff2fb27
      mgl=/media/fat/theta400_cvc_tuck.mgl

Core `NES_theta400_20260809.rbf` **de7dea35** · cart `drmario_tuck_cvc_mister.nes` **9fefaedb**
(both hashed on the box). Because #111 shipped seed injection, **seed 4557 is re-runnable** —
if it re-wedges, this becomes the **first reproducible member of the freeze family**
(cf. #40 copro-wait stall, #42 black-screen, seed-30011). That is the single highest-value
follow-up here.

⚠ nmi-fix's #120 closeout explicitly listed "CvC-tuck long-soak bound" as NOT closed. This
looks like that caveat cashing.

## Frozen-state fingerprint

~99 save-states over ~7 minutes, **every one identical**:

| field | value |
|---|---|
| `$0046` mode | **4** (in play — not title, not menu) |
| P2 board occupancy | **83 / 128**, unchanging |
| `$0381/$0382` capsule | **cA = cB = 2** (a DOUBLE, frozen) |
| `TGT_O2 ($6153)` | **3**, unchanging |
| `STABLE_CT2 ($6171)` | **254 — SATURATED** |

Internal RAM: **4 bytes differ out of 2048** between the first and last sample. Whole-file
sampled sweep: 1 differing byte in ~13,700 sampled. Save-state md5s all differ (so the
capture path is live and this is not a stale-file artifact) while the CONTENT is frozen.

`STABLE_CT2` saturated at 254 is the sharpest signature: the driver's published target has
been unchanged for a saturating number of hooks, i.e. the executor is holding a target that
never completes. `remote.log` shows `core started 20:21` and nothing until the next cycle.

## ⚠ How this nearly produced a false result for #123

Sampling one frozen frame 99 times yielded "double capsules 53/53, expensive share **0.0%**".
Read naively that says *the OLD core already never publishes the expensive orientation*, which
would refute #123's entire premise. It is an artifact. **Zero variance across 53 samples is a
dead read, not a result** — any future control arm must assert the sample set VARIES
(occ / cA / TGT_O2 all moving, `STABLE_CT2` unsaturated) before any rate is computed.

## Instrument bug found on the way

`tools/livecatch/ss_decode.py` **refuses every one of these captures** ("$0400/$0500 do not
hold a legal playfield") because its cart base is hardcoded near `0x103508`. On this
core/cart the real base is **`0x103308`** (internal RAM `0x102b08`), recoverable by signature
scan on `NAV_MAGIC ($6149)==0xA5` **and** `MATCH_ACTIVE ($6164)==1`. The decoder should derive
the base by signature, exactly as `mister-savestate-ram-read` prescribes — as written it
silently rejects valid data from the current shipped pairing.

## Evidence

- `screen_wedged_221242.png` — the static mid-match board (this file).
- ~99 raw `.ss` captures + capture log: `tmp/wedge_20260818/` (gitignored; ~130 MB).
- Capture method: `tools/livecatch/ring_capture.sh --slot 4 --interval 4` (read-only; slot 4
  is the designated safe slot). The MiSTer was otherwise untouched — no core load, no MGL
  write, no file overwritten.

## Recovery

No intervention. The ~2 h watchdog reload (`:20–:21` past even hours) restores the soak
unconditionally. Cadence confirmed from `remote.log`: reloads at 16:20, 18:20, 20:21 EDT.
