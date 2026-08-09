# theta400 MiSTer deploy — Phase 1 log (checksums → prior-core record → copy → load → liveness)

Date: 2026-08-09 (all times UTC). Operator: subagent under owner authorization recorded on
task #98 ("you can test on the mister while im gone fwiw", 2026-08-09).
Payload: /mnt/data/drmario_cosim/staging/mister_theta400_20260809/ per DEPLOY.md.
MiSTer: 10.42.0.226 (resolved via tools/mister_ip.sh at 17:23Z), uname -n = MiSTer.

## 1. Checksums (gate: all 19)

`md5sum -c CHECKSUMS.md5` at 17:23Z: **19/19 OK** (DEPLOY.md, NES_theta400_20260809.rbf,
PROVENANCE.txt, cart/mister-tuck-demo-theta400.json, core/{IMAGE_PROOF.log, NES.fit.summary,
NES.sta.summary, core_manifest.json, gate_candidate.log, gate_linknode_winner.log,
gate_pairs.log, gate_rtl_qawt.log, verdict.txt}, drmario_tuck_demo_mister.nes,
evidence/{tuck_lock_s05.png, tuck_lock_s05_zoomP2.png}, fw/{RECIPE.json, copro_rom.hex},
theta400_tuck_demo.mgl). PASS.

## 2. Step 0 — prior core record (rollback manifest)

Saved: `prior_core_record_20260809_1325.txt` in the staging dir (kept, per runbook).
Recorded 2026-08-09T17:25:44Z:

```
71d2de37b1fbcabbb92701fc4094f833  /media/fat/_Console/NES_stomper180_20260801.rbf   <- EXPECTED prior champion, MATCH
6fa85844a255df936259678394838aed  /media/fat/_Console/NES_stomper180s20_20260804.rbf
72d5a92fc73080baa9d6fe74da7810fd  /media/fat/_Console/NES_stomper180s20b_20260804.rbf
caa5b5c669017dac7e14e82b8e94a722  /media/fat/_Console/NES_stomper180s20t3_20260805_seed13.rbf
be266883c5b79759a615220e457fa3af  /media/fat/_Console/NES_tuckmb_20260731.rbf
```

/tmp/CORENAME at record time: `NES`. Rollback mgl `combo_stomper_s20b_probe.mgl` present
(176 B, Aug 4 13:54); its cart `latch_converged_native_probe.nes` present in
/media/fat/games/NES/ (98320 B, Aug 2 23:18). Nothing was deleted or overwritten at any
point in this phase.

Note: a first attempt to md5 ALL of `_Console/*.rbf` (runbook literal) timed out at 120 s
hashing ~44 unrelated console cores; re-ran targeted on the 5 Dr. Mario NES rbfs. The
critical 71d2de37 line was captured in both runs and matched both times.

## 3. Step 0 — interfering units

- `systemctl --user list-units --all | grep -i 'reload|wedge|soak'`: 0 matches.
- `pgrep -af 'preventive|wedge'`: only the pgrep wrapper's own shell (known self-match
  trap, harness-pgrep-self-match). Count of real processes: 0.
- Conclusion: preventive_reload.sh and wedge_probe.sh were NOT running — nothing to stop.
  Did NOT fire a blind `pkill -f` (it would match this session's own wrapper shell).

## 4. Step 1 — copy + device-side md5 gate

scp at ~17:27Z. Device-side md5s (gate values from DEPLOY.md table):

```
de7dea35a9fa03a622cccc8068bd935e  /media/fat/_Console/NES_theta400_20260809.rbf      MATCH
7611d54b35290950d407f08966eb240e  /media/fat/drmario_tuck_demo_mister.nes            MATCH
7611d54b35290950d407f08966eb240e  /media/fat/games/NES/drmario_tuck_demo_mister.nes  MATCH
70ae1043414ea3b5568c637d080fc8d5  /media/fat/theta400_tuck_demo.mgl                  MATCH
```

Deviation (recorded): cart copied to BOTH /media/fat/ (runbook literal) AND
/media/fat/games/NES/ — the working combo_stomper_s20b_probe.mgl resolves its bare-path
cart from games/NES/ (verified on-device; no *.nes exists at /media/fat/ top level), so the
mgl `path="drmario_tuck_demo_mister.nes"` needs the games/NES copy. GATE PASS.

## 5. Step 2 — busy-brick-safe load

- 17:28:52Z `load_core /media/fat/menu.rbf` → CORENAME `MENU` confirmed at 17:29:09Z
  (framework argv: `/media/fat/MiSTer /media/fat/menu.rbf`).
- 17:29:58Z `load_core /media/fat/theta400_tuck_demo.mgl` → at 17:30:14Z framework argv:
  `/media/fat/MiSTer /media/fat/_Console/NES_theta400_20260809.rbf /media/fat/theta400_tuck_demo.mgl`,
  CORENAME `NES`. No load_core was ever issued mid-invocation.

## 6. Liveness gate (NAV_T-advancing capture pairs; 5 captures total)

Trigger: `misterclaw-send -H 10.42.0.226 input combo leftalt f2` (save slot 2), file
`/media/fat/savestates/NES/drmario_tuck_demo_mister_2.ss`, size 1327112 every capture.
Decoder: theta400_liveness/decode_liveness.py — bases re-verified per file by NAV_MAGIC
signature (wram=0x103308, iram=0x102b08 in all 5) + virus ctr==board-popcount
cross-invariant (held on BOTH boards in ALL 5 captures).

| cap | trigger (UTC) | device mtime | NAV_T | BUSY | BUSYSKP | MATCH_ACTIVE | mode $46 | P1 ctr/board | P2 ctr/board | ss md5 |
|-----|--------------|--------------|-------|------|---------|--------------|----------|--------------|--------------|--------|
| 1 | 17:30:43 | 1786296644 | $A4 | $00 | $00 | $01 | $04 | 44/44 | 29/29 | 2ab0a024 |
| 2 | 17:32:02 | 1786296724 | $30 | $00 | $00 | $01 | $04 | 46/46 | 27/27 | a1555fdd |
| 3 | 17:33:34 | 1786296815 | $00 | $00 | $00 | $00 | $08 | 32/32 | 32/32 | 74264a4e-family (11428e4c) |
| 4 | 17:34:57 | — | $1C | $00 | $00 | $01 | $04 | 48/48 | 37/37 | 74264a4e |
| 5 | 17:35:25 | — | $5A | $00 | $00 | $01 | $04 | 47/47 | 25/25 | fe5df7b7 |

(cap3 md5 11428e4c10b05cc2de7ea7ed89b135b7; cap4 74264a4e40e73e7221f05f2524e3ff93;
cap5 fe5df7b72e8cfd775dd713cf1686082b; cap1 2ab0a02442730f1e100e03d89df5a117;
cap2 a1555fdd3a0b9a144a18699a607d5de4. $0727=$02, $04=$01 in all 5.)

**VERDICT: LIVENESS PASS.**
- NAV_T advances in both same-round pairs: cap4→cap5 $1C→$5A over 24 s with
  MATCH_ACTIVE=1 throughout; cap1→cap2 also moved ($A4→$30).
- P2 virus count moves and moves FAST: 37→25 in 24 s (12 clears ≈ 0.5 viruses/s) —
  the copro is searching and committing.
- No brick signature: BUSY $6176 = $00 and BUSYSKP $6192 = $00 in all 5 captures;
  NAV_MAGIC $A5 warm; no static NAV_T anywhere.
- cap3 is a healthy inter-round transition caught mid virus re-placement (32/32 equal and
  growing, MATCH_ACTIVE=0, mode $08); cap4 shows the fresh round at the full L11 count 48.
  This also resolves the cap1 P1=44 vs cap2 P1=46 apparent "increase": 80 s separate
  cap1/cap2 and the measured clear rate (~0.5/s) means they straddled a round boundary —
  different rounds' P1 boards. Round auto-cycling (nav restart) is working.

## 7. State at end of Phase 1

- theta400 core RUNNING on the MiSTer, VS match active, auto-cycling rounds.
- Prior champion untouched: NES_stomper180_20260801.rbf (71d2de37) + s20b mgl + cart all
  still in place; rollback = DEPLOY.md step 6 against prior_core_record_20260809_1325.txt.
- No soak units started (Phase 1 scope ends at the liveness gate).
- Local artifacts: staging dir prior_core_record_20260809_1325.txt; captures + decoder in
  session scratchpad theta400_liveness/ (cap1..cap5.ss + decode_liveness.py; md5s above).
- Next: DEPLOY.md step 3 (>=3-board silicon fingerprints), step 4 (silicon tuck proof),
  step 5 (soak + alarms). STOP rule remains: any fingerprint mismatch → rollback + evidence.
