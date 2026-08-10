# v8 rematch cart — provenance / shipping document

Generated from the recorded manifests, not transcribed by hand.

**GATE STATUS: the two candidates below PASSED the multi-match gate. Neither carries
DRMMC1RST — that flag stops the MMC1 interleave but wedges the cart (see
`tools/gate/results/`), so it is deliberately absent pending root cause.**

## v8-rematch

- **output md5**: `d838ee103ad1c2319d65d3803dd72b76`  (`roms/v8-rematch.nes`, 98320 bytes)
- **base ROM**: `drmario_v28cs.nes` md5 `7d307c3051ebc0f8a10e259e3c270acb`
- **emitter**: `patch_cartridge_copro.py` md5 `546790ca14d6b09f4687bbf668b09846`
- **commit**: `6f032127a089118bb0153f1ae5eece5c6f8343ed` (branch `v8-rematch`, dirty=False)
- **build**: `bash tools/build_v8.sh v8-rematch`
- **rebuild/verify**: `python3 tools/romgen.py rebuild roms/manifests/v8-rematch.json`
- **gate**: 20 matches started / 19 clean round-ends / **0** catastrophic 4->0 / 0 hold episodes / 155 searches, 147 completed (18,000 frames, seed 114)

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
| `DRFCGATE` | `0` |
| `DRHOLDBOARD` | `0` |
| `DRHOLDBOARD_F` | `600` |
| `DRHUMAN` | `1` |
| `DRLEVEL` | `11` |
| `DRMINTHINK` | `12` |
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

## v8-fcgate

- **output md5**: `c16271c6f093b518404d5d17e31616fb`  (`roms/v8-fcgate.nes`, 98320 bytes)
- **base ROM**: `drmario_v28cs.nes` md5 `7d307c3051ebc0f8a10e259e3c270acb`
- **emitter**: `patch_cartridge_copro.py` md5 `546790ca14d6b09f4687bbf668b09846`
- **commit**: `6f032127a089118bb0153f1ae5eece5c6f8343ed` (branch `v8-rematch`, dirty=False)
- **build**: `bash tools/build_v8.sh v8-fcgate DRFCGATE=1`
- **rebuild/verify**: `python3 tools/romgen.py rebuild roms/manifests/v8-fcgate.json`
- **gate**: 20 matches started / 19 clean round-ends / **0** catastrophic 4->0 / 0 hold episodes / 155 searches, 147 completed (18,000 frames, seed 114)

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

## Difference between the two

Exactly one byte: file `0x0822E`, `90` (BCC) -> `D0` (BNE) — DRFCGATE narrowing the
full-clear gate from `mode>=4` to `mode==4`, so the two-bottle intro (mode 8) can no
longer false-fire it. Both rebuild byte-exact from their manifests.

## Known-absent / deliberate

- `DRHOLDBOARD=0` — soft-bricks the cart after a match; owner ruled ship without it.
- `DRMMC1RST=0`, `DRRTIVEC=0` — gated and BLOCKED (wedge), see the gate result commit.
- `DRBUILDID=0` — pinned so the build stamp cannot move bytes under a comparison.

## Gate strength — stated honestly

18,000 frames is ~5 minutes of emulated play. The 20 matches are AI-vs-idle-P1 rounds of
~15 s each (the idle human seat tops out fast), so this exercises **20 end-of-match
transitions** — exactly the defect class DRHOLDBOARD belongs to — but it is **not** 20
human-length matches of soak.

For the mid-match MMC1 crash the relevant figure is total play time. Zero catastrophic
events in 18,000 frames against the defect arm's measured 14 mixed-PRG loads per 3,000
frames puts DRHOLDBOARD=0 at **>=28x better** by a rule-of-three bound, and probably much
better — but it **cannot rule out a crash during a real match against a human**. Quote the
bound, never "0 events = safe".
