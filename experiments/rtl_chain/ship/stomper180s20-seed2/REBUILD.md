# Rebuild the strand20 core (#47 abandoned-material fix, first silicon)

Deployed to the user's MiSTer 2026-08-04 02:45 as `_Console/NES_stomper180s20_20260804.rbf`.

## Identity

| | |
|---|---|
| arm | Combo Stomper chain180 + **DRSTRAND=20** (#47 stranded-half root cost) |
| rbf | `6fa85844a255df936259678394838aed` (not in git; 3.5MB) |
| firmware | `e970e9ab0208cdbce1d39ed33e2f51ee` (`fw_stomper180s20.hex`, here) |
| RTL | NES_MiSTer-winner `claude/winner-single-copro` @ `7f6ba69` (CMD-8 vendor) |
| copro source | dr-mario-canonical `copro-canonical` @ merge `64f3860`, tag `eval47-silicon` |
| seed | 2 (only SEED line in NES.qsf) |
| fit | slack **+0.102**, ALM **37,591**/41,910 (baseline 37,249 → CMD-8 = +342) |
| cart | latch_converged_native_probe.nes (UNCHANGED) via combo_stomper_s20_probe.mgl |

## Recipe

    cd dr-mario-canonical-wt/fpga/copro
    DRSTRAND=20 DRCOPRO_TUCK=1 DRCOPRO_ARM=1 DRFIX=1 DRCHAIN=180 python dbg_build.py all 0
    # -> copro_rom.hex e970e9ab  (DRSTRAND unset MUST give f4b6dfbf — drift guard)
    cp copro_rom.hex NES_MiSTer-winner/copro_rom.hex
    cp LeafEval.sv CoproDrMario.sv NES_MiSTer-winner/rtl/mappers/   # CMD-8 scan
    cd NES_MiSTer-winner && rm -rf db incremental_db && ./run_fit.sh

## Provenance (offline gates, all green before silicon)
- fast rig n=120: ws=20 pills −7.90 [−13.98,−1.68] REAL, stranded −66%, deaths 5→1
- leaf_r47 mirror n=120: −9.85 [−16.28,−3.57] REAL (stronger than fast rig)
- VS vs chain180 n=60: 54.2% [45.8,62.5], atk 11.87v11.31 (attack channel intact)
- tb_strand 200/200 (incl. user-flagged silicon fixture); co-sim GATE PASS CELL-EXACT
- byte-identity: DRSTRAND unset reproduces c87e60a1 (baseline) AND f4b6dfbf (ship)

## Silicon stability addendum (2026-08-04 morning)

The seed-2 MiSTer build (+0.102 slack) froze **3x in ~7h** of duel soak
(03:33 black-screen save-refusal; 08:35 frozen-counts; ~10:00 frozen-counts)
vs chain180's (+0.181) historical ~1.5/day. All three are pre-existing freeze
classes, but the RATE convicts the thin margin in practice. Seed sweep:
seed2 +0.102 / seed3 −0.327 / seed5 −0.049 / seed7 (pending). Duel reverted
to chain180 at ~10:02 pending a passing build. If no seed clears ~+0.15, the
next lever is a dedicated copro-clock retime (NOT clk85 — SDRAM/EEPROM clock,
never touch), or modest copro MHz reduction.

**The Pocket build is unaffected**: its own fit carries +1.586 worst setup
slack (15x the MiSTer margin) on a different device; the strand20 Pocket
payload ships regardless.

**RESOLUTION**: seed 7 = **+0.156 slack, TNS 0.000**, ALM 37,661 — deployed
2026-08-04 ~10:15 as `NES_stomper180s20b_20260804.rbf` (72d5a92f), duel
relaunched via combo_stomper_s20b_probe.mgl. s20b supersedes the seed-2 rbf
for the MiSTer; seed-2 kept on device per keep-all-versions.

s20b freeze #1 at ~13:45 (~3.5h post-deploy; frozen-counts class). Better than
seed2 (48min) but likely still above chain180 baseline. NEW WORKING THEORY if
rate stays elevated at matched slack: CMD-8 adds ~28 GO transactions/decision
(~2x mailbox traffic) -> proportional exposure to the KNOWN copro-wait/GO-storm
freeze class (see freeze #4/#40 + unfixed stale-ARMED2 defect). Remedy would be
the driver-side ARMED2 fix, not further reseeds.

s20b freeze #2 @ ~19:00 (~5.3h after #1). s20b rate ~5.5/day vs chain180
~1.5/day at near-matched slack (+0.156 vs +0.181) — timing largely EXONERATED;
GO-traffic/ARMED2 exposure theory now primary. Named fix: driver stale-ARMED2
re-entrancy repair (dr-mario-p0-defects-verified), next silicon session.

**s20b freeze #3 (2026-08-04 ~23:38, logged 23:45):** mid-PLAY wedge, display
alive, in-play counts frozen at (4, 41-25) across 3 tracker captures
(233830/234134/234437 .ss = evidence). Same copro-wait/ARMED2-family
signature as #1/#2. Detection: frozen-counts alarm (3rd live catch).
Recovery: menu.rbf cycle + mgl relaunch, clean (post_recovery_2346.png,
fresh game 46-46). Freeze rate now 3 in ~29h. Remedy unchanged: stale-ARMED2
driver fix + the #49 COLGATE port (audit found the pair-latch fix never
shipped in this lineage's driver either — same root repair session).

**s20b freeze #4 (2026-08-05 ~00:40, logged 00:52): FIRST BLACK-SCREEN-CLASS
on s20b** — display fully blank (wedge2_0051.png, 1KB), save-state captures
STALE x5 (the freeze-#5/task-#42 signature: states return nothing), distinct
from freezes #1-3 (mid-play, display alive). Recovery: menu.rbf cycle +
relaunch, clean (post_recovery2_0052.png, brightness 55.6). Rate: 4 freezes
in ~30h, now TWO distinct families on this core. Stability workstream note:
the stale-ARMED2/commit-path remedies target the mid-play family; the
black-screen family remains uncharacterized (no state capture possible by
definition) — needs a different instrument (e.g. periodic RAM-snapshot
BEFORE death, or core-side watchdog register).

**s20b freeze #5 (2026-08-05 ~01:40, logged 01:58): black-screen class
AGAIN** — 1KB blank screenshot (wedge3_0157.png), STALE x5, identical
signature to freeze #4 one hour earlier. Recovery clean (post_recovery3,
8KB). Rate: 5 in ~31h, black-screen family now 2/5 and accelerating
(2 in the last 2 hours vs 0 in the first 27). Pattern watch: both
black-screen events occurred during overnight unattended soak; if #6
follows within ~1-2h, suspect a time/uptime-correlated resource leak
rather than a per-game race — instrument accordingly (pre-death RAM
snapshot ring + core watchdog remain the named instruments).
