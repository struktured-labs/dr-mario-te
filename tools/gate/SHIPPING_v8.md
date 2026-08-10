# v8 rematch cart — provenance / shipping document

Generated from the recorded manifest, not transcribed by hand.

## SHIP CANDIDATE: `c-v8ship`

Blocks the MMC1 shift-register interleave (the root cause of the 2026-08-09 field crash)
AND clears the multi-match gate identically to the unhardened build.

- **output md5**: `087ff959ac510c613bbbd2eb1ac5ecf3`  (`roms/c-v8ship.nes`, 98320 bytes)
- **base ROM**: `drmario_v28cs.nes` md5 `7d307c3051ebc0f8a10e259e3c270acb`
- **emitter**: `patch_cartridge_copro.py` md5 `0bdf5653523fdad835f6f451bf38fc99`
- **commit**: `243cc0c0bd35444fb076489c9291373bc28ab045` (branch `v8-rematch`, dirty=True)
- **build**: `bash tools/build_v8.sh c-v8ship DRMMC1RST=1 DRRTIVEC=1 DRFCGATE=1`
- **rebuild/verify**: `python3 tools/romgen.py rebuild roms/manifests/c-v8ship.json`
- **remap for emulator QA only**: `python3 tools/gate/remap_mapper.py` (header bytes 6/7 only; PRG+CHR untouched)

### Gate results (18,000 frames, seed 114, matches allowed to end)

| cart | hardening | started | clean ends | aborts | searches |
|---|---|---|---|---|---|
| `c-v8ship` **(ship)** | MMC1RST + RTIVEC | 20 | 19 | **0** | 155 / 147 |
| `v8-fcgate` (control) | none | 20 | 19 | **0** | 155 / 147 |

Mechanism arms (3,000 frames): defect build `a-v6crepro` = 18 mixed-into-PRG loads / 18 RAM
wipes; both fix-on builds = **0 / 0**.

### Full flag set

| flag | value |
|---|---|
| `DRBUILDID` | `0` |
| `DRBUILDID_TAG` | `STUD` |
| `DRBUSYESC` | `1` |
| `DRCOLDINIT` | `1` |
| `DRCOLGATE` | `1` |
| `DRDISTGATE` | `1` |
| `DRDIST_DASEDGE` | `12` |
| `DRDIST_FLOORREL` | `0` |
| `DRDIST_GRAVROW` | `30` |
| `DRFCGATE` | `1` |
| `DRHOLDBOARD` | `0` |
| `DRHOLDBOARD_F` | `600` |
| `DRHUMAN` | `1` |
| `DRLEVEL` | `11` |
| `DRMINTHINK` | `12` |
| `DRMMC1RST` | `1` |
| `DRNAVDWELL` | `0` |
| `DRNAVDWELL_F` | `180` |
| `DRNAVESC` | `0` |
| `DRNAVESC_N` | `1200` |
| `DRNAVFIX` | `1` |
| `DRNAV_HOLD` | `1` |
| `DRNAV_M` | `24` |
| `DRNAV_M4` | `4` |
| `DRNAV_V4` | `1` |
| `DRNOFREEZE` | `1` |
| `DRP1NATIVE` | `0` |
| `DRP1WIGGLE` | `0` |
| `DRPENDBOUND` | `1` |
| `DRPOCKET` | `1` |
| `DRPRESTART` | `1` |
| `DRPROBE` | `0` |
| `DRRECOMMIT` | `1` |
| `DRRECOMMIT_NOFREEZE` | `1` |
| `DRREENTRY` | `1` |
| `DRRELATCH` | `1` |
| `DRROTFIX` | `1` |
| `DRRTIVEC` | `1` |
| `DRSEED` | `1` |
| `DRSLAM` | `1` |
| `DRSLAM_KCROSS` | `8` |
| `DRSLAM_KEND` | `255` |
| `DRSLAM_KOPEN` | `32` |
| `DRSLAM_LOWY` | `8` |
| `DRSLAM_MATURE` | `2` |
| `DRSLAM_VCEND` | `10` |
| `DRSPEED` | `1` |
| `DRSTALLWD` | `1` |
| `DRSTALLWD_N` | `2400` |
| `DRSTUDY` | `1` |
| `DRSTUDY2P` | `1` |
| `DRSTUDYCOUNTS` | `1` |
| `DRTRACE` | `0` |
| `DRTUCK` | `0` |
| `DRWEAVE` | `1` |
| `DRWEAVELIM` | `40` |
| `DRWRETRY` | `1` |

### Deliberate settings

- `DRHOLDBOARD=0` — soft-bricks the cart after a match; owner ruled ship without it.
- `DRMMC1RST=1` + `DRRTIVEC=1` — **co-dependent, never ship one without the other**: the
  MMC1 bit-7 reset permanently forces PRG mode 3, which is only safe because RTIVEC's NMI
  shield is bank-discriminating. A literal in-bank RTI vector plus MMC1RST is an instant brick.
- `DRFCGATE=1` — narrows the full-clear gate from `mode>=4` to `mode==4`, so the mode-8 intro
  can no longer false-fire it (one byte: `0x0822E` `90`->`D0`).
- `DRBUILDID=0` — pinned so the build stamp cannot move 1868 bytes under a comparison.

### Gate strength — stated honestly

18,000 frames is ~5 minutes of emulated play; the 20 matches are ~15 s AI-vs-idle-P1 rounds,
so this exercises **20 end-of-match transitions**, not a soak. Rule of three on zero events
puts this at **>=28x** better than the defect build — a bound, not a guarantee. Do not quote
"0 events" as "safe".

⚠ Probe `goes`/activity counts from short runs are NOT a health metric (same build gave 9 over
1,200 frames and 2 over 3,000, both verified). Gate on the 18,000-frame run only.
