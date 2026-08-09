# DEPLOY.md — theta400 champion candidate on MiSTer (one guided session)

Staged 2026-08-09. NOTHING in this directory has touched the MiSTer.
Owner-present deployment only. Estimated session: ~60-90 min including the
fingerprint battery; the soak then runs unattended.

## What ships

| artifact | md5 | what |
|---|---|---|
| `NES_theta400_20260809.rbf` | `de7dea35a9fa03a622cccc8068bd935e` | theta400 core, SEED 13, ALM 37575/41910, copro slack +0.391 |
| `drmario_tuck_demo_mister.nes` | `7611d54b35290950d407f08966eb240e` | first cart ever with the DRTUCK executor wired (DRBUSYESC=1, DRBUILDID=0) |
| `theta400_tuck_demo.mgl` | see CHECKSUMS.md5 | loads the pair above |
| `fw/copro_rom.hex` | `f78f1e9376405dc996404f68dfa9dfb8` | theta400 firmware (DRCOPRO_TUCKV3_THETA=400) — PROVEN inside the rbf (16/16 BRAM-slice bijection + mif 0/16384 diffs, killed-mutant controlled; core/IMAGE_PROOF.log) |

Verify before anything: `cd <this dir> && md5sum -c CHECKSUMS.md5` → all OK.

Evidence behind the release: 81/81 Mesen landed-placement fingerprints vs the
real verilated firmware, incl. the first cart-executed tuck (depth-gain 2,
2 viruses cleared; `evidence/tuck_lock_s05.png`). Full record: `PROVENANCE.txt`.

## Step 0 — reach the box + RECORD PRIOR STATE (do not skip)

Addressing wanders (DHCP + mDNS both unreliable). Resolve per invocation:

```bash
IP=$(~/projects/dr-mario-qa-wt/tools/mister_ip.sh)   # mDNS -> ARP-scan -> fallback
ssh root@$IP 'uname -n; cat /tmp/CORENAME'
```

Record what is running NOW (the s20b champion soak) so rollback is exact:

```bash
ssh root@$IP 'md5sum /media/fat/_Console/*.rbf; ls -la /media/fat/*.mgl /media/fat/*.nes; cat /tmp/CORENAME' \
  | tee prior_core_record_$(date +%Y%m%d_%H%M).txt
```

Expected prior core: `NES_stomper180_20260801.rbf` md5 `71d2de37...` (fw f4b6dfbf).
Keep this file — it IS the rollback manifest.

STOP the soak automation before touching cores (it fights you mid-swap):

```bash
pkill -f preventive_reload.sh          # the 2h menu-cycle loop (PC side)
pkill -f wedge_probe.sh                # observer only, but silence the alarms
```

## Step 1 — copy artifacts (no core change yet)

```bash
cd <this staging dir>
scp NES_theta400_20260809.rbf  root@$IP:/media/fat/_Console/
scp drmario_tuck_demo_mister.nes theta400_tuck_demo.mgl root@$IP:/media/fat/
ssh root@$IP 'md5sum /media/fat/_Console/NES_theta400_20260809.rbf /media/fat/drmario_tuck_demo_mister.nes'
```

GATE: device-side md5s must equal the table above. Do not proceed on mismatch.
(If /media/fat has a working `combo_stomper*.mgl`, sanity-compare its structure
with `theta400_tuck_demo.mgl`; only the rbf name and cart path should differ.)

## Step 2 — BUSY-BRICK-SAFE load (memory: dr-mario-busy-brick)

FPGA BRAM (cart PRG-RAM) survives `load_core`; reloading mid-invocation
latches BUSY=1 + warm NAV_MAGIC → driver dead every boot. Rules:

1. ALWAYS interleave through the menu: 
   ```bash
   ssh root@$IP 'echo load_core /media/fat/menu.rbf > /dev/MiSTer_cmd'; sleep 12
   ssh root@$IP 'echo load_core /media/fat/theta400_tuck_demo.mgl > /dev/MiSTer_cmd'; sleep 15
   ```
2. NEVER `load_core` again while a match is visibly frozen "thinking" — that is
   exactly the mid-invocation window. Wait 10 s, menu-cycle instead.
3. This cart carries the structural fix (DRBUSYESC=1, force-free after ~2 s),
   but do not lean on it during first bring-up.

LIVENESS GATE (never trust one screenshot): two save-state captures ~20 s
apart; NAV_T must ADVANCE and the P2 virus count must eventually move.
Symptom of the brick: title sits >10 s → attract demo. Diagnosis: read
BUSY $6176 from a save-state, don't debug the nav.
Unbrick: menu.rbf cycle, then reload the mgl (rbf reprogram re-inits BRAM).

Save-state read recipe (validated): `misterclaw-send -H $IP input combo leftalt f2`
→ poll remote `stat` until size==1327112 AND mtime changed → scp
`/media/fat/savestates/NES/drmario_tuck_demo_mister_2.ss`. Internal RAM $0000
at ss+0x102b08, cart WRAM $6000 at ss+0x103308 (re-derive by signature if off).

## Step 3 — silicon fingerprints, >=3 boards (memory: dr-mario-silicon-fingerprint-rig)

Same protocol that passed 81/81 in Mesen; the co-sim decisions are the truth.

Boards (the Mesen-screened set, byte-identical copies live in
`/mnt/data/drmario_cosim/staging/tuck_cart_theta400/mesen_qa/`):
1. `hostdata_l11_20` board 18 — expected col=4 family incl. 3 lateral tucks
2. `hostdata_l11_hz30` board 29 — expected col=3 o4=2 TUCK_COL=2 TUCK_ROW=4 (the proof board)
3. `hostdata_l11_hz30` board 29 replicate (determinism check) + >=1 natural-play board

Per board:
1. Build patched .ss locally from a fresh-P2-spawn template: patch board $0500,
   pin pill $0381/$0382, then RESET the search state exactly as the rig fix says:
   ARMED2 $6161=0, WDOG2 $6162=0, WDOGH2 $6166=0, PEND2 $614F=1, DELAY2 $615F=0,
   ROT_DONE2 $616E=0, STABLE_CT2 $6171=0, SLAM_ARM $6172=0, LASTY2 $6155=cur $0386.
   Patch INTERNAL RAM only (cart-WRAM mirror is ignored by the loader).
   NEW for this cart: also invalidate the tuck latch — TUCK_C2/TUCK_R2 (the two
   driver bytes after TGT_C2/$6152,TGT_O2/$6153; see patch_cartridge_copro.py
   on branch tuck-cart-mister) so a stale descriptor can't leak across injects.
2. scp over the slot file, `load_core` the mgl (re-caches from disk), wait 15 s,
   bare `input combo f2` to load.
3. Read the COMMITTED result, not the live argmax: one save at ~4.5 s post-load,
   diff board vs injected, GUARD occ==injected+2 (exactly one pill). Compare
   (col, orient from PLACED CELLS — mailbox orient byte is copro-space,
   map {0:3,1:1,2:0,3:2}) and cell colors vs the co-sim decision.
4. PASS bar: >=3 distinct boards, every landed placement matching, board-29
   replicate identical twice. Any mismatch → stop, capture the .ss, compare
   against `mesen_qa/analyze_fp.py` output — do NOT rationalize a miss
   (fidelity is regime-dependent; a near-death divergence is signal).

## Step 4 — silicon tuck-execution proof (first tuck on real silicon)

Board 2 above is pre-screened: shipped fw publishes col=3 o4=2 TUCK_COL=2
TUCK_ROW=4 on it, and the Mesen executor landed (4,3),(4,4) UNDER the (3,4)
lip, clearing 2 viruses unreachable by any straight drop.

1. Inject board 29 as in Step 3 (pill pinned (cA,cB)=(0,2)).
2. Confirm the driver latched TUCK_C2=2 / TUCK_R2=11 (save-state at ~2 s).
3. Take saves at ~3.5 s and ~5 s: expect approach to col2, switch at trigger
   row, DAS slide right, lock at board cells (4,3)=yellow,(4,4)=blue; the
   4-blue column clears 2 viruses.
4. Screenshot at lock (`mister-screenshot` skill, pass $IP explicitly; the
   misterclaw shot service needs a few min post-boot — use save-states if it
   times out). Mesen reference: `evidence/tuck_lock_s05.png` — the silicon
   frame should match it cell-for-cell.
PASS = landed cells+colors exact. That is the first tuck ever executed on
silicon; archive .ss + screenshot next to prior_core_record.

## Step 5 — start the soak + alarms

Expectations: CvC autonav soaks wedge the DISPLAY path over hours (driver/RTL
exonerated; it is a rig cost, not a demo risk). Auto-reboot is OFF by design.

```bash
# preventive 2h menu-cycle (edit the mgl path from the stomper one):
sed 's|combo_stomper_s20b_probe.mgl|theta400_tuck_demo.mgl|' \
  ~/projects/dr_mario_rl/tmp/preventive_reload.sh > ~/projects/dr_mario_rl/tmp/preventive_reload_theta400.sh
chmod +x ~/projects/dr_mario_rl/tmp/preventive_reload_theta400.sh
systemd-run --user --unit drm-soak-reload-theta400 ~/projects/dr_mario_rl/tmp/preventive_reload_theta400.sh

# wedge observer + alarm (observe-only, ENABLE_AUTO_REBOOT=0):
systemd-run --user --unit drm-wedge-probe-theta400 \
  ~/projects/dr-mario-qa-wt/experiments/freeze5_blackscreen/wedge_probe.sh
```

Alarm discrimination order (memory mister-savestate-ram-read): a "stale
captures" alarm = ADDRESSING until proven otherwise — re-run mister_ip.sh,
ssh + `cat /tmp/CORENAME`, THEN suspect a wedge; a wedge is proven by
screenshot TIMEOUT, never by frame content (use 3-capture motion when in doubt).
Soak ledger: capture a save-state pair every few hours; log P2 virus counts and
any tuck latches (TUCK_C2 != invalid) — the soak doubles as tuck-frequency data
(shipped fw publish rate was 4/100 boards offline; count silicon publishes).

## Step 6 — rollback (exact, ~2 min)

The prior champion is untouched on the SD; nothing is overwritten by this deploy.

```bash
IP=$(~/projects/dr-mario-qa-wt/tools/mister_ip.sh)
ssh root@$IP 'echo load_core /media/fat/menu.rbf > /dev/MiSTer_cmd'; sleep 12
ssh root@$IP 'echo load_core /media/fat/combo_stomper_s20b_probe.mgl > /dev/MiSTer_cmd'
# then restart the ORIGINAL preventive_reload.sh and wedge probe
```

Verify against `prior_core_record_*.txt` (rbf md5 71d2de37..., CORENAME).
If the driver looks dead after any swap: menu-cycle first (busy-brick), only
then investigate. Never delete `NES_stomper180_20260801.rbf`.

## Provenance chain (why you can trust the bits)

- Cart: romgen manifest `cart/mister-tuck-demo-theta400.json`, branch
  tuck-cart-mister @ 69459c6, rebuild = `tools/romgen.py rebuild`, determinism
  verified (two builds byte-identical). Gates 0-5 + fw-image gates green.
- Core: `core/core_manifest.json` (rtl ff1db5a, SEED 13), fit/STA verdict
  SHIP AS-IS (`core/verdict.txt`), update_mif no-op defeated (clean db),
  firmware-in-image proven two independent ways (`core/IMAGE_PROOF.log`),
  bit-exactness gates candidate/pairs/rtl/linknode PASS (`core/gate_*.log`).
- Emulator gate: 81/81 fingerprints, 0 bridge misses, tuck proof replicated
  twice (`PROVENANCE.txt` Phase 3).
